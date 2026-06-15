#!/usr/bin/env python3
"""生成 PWA 图标和 favicon"""

import struct
import zlib
import os

def create_png(width, height, color):
    """创建纯色 PNG"""
    def make_chunk(chunk_type, data):
        chunk = chunk_type + data
        crc = struct.pack('>I', zlib.crc32(chunk) & 0xFFFFFFFF)
        return struct.pack('>I', len(data)) + chunk + crc

    # 创建带渐变效果的圆形图标
    raw_data = b''
    cx, cy = width / 2, height / 2
    r = min(width, height) * 0.4

    for y in range(height):
        raw_data += b'\x00'  # filter none
        for x in range(width):
            dx, dy = x - cx, y - cy
            dist = (dx*dx + dy*dy) ** 0.5

            if dist <= r:
                # 圆形内部：渐变蓝色
                t = dist / r
                r_val = int(79 + (167 - 79) * t)
                g_val = int(110 + (139 - 110) * t)
                b_val = int(247 + (250 - 247) * t)
                raw_data += bytes([r_val, g_val, b_val, 255])
            else:
                # 背景透明
                raw_data += b'\x00\x00\x00\x00'

    ihdr = make_chunk(b'IHDR', struct.pack('>IIBBBBB', width, height, 8, 6, 0, 0, 0))
    idat = make_chunk(b'IDAT', zlib.compress(raw_data))
    iend = make_chunk(b'IEND', b'')

    return b'\x89PNG\r\n\x1a\n' + ihdr + idat + iend

def main():
    base = os.path.dirname(os.path.abspath(__file__))
    icons_dir = os.path.join(base, 'static', 'icons')
    os.makedirs(icons_dir, exist_ok=True)

    sizes = [72, 96, 128, 144, 152, 192, 384, 512]
    for size in sizes:
        png_data = create_png(size, size, (79, 110, 247))
        path = os.path.join(icons_dir, f'icon-{size}.png')
        with open(path, 'wb') as f:
            f.write(png_data)
        print(f'Created {path} ({size}x{size})')

if __name__ == '__main__':
    main()
