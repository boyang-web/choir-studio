import test from 'node:test';
import assert from 'node:assert/strict';
import {ChoirAudio} from '../public/audio-engine.js';
import {fakeTone} from './fake-tone.mjs';
test('visual position follows the native output clock instead of scheduling lookahead',()=>{
 globalThis.Tone=fakeTone();
 Tone.getContext=()=>({rawContext:{currentTime:10,outputLatency:.03}});
 const e=new ChoirAudio();e.ready=true;e._playing=true;e.transport={ticks:3840,getTicksAtTime:time=>time*384};
 assert.equal(e.position,10);assert.ok(Math.abs(e.audiblePosition-9.97)<1e-9);
});
test('Tone scheduling: shared clock, preserved pre-play loop, seek, held notes, mute and speed',async()=>{
 globalThis.Tone=fakeTone();
 const e=new ChoirAudio();const song={parts:[{id:'soprano',notes:[{time:0,duration:2,midi:60}]},{id:'bass',notes:[{time:1,duration:1,midi:48}]}],beats:[{time:0,accent:true}]};
 const settings={soprano:{enabled:true,volume:.8},bass:{enabled:false,volume:.7}};
 e.load(song,settings);e.seek(.5);e.setLoop({a:1,b:1,start:0,end:2});e.setRate(.75);
 await e.play(song,settings);
 assert.ok(e.playing);assert.equal(e.position,.5);assert.equal(e.transport.bpm.value,90);assert.equal(e.transport.loop,true);assert.equal(e.transport.loopEnd,'768i');
 assert.equal(e.voices.get('soprano').channel.gain.value,.8);assert.equal(e.voices.get('bass').channel.gain.value,0);
 assert.ok(e.voices.get('soprano').synth.events.length>0,'seek resumes a held note');
 assert.equal(e.transport.events[0].time,'0i');assert.equal(e.transport.events[1].time,'384i');
 e.transport.events[1].callback(10);assert.equal(e.voices.get('bass').synth.events[0][0],440*2**((48-69)/12));
 e.transport.ticks=384;e.setRate(.5);assert.equal(e.position,1);assert.equal(e.transport.bpm.value,60);assert.ok(e.playing);
 e.pause();assert.ok(!e.playing);assert.equal(e.gate.gain.value,0);
 e.seek(1.25);assert.equal(e.position,1.25);e.setVolume(.3);assert.equal(e.master.gain.value,.3);
 e.load(song,settings);assert.equal(e.position,0);assert.equal(e.loop,null);assert.equal(e.transport.loop,false);
});
