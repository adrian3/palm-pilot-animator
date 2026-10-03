const assert=require('node:assert/strict');
const {decideReplacement,matches}=require('./install-app.cjs');
const app={header:{name:"Ade's App",creator:'PAnm',type:'appl'}};
const existing=[{...app.header}];
assert.equal(decideReplacement([],app),false);
assert.throws(()=>decideReplacement(existing,app),/backup/);
assert.equal(decideReplacement(existing,app,{freshBackup:true}),true);
assert.equal(decideReplacement([{...existing[0],name:'Palm Animation'}],app,{freshBackup:true}),false);
assert.throws(()=>decideReplacement([{...existing[0],creator:'Else'}],app,{freshBackup:true}),/collision/);
assert.throws(()=>decideReplacement([{...existing[0],name:'Other app'}],app,{freshBackup:true}),/collision/);
assert.throws(()=>decideReplacement([...existing,...existing],app,{freshBackup:true}),/collision/);
assert.throws(()=>decideReplacement(existing,app,{expected:{header:{name:'Palm Animation',creator:'PAnm'}}}),/mismatch/);
const record={entry:{type:'Tbmp',resourceId:1000},data:Buffer.from([1,2,3])};
assert(matches({records:[record]},{records:[record]}));
assert(!matches({records:[record]},{records:[{...record,data:Buffer.from([1,2,4])}]}));
console.log('PASS: replacement requires checked identity and backup; resource changes are detected.');

const {installApp}=require('./install-app.cjs');
const fs=require('fs'),os=require('os'),path=require('path');
const dir=fs.mkdtempSync(path.join(os.tmpdir(),'palm-install-test-'));
class FakeDb {
  constructor(header, records){this.header=header;this.records=records;}
  serialize(){return Buffer.from(JSON.stringify({header:this.header,records:this.records.map(r=>({entry:r.entry,data:[...r.data]}))}));}
  static from(data){const d=JSON.parse(data);return new FakeDb(d.header,d.records.map(r=>({...r,data:Buffer.from(r.data)})));}
}
async function integration(){
  const old=new FakeDb(app.header,[record]);
  const next=new FakeDb(app.header,[{...record,data:Buffer.from([4,5,6])}]);
  fs.writeFileSync(path.join(dir,'BACKUP_COMPLETE'),'complete');
  fs.writeFileSync(path.join(dir,'000-Ade_s_App.prc'),old.serialize());
  fs.writeFileSync(path.join(dir,'new.prc'),next.serialize());
  const env={PALM_INSTALL:path.join(dir,'new.prc'),PALM_BACKUP_DIR:dir,PALM_BACKUP:'1',PALM_ALLOW_BACKED_UP_REPLACE:'1'};
  let installed=old,writes=0,corrupt=false;
  const deps={RawPrcDatabase:FakeDb,DlpDeleteDBReqType:{with:x=>x},readRawDb:async()=>installed,writeRawDb:async(dlp,db,opts)=>{assert.equal(opts.overwrite,true);writes++;installed=corrupt?old:db;}};
  const context={dbs:existing,storage:{cardInfo:[{cardNo:0,freeRam:8388608}]},out:dir};
  await installApp({},context,env,deps);
  assert.equal(writes,1);assert(matches(FakeDb.from(fs.readFileSync(path.join(dir,'previous-PalmAnimation.prc'))),old));
  installed=old;writes=0;
  await assert.rejects(installApp({}, {...context,storage:{cardInfo:[{cardNo:0,freeRam:0}]}},env,deps),/free memory/);
  assert.equal(writes,0);
  fs.writeFileSync(path.join(dir,'000-Ade_s_App.prc'),next.serialize());
  await assert.rejects(installApp({},context,env,deps),/fresh backup/);assert.equal(writes,0);
  fs.writeFileSync(path.join(dir,'000-Ade_s_App.prc'),old.serialize());
  corrupt=true;
  await assert.rejects(installApp({},context,env,deps),/verification failed/);
  console.log('PASS: fresh backup equality, free-memory rejection, retained previous app, and read-back verification.');
}
integration().catch(e=>{console.error(e);process.exitCode=1;}).finally(()=>fs.rmSync(dir,{recursive:true,force:true}));
