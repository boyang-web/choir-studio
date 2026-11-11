import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {writeFile} from 'node:fs/promises';
const browser=await chromium.connectOverCDP(process.env.CDP_URL||'http://127.0.0.1:9333');
try{
 const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});const page=await context.newPage();await page.goto('http://127.0.0.1:5173');await page.locator('#play:enabled').waitFor();await page.locator('#mixer-toggle').click();
 await page.locator('#master-volume').fill('4');await page.locator('#master-volume').dispatchEvent('input');assert.equal(await page.locator('#master-volume-value').textContent(),'400%');await page.reload();await page.locator('#play:enabled').waitFor();assert.equal(await page.locator('#master-volume').inputValue(),'4');
 const result=await page.evaluate(async()=>{
  const {ChoirAudio}=await import('/audio-engine.js');
  async function render(volume,input){const buffer=await Tone.Offline(async()=>{const engine=new ChoirAudio();engine.setVolume(volume);await engine.init();const oscillator=new Tone.Oscillator({frequency:440,type:'sine',volume:20*Math.log10(input)}).connect(engine.gate);oscillator.start(0).stop(.4);},.5,1,22050);const data=buffer.getChannelData(0);let sum=0,peak=0;for(let i=2205;i<7717;i++){sum+=data[i]**2;peak=Math.max(peak,Math.abs(data[i]));}return {rms:Math.sqrt(sum/(7717-2205)),peak};}
  const normal=await render(1,.05),boost=await render(4,.05),loud=await render(4,1);return {normal,boost,loud,ratio:boost.rms/normal.rms};
 });
 console.log(result);assert.ok(result.ratio>3.9&&result.ratio<4.1,'quiet signals receive the full 4x boost');assert.ok(result.loud.peak<1,'amplified steady-state output remains below digital full scale');await writeFile('test-results/volume-report.json',JSON.stringify(result,null,2));await context.close();
}finally{await browser.close();}
