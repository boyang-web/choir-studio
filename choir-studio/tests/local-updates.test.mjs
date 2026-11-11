import test from 'node:test';
import assert from 'node:assert/strict';
import {mkdtemp,mkdir,readFile,writeFile,rm} from 'node:fs/promises';
import {tmpdir} from 'node:os';
import path from 'node:path';
import {verify,generateKeyPairSync} from 'node:crypto';
import {JSDOM} from 'jsdom';
import {ensureUpdateKey,createUpdateSnapshot,hash} from '../local-update-server.mjs';
import {installLocalUpdates} from '../public/local-updates.js';

test('signed LAN manifest pins a persistent computer key and immutable hashed files',async()=>{
 const dir=await mkdtemp(path.join(tmpdir(),'choir-update-'));
 try{
  await mkdir(path.join(dir,'public/songs'),{recursive:true});
  await writeFile(path.join(dir,'package.json'),JSON.stringify({version:'test'}));
  await writeFile(path.join(dir,'public/index.html'),'original');
  await writeFile(path.join(dir,'public/songs/catalog.json'),'[]');
  const key=await ensureUpdateKey(dir);assert.equal(await ensureUpdateKey(dir),key);
  const pub=await readFile(path.join(dir,'android/app/src/main/assets/update-public-key.pem'),'utf8');
  const snapshot=await createUpdateSnapshot(dir,key),{envelope,blobs}=snapshot;
  const payload=Buffer.from(envelope.payload,'base64'),signature=Buffer.from(envelope.signature,'base64');
  assert.ok(verify('RSA-SHA256',payload,pub,signature));
  assert.equal(verify('RSA-SHA256',Buffer.from('tampered'),pub,signature),false);
  const wrong=generateKeyPairSync('rsa',{modulusLength:2048}).publicKey;
  assert.equal(verify('RSA-SHA256',payload,wrong,signature),false);
  const manifest=JSON.parse(payload);assert.equal(manifest.protocol,1);
  for(const f of manifest.files){assert.equal(hash(blobs.get(f.sha256)),f.sha256);assert.equal(blobs.get(f.sha256).length,f.size);}
  await writeFile(path.join(dir,'public/index.html'),'corrected');
  assert.equal(blobs.get(hash(Buffer.from('original'))).toString(),'original','already offered file stays immutable');
  const updated=await createUpdateSnapshot(dir,key);
  assert.notEqual(JSON.parse(Buffer.from(updated.envelope.payload,'base64')).revision,manifest.revision,'content changes trigger updates without a package version bump');
 }finally{await rm(dir,{recursive:true,force:true});}
});

const html=await readFile(new URL('../public/index.html',import.meta.url),'utf8');
async function fixture(handler){
 const dom=new JSDOM(html),calls=[];
 const cap={isNativePlatform:()=>true,getPlatform:()=> 'android',nativePromise:async(plugin,method,args)=>{
  calls.push({plugin,method,args});
  if(method==='status')return {version:'1.6.0',revision:'abcdef0123456789',source:'http://192.168.1.2:5173',downloaded:false};
  return handler(method,args);
 }};
 let paused=0;installLocalUpdates({document:dom.window.document,capacitor:cap,beforeSwitch:()=>paused++});
 await new Promise(r=>setImmediate(r));
 return {dom,calls,get paused(){return paused;},el:id=>dom.window.document.getElementById(id)};
}
test('native update UI checks explicitly, installs the verified ticket and pauses playback',async()=>{
 const f=await fixture((method)=>method==='check'?{available:true,ticket:'verified-ticket',version:'1.6.1',revision:'1234567890',bytes:1024}:{});
 try{
  assert.equal(f.el('local-updates').hidden,false);
  assert.equal(f.calls.some(c=>c.method==='check'),false,'no unsolicited network checks');
  f.dom.window.document.dispatchEvent(new f.dom.window.Event('choir-ready'));
  await f.el('update-check').onclick();assert.equal(f.el('update-apply').hidden,false);
  await f.el('update-apply').onclick();
  assert.deepEqual(f.calls.find(c=>c.method==='install').args,{ticket:'verified-ticket'});
  assert.equal(f.paused,1);assert.ok(f.calls.some(c=>c.method==='ready'));
 }finally{f.dom.window.close();}
});
test('download failure clears the stale candidate and permits retry while retaining offline content',async()=>{
 const f=await fixture(method=>{if(method==='check')return {available:true,ticket:'x',version:'x',revision:'abcd',bytes:100};throw new Error('连接中断');});
 try{
  await f.el('update-check').onclick();await f.el('update-apply').onclick();
  assert.match(f.el('update-status').textContent,/连接中断.*离线/);
  assert.equal(f.el('update-check').disabled,false);assert.equal(f.el('update-apply').hidden,true);
  await f.el('update-check').onclick();f.el('update-source').dispatchEvent(new f.dom.window.Event('input'));
  assert.equal(f.el('update-apply').hidden,true,'changing the source invalidates the offered update');
 }finally{f.dom.window.close();}
});
test('web UI hides native-only updates and current content needs no download',async()=>{
 const dom=new JSDOM(html);
 installLocalUpdates({document:dom.window.document,capacitor:undefined});
 assert.equal(dom.window.document.getElementById('local-updates').hidden,true);dom.window.close();
 const f=await fixture(()=>({available:false}));
 try{await f.el('update-check').onclick();assert.match(f.el('update-status').textContent,/最新/);assert.equal(f.el('update-apply').hidden,true);}
 finally{f.dom.window.close();}
});

test('offline sharing shows phone addresses and blocks local replacement until sharing stops',async()=>{
 const dom=new JSDOM(html);let sharing=false;const calls=[];
 const status=()=>({canShare:true,sharing,shareAddresses:sharing?['http://192.168.43.1:5174']:[],shareError:'',version:'1.7.0',revision:'abcdef',source:''});
 const cap={isNativePlatform:()=>true,getPlatform:()=> 'android',nativePromise:async(plugin,method)=>{
  calls.push(method);if(method==='startShare')sharing=true;if(method==='stopShare')sharing=false;return status();
 }};
 installLocalUpdates({document:dom.window.document,capacitor:cap});
 const el=id=>dom.window.document.getElementById(id);
 try{
  await new Promise(r=>setImmediate(r));assert.equal(el('offline-share').hidden,false);
  assert.equal(calls.includes('startShare'),false);
  await el('share-start').onclick();
  assert.match(el('share-addresses').textContent,/192\.168\.43\.1:5174/);
  assert.equal(el('update-check').disabled,true);assert.equal(el('update-restore').disabled,true);
  assert.equal(el('share-stop').hidden,false);
  await el('share-stop').onclick();assert.equal(el('update-check').disabled,false);assert.equal(el('share-addresses').textContent,'');
 }finally{dom.window.dispatchEvent(new dom.window.Event('pagehide'));dom.window.close();}
});
