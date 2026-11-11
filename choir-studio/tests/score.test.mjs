import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,stat} from 'node:fs/promises';
import {measureAt,loopRange,cursorX,formatTime} from '../public/score-utils.js';
const root=new URL('../public/songs/',import.meta.url);
for(const id of ['chi-le-ge','let-it-go']){
 const song=JSON.parse(await readFile(new URL(`${id}/song.json`,root),'utf8'));
 test(`${id}: full score, continuous common timeline and every part populated`,async()=>{
  assert.equal(song.pages.length,id==='chi-le-ge'?10:19);
  assert.equal(song.measures.length,id==='chi-le-ge'?69:119);
  assert.equal(song.parts.length,6);
  let end=0;
  for(const [index,m]of song.measures.entries()){
   assert.equal(m.index,index);assert.ok(Math.abs(m.time-end)<.0001);end=m.time+m.duration;
   const sys=song.systems[m.system],page=song.pages[m.page];
   assert.equal(sys.page,m.page);assert.ok(m.left>=sys.x&&m.right<=sys.x+sys.width+2);assert.ok(sys.y+sys.height<=page.height);
   let last=-Infinity;for(const p of m.positions){assert.ok(p.time>=0&&p.time<m.duration+.001);assert.ok(p.x>=m.left&&p.x<=m.right+2);assert.ok(p.x>=last);last=p.x;}
   assert.equal(measureAt(song.measures,m.time+.0001).index,index);
   assert.ok(Number.isFinite(cursorX(m,m.time+m.duration*.5)));
  }
  assert.ok(Math.abs(end-song.duration)<.0001);
  for(const part of song.parts){assert.ok(part.notes.length>50);let previous=-1;for(const n of part.notes){assert.ok(n.time>=previous);assert.ok(n.duration>0);assert.ok(n.midi>=0&&n.midi<=127);assert.ok(n.time+n.duration<song.duration+.001);previous=n.time;}}
  for(const page of song.pages)assert.ok((await stat(new URL(`${id}/${page.image}`,root))).size>100);
  for(const sys of song.systems)assert.ok((await stat(new URL(`${id}/${sys.image}`,root))).size>100);
  assert.ok((await stat(new URL(`${id}/score.pdf`,root))).size>1000);
 });
 test(`${id}: loop bounds and score position follow one timeline`,()=>{
  const range=loopRange(song,'-5','999');assert.equal(range.a,1);assert.equal(range.b,song.measures.length);assert.ok(Math.abs(range.end-song.duration)<.0001);
  const reverse=loopRange(song,6,2);assert.equal(reverse.a,6);assert.equal(reverse.b,6);
  assert.equal(measureAt(song.measures,song.duration).index,song.measures.length-1);
 });
}
test('readable time formatting',()=>{assert.equal(formatTime(201.13),'3:21');assert.equal(formatTime(-1),'0:00');});
