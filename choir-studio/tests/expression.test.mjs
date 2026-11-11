import test from 'node:test';
import assert from 'node:assert/strict';
import {expressionAt} from '../public/expression.js';
import {ChoirAudio} from '../public/audio-engine.js';
import {fakeTone} from './fake-tone.mjs';
test('expression interpolation changes the level inside held notes and restores after seeking',async()=>{
 const points=[{time:0,value:.3},{time:2,value:.9,linear:true},{time:3,value:.4}];
 assert.ok(Math.abs(expressionAt(points,1)-.6)<1e-9);assert.equal(expressionAt(points,2.5),.9);assert.equal(expressionAt(points,4),.4);
 globalThis.Tone=fakeTone();const engine=new ChoirAudio(),song={parts:[{id:'bass',expression:points,branches:[{id:'1'},{id:'2'}],notes:[{time:0,duration:4,midi:48,branch:'1'},{time:0,duration:4,midi:43,branch:'2'},{time:4,duration:1,midi:48,branch:'shared'}]}]};
 const settings={bass:{enabled:true,volume:.8,branches:{'1':true,'2':false}}};
 engine.load(song,settings);await engine.play(song,settings);
 const voice=engine.voices.get('bass');assert.equal(voice.layers.get('1').channel.gain.value,1);assert.equal(voice.layers.get('2').channel.gain.value,0);assert.equal(voice.layers.get('shared').channel.gain.value,1);
 engine.seek(1);assert.ok(Math.abs(voice.expression.gain.value-.6)<1e-9);engine.setExpressive(false);assert.equal(voice.expression.gain.value,.65);engine.setExpressive(true);assert.ok(Math.abs(voice.expression.gain.value-.6)<1e-9);
 settings.bass.branches['1']=false;engine.apply(settings);assert.equal(voice.layers.get('shared').channel.gain.value,0);engine.pause();
});
