import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {mkdir,writeFile} from 'node:fs/promises';
const browser=await chromium.connectOverCDP(process.env.CDP_URL||'http://127.0.0.1:9333');
try{
 const context=await browser.newContext();const page=await context.newPage();
 await page.goto(process.env.BASE_URL||'http://127.0.0.1:5173');await page.locator('#play:enabled').waitFor();
 await page.locator('#play').click();await page.waitForFunction(()=>Tone.getTransport().state==='started');await page.locator('#play').click();
 const result=await page.evaluate(async()=>{
  const {SampleVoice,Beatbox}=await import('/instruments.js');
  const rms=(buffer,start,end)=>{const array=buffer.getChannelData(0),a=Math.round(start*buffer.sampleRate),b=Math.min(array.length,Math.round(end*buffer.sampleRate));let sum=0;for(let i=a;i<b;i++)sum+=array[i]**2;return Math.sqrt(sum/Math.max(1,b-a));};
  const result={};
  for(const name of ['male','female']){
   const buffer=await Tone.Offline(async()=>{const voice=new SampleVoice(name,new Tone.Gain(1).toDestination());await voice.ready;voice.triggerAttackRelease(Tone.Frequency('C4').toFrequency(),14,0,.8);},15,1,22050);
   result[name]={earlyRms:rms(buffer,1,2),lateRms:rms(buffer,12,13)};
  }
  const piano=await Tone.Offline(async()=>{const voice=new SampleVoice('piano',new Tone.Gain(1).toDestination());await voice.ready;voice.triggerAttackRelease(Tone.Frequency('C4').toFrequency(),3,0,.8);},4,1,22050);
  result.piano={earlyRms:rms(piano,.1,.6)};
  const short=await Tone.Offline(async()=>{const voice=new SampleVoice('female',new Tone.Gain(1).toDestination());await voice.ready;for(let i=0;i<40;i++)voice.triggerAttackRelease(Tone.Frequency(i%2?'D4':'C4').toFrequency(),.1,i*.1,.8);result.rapidSourceCount=voice.sources.size;},4.2,1,22050);
  result.shortNotes=Array.from({length:40},(_,i)=>rms(short,i*.1+.015,i*.1+.085));
  const kinds=['kick','snare','hat','click','breath','vocal'];
  const percussion=await Tone.Offline(()=>{const voice=new Beatbox(new Tone.Gain(1).toDestination());kinds.forEach((kind,i)=>voice.hit(kind,i,.8));},kinds.length,1,22050);
  result.beatbox=Object.fromEntries(kinds.map((kind,i)=>[kind,rms(percussion,i,i+.3)]));
  return result;
 });
 console.log('Measured audio',JSON.stringify(result));
 for(const name of ['male','female']){assert.ok(result[name].earlyRms>1e-5);assert.ok(result[name].lateRms>1e-5,'choir sustain loop must remain audible after 12 seconds');}
 assert.equal(result.rapidSourceCount,1,'adjacent choir notes share a continuous vowel');assert.ok(result.piano.earlyRms>1e-5);for(const rms of result.shortNotes)assert.ok(rms>1e-5,'every rapid choir note must sound');for(const rms of Object.values(result.beatbox))assert.ok(rms>1e-6);
 await mkdir('test-results',{recursive:true});await writeFile('test-results/audio-report.json',JSON.stringify(result,null,2));console.log('PASS',JSON.stringify(result));await context.close();
}finally{await browser.close();}
