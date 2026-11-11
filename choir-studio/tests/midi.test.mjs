import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import {readPerformance} from '../public/midi-performance.js';
const scope={};vm.runInNewContext(await readFile(new URL('../public/vendor/midi.js',import.meta.url),'utf8'),scope);
for(const id of ['chi-le-ge','let-it-go'])test(`${id}: every voice follows the standard MIDI tempo/tick timeline`,async()=>{
 const base=new URL(`../public/songs/${id}/`,import.meta.url),song=JSON.parse(await readFile(new URL('song.json',base),'utf8')),bytes=await readFile(new URL('performance.mid',base));
 assert.equal(bytes.subarray(0,4).toString(),'MThd');const midi=new scope.Midi(bytes);readPerformance(song,bytes,scope.Midi);
 for(const part of song.parts)for(const note of part.notes){assert.ok(note.durationTicks>0);assert.ok(Math.abs(note.time-midi.header.ticksToSeconds(note.ticks))<1e-8);assert.ok(Math.abs(note.duration-(midi.header.ticksToSeconds(note.ticks+note.durationTicks)-note.time))<1e-8);}
 if(id==='let-it-go'){
  const bar=song.measures[75],events=song.parts.find(p=>p.id==='percussion').notes.filter(n=>n.measure===76);
  assert.deepEqual([...new Set(events.map(n=>(n.ticks-bar.ticks)/song.midi.ppq))],[0,1,2,2.5,3,3.5],'bar 76 follows two quarters and four eighths');
 }
});
