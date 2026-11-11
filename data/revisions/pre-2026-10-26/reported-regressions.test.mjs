import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {cursorX} from '../public/score-utils.js';
const song=JSON.parse(await readFile(new URL('../public/songs/chi-le-ge/song.json',import.meta.url),'utf8'));
test('chi-le-ge bar 23 restores the triplet, dropped piano note and continuous bass',()=>{
 const bar=song.measures[22],notes=song.parts.find(p=>p.id==='piano').notes.filter(n=>n.measure===23),ppq=song.midi.ppq;
 for(const [pitch,quarter,length] of [[84,1,1/3],[86,4/3,1/3],[79,5/3,1/3],[77,2,.5],[76,2.5,1],[50,0,3.5]]){
  assert.ok(notes.some(n=>n.midi===pitch&&Math.abs((n.ticks-bar.ticks)/ppq-quarter)<1e-6&&Math.abs(n.durationTicks/ppq-length)<1e-6),`pitch ${pitch} follows the printed rhythm`);
 }
});
test('chi-le-ge bar 44 uses printed sextuplets rather than ordinary sixteenths',()=>{
 const bar=song.measures[43],notes=song.parts.find(p=>p.id==='piano').notes.filter(n=>n.measure===44),ppq=song.midi.ppq;
 for(const [pitch,quarter] of [[50,1/6],[53,1/3],[55,.5],[58,2/3],[62,5/6]])assert.ok(notes.some(n=>n.midi===pitch&&n.ticks===bar.ticks+Math.round(quarter*ppq)&&n.durationTicks===ppq/6));
});
test('ornaments borrow time before the main note without extending the bar',()=>{
 const part=song.parts.find(p=>p.id==='tenor'),bar=song.measures[22],grace=part.notes.find(n=>n.measure===23&&n.grace);
 assert.ok(grace);assert.equal(grace.midi,65);assert.equal(grace.ticks+grace.durationTicks,bar.ticks+song.midi.ppq*.75);
 assert.ok(part.notes.some(n=>n.measure===23&&n.midi===62&&n.durationTicks===song.midi.ppq*2.25));
 assert.ok(song.parts.some(p=>p.notes.some(n=>n.ornament)));
});
test('bar 44 cursor advances continuously with no frozen OMR-coordinate plateaus',()=>{
 const bar=song.measures[43];let last=cursorX(bar,bar.time),maxStep=0;
 for(let t=1/120;t<bar.duration;t+=1/120){const x=cursorX(bar,bar.time+t);assert.ok(x>last,'cursor must keep moving');maxStep=Math.max(maxStep,x-last);last=x;}
 assert.ok(maxStep<8,'no abrupt cursor jump at 120 Hz');
});
