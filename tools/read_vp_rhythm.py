"""Read printed VP duration symbols, then accumulate exact rational beat offsets.

Geometry associates heads, stems, beams, flags and dots; it NEVER determines time.
The resulting musical symbols can be reviewed and exported through music21.
"""
from pathlib import Path
from fractions import Fraction as F
import json,zipfile,xml.etree.ElementTree as ET,collections,re,sys
import fitz
ROOT=Path(__file__).resolve().parents[1]
HEADS={'\u00bf':F(1),'\u0153':F(1),'\u02d9':F(2),'w':F(4),'O':F(4)}
RESTS={'\u0152':F(1),'\u00d3':F(2),'\u2211':None,'\u2030':F(1,2),'\u2248':F(1,4)}
def read(data,part_id="5",margin=(8,3)):
 records=[];warnings=[];pdf=fitz.open(ROOT/'data/let-it-go.pdf');system_index=0
 with zipfile.ZipFile(ROOT/'data/omr/let-it-go-corrected.omr') as book:
  for pi,page in enumerate(pdf):
   sheet=ET.fromstring(book.read(f'sheet#{pi+1}/sheet#{pi+1}.xml'));scale=page.rect.width/int(sheet.find('picture').get('width'));to_app=1600/page.rect.width
   chars=[dict(c,font=span['font']) for b in page.get_text('rawdict')['blocks'] for line in b.get('lines',[]) for span in line['spans'] for c in span['chars']]
   lines=[];beams=[];curves=[]
   for drawing in page.get_drawings():
    for item in drawing['items']:
     if item[0]=='l' and abs(item[1].x-item[2].x)<.2 and 8<abs(item[1].y-item[2].y)<45:lines.append((item[1].x,min(item[1].y,item[2].y),max(item[1].y,item[2].y)))
    r=drawing['rect']
    if drawing.get('fill') is not None and drawing['items'] and all(i[0]=='l' for i in drawing['items']) and r.width>5 and 1<r.height<18 and r.height/r.width<.6:beams.append(r)
   for system in sheet.findall('./page/system'):
    measures=[m for m in data['measures'] if m['system']==system_index];part=system.find(f"part[@id='{part_id}']")
    if part is not None:
     ys=[float(p.get('y'))*scale for p in part.findall('./staff/lines/line/point')];top,bottom=min(ys),max(ys)
     musicfonts={c['font'] for c in chars if c['c'] in ['\u0153','\u00bf','\u2211'] and top-margin[0]<=c['origin'][1]<=bottom+margin[1]}
     symbols=[c for c in chars if c['font'] in musicfonts];syllables=[w for w in page.get_text('words') if bottom+2<w[1]<bottom+26 and re.search(r'tk|ka|shoo|knock|bom|pff|doo|doh|koo|dun|doom',w[4],re.I)]
     for m in measures:
      items=[c for c in symbols if c['c'] in HEADS or c['c'] in RESTS];items=[c for c in items if top-margin[0]<=c['origin'][1]<=bottom+margin[1] and m['left']<=c['origin'][0]*to_app<m['right']]
      groups=[]
      for c in sorted(items,key=lambda c:c['origin'][0]):
       x,y=c['origin'];rest=c['c'] in RESTS
       candidates=[line for line in lines if min(abs(line[0]-x-.28),abs(line[0]-x-4.6))<1.1 and line[1]-3<=y<=line[2]+3]
       stem=min(candidates,key=lambda line:min(abs(line[0]-x-.28),abs(line[0]-x-4.6)),default=None)
       same_stem=groups and stem and groups[-1].get('stem') and abs(groups[-1]['stem'][0]-stem[0])<.6
       if not rest and groups and (abs(groups[-1]['x']-x)<1 or same_stem) and not groups[-1]['rest']:groups[-1]['heads'].append(c)
       else:groups.append(dict(x=x,rest=rest,heads=[c],stem=stem))
      offset=F(0);events=[]
      for group in groups:
       durations=[];notations=[]
       for c in group['heads']:
        x,y=c['origin'];symbol=c['c'];beam_count=0;flag_count=0
        if group['rest']:duration=RESTS[symbol] or F(str(m['quarterLength']))
        else:
         candidates=[line for line in lines if min(abs(line[0]-x-.28),abs(line[0]-x-4.6))<1.1 and line[1]-3<=y<=line[2]+3]
         stem=min(candidates,key=lambda line:min(abs(line[0]-x-.28),abs(line[0]-x-4.6)),default=None)
         if stem:
          beam_count=sum(1 for r in beams if r.x0-.7<=stem[0]<=r.x1+.7 and r.y0<=stem[2]+1 and r.y1>=stem[1]-1)
          flag_count=max([1 if f['c'] in ['j','J'] else 2 for f in symbols if f['c'] in ['j','J','r','R'] and abs(f['origin'][0]-stem[0])<1.1 and stem[1]-5<=f['origin'][1]<=stem[2]+5]+[0])
         duration=HEADS[symbol]/(2**max(beam_count,flag_count))
        dots=[d for d in symbols if d['c']=='.' and 4.8<d['origin'][0]-x<11 and abs(d['origin'][1]-y)<4]
        if dots:duration*=sum((F(1,2**i) for i in range(len(dots)+1)),F(0))
        durations.append(duration);notations.append(dict(symbol=symbol,beams=beam_count,flags=flag_count,dots=len(dots),duration=str(duration)))
       duration=max(durations);event=dict(offset=str(offset),duration=str(duration),rest=group['rest'],x=round(group['x'],3),notation=notations,heads=[])
       if not group['rest']:
        for c in group['heads']:
         x,y=c['origin'];word=min(syllables,key=lambda w:abs((w[0]+w[2])/2-x)) if syllables else None;text=word[4] if word and min(abs(word[0]-x),abs((word[0]+word[2])/2-x))<22 else ''
         event['heads'].append(dict(head='cross' if c['c']=='\u00bf' else 'wind' if c['c']=='O' else 'ordinary',syllable=text,x=round(x*to_app,4),y=round(y,4)))
       events.append(event);offset+=duration
      expected=F(str(m['quarterLength']));record=dict(measure=m['label'],page=pi+1,expected=str(expected),total=str(offset),events=events)
      if offset!=expected:warnings.append(dict(measure=m['label'],expected=str(expected),total=str(offset),pattern=[('r' if e['rest'] else 'n')+e['duration'] for e in events]))
      records.append(record)
    system_index+=1
 return records,warnings
if __name__=='__main__':
 data=json.loads((ROOT/'choir-studio/public/songs/let-it-go/song.json').read_text(encoding='utf8'));records,warnings=read(data)
 (ROOT/'inspection/vp-rhythm-symbols.json').write_text(json.dumps(dict(records=records,warnings=warnings),ensure_ascii=False,indent=2),encoding='utf8')
 print('Bars',len(records),'valid',len(records)-len(warnings),'warnings',len(warnings));print(json.dumps(warnings,ensure_ascii=True))
