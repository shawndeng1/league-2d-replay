"""Explicit candidate emulation, isolated from the production parser."""
import json
import struct
from pathlib import Path
from rofllens.decoders.emulator import UnicornDecoderEngine
from rofllens.decoders.movement import parse_movement_payloads

profile_path = next(Path('samples/local/profiles').glob('*/profile.json'))
profile = json.loads(profile_path.read_text())
profile['complete'] = True  # Research engine only; decoder remains candidate.
profile['stubs'] = {'returnTrueRvas': ['0x1256800'], 'allocatorRvas': [], 'mallocRvas': ['0x11b9530'], 'freeRvas': ['0x11b9560']}
profile['decoders'] = {'candidate': {'status': 'candidate', 'entryRva': '0x104f430', 'endRva': '0x104f82c'}}
research = profile_path.with_name('candidate.json')
research.write_text(json.dumps(profile, indent=2))
engine = UnicornDecoderEngine.from_cached_profile_sections(research)
probe = json.loads(Path('samples/local/probe.json').read_text())
for sample in next(x for x in probe['opcodes'] if x['opcode']=='0x004c')['examples']:
    try:
        result = engine.observe_decoder('candidate', bytes.fromhex(sample['payloadHex']), allow_unverified=True)
        print('time', sample['timestamp'], 'output', result.output_snapshot[:48].hex(), 'heap', result.heap_snapshot[:256].hex())
        print('writes', result.output_writes)
        pointer, size = struct.unpack_from('<QI', result.output_snapshot, 0x18)
        raw = bytes(engine._uc.mem_read(pointer, size))
        print('paths', parse_movement_payloads(raw))
    except Exception as exc:
        print(type(exc).__name__, str(exc))
