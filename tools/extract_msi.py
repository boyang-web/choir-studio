import ctypes as c, pathlib, json, subprocess
root=pathlib.Path(__file__).resolve().parent
m=c.WinDLL('msi'); H=c.c_uint
db=H(); assert m.MsiOpenDatabaseW(str(root/'audiveris.msi'),None,c.byref(db))==0
def query(sql):
 v=H(); assert m.MsiDatabaseOpenViewW(db,c.c_wchar_p(sql),c.byref(v))==0
 assert m.MsiViewExecute(v,0)==0
 while True:
  r=H()
  if m.MsiViewFetch(v,c.byref(r)): break
  yield r
 m.MsiCloseHandle(v)
def string(r,i):
 b=c.create_unicode_buffer(2048);n=H(2048);m.MsiRecordGetStringW(r,i,b,c.byref(n));return b.value
for r in query('SELECT `Name`, `Data` FROM `_Streams`'):
 name=string(r,1)
 if name.endswith('.cab'):
  with open(root/'payload.cab','wb') as f:
   while True:
    b=c.create_string_buffer(1048576);n=H(len(b));assert m.MsiRecordReadStream(r,2,b,c.byref(n))==0
    if not n.value:break
    f.write(b.raw[:n.value])
 m.MsiCloseHandle(r)
files={}
for r in query('SELECT `File`, `Component_`, `FileName` FROM `File`'):
 files[string(r,1)]=(string(r,2),string(r,3).split('|')[-1]);m.MsiCloseHandle(r)
components={}
for r in query('SELECT `Component`, `Directory_` FROM `Component`'):
 components[string(r,1)]=string(r,2);m.MsiCloseHandle(r)
dirs={}
for r in query('SELECT `Directory`, `Directory_Parent`, `DefaultDir` FROM `Directory`'):
 dirs[string(r,1)]=(string(r,2),string(r,3).split('|')[-1]);m.MsiCloseHandle(r)
def path(d):
 parent,name=dirs[d]
 if not parent:return pathlib.Path()
 return path(parent)/(name if name not in ('.','SourceDir') else '')
raw=root/'raw';raw.mkdir(exist_ok=True)
subprocess.run(['expand.exe',str(root/'payload.cab'),'-F:*',str(raw)],stdout=subprocess.DEVNULL,check=True)
out=root/'audiveris';out.mkdir(exist_ok=True)
for k,(comp,name) in files.items():
 p=out/path(components[comp])/name;p.parent.mkdir(parents=True,exist_ok=True)
 (raw/k).replace(p)
print('Extracted',len(files),'files into',out)
