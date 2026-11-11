"""Verified corrections against chi-le-ge PDF pp. 3, 5, 6, 8, 9.

Audiveris retains pitch heads that its rhythm exporter drops after an overfull
voice. Reuse those heads; assign the explicitly printed tuplet/rest structure.
Horizontal positions determine reading order only, never elapsed time.
"""
from fractions import Fraction as F
from pathlib import Path
import zipfile,xml.etree.ElementTree as ET,collections,copy
import music21 as m
ROOT=Path(__file__).resolve().parents[1]
def bar(source,part,number):return list(source.parts[part].getElementsByClass(m.stream.Measure))[number-1]
def replace(source,part,number,voices):
 b=bar(source,part,number)
 for obj in list(b):
  if isinstance(obj,(m.stream.Voice,m.note.GeneralNote)):b.remove(obj)
 for index,spec in enumerate(voices):
  v=m.stream.Voice(id=str(index+1));b.insert(0,v)
  for offset,pitch,length in spec:
   n=m.note.Rest() if pitch is None else m.chord.Chord(pitch) if isinstance(pitch,list) else m.note.Note(pitch)
   n.duration=m.duration.Duration(F(length));v.insert(F(offset),n)
 return b
def sequence(tokens,durations,start=F(0)):
 assert len(tokens)==len(durations),(len(tokens),len(durations))
 result=[];offset=F(start)
 for pitch,length in zip(tokens,durations):result.append((offset,pitch,F(length)));offset+=F(length)
 return result
def original_tokens(source,data,number):
 measure=data['measures'][number-1];page=measure['page'];local_system=sorted({b['system'] for b in data['measures'] if b['page']==page}).index(measure['system'])
 with zipfile.ZipFile(ROOT/'data/omr/chi-le-ge-corrected.omr') as z:
  sheet=ET.fromstring(z.read(f'sheet#{page+1}/sheet#{page+1}.xml'));system=sheet.findall('./page/system')[local_system]
 part=system.find("part[@id='6']");staffs=[st.get('id') for st in part.findall('staff')];inters={n.get('id'):n for n in system.findall('./sig/inters/*')};relations=system.findall('./sig/relations/relation')
 local_measure=[b['label'] for b in data['measures'] if b['system']==measure['system']].index(number);original=part.findall('measure')[local_measure]
 contain=collections.defaultdict(list);alters={}
 for relation in relations:
  if relation.find('containment') is not None:contain[relation.get('source')].append(inters[relation.get('target')])
  if relation.find('alter-head') is not None:alters[relation.get('target')]=inters[relation.get('source')].get('shape')
 ordered=[]
 for tag in ['head-chords','rest-chords']:
  for cid in (original.findtext(tag) or '').split():
   chord=inters[cid];heads=contain[cid];bounds=chord.find('bounds');ordered.append((int(bounds.get('x')),chord,heads))
 accidental_state={};result=[]
 for x,chord,heads in sorted(ordered,key=lambda t:t[0]):
  pitches=[];shapes=[];staff_index=staffs.index(chord.get('staff'))
  for head in heads:
   shapes.append(head.get('shape'))
   if head.tag=='rest':continue
   si=staffs.index(head.get('staff') or chord.get('staff'));b=bar(source,5+si,number);clef=b.getContextByClass(m.clef.Clef);key=b.getContextByClass(m.key.KeySignature) or m.key.KeySignature(-1)
   pitch=m.pitch.Pitch();pitch.diatonicNoteNum=clef.lowestLine+4-round(float(head.get('pitch')))
   identity=(si,pitch.step,pitch.octave);shape=alters.get(head.get('id'))
   if shape:
    accidental_state[identity]=0 if 'NATURAL' in shape else -2 if 'DOUBLE_FLAT' in shape else 2 if 'DOUBLE_SHARP' in shape else -1 if 'FLAT' in shape else 1
   accidental=accidental_state.get(identity)
   pitch.accidental=m.pitch.Accidental(accidental) if accidental is not None else key.accidentalByStep(pitch.step)
   pitches.append(pitch.nameWithOctave)
  result.append(dict(x=x,pitches=pitches,shapes=shapes,staff=staff_index))
 return result
