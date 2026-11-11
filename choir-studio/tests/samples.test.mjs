import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,stat} from 'node:fs/promises';
const root=new URL('../public/samples/',import.meta.url);
test('three offline sample banks exist; choir recordings have valid sustain loops',async()=>{
 const manifest=JSON.parse(await readFile(new URL('manifest.json',root),'utf8'));
 for(const name of ['male','female','piano']){
  const entries=Object.entries(manifest[name].samples);assert.ok(entries.length>=5);
  for(const [,sample]of entries){assert.ok((await stat(new URL(sample.file,root))).size>10000);if(name!=='piano'){assert.ok(sample.loopStart>0);assert.ok(sample.loopEnd>sample.loopStart);assert.ok(sample.loopEnd<sample.duration);}}
 }
 const male=await readFile(new URL(manifest.male.samples.C4.file,root));const female=await readFile(new URL(manifest.female.samples.C5.file,root));assert.notDeepEqual(male,female);
});
