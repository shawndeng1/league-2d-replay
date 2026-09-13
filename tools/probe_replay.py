"""Transport-only evidence. Never labels raw payload bytes as positions."""
import argparse
import json
from collections import Counter, defaultdict
from pathlib import Path
from rofllens import ReplayReader


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('replay')
    ap.add_argument('--output', default='samples/local/probe.json')
    args = ap.parse_args()
    counts, sizes, params = Counter(), defaultdict(Counter), defaultdict(Counter)
    examples = defaultdict(list)
    with ReplayReader.open(args.replay) as replay:
        summary = replay.summary().as_dict()
        players = [{k: v for k, v in p.items() if k in ('SKIN', 'TEAM', 'TEAM_POSITION', 'CHAMPION_ID', 'PLAYER_ID', 'ID')} for p in replay.metadata.participants]
        keys = list(replay.metadata.participants[0])
        for block in replay.iter_blocks(streams={'gameChunk'}, include_payload=True):
            op = f'0x{block.packet_id:04x}'
            counts[op] += 1
            sizes[op][block.payload_length] += 1
            params[op][hex(block.param)] += 1
            if len(examples[op]) < 4:
                examples[op].append({'timestamp': block.timestamp, 'param': hex(block.param), 'payloadHex': block.payload.hex()})
        result = {'summary': summary, 'players': players, 'participantFields': keys,
                  'gameChunkBlocks': sum(counts.values()), 'opcodes': [
                      {'opcode': op, 'count': n, 'sizes': sizes[op].most_common(10), 'params': params[op].most_common(15), 'examples': examples[op]}
                      for op, n in counts.most_common()]}
    out = Path(args.output)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({'players': players, 'opcode022c': next((p for p in result['opcodes'] if p['opcode']=='0x022c'), None), 'top': counts.most_common(20)}, indent=2))


if __name__ == '__main__':
    main()
