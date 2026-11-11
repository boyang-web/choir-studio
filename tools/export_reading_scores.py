"""Extract original PDF graphics and geometry for lossless, bar-level reflow.

No pitches, lyrics or musical symbols are regenerated from OMR. OMR supplies only
bar boundaries and staff measurements. Vector PDF paths stay vector; scanned PDF
images remain embedded at their original resolution inside the SVG.
"""
from pathlib import Path
import json, statistics, zipfile, xml.etree.ElementTree as ET
import fitz
ROOT=Path(__file__).resolve().parents[1]
for sid in ['chi-le-ge','let-it-go']:
 target=ROOT/'choir-studio/public/songs'/sid
 data=json.loads((target/'song.json').read_text(encoding='utf-8'))
 pdf=fitz.open(ROOT/'data'/f'{sid}.pdf')
 omr=(ROOT/data['import']['musicxml']).with_suffix('.omr') if data['import'].get('revision') else ROOT/'data/omr'/f'{sid}-corrected.omr'
 with zipfile.ZipFile(omr) as book:
  system_index=0
  for page_index,page in enumerate(pdf):
   scale=1600/page.rect.width
   svg=page.get_svg_image(matrix=fitz.Matrix(scale,scale),text_as_path=True)
   svg_root=ET.fromstring(svg);viewbox=[float(v) for v in svg_root.get('viewBox').split()]
   name=f'original-{page_index+1:02}.svg';(target/name).write_text(svg,encoding='utf-8')
   data['pages'][page_index].update(svg=name,svgWidth=viewbox[2],svgHeight=viewbox[3],sourceType='scan' if page.get_images() else 'vector')
   sheet=ET.fromstring(book.read(f'sheet#{page_index+1}/sheet#{page_index+1}.xml'))
   omr_scale=1600/int(sheet.find('picture').get('width'))
   for source_system in sheet.findall('./page/system'):
    system=data['systems'][system_index]
    staves=source_system.findall('./part/staff')
    tops=[];gaps=[];headers=[]
    for staff in staves:
     lines=staff.findall('./lines/line');ys=[]
     for line in lines:
      pts=line.findall('point');ys.append(sum(float(p.get('y')) for p in pts)/len(pts)*omr_scale)
     if ys:
      tops.append(ys[0]);gaps.extend(b-a for a,b in zip(ys,ys[1:]))
     header=staff.find('header')
     if header is not None:headers.append(float(header.get('stop'))*omr_scale)
    first=next(m for m in data['measures'] if m['system']==system_index)
    first_note=min((p['x'] for p in first['positions']),default=first['right'])
    # Header ends before the first musical event: no notehead is hidden by a crop.
    right=min(max(headers,default=first['left']+40)+5,first_note-9)
    system.update(interline=round(statistics.median(gaps),4),headerRight=round(max(first['left']+1,right),4),staffTop=round(min(tops),4))
    system_index+=1
 assert system_index==len(data['systems'])
 data['reading']={'version':2,'method':'original-pdf-graphics','description':'Original PDF graphics reflowed at bar boundaries; no semantic re-engraving.'}
 (target/'song.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
 print(sid,len(data['pages']),'original SVG pages,',system_index,'systems',flush=True)
