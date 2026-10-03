const fs = require('fs');
const path = require('path');
const root = process.env.PALM_SYNC_ROOT;
const {UsbSyncServer} = require(path.join(root,'dist/sync-servers/usb-sync-server'));
const configs=require(path.join(root,'dist/sync-servers/usb-device-configs'));
for(const [id,cfg] of Object.entries(configs.USB_DEVICE_CONFIGS_BY_ID)) if(cfg.vendorId!==0x0830 || cfg.productId!==0x0040) delete configs.USB_DEVICE_CONFIGS_BY_ID[id];
const {DlpReadStorageInfoReqType} = require(path.join(root,'dist/protocols/dlp-commands'));
const {readDbList,readRawDb} = require(path.join(root,'dist/sync-utils/read-db'));
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
  await require('./install-app.cjs').installApp(dlp,{dbs,storage,out});

  success=true;
 } catch(e) {console.error('Session failed:',e.stack); throw e;}
});
server.on('disconnect',()=>{console.log(success?'m125 installation session verified and complete':'m125 session failed');setTimeout(()=>process.exit(success?0:1),1500);});
server.start().then(()=>console.log('READY: press HotSync on the m125. Waiting for Palm USB 0830:0040.'));
setTimeout(()=>{console.error('USB HotSync wait expired');process.exit(1);},1800000);
