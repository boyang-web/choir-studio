/* Tone.js provides sampling, buffer playback, filtering and envelopes.
 * Sample credits: samples/SOURCES.md. */
let manifestPromise;
const banks=new Map();
async function sampleBank(name){
 if(!banks.has(name))banks.set(name,(async()=>{
  manifestPromise??=fetch('samples/manifest.json').then(r=>{if(!r.ok)throw new Error('音色清单读取失败');return r.json();});
  const manifest=await manifestPromise,bank=manifest[name];
  if(!bank)throw new Error('未知音色 '+name);
  return Promise.all(Object.entries(bank.samples).map(async([note,info])=>{
   const buffer=await new Promise((resolve,reject)=>{const b=new Tone.ToneAudioBuffer({url:'samples/'+info.file,onload:()=>resolve(b),onerror:reject});});
   // Choir practice needs a stable mono image. Decode once at a smaller rate
   // instead of resampling dozens of stereo 44.1 kHz voices on a phone.
   const original=buffer.get(),rate=22050,mono=Tone.getContext().rawContext.createBuffer(1,Math.ceil(original.duration*rate),rate),out=mono.getChannelData(0),channels=Array.from({length:original.numberOfChannels},(_,i)=>original.getChannelData(i));
   for(let i=0;i<out.length;i++){const pos=i*original.sampleRate/rate,a=Math.floor(pos),f=pos-a;let value=0;for(const channel of channels)value+=(channel[a]||0)*(1-f)+(channel[Math.min(a+1,channel.length-1)]||0)*f;out[i]=value/channels.length;}
   buffer.set(mono);
   return {...info,midi:Tone.Frequency(note).toMidi(),note,buffer};
  }));
 })().catch(error=>{banks.delete(name);throw error;}));
 return banks.get(name);
}
export class SampleVoice{
 constructor(bank,output){this.bank=bank;this.output=output;this.sources=new Map();this.disposed=false;this.ready=sampleBank(bank).then(samples=>{this.samples=samples;});this.ready.catch(()=>{});}
 triggerAttackRelease(frequency,duration,time,velocity=.75){
  if(this.disposed||!this.samples)return;
  const midi=69+12*Math.log2(frequency/440),sample=this.samples.reduce((a,b)=>Math.abs(a.midi-midi)<Math.abs(b.midi-midi)?a:b),loop=this.bank!=='piano';
  const context=Tone.getContext().rawContext,start=Math.max(time,context.currentTime),end=start+Math.max(.02,duration),level=Math.max(.01,Math.min(1,velocity))*(loop?.34:.5),release=loop?.06:.2;
  // Carry a choir vowel through an adjacent melodic note. Restarting its
  // recorded attack on every short note sounds chopped even with perfect timing.
  const previous=loop?[...this.sources.keys()].find(v=>v.start<start-.01&&Math.abs(v.end-start)<.012&&Math.abs(v.midi-midi)<=7):null;
  if(previous){
   previous.source.playbackRate.setValueAtTime(previous.rate,Math.max(previous.start,start-.012));
   previous.rate=2**((midi-previous.rootMidi)/12);previous.source.playbackRate.linearRampToValueAtTime(previous.rate,start+.012);
   previous.gain.gain.cancelScheduledValues(start);previous.gain.gain.setValueAtTime(previous.level,start);previous.gain.gain.linearRampToValueAtTime(level,start+.012);previous.gain.gain.setValueAtTime(level,end);previous.gain.gain.linearRampToValueAtTime(0,end+release);
   previous.source.stop(end+release+.005);previous.end=end;previous.midi=midi;previous.level=level;return;
  }
  // Native onended runs after actual rendering, so short notes and offline
  // rendering cannot lose their buffers to an early scheduling callback.
  const source=context.createBufferSource(),gain=context.createGain();
  source.buffer=sample.buffer.get();source.loop=loop;source.loopStart=sample.loopStart||0;source.loopEnd=sample.loopEnd||0;source.playbackRate.value=2**((midi-sample.midi)/12);
  source.connect(gain);Tone.connect(gain,this.output);
  gain.gain.setValueAtTime(0,start);gain.gain.linearRampToValueAtTime(level,start+(loop?.008:.002));gain.gain.setValueAtTime(level,end);gain.gain.linearRampToValueAtTime(0,end+release);
  const voice={source,gain,start,end,midi,level,rootMidi:sample.midi,rate:source.playbackRate.value,stop:when=>{const at=Math.max(when,start+.001);gain.gain.cancelScheduledValues(at);gain.gain.setTargetAtTime(0,at,.008);source.stop(at+.04);voice.end=-1;},dispose:()=>{source.onended=null;try{source.stop();}catch{}source.disconnect();gain.disconnect();}};
  source.onended=()=>{this.sources.delete(voice);source.disconnect();gain.disconnect();};
  this.sources.set(voice,start);source.start(start,0);source.stop(end+release+.005);
 }
 releaseAll(time=Tone.now()){for(const [source,start]of this.sources){try{source.stop(Math.max(time,start+.001));}catch{}}}
 dispose(){this.disposed=true;for(const source of this.sources.keys())source.dispose();this.sources.clear();}
}
export class Beatbox{
 constructor(output){
  this.nodes=[];
  if(!Tone.Filter){this.fallback=new Tone.NoiseSynth().connect(output);return;}
  const filter=(frequency,type,Q=.7)=>{const f=new Tone.Filter(frequency,type);f.Q.value=Q;f.connect(output);this.nodes.push(f);return f;};
  this.kick=new Tone.MembraneSynth({pitchDecay:.035,octaves:1.5,oscillator:{type:'triangle'},envelope:{attack:.002,decay:.10,sustain:0,release:.045},volume:-17}).connect(filter(900,'lowpass'));
  this.body=new Tone.MembraneSynth({pitchDecay:.025,octaves:.45,oscillator:{type:'triangle'},envelope:{attack:.003,decay:.10,sustain:.12,release:.055},volume:-10}).connect(filter(1900,'lowpass'));
  this.snare=new Tone.NoiseSynth({noise:{type:'brown'},envelope:{attack:.002,decay:.085,sustain:0,release:.045},volume:-10}).connect(filter(1550,'bandpass',1.4));
  this.hat=new Tone.NoiseSynth({noise:{type:'white'},envelope:{attack:.001,decay:.018,sustain:0,release:.018},volume:-17}).connect(filter(6100,'highpass'));
  this.click=new Tone.NoiseSynth({noise:{type:'white'},envelope:{attack:.001,decay:.022,sustain:0,release:.012},volume:-11}).connect(filter(2300,'bandpass',7));
  this.breath=new Tone.NoiseSynth({noise:{type:'pink'},envelope:{attack:.04,decay:.16,sustain:.55,release:.12},volume:-16}).connect(filter(2900,'bandpass',.7));
  this.nodes.push(this.kick,this.body,this.snare,this.hat,this.click,this.breath);
 }
 hit(kind,time,velocity=.75,syllable='',duration=.12){
  if(this.fallback){this.fallback.triggerAttackRelease(.07,time,velocity);return;}
  if(kind==='vocal')this.body.triggerAttackRelease(/^k/i.test(syllable)?'G3':'C3',Math.max(.04,Math.min(.35,duration)),time,velocity);
  else if(kind==='kick')this.kick.triggerAttackRelease('C2',.08,time,velocity);
  else if(kind==='snare'){this.snare.triggerAttackRelease(.05,time,velocity);this.kick.triggerAttackRelease('G1',.04,time,velocity*.32);}
  else if(kind==='breath')this.breath.triggerAttackRelease(Math.max(.12,duration),time,velocity);
  else if(kind==='click')this.click.triggerAttackRelease(.025,time,velocity);
  else this.hat.triggerAttackRelease(.025,time,velocity);
 }
 releaseAll(time=Tone.now()){if(this.fallback)this.fallback.triggerRelease(time);else for(const node of [this.kick,this.body,this.snare,this.hat,this.click,this.breath])node.triggerRelease(time);}
 dispose(){if(this.fallback)this.fallback.dispose();for(const n of this.nodes)n.dispose();}
}
export function instrumentFor(sound,output){
 if(sound==='beatbox')return new Beatbox(output);
 if(['male','female','piano'].includes(sound)&&Tone.ToneAudioBuffer)return new SampleVoice(sound,output);
 return new Tone.PolySynth(Tone.Synth,{oscillator:{type:sound==='flute'?'triangle':'sine'},envelope:{attack:sound==='pure'?.01:.035,decay:.12,sustain:.65,release:.10},volume:-17}).connect(output);
}
export const defaultSound=id=>id==='percussion'?'beatbox':id==='piano'?'piano':id==='ocarina'?'flute':['soprano','alto'].includes(id)?'female':'male';
