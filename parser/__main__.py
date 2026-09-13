import argparse
import json
import logging
import os
from pathlib import Path
from .replay_parser import ReplayParser, ParseError

def main():
    ap = argparse.ArgumentParser(description='Decode a real ROFL into normalized champion samples.')
    ap.add_argument('replay', type=Path)
    ap.add_argument('--inspect', action='store_true', help='Print container metadata without requiring a client executable.')
    ap.add_argument('--client-exe', default=os.environ.get('LEAGUE_CLIENT_EXE', r'C:\Riot Games\League of Legends\Game\League of Legends.exe'))
    ap.add_argument('--output', type=Path, default=Path('samples/local/replay.json'))
    args = ap.parse_args()
    logging.basicConfig(level=logging.INFO)
    parser = ReplayParser(args.client_exe)
    try:
        if args.inspect:
            print(json.dumps(parser.inspect(args.replay), indent=2))
        else:
            result = parser.parse(args.replay)
            args.output.parent.mkdir(parents=True, exist_ok=True)
            temp = args.output.with_suffix('.part')
            temp.write_text(json.dumps(result, separators=(',', ':')), encoding='utf-8')
            temp.replace(args.output)
            print(f"Saved {result['diagnostics']['sampleCount']} real samples to {args.output}")
    except ParseError as exc:
        ap.exit(1, f'{exc.code}: {exc}\n')

if __name__ == '__main__':
    main()
