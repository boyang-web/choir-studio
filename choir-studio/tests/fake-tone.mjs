export function fakeTone(){
 const synths=[];
 class Gain{constructor(value=1){this.gain={value,rampTo:(v)=>this.gain.value=v,cancelScheduledValues(){},setValueAtTime:(v)=>this.gain.value=v};}connect(){return this;}toDestination(){return this;}dispose(){}}
 class Synth{constructor(){this.events=[];synths.push(this);}connect(){return this;}triggerAttackRelease(...args){this.events.push(args);}releaseAll(){this.released=true;}triggerRelease(){this.released=true;}dispose(){this.disposed=true;}}
 const transport={PPQ:192,ticks:0,state:'stopped',bpm:{value:120},events:[],start(){this.state='started';},pause(){this.state='paused';},stop(){this.state='stopped';this.ticks=0;},cancel(){this.events=[];},schedule(callback,time){this.events.push({callback,time});}};
 return {start:async()=>{},getContext:()=>({}),getTransport:()=>transport,Gain,Limiter:Gain,Synth,PolySynth:Synth,NoiseSynth:Synth,Frequency:midi=>({toFrequency:()=>440*2**((midi-69)/12)}),now:()=>0,_transport:transport,_synths:synths};
}
