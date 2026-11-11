export function installScoreZoom({getZoom,onZoom}){
 const sc=document.getElementById('score-scroll'),content=document.getElementById('score-content'),byId=id=>document.getElementById(id);
 let pinch=null,suppressUntil=0,manualUntil=0;
 function anchorAt(x,y){
  const viewport=sc.getBoundingClientRect();x??=viewport.left+viewport.width/2;y??=viewport.top+viewport.height/2;
  const pages=[...content.querySelectorAll('.page-wrapper')],page=pages.reduce((best,p)=>{const r=p.getBoundingClientRect(),gap=Math.max(r.top-y,0,y-r.bottom);return !best||gap<best.gap?{node:p,gap}:best;},null)?.node;if(!page)return;
  const r=page.getBoundingClientRect();return {page:Number(page.dataset.page),x:r.width?(x-r.left)/r.width:0,y:r.height?(y-r.top)/r.height:0,screenX:x-viewport.left,screenY:y-viewport.top};
 }
 function change(value,anchor=anchorAt()){onZoom(Math.max(25,Math.min(400,Math.round(value))),anchor);manualUntil=performance.now()+1800;}
 byId('zoom-in').onclick=()=>change(getZoom()+25);byId('zoom-out').onclick=()=>change(getZoom()-25);byId('fit-score').onclick=()=>change(100);
 const distance=touches=>Math.hypot(touches[0].clientX-touches[1].clientX,touches[0].clientY-touches[1].clientY);
 sc.addEventListener('touchstart',event=>{
  manualUntil=performance.now()+1800;if(event.touches.length!==2)return;event.preventDefault();
  const x=(event.touches[0].clientX+event.touches[1].clientX)/2,y=(event.touches[0].clientY+event.touches[1].clientY)/2;
  pinch={distance:distance(event.touches),zoom:getZoom(),next:getZoom(),anchor:anchorAt(x,y)};
  const rect=content.getBoundingClientRect();content.style.transformOrigin=`${x-rect.left}px ${y-rect.top}px`;
 },{passive:false});
 sc.addEventListener('touchmove',event=>{manualUntil=performance.now()+1800;if(!pinch||event.touches.length!==2)return;event.preventDefault();pinch.next=Math.max(25,Math.min(400,pinch.zoom*distance(event.touches)/Math.max(1,pinch.distance)));content.style.transform=`scale(${pinch.next/pinch.zoom})`;},{passive:false});
 function finish(event){if(!pinch||event.touches.length>=2)return;const gesture=pinch;pinch=null;content.style.transform='';content.style.transformOrigin='';suppressUntil=performance.now()+450;change(gesture.next,gesture.anchor);}
 sc.addEventListener('touchend',finish);sc.addEventListener('touchcancel',finish);
 sc.addEventListener('click',event=>{if(performance.now()<suppressUntil){event.preventDefault();event.stopImmediatePropagation();}},true);
 sc.addEventListener('wheel',event=>{manualUntil=performance.now()+1800;if(!event.ctrlKey)return;event.preventDefault();change(getZoom()*(event.deltaY<0?1.1:1/1.1),anchorAt(event.clientX,event.clientY));},{passive:false});
 return {get pinching(){return !!pinch;},get browsing(){return !!pinch||performance.now()<manualUntil;}};
}
