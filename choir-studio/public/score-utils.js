export const clamp=(value,min,max)=>Math.max(min,Math.min(max,value));
export function measureAt(measures,time){
 let lo=0,hi=measures.length-1;
 // Tone quantizes event positions to transport ticks (one tick = 1/384 source second).
 // Treat half a tick as the same boundary so clicking a bar never selects its predecessor.
 while(lo<hi){const mid=Math.ceil((lo+hi)/2);if(measures[mid].time<=time+.00131)lo=mid;else hi=mid-1;}
 return measures[lo];
}
export function loopRange(song,start,end){
 const a=clamp(Math.round(Number(start)||1),1,song.measures.length);
 const b=clamp(Math.round(Number(end)||a),a,song.measures.length);
 return {a,b,start:song.measures[a-1].time,end:song.measures[b-1].time+song.measures[b-1].duration};
}
const cursorCurves=new WeakMap();
function cursorCurve(measure){
 if(cursorCurves.has(measure))return cursorCurves.get(measure);
 const points=[];
 for(const p of [...(measure.positions||[])].sort((a,b)=>a.time-b.time)){
  if(p.time<0||p.time>=measure.duration||!Number.isFinite(p.x))continue;
  const x=clamp(p.x,measure.left,measure.right),last=points.at(-1);
  // Repeated coordinates came from clamped OMR slots, not musical pauses.
  if(last&&(p.time<=last.time||x<=last.x+.001))continue;
  points.push({time:p.time,x});
 }
 if(!points.length||points[0].time>0)points.unshift({time:0,x:measure.left});
 if(points.at(-1).x>=measure.right)points.pop();
 if(!points.length)points.push({time:0,x:measure.left});
 points.push({time:measure.duration,x:measure.right});
 const h=points.slice(1).map((p,i)=>p.time-points[i].time),d=points.slice(1).map((p,i)=>(p.x-points[i].x)/h[i]);
 // PCHIP's weighted harmonic slopes preserve anchors and monotonicity with
 // continuous velocity. Fritsch–Butland; see SciPy PchipInterpolator notes.
 const slopes=points.map((p,i)=>{if(i===0)return d[0];if(i===points.length-1)return d.at(-1);if(d[i-1]<=0||d[i]<=0)return 0;const a=2*h[i]+h[i-1],b=h[i]+2*h[i-1];return (a+b)/(a/d[i-1]+b/d[i]);});
 const curve={points,slopes};cursorCurves.set(measure,curve);return curve;
}
export function cursorX(measure,time){
 const {points,slopes}=cursorCurve(measure),local=clamp(time-measure.time,0,measure.duration);
 let i=0;while(i<points.length-2&&local>points[i+1].time)i++;
 const a=points[i],b=points[i+1],h=b.time-a.time,t=clamp((local-a.time)/h,0,1),t2=t*t,t3=t2*t;
 return clamp((2*t3-3*t2+1)*a.x+(t3-2*t2+t)*h*slopes[i]+(-2*t3+3*t2)*b.x+(t3-t2)*h*slopes[i+1],a.x,b.x);
}
export function formatTime(seconds){const n=Math.max(0,Math.floor(seconds));return `${Math.floor(n/60)}:${String(n%60).padStart(2,'0')}`;}
