import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
test('VP recovery retains ordinary voiced heads as well as crossed percussion heads',async()=>{
 const song=JSON.parse(await readFile(new URL('../public/songs/let-it-go/song.json',import.meta.url),'utf8'));
 const notes=song.parts.find(p=>p.id==='percussion').notes;
 assert.ok(notes.filter(n=>n.head==='cross').length>150);
 assert.ok(notes.filter(n=>n.head==='ordinary').length>100,'voiced percussion heads must not disappear');
 assert.ok(notes.filter(n=>n.time>=125&&n.kind==='vocal').length>80,'retain voiced percussion in the rear section');
 assert.ok(notes.some(n=>n.kind==='vocal'&&/doo|doh|koo/i.test(n.syllable)));
 assert.equal(new Set(notes.map(n=>`${n.ticks}:${n.kind}`)).size,notes.length,'deduplicate only identical percussion layers');
 assert.ok(new Set(notes.map(n=>n.ticks)).size<notes.length,'different percussion layers must sound together');
 assert.ok(notes.some(n=>n.head==='wind'&&n.durationTicks/song.midi.ppq===12),'retain the ending three-bar wind gesture');
});
