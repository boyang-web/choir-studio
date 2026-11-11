// Real browser acceptance checks. CHROME_PATH or CDP_URL can point to an existing QA browser.
import {chromium} from 'playwright';
import assert from 'node:assert/strict';
import {mkdir} from 'node:fs/promises';
const options=process.env.CHROME_PATH?{executablePath:process.env.CHROME_PATH}:process.platform==='win32'?{channel:'chrome'}:{};
const browser=process.env.CDP_URL?await chromium.connectOverCDP(process.env.CDP_URL):await chromium.launch({headless:true,...options});
await mkdir('test-results',{recursive:true});
const errors=[];
try{
 for(const [name,viewport] of [['desktop',{width:1440,height:1000}],['mobile',{width:390,height:844}],['small-mobile',{width:320,height:740}],['tablet-portrait',{width:768,height:1024}],['tablet-landscape',{width:1024,height:768}],['phone-landscape',{width:844,height:390}]]){
  const context=await browser.newContext({viewport,isMobile:viewport.width<600,hasTouch:name!=='desktop'});
  const page=await context.newPage();page.on('pageerror',e=>errors.push(e.message));
  await page.goto(process.env.BASE_URL||'http://127.0.0.1:5173');
  await page.locator('#play:enabled').waitFor();
  await page.waitForTimeout(200);
  assert.equal(await page.locator('.voice-row').count(),6);
  assert.ok(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'no page-wide horizontal overflow');
  await page.getByRole('button',{name:'播放',exact:true}).click();
  await page.waitForFunction(()=>Tone.getTransport().state==='started');
  await page.evaluate(()=>{window.qaAnalyser=new Tone.Analyser('waveform',1024);Tone.getDestination().connect(window.qaAnalyser);});
  await page.waitForFunction(()=>window.qaAnalyser.getValue().some(v=>Math.abs(v)>.00001),{timeout:10000});
  if(viewport.width<1100)await page.locator('#mixer-toggle').click();
  await page.getByRole('button',{name:'独听女高音',exact:true}).click();
  assert.equal(await page.locator('.voice-toggle:checked').count(),1);
  await page.locator('#all-voices').click();
  if(viewport.width<1100)await page.locator('#mixer-close').click();
  await page.getByRole('button',{name:'暂停',exact:true}).click();
  await page.getByLabel('练习速度',{exact:true}).selectOption('0.5');
  assert.equal(await page.evaluate(()=>Tone.getTransport().bpm.value),60);
  if(viewport.width<1100)await page.locator('#mixer-toggle').click();
  await page.locator('#loop-start').fill('3');await page.locator('#loop-end').fill('4');
  await page.getByText('重复练习此段',{exact:true}).click();
  assert.equal(await page.evaluate(()=>Tone.getTransport().loop),true);
  if(viewport.width<1100)await page.locator('#mixer-close').click();
  assert.equal(await page.locator('.page-wrapper').count(),9);assert.equal(await page.locator('.reading-row').count(),0);
  await page.locator('#zoom-in').click();assert.equal(await page.locator('#zoom-label').textContent(),'125%');
  await page.locator('#zoom-out').click();await page.locator('#zoom-out').click();assert.equal(await page.locator('#zoom-label').textContent(),'75%');
  await page.locator('#fit-score').click();assert.equal(await page.locator('#zoom-label').textContent(),'100%');
  await page.screenshot({path:`test-results/${name}.png`,fullPage:true});
  if(name!=='desktop')await page.getByRole('button',{name:'打开曲库',exact:true}).click();
  await page.locator('[data-song="let-it-go"]').click();await page.waitForFunction(()=>document.getElementById('song-title').textContent==='Let It Go');
  assert.equal(await page.locator('[data-measure]').count(),119);
  if(viewport.width<1100)await page.locator('#mixer-toggle').click();
  await page.getByRole('button',{name:'独听男低音 1',exact:true}).click();
  assert.equal(await page.locator('[data-parent="bass"][data-branch="1"]').isChecked(),true);
  assert.equal(await page.locator('[data-parent="bass"][data-branch="2"]').isChecked(),false);
  await page.locator('#all-voices').click();await page.locator('[data-toggle="piano"]').uncheck();
  assert.equal(await page.locator('[data-toggle="piano"]').isChecked(),false);
  if(viewport.width<1100)await page.locator('#mixer-close').click();
  if(viewport.width===768){await page.setViewportSize({width:1024,height:768});await page.waitForTimeout(300);assert.equal(await page.locator('.page-wrapper').count(),19);await page.screenshot({path:'test-results/tablet-rotated.png',fullPage:true});}
  console.log('PASS',name,'audio + layout + divisi + controls');
  await context.close();
 }
 assert.deepEqual(errors,[]);console.log('PASS: real audio output, desktop/mobile layout and core interactions.');
}finally{await browser.close();}
