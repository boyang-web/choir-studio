/** Bar-level responsive layout. All source rectangles refer to original PDF graphics. */
export function layoutScore(song,availableWidth,zoom=100){
 const width=Math.max(180,availableWidth);
 // Staff spacing is independent of viewport width. Narrow devices get more rows,
 // rather than smaller notation. Desktop/tablet users can request larger notation.
 const targetInterline=(width<600?8.5:9)*zoom/100;
 const rows=[];
 song.systems.forEach((system,systemIndex)=>{
  const measures=song.measures.filter(m=>m.system===systemIndex);
  const headerRight=system.headerRight??measures[0].left+40;
  const headerWidth=headerRight-system.x;
  const scale=targetInterline/(system.interline||12);
  let batch=[];
  const flush=()=>{
   if(!batch.length)return;
   const sourceWidth=headerWidth+batch.reduce((s,item)=>s+item.sourceWidth,0);
   const fittedScale=Math.max(scale,Math.min(width/sourceWidth,scale*1.12));
   const row={index:rows.length,system:systemIndex,page:system.page,continuation:batch[0].measure.index!==measures[0].index,scale:fittedScale,headerWidth:headerWidth*fittedScale,width:sourceWidth*fittedScale,height:system.height*fittedScale,items:batch.map(item=>({...item,width:item.sourceWidth*fittedScale}))};
   let x=row.headerWidth;for(const item of row.items){item.x=x;x+=item.width;}
   rows.push(row);batch=[];
  };
  for(const measure of measures){
   const sourceLeft=measure.index===measures[0].index?headerRight:measure.left;
   const item={measure,sourceLeft,sourceWidth:measure.right-sourceLeft};
   const sourceWidth=headerWidth+batch.reduce((s,item)=>s+item.sourceWidth,0)+item.sourceWidth;
   if(batch.length&&sourceWidth*scale>width)flush();
   batch.push(item);
  }
  flush();
 });
 return rows;
}
