import copy
import json
from pathlib import Path
from tools.analyze_relocation_population import analyze_population


def inputs():
    data=json.loads(Path('samples/relocation-cluster-fixture.json').read_text())
    for row in data['rows']:row['playerId']=int(row['entity'],16)-0x400000ae
    scan={'replay':'fixture','replayId':data['replayId'],'decodedActionPackets':len(data['rows']),'rows':data['rows']}
    replay={'tracks':data['tracks'],'players':[{'id':t['playerId'],'championName':str(t['playerId'])} for t in data['tracks']],'events':[]}
    return scan,replay


def test_accounts_for_every_candidate_including_uncorroborated_target():
    scan,replay=inputs();original=copy.deepcopy((scan,replay))
    report=analyze_population(scan,replay)
    assert report['counts']=={'TARGET_OBSERVED':3}
    assert all(r['elapsedToObservation']>6 for r in report['actions'])
    assert (scan,replay)==original
    row=next(r for r in scan['rows'] if r['actionFingerprint']==0x008fa255)
    row['targetCandidate']=[0,0,0]
    report=analyze_population(scan,replay)
    assert report['counts']=={'UNRESOLVED':1,'TARGET_OBSERVED':2}
    assert len(report['actions'])==3
    assert report['actions'][0]['firstTargetTimestamp'] is None


def test_invalid_source_and_clock_are_reported_not_silently_dropped():
    scan,replay=inputs()
    rows=[r for r in scan['rows'] if r['actionFingerprint']==0x008fa255]
    rows[0]['sourceA']=0;rows[1]['clockCandidate']-=1
    report=analyze_population(scan,replay)
    assert report['counts']=={'INVALID_IDENTITY_OR_TIME':2,'TARGET_OBSERVED':1}


def test_packet_proximity_is_not_reported_as_verified_completion():
    scan,replay=inputs();row=scan['rows'][0]
    row['nearbyPackets']=[{'timestamp':row['timestamp']+3,'opcode':'0x03d6','size':5,'payloadHex':'0000000000'}]
    action=analyze_population(scan,replay)['actions'][0]
    assert action['endToObservation']>3
    assert action['candidateEndPackets'][0]['elapsed']==3
    assert 'completionTimestamp' not in action
