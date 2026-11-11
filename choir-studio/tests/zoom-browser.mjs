import {chromium} from 'playwright';
import assert from 'node:assert/strict';
const browser=await chromium.connectOverCDP(process.env.CDP_URL||'http://127.0.0.1:9333');
try{
 const context=await browser.newContext({viewport:{width:390,height:844},isMobile:true,hasTouch:true});const page=await context.newPage();await page.goto('http://127.0.0.1:5173');await page.locator('#play:enabled').waitFor();
 assert.equal(await page.locator('.page-wrapper').count(),10);assert.equal(await page.locator('.reading-row').count(),0);
 await page.locator('#follow').uncheck();const session=await context.newCDPSession(page),box=await page.locator('#score-scroll').boundingBox(),cy=box.y+Math.min(100,box.height/2);
 await session.send('Input.dispatchTouchEvent',{type:'touchStart',touchPoints:[{id:1,x:145,y:cy},{id:2,x:245,y:cy}]});
 await session.send('Input.dispatchTouchEvent',{type:'touchMove',touchPoints:[{id:1,x:105,y:cy},{id:2,x:285,y:cy}]});
 await session.send('Input.dispatchTouchEvent',{type:'touchEnd',touchPoints:[]});
 await page.waitForFunction(()=>document.querySelector('#zoom-label').textContent==='180%');
 assert.ok(await page.evaluate(()=>document.querySelector('#score-scroll').scrollWidth>document.querySelector('#score-scroll').clientWidth));
 const geometry=await page.locator('.page-wrapper').first().evaluate(el=>({actual:el.clientWidth/el.clientHeight,original:Number(el.querySelector('img').getAttribute('width'))/Number(el.querySelector('img').getAttribute('height'))}));assert.ok(Math.abs(geometry.actual-geometry.original)<.005,'page retains its exact original aspect ratio');
 await page.evaluate(()=>document.querySelector('#score-scroll').scrollLeft=100);assert.ok(await page.evaluate(()=>document.querySelector('#score-scroll').scrollLeft>50));
 await page.screenshot({path:'test-results/pinch-mobile.png'});await page.locator('#fit-score').click();assert.equal(await page.locator('#zoom-label').textContent(),'100%');
 await page.reload();await page.locator('#play:enabled').waitFor();assert.equal(await page.locator('#zoom-label').textContent(),'100%');
 console.log('PASS: real two-finger pinch 100% -> 180%, original pages, horizontal panning, fit width and persisted zoom');await context.close();
}finally{await browser.close();}
