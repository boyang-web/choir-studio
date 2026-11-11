import http from 'node:http';
import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import os from 'node:os';
import {execFile} from 'node:child_process';
import {ensureUpdateKey,createUpdateSnapshot} from './local-update-server.mjs';
function openBrowser(url){
 try {
  const report=error=>{if(error)console.log(`  Please open ${url} in your browser.`);};
  if(process.platform==='win32')execFile('cmd.exe',['/d','/c','start','',url],{windowsHide:true},report);
  else execFile(process.platform==='darwin'?'open':'xdg-open',[url],report);
 }catch{console.log(`  Please open ${url} in your browser.`);}
}
const root = path.resolve(fileURLToPath(new URL('./public/', import.meta.url)));
const port = Number(process.env.PORT || 5173);
const project=path.dirname(root),updateKey=await ensureUpdateKey(project);
let snapshot=null,refreshing=null;
const types = {'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.webp':'image/webp','.png':'image/png','.svg':'image/svg+xml','.pdf':'application/pdf','.wav':'audio/wav','.mp3':'audio/mpeg','.md':'text/plain; charset=utf-8','.apk':'application/vnd.android.package-archive','.webmanifest':'application/manifest+json'};
http.createServer(async (req,res)=>{
  try {
    let requestPath;
    try { requestPath = decodeURIComponent(new URL(req.url,'http://localhost').pathname); } catch {res.writeHead(400).end();return;}
    if(requestPath==='/local-update/manifest'){
      // Hash once per explicit check. All downloads use this immutable snapshot,
      // so changes on the computer during a download cannot mix revisions.
      refreshing ||= createUpdateSnapshot(project,updateKey).finally(()=>{refreshing=null;});
      snapshot=await refreshing;
      const body=JSON.stringify(snapshot.envelope);
      res.writeHead(200,{'Content-Type':'application/json','Cache-Control':'no-store'}).end(body);return;
    }
    if(requestPath.startsWith('/local-update/files/')){
      const digest=requestPath.slice('/local-update/files/'.length);
      const bytes=/^[a-f0-9]{64}$/.test(digest)&&snapshot?.blobs.get(digest);
      if(!bytes){res.writeHead(404).end();return;}
      res.writeHead(200,{'Content-Type':'application/octet-stream','Content-Length':bytes.length,'Cache-Control':'no-store'});
      if(req.method==='HEAD')res.end();else res.end(bytes);return;
    }
    const isApk=requestPath==='/download/choir-studio.apk';
    const file = isApk ? path.resolve(root,'../releases/choir-studio.apk') : path.resolve(root, '.' + (requestPath==='/'?'/index.html':requestPath));
    if (!isApk&&!file.startsWith(root + path.sep)) {res.writeHead(403).end();return;}
    const info = await stat(file);
    if (!info.isFile()) throw new Error('Not a file');
    res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream','Content-Length':info.size,'Cache-Control':'no-cache','X-Content-Type-Options':'nosniff',...(isApk?{'Content-Disposition':'attachment; filename="choir-studio.apk"'}:{})});
    if(req.method==='HEAD')res.end();else createReadStream(file).pipe(res);
  } catch { res.writeHead(404,{'Content-Type':'text/plain; charset=utf-8'}).end('文件未找到'); }
}).listen(port,'0.0.0.0',()=>{
 console.log(`\n  和声 · 合唱练习室\n  电脑打开：http://localhost:${port}`);
 for(const items of Object.values(os.networkInterfaces())) for(const i of items||[]) if(i.family==='IPv4'&&!i.internal)console.log(`  手机同一 Wi-Fi 打开：http://${i.address}:${port}`);
 console.log('  安卓控制台「局域网更新」填写上面的电脑地址，然后检查更新。');
 console.log('  按 Ctrl+C 关闭服务\n');
 if(process.argv.includes('--open')){
  const url=`http://localhost:${port}`;
  openBrowser(url);
 }
});
