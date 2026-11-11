/** Standard MIDI supplies the tempo map and note onsets for every instrument. */
export function readPerformance(song,bytes,Parser=globalThis.Midi){
 if(!Parser)throw new Error('MIDI reader unavailable');
 const midi=new Parser(bytes),ppq=midi.header.ppq;
 if(ppq!==song.midi.ppq)throw new Error('MIDI resolution mismatch');
 const pending=new Map(song.parts.map(part=>[part.id,new Map()]));
 for(const part of song.parts)for(const note of part.notes){
  const key=`${note.branch||'shared'}:${note.ticks}:${note.midi}`;
  const list=pending.get(part.id).get(key)||[];list.push(note);pending.get(part.id).set(key,list);
 }
 const counts=new Map();
 for(const track of midi.tracks){
  const [id,branch]=track.name.split(':');if(!pending.has(id))continue;
  for(const note of track.notes){
   const source=pending.get(id).get(`${branch}:${note.ticks}:${note.midi}`)?.shift();if(!source)throw new Error('MIDI note metadata mismatch');
   source.time=midi.header.ticksToSeconds(note.ticks);
   // Explicit MIDI gate pairing preserves independent overlapping unisons.
   source.duration=midi.header.ticksToSeconds(note.ticks+source.durationTicks)-source.time;
   source.velocity=note.velocity;counts.set(id,(counts.get(id)||0)+1);
  }
 }
 for(const part of song.parts){
  if(counts.get(part.id)!==part.notes.length)throw new Error('MIDI track incomplete');
  for(const point of part.expression||[])point.time=midi.header.ticksToSeconds(point.ticks);
 }
 for(const measure of song.measures){measure.time=midi.header.ticksToSeconds(measure.ticks);measure.duration=midi.header.ticksToSeconds(measure.ticks+measure.durationTicks)-measure.time;for(const point of measure.positions||[])if(point.ticks!==undefined)point.time=midi.header.ticksToSeconds(measure.ticks+point.ticks)-measure.time;}
 for(const beat of song.beats)beat.time=midi.header.ticksToSeconds(beat.ticks);
 const last=song.measures.at(-1);song.duration=last.time+last.duration;return song;
}
