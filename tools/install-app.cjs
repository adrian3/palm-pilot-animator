/* Shared checked installation for command-line and local-web receivers. */
const fs = require('fs');
const path = require('path');
const matches = (a,b) => a.records.length===b.records.length && a.records.every((r,i)=>r.entry.type===b.records[i].entry.type && r.entry.resourceId===b.records[i].entry.resourceId && r.data.equals(b.records[i].data));
function decideReplacement(existing, app, {expected, freshBackup=false}={}) {
  if(!existing.length) return false;
  if(existing.length!==1 || existing[0].creator!==app.header.creator || existing[0].type!=='appl' || !['Palm Animation',"Ade's App"].includes(existing[0].name)) throw new Error('Unexpected app collision; refusing replacement');
  if(expected) {
    if(expected.header.name!==existing[0].name || expected.header.creator!==app.header.creator) throw new Error('Replacement backup identity mismatch');
  } else if(!freshBackup) throw new Error('A verified previous build or fresh device backup is required before replacement');
  return existing[0].name===app.header.name;
}
function dependencies(root) {
  return {
    ...require(path.join(root,'dist/protocols/dlp-commands')),
    ...require(path.join(root,'dist/sync-utils/read-db')),
    ...require(path.join(root,'dist/sync-utils/write-db')),
    ...require(path.join(root,'node_modules/palm-pdb')),
  };
}
async function installApp(dlp,{dbs,storage,out}, env=process.env, suppliedDependencies) {
  if(!env.PALM_INSTALL) return;
  const {DlpDeleteDBReqType,readRawDb,writeRawDb,RawPrcDatabase}=suppliedDependencies || dependencies(env.PALM_SYNC_ROOT);
  const backupDir=env.PALM_BACKUP_DIR || out;
  if(!backupDir || !fs.existsSync(path.join(backupDir,'BACKUP_COMPLETE'))) throw new Error('A completed backup is required before installation');
  const bytes=fs.readFileSync(env.PALM_INSTALL);
  const app=RawPrcDatabase.from(bytes);
  if(!['Palm Animation',"Ade's App"].includes(app.header.name) || app.header.creator!=='PAnm' || app.header.type!=='appl') throw new Error('Unexpected app identity');
  const existing=dbs.filter(info=>info.name===app.header.name || info.creator===app.header.creator);
  const expected=env.PALM_REPLACE_FROM ? RawPrcDatabase.from(fs.readFileSync(env.PALM_REPLACE_FROM)) : undefined;
  const freshBackup=env.PALM_ALLOW_BACKED_UP_REPLACE==='1' && env.PALM_BACKUP==='1' && path.resolve(backupDir)===path.resolve(out);
  const overwrite=decideReplacement(existing,app,{expected,freshBackup});
  let previousName=null;
  if(existing.length) {
    const old=await readRawDb(dlp,existing[0].name);
    if(expected && !matches(old,expected)) throw new Error('Installed app differs from the verified previous build');
    if(freshBackup) {
      const index=dbs.findIndex(info=>info.name===existing[0].name);
      const filename=String(index).padStart(3,'0')+'-'+existing[0].name.replace(/[^a-zA-Z0-9_.-]/g,'_')+'.prc';
      const backedUp=RawPrcDatabase.from(fs.readFileSync(path.join(out,filename)));
      if(!matches(old,backedUp)) throw new Error('Installed app differs from this session’s fresh backup');
    }
    fs.writeFileSync(path.join(out,'previous-PalmAnimation.prc'),old.serialize());
    if(!overwrite) previousName=existing[0].name;
  }
  const card=storage?.cardInfo?.find(info=>info.cardNo===0);
  if(!card || !Number.isFinite(card.freeRam)) throw new Error('Could not determine the Palm’s free memory; no app was written');
  if(bytes.length+65536>card.freeRam) throw new Error('The Palm does not have enough free memory for this collection. Remove or shorten an animation');
  console.log('Installing '+app.header.name);
  await writeRawDb(dlp,app,{overwrite});
  console.log('App written; reading all resources back for verification');
  const verify=await readRawDb(dlp,app.header.name);
  if(!matches(verify,app)) throw new Error('Installed resource verification failed. The previous app is saved in the session backup');
  console.log('Installed app verified by reading back all resources');
  if(previousName) {await dlp.execute(DlpDeleteDBReqType.with({cardNo:0,name:previousName}));console.log('Previous app name removed: '+previousName);}
}
module.exports={installApp,matches,decideReplacement};
