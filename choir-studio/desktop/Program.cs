using System;
using System.IO;
using System.IO.Compression;
using System.Drawing;
using System.Reflection;
using System.Runtime.CompilerServices;
using System.Runtime.InteropServices;
using System.Threading.Tasks;
using System.Windows.Forms;
using Microsoft.Web.WebView2.Core;
using Microsoft.Web.WebView2.WinForms;

[assembly: AssemblyTitle("和声练习室")]
[assembly: AssemblyProduct("和声练习室")]
[assembly: AssemblyVersion("1.8.0.0")]
static class Program {
 internal static string DataDirectory;
 internal static string AssetsDirectory;
 internal static bool Qa;
 [DllImport("kernel32.dll", CharSet=CharSet.Unicode)] static extern bool SetDllDirectory(string path);
 [STAThread] static void Main(string[] args) {
  Application.EnableVisualStyles();Application.SetCompatibleTextRenderingDefault(false);
  try {
   DataDirectory=Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),"HeshengChoir");
   for(int i=0;i<args.Length;i++){if(args[i]=="--qa")Qa=true;if(args[i]=="--data-dir"&&i+1<args.Length)DataDirectory=Path.GetFullPath(args[++i]);}
   Directory.CreateDirectory(DataDirectory);
   using(var payload=Assembly.GetExecutingAssembly().GetManifestResourceStream("ChoirPayload")){
    string digest;using(var sha=System.Security.Cryptography.SHA256.Create())digest=BitConverter.ToString(sha.ComputeHash(payload)).Replace("-","").Substring(0,16);
    payload.Position=0;AssetsDirectory=Path.Combine(DataDirectory,"versions","1.8.0-"+digest);string marker=Path.Combine(AssetsDirectory,"ready");
    if(!File.Exists(marker)){
     Directory.CreateDirectory(AssetsDirectory);string prefix=Path.GetFullPath(AssetsDirectory)+Path.DirectorySeparatorChar;
     using(var archive=new ZipArchive(payload,ZipArchiveMode.Read,true))foreach(var entry in archive.Entries){
      string target=Path.GetFullPath(Path.Combine(AssetsDirectory,entry.FullName));if(!target.StartsWith(prefix,StringComparison.OrdinalIgnoreCase))throw new IOException("Invalid resource path");
      if(String.IsNullOrEmpty(entry.Name)){Directory.CreateDirectory(target);continue;}
      Directory.CreateDirectory(Path.GetDirectoryName(target));using(var input=entry.Open())using(var output=File.Create(target))input.CopyTo(output);
     }
     File.WriteAllText(marker,digest);
    }
   }
   SetDllDirectory(AssetsDirectory);
   AppDomain.CurrentDomain.AssemblyResolve+=(sender,e)=>{
    string name=new AssemblyName(e.Name).Name;if(name!="Microsoft.Web.WebView2.Core"&&name!="Microsoft.Web.WebView2.WinForms")return null;
    return Assembly.LoadFrom(Path.Combine(AssetsDirectory,name+".dll"));
   };
   Run();Environment.Exit(Environment.ExitCode);
  }catch(Exception e){File.WriteAllText(Path.Combine(DataDirectory,"startup-error.txt"),e.ToString());MessageBox.Show("启动失败："+e.Message+"\n\n请确认 Windows 已安装 Microsoft Edge WebView2 Runtime。", "和声练习室",MessageBoxButtons.OK,MessageBoxIcon.Error);Environment.ExitCode=1;}
 }
 [MethodImpl(MethodImplOptions.NoInlining)] static void Run(){Application.Run(new ChoirWindow());}
}
class ChoirWindow:Form {
 WebView2 web;Label loading;
 [DllImport("dwmapi.dll")] static extern int DwmSetWindowAttribute(IntPtr window,int attribute,ref int value,int size);
 public ChoirWindow(){
  Text="和声练习室";ClientSize=new Size(1360,900);MinimumSize=new Size(840,640);StartPosition=FormStartPosition.CenterScreen;BackColor=Color.FromArgb(16,21,30);
  using(var stream=Assembly.GetExecutingAssembly().GetManifestResourceStream("ChoirIcon"))if(stream!=null)Icon=new Icon(stream);
  loading=new Label{Text="正在打开练习室…",Dock=DockStyle.Fill,TextAlign=ContentAlignment.MiddleCenter,ForeColor=Color.LightSteelBlue,Font=new Font("Microsoft YaHei",14)};Controls.Add(loading);
  if(Program.Qa){Opacity=0;ShowInTaskbar=false;}
  Shown+=async(sender,e)=>await Open();
  FormClosed+=(sender,e)=>{if(web!=null)web.Dispose();};
 }
 protected override void OnHandleCreated(EventArgs e){base.OnHandleCreated(e);try{int dark=1;DwmSetWindowAttribute(Handle,20,ref dark,4);}catch{}}
 async Task Open(){
  try{
   web=new WebView2{Dock=DockStyle.Fill,DefaultBackgroundColor=BackColor};Controls.Add(web);
   var options=new CoreWebView2EnvironmentOptions(Program.Qa?"--remote-debugging-port=9334 --autoplay-policy=no-user-gesture-required":null);
   var environment=await CoreWebView2Environment.CreateAsync(null,Path.Combine(Program.DataDirectory,"profile"),options);
   await web.EnsureCoreWebView2Async(environment);
   web.CoreWebView2.SetVirtualHostNameToFolderMapping("choir.local",Path.Combine(Program.AssetsDirectory,"public"),CoreWebView2HostResourceAccessKind.DenyCors);
   web.CoreWebView2.Settings.IsZoomControlEnabled=false;web.CoreWebView2.Settings.IsStatusBarEnabled=false;
   await web.CoreWebView2.AddScriptToExecuteOnDocumentCreatedAsync("window.choirDesktop=true;");
   web.CoreWebView2.NewWindowRequested+=(sender,e)=>{e.Handled=true;};
   web.CoreWebView2.NavigationCompleted+=async(sender,e)=>{if(e.IsSuccess){loading.Hide();web.BringToFront();if(Program.Qa)await Verify();}else loading.Text="页面打开失败，请关闭后重试。";};
   web.CoreWebView2.Navigate("https://choir.local/index.html");
  }catch(Exception e){File.WriteAllText(Path.Combine(Program.DataDirectory,"startup-error.txt"),e.ToString());loading.Text="无法启动浏览器内核。请安装微软 WebView2 Runtime 后重试。\n"+e.Message;Environment.ExitCode=1;if(Program.Qa)Close();}
 }
 async Task Verify(){
  try{
   for(int i=0;i<100;i++){if(await web.CoreWebView2.ExecuteScriptAsync("!!document.querySelector('#play:not(:disabled)')")=="true")break;await Task.Delay(200);}
   await web.CoreWebView2.ExecuteScriptAsync(@"window.desktopQa={};document.querySelector('#zoom-in').click();desktopQa.zoom=document.querySelector('#zoom-label').textContent;document.querySelector('#fit-score').click();desktopQa.fit=document.querySelector('#zoom-label').textContent;desktopQa.pages=document.querySelectorAll('.page-wrapper').length;document.querySelector('[data-song=let-it-go]').click();");
   await Task.Delay(1500);
   await web.CoreWebView2.ExecuteScriptAsync("document.querySelector('#seek').value=125;document.querySelector('#seek').dispatchEvent(new Event('input'));document.querySelector('#play').click();");
   for(int i=0;i<150;i++){if(await web.CoreWebView2.ExecuteScriptAsync("!!(window.Tone&&Tone.getTransport().state==='started')")=="true")break;await Task.Delay(200);}
   await web.CoreWebView2.ExecuteScriptAsync("window.desktopAnalyser=new Tone.Analyser('waveform',2048);Tone.getDestination().connect(desktopAnalyser);");await Task.Delay(3000);
   string report=await web.CoreWebView2.ExecuteScriptAsync("desktopQa.audio=Array.from(desktopAnalyser.getValue()).some(v=>Math.abs(v)>.00001);desktopQa.state=Tone.getTransport().state;desktopQa.song=document.querySelector('#song-title').textContent;desktopQa.scheme=location.protocol;desktopQa.native=window.choirDesktop;document.querySelector('#play').click();desktopQa;");
   File.WriteAllText(Path.Combine(Program.DataDirectory,"qa-report.json"),report);
   using(var output=File.Create(Path.Combine(Program.DataDirectory,"desktop.png")))await web.CoreWebView2.CapturePreviewAsync(CoreWebView2CapturePreviewImageFormat.Png,output);
   if(!report.Contains("\"audio\":true"))Environment.ExitCode=2;
  }catch(Exception e){File.WriteAllText(Path.Combine(Program.DataDirectory,"qa-error.txt"),e.ToString());Environment.ExitCode=1;}
  Close();
 }
}
