"""Exact-build movement buffer decoder. See docs/rofl-format.md for evidence.

Only packet 0x004c is supported. Header business fields are deliberately unnamed.
This translates the buffer transport operations at client RVAs 0x104f430 and
0xfc00f0. Lookup data is read from the user's hash-checked client, not shipped.
"""
import hashlib
from pathlib import Path
import pefile

CLIENT_VERSION = '16.18.817.5716'
PROTOCOL_DIGEST = 'f6a10af08504a7ee'
CLIENT_SHA256 = '6c3a62afa3d62b66db8a777140c4338979bdb56b87242446570fe6b118f40095'
PLAYER_ENTITY_START = 0x400000AE
MOVEMENT_OPCODE = 0x004C


def rotate_left(v: int, n: int) -> int:
    return ((v << n) | (v >> (8-n))) & 255


def swap_bits(v: int) -> int:
    return ((v & 0x55) << 1) | ((v >> 1) & 0x55)


class PatchDecoder:
    def __init__(self, client_exe: Path):
        with client_exe.open('rb') as handle:
            digest = hashlib.file_digest(handle, 'sha256').hexdigest()
        if digest != CLIENT_SHA256:
            raise ValueError(f'Client executable does not match supported build {CLIENT_VERSION}.')
        pe = pefile.PE(str(client_exe), fast_load=True)
        try:
            table = pe.get_data(0x1B92E90, 256)
        finally:
            pe.close()
        if len(table) != 256:
            raise ValueError('Client lookup table is truncated.')
        self.field_a = bytes((0x48-table[(table[v ^ 0x95]+0x52)&255])&255 for v in range(256))
        self.field_b = bytes(rotate_left((0x0f-rotate_left(swap_bits(v)^0xf4,4))&255,1) for v in range(256))
        self.buffer = bytes(table[table[rotate_left(table[(v-0x57)&255],3)]] for v in range(256))

    def decode_movement_buffer(self, payload: bytes) -> bytes:
        if not payload:
            raise ValueError('Empty movement packet.')
        cursor = 1

        def varint(table: bytes, bits: int) -> int:
            nonlocal cursor
            value = 0
            for shift in range(0, bits, 7):
                if cursor >= len(payload):
                    raise ValueError('Truncated movement varint.')
                byte = table[payload[cursor]]
                cursor += 1
                value |= (byte & 127) << shift
                if byte < 128:
                    if value >= 1 << bits:
                        raise ValueError('Movement varint overflow.')
                    return value
            raise ValueError('Movement varint overflow.')

        # Selector codes choose either an inline constant or an encoded varint.
        if ((payload[0] >> 1) & 7) not in (1, 2, 3, 5):
            varint(self.field_a, 32)
        if ((payload[0] >> 4) & 7) not in (2, 3, 4, 6):
            varint(self.field_b, 16)
        size = 0 if payload[0] & 1 else varint(self.buffer, 32)
        if size != len(payload)-cursor:
            raise ValueError('Movement buffer length disagrees with packet boundary.')
        decoded = payload[cursor:].translate(self.buffer)
        result = bytearray(size)
        # Client fills alternating front/back slots, not sequential slots.
        result[:(size+1)//2] = decoded[::2]
        result[(size+1)//2:] = decoded[1::2][::-1]
        return bytes(result)
