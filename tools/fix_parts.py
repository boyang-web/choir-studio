"""Correct bottom-aligned OMR part guesses using the actual staff order in these two scores."""
from pathlib import Path
import zipfile, xml.etree.ElementTree as E
root=Path(__file__).resolve().parents[1]
for song in ['let-it-go','chi-le-ge']:
 source=root/'data/omr'/f'{song}.omr'
 target=root/'data/omr'/f'{song}-corrected.omr'
 with zipfile.ZipFile(source) as z,zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED) as out:
  book=E.fromstring(z.read('book.xml'))
  for score in book.findall('score'):
   for i,p in enumerate(score.findall('logical-part')):
    name=['Soprano','Alto','Tenor','Bass','Vocal Percussion' if song=='let-it-go' else 'Ocarina','Piano'][i]
    p.set('name',name);p.set('abbreviation',['S','A','T','B','VP' if song=='let-it-go' else 'Oc','Pno'][i]);p.set('midi-program','1' if i==5 else ('80' if i==4 else '54'))
  updates={}
  for sh in book.findall('sheet'):
   num=sh.get('number');name=f'sheet#{num}/sheet#{num}.xml';sheet=E.fromstring(z.read(name))
   for sys,ref in zip(sheet.findall('./page/system'),sh.findall('./page/system')):
    parts=sys.findall('part');refs=ref.findall('part')
    ids={3:[1,2,6],5:[1,2,3,4,6],6:[1,2,3,4,5,6]}[len(parts)]
    for part,pr,i in zip(parts,refs,ids):
     part.set('id',str(i));pr.set('logical-id',str(i));pr.set('manual','true')
   # Audiveris 5.11 throws during export if a dynamic wedge has no rhythmic anchor.
   # Dynamics remain visible in the original PDF; remove them from the playback export only.
   wedge_ids={x.get('id') for x in sheet.iter('wedge')}
   for parent in sheet.iter():
    for child in list(parent):
     if child.tag=='wedge' or (child.tag=='relation' and (child.get('source') in wedge_ids or child.get('target') in wedge_ids)):
      parent.remove(child)
   updates[name]=E.tostring(sheet,encoding='utf-8',xml_declaration=True)
  updates['book.xml']=E.tostring(book,encoding='utf-8',xml_declaration=True)
  for name in z.namelist():out.writestr(name,updates.get(name,z.read(name)))
 print('Corrected',target.name)
