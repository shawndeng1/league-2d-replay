import json
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
import pytest
from parser.events import DeathDecoder, validate_deaths, attach_observed_locations
from rofllens.errors import SemanticDecodeError

def test_real_kills(normalized):
    events=[e for e in normalized['events'] if e['type']=='CHAMPION_KILL']; players=normalized['players']
    assert len(events)==75
    assert len({e['id'] for e in events})==75
    assert events==sorted(events,key=lambda e:(e['timestamp'],e['id']))
    assert all(e['type']=='CHAMPION_KILL' and 0<=e['victimPlayerId']<10 and 0<=e['killerPlayerId']<10 for e in events)
    assert all('assistingPlayerIds' not in e for e in events)
    assert events[0]['timestamp']==62.369717
    assert (events[0]['killerPlayerId'],events[0]['victimPlayerId'])==(7,2)
    for p in players:
        assert sum(e['victimPlayerId']==p['id'] for e in events)==p['finalStats']['deaths']
        assert sum(e['killerPlayerId']==p['id'] for e in events)==p['finalStats']['kills']
    assert all(e['source']['confidence']=='VERIFIED' for e in events)
    assert all(0<=e['timestamp']-e['source']['coordinateTimestamp']<=.5 for e in events if 'x' in e)

def test_packet_fixtures_and_stable_ids(replay_parser,replay_file):
    if not replay_parser.client_exe.is_file():pytest.skip('Exact client required')
    decoder=DeathDecoder(replay_parser.client_exe)
    players=replay_parser.inspect(replay_file)['players']
    for row in json.loads(Path('samples/death-packets.json').read_text()):
        block=SimpleNamespace(timestamp=row['timestamp'],payload=bytes.fromhex(row['payloadHex']))
        event=decoder.decode(block,players)
        assert event==decoder.decode(block,players)
        assert event['source']['victimEntityId']==row['victim']
        assert event['source']['killerEntityId']==row['killer']
        assert players[event['victimPlayerId']]['championName']==row['name']
    for payload in [b'',b'\0',b'\xff'*8]:
        with pytest.raises((ValueError,SemanticDecodeError)):decoder.decode(SimpleNamespace(timestamp=10,payload=payload),players)

def test_validation_rejects_inconsistent_totals():
    with pytest.raises(ValueError,match='disagree'):validate_deaths([],[{'id':0,'championName':'Test','finalStats':{'deaths':1}}],100)

def test_location_never_uses_future_or_stale_data():
    events=[{'victimPlayerId':0,'timestamp':t,'source':{}} for t in [1,2,10]]
    attach_observed_locations(events,[[{'timestamp':1.8,'x':10,'y':20}]])
    assert 'x' not in events[0] and 'x' not in events[2]
    assert events[1]['x']==10
