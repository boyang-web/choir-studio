"""Build Hui Sheng from a source-compared, eight-voice transcription ledger.

The ledger retains PDF coordinates as evidence; timing is accumulated from
written durations, never derived from horizontal distances. Run from any cwd.
"""
from pathlib import Path
import hashlib
import json
import shutil

import fitz
import music21 as m21
from PIL import Image

from import_new_scores import PPQ, write_midi

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'data/sources/3.回声.pdf'
LEDGER = ROOT / 'data/verified/hui-sheng.json'
TARGET = ROOT / 'choir-studio/public/songs/hui-sheng'


def build():
    ledger = json.loads(LEDGER.read_text(encoding='utf8'))
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == ledger['sourceSha256']
    TARGET.mkdir(parents=True, exist_ok=True)
    tempo = ledger['tempo']
    seconds = lambda quarter: quarter * 60 / tempo
    song = dict(id=ledger['id'], title=ledger['title'], tempo=tempo,
                tag='双合唱队 · 八声部',
                subtitle='奥兰多·德·拉絮斯 · 双混声四部无伴奏合唱 · 练习速度 120 BPM',
                pages=[], systems=[], measures=[], parts=[], beats=[],
                duration=seconds(38 * 4), performanceVersion=3,
                midi=dict(file='performance.mid', ppq=PPQ, source='Source-compared MusicXML'),
                import_=None)
    song.pop('import_')
    song['import'] = dict(method=ledger['method'], status='source-compared',
                         source='data/sources/3.回声.pdf', sourceSha256=ledger['sourceSha256'],
                         tempoEstimated=True, tempoSource=ledger['tempoSource'],
                         rhythmWarnings=[], limitations=[
                             '120 BPM is a user-approved rehearsal tempo, not a printed metronome mark.',
                             'Source comparison and automated validation do not replace musician listening acceptance.',
                             'Explicit dynamics are retained; hairpins are a rehearsal approximation.'])
    score = m21.stream.Score(id='hui-sheng')
    score.metadata = m21.metadata.Metadata()
    score.metadata.title = '回声'
    score.metadata.composer = 'Orlando di Lasso'
    audit_parts = {}
    for source in ledger['parts']:
        part = dict(id=source['id'], name=source['name'], english=source['id'],
                    letter=source['letter'], role=source['role'], choir=source['choir'],
                    sound='female' if source['role'] in ('soprano', 'alto') else 'male',
                    notes=[], expression=[])
        xmlpart = m21.stream.Part(id=source['id'])
        xmlpart.partName = source['name']
        previous = None
        for bar in source['measures']:
            assert bar['number'] in range(1, 39)
            measure = m21.stream.Measure(number=bar['number'])
            if bar['number'] == 1:
                measure.insert(0, m21.clef.TrebleClef() if part['sound'] == 'female' else m21.clef.BassClef())
                measure.insert(0, m21.key.KeySignature(3))
                measure.insert(0, m21.meter.TimeSignature('4/4'))
                measure.insert(0, m21.tempo.MetronomeMark(number=tempo))
            extent = 0
            for event in bar['events']:
                assert event['offset'] == extent, (part['id'], bar['number'], event)
                extent += event['duration']
                note = m21.note.Rest() if event.get('rest') else m21.note.Note(event['pitch'])
                if not event.get('rest'):
                    assert note.pitch.midi == event['midi']
                note.quarterLength = event['duration']
                if event.get('tieStart') or event.get('tieStop'):
                    note.tie = m21.tie.Tie('continue' if event.get('tieStart') and event.get('tieStop')
                                          else 'start' if event.get('tieStart') else 'stop')
                measure.insert(event['offset'], note)
                if event.get('rest'):
                    continue
                quarter = (bar['number'] - 1) * 4 + event['offset']
                duration_ticks = round(event['duration'] * PPQ)
                ticks = round(quarter * PPQ)
                if event.get('tieStop'):
                    assert previous and previous['midi'] == event['midi']
                    assert previous['ticks'] + previous['durationTicks'] == ticks
                    previous['durationTicks'] += duration_ticks
                    previous['duration'] += seconds(event['duration'])
                else:
                    previous = dict(midi=event['midi'], ticks=ticks, durationTicks=duration_ticks,
                                    time=seconds(quarter), duration=seconds(event['duration']),
                                    velocity=90/127, branch='shared', measure=bar['number'])
                    part['notes'].append(previous)
            assert extent == 4, (part['id'], bar['number'], extent)
            xmlpart.append(measure)
        for point in source['expression']:
            part['expression'].append(dict(ticks=round(point['quarter']*PPQ),
                                           time=seconds(point['quarter']), value=point['value']))
        audit_parts[part['id']] = dict(measures=38, notes=len(part['notes']),
                                      rests=sum(bool(e.get('rest')) for m in source['measures'] for e in m['events']))
        song['parts'].append(part)
        score.insert(0, xmlpart)
    score.write('musicxml', fp=str(TARGET / 'score.musicxml'))
    score.write('mxl', fp=str(TARGET / 'score.mxl'))
    with fitz.open(SOURCE) as pdf:
        for index, page in enumerate(pdf):
            scale = 1600 / page.rect.width
            pix = page.get_pixmap(matrix=fitz.Matrix(scale, scale), alpha=False)
            image, svg = f'page-{index+1:02}.webp', f'original-{index+1:02}.svg'
            Image.frombytes('RGB', (pix.width, pix.height), pix.samples).save(TARGET/image, 'WEBP', quality=92)
            (TARGET/svg).write_text(page.get_svg_image(matrix=fitz.Matrix(scale, scale), text_as_path=True), encoding='utf8')
            song['pages'].append(dict(image=image, svg=svg, width=pix.width, height=pix.height))
            for local_system in range(3):
                bars = sorted((m for m in ledger['layout'] if m['page'] == index and m['system'] == local_system), key=lambda m:m['number'])
                # Locate the four printed staves from their clef baselines.
                clefs = sorted(c[2][1] - (12.756 if c[0] == 0xe050 else 4.252)
                               for span in page.get_texttrace() if span['font'] == 'Leland'
                               for c in span['chars'] if c[0] in (0xe050, 0xe062))
                top = max(0, clefs[local_system*4] - 18)
                bottom = clefs[local_system*4+3] + 32
                system_index = len(song['systems'])
                song['systems'].append(dict(page=index, x=bars[0]['left']*scale, y=top*scale,
                                            width=(bars[-1]['right']-bars[0]['left'])*scale,
                                            height=(bottom-top)*scale))
                for bar in bars:
                    number = bar['number']
                    anchors = {}
                    for part in ledger['parts']:
                        for event in part['measures'][number-1]['events']:
                            anchors.setdefault(event['offset'], []).append(event['x'])
                    positions = []
                    for offset, xs in sorted(anchors.items()):
                        x = min(xs)*scale
                        if not positions or x > positions[-1]['x']:
                            positions.append(dict(ticks=round(offset*PPQ), time=seconds(offset), x=x))
                    start = (number-1)*4
                    song['measures'].append(dict(index=number-1, label=number, ticks=start*PPQ,
                        durationTicks=4*PPQ, time=seconds(start), duration=seconds(4), quarterLength=4,
                        page=index, system=system_index, left=bar['left']*scale, right=bar['right']*scale,
                        positions=positions))
    song['beats'] = [dict(ticks=q*PPQ, time=seconds(q), accent=q%4 == 0) for q in range(152)]
    write_midi(TARGET/'performance.mid', song['parts'], [(0, round(60000000/tempo))])
    shutil.copyfile(SOURCE, TARGET/'score.pdf')
    (TARGET/'song.json').write_text(json.dumps(song, ensure_ascii=False, separators=(',', ':'))+'\n', encoding='utf8')
    catalog_file = TARGET.parent/'catalog.json'
    catalog = [s for s in json.loads(catalog_file.read_text(encoding='utf8')) if s['id'] != song['id']]
    catalog.append({k:song[k] for k in ('id', 'title', 'tag', 'tempo', 'subtitle')} | dict(pages=3))
    catalog_file.write_text(json.dumps(catalog, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    audit = dict(id=song['id'], sourceSha256=ledger['sourceSha256'], pages=3, measures=38,
                 parts=audit_parts, duration=song['duration'], rhythmWarnings=[],
                 verification='All 304 voice-measures conserve 4 beats; ties and independent rhythms explicitly source-compared.',
                 limitations=song['import']['limitations'])
    (ROOT/'inspection/hui-sheng-audit.json').write_text(json.dumps(audit, ensure_ascii=False, indent=2)+'\n', encoding='utf8')
    print(json.dumps(audit, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    build()
