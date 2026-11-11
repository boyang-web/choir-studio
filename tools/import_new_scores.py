"""Import the five new PDFs after transcription, retaining recognition warnings.

Uses printed staff order verified on the source PDFs. Playback follows MusicXML
durations on a common bar grid; no song-specific corrections from older songs
are applied. Run with --id to retry a single song.
"""
from pathlib import Path
from fractions import Fraction as F
from collections import defaultdict
import argparse, bisect, json, math, os, shutil, struct, subprocess, sys, zipfile
import xml.etree.ElementTree as E

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'tools/python-libs'))
import fitz

PPQ = 10080
ROLES = [('soprano','女高音','Soprano','S'), ('alto','女中音','Alto','A'),
         ('tenor','男高音','Tenor','T'), ('bass','男低音','Bass','B'),
         ('piano','钢琴','Piano','P')]

def fraction(value, default='0'):
    return F(value or default)

def normalize(item, folder):
    """Correct physical-to-logical staff assignment before MusicXML export."""
    source = folder/(item['id']+'.omr')
    target = folder/(item['id']+'-corrected.omr')
    with zipfile.ZipFile(source) as book:
        tree = E.fromstring(book.read('book.xml'))
        sheets = {}
        arrangements = set()
        for sh in tree.findall('sheet'):
            number = sh.get('number')
            name = f'sheet#{number}/sheet#{number}.xml'
            sheet = E.fromstring(book.read(name))
            systems = sheet.findall('./page/system')
            refs = sh.findall('./page/system')
            if len(systems) != len(refs):
                raise ValueError('OMR system references do not match')
            for system, ref in zip(systems, refs):
                parts = system.findall('part')
                sizes = tuple(len(p.findall('staff')) for p in parts)
                if sizes not in ((1,1,1,1), (1,1,1,1,2), (1,1,1,1,1,1)):
                    raise ValueError(f'Unverified staff layout on sheet {number}: {sizes}')
                arrangements.add(sizes)
                if len(ref.findall('part')) != len(parts):
                    raise ValueError('OMR part references do not match')
                for index, (part, pr) in enumerate(zip(parts, ref.findall('part')), 1):
                    part.set('id', str(index))
                    pr.set('logical-id', str(index))
                    pr.set('manual', 'true')
            wedges = {e.get('id') for e in sheet.iter('wedge')}
            for parent in sheet.iter():
                for child in list(parent):
                    if child.tag == 'wedge' or (child.tag == 'relation' and
                       (child.get('source') in wedges or child.get('target') in wedges)):
                        parent.remove(child)
            sheets[name] = E.tostring(sheet, encoding='utf-8', xml_declaration=True)
        if len(arrangements) != 1:
            raise ValueError(f'Changing staff layout needs manual review: {arrangements}')
        sizes = next(iter(arrangements))
        for score in tree.findall('score'):
            for part in score.findall('logical-part'):
                score.remove(part)
            for index, size in enumerate(sizes):
                name = ROLES[index][2] if index < 4 else 'Piano' if len(sizes)==5 else ['Piano RH','Piano LH'][index-4]
                logical = E.Element('logical-part', {'id':str(index+1), 'staff-count':str(size),
                    'name':name, 'abbreviation':name, 'midi-program':'1' if index>=4 else '54'})
                for _ in range(size):
                    E.SubElement(logical, 'staff-configuration', {'line-count':'5'})
                score.insert(index, logical)
        sheets['book.xml'] = E.tostring(tree, encoding='utf-8', xml_declaration=True)
        with zipfile.ZipFile(target, 'w', zipfile.ZIP_DEFLATED) as out:
            for name in book.namelist():
                out.writestr(name, sheets.get(name, book.read(name)))
    java = ROOT/'tools/audiveris/Audiveris/runtime/bin/java.exe'
    with (folder/'export.log').open('w', encoding='utf-8') as log:
        subprocess.run([str(java), '-Xmx3g', '-Djava.awt.headless=true', '-cp',
            str(ROOT/'tools/audiveris/Audiveris/app/*'), 'Audiveris', '-batch', '-export',
            '-output', str(folder), '--', str(target)],
            env=dict(os.environ, APPDATA=str(ROOT/'tools/state')), stdout=log, stderr=subprocess.STDOUT, check=True)
    mxl = folder/(item['id']+'-corrected.mxl')
    if not mxl.exists():
        raise ValueError('MusicXML export missing; inspect export.log')
    return mxl

