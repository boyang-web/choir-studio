import {createHash,createPublicKey,generateKeyPairSync,sign} from 'node:crypto';
import {mkdir,readFile,readdir,writeFile} from 'node:fs/promises';
import path from 'node:path';

export const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
export async function ensureUpdateKey(project){
 const dir=path.join(project,'.update-keys');
 await mkdir(dir,{recursive:true});
 const privateFile=path.join(dir,'private.pem');
 let key;
 try{key=await readFile(privateFile,'utf8');}
 catch(error){
  if(error.code!=='ENOENT')throw error;
  const pair=generateKeyPairSync('rsa',{modulusLength:3072,privateKeyEncoding:{type:'pkcs8',format:'pem'},publicKeyEncoding:{type:'spki',format:'pem'}});
  await writeFile(privateFile,pair.privateKey,{flag:'wx',mode:0o600});key=pair.privateKey;
 }
 const publicKey=createPublicKey(key).export({type:'spki',format:'pem'});
 // This key is pinned in the APK, outside the downloadable web directory.
 const assets=path.join(project,'android/app/src/main/assets');
 await mkdir(assets,{recursive:true});
 await writeFile(path.join(assets,'update-public-key.pem'),publicKey);
 return key;
}

export async function createUpdateSnapshot(project,key){
 const root=path.join(project,'public'),files=[],blobs=new Map();
 async function walk(dir){
  for(const item of (await readdir(dir,{withFileTypes:true})).sort((a,b)=>a.name.localeCompare(b.name))){
   if(item.name==='designs'||item.name.startsWith('.'))continue;
   const full=path.join(dir,item.name);
   if(item.isDirectory())await walk(full);
   else if(item.isFile()){
    const bytes=await readFile(full),sha256=hash(bytes);
    files.push({path:path.relative(root,full).split(path.sep).join('/'),size:bytes.length,sha256});
    blobs.set(sha256,bytes);
   }
  }
 }
 await walk(root);
 const {version}=JSON.parse(await readFile(path.join(project,'package.json'),'utf8'));
 const revision=hash(JSON.stringify(files));
 const payload=Buffer.from(JSON.stringify({protocol:1,minNative:1,version,revision,files}));
 return {envelope:{payload:payload.toString('base64'),signature:sign('RSA-SHA256',payload,key).toString('base64')},blobs};
}
