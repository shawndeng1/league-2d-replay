import copy
import json
from pathlib import Path
from tools.analyze_relocation_candidates import correlate_relocations


def fixture():
    return json.loads(Path('samples/relocation-cluster-fixture.json').read_text())


def test_real_cluster_matches_three_targets_without_asserting_completion():
    data=fixture();before=copy.deepcopy(data)
    matches=correlate_relocations(data['rows'],data['tracks'])
    assert [m['playerId'] for m in matches]==[2,7,0]
    assert {m['fingerprint'] for m in matches}=={'0x008fa255'}
    assert all(m['originError']<3 and m['targetError']<30 for m in matches)
    assert all(6<m['elapsedSeconds']<6.3 for m in matches)
    assert all(m['confidence']=='LIKELY' for m in matches)
    assert data==before


def test_rejects_wrong_identity_time_and_uncorroborated_target():
    data=fixture();row=next(r for r in data['rows'] if r['actionFingerprint']==0x8fa255)
    assert correlate_relocations([{**row,'sourceA':0}],data['tracks'])==[]
    assert correlate_relocations([{**row,'clockCandidate':row['timestamp']-1}],data['tracks'])==[]
    assert correlate_relocations([{**row,'targetCandidate':[0,0,0]}],data['tracks'])==[]
    assert correlate_relocations([{**row,'targetCandidate':[float('nan'),0,0]}],data['tracks'])==[]
    assert correlate_relocations(data['rows'],[])==[]
