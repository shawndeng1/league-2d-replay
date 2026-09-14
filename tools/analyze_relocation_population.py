"""Account for every candidate action, including failed corroboration.

A nearby target observation is evidence of location, not a decoded completion.
Absence within 12 seconds is unresolved, never proof of cancellation.
"""
import argparse
import bisect
import json
import math
from collections import Counter
from pathlib import Path


def analyze_population(scan,replay):
    tracks={t['playerId']:[s for s in t['samples'] if not s.get('positionOnly')] for t in replay['tracks']}
    times={p:[s['timestamp'] for s in samples] for p,samples in tracks.items()}
    players={p['id']:p for p in replay['players']};results=[]
    for row in scan['rows']:
        if row['actionFingerprint']!=0x008fa255:continue
        player=row['playerId'];t=row['timestamp'];origin=row['originCandidate'];target=row['targetCandidate']
        valid=row['sourceA']==row['sourceB']==int(row['entity'],16) and all(math.isfinite(v) for v in [t,row['clockCandidate'],*origin,*target]) and abs(t-row['clockCandidate'])<=.002
        samples=tracks[player];at=bisect.bisect_left(times[player],t)
        near=samples[max(0,at-1):at+2]
        nearest=min(near,key=lambda s:abs(s['timestamp']-t)) if near else None
        window=samples[bisect.bisect_right(times[player],t+.15):bisect.bisect_right(times[player],t+12)]
        error=lambda s:math.hypot(s['x']-target[0],s['y']-target[2])
        matches=[s for s in window if error(s)<=64] if valid else []
        first=matches[0] if matches else None
        ends=[p for p in row.get('nearbyPackets',[]) if p['opcode']=='0x03d6' and p['size']==5]
        results.append({'playerId':player,'champion':players[player]['championName'],'timestamp':t,
            'status':'TARGET_OBSERVED' if first else 'UNRESOLVED' if valid else 'INVALID_IDENTITY_OR_TIME',
            'originError':None if nearest is None else math.hypot(nearest['x']-origin[0],nearest['y']-origin[2]),
            'originTimeDistance':None if nearest is None else abs(nearest['timestamp']-t),
            'targetDisplacement':math.hypot(target[0]-origin[0],target[2]-origin[2]),
            'firstTargetTimestamp':None if first is None else first['timestamp'],
            'firstTargetError':None if first is None else error(first),
            'elapsedToObservation':None if first is None else first['timestamp']-t,
            'closestTargetError':min(map(error,window),default=None),
            'windowSamples':len(window),
            'candidateEndPackets':[{'elapsed':p['timestamp']-t,'payloadHex':p['payloadHex']} for p in ends],
            'endToObservation':None if not ends or first is None else min((first['timestamp']-p['timestamp'] for p in ends),key=abs),
            'nearbyLifeEvents':[{'type':e['type'],'timestamp':e['timestamp']} for e in replay['events'] if t<=e['timestamp']<=t+12 and ((e['type']=='CHAMPION_KILL' and e['victimPlayerId']==player) or (e['type']=='CHAMPION_RESPAWN' and e['playerId']==player))]})
    return {'replay':scan['replay'],'replayId':scan['replayId'],'decodedActionPackets':scan['decodedActionPackets'],
        'counts':dict(Counter(r['status'] for r in results)),'actions':results,
        'confidence':'RESEARCH_ONLY: target observations do not verify completion or cancellation semantics'}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('directory',type=Path);ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();reports=[]
    for path in sorted(args.directory.glob('NA1-*.json')):
        scan=json.loads(path.read_text());replay=json.loads(Path('samples/local/replays',scan['replayId']+'.json').read_text())
        reports.append(analyze_population(scan,replay))
    args.output.write_text(json.dumps(reports,indent=2)+'\n')
    for r in reports:print(r['replay'],r['counts'])


if __name__=='__main__':main()
