import {chromium} from 'playwright';
import {writeFile} from 'node:fs/promises';
import assert from 'node:assert/strict';
const browser=await chromium.connectOverCDP(process.env.CDP_URL||'http://127.0.0.1:9333');
try{
 const context=await browser.newContext();const page=await context.newPage();await page.goto('http://127.0.0.1:5173');await page.locator('#play:enabled').waitFor();
 const result=await page.evaluate(async()=>{
  const {SampleVoice,Beatbox}=await import('/instruments.js'),{expressionAt}=await import('/expression.js');
  const song=await (await fetch('/songs/let-it-go/song.json')).json(),start=125,end=song.duration,duration=end-start;let notes=0,peak=0,sources=0;
  const rendered=await Tone.Offline(async()=>{
   for(const part of song.parts.filter(p=>p.id!=='piano')){
    const out=new Tone.Gain(.5).toDestination(),expression=new Tone.Gain(expressionAt(part.expression,start)).connect(out),layers=new Map();
    for(const id of ['shared',...(part.branches||[]).map(b=>b.id)]){const voice=part.id==='percussion'?new Beatbox(expression):new SampleVoice(['soprano','alto'].includes(part.id)?'female':'male',expression);await voice.ready;layers.set(id,voice);}
    for(const point of part.expression||[])if(point.time>=start&&point.time<end){if(point.linear)expression.gain.linearRampToValueAtTime(point.value,point.time-start);else expression.gain.setValueAtTime(point.value,point.time-start);}
    for(const n of part.notes){if(n.time+n.duration<=start||n.time>=end)continue;const voice=layers.get(n.branch)||layers.get('shared'),at=Math.max(0,n.time-start),length=Math.min(end,n.time+n.duration)-Math.max(start,n.time);if(part.id==='percussion'){if(n.time>=start)voice.hit(n.kind,at,n.velocity??.75,n.syllable,length);}else voice.triggerAttackRelease(440*2**((n.midi-69)/12),length,at,n.velocity??.75);notes++;}
    for(const voice of layers.values())sources+=voice.sources?.size||0;
   }
  },duration+.3,1,22050);
  const audio=rendered.getChannelData(0);for(const v of audio)peak=Math.max(peak,Math.abs(v));
  const wav=new ArrayBuffer(44+audio.length*2),view=new DataView(wav),write=(offset,text)=>[...text].forEach((c,i)=>view.setUint8(offset+i,c.charCodeAt(0)));
  write(0,'RIFF');view.setUint32(4,36+audio.length*2,true);write(8,'WAVE');write(12,'fmt ');view.setUint32(16,16,true);view.setUint16(20,1,true);view.setUint16(22,1,true);view.setUint32(24,22050,true);view.setUint32(28,44100,true);view.setUint16(32,2,true);view.setUint16(34,16,true);write(36,'data');view.setUint32(40,audio.length*2,true);for(let i=0;i<audio.length;i++)view.setInt16(44+i*2,Math.round(Math.max(-1,Math.min(1,audio[i]))*32767),true);
  const bytes=new Uint8Array(wav),chunks=[];for(let i=0;i<bytes.length;i+=16384)chunks.push(String.fromCharCode(...bytes.subarray(i,i+16384)));
  return {from:start,to:end,notes,sources,peak,wav:btoa(chunks.join(''))};
 });
 const {wav,...report}=result;assert.ok(report.notes>500);assert.ok(report.peak>.01&&report.peak<1,'tail mix has sound without clipping');await writeFile('test-results/let-it-go-tail.wav',Buffer.from(wav,'base64'));await writeFile('test-results/tail-report.json',JSON.stringify(report,null,2));console.log('PASS rear a cappella rendered:',report);await context.close();
}finally{await browser.close();}