def single_run(tokens,staff=None):
 return [None if not t['pitches'] else t['pitches'][0] for t in tokens if (staff is None or t['staff']==staff) and (t['shapes']==['ONE_16TH_REST'] or len(t['pitches'])==1 and t['shapes']==['NOTEHEAD_BLACK'])]
def basses(tokens):return [t['pitches'] for t in tokens if t['staff']==1 and t['pitches'] and set(t['shapes'])=={'NOTEHEAD_VOID'}]
def add_graces(source,part,number,anchor,pitches,audit):
 b=bar(source,part,number);anchor=F(anchor);candidates=[e for e in b.recurse().notes if F(e.getOffsetInHierarchy(b))==anchor]
 if not candidates:return
 target=candidates[-1];site=target.activeSite;earlier=[e for e in site.notes if F(e.offset)<F(target.offset) and F(e.offset)+F(e.duration.quarterLength)==F(target.offset)]
 if not earlier:return
 prev=earlier[-1];borrow=min(F(1,8),F(prev.duration.quarterLength)/2);prev.duration=m.duration.Duration(F(prev.duration.quarterLength)-borrow)
 at=F(target.offset)-borrow
 for pitch in pitches:
  n=m.note.Note(pitch,quarterLength=borrow/len(pitches));n.editorial['performedGrace']=True;site.insert(at,n);at+=borrow/len(pitches)
 audit.setdefault('graces',[]).append(dict(part=part,measure=number,anchor=str(anchor),pitches=pitches,borrowed=str(borrow)))
