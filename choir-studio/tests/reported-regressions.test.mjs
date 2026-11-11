import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import {cursorX} from '../public/score-utils.js';
const base=new URL('../public/songs/chi-le-ge/',import.meta.url);
const song=JSON.parse(await readFile(new URL('song.json',base),'utf8'));
const piano=song.parts.find(p=>p.id==='piano');
test('revised score uses the supplied ten-page PDF and its printed bar grid',async()=>{
 const pdf=await readFile(new URL('score.pdf',base));
 assert.equal(createHash('sha256').update(pdf).digest('hex'),'0c0f98ad55706e8d6c244d58991093861c8f8ea556985e5058bae43b2c5311b4');
 assert.equal(song.pages.length,10);assert.equal(song.measures.length,69);
 assert.equal(song.measures[0].quarterLength,4);
 assert.deepEqual(song.measures.filter(m=>m.quarterLength===6).map(m=>m.label),[55,67]);
 assert.deepEqual(song.import.rhythmWarnings,[]);
});
test('bar 42 follows two printed nonuplets and eight ordinary thirty-seconds',()=>{
 const bar=song.measures[41],ppq=song.midi.ppq;
 const run=piano.notes.filter(n=>n.measure===42&&n.ticks>=bar.ticks+ppq);
 assert.equal(run.length,26);
 for(let i=0;i<18;i++){
  assert.equal(run[i].ticks,bar.ticks+ppq+Math.round(i*ppq/9));
  assert.equal(run[i].durationTicks,ppq/9);
 }
 assert.ok(run.some(n=>n.midi===98),'high D7 retained from PDF');
 for(const n of run.slice(18))assert.equal(n.durationTicks,ppq/8);
});
test('bar 44 cross-staff sextuplets fill the bar without spilling into bar 45',()=>{
 const bar=song.measures[43],ppq=song.midi.ppq;
 const run=piano.notes.filter(n=>n.measure===44&&n.durationTicks===ppq/6);
 assert.equal(run.length,22);
 assert.ok(run.some(n=>n.midi===50&&n.ticks===bar.ticks+ppq/6));
 for(const n of piano.notes.filter(n=>n.measure===44))assert.ok(n.ticks+n.durationTicks<=bar.ticks+bar.durationTicks);
});
test('revised grace notes borrow time and every event starts in its bar and tied notes stay within the score',()=>{
 assert.ok(song.parts.some(p=>p.notes.some(n=>n.grace)));
 for(const part of song.parts)for(const n of part.notes){
  const bar=song.measures[n.measure-1];
  assert.ok(n.ticks>=bar.ticks);assert.ok(n.ticks+n.durationTicks<=song.measures.at(-1).ticks+song.measures.at(-1).durationTicks+1);
 }
});
test('bar 44 cursor advances smoothly across the revised vector page',()=>{
 const bar=song.measures[43];let last=cursorX(bar,bar.time),maxStep=0;
 for(let t=1/120;t<bar.duration;t+=1/120){const x=cursorX(bar,bar.time+t);assert.ok(x>last);maxStep=Math.max(maxStep,x-last);last=x;}
 assert.ok(maxStep<8);
});
