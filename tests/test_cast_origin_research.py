import json
from pathlib import Path
import pytest
from tools.research_cast_origins import observed_fields


def test_real_observation_writes_keep_origin_and_target_separate():
    rows=json.loads(Path('samples/cast-origin-research-fixture.json').read_text())['rows']
    first=observed_fields(rows[0]['writes'])
    assert first['sourceA']==first['sourceB']==0x400000b0
    assert first['originCandidate'][0]==pytest.approx(7726.394,abs=.001)
    assert first['originCandidate'][2]==pytest.approx(7410.062,abs=.001)
    assert first['targetCandidate'][0]==pytest.approx(8470.953,abs=.001)
    assert first['clockCandidate']==pytest.approx(rows[0]['timestamp'],abs=.002)
    later=observed_fields(rows[-1]['writes'])
    assert later['originCandidate'][0]==8210
    assert later['originCandidate'][2]==7934
    # Per-byte obfuscation after scalar writes must not overwrite candidate floats.
    extra=rows[0]['writes']+[[0x104,1,255]]
    assert observed_fields(extra)==first


def test_incomplete_or_nonfinite_candidate_rejected():
    with pytest.raises(ValueError,match='lacks'):observed_fields([])
    rows=json.loads(Path('samples/cast-origin-research-fixture.json').read_text())['rows']
    with pytest.raises(ValueError,match='Nonfinite'):
        observed_fields(rows[0]['writes']+[[0x104,4,0x7f800000]])
