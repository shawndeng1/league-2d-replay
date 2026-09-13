"""Research-only falsification of a gold-recipient assist heuristic.

Input is a normalized replay plus a probe_packet 0x003B observation dump.
Never emits normalized events. A matching aggregate cannot verify per-kill credit.
"""
import argparse
import json
import struct
from collections import Counter
from pathlib import Path

def audit(replay, rows):
    counts=Counter()
    for death in replay['events']:
        if death['type']!='CHAMPION_KILL':continue
        recipients=set()
        for row in rows:
            if abs(row['timestamp']-death['timestamp'])>.000002:continue
            fields={a:v for a,s,v in row['outputWrites'] if s==4}
            # Client decoded object: +0x10 float award, +0x14 entity. The
            # gold interpretation is LIKELY. It has no victim or credit reason.
            player=fields[0x14]-0x400000ae
            amount=struct.unpack('<f',struct.pack('<I',fields[0x10]))[0]
            # Deliberately test (not endorse) the tempting >2 filter that drops
            # observed passive awards. It fails independent real fixtures.
            if amount>2 and 0<=player<len(replay['players']) and player!=death.get('killerPlayerId'):
                if replay['players'][player]['team']!=replay['players'][death['victimPlayerId']]['team']:
                    recipients.add(player)
        counts.update(recipients)
    actual=[p['finalStats']['assists'] for p in replay['players']]
    candidate=[counts[p['id']] for p in replay['players']]
    return {'sha256':replay['metadata']['sourceSha256'],
            'champions':[p['championName'] for p in replay['players']],
            'candidate':candidate,'metadata':actual,'totalsMatch':candidate==actual,
            'confidence':'UNKNOWN: gold recipient is not verified assist credit'}

def main():
    ap=argparse.ArgumentParser();ap.add_argument('replay',type=Path);ap.add_argument('observations',type=Path)
    args=ap.parse_args()
    print(json.dumps(audit(json.loads(args.replay.read_text()),json.loads(args.observations.read_text())),indent=2))

if __name__=='__main__':main()
