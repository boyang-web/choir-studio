"""Verify OMR durations against the SMuFL glyphs in the revised vector PDF."""
from pathlib import Path
from fractions import Fraction as F
import collections, json, zipfile, statistics, xml.etree.ElementTree as ET
import fitz
import music21 as m
ROOT=Path(__file__).resolve().parents[1]
HEADS={'\ue0a4':F(1),'\ue0a3':F(2),'\ue0a2':F(4)}
RESTS={'\ue4e3':None,'\ue4e4':F(2),'\ue4e5':F(1),'\ue4e6':F(1,2),'\ue4e7':F(1,4),'\ue4e8':F(1,8)}

def pages():
 result=[]
 with fitz.open(ROOT/'data/revisions/2026-10-26/chi-le-ge.pdf') as pdf:
  for page in pdf:
   chars=[dict(c,font=s['font'],size=s['size']) for b in page.get_text('rawdict')['blocks'] for l in b.get('lines',[]) for s in l['spans'] for c in s['chars']]
   stems=[];beams=[]
   for d in page.get_drawings():
    for i in d['items']:
     if i[0]=='l' and abs(i[1].x-i[2].x)<.05 and 5<abs(i[1].y-i[2].y)<65:stems.append((i[1].x,min(i[1].y,i[2].y),max(i[1].y,i[2].y)))
    r=d['rect']
    if d.get('fill') is not None and d['items'] and all(i[0]=='l' for i in d['items']) and r.width>2 and .5<r.height<16 and r.height/r.width<.8:beams.append(r)
   result.append((chars,stems,beams))
 return result

