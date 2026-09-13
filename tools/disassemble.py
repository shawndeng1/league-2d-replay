"""Print local, offline function disassembly for a supplied RVA."""
import argparse
import json
from pathlib import Path
import capstone


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('rva', type=lambda s: int(s, 0))
    ap.add_argument('--size', type=lambda s: int(s, 0), default=0x500)
    args = ap.parse_args()
    profile_path = next(Path('samples/local/profiles').glob('*/profile.json'))
    profile = json.loads(profile_path.read_text())
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    for sec in profile['sections']:
        start = sec['virtualAddress']
        if start <= args.rva < start + sec['rawSize']:
            data = (profile_path.parent/sec['file']).read_bytes()
            for ins in md.disasm(data[args.rva-start:args.rva-start+args.size], args.rva):
                print(f'{ins.address:x}: {ins.mnemonic} {ins.op_str}')
            break


if __name__ == '__main__':
    main()
