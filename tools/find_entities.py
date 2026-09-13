"""Find champion-name byte anchors without assigning semantic meaning."""
import json
import sys
from rofllens import ReplayReader

with ReplayReader.open(sys.argv[1]) as replay:
    names = [p['SKIN'] for p in replay.metadata.participants]
    hits = []
    for block in replay.iter_blocks(streams={'gameChunk', 'keyframe'}, include_payload=True):
        if block.timestamp > 5:
            continue
        for name in names:
            off = block.payload.find(name.encode())
            if off >= 0:
                hits.append({'champion': name, 'opcode': hex(block.packet_id), 'param': hex(block.param), 'time': block.timestamp, 'offset': off, 'payloadHex': block.payload.hex()})
    print(json.dumps(hits, indent=2))
