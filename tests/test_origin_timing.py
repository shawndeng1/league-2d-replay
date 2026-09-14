import copy
import json
from pathlib import Path
import pytest
from tools.analyze_origin_timing import compare_origin,name_fingerprint


def test_real_earlier_origins_and_instant_relocation_cases_are_not_conflated():
    cases=json.loads(Path('samples/origin-timing-fixture.json').read_text())['cases']
    for index,case in enumerate(cases):
        original=copy.deepcopy(case)
        result=compare_origin(case['row'],case['samples'])
        if index<2:
            assert result['timingClass']=='EARLIER_POSITION_CORROBORATED'
            assert result['arrivalMatch']['errorWorldUnits']>400
            assert result['embeddedTimeMatch']['errorWorldUnits']<2
        else:
            assert result['timingClass']=='ORIGIN_MISMATCH_AT_EMBEDDED_TIME'
            assert result['embeddedTimeMatch']['errorWorldUnits']>300
        if index in (2,3):assert result['actionNameHypothesis']=='SummonerFlash'
        if index==4:assert result['actionNameHypothesis']=='VladimirE'
        assert case==original


def test_name_hypothesis_hashes_are_case_insensitive():
    assert name_fingerprint('SummonerFlash')==name_fingerprint('summonerflash')==0x6496ea8
    assert name_fingerprint('Tantrum')==0xa85b9cd


def test_sparse_or_missing_observations_are_not_corroboration():
    row={'timestamp':10,'clockCandidate':9,'originCandidate':[10,0,20]}
    result=compare_origin(row,[{'timestamp':0,'x':10,'y':20}])
    assert result['timingClass']=='INSUFFICIENT_OBSERVATIONS'
    assert not result['embeddedTimeMatch']['corroborated']
    with pytest.raises(ValueError):compare_origin(row,[])
    with pytest.raises(ValueError):compare_origin(row,[{'timestamp':2,'x':0,'y':0},{'timestamp':1,'x':0,'y':0}])
