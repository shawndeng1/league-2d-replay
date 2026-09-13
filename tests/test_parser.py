import math
import random
import pytest
from parser import ParseError
from parser.patch_16_18 import PatchDecoder

CHAMPIONS = ['Malphite','Graves','TwistedFate','Ashe','Seraphine','Camille','Naafiri','Syndra','Vayne','Shaco']

def test_real_container(replay_file, replay_parser):
    result = replay_parser.inspect(replay_file)
    assert result['container']['header']['clientVersion'] == '16.18.817.5716'
    assert result['container']['header']['formatVersion'] == 2
    assert result['container']['chunkCount'] == 113
    assert result['container']['streamChunks'] == {'gameChunk':74,'keyframe':37,'startKeyframe':1,'startSentinel':1}
    assert [p['championName'] for p in result['players']] == CHAMPIONS
    assert [p['championId'] for p in result['players']] == [54,104,4,22,147,164,950,134,67,35]

def test_real_movement(normalized):
    assert len(normalized['players']) == len(normalized['tracks']) == 10
    assert normalized['metadata']['patch'] == '16.18.817.5716'
    assert normalized['metadata']['duration'] == 2193.710
    assert normalized['diagnostics']['movementPackets'] == 51264
    assert normalized['diagnostics']['sampleCount'] == 56432
    assert sum(normalized['diagnostics']['opcodeHistogram'].values()) == 1971319
    assert normalized['diagnostics']['opcodeHistogram'].get('0x022c',0) == 0
    for track in normalized['tracks']:
        samples = track['samples']
        assert len(samples) > 4000
        assert samples[0]['timestamp'] == .146
        assert samples[-1]['timestamp'] > 2180
        assert all(a['timestamp'] < b['timestamp'] for a,b in zip(samples,samples[1:]))
        assert len({(s['x'],s['y']) for s in samples}) > 1000
        assert all(math.isfinite(s[a]) and 0<=s[a]<=15000 for s in samples for a in ('x','y'))
        assert all(s['path'][0] == {'x':s['x'],'y':s['y']} for s in samples)
        assert all(math.isfinite(p[a]) for s in samples for p in s['path'] for a in ('x','y'))
    assert normalized['tracks'][0]['samples'][0]['x'] == 604
    assert normalized['tracks'][0]['samples'][0]['y'] == 612
    # Real signed-delta regression: unsigned bytes incorrectly produced x=1868.
    command = min(normalized['tracks'][0]['samples'],key=lambda s:abs(s['timestamp']-29.072778))
    assert command['path'] == [{'x':1370.0,'y':9922.0},{'x':1356.0,'y':10504.0}]
    # Independent spatial sanity: opposing top laners are in the top lane at 3m.
    for index in (0,5):
        pos = min(normalized['tracks'][index]['samples'],key=lambda p:abs(p['timestamp']-180))
        assert pos['x'] < 3000 and pos['y'] > 10000

@pytest.mark.parametrize('size',[0,1,8,31,32,100,1024])
def test_malformed_never_panics(tmp_path, replay_parser, size):
    file = tmp_path/'bad.rofl'
    file.write_bytes(random.Random(size).randbytes(size))
    with pytest.raises(ParseError): replay_parser.parse(file)

def test_truncated_container(tmp_path,replay_file,replay_parser):
    file = tmp_path/'truncated.rofl'
    file.write_bytes(replay_file.read_bytes()[:1000])
    with pytest.raises(ParseError): replay_parser.parse(file)

def test_unsupported_patch(tmp_path,replay_file,replay_parser):
    raw = replay_file.read_bytes().replace(b'16.18.817.5716',b'16.19.817.5716',1)
    file = tmp_path/'future.rofl'; file.write_bytes(raw)
    with pytest.raises(ParseError) as error: replay_parser.parse(file)
    assert error.value.code == 'UNSUPPORTED_VERSION'

def test_wrong_executable(tmp_path):
    exe = tmp_path/'client.exe';exe.write_bytes(b'unrelated binary')
    with pytest.raises(ValueError,match='does not match'): PatchDecoder(exe)

def test_movement_truncation(replay_parser):
    if not replay_parser.client_exe.is_file(): pytest.skip('Exact client needed')
    decoder = PatchDecoder(replay_parser.client_exe)
    for value in (b'',b'\0',b'\0'*6,b'\xff'*20):
        with pytest.raises(ValueError): decoder.decode_movement_buffer(value)