def duration(c,content,q):
 chars,stems,beams=content;x,y=c['origin'];symbol=c['c'];small=c['size']<15
 if symbol in RESTS:base=RESTS[symbol] or F(q)
 else:
  base=HEADS[symbol];width=4.89*c['size']/17.02286
  candidates=[s for s in stems if min(abs(s[0]-x-.2),abs(s[0]-x-width))<.65 and s[1]-.8<=y<=s[2]+.8]
  stem=min(candidates,key=lambda s:min(abs(s[0]-x-.2),abs(s[0]-x-width)),default=None)
  if stem:
   count=sum(1 for r in beams if r.x0-.25<=stem[0]<=r.x1+.25 and r.y0<=stem[2]+.4 and r.y1>=stem[1]-.4)
   flags=max([1+(ord(f['c'])-0xe240)//2 for f in chars if 0xe240<=ord(f['c'])<=0xe247 and abs(f['origin'][0]-stem[0])<.5 and stem[1]-1<=f['origin'][1]<=stem[2]+1]+[0])
   if symbol=='\ue0a4':base/=2**max(count,flags)
 dots={round(d['origin'][0],1) for d in chars if d['c']=='\ue1e7' and 5*c['size']/17<d['origin'][0]-x<12*c['size']/17 and abs(d['origin'][1]-y)<2.2}
 if dots:base*=sum((F(1,2**i) for i in range(len(dots)+1)),F(0))
 return base,small

def apply(source,data,audit):
 contents=pages();staffs=[]
 with zipfile.ZipFile(ROOT/'data/revisions/2026-10-26/omr/chi-le-ge-corrected.omr') as book:
  for pi in range(10):
   sheet=ET.fromstring(book.read(f'sheet#{pi+1}/sheet#{pi+1}.xml'));scale=595/int(sheet.find('picture').get('width'))
   for system in sheet.findall('./page/system'):
    rows={}
    for part in system.findall('part'):
     rows[int(part.get('id'))]=[statistics.mean(float(p.get('y'))*scale for p in st.findall('./lines/line/point')) for st in part.findall('staff')]
    staffs.append(rows)
 changes=[];unmatched=[]
 normalize_printed_graces(source,data,contents,staffs,audit)
 for pi,part in enumerate(source.parts):
  for bi,b in enumerate(part.getElementsByClass(m.stream.Measure)):
   bar=data['measures'][bi];content=contents[bar['page']];chars=content[0];rows=staffs[bar['system']]
   logical=pi+1 if pi<5 else 6;row_index=0 if pi<6 else 1
   if logical not in rows:continue
   center=rows[logical][row_index];symbols=[c for c in chars if c['c'] in HEADS or c['c'] in RESTS]
   symbols=[c for c in symbols if abs(c['origin'][1]-center)<28 and bar['left']*595/1600-1<=c['origin'][0]<bar['right']*595/1600+1]
   voices=list(b.getElementsByClass(m.stream.Voice)) or [b]
   for voice in voices:
    shift=F(0);graces=[];previous=None
    for e in list(voice.notesAndRests):
     if e.editorial.get('graceAdjusted') or e.editorial.get('performedGrace'):continue
     notes=e.notes if e.isChord else [e];xs=[n.style.absoluteX for n in notes if n.style.absoluteX is not None]
     if not xs:continue
     x=(bar['left']+(sum(float(x) for x in xs)/len(xs))/b.layoutWidth*(bar['right']-bar['left']))*595/1600
     clef=e.getContextByClass(m.clef.Clef) or (m.clef.BassClef() if pi in [3,6] else m.clef.Treble8vbClef() if pi==2 else m.clef.TrebleClef())
     gap=data['systems'][bar['system']]['interline']*595/1600
     expected_y=[center+2*gap-(n.pitch.diatonicNoteNum-clef.lowestLine)*gap/2 for n in notes] if not e.isRest else []
     candidates=[c for c in symbols if (c['c'] in RESTS)==e.isRest and abs(c['origin'][0]-x)<3 and (e.isRest or min(abs(c['origin'][1]-y) for y in expected_y)<1.8)]
     if not candidates:continue
     c=min(candidates,key=lambda c:abs(c['origin'][0]-x)+(min(abs(c['origin'][1]-y) for y in expected_y) if expected_y else 0))
     length,small=duration(c,content,int(bar['quarterLength']))
     original=F(e.quarterLength);old=F(e.offset)
     if small and not e.isRest:
      graces.append((e,old));shift-=original;voice.remove(e)
      changes.append(dict(part=pi,measure=bi+1,kind='grace',pitch=str(e),oldDuration=str(original)))
      continue
     # Retain explicitly recognized tuplet ratios until their complete printed
     # groups can be verified; ordinary symbols have exact binary durations.
     if e.duration.tuplets:
      for t in e.duration.tuplets:length*=F(t.numberNotesNormal,t.numberNotesActual)
     if length!=original:
      changes.append(dict(part=pi,measure=bi+1,kind='duration',old=str(original),new=str(length),x=round(x,2),symbol=hex(ord(c['c']))))
     voice.setElementOffset(e,old+shift);e.duration=m.duration.Duration(length)
     shift+=length-original
     if graces:
      anchor=F(e.offset);borrow=min(F(1,8),F(previous.quarterLength)/2) if previous is not None and previous.offset+previous.quarterLength==anchor else F(0)
      if not borrow:
       borrow=min(F(1,8),length/2)
       voice.setElementOffset(e,anchor+borrow);e.duration=m.duration.Duration(length-borrow)
       anchor+=borrow
      else:
       previous.duration=m.duration.Duration(F(previous.quarterLength)-borrow)
      for j,(g,_) in enumerate(graces):
       g.duration=m.duration.Duration(borrow/len(graces));g.editorial['performedGrace']=True;voice.insert(anchor-borrow+j*borrow/len(graces),g)
      graces=[]
     previous=e
 # Rebuild the complete, unambiguous printed vocal sequences in bars where
 # OMR inserted time-signature digits as pitches or counted grace notes.
 # Bass 26: whole Bb2 was a whole rest; 29: the final G3 was a rest;
 # 67: the 6/4 digit became Bb2 and the dotted-half C3 was omitted.
 fixed=[(0,29),(0,45),(0,67),(1,21),(2,29),(2,45),(2,55),(3,26),(3,29),(3,55),(3,67),(3,68),(4,64)]
 for pi,number in fixed:
  rebuild_voice(source,data,contents,staffs,pi,number,changes)
 repair_piano(source,changes)
 # The explicitly rebuilt vocal and piano bars also contain verified graces.
 audit['performedGraceNotes']=sum(bool(e.editorial.get('performedGrace')) for p in source.parts for e in p.recurse().notes)
 realize_printed_mordents(source,data,contents,staffs,audit)
 diagnostics={}
 for number in [4,21,28,39,42,43,44,45,61,62,63,64,68]:
  diagnostics[number]={pi:[dict(x=round(t['x'],2),pitch=str(t['pitch']),length=str(t['length']),grace=t['grace']) for t in printed_tokens(data,contents,staffs,pi,number)] for pi in [5,6]}
 (ROOT/'inspection/new-piano-symbols.json').write_text(json.dumps(diagnostics,indent=2),'utf8')
 audit['vectorDurationRepairs']=changes
 (ROOT/'inspection/new-vector-duration-repairs.json').write_text(json.dumps(changes,indent=2),'utf8')

def printed_tokens(data,contents,staffs,pi,number):
 bar=data['measures'][number-1];content=contents[bar['page']];rows=staffs[bar['system']]
 logical=pi+1 if pi<5 else 6;row_index=0 if pi<6 else 1
 center=rows[logical][row_index];gap=data['systems'][bar['system']]['interline']*595/1600
 symbols=[c for c in content[0] if c['c'] in HEADS or c['c'] in RESTS]
 symbols=sorted([c for c in symbols if abs(c['origin'][1]-center)<28 and bar['left']*595/1600-1<c['origin'][0]<bar['right']*595/1600],key=lambda c:c['origin'][0])
 clef=m.clef.BassClef() if pi in [3,6] else m.clef.Treble8vbClef() if pi==2 else m.clef.TrebleClef()
 state={};tokens=[]
 for c in symbols:
  length,grace=duration(c,content,int(bar['quarterLength']));x,y=c['origin'];pitch=None
  if c['c'] in HEADS:
   pitch=m.pitch.Pitch();pitch.diatonicNoteNum=clef.lowestLine+round((center+2*gap-y)*2/gap)
   alterations=[a for a in content[0] if a['c'] in ['\ue260','\ue261','\ue262'] and 0<x-a['origin'][0]<14 and abs(a['origin'][1]-y)<1]
   if alterations:state[(pitch.step,pitch.octave)]={'\ue260':-1,'\ue261':0,'\ue262':1}[min(alterations,key=lambda a:x-a['origin'][0])['c']]
   pitch.accidental=m.pitch.Accidental(state.get((pitch.step,pitch.octave),-1 if pitch.step=='B' else 0))
  tokens.append(dict(x=x,y=y,pitch=pitch,length=length,grace=grace,c=c))
 return tokens

def printed_grace_groups(data,contents,staffs):
 groups=[]
 for page,content in enumerate(contents):
  systems=sorted({b['system'] for b in data['measures'] if b['page']==page});rows={}
  for si in systems:
   for logical,centers in staffs[si].items():
    for j,center in enumerate(centers):rows[(si,logical-1 if logical<6 else 5+j)]=center
  assigned={}
  for c in content[0]:
   if c['c'] not in HEADS:continue
   key=min(rows,key=lambda key:abs(rows[key]-c['origin'][1]));assigned.setdefault(key,[]).append(c)
  for (si,pi),chars in assigned.items():
   small=sorted([c for c in chars if c['size']<15],key=lambda c:c['origin'][0]);clusters=[]
   for c in small:
    if clusters and c['origin'][0]-clusters[-1][-1]['origin'][0]<9:clusters[-1].append(c)
    else:clusters.append([c])
   center=rows[(si,pi)];gap=data['systems'][si]['interline']*595/1600
   clef=m.clef.BassClef() if pi in [3,6] else m.clef.Treble8vbClef() if pi==2 else m.clef.TrebleClef()
   def pitch(c):
    p=m.pitch.Pitch();p.diatonicNoteNum=clef.lowestLine+round((center+2*gap-c['origin'][1])*2/gap)
    p.accidental=m.pitch.Accidental(-1 if p.step=='B' else 0);return p.nameWithOctave
   for cluster in clusters:
    following=sorted([c for c in chars if c['size']>=15 and c['origin'][0]>cluster[-1]['origin'][0]+1],key=lambda c:c['origin'][0])
    if not following:raise ValueError('Grace group without following principal note')
    main=following[0];mx=main['origin'][0]
    bar=next(b for b in data['measures'] if b['system']==si and b['left']*595/1600-1<=mx<b['right']*595/1600)
    groups.append(dict(page=page+1,part=pi,measure=bar['label'],pitches=[pitch(c) for c in cluster],x=[c['origin'][0] for c in cluster],main=pitch(main),mainX=mx))
 return groups

def normalize_printed_graces(source,data,contents,staffs,audit):
 groups=printed_grace_groups(data,contents,staffs);records=[]
 for group in groups:
  pi=group['part'];number=group['measure'];bar=data['measures'][number-1]
  if (pi,number) in [(0,29),(0,45),(4,64),(5,63),(5,64)]:
   records.append(dict(part=pi,measure=number,page=group['page'],pitches=group['pitches'],main=group['main'],mode='complete-voice-rebuild'))
   continue
  b=list(source.parts[pi].getElementsByClass(m.stream.Measure))[number-1]
  def pdf_x(e):
   notes=e.notes if e.isChord else [e];xs=[float(n.style.absoluteX) for n in notes if n.style.absoluteX is not None]
   return (bar['left']+sum(xs)/len(xs)/b.layoutWidth*(bar['right']-bar['left']))*595/1600 if xs else None
  notes=list(b.recurse().notes)
  main_candidates=[e for e in notes if pdf_x(e) is not None and abs(pdf_x(e)-group['mainX'])<4]
  if not main_candidates:raise ValueError('Grace main note not found: '+str(group))
  main=min(main_candidates,key=lambda e:abs(pdf_x(e)-group['mainX'])+(0 if any(p.nameWithOctave==group['main'] for p in e.pitches) else 10))
  removed=[]
  for x in group['x']:
   choices=[e for e in notes if e is not main and e not in removed and pdf_x(e) is not None and abs(pdf_x(e)-x)<4]
   if choices:removed.append(min(choices,key=lambda e:abs(pdf_x(e)-x)))
  # Some grace heads are absent from the OMR export. The PDF, rather than
  # the count of recognized notes, determines the performed group.
  for e in sorted(removed,key=lambda e:F(e.getOffsetInHierarchy(b)),reverse=True):
   site=e.activeSite;at=F(e.offset);length=F(e.quarterLength);site.remove(e)
   if length:
    for other in list(site.notesAndRests):
     if F(other.offset)>=at+length:site.setElementOffset(other,F(other.offset)-length)
  site=main.activeSite;anchor=F(main.offset);length=F(main.quarterLength)
  previous=[e for e in site.notesAndRests if e is not main and F(e.offset)<anchor and F(e.offset)+F(e.quarterLength)==anchor]
  borrow=min(F(1,8),length/2)
  if previous:
   donor=max(previous,key=lambda e:F(e.offset));borrow=min(borrow,F(donor.quarterLength)/2)
   donor.duration=m.duration.Duration(F(donor.quarterLength)-borrow);donor.editorial['graceAdjusted']=True
   start=anchor-borrow
  else:
   start=anchor;site.setElementOffset(main,anchor+borrow);main.duration=m.duration.Duration(length-borrow)
  main.editorial['graceAdjusted']=True
  for i,pitch in enumerate(group['pitches']):
   n=m.note.Note(pitch,quarterLength=borrow/len(group['pitches']));n.editorial['performedGrace']=True
   site.insert(start+i*borrow/len(group['pitches']),n)
  records.append(dict(part=pi,measure=number,page=group['page'],pitches=group['pitches'],main=group['main'],anchor=str(anchor),borrow=str(borrow),removedOmrHeads=len(removed)))
 audit['graceGroups']=records

def realize_printed_mordents(source,data,contents,staffs,audit):
 """Require a matching PDF glyph; OMR alone contains false ornament detections."""
 import copy
 candidates=[]
 for pi,part in enumerate(source.parts):
  for bi,b in enumerate(part.getElementsByClass(m.stream.Measure)):
   bar=data['measures'][bi]
   for e in b.recurse().notes:
    if not any(isinstance(ex,m.expressions.GeneralMordent) for ex in e.expressions):continue
    clef=e.getContextByClass(m.clef.Clef);gap=data['systems'][bar['system']]['interline']*595/1600
    center=staffs[bar['system']][pi+1][0]
    head=max(e.notes,key=lambda n:n.pitch.midi) if e.isChord else e
    x=(bar['left']+float(head.style.absoluteX)/b.layoutWidth*(bar['right']-bar['left']))*595/1600
    y=center+2*gap-(head.pitch.diatonicNoteNum-clef.lowestLine)*gap/2
    candidates.append(dict(part=pi,measure=bi+1,page=bar['page'],x=x,y=y,offset=F(e.getOffsetInHierarchy(b)),element=e,head=head))
 used=set();records=[]
 for page,content in enumerate(contents):
  for mark in content[0]:
   if mark['c']!='\ue56c':continue
   x,y=mark['origin']
   choices=[c for c in candidates if c['page']==page and abs(c['x']-x)<10 and abs(c['y']-y)<55 and id(c['element']) not in used]
   if not choices:raise ValueError('Printed mordent has no musical anchor: '+str((page+1,x,y)))
   c=min(choices,key=lambda c:8*abs(c['x']-x)+abs(c['y']-y));e=c['element'];used.add(id(e))
   site=e.activeSite;at=F(e.offset);length=F(e.quarterLength)
   melody=m.note.Note(c['head'].pitch,quarterLength=length)
   melody.expressions=[copy.deepcopy(next(ex for ex in e.expressions if isinstance(ex,m.expressions.GeneralMordent)))]
   realized=m.expressions.realizeOrnaments(melody,keySig=e.getContextByClass(m.key.KeySignature) or m.key.KeySignature(-1))
   assert sum(F(n.quarterLength) for n in realized)==length
   site.remove(e)
   # The sign above a divisi chord ornaments its upper melody; sustain the lower voice.
   if e.isChord:
    lower=[copy.deepcopy(n) for n in e.notes if n is not c['head']]
    if lower:site.insert(at,m.chord.Chord(lower,quarterLength=length))
   for n in realized:
    n.editorial['performedOrnament']=True;site.insert(at,n);at+=F(n.quarterLength)
   records.append(dict(part=c['part'],measure=c['measure'],page=page+1,type='upper-mordent',pitch=c['head'].pitch.nameWithOctave,offset=str(c['offset']),duration=str(length),midi=[int(n.pitch.midi) for n in realized]))
 audit['ornaments']=records

def rebuild_voice(source,data,contents,staffs,pi,number,changes):
 b=list(source.parts[pi].getElementsByClass(m.stream.Measure))[number-1]
 bar=data['measures'][number-1];tokens=printed_tokens(data,contents,staffs,pi,number)
 original=list(b.recurse().notes);voice=m.stream.Voice(id='verified');offset=F(0);graces=[];previous=None
 for token in tokens:
  pitch=token['pitch'];length=token['length']
  if token['grace']:graces.append(token);continue
  e=m.note.Note(pitch) if pitch else m.note.Rest();e.duration=m.duration.Duration(length)
  if pitch:
   candidates=[]
   for old in original:
    for note in old.notes if old.isChord else [old]:
     if note.pitch.midi==pitch.midi and note.style.absoluteX is not None:
      x=(bar['left']+float(note.style.absoluteX)/b.layoutWidth*(bar['right']-bar['left']))*595/1600
      if abs(x-token['x'])<3:candidates.append(note)
   if candidates:e.tie=candidates[0].tie
  voice.insert(offset,e)
  if graces:
   borrow=F(1,8);anchor=offset
   if previous is not None:
    previous.duration=m.duration.Duration(F(previous.quarterLength)-borrow)
   else:
    voice.setElementOffset(e,offset+borrow);e.duration=m.duration.Duration(length-borrow);anchor+=borrow
   for j,g in enumerate(graces):
    n=m.note.Note(g['pitch'],quarterLength=borrow/len(graces));n.editorial['performedGrace']=True;voice.insert(anchor-borrow+j*borrow/len(graces),n)
   graces=[]
  previous=e;offset+=length
 assert offset==F(str(bar['quarterLength'])),(pi,number,offset,tokens)
 for e in list(b):
  if isinstance(e,(m.stream.Voice,m.note.GeneralNote)):b.remove(e)
 b.insert(0,voice);changes.append(dict(part=pi,measure=number,kind='complete printed voice'))

def repair_piano(source,changes):
 # Complete runs verified in the revised PDF. Lists are reading order;
 # Fraction durations follow the printed tuplet numerals, never note spacing.
 from score_repairs import replace,sequence
 def seq(pitches,lengths,start=0):return sequence(pitches.split() if isinstance(pitches,str) else pitches,lengths,F(start))
 def fix(pi,number,voices):
  replace(source,pi,number,voices);changes.append(dict(part=pi,measure=number,kind='verified printed piano voices'))
 fix(5,4,[[(0,['B-4','D5'],F(3,2)),(F(3,2),'A5',F(1,2)),(2,['B-4','G5'],1),(3,['E5','C6'],1)],[(1,'F4',F(1,2)),(F(3,2),'G4',F(1,2)),(3,'D4',1)]])
 fix(5,28,[[ (i,p,1) for i,p in enumerate([['D4','F4','B-4','D5'],['B-3','D4'],['B-3','D4','G4'],['E4','C5']]) ]])
 fix(6,28,[[(0,'G2',2),(2,'C2',2)],seq([None,'D3','F3','D3',None,'C3','B-3','G3'],[F(1,2)]*8)])
 run=[None,'E3','G3','A3','C4','E4','G4','E4','C4','A3','G3','E3',None,'A2','D3','E3','F#3','A3','D4']
 fix(6,39,[seq(run,[F(1,6)]*18+[F(1)]),[(0,'A2',2),(2,'D2',2)]])
 run='D4 G4 A4 D5 G5 A5 G5 D5 G5 A5 D6 G6 A6 D7 A6 G6 D6 A5 G5 D6 A5 G5 D5 A4 G4 D4'
 fix(5,42,[seq(run,[F(1,9)]*18+[F(1,8)]*8,1)])
 fix(6,42,[[(0,['B-1','B-2'],4)],seq([None,'D3','F3','B-3'],[F(1,2)]+[F(1,6)]*3)])
 run='C4 E4 G4 C5 E5 G5 A5 G5 E5 C5 A4 G4 E4 G4 A4 C5 E5 G5'
 fix(5,43,[seq(run,[F(1,9)]*18,1)+[(3,['C5','C6'],F(1,2)),(F(7,2),['D5','D6'],F(1,2))]])
 fix(6,43,[[(0,['A1','A2'],4)],seq([None,'C3','E3','G3','A3'],[F(1,2)]+[F(1,8)]*4)+seq('E4 C4 A3 G3 E3',[F(1,6)]*3+[F(1,4)]*2,3)])
 run=[None,'D3','F3','G3','B-3','D4','F4','D4','B-3','G3','F3','D3',None,'C3','G3','B-3','C4','D4','F4','D4','C4','B-3','G3','C3']
 fix(5,44,[[(0,['D4','D5'],F(3,2))],seq(run,[F(1,6)]*24)])
 fix(6,44,[[(0,'G2',2),(2,'C2',2)]])
 run=[None,'C3','G3','A3','C4','F4','G4','F4','C4','A3','G3','C3',None,'C3','G3','A3','C4','G4']
 fix(5,45,[seq(run,[F(1,6)]*18)+[(3,['A4','A5'],F(1,2)),(F(7,2),['C5','C6'],F(1,2))]])
 fix(6,45,[[(0,'F2',2),(2,'F2',2)],[(3,['C4','E-4'],1)]])
 chords=[['D5','F5','B-5','D6'],['C5','F5','B-5','C6'],['C5','F5','B-5','C6'],['A4','A5'],['G4','G5'],['A4','A5'],['C5','C6'],['G4','G5']]
 fix(5,61,[seq(chords,[F(3,4),F(1,4)]+[F(1,2)]*6),[(2,['C5','E5'],2)]])
 run=[None,'F2','B-2','C3','D3','F3','B-3','F3','D3','C3','B-2','F2',None,'G2','C3','E3','G3','B-3','C4','B-3','G3','E3','C3','G2']
 fix(6,61,[seq(run,[F(1,6)]*24),[(0,'B-1',2),(2,'C2',2)]])
 fix(5,62,[[(0,['G4','G5'],2),(2,['G4','B4','D5','F5'],2)]])
 run=[None,'A2','D3','F3','G3','A3','D4','A3','G3','F3','D3',None,'D3','G3','B3','D4','F4','A4']
 fix(6,62,[seq(run,[F(1,6)]*6+[F(1,5)]*5+[F(1,6)]*6+[F(1)]),[(0,'D2',2),(2,'G2',2)]])
 run=[None,'F3','B-3','C4','D4','F4']
 voices=[seq(run,[F(1,6)]*6)+[(1,'A4',1)]+seq([None,'G3','B-3','C4','D4','G4'],[F(1,6)]*6,2),[(F(5,2),'D5',F(1,4)),(F(11,4),'F5',F(1,8)),(F(23,8),'D5',F(1,16)),(F(47,16),'F5',F(1,16)),(3,['G4','D5'],1)]]
 fix(5,63,voices);fix(6,63,[[(0,'B-2',2),(2,'C3',2)]])
 run=[None,'G3','A3','D4','F4','A4']
 fix(5,64,[seq(run,[F(1,6)]*6)+[(1,'D5',1)]+seq([None,'G3','A3','C4','D4','F4'],[F(1,6)]*6,2)+[(3,'G4',1)],[(0,'D5',F(1,8)),(F(1,8),'A5',F(31,8))]])
 fix(6,64,[[(0,'D3',2),(2,'D3',2)]])
 for number,offsets in [(63,[F(23,8),F(47,16)]),(64,[F(0)])]:
  b=list(source.parts[5].getElementsByClass(m.stream.Measure))[number-1]
  for e in b.recurse().notes:
   if F(e.getOffsetInHierarchy(b)) in offsets:e.editorial['performedGrace']=True
 b=list(source.parts[6].getElementsByClass(m.stream.Measure))[67]
 for e in b.recurse().notes:
  if not e.isChord and e.pitch.nameWithOctave=='D2' and e.quarterLength==4:e.activeSite.setElementOffset(e,0)
