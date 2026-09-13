"""16.18 research translation of 0x104f430 / 0xfc00f0; parity required."""
import json
from pathlib import Path

def rol(v, n):
    return ((v << n) | (v >> (8-n))) & 255

def swap(v):
    return ((v & 0x55) << 1) | ((v >> 1) & 0x55)

class Candidate:
    def __init__(self):
        p = next(Path('samples/local/profiles').glob('*/profile.json'))
        profile = json.loads(p.read_text())
        sec = next(s for s in profile['sections'] if s['name']=='.rdata')
        raw = (p.parent/sec['file']).read_bytes()
        offset = 0x1b92e90-sec['virtualAddress']
        table = raw[offset:offset+256]
        self.a = bytes((0x48-table[(table[v ^ 0x95]+0x52)&255])&255 for v in range(256))
        self.b = bytes(rol((0x0f-rol(swap(v)^0xf4,4))&255,1) for v in range(256))
        self.c = bytes(table[table[rol(table[(v-0x57)&255],3)]] for v in range(256))

    def decode(self, payload):
        if not payload:
            raise ValueError('empty packet')
        cursor = 1
        def varint(table, bits):
            nonlocal cursor
            value = 0
            for shift in range(0, bits, 7):
                if cursor >= len(payload):
                    raise ValueError('truncated varint')
                byte = table[payload[cursor]]
                cursor += 1
                value |= (byte&127)<<shift
                if byte < 128:
                    return value
            raise ValueError('varint overflow')
        if ((payload[0]>>1)&7) not in (1,2,3,5):
            varint(self.a,32)
        if ((payload[0]>>4)&7) not in (2,3,4,6):
            varint(self.b,16)
        if payload[0]&1:
            size = 0
        else:
            size = varint(self.c,32)
        if size != len(payload)-cursor:
            raise ValueError(f'buffer length mismatch {size} != {len(payload)-cursor}')
        decoded = payload[cursor:].translate(self.c)
        result = bytearray(size)
        # Client consumes bytes alternately into the front and back of the buffer.
        result[:(size+1)//2] = decoded[::2]
        result[(size+1)//2:] = decoded[1::2][::-1]
        return bytes(result)
