const net = require('net');
const fs = require('fs');
const path = require('path');
const root = process.env.PALM_SYNC_ROOT;
console.log('Loading Palm connection software');
const {SerialSyncConnection} = require(path.join(root,'dist/protocols/sync-connections'));
const {DlpReadStorageInfoReqType,DlpDeleteDBReqType} = require(path.join(root,'dist/protocols/dlp-commands'));
const {readDbList,readRawDb} = require(path.join(root,'dist/sync-utils/read-db'));
const {writeRawDb} = require(path.join(root,'dist/sync-utils/write-db'));
const {RawPrcDatabase} = require(path.join(root,'node_modules/palm-pdb'));
console.log('Palm connection software loaded');
const out = process.argv[2];
fs.mkdirSync(out,{recursive:true});
const server=net.createServer(async socket=>{
 server.close();
 const conn=new SerialSyncConnection(socket,{maxBaudRate:Number(process.env.PALM_BAUD || 9600)});
 try {
  await conn.doHandshake(); console.log('PALM_BAUD='+conn.baudRate);
  await new Promise(resolve=>setTimeout(resolve,150));
  console.log('Two-way HotSync handshake complete');
  await conn.start();
  const storage=await conn.dlpConnection.execute(new DlpReadStorageInfoReqType());
  const dbs=await readDbList(conn.dlpConnection,{ram:true,rom:false});
  fs.writeFileSync(path.join(out,'device-info.json'),JSON.stringify({system:conn.dlpConnection.sysInfo,storage,databases:dbs},null,2));
  console.log('System:',JSON.stringify(conn.dlpConnection.sysInfo));
  console.log('Storage:',JSON.stringify(storage));
  console.log('RAM databases:',dbs.length);
  if(process.env.PALM_BACKUP==='1') {
   for(const [i,info] of dbs.entries()) {
    console.log(`Backing up ${i+1}/${dbs.length}: ${info.name}`);
    const db=await readRawDb(conn.dlpConnection,info.name,{dbInfo:info,includeDeletedAndArchivedRecords:true});
    const filename=String(i).padStart(3,'0')+'-'+info.name.replace(/[^a-zA-Z0-9_.-]/g,'_')+(info.dbFlags.resDB?'.prc':'.pdb');
    fs.writeFileSync(path.join(out,filename),db.serialize());
   }
   fs.writeFileSync(path.join(out,'BACKUP_COMPLETE'),'All enumerated RAM databases retrieved.\n');
  }
  if(process.env.PALM_INSTALL) {
   const backupDir=process.env.PALM_BACKUP_DIR;
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
    const old=await readRawDb(conn.dlpConnection,expected.header.name);
    if(!matches(old,expected)) throw new Error('Installed app differs from the verified previous build');
    fs.writeFileSync(path.join(out,'previous-PalmAnimation.prc'),old.serialize());
    overwrite=expected.header.name===app.header.name;
    if(!overwrite) previousName=expected.header.name;
   }
   console.log('Installing '+app.header.name);
   await writeRawDb(conn.dlpConnection,app,{overwrite});
   console.log('App written; reading all resources back for verification');
   const verify=await readRawDb(conn.dlpConnection,app.header.name);
   if(verify.records.length!==app.records.length || verify.records.some((r,i)=>r.entry.type!==app.records[i].entry.type || r.entry.resourceId!==app.records[i].entry.resourceId || !r.data.equals(app.records[i].data))) throw new Error('Installed resource verification failed');
   console.log('Installed app verified by reading back all resources');
   if(previousName) {await conn.dlpConnection.execute(DlpDeleteDBReqType.with({cardNo:0,name:previousName}));console.log('Previous app name removed: '+previousName);}
  }
  await conn.end();console.log('Session finished successfully');socket.end(()=>setTimeout(()=>process.exit(0),100));
 } catch(e) {console.error('Session failed:',e.stack);socket.destroy();process.exitCode=1;setTimeout(()=>process.exit(1),100);}
});
server.listen(16416,'127.0.0.1',()=>console.log('HotSync server ready'));
