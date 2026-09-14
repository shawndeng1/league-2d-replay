"""Small real keyframe corpus, without player names or client executable code."""
import hashlib
import json
from pathlib import Path
from rofllens import ReplayReader

def main():
    output=[]
    directory=Path.home()/'OneDrive/Documents/League of Legends/Replays'
    for match in json.loads(Path('samples/notification-packets.json').read_text()):
        replay=directory/match['file']
        data=json.loads(Path(f"samples/local/replays/{match['sha256']}.json").read_text())
        events=[e for e in data['events'] if e.get('objective') or e.get('structure')=='TOWER']
        with ReplayReader.open(replay) as reader:
            removals=[(b.timestamp,b.param) for b in reader.iter_blocks(streams={'gameChunk'},opcodes={0x39})]
            objectives={e['source']['entityId'] for e in events if e.get('objective') in ('BARON','RIFT_HERALD')}
            objectives.update(entity for time,entity in removals if any(e.get('objective')=='DRAGON' and abs(e['timestamp']-time)<.000002 for e in events))
            packets=[];towers=set()
            for b in reader.iter_blocks(streams={'keyframe'},opcodes={0x456,0x181,0x287},include_payload=True):
                if b.packet_id==0x456 and b.timestamp==0:towers.add(b.param)
                if ((b.packet_id==0x456 and b.timestamp==0) or
                    (b.packet_id==0x181 and b.param in towers and b.timestamp<121) or
                    (b.packet_id in (0x181,0x287) and b.param in objectives)):
                    packets.append({'opcode':b.packet_id,'timestamp':b.timestamp,'param':b.param,'payloadHex':b.payload.hex()})
        output.append({'file':match['file'],'sha256':match['sha256'],'events':events,'neutralRemovals':removals,'packets':packets})
    Path('samples/map-entity-packets.json').write_text(json.dumps(output,indent=2))
    print('Exported',len(output),'matches')

if __name__=='__main__':main()
