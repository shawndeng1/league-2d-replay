import copy
import json
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from parser.events import DeathDecoder
from parser.notifications import ReviewNotifications
from parser.grubs import normalize_grub_notifications
from parser.map_entities import extract_map_entities

@pytest.fixture(scope='module')
def engine(replay_parser):
    if not replay_parser.client_exe.is_file():pytest.skip('Exact local client required')
    return DeathDecoder(replay_parser.client_exe).engine

def blocks(match):
    return [NS(packet_id=p['opcode'],timestamp=p['timestamp'],param=p['param'],payload=bytes.fromhex(p['payloadHex'])) for p in match['packets']]

def decode(match,engine):
    decoder=ReviewNotifications(engine)
    for b in blocks(match):
        if b.packet_id==0x23d:decoder.accept(b)
    players=[{'id':i,'championName':p['SKIN'],'team':'BLUE' if p['TEAM']=='100' else 'RED'} for i,p in enumerate(match['participants'])]
    return normalize_grub_notifications(decoder.grubs,blocks(match),engine,players,match['participants'],match['duration'])

def test_real_grub_corpus_and_observed_positions(engine):
    corpus=json.loads(Path('samples/grub-packets.json').read_text())
    towers=json.loads(Path('samples/map-entity-packets.json').read_text())
    for match,base,count in zip(corpus,towers,[1,1,1,0,1]):
        events=decode(match,engine)
        assert len(events)==count
        assert events==match['expectedEvents']==decode(match,engine)
        # Final HORDE_KILLS is larger than event coverage; never manufacture the rest.
        assert len(events)<=sum(int(p['HORDE_KILLS']) for p in match['participants'])
        selected=[b for b in blocks(base) if b.packet_id in (0x456,0x181) and b.timestamp==0]
        selected += [b for b in blocks(match) if b.packet_id in (0x181,0x287)]
        reader=NS(iter_blocks=lambda **kw:iter(selected))
        entities=extract_map_entities(reader,engine,events,[])
        grubs=[e for e in entities if e['kind']=='VOID_GRUB']
        # These grub snapshots have no matching 0x0181 position.
        # Do not substitute a pit anchor for a decoded entity position.
        assert grubs==[]
        for e in grubs:
            assert 3500<e['x']<6500 and 8500<e['y']<12000
            assert e['states'][0]['timestamp']<e['states'][1]['timestamp']
            assert e['states'][0]['state']=='OBSERVED'

def test_grub_missing_and_conflicting_evidence_rejected(engine):
    match=json.loads(Path('samples/grub-packets.json').read_text())[0]
    missing=copy.deepcopy(match)
    missing['packets']=[p for p in missing['packets'] if p['opcode']!=0x119]
    with pytest.raises(ValueError,match='Missing or ambiguous'):decode(missing,engine)
    conflict=copy.deepcopy(match);conflict['participants'][1]['HORDE_KILLS']='0'
    with pytest.raises(ValueError,match='metadata'):decode(conflict,engine)
