import struct
import pytest
from parser.movement import parse_movement_payloads

def test_signed_delta_and_absolute_waypoints():
    # Three waypoints, both axes delta-encoded on point 2, absolute on point 3.
    raw = struct.pack('<HIfBhhbbhh', 6, 0x400000ae, 350, 3, 100, 200, -10, -128, -50, 400)
    [(entity,speed,path)] = parse_movement_payloads(raw)
    assert entity == 0x400000ae and speed == 350
    assert path == [{'x':7558,'y':7812},{'x':7538,'y':7556},{'x':7258,'y':8212}]

def test_signed_wrap_and_optional_byte():
    raw = struct.pack('<HIfBBhhbb',5,1,300,1,3,-32768,32767,-1,1)
    path = parse_movement_payloads(raw)[0][2]
    assert path[1] == {'x':72892,'y':-58124}

def test_concatenation_and_truncation():
    raw=struct.pack('<HIfhh',2,1,300,0,0)
    assert len(parse_movement_payloads(raw+raw)) == 2
    for size in range(1,len(raw)):
        with pytest.raises(ValueError): parse_movement_payloads(raw[:size])

@pytest.mark.parametrize('speed',[float('nan'),float('inf'),-1,6000])
def test_bad_speed(speed):
    with pytest.raises(ValueError): parse_movement_payloads(struct.pack('<HIfhh',2,1,speed,0,0))
