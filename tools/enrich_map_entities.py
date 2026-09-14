"""Refresh only map-entity data in an existing private normalized replay."""
import argparse
import hashlib
import json
from pathlib import Path
from rofllens import ReplayReader
from parser.events import DeathDecoder
from parser.notifications import ReviewNotifications
from parser.neutral_entities import extract_grub_entities
from parser.grubs import normalize_grub_notifications
from parser.map_entities import extract_map_entities
from parser.patch_16_18 import CLIENT_VERSION,PROTOCOL_DIGEST

def main():
    ap=argparse.ArgumentParser();ap.add_argument('replay',type=Path);ap.add_argument('json',type=Path)
    ap.add_argument('--client',default=r'C:\Riot Games\League of Legends\Game\League of Legends.exe')
    args=ap.parse_args();data=json.loads(args.json.read_text())
    with args.replay.open('rb') as f: digest=hashlib.file_digest(f,'sha256').hexdigest()
    if digest!=data['metadata']['sourceSha256']:raise ValueError('Replay/JSON mismatch')
    with ReplayReader.open(args.replay) as reader:
        if (reader.header.client_version,reader.header.protocol_digest)!=(CLIENT_VERSION,PROTOCOL_DIGEST):raise ValueError('Unsupported build')
        removals=[(b.timestamp,b.param) for b in reader.iter_blocks(streams={'gameChunk'},opcodes={0x39})]
        engine=DeathDecoder(args.client).engine
        notices=ReviewNotifications(engine)
        for b in reader.iter_blocks(streams={'gameChunk'},opcodes={0x23d},include_payload=True):notices.accept(b)
        blocks=[b for b in reader.iter_blocks(streams={'gameChunk'},opcodes={0x43c,0x119},include_payload=True)
                if any(abs(b.timestamp-n.block.timestamp)<.000002 for n in notices.grubs)]
        events=normalize_grub_notifications(notices.grubs,blocks,engine,data['players'],reader.metadata.participants,data['metadata']['duration'])
        events,grub_entities=extract_grub_entities(reader,engine,data['players'],reader.metadata.participants,data['metadata']['duration'],events)
        data['events']=sorted([e for e in data['events'] if e.get('objective')!='VOID_GRUB']+events,key=lambda e:(e['timestamp'],e['id']))
        data['metadata']['eventCoverage']['voidGrubs']='INDIVIDUAL_KILLS'
        data['mapEntities']=extract_map_entities(reader,engine,data['events'],removals)+grub_entities
    data['metadata']['decoder']='rofl-v2/16.18-review-v7'
    temporary=args.json.with_suffix('.tmp');temporary.write_text(json.dumps(data),encoding='utf-8');temporary.replace(args.json)
    from collections import Counter
    print(args.replay.name,dict(Counter(x['kind'] for x in data['mapEntities'])))

if __name__=='__main__':main()
