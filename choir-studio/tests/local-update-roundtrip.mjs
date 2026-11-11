// Run with the computer server already listening: node tests/local-update-roundtrip.mjs
import {readFile,writeFile,mkdir} from 'node:fs/promises';
import {createPublicKey,verify} from 'node:crypto';
const base=process.env.UPDATE_TEST_URL||'http://127.0.0.1:5173/';
const response=await fetch(new URL('local-update/manifest',base));
if(!response.ok)throw new Error(`Manifest HTTP ${response.status}`);
const envelope=await response.json(),payload=Buffer.from(envelope.payload,'base64'),sig=Buffer.from(envelope.signature,'base64');
const pub=await readFile(new URL('../android/app/src/main/assets/update-public-key.pem',import.meta.url));
if(!verify('RSA-SHA256',payload,pub,sig))throw new Error('Computer/APK signing keys differ');
const manifest=JSON.parse(payload),dir=new URL('../test-results/update-roundtrip/',import.meta.url);
await mkdir(dir,{recursive:true});
await writeFile(new URL('envelope.json',dir),JSON.stringify(envelope));
await writeFile(new URL('payload',dir),payload);await writeFile(new URL('signature',dir),sig);
await writeFile(new URL('key.der',dir),createPublicKey(pub).export({type:'spki',format:'der'}));
await writeFile(new URL('files.tsv',dir),manifest.files.map(f=>`${f.path}\t${f.size}\t${f.sha256}`).join('\n'));
await writeFile(new URL('server.txt',dir),base);
console.log(`Signed HTTP manifest verified: ${manifest.files.length} files; Java roundtrip fixture ready.`);
