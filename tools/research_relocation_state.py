"""Compare opaque 0x03d6 scalar states against relocation action windows.

Object offsets are observed from exact-client deserialization. Scalar meanings
remain UNKNOWN; this tool does not emit normalized channel/teleport events.
"""
import argparse
import json
import struct
from pathlib import Path
from rofllens import ReplayReader
from rofllens.decoders.emulator import UnicornDecoderEngine
from parser.patch_16_18 import CLIENT_VERSION,PROTOCOL_DIGEST,PLAYER_ENTITY_START


def scalar_fields(writes):
    values={offset:value for offset,size,value in writes if size==4}
    words={offset:value for offset,size,value in writes if size==2}
    return {'field18':struct.unpack('<f',struct.pack('<I',values[0x18]&0xffffffff))[0],
            'field1c':words.get(0x1c),'field20':struct.unpack('<f',struct.pack('<I',values[0x20]&0xffffffff))[0]}


def main():
    ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('replay',type=Path);ap.add_argument('--profile',type=Path,required=True)
    ap.add_argument('--client',type=Path,default=Path(r'C:\Riot Games\League of Legends\Game\League of Legends.exe'))
    ap.add_argument('--output',type=Path,required=True);args=ap.parse_args()
    engine=UnicornDecoderEngine(args.profile,args.client);rows=[]
    with ReplayReader.open(args.replay) as reader:
        if (reader.header.client_version,reader.header.protocol_digest)!=(CLIENT_VERSION,PROTOCOL_DIGEST):raise ValueError('Unsupported replay')
        for block in reader.iter_blocks(streams={'gameChunk'},opcodes={0x03d6},include_payload=True):
            player=block.param-PLAYER_ENTITY_START
            if not 0<=player<10:continue
            observation=engine.observe_decoder('candidate',block.payload,allow_unverified=True,capture_heap_writes=False)
            rows.append({'timestamp':block.timestamp,'playerId':player,'size':len(block.payload),'payloadHex':block.payload.hex(),
                         **scalar_fields(observation.output_writes)})
    args.output.write_text(json.dumps(rows,indent=2)+'\n');print(f'{len(rows)} scalar records')


if __name__=='__main__':main()
