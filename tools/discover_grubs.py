import json
from pathlib import Path
from types import SimpleNamespace as NS
from rofllens import ReplayReader
from parser.events import DeathDecoder
from parser.notifications import Announcement
from parser.grubs import normalize_grub_notifications
from parser.replay_parser import ReplayParser
engine=DeathDecoder(r'C:\Riot Games\League of Legends\Game\League of Legends.exe').engine
out=[]
for match in json.load(open('samples/dragon-packets.json')):
 stem=Path(match['file']).stem
 path=Path('samples/local/packet-023d.json') if stem.endswith('196741') else Path(f'samples/local/{stem}-23d.json')
 notices=[];packets=[]
 for row in json.load(open(path)):
  f={a:v for a,s,v in row['outputWrites'] if s==4}
  if f[28]!=0x8b8ab483:continue
  b=NS(timestamp=row['timestamp'],param=row['param'],payload=bytes.fromhex(row['payloadHex']),packet_id=0x23d)
  notices.append(Announcement(b,f[16],f[24],f[28],{100:'BLUE',200:'RED',300:'NEUTRAL'}[f[32]]))
  packets.append({'opcode':0x23d,'timestamp':b.timestamp,'param':b.param,'payloadHex':b.payload.hex()})
 with ReplayReader.open(Path.home()/'OneDrive/Documents/League of Legends/Replays'/match['file']) as reader:
  blocks=[b for b in reader.iter_blocks(streams={'gameChunk'},opcodes={0x43c,0x119},include_payload=True) if any(abs(b.timestamp-n.block.timestamp)<.000002 for n in notices)]
  players=ReplayParser._players(reader)
  events=normalize_grub_notifications(notices,blocks,engine,players,reader.metadata.participants,reader.metadata.game_length/1000)
  packets.extend({'opcode':b.packet_id,'timestamp':b.timestamp,'param':b.param,'payloadHex':b.payload.hex()} for b in blocks)
  ids={e['source']['entityId'] for e in events}
  for b in reader.iter_blocks(streams={'keyframe'},opcodes={0x181,0x287},include_payload=True):
   if b.param in ids:packets.append({'opcode':b.packet_id,'timestamp':b.timestamp,'param':b.param,'payloadHex':b.payload.hex()})
  out.append({'file':match['file'],'sha256':match['sha256'],'duration':reader.metadata.game_length/1000,'participants':[{k:p[k] for k in ('SKIN','TEAM','HORDE_KILLS')} for p in reader.metadata.participants],'packets':packets,'expectedEvents':events})
  print(match['file'],[(e['timestamp'],hex(e['source']['entityId']),e['killerPlayerId']) for e in events],flush=True)
Path('samples/grub-packets.json').write_text(json.dumps(out,indent=2))
