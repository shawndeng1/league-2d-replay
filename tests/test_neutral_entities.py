import copy
import json
from pathlib import Path
from types import SimpleNamespace as NS
import pytest
from rofllens.errors import SemanticDecodeError
from parser.events import DeathDecoder
from parser.neutral_entities import decode_neutral_identity,extract_grub_entities
from parser.map_entities import decode_position

@pytest.fixture(scope='module')
def engine(replay_parser):
    if not replay_parser.client_exe.is_file():pytest.skip('Exact local client required')
    return DeathDecoder(replay_parser.client_exe).engine

def block(p):return NS(packet_id=p['opcode'],timestamp=p['timestamp'],param=p['param'],payload=bytes.fromhex(p['payloadHex']))

def extract(match,engine):
    reader=NS(iter_blocks=lambda **kw:iter(block(p) for p in match['packets'] if p['opcode'] in kw['opcodes']))
    players=[{'id':i,'team':'BLUE' if p['TEAM']=='100' else 'RED'} for i,p in enumerate(match['participants'])]
    return extract_grub_entities(reader,engine,players,match['participants'],match['duration'],[])

def test_all_individual_grubs_and_cleanup(engine):
    corpus=json.loads(Path('samples/grub-entity-packets.json').read_text())
    previous=json.loads(Path('samples/grub-packets.json').read_text())
    for match,old in zip(corpus,previous):
        events,entities=extract(match,engine)
        assert (events,entities)==extract(match,engine)
        assert len(events)==match['expectedKills']
        assert len(entities)==3
        assert {e['name'] for e in entities}=={f'SRU_Horde.12.{n}' for n in (1,2,3)}
        assert {e['id'] for e in old['expectedEvents']}<={e['id'] for e in events}
        assert events==sorted(events,key=lambda e:(e['timestamp'],e['id']))
        for p in range(10):
            assert sum(e['killerPlayerId']==p for e in events)==int(match['participants'][p]['HORDE_KILLS'])
        for e in entities:
            assert 470<e['states'][0]['timestamp']<480 # Recorded creation precedes targetability; no timer added.
            assert e['states'][0]['timestamp']<e['states'][1]['timestamp']
            assert e['states'][1]['state']==('DESTROYED' if events else 'DESPAWNED')
            assert 3500<e['x']<6500 and 8500<e['y']<12000
        assert all('x' not in e for e in events) # Placement is not asserted to be death location.
    events,_=extract(corpus[0],engine)
    assert [round(e['timestamp'],3) for e in events]==[628.276,641.987,652.348]

def test_neutral_coordinates_match_independent_position_decoder(engine):
    rows=json.loads(Path('samples/map-entity-packets.json').read_text())[0]['packets']
    positions={(p['param'],p['timestamp']):p for p in rows if p['opcode']==0x181}
    matched=0
    for p in rows:
        q=positions.get((p['param'],p['timestamp']))
        if p['opcode']!=0x287 or q is None:continue
        identity=decode_neutral_identity(block(p),engine)
        point=decode_position(block(q),engine)
        assert (identity['x'],identity['y'])==(point['x'],point['y'])
        matched+=1
    assert matched>10
    # Non-grub envelope semantics are outside this adapter's scope.
    other=next(p for p in rows if p['opcode']==0x287)
    b=block(other);b.param+=1
    assert decode_neutral_identity(b,engine,unit_filter='SRU_Horde') is None

def test_neutral_prefix_rejects_early_exit_and_wrong_entity(engine):
    p=json.loads(Path('samples/grub-entity-packets.json').read_text())[0]['packets'][0]
    for size in (0,1,7,20):
        b=block(p);b.payload=b.payload[:size]
        with pytest.raises((ValueError,SemanticDecodeError)):decode_neutral_identity(b,engine)
    b=block(p);b.param+=1
    with pytest.raises(ValueError,match='identity'):decode_neutral_identity(b,engine)

def test_missing_death_and_inconsistent_totals_fail_closed(engine):
    m=json.loads(Path('samples/grub-entity-packets.json').read_text())[0]
    missing=copy.deepcopy(m);missing['packets']=[p for p in missing['packets'] if p['opcode']!=0x43c]
    with pytest.raises(ValueError,match='Missing'):extract(missing,engine)
    m['participants'][1]['HORDE_KILLS']='2'
    with pytest.raises(ValueError,match='metadata'):extract(m,engine)
