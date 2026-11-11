import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
const browser=await chromium.connectOverCDP(process.env.CDP_URL||'http://127.0.0.1:9333');
try{
 const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});const page=await context.newPage();await page.goto('http://127.0.0.1:5173');await page.locator('#play:enabled').waitFor();
 assert.equal(await page.locator('[data-sound]').count(),0);
 const errors=[];page.on('pageerror',e=>errors.push(e.message));
 await page.evaluate(async()=>{const {ChoirAudio}=await import('/audio-engine.js'),play=ChoirAudio.prototype.playNote;window.qaNotes=[];ChoirAudio.prototype.playNote=function(v,n,time,remaining){window.qaNotes.push({part:v.part.id,midi:n.midi,source:n.time,lead:time-Tone.getContext().rawContext.currentTime});return play.call(this,v,n,time,remaining);};const song=await (await fetch('/songs/chi-le-ge/song.json')).json();window.qaSong=song;document.querySelector('#seek').value=song.measures[41].time;document.querySelector('#seek').dispatchEvent(new Event('input'));});
 await page.locator('#play').click();await page.waitForFunction(()=>Tone.getTransport().state==='started');await page.waitForTimeout(4200);await page.locator('#play').click();
 const bar42=await page.evaluate(()=>({events:qaNotes.length,late:qaNotes.filter(n=>n.lead<-.005).length,hasNonupletD7:qaNotes.some(n=>n.part==='piano'&&n.midi===98&&Math.abs(n.source-qaSong.measures[41].time-60/qaSong.tempo*(22/9))<.001)}));assert.ok(bar42.hasNonupletD7);assert.equal(bar42.late,0);
 await page.evaluate(()=>{document.querySelector('#seek').value=qaSong.measures[43].time;document.querySelector('#seek').dispatchEvent(new Event('input'));window.qaFrames=[];function frame(t){if(Tone.getTransport().state==='started'&&Tone.getTransport().getTicksAtTime(Tone.getContext().rawContext.currentTime)/384>qaSong.measures[43].time+.03&&document.querySelector('.measure-hit.current')?.dataset.measure==='43'){const cursor=document.querySelector('.page-wrapper .score-cursor:not([hidden])');if(cursor)qaFrames.push({t,x:new DOMMatrixReadOnly(getComputedStyle(cursor).transform).m41});}if(!window.qaDone)requestAnimationFrame(frame);}requestAnimationFrame(frame);});
 await page.locator('#play').click();await page.waitForTimeout(3900);await page.locator('#play').click();
 const cursor=await page.evaluate(()=>{window.qaDone=true;let frozen=0,backward=0;const gaps=[];for(let i=1;i<qaFrames.length;i++){const dt=qaFrames[i].t-qaFrames[i-1].t,dx=qaFrames[i].x-qaFrames[i-1].x;gaps.push(dt);if(dx<=.0001)frozen++;if(dx<-.001)backward++;}gaps.sort((a,b)=>a-b);return {frames:qaFrames.length,frozen,backward,frameP95:gaps[Math.floor(gaps.length*.95)]};});
 console.log('Measured cursor',cursor);assert.ok(cursor.frames>100);assert.ok(cursor.frozen<=2);assert.equal(cursor.backward,0);assert.deepEqual(errors,[]);const report={bar42,cursor};await writeFile('test-results/reported-regressions.json',JSON.stringify(report,null,2));console.log('PASS',report);await context.close();
}finally{await browser.close();}
