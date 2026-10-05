#!/usr/bin/env python3
"""
steg_png.py - hide / extract a short message in the pixels of a PNG.
Python standard library only (zlib, struct).

ALGORITHM (keep this: it is enough to reimplement everything):
1. Data = 2-byte length (big-endian) + the message in ASCII.
2. Only the R, G, B colour bytes are used (alpha ignored),
   numbered row by row from the top-left pixel.
   step = (width x height x 3) // 4096
3. Bit no. k of the data (byte by byte, most significant bit first)
   replaces the least significant bit of the colour byte of rank k x step.
Supported PNG: 8 bits per channel, RGB or RGBA, non-interlaced.
Message: 510 ASCII characters maximum.
"""
import sys
import zlib
import struct

SIG = b"\x89PNG\r\n\x1a\n"
BITS_MAX = 4096  # 512 bytes, length included


def paeth(a, b, c):
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    return b if pb <= pc else c


def unfilter(raw, width, height, bpp):
    stride = width * bpp
    pixels, prev, i = bytearray(), bytearray(stride), 0
    for _ in range(height):
        f = raw[i]
        i += 1
        line = bytearray(raw[i:i + stride])
        i += stride
        for x in range(stride):
            a = line[x - bpp] if x >= bpp else 0
            b = prev[x]
            c = prev[x - bpp] if x >= bpp else 0
            if f == 1:
                line[x] = (line[x] + a) & 0xFF
            elif f == 2:
                line[x] = (line[x] + b) & 0xFF
            elif f == 3:
                line[x] = (line[x] + ((a + b) >> 1)) & 0xFF
            elif f == 4:
                line[x] = (line[x] + paeth(a, b, c)) & 0xFF
            elif f != 0:
                sys.exit("Error: unknown PNG filter.")
        pixels += line
        prev = line
    return pixels


def read_png(path):
    with open(path, "rb") as f:
        data = f.read()
    if data[:8] != SIG:
        sys.exit("Error: this file is not a PNG.")
    chunks, pos = [], 8
    while pos < len(data):
        (length,) = struct.unpack(">I", data[pos:pos + 4])
        ctype = data[pos + 4:pos + 8]
        chunks.append((ctype, data[pos + 8:pos + 8 + length]))
        pos += 12 + length
    width, height, depth, colour, _, _, interlace = struct.unpack(
        ">IIBBBBB", chunks[0][1])
    if depth != 8 or colour not in (2, 6) or interlace != 0:
        sys.exit("Error: unsupported PNG (8-bit, RGB/RGBA, non-interlaced only).")
    bpp = 3 if colour == 2 else 4
    raw = zlib.decompress(b"".join(c for t, c in chunks if t == b"IDAT"))
    return chunks, unfilter(raw, width, height, bpp), width, height, bpp


def make_chunk(ctype, content):
    crc = zlib.crc32(ctype + content) & 0xFFFFFFFF
    return struct.pack(">I", len(content)) + ctype + content + struct.pack(">I", crc)


def write_png(path, chunks, pixels, width, height, bpp):
    stride = width * bpp
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter 0 on every line
        raw += pixels[y * stride:(y + 1) * stride]
    idat = zlib.compress(bytes(raw), 9)
    out, idat_written = bytearray(SIG), False
    for ctype, content in chunks:
        if ctype == b"IDAT":
            if not idat_written:
                out += make_chunk(b"IDAT", idat)
                idat_written = True
        else:
            out += make_chunk(ctype, content)
    with open(path, "wb") as f:
        f.write(out)


def positions(width, height, bpp):
    step = (width * height * 3) // BITS_MAX
    if step < 1:
        sys.exit("Error: image too small.")
    for k in range(BITS_MAX):
        j = k * step  # rank among R, G, B bytes
        yield j if bpp == 3 else (j // 3) * 4 + j % 3


def hide(src, dst):
    chunks, pixels, width, height, bpp = read_png(src)
    message = input("Message to hide: ").strip()
    try:
        data = message.encode("ascii")
    except UnicodeEncodeError:
        sys.exit("Error: ASCII characters only.")
    data = struct.pack(">H", len(data)) + data
    if len(data) * 8 > BITS_MAX:
        sys.exit("Error: message too long (510 characters max).")
    pos = positions(width, height, bpp)
    for byte in data:
        for k in range(7, -1, -1):
            i = next(pos)
            pixels[i] = (pixels[i] & 0xFE) | ((byte >> k) & 1)
    write_png(dst, chunks, pixels, width, height, bpp)
    print(f"OK: {len(message)} characters hidden in {dst}")


def extract(path):
    _, pixels, width, height, bpp = read_png(path)
    pos = positions(width, height, bpp)

    def read_bytes(n):
        res = bytearray()
        for _ in range(n):
            v = 0
            for _ in range(8):
                v = (v << 1) | (pixels[next(pos)] & 1)
            res.append(v)
        return bytes(res)

    (n,) = struct.unpack(">H", read_bytes(2))
    if (n + 2) * 8 > BITS_MAX:
        sys.exit("No valid message found.")
    try:
        return read_bytes(n).decode("ascii")
    except UnicodeDecodeError:
        sys.exit("No valid message found.")


def main():
    if len(sys.argv) == 4 and sys.argv[1] == "hide":
        hide(sys.argv[2], sys.argv[3])
    elif len(sys.argv) == 3 and sys.argv[1] == "extract":
        print(extract(sys.argv[2]))
    else:
        sys.exit("Usage:\n"
                 "  python3 steg_png.py hide <input.png> <output.png>\n"
                 "  python3 steg_png.py extract <image.png>")


if __name__ == "__main__":
    main()
