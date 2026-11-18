import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import vm from 'node:vm';
import {readPerformance} from '../public/midi-performance.js';

const base=new URL('../public/songs/hui-sheng/',import.meta.url);
const song=JSON.parse(await readFile(new URL('song.json',base),'utf8'));
const ledger=JSON.parse(await readFile(new URL('../../data/verified/hui-sheng.json',import.meta.url),'utf8'));
const ppq=song.midi.ppq;
const hash=bytes=>createHash('sha256').update(bytes).digest('hex');

test('Hui Sheng: exact source PDF, eight independent voices and 304 complete voice-measures',async()=>{
 assert.equal(hash(await readFile(new URL('score.pdf',base))),ledger.sourceSha256);
 assert.equal(hash(await readFile(new URL('../../data/sources/3.回声.pdf',import.meta.url))),ledger.sourceSha256);
 assert.equal(song.parts.length,8);assert.equal(song.pages.length,3);
 assert.equal(song.measures.length,38);assert.equal(song.duration,76);assert.equal(song.tempo,120);
 assert.equal(new Set(song.parts.map(p=>p.id)).size,8);
 for(const part of ledger.parts){
  assert.equal(part.measures.length,38);
  for(const bar of part.measures){
   let end=0;
   for(const event of bar.events){assert.equal(event.offset,end);end+=event.duration;}
   assert.equal(end,4,`${part.id} bar ${bar.number}`);
  }
 }
 for(const part of song.parts)assert.equal(part.sound,['soprano','alto'].includes(part.role)?'female':'male');
});

test('Hui Sheng: every echoed note preserves pitch and duration exactly two beats later',()=>{
 for(let i=0;i<4;i++){
  const leader=song.parts[i],echo=song.parts[i+4];assert.equal(leader.notes.length,echo.notes.length);
  leader.notes.forEach((note,index)=>{
   const answer=echo.notes[index];assert.equal(answer.midi,note.midi);
   assert.equal(answer.durationTicks,note.durationTicks);assert.equal(answer.ticks-note.ticks,2*ppq);
  });
 }
});

test('Hui Sheng: independent rhythms, chromatic notes, sixteenths and tied endings match the source',()=>{
 const voice=id=>song.parts.find(p=>p.id===id).notes;
 const events=(id,bar)=>voice(id).filter(n=>n.measure===bar).map(n=>[n.midi,(n.ticks-(bar-1)*4*ppq)/ppq,n.durationTicks/ppq]);
 assert.deepEqual(events('soprano-1',8),[[69,0,1.5],[71,1.5,.5],[73,2,1],[69,3,1]]);
 assert.deepEqual(events('alto-1',8),[[64,0,1],[66,1,1],[69,2,1],[66,3,1]]);
 assert.deepEqual(events('tenor-1',18).slice(-2),[[64,3,.5],[67,3.5,.5]]);
 assert.deepEqual(events('bass-1',18).at(-1),[52,3,1]);
 assert.deepEqual(events('soprano-1',20).slice(-2),[[71,3.5,.25],[71,3.75,.25]]);
 assert.deepEqual(events('alto-1',21).map(n=>n[0]),[64,64,63,64]);
 for(const id of ['soprano-1','alto-1','tenor-1','bass-1']){
  assert.equal(events(id,33).at(-1)[2],1,'tie across bars 33 and 34 must sustain');
  assert.equal(events(id,36).at(-1)[2],4,'tie across bars 36 and 37 must sustain');
  assert.equal(events(id,37).length,1,'second syllable rearticulates after the tie');
 }
});

test('Hui Sheng: exported standard MIDI round-trips every event and the common score timeline',async()=>{
 const scope={};vm.runInNewContext(await readFile(new URL('../public/vendor/midi.js',import.meta.url),'utf8'),scope);
 const loaded=readPerformance(structuredClone(song),await readFile(new URL('performance.mid',base)),scope.Midi);
 assert.equal(loaded.duration,76);
 loaded.parts.forEach((part,i)=>part.notes.forEach((note,j)=>{
  assert.equal(note.time,song.parts[i].notes[j].time);
  assert.equal(note.duration,song.parts[i].notes[j].duration);
  assert.ok(note.time>=0&&note.time+note.duration<=76);
 }));
});
