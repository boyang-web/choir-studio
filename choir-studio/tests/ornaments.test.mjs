import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
const song=JSON.parse(await readFile(new URL('../public/songs/chi-le-ge/song.json',import.meta.url),'utf8'));
const byId=id=>song.parts.find(p=>p.id===id);

test('all 52 printed grace heads in the ten-page score are performed',()=>{
 const expected={soprano:18,alto:3,tenor:11,bass:7,ocarina:10,piano:3};
 for(const [id,count] of Object.entries(expected)){
  const grace=byId(id).notes.filter(n=>n.grace);
  assert.equal(grace.length,count,`${id}: complete PDF grace heads`);
  for(const note of grace)assert.ok(note.durationTicks>0&&note.durationTicks<=song.midi.ppq/8);
 }
 for(const id of ['soprano','tenor','bass','ocarina']){
  const groups={soprano:[13,29,45,53,62,65],tenor:[19,21,29,45],bass:[19,21],ocarina:[35,37,63]};
  for(const bar of groups[id])assert.ok(byId(id).notes.filter(n=>n.measure===bar&&n.grace).length>=2);
 }
});

test('all 15 printed mordents are encoded as main-upper-main sequences',()=>{
 const expected={soprano:[[9,65],[27,72],[30,77],[32,67],[33,65],[43,72],[46,77],[48,67],[49,65]],alto:[[9,65],[11,60],[51,60]],ocarina:[[38,86],[42,86],[45,84]]};
 let total=0;
 for(const [id,marks] of Object.entries(expected))for(const [bar,pitch] of marks){
  const notes=byId(id).notes.filter(n=>n.measure===bar&&n.ornament);
  assert.deepEqual(notes.map(n=>n.midi),[pitch,pitch+2,pitch],`${id} bar ${bar}`);
  assert.equal(notes[0].ticks+notes[0].durationTicks,notes[1].ticks);
  assert.equal(notes[1].ticks+notes[1].durationTicks,notes[2].ticks);
  total+=notes.length;
 }
 assert.equal(total,45);
 assert.equal(song.parts.flatMap(p=>p.notes).filter(n=>n.ornament).length,45,'false OMR trill/mordent guesses are not played');
});

test('ornaments preserve the held lower divisi note and common bar grid',()=>{
 for(const bar of [30,46]){
  const notes=byId('soprano').notes.filter(n=>n.measure===bar);
  assert.ok(notes.some(n=>n.midi===74&&!n.ornament&&n.durationTicks===2*song.midi.ppq));
 }
 assert.equal(song.measures.length,69);
 assert.deepEqual(song.import.rhythmWarnings,[]);
 for(const n of song.parts.flatMap(p=>p.notes))assert.ok(n.time+n.duration<=song.duration+.00001);
});
