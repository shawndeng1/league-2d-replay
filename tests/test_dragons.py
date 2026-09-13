import json
import os
from collections import Counter
from pathlib import Path
from types import SimpleNamespace
import pytest
from rofllens.errors import SemanticDecodeError
from parser.events import DeathDecoder, validate_dragons

FIXTURES=json.loads(Path('samples/dragon-packets.json').read_text())

def test_dragon_packets_across_five_matches(replay_parser):
    if not replay_parser.client_exe.is_file():pytest.skip('Exact local client required')
    decoder=DeathDecoder(replay_parser.client_exe)
    for match in FIXTURES:
        events=[]
        for row in match['packets']:
            block=SimpleNamespace(timestamp=row['timestamp'],payload=bytes.fromhex(row['payloadHex']))
            event=decoder.decode_dragon(block)
            assert event==decoder.decode_dragon(block)
            assert event['killerTeam']==row['killerTeam']
            assert event['objective']=='DRAGON'
            assert 'killerPlayerId' not in event and 'x' not in event
            events.append(event)
        assert Counter(e['killerTeam'] for e in events)==Counter(match['finalTeamDragons'])
        assert len({e['id'] for e in events})==len(events)
    for payload in [b'',b'\0',b'\xff']:
        with pytest.raises((ValueError,SemanticDecodeError)):
            decoder.decode_dragon(SimpleNamespace(timestamp=400,payload=payload))

def test_dragon_validation_rejects_mismatch():
    participants=[{'TEAM':'100','DRAGON_KILLS':'1'},{'TEAM':'200','DRAGON_KILLS':'0'}]
    event={'id':'a','timestamp':400,'killerTeam':'BLUE'}
    assert validate_dragons([event],participants,500)==[event]
    with pytest.raises(ValueError,match='disagree'):validate_dragons([],participants,500)
    with pytest.raises(ValueError,match='Duplicate'):validate_dragons([event,event],participants,500)
    with pytest.raises(ValueError,match='outside'):validate_dragons([event],participants,300)

@pytest.mark.parametrize('match',FIXTURES,ids=lambda m:m['file'])
def test_real_corpus(match,replay_parser):
    directory=Path(os.environ.get('ROFL_TEST_DIR',r'C:\Users\tom-d\OneDrive\Documents\League of Legends\Replays'))
    path=directory/match['file']
    if not path.is_file() or not replay_parser.client_exe.is_file():pytest.skip('Optional private integration fixture unavailable')
    replay=replay_parser.parse(path)
    assert replay['metadata']['sourceSha256']==match['sha256']
    assert replay['metadata']['patch']=='16.18.817.5716'
    assert len(replay['players'])==10
    assert all(len(t['samples'])>2 for t in replay['tracks'])
    assert replay['events']==sorted(replay['events'],key=lambda e:(e['timestamp'],e['id']))
    dragons=[e for e in replay['events'] if e['type']=='OBJECTIVE_KILL']
    assert Counter(e['killerTeam'] for e in dragons)==Counter(match['finalTeamDragons'])
    assert [e['timestamp'] for e in dragons]==[round(e['timestamp'],6) for e in match['packets']]
    # No guessed assist credit is exposed while discovery is incomplete.
    assert all('assistingPlayerIds' not in e for e in replay['events'])
