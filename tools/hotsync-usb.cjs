const fs = require('fs');
const path = require('path');
const root = process.env.PALM_SYNC_ROOT;
const {UsbSyncServer} = require(path.join(root,'dist/sync-servers/usb-sync-server'));
const configs=require(path.join(root,'dist/sync-servers/usb-device-configs'));
for(const [id,cfg] of Object.entries(configs.USB_DEVICE_CONFIGS_BY_ID)) if(cfg.vendorId!==0x0830 || cfg.productId!==0x0040) delete configs.USB_DEVICE_CONFIGS_BY_ID[id];
const {DlpReadStorageInfoReqType,DlpDeleteDBReqType} = require(path.join(root,'dist/protocols/dlp-commands'));
const {readDbList,readRawDb} = require(path.join(root,'dist/sync-utils/read-db'));
const {writeRawDb} = require(path.join(root,'dist/sync-utils/write-db'));
const {RawPrcDatabase} = require(path.join(root,'node_modules/palm-pdb'));
const out = process.argv[2];
fs.mkdirSync(out,{recursive:true});
let success=false;
const server=new UsbSyncServer(async dlp=>{
 try {
  const storage=await dlp.execute(new DlpReadStorageInfoReqType());
  const dbs=await readDbList(dlp,{ram:true,rom:false});
  fs.writeFileSync(path.join(out,'device-info.json'),JSON.stringify({system:dlp.sysInfo,storage,databases:dbs},null,2));
  console.log('System:',JSON.stringify(dlp.sysInfo));
  console.log('Storage:',JSON.stringify(storage));
  console.log('RAM databases:',dbs.length);
  if(true) {
   for(const [i,info] of dbs.entries()) {
    console.log(`Backing up ${i+1}/${dbs.length}: ${info.name}`);
    const db=await readRawDb(dlp,info.name,{dbInfo:info,includeDeletedAndArchivedRecords:true});
    const filename=String(i).padStart(3,'0')+'-'+info.name.replace(/[^a-zA-Z0-9_.-]/g,'_')+(info.dbFlags.resDB?'.prc':'.pdb');
    fs.writeFileSync(path.join(out,filename),db.serialize());
   }
   fs.writeFileSync(path.join(out,'BACKUP_COMPLETE'),'All enumerated RAM databases retrieved.\n');
  }
  if(process.env.PALM_INSTALL) {
   const backupDir=out;
   if(!backupDir || !fs.existsSync(path.join(backupDir,'BACKUP_COMPLETE'))) throw new Error('A completed backup is required before installation');
   const bytes=fs.readFileSync(process.env.PALM_INSTALL);
   const app=RawPrcDatabase.from(bytes);
   if(!["Palm Animation","Ade's App"].includes(app.header.name) || app.header.creator!=='PAnm' || app.header.type!=='appl') throw new Error('Unexpected app identity');
   const matches=(a,b)=>a.records.length===b.records.length && a.records.every((r,i)=>r.entry.type===b.records[i].entry.type && r.entry.resourceId===b.records[i].entry.resourceId && r.data.equals(b.records[i].data));
   const existing=dbs.filter(info=>info.name===app.header.name || info.creator===app.header.creator);
   let overwrite=false;let previousName=null;
   if(existing.length) {
    if(existing.length!==1 || existing[0].creator!==app.header.creator || !process.env.PALM_REPLACE_FROM) throw new Error('Unexpected app collision; refusing replacement');
    const expected=RawPrcDatabase.from(fs.readFileSync(process.env.PALM_REPLACE_FROM));
    if(expected.header.name!==existing[0].name || expected.header.creator!==app.header.creator) throw new Error('Replacement backup identity mismatch');
    const old=await readRawDb(dlp,expected.header.name);
    if(!matches(old,expected)) throw new Error('Installed app differs from the verified previous build');
    fs.writeFileSync(path.join(out,'previous-PalmAnimation.prc'),old.serialize());
    overwrite=expected.header.name===app.header.name;
    if(!overwrite) previousName=expected.header.name;
   }
   console.log('Installing '+app.header.name);
   await writeRawDb(dlp,app,{overwrite});
   console.log('App written; reading all resources back for verification');
   const verify=await readRawDb(dlp,app.header.name);
   if(verify.records.length!==app.records.length || verify.records.some((r,i)=>r.entry.type!==app.records[i].entry.type || r.entry.resourceId!==app.records[i].entry.resourceId || !r.data.equals(app.records[i].data))) throw new Error('Installed resource verification failed');
   console.log('Installed app verified by reading back all resources');
   if(previousName) {await dlp.execute(DlpDeleteDBReqType.with({cardNo:0,name:previousName}));console.log('Previous app name removed: '+previousName);}
  }

  success=true;
 } catch(e) {console.error('Session failed:',e.stack); throw e;}
});
server.on('disconnect',()=>{console.log(success?'m125 installation session verified and complete':'m125 session failed');setTimeout(()=>process.exit(success?0:1),1500);});
server.start().then(()=>console.log('READY: press HotSync on the m125. Waiting for Palm USB 0830:0040.'));
setTimeout(()=>{console.error('USB HotSync wait expired');process.exit(1);},1800000);
