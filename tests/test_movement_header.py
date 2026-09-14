import json
import struct
from pathlib import Path
import pytest
from parser.patch_16_18 import PatchDecoder
from parser.movement import parse_movement_payloads


@pytest.mark.parametrize('selector_a,expected_a', [(2,2),(5,0),(1,1),(3,0xffffffff)])
@pytest.mark.parametrize('selector_b,expected_b', [(2,65535),(6,1),(4,2),(3,0)])
def test_inline_constants(selector_a,expected_a,selector_b,expected_b):
    # No lookup is required for an empty buffer with inline header constants.
    decoder = PatchDecoder.__new__(PatchDecoder)
    decoder.buffer = bytes(range(256))
    packet = decoder.decode_movement_packet(bytes([1 | selector_a<<1 | selector_b<<4]))
    assert packet.field_u32 == expected_a
    assert packet.record_count == expected_b
    assert packet.buffer == b''


def test_varint_bounds():
    decoder = PatchDecoder.__new__(PatchDecoder)
    decoder.field_a = decoder.field_b = decoder.buffer = bytes(range(256))
    packet = decoder.decode_movement_packet(bytes([1, 0xac, 2, 3]))
    assert (packet.field_u32,packet.record_count)==(300,3)
    for payload in [b'', b'\x01', b'\x01\x80', b'\x01\xff\xff\xff\xff\x10', b'\x01\x00\xff\xff\x04']:
        with pytest.raises(ValueError):decoder.decode_movement_packet(payload)


def test_real_header_fixture(replay_parser):
    if not replay_parser.client_exe.is_file():pytest.skip('Exact client required')
    decoder = PatchDecoder(replay_parser.client_exe)
    fixture=json.loads(Path('samples/movement-header-fixture.json').read_text())
    for example in fixture['packets']:
        payload=bytes.fromhex(example['payloadHex'])
        packet=decoder.decode_movement_packet(payload)
        assert packet.field_u32==example['fieldU32']
        assert packet.record_count==example['recordCount']==len(parse_movement_payloads(packet.buffer))
        assert packet.buffer==decoder.decode_movement_buffer(payload)


def test_count_disagreement_and_empty_buffer():
    raw=struct.pack('<HIfhh',2,0x400000ae,350,0,0)
    assert len(parse_movement_payloads(raw,expected_count=1))==1
    assert parse_movement_payloads(b'',expected_count=0)==[]
    for payload,count in [(raw,0),(raw,2),(b'',1)]:
        with pytest.raises(ValueError,match='record count'):
            parse_movement_payloads(payload,expected_count=count)
