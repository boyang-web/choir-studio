import {instrumentFor,defaultSound} from './instruments.js';
import {expressionAt} from './expression.js';
const PPQ=192,toTicks=seconds=>Math.round(seconds*PPQ*2);
export class ChoirAudio{
 constructor(){this.ready=false;this.voices=new Map();this.rate=1;this.offset=0;this.song=null;this.metro=false;this.expressive=true;this._playing=false;this.settings={};}
 async init(){
  await Tone.start();if(this.ready)return;
  // Leave enough scheduling headroom for scrolling and mobile WebView paints.
  Tone.getContext().lookAhead=.25;Tone.getContext().updateInterval=.025;this.transport=Tone.getTransport();this.transport.PPQ=PPQ;
  this.ceiling=Tone.WaveShaper?new Tone.WaveShaper(x=>{const a=Math.abs(x);return a<=.82?x:Math.sign(x)*(.82+.13*Math.tanh((a-.82)/.13));},8192).toDestination():new Tone.Gain(1).toDestination();
  this.limiter=new Tone.Limiter(-1).connect(this.ceiling);this.master=new Tone.Gain(this.volume??.7).connect(this.limiter);this.gate=new Tone.Gain(1).connect(this.master);
  this.click=new Tone.Synth({oscillator:{type:'sine'},envelope:{attack:.001,decay:.035,sustain:0,release:.02},volume:-18}).connect(this.gate);
  this.transport.on?.('loopEnd',time=>this.silence(time));this.transport.on?.('loopStart',time=>this.restoreExpression(this.loop?.start||0,time));this.ready=true;
 }
 load(song,settings){
  this.song=song;this.offset=0;this.loop=null;this._playing=false;this.settings=settings;if(!this.ready)return;
  this.transport.stop();this.transport.cancel(0);
  for(const v of this.voices.values()){for(const layer of v.layers.values()){layer.synth.dispose();layer.channel.dispose();}v.expression.dispose();v.channel.dispose();}
  this.voices.clear();this.transport.bpm.value=120*this.rate;
  for(const part of song.parts){
   const channel=new Tone.Gain(1).connect(this.gate),expression=new Tone.Gain(.65).connect(channel),sound=settings[part.id]?.sound||defaultSound(part.id),layers=new Map();
   const branches=part.branches?.length?['shared',...part.branches.map(b=>b.id)]:['shared'];
   for(const id of branches){const layerChannel=new Tone.Gain(1).connect(expression);layers.set(id,{channel:layerChannel,synth:instrumentFor(sound,layerChannel)});}
   const v={part,channel,expression,layers,synth:layers.get('shared').synth,isDrum:sound==='beatbox'};this.voices.set(part.id,v);
   for(const n of part.notes)this.transport.schedule(time=>this.playNote(v,n,time,n.duration),`${toTicks(n.time)}i`);
   const points=part.expression||[];
   points.forEach((point,index)=>this.transport.schedule(time=>{
    if(!this.expressive)return;expression.gain.setValueAtTime(point.value,time);
    const next=points[index+1];if(next?.linear&&expression.gain.linearRampToValueAtTime)expression.gain.linearRampToValueAtTime(next.value,time+(next.time-point.time)/this.rate);
   },`${toTicks(point.time)}i`));
  }
  for(const beat of song.beats||[])this.transport.schedule(time=>{if(this.metro)this.click.triggerAttackRelease(beat.accent?'C6':'G5',.025,time);},`${toTicks(beat.time)}i`);
  this.apply(settings);this.setLoop(null);this.gate.gain.value=1;this.restoreExpression(0);
 }
 playNote(v,n,time,remaining){
  const layer=v.layers.get(n.branch)||v.layers.get('shared');
  if(v.isDrum)layer.synth.hit(n.kind||'hat',time,n.velocity??.75,n.syllable,remaining/this.rate);
  else layer.synth.triggerAttackRelease(Tone.Frequency(n.midi,'midi').toFrequency(),Math.max(.02,remaining/this.rate),time,n.velocity??.75);
 }
 apply(settings){
  this.settings=settings;if(!this.ready)return;
  for(const [id,v]of this.voices){
   const s=settings[id];v.channel.gain.rampTo(s?.enabled?s.volume:0,.025);
   const enabled=(v.part.branches||[]).some(b=>s?.branches?.[b.id]!==false);
   for(const [branch,layer]of v.layers){const on=branch==='shared'?(!(v.part.branches?.length)||enabled):s?.branches?.[branch]!==false;layer.channel.gain.rampTo(on?1:0,.025);}
  }
 }
 restoreExpression(position,time=Tone.now()){
  if(!this.ready)return;
  for(const v of this.voices.values()){
   const param=v.expression.gain;param.cancelScheduledValues(time);param.setValueAtTime(this.expressive?expressionAt(v.part.expression,position):.65,time);
   if(!this.expressive)continue;
   const next=v.part.expression?.find(p=>p.time>position);if(next?.linear&&param.linearRampToValueAtTime)param.linearRampToValueAtTime(next.value,time+(next.time-position)/this.rate);
  }
 }
 setExpressive(on){this.expressive=on;if(this.ready)this.restoreExpression(this.position);}
 get playing(){return this._playing;}
 get position(){return this.ready?this.transport.ticks/(PPQ*2):this.offset;}
 get audiblePosition(){
  if(!this.ready||!this.playing||!this.transport.getTicksAtTime)return this.position;
  const raw=Tone.getContext().rawContext;
  // Render against the output clock, rather than Tone's future scheduling clock.
  const stamp=raw.getOutputTimestamp?.();
  const time=stamp?.contextTime>0?Math.min(raw.currentTime,stamp.contextTime+Math.max(0,performance.now()-stamp.performanceTime)/1000):Math.max(0,raw.currentTime-(raw.outputLatency||0));
  return Math.max(0,this.transport.getTicksAtTime(time)/(PPQ*2));
 }
 async play(song,settings){
  await this.init();if(this.song!==song)return;
  if(this.voices.size===0){const saved=this.offset,range=this.loop;this.load(song,settings);this.setLoop(range);this.offset=saved;this.transport.ticks=toTicks(saved);}
  await Promise.all([...this.voices.values()].flatMap(v=>[...v.layers.values()].map(l=>l.synth.ready)));
  if(this.song!==song)return;
  this.gate.gain.cancelScheduledValues(Tone.now());this.gate.gain.setValueAtTime(1,Tone.now());this.restoreExpression(this.position);this.resumeHeld(this.position);this.transport.start('+0.04');this._playing=true;
 }
 silence(time=Tone.now()){if(!this.ready)return;for(const v of this.voices.values())for(const layer of v.layers.values())layer.synth.releaseAll(time);}
 pause(){if(!this.ready){this._playing=false;return;}this.offset=this.position;this.transport.pause();this.gate.gain.rampTo(0,.015);this.silence();this._playing=false;}
 seek(seconds){this.offset=seconds;if(!this.ready)return;const playing=this.playing;this.transport.pause();this.silence();this.transport.ticks=toTicks(seconds);this.restoreExpression(seconds);if(playing){this.resumeHeld(seconds);this.transport.start('+0.04');}}
 resumeHeld(seconds){for(const v of this.voices.values())for(const n of v.part.notes){if(v.isDrum&&n.kind!=='breath')continue;if(n.time<seconds-.025&&n.time+n.duration>seconds+.025)this.playNote(v,n,Tone.now()+.04,n.time+n.duration-seconds);}}
 setRate(rate){const pos=this.position,playing=this.playing;if(playing)this.pause();this.rate=rate;if(this.ready){this.transport.bpm.value=120*rate;this.transport.ticks=toTicks(pos);this.restoreExpression(pos);}if(playing){this.gate.gain.rampTo(1,.015);this.resumeHeld(pos);this.transport.start('+0.04');this._playing=true;}}
 setVolume(volume){this.volume=Math.max(0,Math.min(4,Number(volume)||0));if(this.ready)this.master.gain.rampTo(this.volume,.025);}
 setLoop(range){this.loop=range;if(!this.ready)return;this.transport.loop=false;if(range){this.transport.loopStart=`${toTicks(range.start)}i`;this.transport.loopEnd=`${toTicks(range.end)}i`;this.transport.loop=true;}}
}
