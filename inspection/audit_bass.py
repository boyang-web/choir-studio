import sys,json,zipfile,statistics,xml.etree.ElementTree as ET
from pathlib import Path
from fractions import Fraction as F
root=Path(__file__).resolve().parents[1]
sys.path[:0]=[str(root/'tools/python-libs'),str(root/'tools')]
import new_score_symbols as s
r=Path(__file__).resolve().parents[1];d=json.loads((r/'choir-studio/public/songs/chi-le-ge/song.json').read_text('utf8'));contents=s.pages();staffs=[]
with zipfile.ZipFile(r/'data/revisions/2026-10-26/omr/chi-le-ge-corrected.omr') as z:
 for pi in range(10):
  sh=ET.fromstring(z.read(f'sheet#{pi+1}/sheet#{pi+1}.xml'));scale=595/int(sh.find('picture').get('width'))
  for sy in sh.findall('./page/system'):
   staffs.append({int(p.get('id')):[statistics.mean(float(pt.get('y'))*scale for pt in st.findall('./lines/line/point')) for st in p.findall('staff')] for p in sy.findall('part')})
ppq=d['midi']['ppq'];ns=next(p for p in d['parts'] if p['id']=='bass')['notes'];report=[]
for num in range(1,70):
 bar=d['measures'][num-1];ts=s.printed_tokens(d,contents,staffs,3,num);expected=[];pos=F(0);graces=[]
 for t in ts:
  if t['grace']:graces.append(t);continue
  start=pos;end=pos+t['length']
  if graces:
   borrow=F(1,8)
   if expected and expected[-1][1]==pos:expected[-1][1]-=borrow;anchor=pos-borrow
   else:anchor=pos;start+=borrow
   for j,g in enumerate(graces):expected.append([anchor+j*borrow/len(graces),anchor+(j+1)*borrow/len(graces),g['pitch'].midi])
   graces=[]
  if t['pitch'] is not None:expected.append([start,end,t['pitch'].midi])
  pos=end
 actual=[]
 for n in ns:
  start=F(n['ticks']-bar['ticks'],ppq);end=start+F(n['durationTicks'],ppq)
  if start<pos and end>0:actual.append([max(F(0),start),min(pos,end),n['midi']])
 points=sorted({F(0),pos}|{p for note in expected+actual for p in note[:2]});diff=[]
 for a,b in zip(points,points[1:]):
  mid=(a+b)/2;e=sorted(n[2] for n in expected if n[0]<=mid<n[1]);v=sorted(n[2] for n in actual if n[0]<=mid<n[1])
  if e!=v:diff.append(dict(start=str(a),end=str(b),printed=e,played=v))
 report.append(dict(measure=num,printedBeats=str(pos),expectedBeats=bar['quarterLength'],differences=diff))
 if diff or pos!=F(str(bar['quarterLength'])):print(report[-1])
(r/'inspection/bass-score-audit.json').write_text(json.dumps(report,indent=2),'utf8')

assert len(report)==69 and all(not b["differences"] and F(b["printedBeats"])==F(str(b["expectedBeats"])) for b in report), "Bass differs from the printed score; inspect bass-score-audit.json"
print("Bass PDF pitch/time audit: all 69 bars passed (ties and borrowed grace time included).")
