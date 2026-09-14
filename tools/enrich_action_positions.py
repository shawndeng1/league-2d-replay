"""Add validated, scoped action observations to a matching local replay cache."""
import argparse
import hashlib
import json
from pathlib import Path
from rofllens import ReplayReader
from parser.events import DeathDecoder
from parser.patch_16_18 import CLIENT_VERSION,PROTOCOL_DIGEST
from parser.action_positions import ACTION_OPCODE,SOURCE_KIND,decode_action_position,supplement_track


def main():
    ap=argparse.ArgumentParser(description=__doc__)
    ap.add_argument('replay',type=Path)
    ap.add_argument('json',type=Path)
    ap.add_argument('--client',default=r'C:\Riot Games\League of Legends\Game\League of Legends.exe')
    args=ap.parse_args()
    original=args.json.read_bytes();data=json.loads(original)
    with args.replay.open('rb') as handle:digest=hashlib.file_digest(handle,'sha256').hexdigest()
    if digest!=data['metadata']['sourceSha256'] or data['metadata']['patch']!=CLIENT_VERSION:
        raise ValueError('Replay/cache mismatch')
    candidates=[[] for _ in data['players']]
    engine=DeathDecoder(args.client).engine
    with ReplayReader.open(args.replay) as reader:
        if (reader.header.client_version,reader.header.protocol_digest)!=(CLIENT_VERSION,PROTOCOL_DIGEST):
            raise ValueError('Unsupported replay')
        for block in reader.iter_blocks(streams={'gameChunk'},opcodes={ACTION_OPCODE},include_payload=True):
            result=decode_action_position(engine,block,data['players'])
            if result is not None:candidates[result[0]].append(result[1])
    for track in data['tracks']:
        player=track['playerId']
        life=[e for e in data['events'] if (e['type']=='CHAMPION_KILL' and e['victimPlayerId']==player) or (e['type']=='CHAMPION_RESPAWN' and e['playerId']==player)]
        track['samples']=supplement_track(track['samples'],candidates[player],life)
    count=sum(s.get('positionSource')==SOURCE_KIND for t in data['tracks'] for s in t['samples'])
    data['diagnostics']['sampleCount']=sum(len(t['samples']) for t in data['tracks'])
    data['diagnostics']['supplementalPositionSamples']=count
    data['metadata']['decoder']='rofl-v2/16.18-review-v8'
    data['metadata']['positionSource']='movement-path-origin-with-route-and-amumu-observations'
    backup=args.json.with_suffix('.before-amumu.bak')
    if not backup.exists():backup.write_bytes(original)
    temporary=args.json.with_suffix('.amumu.tmp')
    temporary.write_text(json.dumps(data),encoding='utf-8');temporary.replace(args.json)
    print(json.dumps({'replay':args.replay.name,'candidateObservations':sum(map(len,candidates)),'supplementalSamples':count}))


if __name__=='__main__':main()
