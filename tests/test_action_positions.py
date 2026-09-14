import copy
import json
from pathlib import Path
from types import SimpleNamespace
import pytest
from parser.action_positions import position_from_writes,supplement_track,decode_action_position


def test_real_tantrum_observation_and_other_action_rejection():
    rows=json.loads(Path('samples/cast-origin-research-fixture.json').read_text())['rows']
    assert position_from_writes(rows[0]['writes'],rows[0]['timestamp'],0x400000b0) is None
    row=rows[2]
    sample=position_from_writes(row['writes'],row['timestamp'],0x400000b0)
    assert sample['x']==8210 and sample['y']==7934
    assert sample['positionOnly'] is True
    assert 'speed' not in sample and 'path' not in sample
    with pytest.raises(ValueError,match='identity'):position_from_writes(row['writes'],row['timestamp'],0x400000af)
    with pytest.raises(ValueError,match='time'):position_from_writes(row['writes'],row['timestamp']+1,0x400000b0)
    with pytest.raises(ValueError,match='Nonfinite'):position_from_writes(row['writes']+[[0x104,4,0x7f800000]],row['timestamp'],0x400000b0)


def test_other_champions_never_invoke_action_decoder():
    assert decode_action_position(None,SimpleNamespace(param=0x400000ae),[{'championName':'Ashe'}]) is None


def test_real_amumu_replay_end_to_end(replay_file,replay_parser):
    actual=replay_file.with_name('NA1-5640962900.rofl')
    if not actual.is_file() or not replay_parser.client_exe.is_file():pytest.skip('Private Amumu replay/client required')
    replay=replay_parser.parse(actual)
    track=next(t['samples'] for t in replay['tracks'] if t['playerId']==2)
    added=[s for s in track if s.get('positionOnly')]
    assert [s['timestamp'] for s in added]==[342.335318,933.029361,1035.553428]
    assert added[0]['x']==8210 and added[0]['y']==7934
    assert len(track)==len({s['timestamp'] for s in track})
    assert all(a['timestamp']<b['timestamp'] for a,b in zip(track,track[1:]))
    assert replay['diagnostics']['supplementalPositionSamples']==3
    assert replay['diagnostics']['sampleCount']==37968
    assert replay['metadata']['decoder']=='rofl-v2/16.18-review-v8'


def test_supplement_preserves_commands_dead_intervals_and_nearby_observations():
    stopped={'timestamp':0,'x':0,'y':0,'speed':0,'path':[{'x':0,'y':0}]}
    end={'timestamp':5,'x':500,'y':500,'path':[{'x':500,'y':500}]}
    candidate={'timestamp':2,'x':200,'y':200,'positionOnly':True}
    track=[stopped,end];original=copy.deepcopy(track)
    merged=supplement_track(track,[candidate,candidate],[])
    assert [s['timestamp'] for s in merged]==[0,2,5]
    assert supplement_track(merged,[candidate],[])==merged
    assert track==original
    assert supplement_track(track,[{**candidate,'timestamp':.05}],[])==track
    assert supplement_track(track,[candidate],[{'timestamp':1,'type':'CHAMPION_KILL'}])==track
    moving={**stopped,'speed':100,'path':[{'x':0,'y':0},{'x':1000,'y':0}]}
    assert supplement_track([moving,end],[candidate],[])==[moving,end]
    assert supplement_track([], [candidate],[])==[]
