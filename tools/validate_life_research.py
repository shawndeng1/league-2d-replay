"""Reproduce fixture-only checks; candidate fields do not enter production JSON.

Requires the ignored dumps made by discover_deaths.py and probe_packet.py.
"""
import argparse
import json
import struct
import statistics
from collections import Counter
from pathlib import Path

def last(writes,offset):return [v&0xffffffff for a,s,v in writes if a==offset and s==4][-1]
def as_float(value):return struct.unpack('<f',struct.pack('<I',value))[0]

def main():
    ap=argparse.ArgumentParser();ap.add_argument('normalized_replay');args=ap.parse_args()
    replay=json.loads(Path(args.normalized_replay).read_text())
    root=Path('samples/local')
    deaths=json.loads((root/'death-evidence.json').read_text())
    notices=json.loads((root/'packet-00e7.json').read_text())
    respawns=json.loads((root/'packet-01b3.json').read_text())
    names=[p['championName'] for p in replay['players']]
    counts=Counter();timers=[]
    for death in deaths:
        # Research-only correlation. Companion block parameters sometimes have
        # an additional 0x100; its semantics remain unknown. The production
        # respawn decoder uses only exact, unflagged 0x01B3 participant IDs.
        matches=[n for n in notices if abs(n['timestamp']-death['timestamp'])<1e-6
                 and (n['param']&~0x100)==death['victim']
                 and last(n['outputWrites'],0x1c)==death['killer']]
        assert len(matches)==1
        delay=as_float(last(matches[0]['outputWrites'],0x54))
        timers.append((death['victim'],death['timestamp']+delay))
        heap=bytes.fromhex(death['heap']);out=bytes.fromhex(death['output']);base=0x10200000
        pointer,count=struct.unpack_from('<QI',out,0x48);contributors=set()
        for i in range(count):
            offset=pointer-base+i*0x30;entity=last(death['heapWrites'],offset+0x18)
            ptr,length=struct.unpack_from('<QI',heap,offset+0x20)
            name=heap[ptr-base:ptr-base+length].decode();player=entity-0x400000ae
            if 0<=player<10 and names[player]==name and entity!=death['killer']:contributors.add(player)
        counts.update(contributors)
    differences=[]
    for respawn in respawns:
        matches=[t for entity,t in timers if entity==respawn['param'] and abs(t-respawn['timestamp'])<.1]
        assert len(matches)==1
        differences.append(respawn['timestamp']-matches[0])
    result={'fixtureSha256':replay['metadata']['sourceSha256'],'deaths':len(deaths),'respawns':len(respawns),
            'timerMatches':len(differences),'timersBeyondMatchEnd':sum(t>replay['metadata']['duration'] for _,t in timers),
            'timerToPacketSeconds':{'min':min(differences),'median':statistics.median(differences),'max':max(differences)},
            'assists':{'champions':names,'candidateCounts':[counts[i] for i in range(10)],'metadataCounts':[p['finalStats']['assists'] for p in replay['players']], 'status':'REJECTED: context is not an assist list'}}
    Path('samples/lifecycle-evidence.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
