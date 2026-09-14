"""Research-only 0x02c4 field correlation. Never emits production positions.

Object offsets were observed in writes from the exact client's deserializer
0x10d0760, not guessed raw-payload indexes. Their semantics remain LIKELY until
the consumer and special-case behavior are established. Scalar writes are read
before subsequent per-byte obfuscation, as in existing event research.
"""
import argparse
import bisect
import hashlib
import json
import math
import struct
from pathlib import Path
from rofllens import ReplayReader
from rofllens.decoders.emulator import UnicornDecoderEngine
from parser.patch_16_18 import CLIENT_VERSION, PROTOCOL_DIGEST, PLAYER_ENTITY_START

SOURCE_A, SOURCE_B = 0x5c, 0x6c
ORIGIN = (0x104, 0x108, 0x10c)
TARGET = (0x130, 0x134, 0x138)
CLOCK = 0x110
# Observed scalar fields in the same decoded object. Used only to group records;
# neither their gameplay names nor their mapping to abilities is established.
ACTION_FINGERPRINT, ACTION_SLOT_CANDIDATE = 0x118, 0xd8


def observed_fields(writes):
    scalars = {a: v & 0xffffffff for a,s,v in writes if s == 4}
    required = (SOURCE_A, SOURCE_B, *ORIGIN, *TARGET, CLOCK)
    if any(a not in scalars for a in required):
        raise ValueError('Candidate object lacks required scalar writes')
    def number(a):
        value = struct.unpack('<f', struct.pack('<I', scalars[a]))[0]
        if not math.isfinite(value):
            raise ValueError('Nonfinite candidate coordinate/clock')
        return value
    return {'sourceA': scalars[SOURCE_A], 'sourceB': scalars[SOURCE_B],
            'originCandidate': [number(a) for a in ORIGIN],
            'targetCandidate': [number(a) for a in TARGET], 'clockCandidate': number(CLOCK),
            'actionFingerprint': scalars.get(ACTION_FINGERPRINT),
            'actionSlotCandidate': scalars.get(ACTION_SLOT_CANDIDATE)}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('replay', type=Path)
    ap.add_argument('--limit', type=int, default=200)
    ap.add_argument('--champion', help='Restrict to this exact normalized champion name')
    ap.add_argument('--all', action='store_true', help='Decode every matching packet (maximum 10000)')
    ap.add_argument('--profile', type=Path, required=True, help='Research packet-02c4.json produced by probe_packet')
    ap.add_argument('--client', type=Path, default=Path(r'C:\Riot Games\League of Legends\Game\League of Legends.exe'))
    ap.add_argument('--output', type=Path, required=True)
    args = ap.parse_args()
    if not 1 <= args.limit <= 1000:ap.error('Limit must be 1..1000')
    with args.replay.open('rb') as handle:digest = hashlib.file_digest(handle,'sha256').hexdigest()
    normalized = json.loads(Path('samples/local/replays',digest+'.json').read_text())
    tracks = {t['playerId']:t['samples'] for t in normalized['tracks']}
    allowed={p['id'] for p in normalized['players'] if args.champion is None or p['championName']==args.champion}
    if not allowed:raise ValueError('Requested champion is absent')
    times = {p:[s['timestamp'] for s in track] for p,track in tracks.items()}
    with ReplayReader.open(args.replay) as reader:
        if (reader.header.client_version,reader.header.protocol_digest)!=(CLIENT_VERSION,PROTOCOL_DIGEST):
            raise ValueError('Unsupported replay')
        blocks = [b for b in reader.iter_blocks(streams={'gameChunk'},opcodes={0x2c4},include_payload=True)
                  if b.param-PLAYER_ENTITY_START in allowed]
    if not blocks:raise ValueError('No candidate packets')
    # Deterministic even coverage through the match, not just successful examples.
    if args.all and len(blocks)>10000:raise ValueError('Too many candidate packets for a bounded research run')
    selected = list(range(len(blocks))) if args.all else sorted({round(i*(len(blocks)-1)/max(1,min(args.limit,len(blocks))-1)) for i in range(min(args.limit,len(blocks)))})
    engine = UnicornDecoderEngine(args.profile,args.client)
    rows = []
    for index in selected:
        b = blocks[index]
        observation = engine.observe_decoder('candidate',b.payload,allow_unverified=True,capture_heap_writes=False)
        fields = observed_fields(observation.output_writes)
        player = b.param-PLAYER_ENTITY_START
        j = bisect.bisect_left(times[player],b.timestamp)
        neighbors = tracks[player][max(0,j-1):j+1]
        nearest = min(neighbors,key=lambda s:abs(s['timestamp']-b.timestamp))
        origin = fields['originCandidate']
        rows.append({'timestamp':b.timestamp,'playerId':player,'packetSize':len(b.payload),**fields,
                     'identityMatches':fields['sourceA']==fields['sourceB']==b.param,
                     'clockErrorSeconds':fields['clockCandidate']-b.timestamp,
                     'nearestObservation':nearest,
                     'observationGapSeconds':abs(nearest['timestamp']-b.timestamp),
                     'originErrorWorldUnits':math.hypot(origin[0]-nearest['x'],origin[2]-nearest['y'])})
    coincident = [r for r in rows if r['observationGapSeconds']<=.002]
    summary = {'replay':args.replay.name,'sampledPackets':len(rows),'players':sorted({r['playerId'] for r in rows}),
               'identityMatches':sum(r['identityMatches'] for r in rows),'coincidentObservations':len(coincident),
               'coincidentOriginsWithin4':sum(r['originErrorWorldUnits']<=4 for r in coincident),
               'maxClockErrorSeconds':max(abs(r['clockErrorSeconds']) for r in rows),
               'status':'RESEARCH_ONLY: not a verified champion-position source'}
    args.output.parent.mkdir(parents=True,exist_ok=True)
    args.output.write_text(json.dumps({'summary':summary,'rows':rows},indent=2),encoding='utf-8')
    print(json.dumps(summary))


if __name__=='__main__':main()
