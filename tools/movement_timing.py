"""Offline header/timing research. Does not alter production samples.

Selector constants are translated from supported-client deserializer RVA
0x104f430: object +0x10 (u32) branches 0x104f49e..637, +0x14 (u16)
branches 0x104f644..7d3. Names describe storage, not gameplay semantics.
"""
import argparse
import json
import math
import statistics
from collections import defaultdict
from pathlib import Path
from rofllens import ReplayReader
from parser.patch_16_18 import PatchDecoder, CLIENT_VERSION, PROTOCOL_DIGEST, PLAYER_ENTITY_START
from parser.movement import parse_movement_payloads


def route_at(path, speed, elapsed):
    remaining = max(0, elapsed) * speed
    for a, b in zip(path, path[1:]):
        length = math.hypot(b['x']-a['x'], b['y']-a['y'])
        if length and remaining < length:
            f = remaining / length
            return {k: a[k]+f*(b[k]-a[k]) for k in ('x','y')}
        remaining -= length
    return path[-1]


def summarize(values):
    values = sorted(values)
    return {'count': len(values), 'median': statistics.median(values), 'p95': values[int((len(values)-1)*.95)]} if values else {'count': 0}


def inspect(path, decoder):
    tracks = defaultdict(list)
    count = matches = decreases = 0
    previous = None
    offsets = []
    examples = []
    with ReplayReader.open(path) as reader:
        if (reader.header.client_version, reader.header.protocol_digest) != (CLIENT_VERSION, PROTOCOL_DIGEST):
            raise ValueError('Unsupported replay version/digest')
        for block in reader.iter_blocks(streams={'gameChunk'}, opcodes={0x4c}, include_payload=True):
            packet = decoder.decode_movement_packet(block.payload)
            header = {'fieldU32': packet.field_u32, 'fieldU16': packet.record_count}
            raw = packet.buffer
            records = parse_movement_payloads(raw, expected_count=packet.record_count)
            count += 1
            matches += header['fieldU16'] == len(records)
            clock = header['fieldU32']/1000
            decreases += previous is not None and clock < previous
            previous = clock
            offsets.append(block.timestamp-clock)
            for entity, speed, route in records:
                if 0 <= entity-PLAYER_ENTITY_START < 10:
                    sample = {'timestamp': block.timestamp, 'headerClockCandidate': clock, 'speed': speed, 'path': route}
                    tracks[entity].append(sample)
                    if entity == PLAYER_ENTITY_START+8 and 9 <= block.timestamp <= 12:
                        examples.append({**sample, **header})
    errors = {'transport': [], 'headerCandidate': []}
    better = worse = 0
    for samples in tracks.values():
        for a, b in zip(samples, samples[1:]):
            dt = b['timestamp']-a['timestamp']
            dh = b['headerClockCandidate']-a['headerClockCandidate']
            # Identical population, moving routes, frequent updates; no teleports
            # inferred. Large errors remain included rather than cherry-picked.
            if not .03 <= dt <= 1 or not 0 < dh <= 1 or a['speed'] <= 0 or len(a['path']) < 2:
                continue
            pair = []
            for label, elapsed in [('transport', dt), ('headerCandidate', dh)]:
                predicted = route_at(a['path'], a['speed'], elapsed)
                actual = b['path'][0]
                error = math.hypot(predicted['x']-actual['x'], predicted['y']-actual['y'])
                errors[label].append(error)
                pair.append(error)
            better += pair[1] < pair[0]
            worse += pair[1] > pair[0]
    return {'replay': path.name, 'packets': count, 'fieldU16MatchesRecordCount': matches,
            'fieldU32Decreases': decreases, 'transportMinusHeaderSeconds': summarize(offsets),
            'predictionErrorWorldUnits': {k: summarize(v) for k,v in errors.items()},
            'headerBetter': better, 'headerWorse': worse, 'earlyPlayer8Examples': examples}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('replays', nargs='+', type=Path)
    ap.add_argument('--client', type=Path, default=Path(r'C:\Riot Games\League of Legends\Game\League of Legends.exe'))
    ap.add_argument('--output', type=Path, default=Path('samples/local/movement-audit/timing.json'))
    args = ap.parse_args()
    decoder = PatchDecoder(args.client)
    reports = []
    for path in args.replays:
        report = inspect(path, decoder)
        reports.append(report)
        print(json.dumps({k:v for k,v in report.items() if k != 'earlyPlayer8Examples'}), flush=True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(reports, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
