'use strict';
const $ = id => document.getElementById(id);
let state, selected = null, bytes = null, frame = 0, playing = false, timer, selectionVersion = 0;
let librarySignature = '', previousJob = '', busyUploads = false;
const buffers = new Map();
const formatBytes = n => n < 1024*1024 ? `${Math.round(n/1024)} KB` : `${(n/1024/1024).toFixed(2)} MB`;
const settings = () => ({fit:$('fit').value,dither:$('dither').value,fps:$('fps').value});
function error(message) { $('error').hidden = !message; $('error').textContent = message || ''; }
async function request(path, body = {}, method = 'POST') {
  const res = await fetch(path,{method,headers:{'Content-Type':'application/json','X-Palm-Token':state.token},body:JSON.stringify(body)});
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || 'The request failed.');
  return data;
}
async function action(fn) { error(''); try { await fn(); await refresh(); } catch(e) { error(e.message); } }
function draw(canvas, data, index, inverted = false) {
  const context = canvas.getContext('2d');
  const image = context.createImageData(160,160);
  for(let i=0;i<25600;i++) {
    let black = !!(data[index*3200+(i>>3)] & (128 >> (i&7)));
    if (inverted) black = !black;
    const value = black ? 0 : 255;
    image.data.set([value,value,value,255],i*4);
  }
  context.putImageData(image,0,0);
}
function renderFrame() {
  if(!bytes || !selected) return;
  draw($('screen'),bytes,frame,$('invert').checked);
  $('scrub').value = frame;
  $('frame-position').textContent = `${frame+1} / ${selected.frames} frames`;
}
function pause() {playing=false; clearTimeout(timer); $('play-icon').textContent='▶'; $('play-label').textContent='Play'; $('play').setAttribute('aria-label','Play preview');}
function tick() {
  if(!playing || !selected) return;
  timer=setTimeout(()=>{frame=(frame+1)%selected.frames;renderFrame();tick();},selected.durations[frame]);
}
function play() {playing=true;$('play-icon').textContent='Ⅱ';$('play-label').textContent='Pause';$('play').setAttribute('aria-label','Pause preview');tick();}
async function buffer(id) {
  if(!buffers.has(id)) {
    const res=await fetch('/api/preview/'+id);
    if(!res.ok) throw new Error('The preview could not be loaded.');
    buffers.set(id,new Uint8Array(await res.arrayBuffer()));
  }
  return buffers.get(id);
}
async function select(clip) {
  pause(); selected=clip; bytes=null; frame=0;
  const version=++selectionVersion;
  $('editor').hidden=!clip;$('empty-preview').hidden=!!clip;$('play').disabled=!clip;$('scrub').disabled=!clip;
  if(!clip) { $('screen').getContext('2d').clearRect(0,0,160,160);$('frame-position').textContent='Palm screen preview';return; }
  $('name').value=clip.name;
  for(const key of ['fit','dither','fps']) $(key).value=clip.options[key];
  $('pixel-note').textContent=clip.exact?'Original pixels preserved. No resizing or new dithering.':`${clip.dimensions[0]} × ${clip.dimensions[1]} source → 160 × 160 Palm pixels.`;
  $('scrub').max=clip.frames-1;
  try {
    const data=await buffer(clip.id);
    if(version!==selectionVersion)return;
    bytes=data; renderFrame();
    if(!matchMedia('(prefers-reduced-motion: reduce)').matches) play();
  } catch(e){error(e.message);}
  document.querySelectorAll('.clip-select').forEach(b=>b.classList.toggle('selected',b.dataset.id===clip.id));
}
function icon(path) {
  const svg=document.createElementNS('http://www.w3.org/2000/svg','svg');
  svg.setAttribute('viewBox','0 0 24 24');svg.setAttribute('fill','none');svg.setAttribute('stroke','currentColor');svg.setAttribute('stroke-width','1.5');svg.setAttribute('aria-hidden','true');
  const p=document.createElementNS(svg.namespaceURI,'path');p.setAttribute('d',path);p.setAttribute('stroke-linecap','round');p.setAttribute('stroke-linejoin','round');svg.append(p);return svg;
}
function renderLibrary() {
  const signature=JSON.stringify(state.clips.map(c=>[c.id,c.name]));
  if(signature===librarySignature)return;
  librarySignature=signature;$('library').replaceChildren();
  for(const clip of state.clips) {
    const row=document.createElement('div');row.className='clip-row';
    const button=document.createElement('button');button.className='clip-select';button.dataset.id=clip.id;button.classList.toggle('selected',selected?.id===clip.id);button.setAttribute('aria-label',`Preview ${clip.name}`);
    const canvas=document.createElement('canvas');canvas.width=canvas.height=160;canvas.setAttribute('aria-hidden','true');
    const text=document.createElement('span');text.className='clip-copy';
    const name=document.createElement('strong');name.textContent=clip.name;
    const meta=document.createElement('span');meta.className='caption';meta.textContent=`${clip.frames} frames · ${(clip.duration/1000).toFixed(1)} sec · ${formatBytes(clip.frames*3228)}`;
    text.append(name,meta);button.append(canvas,text);button.onclick=()=>select(clip);
    const remove=document.createElement('button');remove.className='remove';remove.setAttribute('aria-label',`Remove ${clip.name}`);remove.title=`Remove ${clip.name}`;remove.append(icon('m6 6 12 12M6 18 18 6'));
    remove.onclick=()=>action(()=>request('/api/clips/'+clip.id,{},'DELETE'));
    row.append(button,remove);$('library').append(row);
    buffer(clip.id).then(data=>draw(canvas,data,0)).catch(e=>error(e.message));
  }
  $('empty-library').hidden=state.clips.length>0;
}
function taskView() {
  const job=state.job;
  $('task').hidden=!job;
  if(!job)return;
  $('task-title').textContent=job.message;
  $('task-detail').textContent=job.detail || '';
  $('task-progress').hidden=job.status!=='running';
  $('cancel').hidden=job.status!=='running'||!job.cancellable;
  $('stages').hidden=job.kind!=='sync';
  const order=['preparing','building','connecting','waiting','connected','backup','installing','verifying','finishing','complete'];
  for(const li of $('stages').children) {
    const a=order.indexOf(job.phase),b=order.indexOf(li.dataset.stage);
    li.classList.toggle('done',a>b);li.classList.toggle('active',a===b);
  }
  $('download').hidden=job.kind!=='build'||job.status!=='complete'||!state.download;
}
function controls() {
  const busy=state.job?.status==='running'||busyUploads;
  for(const id of ['add','demo','rename','convert','build','sync','device','fit','dither','fps','name']) {
    $(id).disabled=busy || (['rename','convert'].includes(id)&&!selected) || (['build','sync'].includes(id)&&(!state.clips.length||state.setup.length>0));
  }
  document.querySelectorAll('.remove').forEach(b=>b.disabled=busy);
  $('drop').setAttribute('aria-disabled',String(busy));
  $('size').textContent=`${state.clips.length} animation${state.clips.length===1?'':'s'} · ${formatBytes(state.estimatedBytes)} estimated`;
  $('capacity').value=state.estimatedBytes;
}
async function refresh() {
  const res=await fetch('/api/state');if(!res.ok)throw new Error('Cannot reach the local server.');
  state=await res.json();
  for(const id of buffers.keys())if(!state.clips.some(c=>c.id===id))buffers.delete(id);
  $('setup').hidden=!state.setup.length;$('setup-list').replaceChildren();
  for(const item of state.setup){const li=document.createElement('li');li.textContent=item;$('setup-list').append(li);}
  renderLibrary();
  const jobKey=state.job ? state.job.id+state.job.status : '';
  if(jobKey!==previousJob && state.job?.status==='complete' && state.job.clipId) await select(state.clips.find(c=>c.id===state.job.clipId));
  else if(selected&&!state.clips.find(c=>c.id===selected.id))await select(state.clips[0]||null);
  else if(!selected&&state.clips.length)await select(state.clips[0]);
  else if(selected)selected=state.clips.find(c=>c.id===selected.id);
  previousJob=jobKey;taskView();controls();
}
function fileBase64(file) {
  return new Promise((resolve,reject)=>{const reader=new FileReader();reader.onload=()=>resolve(reader.result.split(',')[1]);reader.onerror=()=>reject(new Error('Could not read the GIF.'));reader.readAsDataURL(file);});
}
async function upload(files) {
  if(state.job?.status==='running'||busyUploads)return;
  busyUploads=true;controls();error('');
  try {
    for(const file of files) {
      if(file.size>20*1024*1024)throw new Error(`${file.name} is over 20 MB. Choose a smaller GIF.`);
      await request('/api/upload',{filename:file.name,data:await fileBase64(file),fit:'center',dither:'auto',fps:'source'});
      do {await new Promise(r=>setTimeout(r,350));await refresh();}while(state.job.status==='running');
      if(state.job.status!=='complete')throw new Error(state.job.message);
    }
  }catch(e){error(e.message);}finally{busyUploads=false;$('files').value='';await refresh();}
}
$('add').onclick=()=>$('files').click();$('files').onchange=()=>upload([...$('files').files]);
$('drop').onclick=()=>{if($('drop').getAttribute('aria-disabled')!=='true')$('files').click();};
$('drop').onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();$('drop').click();}};
$('drop').ondragover=e=>{e.preventDefault();$('drop').classList.add('dragging');};
$('drop').ondragleave=()=>$('drop').classList.remove('dragging');
$('drop').ondrop=e=>{e.preventDefault();$('drop').classList.remove('dragging');upload([...e.dataTransfer.files]);};
$('demo').onclick=()=>action(()=>request('/api/demo'));
$('play').onclick=()=>playing?pause():play();$('screen').onclick=()=>{if(bytes)playing?pause():play();};
$('invert').onchange=renderFrame;
$('scrub').oninput=()=>{pause();frame=Number($('scrub').value);renderFrame();};
$('rename').onclick=()=>action(()=>request('/api/clips/'+selected.id,{name:$('name').value},'PATCH'));
$('convert').onclick=()=>action(()=>request('/api/clips/'+selected.id+'/convert',settings()));
$('build').onclick=()=>action(()=>request('/api/build'));
$('sync').onclick=()=>action(()=>{pause();return request('/api/sync',{device:$('device').value});});
$('cancel').onclick=()=>action(()=>request('/api/cancel'));
async function poll(){try{await refresh();}catch(e){error('The local server is unavailable. Restart it to continue.');}setTimeout(poll,1000);}
poll();
