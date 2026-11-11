import {fileURLToPath} from 'node:url';
import {writeFile} from 'node:fs/promises';
import {ensureUpdateKey,createUpdateSnapshot} from '../local-update-server.mjs';
const project=fileURLToPath(new URL('../',import.meta.url));
const key=await ensureUpdateKey(project),snapshot=await createUpdateSnapshot(project,key);
const {revision,version}=JSON.parse(Buffer.from(snapshot.envelope.payload,'base64'));
await writeFile(new URL('../android/app/src/main/assets/update-builtin.json',import.meta.url),JSON.stringify({revision,version}));
await writeFile(new URL('../android/app/src/main/assets/update-builtin-envelope.json',import.meta.url),JSON.stringify(snapshot.envelope));
console.log('Local update signing key ready; preserve .update-keys/private.pem on this computer.');
