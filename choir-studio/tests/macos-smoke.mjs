import {_electron} from 'playwright';
import {fileURLToPath} from 'node:url';
import assert from 'node:assert/strict';

const executablePath=process.env.ELECTRON_PATH||fileURLToPath(new URL('../macos/node_modules/electron/dist/Electron.app/Contents/MacOS/Electron',import.meta.url));
const args=process.env.ELECTRON_PATH?[]:[fileURLToPath(new URL('../macos/main.cjs',import.meta.url))];
const application=await _electron.launch({executablePath,args});
try{
 const page=await application.firstWindow();const errors=[];
 page.on('pageerror',e=>errors.push(e.message));
 await page.locator('#play:enabled').waitFor();
 assert.equal(new URL(page.url()).protocol,'choir:');
 await page.locator('[data-song="hui-sheng"]').click();
 await page.waitForFunction(()=>document.querySelector('#song-title').textContent==='回声'&&!document.querySelector('#play').disabled);
 assert.equal(await page.locator('.voice-row').count(),8);
 await page.locator('#play').click();
 await page.waitForFunction(()=>Tone.getTransport().state==='started');
 await page.evaluate(()=>{window.qaAnalyser=new Tone.Analyser('waveform',2048);Tone.getDestination().connect(window.qaAnalyser);});
 await page.waitForFunction(()=>qaAnalyser.getValue().some(v=>Math.abs(v)>.00001),{timeout:10000});
 assert.equal(await page.evaluate(()=>typeof window.require),'undefined');
 assert.deepEqual(errors,[]);
 console.log('PASS macOS native app: bundled protocol, eight voices, real audio, renderer isolation');
}finally{await application.close();}
