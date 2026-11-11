"""Build the offline library from Audiveris MusicXML and original PDF coordinates.

Requires PyMuPDF/Pillow and music21. All music parsing is delegated to music21.
Run after fix_parts.py and the corrected Audiveris exports have completed.
"""
from pathlib import Path
import sys, json, zipfile, shutil, warnings
from fractions import Fraction
from collections import defaultdict
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools/python-libs'))
import fitz
from PIL import Image
import music21 as m21
OUT=ROOT/'choir-studio/public/songs'
OUT.mkdir(parents=True,exist_ok=True)
DEFS=[
 dict(id='chi-le-ge',title='敕勒歌',tag='中国合唱',tempo=68,subtitle='刘洲 作曲 · 吴昊 编合唱 / SATB 与钢琴、陶笛',pages=9),
 dict(id='let-it-go',title='Let It Go',tag='音乐剧合唱',tempo=142,subtitle='Roger Emerson 编曲 · Pentatonix 版本 / SATB 与钢琴',pages=19),
]
PARTS=[('soprano','女高音','Soprano','S'),('alto','女中音','Alto','A'),('tenor','男高音','Tenor','T'),('bass','男低音','Bass','B'),('extra','','',''),('piano','钢琴伴奏','Piano','P')]
def f(v):return float(Fraction(v or '0'))
def rounded(v):return round(float(v),5)
for definition in DEFS:
 if definition['id']=='chi-le-ge' and (ROOT/'data/revisions/2026-10-26/omr/chi-le-ge-corrected.mxl').exists():
  from update_chile_score import generate
  generate()
  continue
 sid=definition['id'];target=OUT/sid;target.mkdir(exist_ok=True)
 pdf=fitz.open(ROOT/'data'/f'{sid}.pdf')
 source=ROOT/'data/omr'/f'{sid}-corrected.mxl'
 score=m21.converter.parse(source,forceSource=True)
 song=dict(definition,parts=[],pages=[],systems=[],measures=[],beats=[])
 omr=zipfile.ZipFile(ROOT/'data/omr'/f'{sid}-corrected.omr')
 import xml.etree.ElementTree as E
 time=0.;beat_offset=0.;stack_meta=[];issues=[]
 for page_no,pdfpage in enumerate(pdf):
  sheet=E.fromstring(omr.read(f'sheet#{page_no+1}/sheet#{page_no+1}.xml'))
  picture=sheet.find('picture');ow,oh=int(picture.get('width')),int(picture.get('height'))
  # Keep a consistent coordinate space for both original pages and cropped systems.
  scale=1600/ow
  pix=pdfpage.get_pixmap(matrix=fitz.Matrix(1600/pdfpage.rect.width,1600/pdfpage.rect.width),alpha=False)
  image=Image.frombytes('RGB',[pix.width,pix.height],pix.samples)
  page_image=f'page-{page_no+1:02}.webp';image.save(target/page_image,'WEBP',quality=88)
  song['pages'].append(dict(image=page_image,width=pix.width,height=pix.height))
  for system in sheet.findall('./page/system'):
   points=system.findall('./part/staff/lines/line/point')
   xs=[float(p.get('x')) for p in points];ys=[float(p.get('y')) for p in points]
   left=max(0,int((min(xs)-100)*scale));right=min(pix.width,int((max(xs)+25)*scale))
   top=max(0,int((min(ys)-110)*scale));bottom=min(pix.height,int((max(ys)+90)*scale))
   sys_index=len(song['systems']);sys_image=f'system-{sys_index+1:02}.webp'
   image.crop((left,top,right,bottom)).save(target/sys_image,'WEBP',quality=90)
   song['systems'].append(dict(image=sys_image,page=page_no,x=left,y=top,width=right-left,height=bottom-top))
   for stack in system.findall('stack'):
    if stack.get('duration')=='0':continue # Courtesy time signature at the system end is not a measure.
    idx=len(song['measures']);q=4.
    if sid=='chi-le-ge':
     if idx==0:q=1.
     elif idx in [54,66]:q=6. # Verified against printed 6/4; OMR misread the last one as 6/8.
    duration=q*60/definition['tempo']
    sl=float(stack.get('left'))*scale;sr=float(stack.get('right'))*scale
    positions=[]
    for slot in stack.findall('slot'):
     offset=f(slot.get('time-offset'))*4
     if offset<q:
      positions.append(dict(time=rounded(offset*60/definition['tempo']),x=rounded(sl+float(slot.get('x-offset'))*scale)))
    positions.sort(key=lambda p:(p['time'],p['x']))
    unique={}
    for p in positions:unique.setdefault(p['time'],p)
    positions=list(unique.values())
    if not positions:positions=[dict(time=0,x=sl+(sr-sl)*.2)]
    if positions[0]['time']>0:positions.insert(0,dict(time=0,x=sl+(sr-sl)*.1))
    for a,b in zip(positions,positions[1:]):b['x']=max(a['x'],b['x'])
    measure=dict(index=idx,label=idx+1,time=rounded(time),duration=rounded(duration),quarterLength=q,page=page_no,system=sys_index,left=rounded(sl),right=rounded(sr),positions=positions)
    song['measures'].append(measure);stack_meta.append((beat_offset,q))
    if stack.get('excess') or stack.get('abnormal')=='true':issues.append(dict(measure=idx+1,reason='OMR rhythm requires review',excess=stack.get('excess')))
    for beat in range(int(q)):song['beats'].append(dict(time=rounded(time+beat*60/definition['tempo']),accent=beat==0))
    time+=duration;beat_offset+=q
  print(sid,'page',page_no+1,'ready')
 raw=defaultdict(list)
 for part in score.parts:
  pname=part.partName or str(part.id)
  part_idx={'Soprano':0,'Alto':1,'Tenor':2,'Bass':3,'Vocal Percussion':4,'Ocarina':4,'Piano':5}.get(pname)
  if part_idx is None:raise ValueError('Unmapped part '+pname)
  measures=list(part.getElementsByClass(m21.stream.Measure))
  assert len(measures)==len(song['measures']),(sid,pname,len(measures),len(song['measures']))
  for idx,measure in enumerate(measures):
   timing=song['measures'][idx];q=timing['quarterLength'];measure_start=timing['time']
   for element in measure.recurse().notes:
    local=float(element.getOffsetInHierarchy(measure));duration=float(element.duration.quarterLength)
    if duration<=0 or local>=q or local<0:continue
    # Never let recognition overflow shift another part's bar boundary.
    duration=min(duration,q-local)
    notes=element.notes if isinstance(element,m21.chord.Chord) else [element]
    voice=element.getContextByClass(m21.stream.Voice);voice_id=str(voice.id) if voice else '1'
    for note in notes:
     pitch=int(round(note.pitch.midi)) if hasattr(note,'pitch') else 36
     raw[part_idx].append(dict(time=rounded(measure_start+local*60/definition['tempo']),duration=rounded(duration*60/definition['tempo']),midi=pitch,tie=note.tie.type if note.tie else None,voice=voice_id,measure=idx+1))
 for idx,(pid,name,english,letter) in enumerate(PARTS):
  if idx==4:
   pid,name,english,letter=('percussion','人声打击乐','Vocal percussion','V') if sid=='let-it-go' else ('ocarina','陶笛','Ocarina','O')
  notes=[];pending={};seen=set()
  for note in sorted(raw[idx],key=lambda n:(n['time'],n['midi'])):
   key=(note['midi'],note['voice']);identity=(note['time'],note['midi'])
   if identity in seen:continue
   seen.add(identity)
   previous=pending.get(key)
   if note['tie'] in ('stop','continue') and previous and abs(previous['time']+previous['duration']-note['time'])<.025:
    previous['duration']=rounded(note['time']+note['duration']-previous['time'])
    if note['tie']=='stop':pending.pop(key,None)
   else:
    entry={k:note[k] for k in ('time','duration','midi')};notes.append(entry)
    if note['tie'] in ('start','continue'):pending[key]=entry
    else:pending.pop(key,None)
  song['parts'].append(dict(id=pid,name=name,english=english,letter=letter,notes=notes))
 song['duration']=rounded(time)
 song['import']={'method':'Audiveris 5.11.0 + music21 10.5.1','status':'machine-transcribed-needs-proofreading','rhythmWarnings':issues,'corrections':['Physical staff order mapped to SATB, optional instruments, piano','Shared bar grid prevents per-part accumulated drift','Discarded empty courtesy-signature stack','Chi-le-ge 6/4 meters verified in original PDF']}
 (target/'song.json').write_text(json.dumps(song,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
 shutil.copy2(ROOT/'data'/f'{sid}.pdf',target/'score.pdf');shutil.copy2(source,target/'score.mxl')
 print(sid,'DONE',len(song['measures']),'measures',round(time,2),'seconds',[(p['id'],len(p['notes']),min((n['midi'] for n in p['notes']),default=0),max((n['midi'] for n in p['notes']),default=0)) for p in song['parts']])
 omr.close()
for definition in DEFS:
 current=json.loads((OUT/definition['id']/'song.json').read_text(encoding='utf8'))
 definition.update(pages=len(current['pages']),subtitle=current['subtitle'])
catalog_path=OUT/'catalog.json'
existing=json.loads(catalog_path.read_text(encoding='utf-8')) if catalog_path.exists() else []
known={definition['id'] for definition in DEFS}
catalog_path.write_text(json.dumps(DEFS+[entry for entry in existing if entry['id'] not in known],ensure_ascii=False),encoding='utf-8')
