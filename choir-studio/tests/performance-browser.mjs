import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
const browser=await chromium.connectOverCDP(process.env.CDP_URL||'http://127.0.0.1:9333');
try{
 const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});
 const page=await context.newPage();await page.goto('http://127.0.0.1:5173');await page.locator('#play:enabled').waitFor();
 await page.locator('#menu').click();await page.locator('[data-song="let-it-go"]').click();await page.waitForFunction(()=>document.querySelector('#song-title').textContent==='Let It Go');
 await page.evaluate(async()=>{
  const {ChoirAudio}=await import('/audio-engine.js');const playNote=ChoirAudio.prototype.playNote;
  window.qa={lead:[],frames:[],sync:[]};
  ChoirAudio.prototype.playNote=function(v,n,time,remaining){window.qa.lead.push(time-Tone.getContext().rawContext.currentTime);return playNote.call(this,v,n,time,remaining);};
  const descriptor=Object.getOwnPropertyDescriptor(ChoirAudio.prototype,'audiblePosition');
  Object.defineProperty(ChoirAudio.prototype,'audiblePosition',{get(){const result=descriptor.get.call(this),raw=Tone.getContext().rawContext;window.qa.sync.push(Math.abs(result-this.transport.getTicksAtTime(raw.currentTime)/384));return result;}});
  document.querySelector('#seek').value=145;document.querySelector('#seek').dispatchEvent(new Event('input',{bubbles:true}));
 });
 await page.locator('#play').click();await page.waitForFunction(()=>Tone.getTransport().state==='started');
 await page.evaluate(()=>{let last=performance.now();window.qa.raf=true;function frame(now){if(!window.qa.raf)return;window.qa.frames.push(now-last);last=now;requestAnimationFrame(frame);}requestAnimationFrame(frame);window.qa.stress=setInterval(()=>{const end=performance.now()+120;while(performance.now()<end){}},1000);});
 await page.waitForTimeout(12000);
 const report=await page.evaluate(()=>{clearInterval(window.qa.stress);window.qa.raf=false;const sorted=window.qa.frames.slice(5).sort((a,b)=>a-b);return {notes:window.qa.lead.length,lateNotes:window.qa.lead.filter(v=>v<-.005).length,minLead:Math.min(...window.qa.lead),frameP95:sorted[Math.floor(sorted.length*.95)],frameMax:Math.max(...sorted),syncMax:Math.max(...window.qa.sync),stress:'120ms main-thread block every second, 390x844 viewport'};});
 console.log(report);assert.ok(report.notes>40);assert.equal(report.lateNotes,0,'all notes scheduled before their audio deadline');assert.ok(report.frameP95<45,'ordinary animation frames remain smooth between deliberate blocks');assert.ok(report.syncMax<.15,'cursor uses the audible clock');
 await page.locator('#play').click();await page.screenshot({path:'test-results/dark-mobile.png'});await writeFile('test-results/performance-report.json',JSON.stringify(report,null,2));await context.close();
}finally{await browser.close();}
