import copy
import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
import pytest
from rofllens.errors import SemanticDecodeError
from parser.events import DeathDecoder
from parser.notifications import ReviewNotifications, name_hash, Announcement

@pytest.fixture(scope='module')
def corpus():
    return json.loads(Path('samples/notification-packets.json').read_text())

@pytest.fixture(scope='module')
def engine(replay_parser):
    if not replay_parser.client_exe.is_file():pytest.skip('Exact local client required')
    return DeathDecoder(replay_parser.client_exe).engine

def players(match):
    return [{'id':i,'championName':p['SKIN'],'team':'BLUE' if p['TEAM']=='100' else 'RED'}
            for i,p in enumerate(match['participants'])]

def decode(engine,match):
    decoder=ReviewNotifications(engine)
    for p in match['packets']:
        decoder.accept(SimpleNamespace(packet_id=p['opcode'],timestamp=p['timestamp'],param=p['param'],payload=bytes.fromhex(p['payloadHex'])))
    return decoder

def test_name_hashes_identify_real_names():
    assert name_hash('SRU_Baron')==0x68ac12c9
    assert name_hash('sru_riftherald')==0xddaf53d2
    assert name_hash('Turret')==0x07b471d0
    assert name_hash('Syndra')==0x404673ab

def test_real_notification_corpus(engine,corpus):
    expected=[{'TOWER':15,'INHIBITOR':4,'BARON':2,'RIFT_HERALD':1},
              {'TOWER':12,'INHIBITOR':3,'RIFT_HERALD':1}, {'TOWER':3},
              {'TOWER':12,'INHIBITOR':1,'BARON':2,'RIFT_HERALD':1},
              {'TOWER':11,'INHIBITOR':2,'RIFT_HERALD':1}]
    for match,counts in zip(corpus,expected):
        decoder=decode(engine,match)
        events=decoder.normalize(players(match),match['participants'],match['duration'])
        assert Counter(e.get('structure',e.get('objective')) for e in events)==counts
        assert events==decoder.normalize(players(match),match['participants'],match['duration'])
        assert events==sorted(events,key=lambda e:(e['timestamp'],e['id']))
        assert len({e['id'] for e in events})==len(events)
        assert all('x' not in e and 'y' not in e for e in events)
        assert all(e['source']['confidence']=='VERIFIED' and e['source']['corroboratingOpcode']=='0x023d' for e in events)
        assert all(e['killerPlayerId'] in range(10) for e in events if e['type']=='OBJECTIVE_KILL')

def test_primary_times_and_minion_credit(engine,corpus):
    match=corpus[0];decoder=decode(engine,match)
    events=decoder.normalize(players(match),match['participants'],match['duration'])
    barons=[e for e in events if e.get('objective')=='BARON']
    assert [e['killerPlayerId'] for e in barons]==[6,6]
    assert [round(e['timestamp'],1) for e in barons]==[1470.8,1917.5]
    inhibitors=[e for e in events if e.get('structure')=='INHIBITOR']
    assert inhibitors[0]['source']['creditedEntityId']==0x400000b5
    assert inhibitors[0]['source']['killerEntityId']!=0x400000b5
    assert inhibitors[0]['source']['entityId']==inhibitors[-1]['source']['entityId'] # A later destruction after respawn.

def test_neutral_herald_self_removal_is_not_capture(engine,corpus):
    match=corpus[2];decoder=decode(engine,match)
    assert any(o.entity==o.killer for o in decoder.objectives)
    events=decoder.normalize(players(match),match['participants'],match['duration'])
    assert not any(e['type']=='OBJECTIVE_KILL' for e in events)
    decoder.announcements=[a for a in decoder.announcements if a.team!='NEUTRAL']
    with pytest.raises(ValueError,match='corroborating'):decoder.normalize(players(match),match['participants'],match['duration'])

def test_missing_conflicting_and_duplicate_evidence_rejected(engine,corpus):
    match=corpus[0];decoder=decode(engine,match);ps=players(match)
    changed=copy.deepcopy(match['participants']);changed[6]['BARON_KILLS']='3'
    with pytest.raises(ValueError,match='BARON credits'):decoder.normalize(ps,changed,match['duration'])
    saved=decoder.tower_credits.pop()
    with pytest.raises(ValueError,match='corroborating'):decoder.normalize(ps,match['participants'],match['duration'])
    decoder.tower_credits.append(saved)
    decoder.announcements.append(decoder.announcements[0])
    with pytest.raises(ValueError):decoder.normalize(ps,match['participants'],match['duration'])

@pytest.mark.parametrize('opcode',[0x23d,0x119,0x463,0x431,0x406])
def test_truncated_notifications_rejected(engine,opcode):
    decoder=ReviewNotifications(engine)
    with pytest.raises((ValueError,SemanticDecodeError)):
        decoder.accept(SimpleNamespace(packet_id=opcode,timestamp=500,param=0,payload=b''))

def test_unknown_announcement_is_ignored():
    # Unknown semantic category in a successfully decoded packet must not become
    # a speculative event, nor fail because its unused fields have unknown values.
    observation=SimpleNamespace(output_writes=[(16,4,0),(24,4,123),(28,4,456)])
    engine=SimpleNamespace(observe_decoder=lambda *a:observation)
    decoder=ReviewNotifications(engine)
    decoder.accept(SimpleNamespace(packet_id=0x23d,timestamp=500,param=0,payload=b'test'))
    assert decoder.announcements==[]
