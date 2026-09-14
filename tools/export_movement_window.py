"""Export bounded raw packet evidence; unknown packets receive no gameplay labels."""
import argparse
import hashlib
import json
from pathlib import Path
from collections import Counter
from rofllens import ReplayReader
from parser.patch_16_18 import PatchDecoder, CLIENT_VERSION, PROTOCOL_DIGEST, MOVEMENT_OPCODE, PLAYER_ENTITY_START
from parser.movement import parse_movement_payloads


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('replay', type=Path)
    ap.add_argument('--start', type=float, required=True)
    ap.add_argument('--end', type=float, required=True)
    ap.add_argument('--player', type=int, required=True)
    ap.add_argument('--client', type=Path, default=Path(r'C:\Riot Games\League of Legends\Game\League of Legends.exe'))
    ap.add_argument('--output', type=Path, default=Path('samples/local/movement-window.json'))
    args = ap.parse_args()
    if not 0 <= args.player < 10 or not 0 <= args.start < args.end or args.end-args.start > 30:
        ap.error('Require player 0..9 and a nonnegative window of at most 30 seconds.')
    decoder = PatchDecoder(args.client)
    records, movements, counts = [], [], Counter()
    entity = PLAYER_ENTITY_START + args.player
    with ReplayReader.open(args.replay) as reader:
        if (reader.header.client_version, reader.header.protocol_digest) != (CLIENT_VERSION, PROTOCOL_DIGEST):
            raise ValueError('Unsupported replay version/digest')
        for block in reader.iter_blocks(streams={'gameChunk'}, include_payload=True):
            if not args.start <= block.timestamp <= args.end:
                continue
            opcode = f'0x{block.packet_id:04x}'
            counts[opcode] += 1
            record = {'timestamp': block.timestamp, 'opcode': opcode, 'param': hex(block.param),
                      'size': block.payload_length, 'payloadHex': block.payload.hex()}
            records.append(record)
            if block.packet_id == MOVEMENT_OPCODE:
                raw = decoder.decode_movement_buffer(block.payload)
                for net_id, speed, path in parse_movement_payloads(raw):
                    if net_id == entity:
                        movements.append({'timestamp': round(block.timestamp, 6), 'entity': hex(net_id),
                                          'speed': round(speed, 4), 'path': path, 'packetIndex': len(records)-1})
    with args.replay.open('rb') as handle:
        digest = hashlib.file_digest(handle, 'sha256').hexdigest()
    result = {'replayId': digest, 'patch': CLIENT_VERSION, 'playerId': args.player,
              'window': [args.start, args.end], 'opcodeHistogram': dict(counts.most_common()),
              'movement': movements, 'packets': records,
              'note': 'Only 0x004c routes are decoded here. Other packet semantics are UNKNOWN; param is not asserted to be a champion entity ID.'}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'packets': len(records), 'movementRecords': len(movements), 'output': str(args.output)}))


if __name__ == '__main__':
    main()
