import {chromium} from 'playwright';
import assert from 'node:assert/strict';

const browser=await chromium.launch({headless:true,...(process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:{})});
try{
 for(const viewport of [{width:1440,height:1000},{width:390,height:844}]){
  const page=await browser.newPage({viewport});const errors=[];
  page.on('pageerror',e=>errors.push(e.message));
  await page.goto(process.env.BASE_URL||'http://127.0.0.1:5173');
  await page.locator('#play:enabled').waitFor();
  if(viewport.width<1280)await page.locator('#menu').click();
  await page.locator('[data-song="hui-sheng"]').click();
  await page.waitForFunction(()=>document.querySelector('#song-title').textContent==='回声'&&!document.querySelector('#play').disabled);
  assert.equal(await page.locator('.voice-row').count(),8);
  assert.equal(await page.locator('.page-wrapper').count(),3);
  assert.equal(await page.locator('[data-measure]').count(),38);
  assert.equal(await page.locator('#local-updates,#offline-share').count(),0);
  for(const start of [0,14,34,64,72]){
   await page.locator('#seek').evaluate((el,value)=>{el.value=value;el.dispatchEvent(new Event('input'));},start);
   await page.locator('#play').click();
   await page.waitForFunction(()=>Tone.getTransport().state==='started');
   await page.evaluate(()=>{window.qaAnalyser?.dispose();window.qaAnalyser=new Tone.Analyser('waveform',2048);Tone.getDestination().connect(window.qaAnalyser);});
   await page.waitForFunction(()=>qaAnalyser.getValue().some(v=>Math.abs(v)>.00001),{timeout:10000});
   await page.locator('#play').click();
  }
  if(viewport.width<1100)await page.locator('#mixer-toggle').click();
  for(const id of ['soprano-1','alto-1','tenor-1','bass-1','soprano-2','alto-2','tenor-2','bass-2']){
   await page.locator(`[data-solo="${id}"]`).click();
   assert.equal(await page.locator('.voice-toggle:checked').count(),1);
   assert.equal(await page.locator(`[data-toggle="${id}"]`).isChecked(),true);
  }
  await page.locator('#all-voices').click();
  if(viewport.width<1100)await page.locator('#mixer-close').click();
  await page.screenshot({path:`test-results/hui-sheng-${viewport.width}.png`});
  assert.deepEqual(errors,[]);
  console.log(`PASS Hui Sheng ${viewport.width}: 8 solos, 38 bars, 5 real-audio positions`);
  await page.close();
 }
}finally{await browser.close();}
