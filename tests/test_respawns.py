import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from parser.events import DeathDecoder, merge_life_events
from parser import ParseError
from rofllens.errors import SemanticDecodeError

def test_real_respawns(normalized):
    events=normalized['events']
    assert len(events)==152
    assert events==sorted(events,key=lambda e:(e['timestamp'],e['id']))
    deaths={e['id']:e for e in events if e['type']=='CHAMPION_KILL'}
    respawns=[e for e in events if e['type']=='CHAMPION_RESPAWN']
    assert len(respawns)==71
    assert len({e['deathEventId'] for e in respawns})==71
    assert respawns[0]['timestamp']==72.390717
    assert respawns[0]['playerId']==2
    assert (respawns[0]['x'],respawns[0]['y'])==(394,461)
    for e in respawns:
        death=deaths[e['deathEventId']]
        assert death['victimPlayerId']==e['playerId']
        assert death['timestamp']<e['timestamp']<=normalized['metadata']['duration']
        assert e['source']['opcode']=='0x01b3'
        track=normalized['tracks'][e['playerId']]['samples']
        nearby=[s for s in track if e['timestamp']<=s['timestamp']<=e['timestamp']+.2]
        assert nearby
        assert ((nearby[0]['x']-e['x'])**2+(nearby[0]['y']-e['y'])**2)**.5<300
    remaining=[e for key,e in deaths.items() if key not in {r['deathEventId'] for r in respawns}]
    assert sorted(e['victimPlayerId'] for e in remaining)==[2,3,4,7]

def test_respawn_packet_fixtures(replay_parser,replay_file):
    if not replay_parser.client_exe.is_file():pytest.skip('Exact client required')
    decoder=DeathDecoder(replay_parser.client_exe)
    players=replay_parser.inspect(replay_file)['players']
    rows=json.loads(Path('samples/respawn-packets.json').read_text())
    for row in rows:
        b=SimpleNamespace(timestamp=row['timestamp'],param=row['param'],payload=bytes.fromhex(row['payloadHex']))
        e=decoder.decode_respawn(b,players)
        assert e==decoder.decode_respawn(b,players)
        assert (e['x'],e['y'])==(row['x'],row['y'])
        assert e['playerId']==row['param']-0x400000ae
    for bad in [b'',b'\0',b'\xff'*4]:
        with pytest.raises((ValueError,SemanticDecodeError)):
            decoder.decode_respawn(SimpleNamespace(timestamp=72,param=0x400000b0,payload=bad),players)

def test_life_pairing_rejects_impossible_order():
    death={'id':'death','type':'CHAMPION_KILL','timestamp':10,'victimPlayerId':0}
    respawn={'id':'respawn','type':'CHAMPION_RESPAWN','timestamp':20,'playerId':0}
    assert merge_life_events([death],[],30)==[death] # No guessed respawn.
    assert merge_life_events([death],[respawn.copy()],30)[1]['deathEventId']=='death'
    with pytest.raises(ValueError,match='preceding'):merge_life_events([],[respawn],30)
    with pytest.raises(ValueError,match='again'):merge_life_events([death,{**death,'id':'second','timestamp':11}],[],30)
    with pytest.raises(ValueError,match='outside'):merge_life_events([death],[respawn],15)

def test_nearby_real_patch_remains_unsupported(replay_parser):
    path=Path(r'C:\Users\tom-d\OneDrive\Documents\League of Legends\Replays\NA1-5636332267.rofl')
    if not path.is_file():pytest.skip('Optional older real fixture unavailable')
    with pytest.raises(ParseError) as e:replay_parser.parse(path)
    assert e.value.code=='UNSUPPORTED_VERSION'
    assert '16.17.810.4348' in str(e.value)
