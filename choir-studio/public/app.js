import {ChoirAudio} from './audio-engine.js';
import {clamp,measureAt,loopRange,cursorX,formatTime} from './score-utils.js';
import {defaultSound} from './instruments.js';
import {installScoreZoom} from './score-zoom.js';
import {readPerformance} from './midi-performance.js';
import {installLocalUpdates} from './local-updates.js';
const $=id=>document.getElementById(id);
const engine=new ChoirAudio();
installLocalUpdates({document,beforeSwitch:()=>{engine.pause();updatePlay();}});
const colors=[['#e4eee3','#72906b'],['#e8e7f0','#9185a7'],['#e5edf2','#7393a5'],['#f0e8dc','#a89370'],['#e4ece9','#75978a'],['#eee8df','#a19079']];
let catalog=[],song=null,settings={},zoom=100,activeMeasure=-1,activeFrame=null,loading=0,starting=false,toastTimer;
let prefs={};try{prefs=JSON.parse(localStorage.getItem('choir-prefs')||'{}');}catch{}
zoom=clamp(Number(prefs.pageZoom)||100,25,400);
function save(){try{localStorage.setItem('choir-prefs',JSON.stringify(prefs));}catch{}}
function toast(message){$('toast').textContent=message;$('toast').classList.add('visible');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.remove('visible'),2600);}
function escape(s){return String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));}
function updatePlay(){const on=engine.playing;$('play').setAttribute('aria-label',on?'暂停':'播放');$('play').innerHTML=on?'<svg viewBox="0 0 24 24"><path d="M7 5h4v14H7zm6 0h4v14h-4z"/></svg>':'<svg viewBox="0 0 24 24"><path d="M8 5v14l11-7z"/></svg>';}
function makeLibrary(){
 $('library').innerHTML=catalog.map(s=>`<button class="song-card ${s.id==='let-it-go'?'ice':''} ${song?.id===s.id?'active':''}" data-song="${s.id}" aria-pressed="${song?.id===s.id}"><span class="cover">${s.id==='let-it-go'?'❆':escape(s.title.slice(0,1))}</span><span><strong>${escape(s.title)}</strong><small>${escape(s.tag)} · ${s.pages} 页原谱</small></span>${song?.id===s.id?'<span class="playing-mark">≋</span>':''}</button>`).join('');
 for(const b of $('library').querySelectorAll('button'))b.onclick=()=>{loadSong(b.dataset.song);closeMenu();};
}
async function loadSong(id){
 const request=++loading;
 engine.pause();$('play').disabled=true;updatePlay();$('score-content').innerHTML='<p class="loading">正在打开乐谱…</p>';
 try{
  const response=await fetch(`songs/${id}/song.json`);if(!response.ok)throw new Error('歌曲文件读取失败');
  const data=await response.json();
  const midiResponse=await fetch(`songs/${id}/${data.midi.file}`);if(!midiResponse.ok)throw new Error('MIDI unavailable');
  readPerformance(data,await midiResponse.arrayBuffer());if(request!==loading)return;
  song=data;settings={};
  const stored=prefs[id]?.voices||{};
  const migrate=prefs[id]?.performanceVersion!==2;
  for(const p of song.parts)settings[p.id]={enabled:migrate&&song.id==='let-it-go'?p.id!=='piano':stored[p.id]?.enabled??(p.id!=='percussion'),volume:clamp(stored[p.id]?.volume??(p.id==='piano'?.45:.85),0,1),sound:defaultSound(p.id),branches:Object.fromEntries((p.branches||[]).map(b=>[b.id,stored[p.id]?.branches?.[b.id]!==false]))};
  engine.load(song,settings);engine.setVolume(Number($('master-volume').value));engine.metro=$('metronome').checked;
  prefs.lastSong=id;save();
  $('song-title').textContent=song.title;$('song-subtitle').textContent=song.subtitle;
  $('player-title').textContent=song.title;$('album-mini').textContent=id==='let-it-go'?'❆':song.title.slice(0,1);$('album-mini').classList.toggle('ice',id==='let-it-go');
  $('download-score').href=`songs/${id}/score.pdf`;
  $('seek').max=song.duration;$('seek').value=0;$('total-time').textContent=formatTime(song.duration/engine.rate);
  $('loop-start').max=song.measures.length;$('loop-end').max=song.measures.length;$('loop-start').value=1;$('loop-end').value=Math.min(4,song.measures.length);$('loop-enabled').checked=false;
  $('source-info').textContent=`${song.pages.length} 页 · ${song.measures.length} 小节 · ♩ = ${song.tempo}`;
  makeLibrary();makeVoices();renderScore();$('score-scroll').scrollTop=0;$('score-scroll').scrollLeft=0;
  $('play').disabled=false;updatePosition(0,true);
  document.dispatchEvent(new document.defaultView.Event('choir-ready'));
 }catch(error){if(request!==loading)return;console.error(error);$('score-content').innerHTML='<p class="loading error">乐谱加载失败，请重新打开应用。</p>';toast('加载失败，请重试');}
}
function makeVoices(){
 $('voices').innerHTML=song.parts.map((p,i)=>{
  const s=settings[p.id],c=colors[i%colors.length];
  const branches=(p.branches||[]).map(b=>`<div class="branch-row"><label><input type="checkbox" data-branch="${b.id}" data-parent="${p.id}" aria-label="播放${b.name}" ${s.branches[b.id]?'checked':''}>${escape(b.name)}</label><button data-branch-solo="${b.id}" data-parent="${p.id}" aria-label="独听${b.name}">独听</button></div>`).join('');
  return `<div class="voice-row ${s.enabled?'':'muted'}" data-part="${p.id}" style="--voice-bg:${c[0]};--voice-color:${c[1]}"><div class="voice-top"><span class="voice-letter">${p.letter}</span><div class="voice-name"><strong>${escape(p.name)}</strong></div><button class="solo-button" data-solo="${p.id}" aria-label="独听${p.name}" aria-pressed="false">独听</button><input class="voice-toggle" type="checkbox" role="switch" data-toggle="${p.id}" aria-label="播放${p.name}" ${s.enabled?'checked':''}></div><div class="voice-bottom"><input type="range" min="0" max="1" step=".01" value="${s.volume}" data-volume="${p.id}" aria-label="${p.name}音量"><span>${Math.round(s.volume*100)}%</span></div>${branches?`<div class="branch-controls">${branches}</div>`:''}</div>`;
 }).join('');
 for(const control of $('voices').querySelectorAll('[data-toggle]'))control.onchange=()=>{const s=settings[control.dataset.toggle];s.enabled=control.checked;if(s.enabled&&!Object.values(s.branches).some(Boolean))for(const key of Object.keys(s.branches))s.branches[key]=true;applyVoices();};
 for(const control of $('voices').querySelectorAll('[data-volume]'))control.oninput=()=>{settings[control.dataset.volume].volume=Number(control.value);control.nextElementSibling.textContent=`${Math.round(Number(control.value)*100)}%`;persistVoices();engine.apply(settings);};
 for(const control of $('voices').querySelectorAll('[data-solo]'))control.onclick=()=>{const id=control.dataset.solo;const solo=Object.entries(settings).filter(([,v])=>v.enabled).length===1&&settings[id].enabled;for(const [k,v]of Object.entries(settings))v.enabled=solo||k===id;applyVoices();toast(solo?'恢复全声部':`正在独听${song.parts.find(p=>p.id===id).name}`);};
 for(const control of $('voices').querySelectorAll('[data-branch]'))control.onchange=()=>{const s=settings[control.dataset.parent];s.branches[control.dataset.branch]=control.checked;s.enabled=Object.values(s.branches).some(Boolean);applyVoices();};
 for(const control of $('voices').querySelectorAll('[data-branch-solo]'))control.onclick=()=>{const id=control.dataset.parent,branch=control.dataset.branchSolo;for(const [k,v]of Object.entries(settings))v.enabled=k===id;for(const key of Object.keys(settings[id].branches))settings[id].branches[key]=key===branch;applyVoices();};
 applyVoices();
}
function persistVoices(){prefs[song.id]={...prefs[song.id],voices:settings,performanceVersion:2};save();}
function applyVoices(){
 engine.apply(settings);persistVoices();
 const enabled=Object.keys(settings).filter(id=>settings[id].enabled);
 for(const row of $('voices').querySelectorAll('[data-part]')){
  const id=row.dataset.part,on=settings[id].enabled,solo=enabled.length===1&&on;
  row.classList.toggle('muted',!on);row.querySelector('[data-toggle]').checked=on;const b=row.querySelector('[data-solo]');b.classList.toggle('active',solo);b.setAttribute('aria-pressed',solo);
  for(const checkbox of row.querySelectorAll('[data-branch]'))checkbox.checked=settings[id].branches[checkbox.dataset.branch]!==false;
 }
 $('all-voices').classList.toggle('selected',enabled.length===song.parts.length);$('no-voices').classList.toggle('selected',enabled.length===0);
 $('player-voices').textContent=enabled.length===0?'全部静音':enabled.length===1?`${song.parts.find(p=>p.id===enabled[0]).name} · 独听`:enabled.length===song.parts.length?'全部声部':`${enabled.length} 个声部`;
}
function renderScore(anchor){
 if(!song)return;
 activeMeasure=-1;activeFrame=null;
 const base=`songs/${song.id}/`;
 $('score-content').style.width=`${zoom}%`;
  $('score-content').innerHTML=song.pages.map((p,i)=>`<article class="page-wrapper" data-page="${i}" style="aspect-ratio:${p.width}/${p.height}"><img class="score-image" src="${base+(p.svg||p.image)}" alt="${escape(song.title)} 原谱第 ${i+1} 页" loading="${i===0?'eager':'lazy'}" width="${p.width}" height="${p.height}">${song.measures.filter(m=>m.page===i).map(m=>{const sys=song.systems[m.system];return measureButton(m,m.left/p.width,(m.right-m.left)/p.width,sys.y/p.height,sys.height/p.height);}).join('')}<div class="score-cursor" hidden></div></article>`).join('');
  for(const b of $('score-content').querySelectorAll('[data-measure]'))b.onclick=()=>seek(song.measures[Number(b.dataset.measure)].time,true);
 $('zoom-label').textContent=`${zoom}%`;
 $('zoom-out').disabled=zoom<=25;$('zoom-in').disabled=zoom>=400;
 markLoop();updatePosition(engine.position,!anchor);
 if(anchor){const page=$('score-content').querySelector(`[data-page="${anchor.page}"]`);if(page){const sc=$('score-scroll');sc.scrollTop=page.offsetTop+page.clientHeight*anchor.y-anchor.screenY;sc.scrollLeft=page.clientWidth*anchor.x-anchor.screenX;}}
}
function readingWidth(){
 const padding=window.getComputedStyle($('score-content'));
 return Math.max(180,($('score-scroll').clientWidth||Math.max(280,window.innerWidth-60))-(parseFloat(padding.paddingLeft)||0)-(parseFloat(padding.paddingRight)||0));
}
function measureButton(m,left,width,top=0,height=1){return `<button class="measure-hit" data-measure="${m.index}" style="left:${left*100}%;width:${width*100}%;top:${top*100}%;height:${height*100}%" aria-label="从第${m.label}小节播放" title="第 ${m.label} 小节"></button>`;}
function updatePosition(time,force=false){
 if(!song)return;
 const m=measureAt(song.measures,time);const sys=song.systems[m.system];
 const clockText=formatTime(time/engine.rate);if($('current-time').textContent!==clockText)$('current-time').textContent=clockText;
 if(force||!updatePosition.lastControl||performance.now()-updatePosition.lastControl>100){$('seek').value=time;updatePosition.lastControl=performance.now();}
 const change=m.index!==activeMeasure;
 if(change||force){
  $('measure-status').textContent=`第 ${m.label} / ${song.measures.length} 小节`;
  $('score-content').querySelector('.measure-hit.current')?.classList.remove('current');
  $('score-content').querySelector(`[data-measure="${m.index}"]`)?.classList.add('current');
  const frame=$('score-content').querySelector(`[data-page="${m.page}"]`);
  if(activeFrame!==frame){activeFrame?.querySelector('.score-cursor')?.setAttribute('hidden','');activeFrame=frame;}
  if(activeFrame)activeFrame.scoreWidth=activeFrame.clientWidth;
  if((engine.playing||force)&&$('follow').checked&&frame&&(force||!zoomControls.browsing)){
   const target=frame;const sc=$('score-scroll');
   const targetTop=target.offsetTop+sys.y/song.pages[m.page].height*target.clientHeight;
   const targetHeight=sys.height/song.pages[m.page].height*target.clientHeight;
   if(force||targetTop<sc.scrollTop||targetTop+Math.min(targetHeight,sc.clientHeight)>sc.scrollTop+sc.clientHeight)sc.scrollTo({top:Math.max(0,targetTop-14),behavior:force?'instant':'smooth'});
  }
  activeMeasure=m.index;
 }
 if(activeFrame){
  const cursor=activeFrame.querySelector('.score-cursor');cursor.hidden=false;const x=cursorX(m,time);
  const p=song.pages[m.page];cursor.style.transform=`translate3d(${x/p.width*activeFrame.scoreWidth}px,0,0)`;if(change||force){cursor.style.top=`${sys.y/p.height*100}%`;cursor.style.height=`${sys.height/p.height*100}%`;}
  if($('follow').checked&&engine.playing&&!zoomControls.browsing&&zoom>100){const sc=$('score-scroll');const xPx=x/p.width*activeFrame.scoreWidth;if(xPx>sc.scrollLeft+sc.clientWidth-30||xPx<sc.scrollLeft)sc.scrollLeft=Math.max(0,xPx-sc.clientWidth*.25);}
 }
}
function seek(seconds,force=false){if(!song)return;engine.seek(clamp(seconds,0,song.duration));updatePosition(engine.position,force);}
function adjustLoop(){
 if(!song)return;
 const range=loopRange(song,$('loop-start').value,$('loop-end').value);$('loop-start').value=range.a;$('loop-end').value=range.b;
 engine.setLoop($('loop-enabled').checked?range:null);markLoop();
 if(engine.loop&&(engine.position<range.start||engine.position>=range.end))seek(range.start,true);
}
function markLoop(){
 if(!song)return;const range=engine.loop;
 for(const b of $('score-content').querySelectorAll('[data-measure]')){const i=Number(b.dataset.measure);b.classList.toggle('in-loop',!!range&&i>=range.a-1&&i<range.b);}
}
async function togglePlay(){
 if(!song||starting)return;
 if(engine.playing){engine.pause();updatePlay();return;}
 starting=true;$('play').disabled=true;
 if(Tone.ToneAudioBuffer)toast('正在准备播放…');
 try{
  if(engine.position>=song.duration-.02)engine.seek(engine.loop?.start||0);
  if(engine.loop&&(engine.position<engine.loop.start||engine.position>=engine.loop.end))engine.seek(engine.loop.start);
  await engine.play(song,settings);engine.setVolume(Number($('master-volume').value));engine.setLoop(engine.loop);updatePlay();
  if(!Object.values(settings).some(v=>v.enabled))toast('当前全部静音，请开启一个声部');
 }catch(error){console.error(error);toast('播放启动失败，请重新打开应用');}
 finally{starting=false;$('play').disabled=false;}
}
function stepMeasure(delta){if(!song)return;const m=measureAt(song.measures,engine.position);seek(song.measures[clamp(m.index+delta,0,song.measures.length-1)].time,true);}
function tick(){
 if(song&&engine.playing&&!zoomControls.pinching){const time=engine.audiblePosition;if(time>=song.duration&&!engine.loop){engine.pause();engine.seek(song.duration);updatePlay();updatePosition(song.duration);toast('播放结束');}else updatePosition(time);}
 requestAnimationFrame(tick);
}
$('play').onclick=togglePlay;$('previous').onclick=()=>stepMeasure(-1);$('next').onclick=()=>stepMeasure(1);$('restart').onclick=()=>seek(engine.loop?.start||0,true);
$('seek').oninput=()=>seek(Number($('seek').value),true);
$('speed').onchange=()=>{engine.setRate(Number($('speed').value));prefs.speed=engine.rate;save();if(song){$('total-time').textContent=formatTime(song.duration/engine.rate);updatePosition(engine.position);}};
$('master-volume').oninput=()=>{engine.setVolume(Number($('master-volume').value));prefs.volume=Number($('master-volume').value);$('master-volume-value').textContent=`${Math.round(prefs.volume*100)}%`;save();};
$('metronome').onchange=()=>{engine.metro=$('metronome').checked;};
$('expressive').onchange=()=>engine.setExpressive($('expressive').checked);
$('all-voices').onclick=()=>{if(song){for(const v of Object.values(settings)){v.enabled=true;for(const key of Object.keys(v.branches))v.branches[key]=true;}applyVoices();}};
$('no-voices').onclick=()=>{if(song){for(const v of Object.values(settings))v.enabled=false;applyVoices();}};
for(const id of ['loop-start','loop-end','loop-enabled'])$(id).onchange=adjustLoop;
const zoomControls=installScoreZoom({getZoom:()=>zoom,onZoom:(value,anchor)=>{zoom=value;prefs.pageZoom=zoom;save();renderScore(anchor);}});
$('menu').onclick=()=>{$('sidebar').classList.add('open');$('shade').hidden=false;$('menu').setAttribute('aria-expanded','true');};
function closeMenu(){$('sidebar').classList.remove('open');$('shade').hidden=true;$('menu').setAttribute('aria-expanded','false');}
$('shade').onclick=closeMenu;
function closeMixer(){$('mixer').classList.remove('open');$('mixer-shade').hidden=true;$('mixer-toggle').setAttribute('aria-expanded','false');}
$('mixer-toggle').onclick=()=>{$('mixer').classList.add('open');$('mixer-shade').hidden=false;$('mixer-toggle').setAttribute('aria-expanded','true');};
$('mixer-close').onclick=closeMixer;$('mixer-shade').onclick=closeMixer;
document.addEventListener('keydown',event=>{if(event.key==='Escape'){closeMenu();closeMixer();return;}if(['INPUT','SELECT','TEXTAREA','BUTTON','A'].includes(event.target.tagName))return;if(event.code==='Space'){event.preventDefault();togglePlay();}if(event.key==='ArrowLeft'){event.preventDefault();stepMeasure(-1);}if(event.key==='ArrowRight'){event.preventDefault();stepMeasure(1);}});
document.addEventListener('visibilitychange',()=>{if(!document.hidden&&song)updatePosition(engine.position,true);});
window.addEventListener('pagehide',()=>{engine.pause();clearTimeout(toastTimer);clearTimeout(resizeTimer);});
let resizeTimer,lastReadingWidth=0;
function handleResize(){const width=readingWidth();if(Math.abs(width-lastReadingWidth)<2)return;lastReadingWidth=width;clearTimeout(resizeTimer);resizeTimer=setTimeout(()=>{if(song)renderScore();},100);}
if(window.ResizeObserver)new ResizeObserver(handleResize).observe($('score-scroll'));
else window.addEventListener('resize',handleResize);
async function start(){
 if(window.Capacitor?.isNativePlatform?.()){
  $('download-score').hidden=true;
 }
 try{const response=await fetch('songs/catalog.json');if(!response.ok)throw new Error();catalog=await response.json();makeLibrary();
 if(prefs.speed&&[.5,.65,.75,.85,1,1.15,1.25].includes(prefs.speed)){$('speed').value=prefs.speed;engine.setRate(prefs.speed);}
 if(Number.isFinite(prefs.volume))$('master-volume').value=clamp(prefs.volume,0,4);
 $('master-volume-value').textContent=`${Math.round(Number($('master-volume').value)*100)}%`;
 await loadSong(catalog.some(s=>s.id===prefs.lastSong)?prefs.lastSong:catalog[0].id);
 }catch{$('score-content').innerHTML='<p class="loading error">曲库加载失败，请重新打开应用。</p>';}
 requestAnimationFrame(tick);
}
start();
