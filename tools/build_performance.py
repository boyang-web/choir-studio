"""MusicXML/music21 -> standard MIDI -> runtime events. No geometry-to-time conversion.

The original vector PDF supplies missing duration symbols in Let It Go. Physical
positions only associate symbols; Fraction offsets are accumulated from notation.
Unresolved OMR issues are retained in an audit instead of silently time-stretched.
"""
from pathlib import Path
from fractions import Fraction as F
import sys,json,collections,copy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'tools/python-libs'))
import music21 as m21
from read_vp_rhythm import read
from score_repairs import apply as repair_verified
IDS={'Soprano':'soprano','Alto':'alto','Tenor':'tenor','Bass':'bass','Piano':'piano','Ocarina':'ocarina'}
DRUMS={'vocal':36,'kick':35,'snare':38,'hat':42,'click':37,'breath':55}
LEVELS={'ppp':.24,'pp':.32,'p':.43,'mp':.56,'mf':.70,'f':.85,'ff':1.,'fff':1.08}
def frac(value):return F(value).limit_denominator(10080)
def shape_match(elements,symbols):
 return len(elements)==len(symbols) and all(e.isRest==s['rest'] and (e.isRest or (len(e.notes) if e.isChord else 1)==len(s['heads'])) for e,s in zip(elements,symbols))
def repair_vector(source,data,audit):
 anchors=collections.defaultdict(list)
 for index,part in enumerate(list(source.parts)[:4]):
  records,_=read(data,str(index+1),(18,18));by_bar={r['measure']:r for r in records}
  for number,measure in enumerate(part.getElementsByClass(m21.stream.Measure),1):
   record=by_bar.get(number)
   if not record or record['total']!=record['expected']:continue
   elements=list(measure.recurse().notesAndRests);symbols=record['events'];removed=[]
   # Audiveris can insert a leading forward-rest because another staff's slot
   # was misread. Only remove it when the remaining complete symbol sequence matches.
   while elements and elements[0].isRest and len(elements)>len(symbols):removed.append(elements.pop(0))
   if not shape_match(elements,symbols):continue
   if removed or any(frac(e.getOffsetInHierarchy(measure))!=F(s['offset']) or frac(e.duration.quarterLength)!=F(s['duration']) for e,s in zip(elements,symbols)):
    audit['symbolRepairs'].append(dict(part=part.partName,measure=number,removedLeadingRests=len(removed)))
   for e in removed:e.activeSite.remove(e)
   for element,symbol in zip(elements,symbols):
    site=element.activeSite;site.setElementOffset(element,F(symbol['offset']));element.duration=m21.duration.Duration(F(symbol['duration']))
    if symbol['heads']:anchors[number].append(dict(quarter=F(symbol['offset']),x=sum(h['x'] for h in symbol['heads'])/len(symbol['heads'])))
 return anchors
def vp_events(data,audit):
 records,warnings=read(data)
 if warnings:raise ValueError('VP duration symbols do not fill their bars: '+str(warnings))
 events=[];starts=[];quarter=F(0)
 for measure in data['measures']:starts.append(quarter);quarter+=F(str(measure['quarterLength']))
 for record in records:
  for e in record['events']:
   if e['rest']:continue
   for head in e['heads']:
    text=head['syllable'];kind='breath' if head['head']=='wind' or 'shoo' in text.lower() else 'vocal' if head['head']=='ordinary' else 'click' if text.lower()=='tk' else 'hat'
    events.append(dict(quarter=starts[record['measure']-1]+F(e['offset']),length=F(e['duration']),midi=DRUMS[kind],kind=kind,syllable=text,head=head['head'],measure=record['measure'],branch='shared',source='printed duration symbols'))
 unique={}
 for n in events:unique[(n['quarter'],n['kind'])]=n
 events=sorted(unique.values(),key=lambda n:(n['quarter'],n['midi']))
 # The ending wind gesture is written across successive whole-note diamonds.
 wind=None;result=[]
 for n in events:
  if n['head']=='wind' and wind and wind['quarter']+wind['length']==n['quarter']:wind['length']+=n['length'];continue
  result.append(n)
  if n['head']=='wind':wind=n
 audit['vpBars']=[dict(measure=r['measure'],expected=r['expected'],total=r['total']) for r in records]
 audit['vpEvents']=len(result)
 return result,records
