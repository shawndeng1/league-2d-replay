import copy
import json
from pathlib import Path
from types import SimpleNamespace
from collections import Counter
import pytest
from parser.events import DeathDecoder
from parser.map_entities import extract_map_entities,decode_position,decode_tower

@pytest.fixture(scope='module')
def engine(replay_parser):
    if not replay_parser.client_exe.is_file():pytest.skip('Exact local client required')
    return DeathDecoder(replay_parser.client_exe).engine

class Reader:
    def __init__(self,packets):self.packets=packets
    def iter_blocks(self,**kwargs):
        for p in self.packets:
            yield SimpleNamespace(packet_id=p['opcode'],timestamp=p['timestamp'],param=p['param'],payload=bytes.fromhex(p['payloadHex']))

def test_real_map_corpus(engine):
    corpus=json.loads(Path('samples/map-entity-packets.json').read_text())
    for match in corpus:
        events=copy.deepcopy(match['events'])
        entities=extract_map_entities(Reader(match['packets']),engine,events,match['neutralRemovals'])
        towers=[x for x in entities if x['kind']=='TOWER']
        assert len(towers)==22
        assert Counter(t['team'] for t in towers)=={'BLUE':11,'RED':11}
        assert Counter(t['tier'] for t in towers)=={'OUTER':6,'INNER':6,'INHIBITOR':6,'NEXUS':4}
        assert len({x['id'] for x in entities})==len(entities)
        for tower in towers:
            assert tower['states'][0]=={'timestamp':0,'state':'ALIVE'}
            assert 0<tower['x']<15000 and 0<tower['y']<15000
        # Independent later keyframe positions agree exactly for each tower.
        positions={int(t['id'].split('-')[1],16):(t['x'],t['y']) for t in towers}
        for b in Reader(match['packets']).iter_blocks():
            if b.packet_id==0x181 and b.param in positions:
                point=decode_position(b,engine)
                assert (point['x'],point['y'])==positions[b.param]
        for event in events:
            if event.get('structure')=='TOWER':
                tower=next(t for t in towers if t['id']==event['mapEntityId'])
                assert any(s['timestamp']==event['timestamp'] and s.get('eventId')==event['id'] for s in tower['states'])
                assert tower['team']==event['destroyedTeam']
        for obj in entities:
            if obj['kind']=='TOWER':continue
            assert 0<=obj['states'][0]['timestamp']<obj['states'][1]['timestamp']
            assert obj['states'][0]['state']=='OBSERVED'
            assert obj['states'][1]['state']=='DESTROYED'
        again=extract_map_entities(Reader(match['packets']),engine,copy.deepcopy(match['events']),match['neutralRemovals'])
        assert entities==again

def test_missing_initial_towers_fails_closed(engine):
    with pytest.raises(ValueError,match='22'):
        extract_map_entities(Reader([]),engine,[],[])

def test_mismatched_position_identity_rejected(engine):
    match=json.loads(Path('samples/map-entity-packets.json').read_text())[0]
    p=next(p for p in match['packets'] if p['opcode']==0x181)
    block=next(Reader([dict(p,param=0x40000000)]).iter_blocks())
    with pytest.raises(ValueError,match='identity'):decode_position(block,engine)
