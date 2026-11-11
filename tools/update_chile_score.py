"""Import the 2026-10-26 ten-page edition, keeping the old edition archived.

Run after Audiveris transcription to data/revisions/2026-10-26/omr.
Original PDF artwork is retained; audio timing comes exclusively from MusicXML.
"""
from pathlib import Path
from fractions import Fraction
import sys, json, zipfile, shutil, statistics, subprocess, os, hashlib
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools/python-libs'))
import fitz
from PIL import Image
import music21 as m21

REV = ROOT/'data/revisions/2026-10-26'
TARGET = ROOT/'choir-studio/public/songs/chi-le-ge'
NAMES = ['Soprano', 'Alto', 'Tenor', 'Bass', 'Ocarina', 'Piano']

def correct_parts():
    source = REV/'omr/chi-le-ge.omr'
    target = REV/'omr/chi-le-ge-corrected.omr'
    with zipfile.ZipFile(source) as book, zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as out:
        tree = ET.fromstring(book.read('book.xml'))
        for score in tree.findall('score'):
            parts = score.findall('logical-part')
            assert len(parts) == 6, len(parts)
            for i, part in enumerate(parts):
                part.set('name', NAMES[i]); part.set('abbreviation', ['S','A','T','B','Oc','Pno'][i])
                part.set('midi-program', '1' if i == 5 else '80' if i == 4 else '54')
        updates = {}
        for sh in tree.findall('sheet'):
            n = sh.get('number'); name = f'sheet#{n}/sheet#{n}.xml'
            sheet = ET.fromstring(book.read(name))
            for system, ref in zip(sheet.findall('./page/system'), sh.findall('./page/system')):
                parts = system.findall('part'); refs = ref.findall('part')
                ids = {5:[1,2,3,4,6],6:[1,2,3,4,5,6]}[len(parts)]
                for part, pr, logical in zip(parts, refs, ids):
                    part.set('id', str(logical)); pr.set('logical-id', str(logical)); pr.set('manual','true')
            # Audiveris wedges without anchors crash its MusicXML exporter.
            wedges = {e.get('id') for e in sheet.iter('wedge')}
            for parent in sheet.iter():
                for child in list(parent):
                    if child.tag == 'wedge' or (child.tag == 'relation' and (child.get('source') in wedges or child.get('target') in wedges)):
                        parent.remove(child)
            updates[name] = ET.tostring(sheet, encoding='utf-8', xml_declaration=True)
        updates['book.xml'] = ET.tostring(tree, encoding='utf-8', xml_declaration=True)
        for name in book.namelist(): out.writestr(name, updates.get(name, book.read(name)))
    java = ROOT/'tools/audiveris/Audiveris/runtime/bin/java.exe'
    env = dict(os.environ, APPDATA=str(ROOT/'tools/state'))
    with (ROOT/'tools/new-score-export.log').open('w', encoding='utf8') as log:
        subprocess.run([str(java), '-Djava.awt.headless=true', '-cp', str(ROOT/'tools/audiveris/Audiveris/app/*'), 'Audiveris', '-batch', '-export', '-output', str(REV/'omr'), '--', str(target)], env=env, stdout=log, stderr=subprocess.STDOUT, check=True)

