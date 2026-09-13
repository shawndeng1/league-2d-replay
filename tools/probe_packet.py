"""Explicit offline candidate probe. Never changes production decoder profiles."""
import argparse
import json
import struct
from pathlib import Path
import pefile
from rofllens import ReplayReader
from rofllens.decoders.emulator import UnicornDecoderEngine

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument('--opcode',type=lambda v:int(v,0),required=True)
    ap.add_argument('--entry',type=lambda v:int(v,0),required=True)
    ap.add_argument('--constructor-anchor',type=lambda v:int(v,0),required=True)
    ap.add_argument('--all',action='store_true')
    ap.add_argument('--constructor-start',type=lambda v:int(v,0))
    ap.add_argument('--constructor-end',type=lambda v:int(v,0))
    args=ap.parse_args()
    root=next(Path('samples/local/profiles').glob('*/profile.json'))
    profile=json.loads(root.read_text())
    pe=pefile.PE(r'C:\Riot Games\League of Legends\Game\League of Legends.exe',fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXCEPTION']])
    def bounds(address):
        entry=next(e.struct for e in pe.DIRECTORY_ENTRY_EXCEPTION if e.struct.BeginAddress<=address<e.struct.EndAddress)
        return entry.BeginAddress,entry.EndAddress-1
    start,end=bounds(args.entry)
    ctor,ctor_end=(args.constructor_start,args.constructor_end) if args.constructor_start is not None else bounds(args.constructor_anchor)
    profile.update(complete=True,stubs={'returnTrueRvas':['0x1256800'],'allocatorRvas':[],'mallocRvas':['0x11b9530'],'freeRvas':['0x11b9560']},decoders={'candidate':{'status':'candidate','entryRva':hex(start),'endRva':hex(end),'constructorRva':hex(ctor),'constructorEndRva':hex(ctor_end)}})
    path=root.with_name(f'packet-{args.opcode:04x}.json');path.write_text(json.dumps(profile))
    engine=UnicornDecoderEngine.from_cached_profile_sections(path)
    rows=[]
    with ReplayReader.open(r'C:\Users\tom-d\OneDrive\Documents\League of Legends\Replays\NA1-5640196741.rofl') as reader:
        for b in reader.iter_blocks(streams={'gameChunk'},opcodes={args.opcode},include_payload=True):
            try:
                o=engine.observe_decoder('candidate',b.payload,allow_unverified=True,capture_heap_writes=True)
                row={'timestamp':b.timestamp,'param':b.param,'payloadHex':b.payload.hex(),'output':o.output_snapshot.hex(),'heap':o.heap_snapshot.hex(),'outputWrites':o.output_writes,'heapWrites':o.heap_writes}
                rows.append(row)
                if len(rows)<=4:
                    fields={a:v&0xffffffff for a,s,v in o.output_writes if s==4}
                    print(round(b.timestamp,3),hex(b.param),[(hex(a),hex(v),round(struct.unpack('<f',struct.pack('<I',v))[0],3)) for a,v in fields.items()],flush=True)
                    print('output',o.output_snapshot[:128].hex(),'heap',o.heap_snapshot[:128].hex(),flush=True)
                if not args.all and len(rows)>=4:break
            except Exception as exc: print(type(exc).__name__,str(exc),flush=True)
    Path(f'samples/local/packet-{args.opcode:04x}.json').write_text(json.dumps(rows))
    print('decoded',len(rows),'profile',profile['decoders'],flush=True)

if __name__=='__main__':main()
