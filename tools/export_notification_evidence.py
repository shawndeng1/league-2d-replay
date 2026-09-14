"""Export small real-packet fixtures from private candidate dumps; no player names."""
import json
from pathlib import Path
from rofllens import ReplayReader
from parser.notifications import OBJECTIVES,TURRET_HASH,INHIBITOR_CATEGORY

def main():
    directory=Path.home()/'OneDrive/Documents/League of Legends/Replays'
    matches=[]
    for fixture in json.loads(Path('samples/dragon-packets.json').read_text()):
        stem=Path(fixture['file']).stem
        def rows(opcode):
            path=Path(f'samples/local/packet-{opcode:04x}.json') if stem=='NA1-5640196741' else Path(f'samples/local/{stem}-{opcode:x}.json')
            return json.loads(path.read_text())
        announcements=[]
        for row in rows(0x23d):
            fields={a:v for a,s,v in row['outputWrites'] if s==4}
            if fields[28] in OBJECTIVES or fields[28]==TURRET_HASH or fields[24]==INHIBITOR_CATEGORY:
                announcements.append(row)
        selected={0x23d:announcements,0x119:rows(0x119),0x463:rows(0x463),0x431:rows(0x431),0x406:rows(0x406)}
        packets=[{'opcode':op,'timestamp':r['timestamp'],'param':r['param'],'payloadHex':r['payloadHex']}
                 for op,items in selected.items() for r in items]
        with ReplayReader.open(directory/fixture['file']) as reader:
            keys=['SKIN','TEAM','BARON_KILLS','RIFT_HERALD_KILLS','BARRACKS_KILLED','TURRETS_KILLED','FRIENDLY_TURRET_LOST']
            participants=[{k:p[k] for k in keys} for p in reader.metadata.participants]
            matches.append({'file':fixture['file'],'sha256':fixture['sha256'],'duration':reader.metadata.game_length/1000,
                            'participants':participants,'packets':sorted(packets,key=lambda p:p['timestamp'])})
    Path('samples/notification-packets.json').write_text(json.dumps(matches,indent=2))

if __name__=='__main__':main()
