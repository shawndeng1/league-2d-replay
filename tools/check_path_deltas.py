"""Compare waypoint delta interpretations against subsequent observed origins."""
import json
import math
import struct
import sys
from collections import defaultdict
from pathlib import Path

from rofllens import ReplayReader
from rofllens.decoders import movement
from parser.patch_16_18 import PatchDecoder

original = movement._coordinate
def signed(payload, cursor, previous, delta):
    if delta:
        if cursor >= len(payload): raise ValueError('Truncated delta')
        return (previous + struct.unpack_from('<b', payload, cursor)[0]) & 65535, cursor+1
    return original(payload, cursor, previous, delta)

def position(record, elapsed):
    remaining = record['speed']*elapsed
    points = record['path']
    for a,b in zip(points,points[1:]):
        length = math.hypot(b['x']-a['x'],b['y']-a['y'])
        if length and remaining < length:
            return {k:a[k]+(b[k]-a[k])*remaining/length for k in ('x','y')}
        remaining -= length
    return points[-1]

decoder = PatchDecoder(Path(r'C:\Riot Games\League of Legends\Game\League of Legends.exe'))
tracks = defaultdict(list)
with ReplayReader.open(sys.argv[1]) as reader:
    for b in reader.iter_blocks(streams={'gameChunk'},opcodes={0x4c},include_payload=True):
        raw=decoder.decode_movement_buffer(b.payload)
        if not raw: continue
        movement._coordinate=original
        unsigned=movement.parse_movement_payloads(raw)
        movement._coordinate=signed
        signed_paths=movement.parse_movement_payloads(raw)
        for (entity,speed,u),(_,_,s) in zip(unsigned,signed_paths):
            if 0x400000ae<=entity<=0x400000b7:
                tracks[entity].append({'timestamp':b.timestamp,'speed':speed,'path':s,'unsigned':u})
movement._coordinate=original
errors={'signed':[],'unsigned':[]}
for records in tracks.values():
    for a,b in zip(records,records[1:]):
        dt=b['timestamp']-a['timestamp']
        if not 0.03<=dt<=1 or a['speed']<=0 or a['path']==a['unsigned']:continue
        for mode in errors:
            pred=position({**a,'path':a['path'] if mode=='signed' else a['unsigned']},dt)
            actual=b['path'][0]
            errors[mode].append(math.hypot(pred['x']-actual['x'],pred['y']-actual['y']))
import statistics
print({mode:{'comparisons':len(e),'medianError':statistics.median(e),'meanError':statistics.mean(e),'within50':sum(v<50 for v in e)} for mode,e in errors.items()})
Path('samples/local/signed-paths.json').write_text(json.dumps(tracks))
