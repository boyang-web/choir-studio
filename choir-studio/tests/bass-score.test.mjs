import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import vm from 'node:vm';
import {readPerformance} from '../public/midi-performance.js';

test('Chi Le Ge bass bars 26, 29 and 67 match the printed pitches, rests and beats',async()=>{
 const base=new URL('../public/songs/chi-le-ge/',import.meta.url);
 const song=JSON.parse(await readFile(new URL('song.json',base),'utf8'));
 const scope={};vm.runInNewContext(await readFile(new URL('../public/vendor/midi.js',import.meta.url),'utf8'),scope);
 const check=()=>{
  const bass=song.parts.find(p=>p.id==='bass'),ppq=song.midi.ppq;
  for(const [number,expected] of [
   [26,[[46,0,4]]],
   [29,[[48,.5,.5],[55,1,.5],[53,1.5,.5],[57,2,1],[55,3,.5]]],
   [67,[[55,1,.5],[57,1.5,.5],[48,2,3]]],
  ]){
   const bar=song.measures[number-1];
   const actual=bass.notes.filter(n=>n.ticks>=bar.ticks&&n.ticks<bar.ticks+bar.durationTicks)
    .map(n=>[n.midi,(n.ticks-bar.ticks)/ppq,n.durationTicks/ppq]);
   assert.deepEqual(actual,expected,`bass bar ${number}`);
  }
 };
 check();
 readPerformance(song,await readFile(new URL('performance.mid',base)),scope.Midi);
 check();
});
