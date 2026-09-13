"""Validate every candidate movement packet before enabling a patch profile."""
import argparse
import json
import struct
from collections import Counter, defaultdict
from pathlib import Path
from rofllens import ReplayReader
from rofllens.decoders.emulator import UnicornDecoderEngine
from rofllens.decoders.movement import parse_movement_payloads
from fast_candidate import Candidate

ap = argparse.ArgumentParser()
ap.add_argument('replay')
args = ap.parse_args()
profile = next(Path('samples/local/profiles').glob('*/candidate.json'))
engine = UnicornDecoderEngine.from_cached_profile_sections(profile)
fast = Candidate()
counts, errors = Counter(), []
tracks = defaultdict(list)
total = 0
with ReplayReader.open(args.replay) as replay:
    for b in replay.iter_blocks(streams={'gameChunk'}, opcodes={0x4c}, include_payload=True):
        total += 1
        try:
            raw = fast.decode(b.payload)
            if total <= 30 or total % 1000 == 0:
                result = engine.observe_decoder('candidate', b.payload, allow_unverified=True)
                pointer, size = struct.unpack_from('<QI', result.output_snapshot, 0x18)
                if size > 1000000:
                    raise ValueError('implausible decoded size')
                assert raw == bytes(engine._uc.mem_read(pointer, size)), 'emulator parity failed'
            records = parse_movement_payloads(raw)
            for entity, speed, points in records:
                counts[hex(entity)] += 1
                if 0x400000ae <= entity <= 0x400000b7:
                    tracks[hex(entity)].append({'timestamp': b.timestamp, 'speed': speed, 'waypoints': points})
        except Exception as exc:
            errors.append({'time': b.timestamp, 'error': str(exc)})
        if total % 10000 == 0:
            print(total, 'packets,', len(errors), 'errors', flush=True)
report = {'packets': total, 'errors': errors, 'entities': counts, 'tracks': tracks}
Path('samples/local/candidate-paths.json').write_text(json.dumps(report))
print(json.dumps({'packets': total, 'errors': errors[:10], 'errorCount': len(errors), 'champions': {k: {'samples': len(v), 'first': v[0], 'last': v[-1]} for k,v in tracks.items()}}, indent=2))
