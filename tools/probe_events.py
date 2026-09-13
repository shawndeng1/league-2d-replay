"""Offline 16.18 event research; candidates never enter normalized output here."""
import json
import re
from pathlib import Path
import pefile
from rofllens.decoders.emulator import UnicornDecoderEngine

def main():
    profile_path = next(Path('samples/local/profiles').glob('*/profile.json'))
    profile = json.loads(profile_path.read_text())
    pe = pefile.PE(r'C:\Riot Games\League of Legends\Game\League of Legends.exe')
    start = 0xf1b3a0
    end = next(e.struct.EndAddress for e in pe.DIRECTORY_ENTRY_EXCEPTION if e.struct.BeginAddress == start)
    profile['complete'] = True
    profile['stubs'] = {'returnTrueRvas':['0x1256800'],'allocatorRvas':[], 'mallocRvas':['0x11b9530'],'freeRvas':['0x11b9560']}
    profile['decoders'] = {'eventCandidate':{'status':'candidate','entryRva':hex(start),'endRva':hex(end-1)}}
    ctor=next(e.struct for e in pe.DIRECTORY_ENTRY_EXCEPTION if e.struct.BeginAddress <= 0xe99401 < e.struct.EndAddress)
    profile['decoders']['eventCandidate'].update(constructorRva=hex(ctor.BeginAddress),constructorEndRva=hex(ctor.EndAddress-1))
    target=profile_path.with_name('event-candidate.json'); target.write_text(json.dumps(profile))
    print('function',hex(start),hex(end),flush=True)
    engine=UnicornDecoderEngine.from_cached_profile_sections(target)
    probe=json.loads(Path('samples/local/probe.json').read_text())
    for sample in next(p for p in probe['opcodes'] if p['opcode']=='0x0475')['examples']:
        try:
            result=engine.observe_decoder('eventCandidate',bytes.fromhex(sample['payloadHex']),allow_unverified=True,capture_heap_writes=True)
            print(sample['timestamp'],'output',result.output_snapshot[:112].hex(),'writes',result.output_writes,flush=True)
            print('strings',re.findall(rb'[A-Za-z][A-Za-z0-9_]{3,}',result.heap_snapshot), 'heapwrites',result.heap_writes[:40],flush=True)
        except Exception as e: print(type(e).__name__,str(e),flush=True)

if __name__=='__main__':main()
