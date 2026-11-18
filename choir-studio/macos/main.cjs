const {app,BrowserWindow,protocol,net,Menu}=require('electron');
const path=require('node:path');
const {pathToFileURL}=require('node:url');

protocol.registerSchemesAsPrivileged([{scheme:'choir',privileges:{
  standard:true,secure:true,supportFetchAPI:true,stream:true
}}]);

let window;
function openWindow(){
  window=new BrowserWindow({width:1360,height:900,minWidth:840,minHeight:640,
    title:'和声练习室',backgroundColor:'#10151e',
    webPreferences:{contextIsolation:true,nodeIntegration:false,sandbox:true}});
  window.webContents.setWindowOpenHandler(()=>({action:'deny'}));
  window.webContents.on('will-navigate',(event,url)=>{
    if(new URL(url).origin!==new URL('choir://app').origin||!url.startsWith('choir://app/'))event.preventDefault();
  });
  window.on('closed',()=>{window=null;});
  window.loadURL('choir://app/index.html');
}

app.whenReady().then(()=>{
  const root=app.isPackaged?path.join(process.resourcesPath,'public'):path.resolve(__dirname,'../public');
  protocol.handle('choir',request=>{
    try{
      const url=new URL(request.url);
      if(url.host!=='app'||!['GET','HEAD'].includes(request.method))return new Response('',{status:403});
      const file=path.resolve(root,'.'+decodeURIComponent(url.pathname));
      if(!file.startsWith(root+path.sep))return new Response('',{status:403});
      return net.fetch(pathToFileURL(file).toString());
    }catch{return new Response('',{status:400});}
  });
  Menu.setApplicationMenu(Menu.buildFromTemplate([
    {label:app.name,submenu:[{role:'about'},{type:'separator'},{role:'quit'}]},
    {label:'编辑',submenu:[{role:'undo'},{role:'redo'},{type:'separator'},{role:'cut'},{role:'copy'},{role:'paste'},{role:'selectAll'}]},
    {label:'窗口',submenu:[{role:'minimize'},{role:'close'}]}
  ]));
  openWindow();
  app.on('activate',()=>{if(!window)openWindow();});
});
app.on('window-all-closed',()=>{if(process.platform!=='darwin')app.quit();});
