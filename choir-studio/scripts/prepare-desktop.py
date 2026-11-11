"""Bundle static assets and the official WebView2 SDK for a portable Windows EXE."""
from pathlib import Path
import zipfile,urllib.request
from PIL import Image,ImageDraw,ImageFont
project=Path(__file__).resolve().parents[1];workspace=project.parent
sdk=workspace/'tools/webview2';sdk.mkdir(parents=True,exist_ok=True)
files=['lib/net462/Microsoft.Web.WebView2.Core.dll','lib/net462/Microsoft.Web.WebView2.WinForms.dll','runtimes/win-x64/native/WebView2Loader.dll','LICENSE.txt']
if not all((sdk/f).exists() for f in files):
 urllib.request.urlretrieve('https://api.nuget.org/v3-flatcontainer/microsoft.web.webview2/1.0.4258.31/microsoft.web.webview2.1.0.4258.31.nupkg',sdk/'sdk.zip')
 with zipfile.ZipFile(sdk/'sdk.zip') as z:
  for f in files:z.extract(f,sdk)
out=project/'desktop/build';out.mkdir(parents=True,exist_ok=True)
with zipfile.ZipFile(out/'payload.zip','w',zipfile.ZIP_DEFLATED,compresslevel=6) as z:
 for f in (project/'public').rglob('*'):
  if f.is_file() and 'designs' not in f.relative_to(project/'public').parts:z.write(f,'public/'+f.relative_to(project/'public').as_posix())
 for f in files:z.write(sdk/f,Path(f).name)
image=Image.new('RGBA',(256,256),'#10151e');draw=ImageDraw.Draw(image)
draw.rounded_rectangle((12,12,244,244),radius=62,fill='#385776',outline='#9ebee5',width=3)
font=ImageFont.truetype('C:/Windows/Fonts/georgiai.ttf',210)
draw.text((52,-10),'h',font=font,fill='#edf4ff');draw.ellipse((174,48,205,79),fill='#b6d8ff')
image.save(out/'choir.ico',sizes=[(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)])
print('Desktop payload ready:',round((out/'payload.zip').stat().st_size/1024/1024,2),'MiB')
