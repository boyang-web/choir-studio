"""Compatibility entry point: use symbolic durations and the music21 MIDI build."""
from fractions import Fraction
from collections import Counter
from build_performance import vp_events,export

def recover(data):
    events,_=vp_events(data,{})
    data['parts'][next(i for i,p in enumerate(data['parts']) if p['id']=='percussion')]['notes']=[dict(time=float(n['quarter']*60/data['tempo']),duration=float(n['length']*60/data['tempo']),midi=n['midi'],kind=n['kind'],syllable=n['syllable'],head=n['head'],measure=n['measure'],source=n['source']) for n in events]
    return Counter(n['head'] for n in events)

if __name__=='__main__':export('let-it-go')
