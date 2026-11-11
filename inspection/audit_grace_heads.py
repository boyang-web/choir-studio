from pathlib import Path
import sys,json,zipfile,statistics,xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[1];sys.path[:0]=[str(ROOT/'tools'),str(ROOT/'tools/python-libs')]
import music21 as m
from new_score_symbols import pages,HEADS
data=json.loads((ROOT/'choir-studio/public/songs/chi-le-ge/song.json').read_text('utf8'));rows=[]
with zipfile.ZipFile(ROOT/'data/revisions/2026-10-26/omr/chi-le-ge-corrected.omr') as z:
 for p in range(10):
  sh=E.fromstring(z.read(f'sheet#{p+1}/sheet#{p+1}.xml'));sc=595/int(sh.find('picture').get('width'))
  for st in sh.findall('./page/system'):
   r={}
   for part in st.findall('part'):
    for j,sf in enumerate(part.findall('staff')):
     pi=int(part.get('id'))-1 if int(part.get('id'))<6 else 5+j
     r[pi]=statistics.mean(float(pt.get('y'))*sc for pt in sf.findall('./lines/line/point'))
   rows.append(r)
contents=pages();groups=[]
for page,content in enumerate(contents):
 systems=sorted({b['system'] for b in data['measures'] if b['page']==page})
 assigned={}
 for c in content[0]:
  if c['c'] not in HEADS:continue
  x,y=c['origin']
  si,pi,center=min([(si,pi,center) for si in systems for pi,center in rows[si].items()],key=lambda item:abs(item[2]-y))
  assigned.setdefault((si,pi),[]).append(c)
 for (si,pi),chars in assigned.items():
  small=sorted([c for c in chars if c['size']<15],key=lambda c:c['origin'][0]);clusters=[]
  for c in small:
   if clusters and c['origin'][0]-clusters[-1][-1]['origin'][0]<9:clusters[-1].append(c)
   else:clusters.append([c])
  center=rows[si][pi];gap=data['systems'][si]['interline']*595/1600
  clef=m.clef.BassClef() if pi in [3,6] else m.clef.Treble8vbClef() if pi==2 else m.clef.TrebleClef()
  def pitch(c):
   p=m.pitch.Pitch();p.diatonicNoteNum=clef.lowestLine+round((center+2*gap-c['origin'][1])*2/gap)
   p.accidental=m.pitch.Accidental(-1 if p.step=='B' else 0);return p.nameWithOctave
  for cluster in clusters:
   last=cluster[-1]['origin'][0];following=sorted([c for c in chars if c['size']>=15 and c['origin'][0]>last+1],key=lambda c:c['origin'][0])
   if not following:print('NO MAIN',page+1,pi,cluster);continue
   main=following[0];mx=main['origin'][0]
   bar=next((b for b in data['measures'] if b['system']==si and b['left']*595/1600-1<=mx<b['right']*595/1600),None)
   groups.append(dict(page=page+1,part=pi,measure=bar['label'] if bar else None,pitches=[pitch(c) for c in cluster],x=[round(c['origin'][0],2) for c in cluster],main=pitch(main),mainX=round(mx,2)))
print(json.dumps(groups,indent=2));(ROOT/'inspection/printed-grace-groups.json').write_text(json.dumps(groups,indent=2),'utf8')
