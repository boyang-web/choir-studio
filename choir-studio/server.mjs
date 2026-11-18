import http from 'node:http';
import { createReadStream } from 'node:fs';
import { stat } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';
import {execFile} from 'node:child_process';
function openBrowser(url){
 try {
  const report=error=>{if(error)console.log(`  Please open ${url} in your browser.`);};
  if(process.platform==='win32')execFile('cmd.exe',['/d','/c','start','',url],{windowsHide:true},report);
  else execFile(process.platform==='darwin'?'open':'xdg-open',[url],report);
 }catch{console.log(`  Please open ${url} in your browser.`);}
}
const root = path.resolve(fileURLToPath(new URL('./public/', import.meta.url)));
const port = Number(process.env.PORT || 5173);
const types = {'.html':'text/html; charset=utf-8','.js':'text/javascript; charset=utf-8','.css':'text/css; charset=utf-8','.json':'application/json; charset=utf-8','.webp':'image/webp','.png':'image/png','.svg':'image/svg+xml','.pdf':'application/pdf','.wav':'audio/wav','.mp3':'audio/mpeg','.md':'text/plain; charset=utf-8','.apk':'application/vnd.android.package-archive','.webmanifest':'application/manifest+json'};
http.createServer(async (req,res)=>{
  try {
    let requestPath;
    try { requestPath = decodeURIComponent(new URL(req.url,'http://localhost').pathname); } catch {res.writeHead(400).end();return;}
    const file = path.resolve(root, '.' + (requestPath==='/'?'/index.html':requestPath));
    if (!file.startsWith(root + path.sep)) {res.writeHead(403).end();return;}
    const info = await stat(file);
    if (!info.isFile()) throw new Error('Not a file');
    res.writeHead(200,{'Content-Type':types[path.extname(file)]||'application/octet-stream','Content-Length':info.size,'Cache-Control':'no-cache','X-Content-Type-Options':'nosniff'});
    if(req.method==='HEAD')res.end();else createReadStream(file).pipe(res);
  } catch { res.writeHead(404,{'Content-Type':'text/plain; charset=utf-8'}).end('文件未找到'); }
}).listen(port,'127.0.0.1',()=>{
 console.log(`\n  和声 · 合唱练习室\n  电脑打开：http://localhost:${port}`);
 console.log('  按 Ctrl+C 关闭服务\n');
 if(process.argv.includes('--open')){
  const url=`http://localhost:${port}`;
  openBrowser(url);
 }
});
