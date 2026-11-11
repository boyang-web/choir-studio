import test from 'node:test';
import assert from 'node:assert/strict';
import {readFile} from 'node:fs/promises';
import {layoutScore} from '../public/reading-layout.js';
for(const id of ['chi-le-ge','let-it-go']){
 const song=JSON.parse(await readFile(new URL(`../public/songs/${id}/song.json`,import.meta.url),'utf8'));
 test(`${id}: phone/tablet reflow preserves every bar and readable staff size`,()=>{
  for(const width of [280,320,360,600,740,980,1200]){
   const rows=layoutScore(song,width);
   assert.deepEqual(rows.flatMap(r=>r.items.map(i=>i.measure.index)),song.measures.map(m=>m.index));
   for(const row of rows){
    const sys=song.systems[row.system];assert.ok(row.scale*sys.interline>=8.5-.001);
    assert.ok(row.width<=width+.01||row.items.length===1,'only indivisible dense bars may scroll sideways');
    for(const item of row.items){assert.ok(item.sourceWidth>0);assert.ok(item.sourceLeft>=item.measure.left);assert.ok(Math.abs(item.sourceLeft+item.sourceWidth-item.measure.right)<.001);}
   }
  }
  assert.ok(layoutScore(song,320).length>=layoutScore(song,740).length);
  assert.ok(layoutScore(song,740,150).length>=layoutScore(song,740,100).length);
 });
 test(`${id}: SVG assets retain the original PDF graphics`,async()=>{
  for(const p of song.pages){const svg=await readFile(new URL(`../public/songs/${id}/${p.svg}`,import.meta.url),'utf8');assert.ok(svg.includes('<svg'));assert.ok(svg.includes('viewBox='));if(p.sourceType==='vector'){assert.ok(svg.includes('<path'));assert.ok(!svg.includes('<image'));}else assert.ok(svg.includes('<image'));}
 });
}
