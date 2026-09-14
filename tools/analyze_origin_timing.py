"""Compare candidate origins with raw observations at arrival and embedded times.

No route simulation or invented reference points: a match is corroborated only
when an actual movement observation lies within 2ms. Sparse comparisons remain
unresolved. Action fingerprints are opaque grouping keys, not ability names.
"""
import argparse
import bisect
import json
import math
from collections import Counter, defaultdict
from pathlib import Path


def name_fingerprint(name):
    """Case-folded ELF-style hash hypothesis; collisions do not prove identity."""
    result=0
    for char in name.lower():
        result=(result<<4)+ord(char)
        high=result&0xf0000000
        if high:result^=high>>24
        result&=~high
    return result


# Small explicit hypothesis list, not an authoritative game spell catalog.
NAME_CANDIDATES={name_fingerprint(name):name for name in
                 ('SummonerFlash','VladimirQ','VladimirE','Tantrum','BandageToss','ThreshQ','ThreshQLeap')}


def compare_origin(row, samples):
    times = [s['timestamp'] for s in samples]
    if not times or any(not math.isfinite(t) for t in times) or times != sorted(times):
        raise ValueError('Require a nonempty sorted observation track')
    x, _, y = row['originCandidate']
    if not all(math.isfinite(v) for v in (x,y,row['timestamp'],row['clockCandidate'])):
        raise ValueError('Nonfinite candidate')
    def match(time):
        index = bisect.bisect_left(times,time)
        sample = min(samples[max(0,index-1):index+1],key=lambda s:abs(s['timestamp']-time))
        gap = abs(sample['timestamp']-time)
        error = math.hypot(x-sample['x'],y-sample['y'])
        return {'timestamp':sample['timestamp'],'x':sample['x'],'y':sample['y'],
                'gapSeconds':gap,'errorWorldUnits':error,'coincident':gap<=.002,
                'corroborated':gap<=.002 and error<=4}
    arrival, embedded = match(row['timestamp']), match(row['clockCandidate'])
    stale = row['timestamp']-row['clockCandidate']>.05
    return {**row,'arrivalMatch':arrival,'embeddedTimeMatch':embedded,
            'actionNameHypothesis':NAME_CANDIDATES.get(row.get('actionFingerprint')),
            'timingClass':'EARLIER_POSITION_CORROBORATED' if stale and embedded['corroborated'] else
            'ORIGIN_MISMATCH_AT_EMBEDDED_TIME' if embedded['coincident'] and not embedded['corroborated'] else
            'COINCIDENT_ORIGIN_CORROBORATED' if embedded['corroborated'] else 'INSUFFICIENT_OBSERVATIONS'}


def analyze(research,replay):
    tracks={t['playerId']:t['samples'] for t in replay['tracks']}
    rows=[compare_origin(row,tracks[row['playerId']]) for row in research['rows']]
    groups=defaultdict(list)
    for row in rows:
        key=(row.get('actionFingerprint'),row.get('actionSlotCandidate'))
        groups[key].append(row)
    summary={'packets':len(rows),'classes':dict(Counter(r['timingClass'] for r in rows)),
             'arrivalCorroborated':sum(r['arrivalMatch']['corroborated'] for r in rows),
             'embeddedCorroborated':sum(r['embeddedTimeMatch']['corroborated'] for r in rows),
             'status':'RESEARCH_ONLY; matching observations does not validate missing intervals'}
    grouped=[{'fingerprint':None if k[0] is None else hex(k[0]),'slotCandidate':k[1],
              'nameHypothesis':NAME_CANDIDATES.get(k[0]),
              'packets':len(v),'players':sorted({r['playerId'] for r in v}),
              'classes':dict(Counter(r['timingClass'] for r in v))} for k,v in groups.items()]
    grouped.sort(key=lambda g:(-g['packets'],str(g['fingerprint']),str(g['slotCandidate'])))
    return {'summary':summary,'groups':grouped,'rows':rows}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('research',type=Path)
    ap.add_argument('normalized',type=Path)
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    report=analyze(json.loads(args.research.read_text()),json.loads(args.normalized.read_text()))
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report['summary']))


if __name__=='__main__':main()
