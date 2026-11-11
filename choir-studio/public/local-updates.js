export function installLocalUpdates({document,capacitor=globalThis.Capacitor,beforeSwitch=()=>{}}){
 if(!capacitor?.isNativePlatform?.()||capacitor.getPlatform()!=='android')return;
 const $=id=>document.getElementById(id),panel=$('local-updates');
 if(!panel)return;
 panel.hidden=false;
 const call=(method,options={})=>capacitor.nativePromise('LocalUpdates',method,options);
 const status=$('update-status'),source=$('update-source'),check=$('update-check'),apply=$('update-apply'),restore=$('update-restore');
 let candidate=null,busy=false,poll=null,sharing=false,sharePoll=null;
 const message=text=>{status.textContent=text;};
 const lock=value=>{busy=value;check.disabled=value||sharing;apply.disabled=value||sharing;restore.disabled=value||sharing;source.disabled=value||sharing;};
 const clearCandidate=()=>{candidate=null;apply.hidden=true;};
 const failure=error=>message(`${error?.message||'操作失败，请重试'}。原有内容仍可离线使用。`);
 source.addEventListener('input',clearCandidate);
 document.addEventListener('choir-ready',()=>{call('ready').catch(()=>{});},{once:true});
 const renderShare=info=>{
  const share=$('offline-share');if(!share||!info.canShare)return;
  share.hidden=false;sharing=!!info.sharing;lock(busy);
  $('share-start').hidden=sharing;$('share-stop').hidden=!sharing;
  $('share-status').textContent=info.shareError||(sharing?'正在分享当前版本。请让对方连接你的热点，并使用下方热点网卡的地址。30 分钟后自动停止。':'尚未开启分享。先打开个人热点，再点「分享当前版本」。');
  $('share-addresses').replaceChildren();
  if(sharing)for(const address of info.shareAddresses||[]){const line=document.createElement('p');line.textContent=address;$('share-addresses').append(line);}
  if(sharing&&!(info.shareAddresses||[]).length)$('share-addresses').textContent='暂未检测到局域网地址，请确认热点已开启。';
  if(sharing&&!sharePoll)sharePoll=setInterval(()=>call('status').then(renderShare).catch(()=>{}),2000);
  if(!sharing&&sharePoll){clearInterval(sharePoll);sharePoll=null;}
 };
 if($('share-start'))$('share-start').onclick=async()=>{
  if(busy)return;$('share-start').disabled=true;
  try{await call('startShare');renderShare(await call('status'));}
  catch(error){$('share-status').textContent=error?.message||'开启分享失败，请重试';}
  finally{$('share-start').disabled=false;}
 };
 if($('share-stop'))$('share-stop').onclick=async()=>{
  $('share-stop').disabled=true;
  try{await call('stopShare');renderShare(await call('status'));}
  catch(error){$('share-status').textContent=error?.message||'停止分享失败，请重试';}
  finally{$('share-stop').disabled=false;}
 };
 document.defaultView?.addEventListener('pagehide',()=>{clearInterval(poll);clearInterval(sharePoll);});
 call('status').then(info=>{
  source.value=info.source||'';
  message(`当前内容 ${info.version} · ${info.revision.slice(0,8)}${info.downloaded?'（已保存到手机）':'（安装版）'}`);
  renderShare(info);
 }).catch(failure);
 check.onclick=async()=>{
  if(busy)return;clearCandidate();lock(true);message('正在连接电脑并检查更新…');
  try{
   const info=await call('check',{source:source.value.trim()});
   if(info.available){candidate=info;apply.hidden=false;message(`发现更新 ${info.version} · ${info.revision.slice(0,8)}。完整内容 ${(info.bytes/1048576).toFixed(1)} MB，相同文件会直接复用。`);}
   else message('已是电脑上的最新内容，可以离线练习。');
  }catch(error){failure(error);}finally{lock(false);}
 };
 apply.onclick=async()=>{
  if(busy||!candidate)return;lock(true);message('正在保存更新，请保持与电脑连接…');
  poll=setInterval(()=>{call('status').then(info=>{if(info.total)message(`正在保存更新：${info.completed}/${info.total}。完成后将重新打开练习室。`);}).catch(()=>{});},1000);
  try{beforeSwitch();await call('install',{ticket:candidate.ticket});message('更新已保存，正在重新打开…');}
  catch(error){clearCandidate();failure(error);}
  finally{clearInterval(poll);poll=null;lock(false);}
 };
 restore.onclick=async()=>{
  if(busy)return;
  if(!globalThis.confirm('恢复此 APK 自带的内容？练习设置会保留，之后仍可重新检查更新。'))return;
  lock(true);clearCandidate();
  try{beforeSwitch();await call('restore');message('正在恢复安装版…');}catch(error){failure(error);}finally{lock(false);}
 };
 return {get busy(){return busy;}};
}