def generate():
    mxl = REV/'omr/chi-le-ge-corrected.mxl'
    score = m21.converter.parse(mxl, forceSource=True)
    print('Source parts:', [(p.partName, len(list(p.getElementsByClass(m21.stream.Measure)))) for p in score.parts], flush=True)
    backup = ROOT/'data/revisions/pre-2026-10-26'
    if not backup.exists():
        backup.mkdir(parents=True)
        shutil.copytree(TARGET, backup/'chi-le-ge')
        shutil.copy2(ROOT/'data/chi-le-ge.pdf', backup/'chi-le-ge.pdf')
        shutil.copy2(ROOT/'inspection/chi-le-ge-musical-audit.json', backup/'musical-audit.json')
    old = json.loads((backup/'chi-le-ge/song.json').read_text('utf8'))
    data = {k:old[k] for k in ['id','title','tag','tempo','subtitle']}
    data.update(pages=[], systems=[], measures=[], beats=[], parts=[{k:p[k] for k in ['id','name','english','letter']} for p in old['parts']])
    for part in data['parts']:
        if part['id'] == 'alto':
            part['name'] = '女中音'
    data['subtitle'] = '\u5218\u6d32 \u4f5c\u66f2 \u00b7 \u5434\u660a \u7f16\u914d / 2026-10-26 \u4fee\u8ba2\u7248'
    data['import'] = dict(method='Audiveris 5.11.0 + music21 + original vector PDF', status='machine-transcribed-needs-proofreading', revision='2026-10-26', musicxml=mxl.relative_to(ROOT).as_posix(), sourceSha256=hashlib.sha256((REV/'chi-le-ge.pdf').read_bytes()).hexdigest(), rhythmWarnings=[])
    data['reading'] = dict(version=2, method='original-pdf-graphics', description='Original PDF graphics; no semantic re-engraving.')
    piano = next(p for p in score.parts if p.partName == 'Piano')
    bars = list(piano.getElementsByClass(m21.stream.Measure))
    with fitz.open(REV/'chi-le-ge.pdf') as pdf, zipfile.ZipFile(REV/'omr/chi-le-ge-corrected.omr') as book:
        for pi, page in enumerate(pdf):
            scale = 1600/page.rect.width
            pix = page.get_pixmap(matrix=fitz.Matrix(scale,scale), alpha=False)
            im = Image.frombytes('RGB', (pix.width,pix.height), pix.samples)
            image = f'page-{pi+1:02}.webp'; im.save(TARGET/image, 'WEBP', quality=88)
            svg = f'original-{pi+1:02}.svg'; xml = page.get_svg_image(matrix=fitz.Matrix(scale,scale), text_as_path=True)
            (TARGET/svg).write_text(xml, 'utf8'); vb = [float(x) for x in ET.fromstring(xml).get('viewBox').split()]
            data['pages'].append(dict(image=image,width=pix.width,height=pix.height,svg=svg,svgWidth=vb[2],svgHeight=vb[3],sourceType='vector'))
            sheet = ET.fromstring(book.read(f'sheet#{pi+1}/sheet#{pi+1}.xml'))
            oscale = 1600/int(sheet.find('picture').get('width'))
            for system in sheet.findall('./page/system'):
                points = system.findall('./part/staff/lines/line/point')
                xs = [float(p.get('x'))*oscale for p in points]; ys = [float(p.get('y'))*oscale for p in points]
                left=max(0,int(min(xs)-45)); right=min(pix.width,int(max(xs)+18))
                top=max(0,int(min(ys)-105)); bottom=min(pix.height,int(max(ys)+90))
                si=len(data['systems']); image=f'system-{si+1:02}.webp'
                im.crop((left,top,right,bottom)).save(TARGET/image,'WEBP',quality=90)
                gaps=[]; headers=[]
                for st in system.findall('./part/staff'):
                    lines=[statistics.mean(float(p.get('y'))*oscale for p in l.findall('point')) for l in st.findall('./lines/line')]
                    gaps.extend(b-a for a,b in zip(lines,lines[1:]))
                    if st.find('header') is not None: headers.append(float(st.find('header').get('stop'))*oscale)
                data['systems'].append(dict(image=image,page=pi,x=left,y=top,width=right-left,height=bottom-top,interline=statistics.median(gaps),headerRight=max(headers),staffTop=min(ys)))
                for stack in system.findall('stack'):
                    if stack.get('duration')=='0': continue
                    idx=len(data['measures']); bar=bars[idx]
                    # Printed 6/4 in bars 55 and 67, 4/4 everywhere else.
                    # Audiveris misses the opening 4/4 and misreads the final 6/4.
                    q=6.0 if idx in [54,66] else 4.0
                    sl=float(stack.get('left'))*oscale; sr=float(stack.get('right'))*oscale
                    positions=[]
                    for slot in stack.findall('slot'):
                        offset=float(Fraction(slot.get('time-offset','0'))*4)
                        x=sl+float(slot.get('x-offset'))*oscale
                        if 0<=offset<q and sl<=x<sr: positions.append(dict(time=round(offset*60/data['tempo'],8),x=x))
                    positions=sorted({p['time']:p for p in positions}.values(),key=lambda p:p['time'])
                    if not positions: positions=[dict(time=0,x=sl+(sr-sl)*.15)]
                    for a,b in zip(positions,positions[1:]): b['x']=max(a['x'],b['x'])
                    data['measures'].append(dict(index=idx,label=idx+1,quarterLength=q,page=pi,system=si,left=sl,right=sr,positions=positions))
            print('Rendered page',pi+1,flush=True)
    assert len(bars)==len(data['measures']), (len(bars),len(data['measures']))
    (TARGET/'song.json').write_text(json.dumps(data,ensure_ascii=False,separators=(',',':')),'utf8')
    for destination in [ROOT/'data/chi-le-ge.pdf', TARGET/'score.pdf']:
        destination.chmod(0o666)
        shutil.copyfile(REV/'chi-le-ge.pdf',destination)
    shutil.copyfile(mxl,TARGET/'score.mxl')
    from build_performance import export
    export('chi-le-ge',mxl)
    catalog=ROOT/'choir-studio/public/songs/catalog.json'
    items=json.loads(catalog.read_text('utf8'))
    for item in items:
        if item['id']=='chi-le-ge': item.update(pages=10,subtitle=data['subtitle'])
    catalog.write_text(json.dumps(items,ensure_ascii=False),'utf8')
    print('Imported',len(data['measures']),'bars',flush=True)

if __name__=='__main__':
    if '--generate-only' not in sys.argv: correct_parts()
    generate()
