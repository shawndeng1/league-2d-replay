"""Validate candidate death fields against all final participant totals."""
import json
import struct
from collections import Counter
from pathlib import Path
from rofllens import ReplayReader
from rofllens.decoders.emulator import UnicornDecoderEngine

def last(writes,offset):
    return [v & 0xffffffff for o,s,v in writes if o==offset and s==4][-1]

def main():
    engine=UnicornDecoderEngine.from_cached_profile_sections(next(Path('samples/local/profiles').glob('*/event-candidate.json')))
    rows=[]
    with ReplayReader.open(r'C:\Users\tom-d\OneDrive\Documents\League of Legends\Replays\NA1-5640196741.rofl') as reader:
        roster=reader.metadata.participants
        for b in reader.iter_blocks(streams={'gameChunk'},opcodes={0x475},include_payload=True):
            o=engine.observe_decoder('eventCandidate',b.payload,allow_unverified=True,capture_heap_writes=True)
            ptr,length=struct.unpack_from('<QI',o.output_snapshot,0x38)
            name=o.heap_snapshot[ptr-engine.HEAP_BASE:ptr-engine.HEAP_BASE+length].decode()
            rows.append({'timestamp':b.timestamp,'victim':last(o.output_writes,0x30),'killer':last(o.output_writes,0x58),'name':name,'size':len(b.payload),'payloadHex':b.payload.hex(),'output':o.output_snapshot[:104].hex(),'heap':o.heap_snapshot.hex(),'heapWrites':o.heap_writes,'outputWrites':o.output_writes})
    aliases={r['victim']:r['name'] for r in rows}
    kills=Counter(aliases.get(r['killer'],hex(r['killer'])) for r in rows); deaths=Counter(r['name'] for r in rows)
    print('aliases',aliases)
    print('kills',kills,'deaths',deaths)
    print('metadata',[(p['SKIN'],p['CHAMPIONS_KILLED'],p['NUM_DEATHS']) for p in roster])
    for r in rows[:8]: print(round(r['timestamp'],3),aliases.get(r['killer']),r['name'])
    Path('samples/local/death-evidence.json').write_text(json.dumps(rows))

if __name__=='__main__':main()
