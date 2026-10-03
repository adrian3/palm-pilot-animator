const net = require('net');
const fs = require('fs');
const path = require('path');
const root = process.env.PALM_SYNC_ROOT;
console.log('Loading Palm connection software');
const {SerialSyncConnection} = require(path.join(root,'dist/protocols/sync-connections'));
const {DlpReadStorageInfoReqType} = require(path.join(root,'dist/protocols/dlp-commands'));
const {readDbList,readRawDb} = require(path.join(root,'dist/sync-utils/read-db'));
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
  await require('./install-app.cjs').installApp(conn.dlpConnection,{dbs,storage,out});
  await conn.end();console.log('Session finished successfully');socket.end(()=>setTimeout(()=>process.exit(0),100));
 } catch(e) {console.error('Session failed:',e.stack);socket.destroy();process.exitCode=1;setTimeout(()=>process.exit(1),100);}
});
server.listen(16416,'127.0.0.1',()=>console.log('HotSync server ready'));
