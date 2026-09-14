"""Explicit offline candidate probe. Never changes production decoder profiles."""
import argparse
import json
import struct
from bisect import bisect_left
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
    ap.add_argument('--stream',default='gameChunk')
    ap.add_argument('--entity',type=lambda v:int(v,0))
    ap.add_argument('--replay',default=r'C:\Users\tom-d\OneDrive\Documents\League of Legends\Replays\NA1-5640196741.rofl')
    ap.add_argument('--output',type=Path)
    ap.add_argument('--after',type=float,default=0)
    ap.add_argument('--at-events',type=Path,help='Only probe timestamps of champion kills in normalized JSON')
    ap.add_argument('--constructor-start',type=lambda v:int(v,0))
    ap.add_argument('--constructor-end',type=lambda v:int(v,0))
    ap.add_argument('--stack-probe', action='store_true', help='Stub exact-build __chkstk; emulator stack is already committed')
    ap.add_argument('--trace', action='store_true', help='Print final emulated instruction addresses on failure')
    ap.add_argument('--runtime-defaults',action='store_true',help='Initialize single-thread MSVC guards in private emulated memory')
    ap.add_argument('--skip-log',action='store_true',help='Research only: skip client logging, still report decode result')
    args=ap.parse_args()
    root=next(Path('samples/local/profiles').glob('*/profile.json'))
    profile=json.loads(root.read_text())
    pe=pefile.PE(r'C:\Riot Games\League of Legends\Game\League of Legends.exe',fast_load=True)
    pe.parse_data_directories(directories=[pefile.DIRECTORY_ENTRY['IMAGE_DIRECTORY_ENTRY_EXCEPTION']])
    def bounds(address):
        entry=next((e.struct for e in pe.DIRECTORY_ENTRY_EXCEPTION if e.struct.BeginAddress<=address<e.struct.EndAddress),None)
        if entry:return entry.BeginAddress,entry.EndAddress-1
        # Leaf constructors have no unwind entry. Use preceding INT3 padding
        # and first RET; print the range for manual verification before use.
        import capstone
        prefix=pe.get_data(address-64,64)
        start=address-64+prefix.rfind(b'\xcc')+1
        if start<=address-64:raise ValueError('Supply explicit constructor bounds')
        for ins in capstone.Cs(capstone.CS_ARCH_X86,capstone.CS_MODE_64).disasm(pe.get_data(start,2048),start):
            if ins.mnemonic=='ret':return start,ins.address
        raise ValueError('No leaf constructor return found')
    start,end=bounds(args.entry)
    ctor,ctor_end=(args.constructor_start,args.constructor_end) if args.constructor_start is not None else bounds(args.constructor_anchor)
    profile.update(complete=True,stubs={'returnTrueRvas':['0x1256800'],'allocatorRvas':[],'mallocRvas':['0x11b9530'],'freeRvas':['0x11b9560']},decoders={'candidate':{'status':'candidate','entryRva':hex(start),'endRva':hex(end),'constructorRva':hex(ctor),'constructorEndRva':hex(ctor_end)}})
    path=root.with_name(f'packet-{args.opcode:04x}.json');path.write_text(json.dumps(profile))
    engine=UnicornDecoderEngine.from_cached_profile_sections(path)
    if args.skip_log:engine._uc.mem_write(profile['imageBase']+0x23a980,b'\xc3')
    if args.runtime_defaults:
        import unicorn.x86_const as x86
        uc=engine._uc; tls=0x30000000; base=profile['imageBase']
        uc.mem_map(tls,0x10000)
        uc.mem_write(tls+0x58,struct.pack('<Q',tls+0x1000))
        index=struct.unpack('<I',uc.mem_read(base+0x20696c8,4))[0]
        if index>128:raise ValueError('Unexpected TLS index')
        uc.mem_write(tls+0x1000+index*8,struct.pack('<Q',tls+0x2000))
        uc.mem_write(tls+0x2140,struct.pack('<i',-2147483648))
        uc.reg_write(x86.UC_X86_REG_GS_BASE,tls)
        engine._base_context=uc.context_save()
        # Single-thread static initialization: header acquires guard, footer
        # marks initialized (INT_MIN+1); real default constructors still run.
        uc.mem_write(base+0x19e74b4,b'\xc7\x01\xff\xff\xff\xff\xc3')
        uc.mem_write(base+0x19e7448,b'\xc7\x01\x01\x00\x00\x80\xc3')
        uc.mem_write(base+0x19e7784,b'\x31\xc0\xc3') # atexit: no process shutdown here
    if args.stack_probe:
        # __chkstk must preserve RAX (allocation size). The generic free stub
        # zeroes RAX and cannot be used here. This patches only emulated memory.
        engine._uc.mem_write(profile['imageBase']+0x19e7860,b'\xc3')
        # CRT thread-local-data accessor: null selects its static fallback.
        engine._uc.mem_write(profile['imageBase']+0x1a39f3c,b'\x31\xc0\xc3')
    from collections import deque
    trace=deque(maxlen=20)
    if args.trace:
        import unicorn
        engine._uc.hook_add(unicorn.UC_HOOK_CODE,lambda uc,address,size,data:trace.append(hex(address-profile['imageBase'])))
        def log_call(uc,address,size,data):
            import unicorn.x86_const as x86
            for reg in [x86.UC_X86_REG_RDX,x86.UC_X86_REG_R8,x86.UC_X86_REG_R9]:
                pointer=uc.reg_read(reg)
                try:print('CLIENT LOG',bytes(uc.mem_read(pointer,200)).split(b'\0')[0],flush=True)
                except Exception:pass
        engine._uc.hook_add(unicorn.UC_HOOK_CODE,log_call,begin=profile['imageBase']+0x23a980,end=profile['imageBase']+0x23a980)
    rows=[]
    event_times=None if args.at_events is None else sorted(e['timestamp'] for e in json.loads(args.at_events.read_text())['events'] if e['type']=='CHAMPION_KILL')
    with ReplayReader.open(args.replay) as reader:
        for b in reader.iter_blocks(streams={args.stream},opcodes={args.opcode},include_payload=True):
            if b.timestamp<args.after:continue
            if args.entity is not None and b.param!=args.entity:continue
            if event_times is not None:
                i=bisect_left(event_times,b.timestamp-.000002)
                if i==len(event_times) or abs(event_times[i]-b.timestamp)>.000002:continue
            try:
                o=engine.observe_decoder('candidate',b.payload,allow_unverified=True,capture_heap_writes=True)
                if args.skip_log:
                    import unicorn.x86_const as x86
                    print('decode result',engine._uc.reg_read(x86.UC_X86_REG_RAX)&255,flush=True)
                row={'timestamp':b.timestamp,'param':b.param,'payloadHex':b.payload.hex(),'output':o.output_snapshot.hex(),'heap':o.heap_snapshot.hex(),'outputWrites':o.output_writes,'heapWrites':o.heap_writes}
                rows.append(row)
                if len(rows)<=4:
                    fields={a:v&0xffffffff for a,s,v in o.output_writes if s==4}
                    print(round(b.timestamp,3),hex(b.param),[(hex(a),hex(v),round(struct.unpack('<f',struct.pack('<I',v))[0],3)) for a,v in fields.items()],flush=True)
                    print('output',o.output_snapshot[:128].hex(),'heap',o.heap_snapshot[:128].hex(),flush=True)
                if not args.all and len(rows)>=4:break
            except Exception as exc:
                if args.trace:print(list(trace),flush=True)
                raise RuntimeError(f'Candidate failed at {b.timestamp:.6f}s; no fields accepted') from exc
    (args.output or Path(f'samples/local/packet-{args.opcode:04x}.json')).write_text(json.dumps(rows))
    print('decoded',len(rows),'profile',profile['decoders'],flush=True)

if __name__=='__main__':main()
