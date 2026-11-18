"""Independently compare every ledger note with embedded PDF symbols.

This is intentionally specific to the supplied three-page MuseScore PDF.
It is not a general OMR engine or a claim of musician listening acceptance.
"""
from pathlib import Path
import hashlib
import json
import fitz

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT/'data/sources/3.回声.pdf'


def audit():
    ledger = json.loads((ROOT/'data/verified/hui-sheng.json').read_text(encoding='utf8'))
    assert hashlib.sha256(SOURCE.read_bytes()).hexdigest() == ledger['sourceSha256']
    assert len(ledger['parts']) == 8
    matched = set()
    total = set()
    event_count = 0
    with fitz.open(SOURCE) as pdf:
        assert len(pdf) == 3
        for page_index, page in enumerate(pdf):
            glyphs = {(c[0], round(c[2][0], 2), round(c[2][1], 2))
                      for span in page.get_texttrace() if span['font'] == 'Leland'
                      for c in span['chars']}
            heads = [g for g in glyphs if g[0] in (0xe0a2, 0xe0a3, 0xe0a4)]
            total.update((page_index, *g) for g in heads)
            clefs = sorted(y-(12.756 if c == 0xe050 else 4.252)
                           for c, x, y in glyphs if c in (0xe050, 0xe062))
            assert len(clefs) == 12
            for bar in ledger['layout']:
                if bar['page'] != page_index:
                    continue
                for staff in range(4):
                    top = clefs[bar['system']*4+staff]
                    events = []
                    part_index = (staff//2)*4+(staff%2)*2
                    for part in ledger['parts'][part_index:part_index+2]:
                        events.extend(e for e in part['measures'][bar['number']-1]['events'] if not e.get('rest'))
                    accidentals = {}
                    for event in sorted(events, key=lambda e:(e['x'], e['y'])):
                        candidates = [g for g in heads if abs(g[1]-event['x']) < 2.1 and abs(g[2]-event['y']) < .02]
                        assert len(candidates) == 1, (bar['number'], staff, event, candidates)
                        glyph = candidates[0]
                        diatonic = (38 if staff%2 == 0 else 26) + round((top-glyph[2])/2.126)
                        assert abs((top-glyph[2])/2.126-round((top-glyph[2])/2.126)) < .02
                        step = 'CDEFGAB'[diatonic%7]
                        signs = [g for g in glyphs if g[0] in (0xe260, 0xe261, 0xe262)
                                 and 1 < glyph[1]-g[1] < 12 and abs(g[2]-glyph[2]) < .02]
                        if signs:
                            sign = max(signs, key=lambda g:g[1])
                            accidentals[diatonic] = {0xe260:-1, 0xe261:0, 0xe262:1}[sign[0]]
                        alter = accidentals.get(diatonic, int(step in 'FCG'))
                        midi = 12*(diatonic//7+1)+[0, 2, 4, 5, 7, 9, 11][diatonic%7]+alter
                        assert event['midi'] == midi, (bar['number'], staff, event, midi)
                        if glyph[0] in (0xe0a2, 0xe0a3):
                            assert event['duration'] == {0xe0a2:4, 0xe0a3:2}[glyph[0]]
                        matched.add((page_index, *glyph))
                        event_count += 1
    assert total == matched, ('unassigned printed heads', sorted(total-matched))
    print(json.dumps(dict(printedNoteheads=len(total), assignedVoiceNotes=event_count,
                          unassignedNoteheads=0, pitchMismatches=0, sourceSha256=ledger['sourceSha256']), indent=2))


if __name__ == '__main__':
    audit()