def read_xml(path):
    with zipfile.ZipFile(path) as archive:
        container = E.fromstring(archive.read('META-INF/container.xml'))
        node = container.find('.//{*}rootfile')
        return E.fromstring(archive.read(node.get('full-path')))

def variable(number):
    values = [number & 127]
    while number >> 7:
        number >>= 7
        values.insert(0, (number & 127) | 128)
    return bytes(values)

def track(events):
    data = bytearray(); previous = 0
    for tick, priority, message in sorted(events, key=lambda event: (event[0], event[1])):
        if tick < previous:
            raise ValueError('MIDI event order invalid')
        data.extend(variable(tick-previous)); data.extend(message); previous=tick
    data.extend(b'\x00\xff\x2f\x00')
    return b'MTrk'+struct.pack('>I',len(data))+data

def write_midi(path, parts, tempos):
    """Write standard format-1 MIDI with explicit note gates and named tracks."""
    chunks = [track([(tick, 0, b'\xff\x51\x03'+int(micros).to_bytes(3,'big')) for tick,micros in tempos])]
    for channel, part in enumerate(parts):
        label = (part['id']+':shared').encode('ascii')
        events = [(0,0,b'\xff\x03'+variable(len(label))+label),
                  (0,1,bytes([0xC0|channel,0 if part['id']=='piano' else 52]))]
        for note in part['notes']:
            events.extend([(note['ticks'],3,bytes([0x90|channel,note['midi'],90])),
                (note['ticks']+note['durationTicks'],2,bytes([0x80|channel,note['midi'],0]))])
        chunks.append(track(events))
    path.write_bytes(b'MThd'+struct.pack('>IHHH',6,1,len(chunks),PPQ)+b''.join(chunks))

