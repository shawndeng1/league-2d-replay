"""Regenerate real Void Grub fixtures from the five private integration replays."""
import json
from pathlib import Path
from rofllens import ReplayReader
from parser.events import DeathDecoder
from parser.neutral_entities import decode_neutral_identity


def main():
    engine=DeathDecoder(r'C:\Riot Games\League of Legends\Game\League of Legends.exe').engine
    output=[]
    for match in json.loads(Path('samples/grub-packets.json').read_text()):
        packets=[];ids=set()
        with ReplayReader.open(Path.home()/'OneDrive/Documents/League of Legends/Replays'/match['file']) as reader:
            def record(b):
                return {'opcode':b.packet_id,'timestamp':b.timestamp,'param':b.param,'payloadHex':b.payload.hex()}
            for b in reader.iter_blocks(streams={'gameChunk','keyframe'},opcodes={0x287},include_payload=True):
                identity=decode_neutral_identity(b,engine,unit_filter='SRU_Horde')
                if identity is not None:
                    ids.add(identity['entityId']);packets.append(record(b))
            for b in reader.iter_blocks(streams={'gameChunk'},opcodes={0x43c},include_payload=True):
                if b.param in ids:packets.append(record(b))
            participants=[{k:p[k] for k in ('SKIN','TEAM','HORDE_KILLS')} for p in reader.metadata.participants]
            output.append({'file':match['file'],'sha256':match['sha256'],'duration':reader.metadata.game_length/1000,
                           'participants':participants,'packets':packets,
                           'expectedKills':sum(int(p['HORDE_KILLS']) for p in participants)})
        print(match['file'],len(ids),'identified grubs',flush=True)
    Path('samples/grub-entity-packets.json').write_text(json.dumps(output,indent=2))

if __name__=='__main__':main()
