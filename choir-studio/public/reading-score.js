import {layoutScore} from './reading-layout.js';
import {cursorX} from './score-utils.js';
const svgNS='http://www.w3.org/2000/svg';
export class ReadingScore{
 constructor(container,onSeek){this.container=container;this.onSeek=onSeek;this.entries=new Map();this.rows=[];}
 render(song,width,zoom){
  this.song=song;this.rows=layoutScore(song,width,zoom);this.entries.clear();
  const fragment=document.createDocumentFragment();
  for(const row of this.rows){
   const source=song.systems[row.system],page=song.pages[row.page];
   const article=document.createElement('article');article.className='reading-row';article.dataset.row=row.index;article.style.containIntrinsicSize=`auto ${row.height+25}px`;
   const caption=document.createElement('div');caption.className='system-caption';
   const title=document.createElement('span');title.textContent=`第 ${row.items[0].measure.label} — ${row.items.at(-1).measure.label} 小节${row.continuation?' · 续行':''}`;
   const origin=document.createElement('span');origin.textContent=`原谱 ${row.page+1} / ${song.pages.length}`;caption.append(title,origin);article.append(caption);
   const viewport=document.createElement('div');viewport.className='reading-row-scroll';
   const line=document.createElement('div');line.className='reading-line';line.style.width=`${row.width}px`;line.style.height=`${row.height}px`;
   const header=document.createElement('div');header.className='reading-header';header.style.width=`${row.headerWidth}px`;
   header.append(this.tile(song,page,source.x,source.y,row.headerWidth/row.scale,source.height));
   // A continuation repeats the source clefs, not a cut-off fragment of the tempo text above them.
   if(row.continuation){const cover=document.createElement('span');cover.className='header-cover';cover.style.height=`${Math.max(0,(source.staffTop-source.y-20)*row.scale)}px`;header.append(cover);}
   line.append(header);
   for(const item of row.items){
    const button=document.createElement('button');button.className='reading-measure measure-hit';button.dataset.measure=item.measure.index;button.setAttribute('aria-label',`从第${item.measure.label}小节播放`);button.title=`第 ${item.measure.label} 小节`;
    button.style.width=`${item.width}px`;button.append(this.tile(song,page,item.sourceLeft,source.y,item.sourceWidth,source.height));button.onclick=()=>this.onSeek(item.measure.time);
    this.entries.set(item.measure.index,{row,article,viewport,line,button,item});line.append(button);
   }
   const cursor=document.createElement('div');cursor.className='score-cursor';cursor.hidden=true;line.append(cursor);row.cursor=cursor;
   viewport.append(line);article.append(viewport);
   if(row.width>width+1){const hint=document.createElement('div');hint.className='wide-measure-hint';hint.textContent='这个小节较密，可左右滑动阅读';article.append(hint);}
   fragment.append(article);
  }
  this.container.replaceChildren(fragment);this.current=null;this.viewportWidth=0;
 }
 tile(song,page,x,y,width,height){
  const svg=document.createElementNS(svgNS,'svg');svg.setAttribute('viewBox',`${x} ${y} ${width} ${height}`);svg.setAttribute('preserveAspectRatio','xMinYMin meet');svg.setAttribute('aria-hidden','true');svg.classList.add('original-score-svg');
  const image=document.createElementNS(svgNS,'image');image.setAttribute('href',`songs/${song.id}/${page.svg}`);image.setAttribute('width',page.svgWidth);image.setAttribute('height',page.svgHeight);svg.append(image);return svg;
 }
 update(measure,time,{follow,force,playing,scrollContainer}){
  const entry=this.entries.get(measure.index);if(!entry)return;
  const changed=this.current!==entry;
  if(changed){this.current?.button.classList.remove('current');if(this.current)this.current.row.cursor.hidden=true;entry.button.classList.add('current');this.current=entry;}
  const {row,item,viewport}=entry;row.cursor.hidden=false;
  const sourceX=cursorX(measure,time);const x=item.x+Math.max(0,Math.min(item.sourceWidth,sourceX-item.sourceLeft))*row.scale;row.cursor.style.transform=`translate3d(${x}px,0,0)`;
  if(follow&&(force||playing)){
   if(changed||force){const top=entry.article.offsetTop;const visibleHeight=Math.min(entry.article.clientHeight,scrollContainer.clientHeight);if(force||top<scrollContainer.scrollTop||top+visibleHeight>scrollContainer.scrollTop+scrollContainer.clientHeight)scrollContainer.scrollTo({top:Math.max(0,top-10),behavior:force?'instant':'smooth'});}
   if(changed||force)this.viewportWidth=viewport.clientWidth;
   if(force||x<viewport.scrollLeft+10||x>viewport.scrollLeft+this.viewportWidth-25)viewport.scrollLeft=Math.max(0,x-this.viewportWidth*.3);
  }
 }
 markLoop(range){for(const [index,entry] of this.entries)entry.button.classList.toggle('in-loop',!!range&&index>=range.a-1&&index<range.b);}
}
