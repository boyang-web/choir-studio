"""Preserve divisi, reconstruct expression curves, and recover printed beatbox onsets.

The source score remains authoritative. This is still an OMR-derived performance,
with provenance and confidence retained rather than claiming manual proofreading.
"""
from pathlib import Path
import sys,json,zipfile,statistics,re,collections
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools/python-libs'))
import fitz,music21 as m21
IDS=['soprano','alto','tenor','bass','extra','piano']
LEVELS={'PPP':.24,'PP':.32,'P':.43,'MP':.56,'MF':.70,'F':.85,'FF':1.,'FFF':1.08}
def rd(x):return round(float(x),5)
def time_at_x(measures,x):
 m=next((m for m in measures if m['left']<=x<=m['right']),min(measures,key=lambda m:abs(m['left']-x)))
 pts=[dict(time=0,x=m['left'])]+m['positions']+[dict(time=m['duration'],x=m['right'])]
 pts=sorted(pts,key=lambda p:p['x']);prev=pts[0]
 for point in pts[1:]:
  if point['x']>=x:
   frac=max(0,min(1,(x-prev['x'])/max(.001,point['x']-prev['x'])))
   return m['time']+prev['time']+(point['time']-prev['time'])*frac
  prev=point
 return m['time']+m['duration']
def expression_at(points,time):
 last=points[0]
 for point in points[1:]:
  if point['time']>time:
   if point.get('linear'):return last['value']+(point['value']-last['value'])*max(0,(time-last['time'])/(point['time']-last['time']))
   return last['value']
  last=point
 return last['value']