def export(item, folder, mxl):
    xml = read_xml(mxl)
    source_parts = xml.findall('part')
    if not source_parts:
        raise ValueError('No MusicXML parts')
    counts = [len(part.findall('measure')) for part in source_parts]
    if len(set(counts)) != 1:
        raise ValueError(f'Part measure counts differ: {counts}')
    target = ROOT/'choir-studio/public/songs'/item['id']
    target.mkdir(parents=True, exist_ok=True)
    song = dict(id=item['id'],title=item['title'],tag='试导入 · 待校订',tempo=item['tempo'],
        subtitle='PDF 识谱试导入 · 尚未人工逐音校订',pages=[],systems=[],measures=[],beats=[],parts=[])
    warnings = []; starts = []; lengths = []; meter=F(4); divisions=1; quarter=F(0)
    for index, measure in enumerate(source_parts[0].findall('measure')):
        attrs=measure.find('attributes')
        if attrs is not None:
            divisions=int(attrs.findtext('divisions',str(divisions)))
            time=attrs.find('time')
            if time is not None:
                beats=time.findtext('beats','4'); beat_type=time.findtext('beat-type','4')
                meter=sum(F(x) for x in beats.split('+'))*4/F(beat_type)
        cursor=F(0); extent=F(0)
        for child in measure:
            if child.tag in ('note','forward','backup'):
                length=fraction(child.findtext('duration'))/divisions
                if child.tag=='backup':cursor-=length
                elif child.tag=='forward' or (child.find('chord') is None and child.find('grace') is None):cursor+=length
                extent=max(extent,cursor)
        length=extent if measure.get('implicit')=='yes' and 0<extent<meter else meter
        starts.append(quarter);lengths.append(length);quarter+=length
    tempo_marks={0:round(60000000/item['tempo'])}
    events=defaultdict(list)
    steps={'C':0,'D':2,'E':4,'F':5,'G':7,'A':9,'B':11}
    for part_index, source in enumerate(source_parts):
        role=ROLES[min(part_index,4)]
        divisions=1;transposition=0
        for index, measure in enumerate(source.findall('measure')):
            if not measure.findall('note'):
                warnings.append(dict(part=role[0],measure=index+1,reason='MusicXML measure has no notes or rests; possible omitted notation'))
            attrs=measure.find('attributes')
            if attrs is not None:
                divisions=int(attrs.findtext('divisions',str(divisions)))
                transpose=attrs.find('transpose')
                if transpose is not None:
                    transposition=int(transpose.findtext('chromatic','0'))+12*int(transpose.findtext('octave-change','0'))
            cursor=F(0);previous=F(0)
            for child in measure:
                if child.tag=='backup':cursor-=fraction(child.findtext('duration'))/divisions;continue
                if child.tag=='forward':cursor+=fraction(child.findtext('duration'))/divisions;continue
                if child.tag=='direction':
                    sound=child.find('.//sound')
                    if sound is not None and sound.get('tempo'):
                        tempo=float(sound.get('tempo'))
                        if tempo>0:tempo_marks[round((starts[index]+cursor)*PPQ)]=round(60000000/tempo)
                    continue
                if child.tag!='note':continue
                length=fraction(child.findtext('duration'))/divisions
                offset=previous if child.find('chord') is not None else cursor
                if child.find('chord') is None:
                    previous=cursor;cursor+=length
                pitch=child.find('pitch')
                if pitch is None:continue
                if child.find('grace') is not None:
                    warnings.append(dict(part=role[0],measure=index+1,reason='grace note requires manual timing'))
                    continue
                if length<=0:continue
                if offset<0 or offset>=lengths[index] or offset+length>lengths[index]+F(1,1000):
                    warnings.append(dict(part=role[0],measure=index+1,offset=str(offset),duration=str(length),
                        expected=str(lengths[index]),reason='recognized duration crosses bar boundary'))
                if offset<0:continue
                midi=12*(int(pitch.findtext('octave'))+1)+steps[pitch.findtext('step')]+int(pitch.findtext('alter','0'))+transposition
                if not 0<=midi<=127:raise ValueError('Pitch outside MIDI range')
                ties={t.get('type') for t in child.findall('tie')}
                events[role[0]].append(dict(ticks=round((starts[index]+offset)*PPQ),durationTicks=max(1,round(length*PPQ)),
                    midi=midi,branch='shared',velocity=90/127,measure=index+1,_ties=ties,
                    _voice=f"{part_index}:{child.findtext('voice','1')}:{child.findtext('staff','1')}"))
    tempos=sorted(tempo_marks.items());tempo_ticks=[t for t,_ in tempos];seconds=[0.]
    for (ta,ma),(tb,mb) in zip(tempos,tempos[1:]):seconds.append(seconds[-1]+(tb-ta)*ma/1000000/PPQ)
    def sec(tick):
        i=max(0,bisect.bisect_right(tempo_ticks,tick)-1)
        return seconds[i]+(tick-tempos[i][0])*tempos[i][1]/1000000/PPQ
    total_ticks=round(quarter*PPQ)
    for role in ROLES:
        if role[0] not in events:continue
        if role[0]=='bass' and item.get('baritone'):
            role=('bass','男中音','Baritone','B')
        merged=[];pending={};identities=set()
        for note in sorted(events[role[0]],key=lambda n:(n['ticks'],n['midi'])):
            key=(note['_voice'],note['midi']);ties=note.pop('_ties');note.pop('_voice')
            previous=pending.get(key)
            if 'stop' in ties and previous and abs(previous['ticks']+previous['durationTicks']-note['ticks'])<=1:
                previous['durationTicks']+=note['durationTicks']
                if 'start' not in ties:pending.pop(key,None)
                continue
            identity=(note['ticks'],note['midi'],note['durationTicks'])
            if identity in identities:continue
            identities.add(identity);merged.append(note)
            if 'start' in ties:pending[key]=note
            else:pending.pop(key,None)
        for note in merged:
            note['time']=sec(note['ticks']);note['duration']=sec(note['ticks']+note['durationTicks'])-note['time']
            if note['ticks']+note['durationTicks']>total_ticks:
                warnings.append(dict(part=role[0],measure=note['measure'],reason='note extends beyond score end'))
        song['parts'].append(dict(zip(('id','name','english','letter'),role),notes=merged,expression=[]))
    if len(song['parts'])<4:
        raise ValueError('One or more vocal parts have no recognized notes')
    with fitz.open(ROOT/'data/sources'/item['source']) as pdf:
        for index,page in enumerate(pdf):
            scale=1600/page.rect.width
            image=f'page-{index+1:02}.webp'
            pix=page.get_pixmap(matrix=fitz.Matrix(scale,scale),alpha=False)
            from PIL import Image
            Image.frombytes('RGB',(pix.width,pix.height),pix.samples).save(target/image,'WEBP',quality=88)
            svg=f'original-{index+1:02}.svg'
            (target/svg).write_text(page.get_svg_image(matrix=fitz.Matrix(scale,scale),text_as_path=True),encoding='utf-8')
            song['pages'].append(dict(image=image,svg=svg,width=pix.width,height=pix.height))
    with zipfile.ZipFile(folder/(item['id']+'.omr')) as book:
        page_names=sorted((n for n in book.namelist() if n.startswith('sheet#') and n.endswith('.xml')),key=lambda n:int(n.split('/')[0].split('#')[1]))
        stacks=[stack for name in page_names for stack in E.fromstring(book.read(name)).findall('./page/system/stack')]
        if len(stacks)==len(starts):
            keep_zero=True
        elif sum(stack.get('duration')!='0' for stack in stacks)==len(starts):
            keep_zero=False
        else:
            raise ValueError(f'OMR/XML bar count mismatch before alignment: {len(stacks)}/{len(starts)}')
        for name in page_names:
            sheet=E.fromstring(book.read(name));number=int(name.split('/')[0].split('#')[1]);page_index=number-1+item.get('skipPages',0)
            scale=1600/int(sheet.find('picture').get('width'))
            for system in sheet.findall('./page/system'):
                points=system.findall('./part/staff/lines/line/point')
                if not points:continue
                xs=[float(p.get('x'))*scale for p in points];ys=[float(p.get('y'))*scale for p in points]
                system_index=len(song['systems'])
                song['systems'].append(dict(page=page_index,x=max(0,min(xs)-30),y=max(0,min(ys)-50),
                    width=max(xs)-min(xs)+50,height=max(ys)-min(ys)+100))
                for stack in system.findall('stack'):
                    if stack.get('duration')=='0' and not keep_zero:continue
                    index=len(song['measures'])
                    if stack.get('duration')=='0':
                        warnings.append(dict(measure=index+1,reason='OMR recognized no duration in a printed bar; manual review required'))
                    if index>=len(starts):raise ValueError('More OMR bars than MusicXML bars')
                    left=float(stack.get('left'))*scale;right=float(stack.get('right'))*scale
                    tick=round(starts[index]*PPQ);duration_ticks=round(lengths[index]*PPQ)
                    positions=[]
                    for slot in stack.findall('slot'):
                        offset=fraction(slot.get('time-offset'))*4
                        if 0<=offset<lengths[index]:
                            pt=round(offset*PPQ);x=left+float(slot.get('x-offset'))*scale
                            if not positions or (pt>positions[-1]['ticks'] and x>positions[-1]['x']):
                                positions.append(dict(ticks=pt,time=sec(tick+pt)-sec(tick),x=x))
                    if not positions:positions=[dict(ticks=0,time=0,x=left+(right-left)*.15)]
                    song['measures'].append(dict(index=index,label=index+1,ticks=tick,durationTicks=duration_ticks,
                        time=sec(tick),duration=sec(tick+duration_ticks)-sec(tick),quarterLength=float(lengths[index]),
                        page=page_index,system=system_index,left=left,right=right,positions=positions))
                    if stack.get('excess') or stack.get('abnormal')=='true':
                        warnings.append(dict(measure=index+1,reason='OMR marked abnormal rhythm',excess=stack.get('excess')))
    if len(song['measures'])!=len(starts):raise ValueError(f"OMR/XML bar count mismatch: {len(song['measures'])}/{len(starts)}")
    song['beats']=[dict(ticks=round((start+beat)*PPQ),time=sec(round((start+beat)*PPQ)),accent=beat==0)
        for start,length in zip(starts,lengths) for beat in range(math.ceil(length))]
    song['duration']=sec(total_ticks);song['performanceVersion']=3
    song['midi']=dict(file='performance.mid',ppq=PPQ,source='MusicXML',timing='MusicXML durations on a common measure grid')
    song['import']=dict(method='Audiveris + MusicXML',status='machine-transcribed-needs-proofreading',
        source='data/sources/'+item['source'],rhythmWarnings=warnings,tempoEstimated=item.get('tempoEstimated',False),
        limitations=['Repeats are played in printed order; repeat jumps are not expanded.',
                    'Unresolved recognition errors are retained in the audit; source PDF is unchanged.'])
    write_midi(target/'performance.mid',song['parts'],tempos)
    shutil.copy2(ROOT/'data/sources'/item['source'],target/'score.pdf');shutil.copy2(mxl,target/'score.mxl')
    (target/'song.json').write_text(json.dumps(song,ensure_ascii=False,separators=(',',':')),encoding='utf-8')
    audit=dict(id=item['id'],title=item['title'],status='trial-imported',pages=len(song['pages']),measures=len(starts),
        duration=song['duration'],tracks={p['id']:len(p['notes']) for p in song['parts']},
        warnings=warnings,tempoEstimated=item.get('tempoEstimated',False),limitations=song['import']['limitations'])
    (ROOT/'inspection/new-imports'/(item['id']+'-audit.json')).write_text(json.dumps(audit,ensure_ascii=False,indent=2),encoding='utf-8')
    catalog_path=ROOT/'choir-studio/public/songs/catalog.json'
    catalog=json.loads(catalog_path.read_text(encoding='utf-8'))
    catalog=[entry for entry in catalog if entry['id']!=item['id']]
    catalog.append({key:song[key] for key in ('id','title','tag','tempo','subtitle') } | {'pages':len(song['pages'])})
    catalog_path.write_text(json.dumps(catalog,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({k:v for k,v in audit.items() if k!='warnings'},ensure_ascii=True),flush=True)
    print('recognition warnings:',len(warnings),flush=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--id');parser.add_argument('--reuse-export',action='store_true');args=parser.parse_args()
    failures=[]
    for item in json.loads((ROOT/'tools/new-scores.json').read_text(encoding='utf-8')):
        if args.id and item['id']!=args.id:continue
        folder=ROOT/'data/omr/new'/item['id']
        try:
            mxl=folder/(item['id']+'-corrected.mxl') if args.reuse_export else normalize(item,folder)
            export(item,folder,mxl)
        except Exception as error:
            failures.append((item['id'],str(error)));print(item['id'],'FAILED',str(error),flush=True)
            audit=ROOT/'inspection/new-imports'/(item['id']+'-audit.json')
            audit.parent.mkdir(parents=True,exist_ok=True)
            audit.write_text(json.dumps(dict(id=item['id'],title=item['title'],status='failed',reason=str(error),
                source='data/sources/'+item['source']),ensure_ascii=False,indent=2),encoding='utf-8')
    if failures:raise SystemExit(1)

if __name__=='__main__':main()