def collect(source,data,audit):
 raw=collections.defaultdict(list);starts=[];q=F(0)
 for measure in data['measures']:starts.append(q);q+=F(str(measure['quarterLength']))
 for source_index,part in enumerate(source.parts):
  if part.partName not in IDS:continue
  pid=IDS[part.partName]
  for index,measure in enumerate(part.getElementsByClass(m21.stream.Measure)):
   if index>=len(starts):break
   expected=F(str(data['measures'][index]['quarterLength']));elements=list(measure.recurse().notes)
   voices=list(measure.recurse().getElementsByClass(m21.stream.Voice));voice_ids=sorted({str(v.id) for v in voices});degree=max([len(e.notes) if e.isChord else 1 for e in elements]+[len(voice_ids),1])
   for e in elements:
    offset=frac(e.getOffsetInHierarchy(measure));duration=frac(e.duration.quarterLength)
    if duration<=0:continue
    if offset+duration>expected:audit['unresolved'].append(dict(part=part.partName,staff=source_index,measure=index+1,offset=str(offset),duration=str(duration),expected=str(expected)))
    notes=sorted(e.notes,key=lambda n:n.pitch.midi,reverse=True) if e.isChord else [e];voice=e.getContextByClass(m21.stream.Voice);voice_id=str(voice.id) if voice else '1'
    for order,n in enumerate(notes):
     branch='shared' if pid in ['piano','ocarina'] or degree==1 else str(min(order+1,3)) if len(notes)>1 else str(min(voice_ids.index(voice_id)+1 if voice_id in voice_ids else 1,3))
     raw[pid].append(dict(quarter=starts[index]+offset,length=duration,midi=int(round(n.pitch.midi)),branch=branch,voice=str(source_index)+':'+voice_id,tie=n.tie.type if n.tie else None,measure=index+1,grace=bool(e.editorial.get('performedGrace',False)),ornament=bool(e.editorial.get('performedOrnament',False)),source='MusicXML duration'))
 tracks={}
 for pid,notes in raw.items():
  seen=set();pending={};merged=[]
  for n in sorted(notes,key=lambda n:(n['quarter'],n['midi'],n['branch'])):
   identity=(n['quarter'],n['midi'],n['branch'])
   if identity in seen:continue
   seen.add(identity);key=(n['midi'],n['branch'],n['voice']);prev=pending.get(key)
   if n['tie'] in ['stop','continue'] and prev and prev['quarter']+prev['length']==n['quarter']:
    prev['length']+=n['length']
    if n['tie']=='stop':pending.pop(key,None)
   else:
    merged.append(n)
    if n['tie'] in ['start','continue']:pending[key]=n
    else:pending.pop(key,None)
  tracks[pid]=merged
 return tracks,starts
def expression(source,data,starts,ppq):
 points=collections.defaultdict(lambda:{F(0):dict(value=.65)})
 def position(obj):
  measure=obj.getContextByClass(m21.stream.Measure)
  if measure is None:return None
  index=int(measure.number)-1
  if not 0<=index<len(starts):return None
  return starts[index]+frac(obj.getOffsetInHierarchy(measure))
 for part in source.parts:
  pid=IDS.get(part.partName,'percussion' if part.partName=='Vocal Percussion' else None)
  if not pid:continue
  for mark in part.recurse().getElementsByClass(m21.dynamics.Dynamic):
   q=position(mark)
   if q is not None and mark.value in LEVELS:points[pid][q]=dict(value=LEVELS[mark.value],mark=mark.value)
  for wedge in part.recurse().getElementsByClass(m21.dynamics.DynamicWedge):
   a=position(wedge.getFirst());b=position(wedge.getLast())
   if a is None or b is None or b<=a:continue
   value=next((v['value'] for q,v in reversed(sorted(points[pid].items())) if q<=a),.65)
   points[pid].setdefault(a,dict(value=value));points[pid][b]=dict(value=max(.22,min(1.05,value+(.18 if isinstance(wedge,m21.dynamics.Crescendo) else -.18))),linear=True)
 for part in data['parts']:part['expression']=[dict(ticks=round(q*ppq),**v) for q,v in sorted(points[part['id']].items())]
