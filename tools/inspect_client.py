"""Offline static research; no game process is started or modified."""
import argparse
import json
import re
import struct
from pathlib import Path

import capstone
import pefile


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('exe')
    ap.add_argument('--opcode', type=lambda x: int(x, 0))
    args = ap.parse_args()
    pe = pefile.PE(args.exe)
    image = pe.get_memory_mapped_image()
    base = pe.OPTIONAL_HEADER.ImageBase
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_64)
    md.detail = True
    rows = []
    # MSVC packet constructors initialize a u16 opcode at this+8.
    for match in re.finditer(rb'\x66\xc7\x41\x08(..)', image, re.S):
        opcode = struct.unpack('<H', match[1])[0]
        if opcode > 0x800 or (args.opcode is not None and opcode != args.opcode):
            continue
        row = {'opcode': hex(opcode), 'rva': hex(match.start()), 'instructions': []}
        for ins in md.disasm(image[match.start():match.start()+180], base+match.start()):
            row['instructions'].append(f'{ins.address-base:x}: {ins.mnemonic} {ins.op_str}')
            if ins.mnemonic == 'lea' and ins.op_str.startswith('rax, [rip'):
                addr = ins.address + ins.size + ins.operands[1].mem.disp - base
                if 0 <= addr < len(image)-48:
                    methods = struct.unpack_from('<6Q', image, addr)
                    row['vtable'] = hex(addr)
                    row['methods'] = [hex(x-base) for x in methods]
            if ins.mnemonic == 'ret':
                break
        rows.append(row)
    print(json.dumps(rows, indent=2))


if __name__ == '__main__':
    main()
