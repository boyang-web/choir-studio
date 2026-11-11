export function expressionAt(points,time){
 if(!points?.length)return .65;
 let last=points[0];
 for(const p of points.slice(1)){
  if(p.time>time){if(p.linear&&p.time>last.time)return last.value+(p.value-last.value)*Math.max(0,(time-last.time)/(p.time-last.time));return last.value;}
  last=p;
 }
 return last.value;
}