for sid in ['chi-le-ge','let-it-go']:
 target=ROOT/'choir-studio/public/songs'/sid;data=json.loads((target/'song.json').read_text(encoding='utf8'))
 score=m21.converter.parse(ROOT/'data/omr'/f'{sid}-corrected.mxl',forceSource=True)
 part_by_name={p['english']:p for p in data['parts']}
 for source_part in score.parts:
  name=source_part.partName
  if name not in ['Soprano','Alto','Tenor','Bass']:continue
  part=part_by_name[name];raw=[];branch_count=1;divisi_bars=[]
  for index,measure in enumerate(source_part.getElementsByClass(m21.stream.Measure)):
   tm=data['measures'][index];elements=list(measure.recurse().notes)
   voices=list(measure.recurse().getElementsByClass(m21.stream.Voice));voice_ids=sorted({str(v.id) for v in voices})
   degree=max([len(e.notes) if isinstance(e,m21.chord.Chord) else 1 for e in elements]+[len(voice_ids),1])
   if degree>1:branch_count=max(branch_count,min(3,degree));divisi_bars.append(index+1)
   for element in elements:
    local=float(element.getOffsetInHierarchy(measure));dur=min(float(element.duration.quarterLength),tm['quarterLength']-local)
    if local<0 or dur<=0:continue
    notes=sorted(element.notes,key=lambda n:n.pitch.midi,reverse=True) if isinstance(element,m21.chord.Chord) else [element]
    voice=element.getContextByClass(m21.stream.Voice);voice_id=str(voice.id) if voice else '1'
    for order,note in enumerate(notes):
     if degree==1:branch='shared'
     elif len(notes)>1:branch=str(min(order+1,3))
     else:branch=str(min((voice_ids.index(voice_id)+1 if voice_id in voice_ids else 1),3))
     raw.append(dict(time=rd(tm['time']+local*60/data['tempo']),duration=rd(dur*60/data['tempo']),midi=int(round(note.pitch.midi)),branch=branch,voice=voice_id,tie=note.tie.type if note.tie else None))
  notes=[];pending={};seen=set()
  for n in sorted(raw,key=lambda n:(n['time'],n['midi'],n['branch'])):
   identity=(n['time'],n['midi'],n['branch']);key=(n['midi'],n['branch'],n['voice'])
   if identity in seen:continue
   seen.add(identity);prev=pending.get(key)
   if n['tie'] in ('stop','continue') and prev and abs(prev['time']+prev['duration']-n['time'])<.025:
    prev['duration']=rd(n['time']+n['duration']-prev['time'])
    if n['tie']=='stop':pending.pop(key,None)
   else:
    entry={k:n[k] for k in ['time','duration','midi','branch']};notes.append(entry)
    if n['tie'] in ('start','continue'):pending[key]=entry
    else:pending.pop(key,None)
  part['notes']=notes
  part['branches']=[dict(id=str(i),name=part['name']+' '+str(i)) for i in range(1,branch_count+1)] if branch_count>1 else []
  part['divisiMeasures']=divisi_bars
  part['divisiStatus']='score-voice-and-chord-derived; requires proofreading'
 # Expression objects were removed only from the playback-export workaround,
 # not from the original OMR projects. Use chord attachments for part ownership.
 dynamics=collections.defaultdict(list);wedges=collections.defaultdict(list)
 with zipfile.ZipFile(ROOT/'data/omr'/f'{sid}.omr') as book:
  global_system=0
  for page_no in range(len(data['pages'])):
   sheet=ET.fromstring(book.read(f'sheet#{page_no+1}/sheet#{page_no+1}.xml'));scale=1600/int(sheet.find('picture').get('width'))
   for system in sheet.findall('./page/system'):
    parts=system.findall('part');logical={3:[0,1,5],5:[0,1,2,3,5],6:[0,1,2,3,4,5]}[len(parts)]
    staff_owner={st.get('id'):data['parts'][i]['id'] for part,i in zip(parts,logical) for st in part.findall('staff')}
    inters={n.get('id'):n for n in system.findall('./sig/inters/*')}
    links=collections.defaultdict(list)
    for rel in system.findall('./sig/relations/relation'):
     source=inters.get(rel.get('source'));target_node=inters.get(rel.get('target'))
     if source is not None and target_node is not None:
      owner=staff_owner.get(source.get('staff'))
      if owner and target_node.tag in ['dynamics','wedge']:links[target_node.get('id')].append(owner)
    measures=[m for m in data['measures'] if m['system']==global_system]
    for node in inters.values():
     if node.tag not in ['dynamics','wedge'] or not links.get(node.get('id')):continue
     grade=float(node.get('ctx-grade',node.get('grade','0')))
     if grade<.65:continue
     bounds=node.find('bounds')
     if bounds is None:continue
     owners=set(links[node.get('id')]);x=float(bounds.get('x'))*scale
     if node.tag=='dynamics':
      mark=node.get('shape','').replace('DYNAMICS_','')
      if mark not in LEVELS:continue
      when=rd(time_at_x(measures,x))
      for owner in owners:dynamics[owner].append(dict(time=when,value=LEVELS[mark],mark=mark.lower(),source='OMR chord-attached dynamic',confidence=grade))
     else:
      start=time_at_x(measures,x);end=time_at_x(measures,x+float(bounds.get('w'))*scale)
      if end-start<.12:continue
      for owner in owners:wedges[owner].append(dict(start=rd(start),end=rd(end),direction=node.get('shape'),source='OMR chord-attached hairpin',confidence=grade))
    global_system+=1
 for part in data['parts']:
  pid=part['id'];marks=sorted(dynamics[pid],key=lambda x:x['time']);points=[dict(time=0,value=.65)]+marks
  for wedge in sorted(wedges[pid],key=lambda w:w['start']):
   start,end=wedge['start'],wedge['end'];start_value=expression_at(sorted(points,key=lambda p:p['time']),start)
   next_mark=next((m for m in marks if end-.12<=m['time']<=end+2.5),None)
   direction=1 if wedge['direction']=='CRESCENDO' else -1
   end_value=next_mark['value'] if next_mark and (next_mark['value']-start_value)*direction>0 else max(.22,min(1.05,start_value+direction*.18))
   points=[p for p in points if not start<p['time']<end]
   points.extend([dict(time=start,value=rd(start_value)),dict(time=end,value=rd(end_value),linear=True)])
  unique={p['time']:p for p in sorted(points,key=lambda p:p['time'])}
  part['expression']=list(unique.values());part['hairpins']=wedges[pid];part['expressionStatus']='recognized-score-markings; not manually proofread'
 # Recover every printed x-note from the ORIGINAL vector PDF for vocal percussion.
 # Earlier OMR missed a number of these, and all of its unpitched colors were lost.
 if sid=='let-it-go':
  pdf=fitz.open(ROOT/'data'/f'{sid}.pdf');events=[];system_index=0
  with zipfile.ZipFile(ROOT/'data/omr'/f'{sid}-corrected.omr') as book:
   for page_no,page in enumerate(pdf):
    sheet=ET.fromstring(book.read(f'sheet#{page_no+1}/sheet#{page_no+1}.xml'));to_pdf=page.rect.width/int(sheet.find('picture').get('width'));to_app=1600/page.rect.width
    chars=[c for block in page.get_text('rawdict')['blocks'] for line in block.get('lines',[]) for span in line['spans'] for c in span['chars']]
    words=page.get_text('words')
    for system in sheet.findall('./page/system'):
     part=system.find("part[@id='5']");measures=[m for m in data['measures'] if m['system']==system_index]
     if part is not None:
      ys=[float(p.get('y'))*to_pdf for p in part.findall('./staff/lines/line/point')];top,bottom=min(ys),max(ys)
      syllables=[w for w in words if bottom+2<w[1]<bottom+26 and re.search(r'tk|ka|shoo|knock|bom|pff',w[4],re.I)]
      for c in chars:
       x,y=c['origin']
       if c['c']!='¿' or not top-8<=y<=bottom+3:continue
       measure=next((m for m in measures if m['left']<=x*to_app<=m['right']),None)
       if not measure:continue
       text=min(syllables,key=lambda w:abs((w[0]+w[2])/2-x))[4] if syllables else ''
       if syllables and abs((min(syllables,key=lambda w:abs((w[0]+w[2])/2-x))[0])-x)>18:text=''
       if re.search('shoo|pff',text,re.I):kind='breath'
       elif re.search('bom|dum|boom',text,re.I):kind='kick'
       elif text.lower()=='tk':kind='click'
       elif text.lower()=='ka':kind='hat'
       else:kind='hat' if y<top+3 else 'snare'
       raw_time=time_at_x(measures,x*to_app)
       quarter=(raw_time-measure['time'])*data['tempo']/60
       quarter=round(quarter*4)/4
       when=measure['time']+quarter*60/data['tempo']
       when=max(measure['time'],min(measure['time']+measure['duration']-.025,when))
       events.append(dict(time=rd(when),duration=.12,midi=36,kind=kind,syllable=text,measure=measure['label'],source='original PDF printed x-note'))
     system_index+=1
  unique={(n['time'],n['kind']):n for n in events};percussion=next(p for p in data['parts'] if p['id']=='percussion');old=len(percussion['notes']);percussion['notes']=sorted(unique.values(),key=lambda n:n['time']);percussion['percussionStatus']='printed x-note onsets; timbre follows printed syllable where available'
  print('Let It Go beatbox:',old,'old events ->',len(percussion['notes']),'PDF x-notes; first measure',percussion['notes'][0]['measure'])
 if sid=='let-it-go':
  from recover_beatbox import recover
  print('Complete VP head recovery:',dict(recover(data)),flush=True)
 data['performanceVersion']=2
 (target/'song.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf8')
 print(sid,[(p['id'],len(p.get('branches',[])),len(p['expression']),len(p['hairpins'])) for p in data['parts']],flush=True)
