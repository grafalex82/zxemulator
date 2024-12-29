import argparse

def get_scan_line(font, char, line, offset):
    index = (char << 3) + line + offset
    byte = font[index]
    line = ""
    for j in range(8):
        ch = "@" if byte & 0x01 else " "
        line = ch + line
        byte >>= 1

    return line

def dump_font(filename, offset):
    with open(filename, "rb") as f:
        data = f.read()

    size = (len(data) - offset) // 8
    for ch in range(size):
        print()
        print(f"Char: {ch:02x}")

        for i in range(8):
            line = get_scan_line(data, ch, i, offset)
            print(line)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
                    prog='dump_font',
                    description='Utility to dump 8x8 font files')
    parser.add_argument('fontfile')
    parser.register('type', 'hex', lambda s: int(s, 16))
    parser.add_argument('--offset', type='hex', default="0")
    args = parser.parse_args()

    dump_font(args.fontfile, args.offset)
