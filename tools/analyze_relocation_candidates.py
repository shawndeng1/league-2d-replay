"""Correlate decoded action targets with later stopped-track relocations.

Research only: 64 units target proximity and 150 ms stop alignment select review
candidates, not verified gameplay semantics. Never writes normalized replay data.
"""
import argparse
import bisect
import json
import math
from pathlib import Path
from parser.patch_16_18 import PLAYER_ENTITY_START


def correlate_relocations(rows,tracks):
    indexed={t['playerId']:(t['samples'],[s['timestamp'] for s in t['samples']]) for t in tracks}
    matches=[]
    for row in rows:
        entity=int(row['entity'],16)
        if row['sourceA']!=entity or row['sourceB']!=entity:continue
        player=entity-PLAYER_ENTITY_START
        if player not in indexed:continue
        timestamp=row['timestamp']
        origin=row['originCandidate'];target=row['targetCandidate']
        numbers=[timestamp,row['clockCandidate'],*origin,*target]
        if not all(math.isfinite(n) for n in numbers) or abs(row['clockCandidate']-timestamp)>.002:continue
        samples,times=indexed[player];at=bisect.bisect_left(times,timestamp)
        for i in range(max(0,at-1),min(len(samples)-1,at+2)):
            a,b=samples[i:i+2]
            if abs(a['timestamp']-timestamp)>.15 or a.get('speed')!=0 or b['timestamp']-a['timestamp']<2:continue
            if math.hypot(b['x']-a['x'],b['y']-a['y'])<2000:continue
            origin_error=math.hypot(origin[0]-a['x'],origin[2]-a['y'])
            target_error=math.hypot(target[0]-b['x'],target[2]-b['y'])
            if origin_error>4 or target_error>64:continue
            matches.append({'playerId':player,'entity':row['entity'],'actionTimestamp':timestamp,
                'observationTimestamp':b['timestamp'],'elapsedSeconds':b['timestamp']-timestamp,
                'fingerprint':f"0x{row['actionFingerprint']:08x}",
                'originError':origin_error,'targetError':target_error,
                'origin':{'x':origin[0],'y':origin[2]},'target':{'x':target[0],'y':target[2]},
                'observedDestination':{'x':b['x'],'y':b['y']},
                'confidence':'LIKELY','meaning':'Target-correlated relocation candidate; completion time and gameplay identity UNKNOWN'})
            break
    return sorted(matches,key=lambda m:(m['actionTimestamp'],m['playerId']))


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('actions',type=Path);ap.add_argument('replay',type=Path);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args()
    rows=json.loads(args.actions.read_text());replay=json.loads(args.replay.read_text())
    report={'replayId':replay['metadata']['sourceSha256'],'candidates':correlate_relocations(rows,replay['tracks'])}
    args.output.write_text(json.dumps(report,indent=2)+'\n')
    print(f"{len(report['candidates'])} research candidates")


if __name__=='__main__':main()
