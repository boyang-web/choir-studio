"""Fetch an attributed, small offline selection of publicly redistributed samples."""
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
import urllib.request,urllib.parse,wave,io,struct,json
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'choir-studio/public/samples';OUT.mkdir(exist_ok=True)
manifest={}
jobs=[]
for gender,folder,notes in [
 ('male','choir-MALE-normal-mod-wheel',['g2','c3','e3','g3','c4','e4','f4']),
 ('female','choir-FEMALE-sustain',['g4','c5','e5','g5','c6'])]:
 manifest[gender]=dict(type='looped-choir',samples={})
 for note in notes:
  source=f'samples/{folder}/chorus-{gender}-{note}-PB-loop.wav'
  url='https://raw.githubusercontent.com/eodowd/VirtualPlayingOrchestra/main/'+urllib.parse.quote(source,safe='/')
  jobs.append((gender,note.upper(),url,f'{gender}-{note}.wav'))
manifest['piano']=dict(type='piano',samples={})
for octave in range(2,7):
 for note in ['C','Ds','Fs','A']:
  name=f'{note}{octave}';jobs.append(('piano',name.replace('Ds','D#').replace('Fs','F#'),'https://raw.githubusercontent.com/Tonejs/audio/master/salamander/'+name+'.mp3',f'piano-{name}.mp3'))
def download(job):
 bank,note,url,name=job;p=OUT/name
 if not p.exists():
  data=urllib.request.urlopen(url,timeout=60).read()
  if data.startswith(b'version https://git-lfs'):raise ValueError('Unexpected LFS pointer: '+url)
  p.write_bytes(data)
 data=p.read_bytes();entry=dict(file=name)
 if name.endswith('.wav'):
  w=wave.open(io.BytesIO(data));rate=w.getframerate();entry['duration']=w.getnframes()/rate
  pos=12
  while pos+8<=len(data):
   size=struct.unpack_from('<I',data,pos+4)[0]
   if data[pos:pos+4]==b'smpl' and size>=60:
    smpl=struct.unpack_from('<15I',data,pos+8)
    if smpl[7]>0:entry.update(loopStart=smpl[11]/rate,loopEnd=(smpl[12]+1)/rate)
   pos+=8+size+(size%2)
  if 'loopStart' not in entry:raise ValueError('Missing sustained-note loop: '+name)
 manifest[bank]['samples'][note]=entry
 print(bank,note,len(data),flush=True)
with ThreadPoolExecutor(max_workers=6) as pool:list(pool.map(download,jobs))
(OUT/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
readme=urllib.request.urlopen('https://raw.githubusercontent.com/Tonejs/audio/master/salamander/README',timeout=30).read()
(OUT/'SALAMANDER-README.txt').write_bytes(readme)
(OUT/'SOURCES.md').write_text('''# Audio sample credits

## Choir
Male and female sustained choir samples from **Virtual Playing Orchestra**, by Paul Battersby; source sample contributors include Mattias Westlund. This subset is obtained from the DecentSampler conversion by **Eoin O’Dowd**. Files are unchanged and retain their WAV sustain-loop metadata.

- https://virtualplaying.com/virtual-playing-orchestra/
- https://virtualplaying.com/standard-orchestra-documentation/
- https://github.com/eodowd/VirtualPlayingOrchestra

The VPO website allows attributed modification/redistribution for personal use or free distribution and documents the respective contributing sample licenses (including CC Sampling Plus 1.0 and CC BY-SA). This app and the bundled sample subset are provided free. Do not remove credits or re-sell these samples. Consult the original licensing page before other distribution.

## Piano
**Salamander Grand Piano**, Yamaha C5 samples by **Alexander Holm**, CC BY 3.0. MP3 distribution by Tone.js. Original README included alongside this notice.

- https://github.com/Tonejs/audio/tree/master/salamander
- https://creativecommons.org/licenses/by/3.0/

The samples are instrumental/choir vowel samples; they do not synthesize lyrics.
''',encoding='utf8')
print('Offline sample banks ready',flush=True)
