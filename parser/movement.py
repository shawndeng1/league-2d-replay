"""Compact paths after patch-specific buffer decoding.

Layout follows RoflLens's MIT-licensed movement parser. Unlike its 16.14
implementation, 16.18 delta coordinates are signed i8. See the measured
next-origin comparison in docs/rofl-format.md. No future waypoint is presented
as an independently observed timestamped position.
"""
import math
import struct


def parse_movement_payloads(payload: bytes) -> list[tuple[int, float, list[dict]]]:
    cursor = 0

    def read(fmt):
        nonlocal cursor
        size = struct.calcsize(fmt)
        if cursor + size > len(payload):
            raise ValueError('Truncated movement path.')
        values = struct.unpack_from(fmt, payload, cursor)
        cursor += size
        return values

    records = []
    while cursor < len(payload):
        flags, entity, speed = read('<HIf')
        if not math.isfinite(speed) or not 0 <= speed <= 5000:
            raise ValueError('Implausible movement speed.')
        count = (flags & 255) >> 1
        if count == 0:
            raise ValueError('Movement path has no waypoints.')
        if flags & 1:
            read('<B')
        bitmap = read(f'<{(2*(count-1)+7)//8}s')[0]
        previous = [0, 0]
        path = []
        for index in range(count):
            for axis in range(2):
                bit = 2*(index-1)+axis
                delta = index > 0 and (bitmap[bit//8] >> (bit%8)) & 1
                if delta:
                    previous[axis] = (previous[axis] + read('<b')[0] + 32768) % 65536 - 32768
                else:
                    previous[axis] = read('<h')[0]
            path.append({'x': float(previous[0]*2+7358), 'y': float(previous[1]*2+7412)})
        records.append((entity, speed, path))
    return records
