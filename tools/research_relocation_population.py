"""Full-match research scan for the observed relocation fingerprints.

No normalized data is written. Unmatched casts are unresolved, not automatically
labelled cancellations. Packet envelopes are retained as evidence only.
"""
import argparse
import bisect
import hashlib
import json
from collections import Counter
from pathlib import Path
from rofllens import ReplayReader
from rofllens.decoders.emulator import UnicornDecoderEngine
from parser.patch_16_18 import CLIENT_VERSION, PROTOCOL_DIGEST, PLAYER_ENTITY_START
from tools.research_cast_origins import observed_fields

FINGERPRINTS={0x008fa255,0x0a9306a0}
SEQUENCE_OPCODES={0x0345,0x0268,0x03d6,0x01c1,0x0129,0x016b,0x021c,0x028d,0x0499,0x0240,0x009b,0x0136}


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('replays',type=Path,nargs='+')
    ap.add_argument('--profile',type=Path,required=True)
    ap.add_argument('--client',type=Path,default=Path(r'C:\Riot Games\League of Legends\Game\League of Legends.exe'))
    ap.add_argument('--output',type=Path,required=True)
    args=ap.parse_args();args.output.mkdir(parents=True,exist_ok=True)
    engine=UnicornDecoderEngine(args.profile,args.client)
    for path in args.replays:
        with path.open('rb') as handle:digest=hashlib.file_digest(handle,'sha256').hexdigest()
        replay=json.loads(Path('samples/local/replays',digest+'.json').read_text())
        rows=[];packets={p['id']:[] for p in replay['players']};histogram=Counter();decoded=0
        with ReplayReader.open(path) as reader:
            if (reader.header.client_version,reader.header.protocol_digest)!=(CLIENT_VERSION,PROTOCOL_DIGEST):raise ValueError('Unsupported replay')
            for block in reader.iter_blocks(streams={'gameChunk'},opcodes={0x02c4,*SEQUENCE_OPCODES},include_payload=True):
                player=block.param-PLAYER_ENTITY_START
                if player not in packets:continue
                if block.packet_id==0x02c4:
                    decoded+=1
                    observation=engine.observe_decoder('candidate',block.payload,allow_unverified=True,capture_heap_writes=False)
                    fields=observed_fields(observation.output_writes)
                    fingerprint=fields['actionFingerprint'];histogram[f'{fingerprint:#010x}']+=1
                    if fingerprint in FINGERPRINTS:rows.append({'timestamp':block.timestamp,'entity':hex(block.param),'playerId':player,'packetSize':len(block.payload),**fields})
                else:packets[player].append({'timestamp':block.timestamp,'opcode':f'{block.packet_id:#06x}','size':len(block.payload),'payloadHex':block.payload.hex()})
        times={p:[b['timestamp'] for b in values] for p,values in packets.items()}
        for row in rows:
            if row['actionFingerprint']!=0x008fa255:continue
            player=row['playerId'];t=row['timestamp']
            a=bisect.bisect_left(times[player],t-.01);b=bisect.bisect_right(times[player],t+12)
            row['nearbyPackets']=packets[player][a:b]
        result={'replay':path.name,'replayId':digest,'decodedActionPackets':decoded,'fingerprintHistogram':dict(histogram),'rows':rows,'status':'RESEARCH_ONLY'}
        (args.output/(path.stem+'.json')).write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({'replay':path.name,'decoded':decoded,'candidateActions':sum(r['actionFingerprint']==0x008fa255 for r in rows)}),flush=True)


if __name__=='__main__':main()
