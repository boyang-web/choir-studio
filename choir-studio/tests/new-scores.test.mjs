import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile,stat} from 'node:fs/promises';
import {createHash} from 'node:crypto';
import vm from 'node:vm';
import {readPerformance} from '../public/midi-performance.js';
import {measureAt,cursorX} from '../public/score-utils.js';

const definitions=JSON.parse(await readFile(new URL('../../tools/new-scores.json',import.meta.url),'utf8'));
const catalog=JSON.parse(await readFile(new URL('../public/songs/catalog.json',import.meta.url),'utf8'));
const scope={};vm.runInNewContext(await readFile(new URL('../public/vendor/midi.js',import.meta.url),'utf8'),scope);
const pageCounts=[6,10,9,6,12];
for(const [index,definition] of definitions.entries())test(`${definition.id}: ${definition.id==='wei-yao-xun-yi-ge-ming-xing'?'ambiguous staff layout stays out of the playable catalog':'source PDF, vocal tracks and standard MIDI load together'}`,async()=>{
 if(definition.id==='wei-yao-xun-yi-ge-ming-xing'){
  const audit=JSON.parse(await readFile(new URL(`../../inspection/new-imports/${definition.id}-audit.json`,import.meta.url),'utf8'));
  assert.equal(audit.status,'failed');assert.match(audit.reason,/staff layout/i);
  assert.equal(catalog.some(song=>song.id===definition.id),false,'ambiguous staff assignments must not enter the playable catalog');
  assert.ok((await stat(new URL('../../data/sources/'+definition.source,import.meta.url))).size>1000);
  return;
 }
 const base=new URL(`../public/songs/${definition.id}/`,import.meta.url);
 const song=JSON.parse(await readFile(new URL('song.json',base),'utf8'));
 assert.equal(catalog.filter(s=>s.id===song.id).length,1);
 assert.equal(song.title,definition.title);assert.equal(song.pages.length,pageCounts[index]);
 assert.equal(song.parts.find(p=>p.id==='alto').name,'女中音');
 assert.equal(song.parts.some(p=>p.id==='piano'),definition.id!=='ye-lai-xiang');
 assert.equal(song.import.status,'machine-transcribed-needs-proofreading');
 assert.ok(Array.isArray(song.import.rhythmWarnings));
 const hash=bytes=>createHash('sha256').update(bytes).digest('hex');
 assert.equal(hash(await readFile(new URL('score.pdf',base))),hash(await readFile(new URL('../../data/sources/'+definition.source,import.meta.url))));
 readPerformance(song,await readFile(new URL('performance.mid',base)),scope.Midi);
 assert.ok(song.measures.length>20);assert.ok(song.duration>60);
 let end=0;
 for(const [i,measure] of song.measures.entries()){
  assert.equal(measure.index,i);assert.ok(Math.abs(measure.time-end)<1e-7);end=measure.time+measure.duration;
  assert.ok(measure.duration>0);assert.equal(song.systems[measure.system].page,measure.page);
  assert.ok(measure.page>=Number(definition.skipPages||0)&&measure.page<song.pages.length);
  assert.equal(measureAt(song.measures,measure.time+1e-6).index,i);
  assert.ok(Number.isFinite(cursorX(measure,measure.time+measure.duration/2)));
  let lastTick=-1,lastX=-Infinity;
  for(const point of measure.positions){assert.ok(point.ticks>lastTick);assert.ok(point.x>=lastX);assert.ok(point.ticks>=0&&point.ticks<measure.durationTicks);lastTick=point.ticks;lastX=point.x;}
 }
 assert.ok(Math.abs(end-song.duration)<1e-7);
 for(const role of ['soprano','alto','tenor','bass'])assert.ok(song.parts.find(p=>p.id===role)?.notes.length>20);
 for(const part of song.parts)for(const note of part.notes){assert.ok(Number.isFinite(note.time));assert.ok(note.duration>0);assert.ok(Number.isInteger(note.midi)&&note.midi>=0&&note.midi<=127);}
 for(const page of song.pages){assert.ok((await stat(new URL(page.image,base))).size>100);assert.ok((await stat(new URL(page.svg,base))).size>100);}
});