def apply(source,data,audit):
 if data['id']!='chi-le-ge':return
 audit['verifiedPianoRepairs']=[]
 # Bar 23: upper triplet begins on beat 2; the lower eighth-note run crosses
 # staves. A dropped E5 and malformed tie must not create a silent forward gap.
 replace(source,5,23,[sequence(['A5','C6','D6','G5','F5','E5',None],[1,F(1,3),F(1,3),F(1,3),F(1,2),1,F(1,2)]),sequence([None,'A3','E4','D4',['B3','G4','A4'],None],[F(1,2)]*4+[F(3,2),F(1,2)])])
 replace(source,6,23,[[(0,'D3',F(7,2)),(F(7,2),None,F(1,2))]])
 for part in [2,3]:
  b=bar(source,part,23)
  held=[n for n in b.recurse().notes if F(n.getOffsetInHierarchy(b)) in [F(3,4),F(1),F(2)]]
  for n,kind in zip(held,['start','continue','stop']):n.tie=m.tie.Tie(kind)
 audit['verifiedPianoRepairs'].append(23)
 # Printed 9:8 thirty-second runs, not unmodified thirty-seconds.
 for number,groups in [(42,[9,9,8]),(43,[9,9])]:
  b=bar(source,5,number);events=list(b.recurse().notes);offset=F(1);spec=[(0,None,1)];cursor=0
  for count in groups:
   for e in events[cursor:cursor+count]:
    pitch=[n.pitch.nameWithOctave for n in e.notes] if e.isChord else e.pitch.nameWithOctave;spec.append((offset,pitch,F(1,count)));offset+=F(1,count)
   cursor+=count
  if number==43:
   for e in events[cursor:]:spec.append((offset,[n.pitch.nameWithOctave for n in e.notes] if e.isChord else e.pitch.nameWithOctave,F(1,2)));offset+=F(1,2)
  assert offset==4
  replace(source,5,number,[spec]);audit['verifiedPianoRepairs'].append(number)
 # Bar 43 ending: three sixteenths in the time of two, then two sixteenths.
 b=bar(source,6,43)
 for v in b.getElementsByClass(m.stream.Voice):
  if str(v.id)=='7':
   es=list(v.notes);assert len(es)==5
   for e,(at,length) in zip(es,[(3,F(1,6)),(F(19,6),F(1,6)),(F(10,3),F(1,6)),(F(7,2),F(1,4)),(F(15,4),F(1,4))]):v.setElementOffset(e,F(at));e.duration=m.duration.Duration(length)
 # Recover heads retained in the original Audiveris project but lost during
 # overfull MusicXML export; their printed sextuplet structure gives time.
 for number,pattern in [(39,[6,6,6,1]),(44,[6,6,6,6]),(45,[6,6,6]),(62,[6,5,6,1])]:
  tokens=original_tokens(source,data,number);run=single_run(tokens,1 if number in [39,62] else None);durations=[F(1,n) for n in pattern for _ in range(n)];spec=sequence(run,durations);held=basses(tokens);assert len(held)==2
  bass=[(0,held[0],2),(2,held[1],2)]
  if number in [39,62]:
   replace(source,6,number,[spec,bass])
   if number==39:
    b=bar(source,5,number)
    for e in b.recurse().notes:
     if e.isChord and F(e.duration.quarterLength)==2:e.activeSite.setElementOffset(e,F(2))
  else:
   voices=[spec]
   if number==45:
    chords=[t for t in tokens if len(t['pitches'])>1 and set(t['shapes'])=={'NOTEHEAD_BLACK'}];merged=[]
    for t in chords:
     if merged and t['x']-merged[-1]['x']<5:merged[-1]['pitches']+=t['pitches']
     else:merged.append(copy.deepcopy(t))
    assert len(merged)==2;voices.append([(3,merged[0]['pitches'],F(1,2)),(F(7,2),merged[1]['pitches'],F(1,2))])
   replace(source,5,number,voices);replace(source,6,number,[bass])
  audit['verifiedPianoRepairs'].append(number)
 # Bars 63/64: cross-staff sextuplets plus independent melody and bass voices.
 run63=sequence([None,'F3','B-3','C4','D4','F4','A4',None,'G3','B-3','C4','D4','G4','G4'],[F(1,6)]*6+[1]+[F(1,6)]*6+[1])
 replace(source,5,63,[run63,[(0,None,2),(2,None,F(1,2)),(F(5,2),'D5',F(1,4)),(F(11,4),'F5',F(1,4)),(3,'D5',1)]])
 melody=list(bar(source,5,63).getElementsByClass(m.stream.Voice))[0]
 for e in melody.notes:
  if F(e.offset)==F(17,6):e.tie=m.tie.Tie('start')
  if F(e.offset)==3:e.tie=m.tie.Tie('stop')
 replace(source,6,63,[[(0,'B-2',2),(2,'C3',2)]])
 replace(source,5,64,[[(0,'A5',4)],sequence([None,'G3','A3','D4','F4','A4','D5',None,'G3','A3','C4','D4','F4','G4'],[F(1,6)]*6+[1]+[F(1,6)]*6+[1])])
 replace(source,6,64,[[(0,'D3',2),(2,'D3',2)]])
 audit['verifiedPianoRepairs'] += [63,64]
 # Verified acciaccaturas: borrow time before the main note, never add beats.
 for part,number,anchor,pitches in [(2,19,F(1,2),['A4','C5']),(3,19,F(1,2),['A3','C4']),(1,21,F(1,2),['G3','B-3']),(2,21,F(1,2),['A4','C5']),(3,21,F(1,2),['A3','C4']),(2,23,F(3,4),['F4']),(3,23,F(3,4),['G3']),(5,63,F(3),['D5','F5'])]:add_graces(source,part,number,anchor,pitches,audit)
 # Genuine printed mordent marks; use music21's ornament realization. Do not
 # turn every noisy OMR "trill" detection into an invented ornament.
 for part,number in [(0,43),(4,38),(4,42),(4,45)]:
  b=bar(source,part,number)
  for e in list(b.recurse().notes):
   if not e.isNote or not any(isinstance(ex,m.expressions.InvertedMordent) for ex in e.expressions):continue
   site=e.activeSite;at=F(e.offset);length=F(e.duration.quarterLength);notes=m.expressions.realizeOrnaments(e,keySig=e.getContextByClass(m.key.KeySignature));assert sum(F(n.duration.quarterLength) for n in notes)==length;site.remove(e)
   for note in notes:note.editorial['performedOrnament']=True;site.insert(at,note);at+=F(note.duration.quarterLength)
   audit.setdefault('ornaments',[]).append(dict(part=part,measure=number,type='mordent'))