def export(sid, source_path=None):
 target=ROOT/'choir-studio/public/songs'/sid;data=json.loads((target/'song.json').read_text(encoding='utf8'))
 source_path=source_path or (ROOT/data['import']['musicxml'] if data['import'].get('musicxml') else ROOT/'data/omr'/f'{sid}-corrected.mxl')
 source=m21.converter.parse(source_path,forceSource=True)
 audit=dict(source='Audiveris MusicXML + original notation duration repairs + music21 MIDI',symbolRepairs=[],unresolved=[])
 anchors=repair_vector(source,data,audit) if sid=='let-it-go' else {}
 # These hand corrections belong only to the archived nine-page edition.
 if not data['import'].get('revision'):repair_verified(source,data,audit)
 elif data['import']['revision']=='2026-10-26':
  from new_score_symbols import apply
  apply(source,data,audit)
  # Keep a standard, editable MusicXML alongside the MIDI actually performed.
  # The OMR export remains untouched for a reproducible repair pass.
  for part in source.parts:
   for index,measure in enumerate(part.getElementsByClass(m21.stream.Measure)):
    ratio='6/4' if data['measures'][index]['quarterLength']==6 else '4/4'
    for ts in list(measure.getElementsByClass(m21.meter.TimeSignature)):measure.remove(ts)
    if index==0 or ratio!=('6/4' if data['measures'][index-1]['quarterLength']==6 else '4/4'):measure.insert(0,m21.meter.TimeSignature(ratio))
  editable=copy.deepcopy(source);editable.splitAtDurations(recurse=True)
  editable.write('mxl',fp=str(target/'score.mxl'),makeNotation=False)
  import shutil
  shutil.copyfile(target/'score.mxl',ROOT/'data/revisions/2026-10-26/chi-le-ge-playback.mxl')
 tracks,starts=collect(source,data,audit)
 if sid=='let-it-go':tracks['percussion'],vp_records=vp_events(data,audit)
 score=m21.stream.Score();score.metadata=m21.metadata.Metadata(title=data['title']);score.insert(0,m21.tempo.MetronomeMark(number=data['tempo']));labels={};channel=0
 meter=None
 for index,measure in enumerate(data['measures']):
  ratio='6/4' if measure['quarterLength']==6 else '4/4'
  if ratio!=meter:score.insert(starts[index],m21.meter.TimeSignature(ratio));meter=ratio
 for part in data['parts']:
  pid=part['id'];notes=tracks[pid];branches=sorted({n['branch'] for n in notes})
  for branch in branches:
   label=pid+':'+branch;stream=m21.stream.Part();stream.partName=label;instrument=m21.instrument.Instrument();instrument.partName=label;instrument.instrumentName=label;instrument.midiProgram=0 if pid=='piano' else 73 if pid=='ocarina' else 52;instrument.midiChannel=9 if pid=='percussion' else channel
   if pid!='percussion':channel+=1;channel+=channel==9
   stream.insert(0,instrument)
   for n in notes:
    if n['branch']!=branch:continue
    note=m21.note.Note(n['midi'],quarterLength=n['length']);note.volume.velocity=95 if pid=='percussion' else 72 if n.get('grace') else 90;stream.insert(n['quarter'],note)
   score.insert(0,stream);labels[label]=[n for n in notes if n['branch']==branch]
 # Use music21's SMF writer, then read its events back. Runtime JSON is the
 # MIDI round-trip, not an independent timing generator.
 midi=m21.midi.translate.streamToMidiFile(score,addStartDelay=False,addEndDelay=False);midi.open(str(target/'performance.mid'),'wb');midi.write();midi.close();ppq=midi.ticksPerQuarterNote
 midi=m21.midi.MidiFile();midi.open(str(target/'performance.mid'));midi.read();midi.close();runtime=collections.defaultdict(list)
 micros=next(int.from_bytes(e.data,'big') for t in midi.tracks for e in t.events if e.type==m21.midi.MetaEvents.SET_TEMPO);seconds_per_tick=micros/1000000/ppq
 for track in midi.tracks:
  label=next((e.data.decode('utf8') for e in track.events if e.type==m21.midi.MetaEvents.SEQUENCE_TRACK_NAME and e.data.decode('utf8') in labels),None)
  if not label:continue
  pid,branch=label.split(':');metadata=collections.defaultdict(list)
  for n in labels[label]:metadata[(round(n['quarter']*ppq),n['midi'],round(n['length']*ppq))].append(n)
  tick=0;active=collections.defaultdict(list)
  for event in track.events:
   if event.isDeltaTime():tick+=event.time;continue
   if event.isNoteOn():active[event.pitch].append((tick,event.velocity))
   elif event.isNoteOff() and active[event.pitch]:
    match=None
    for active_index,(begin,velocity) in enumerate(active[event.pitch]):
     length=tick-begin
     for delta in [0,-1,1]:
      for duration_delta in [0,-1,1]:
       key=(begin+delta,event.pitch,length+duration_delta)
       if metadata.get(key):match=(active_index,begin,velocity,length,key);break
      if match:break
     if match:break
    if not match:raise ValueError('MIDI note cannot be matched: '+str((label,tick,event.pitch,active[event.pitch])))
    active_index,begin,velocity,length,key=match;active[event.pitch].pop(active_index);original=metadata[key].pop(0)
    entry={k:v for k,v in original.items() if k not in ['quarter','length','tie','voice']};entry.update(ticks=begin,durationTicks=length,time=round(begin*seconds_per_tick,8),duration=round(length*seconds_per_tick,8),velocity=velocity/127,branch=branch);runtime[pid].append(entry)
 for part in data['parts']:
  if not runtime[part['id']]:raise ValueError('MIDI track missing: '+part['id'])
  part['notes']=sorted(runtime[part['id']],key=lambda n:(n['ticks'],n['midi']))
 for i,measure in enumerate(data['measures']):
  measure['ticks']=round(starts[i]*ppq);measure['durationTicks']=round(F(str(measure['quarterLength']))*ppq);measure['time']=round(measure['ticks']*seconds_per_tick,8);measure['duration']=round(measure['durationTicks']*seconds_per_tick,8)
 # Visual anchors associate notated offsets with the printed head centers.
 # Prefer vocal staves so a faulty accompaniment slot cannot freeze the cursor.
 visual=collections.defaultdict(lambda:collections.defaultdict(list))
 for part in list(source.parts)[:4]:
  for index,b in enumerate(part.getElementsByClass(m21.stream.Measure)):
   if index>=len(data['measures']) or not b.layoutWidth:continue
   measure=data['measures'][index];system=data['systems'][measure['system']]
   for e in b.recurse().notes:
    q=frac(e.getOffsetInHierarchy(b));xs=[n.style.absoluteX for n in e.notes] if e.isChord else [e.style.absoluteX];xs=[float(x) for x in xs if x is not None]
    if not xs or q<0 or q>=F(str(measure['quarterLength'])):continue
    x=measure['left']+sum(xs)/len(xs)/b.layoutWidth*(measure['right']-measure['left'])+.65*system.get('interline',12)
    visual[index][q].append(max(measure['left'],min(measure['right']-1,x)))
 for index,points in visual.items():
  if len(points)<3:continue
  import statistics
  candidates=[dict(ticks=round(q*ppq),time=round(round(q*ppq)*seconds_per_tick,8),x=round(statistics.median(xs),5)) for q,xs in sorted(points.items())]
  chains=[]
  for i,p in enumerate(candidates):
   previous=max((chains[j] for j in range(i) if candidates[j]['x']<p['x']-.001),key=len,default=[]);chains.append(previous+[i])
  best=max(chains,key=len);data['measures'][index]['positions']=[candidates[i] for i in best]
 data['duration']=round((data['measures'][-1]['ticks']+data['measures'][-1]['durationTicks'])*seconds_per_tick,8)
 expression(source,data,starts,ppq)
 for part in data['parts']:
  for point in part['expression']:point['time']=round(point['ticks']*seconds_per_tick,8)
 data['beats']=[dict(ticks=round((starts[i]+beat)*ppq),time=round(round((starts[i]+beat)*ppq)*seconds_per_tick,8),accent=beat==0) for i,m in enumerate(data['measures']) for beat in range(int(m['quarterLength']))]
 if sid=='let-it-go':
  for record in vp_records:
   m=data['measures'][record['measure']-1];points=[dict(ticks=round(F(e['offset'])*ppq),time=round(round(F(e['offset'])*ppq)*seconds_per_tick,8),x=e['x']*1600/fitz_width(data,record['page'])) for e in record['events']]
   if points:m['positions']=points
 data['midi']={'file':'performance.mid','ppq':ppq,'source':'music21','timing':'MusicXML duration and printed rhythmic symbols'}
 data['performanceVersion']=3;data['import']['rhythmWarnings']=audit['unresolved'];audit['tracks']={p['id']:len(p['notes']) for p in data['parts']}
 (target/'song.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf8')
 (ROOT/'inspection'/f'{sid}-musical-audit.json').write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf8')
 print(sid,'repairs',len(audit['symbolRepairs']),'unresolved notes',len(audit['unresolved']),'tracks',audit['tracks'],flush=True)
def fitz_width(data,page):
 import fitz
 with fitz.open(ROOT/'data'/f"{data['id']}.pdf") as pdf:return pdf[page-1].rect.width
if __name__=='__main__':
 for sid in ['chi-le-ge','let-it-go']:export(sid)
