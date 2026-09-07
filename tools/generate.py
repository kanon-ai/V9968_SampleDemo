"""Generate original indexed art and motion parameters, not rendered video frames."""
from pathlib import Path
import math
import struct
import json
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'assets'
FRAMES = 512


def packed(image):
    pixels = list(image.getdata())
    return bytes((pixels[n] << 4) | pixels[n + 1] for n in range(0, len(pixels), 2))


def palette():
    # RGB5. Group zero is reserved for the background.
    groups = [[(0, 0, 1), (1, 1, 4), (2, 3, 8), (4, 7, 13),
               (2, 7, 14), (2, 12, 22), (2, 20, 29), (10, 29, 31),
               (24, 31, 31), (16, 11, 31), (11, 5, 23), (6, 3, 14),
               (7, 4, 17), (16, 8, 25), (25, 19, 31), (31, 31, 31)]]
    for rgb in [(3, 28, 31), (22, 9, 31), (31, 13, 5)]:
        group = [(0, 0, 0)]
        for i in range(1, 16):
            f = i / 15
            white = max(0, (f - .7) / .3)
            group.append(tuple(min(31, round(c * f + (31 - c) * white)) for c in rgb))
        groups.append(group)
    return groups


def background():
    im = Image.new('P', (256, 256), 1)
    d = ImageDraw.Draw(im)
    for y in range(0, 256, 16):
        for x in range(0, 256, 16):
            if ((x // 16) + (y // 16)) & 1:
                d.rectangle((x, y, x + 15, y + 15), fill=2)
    # Angular concentric architecture, progressively finer toward the centre.
    for idx, r in reversed(list(enumerate([7, 13, 22, 34, 50, 70, 94, 124, 159, 198]))):
        angle = .20 * math.sin(idx * .7)
        vertices = [(128 + math.cos(angle + k * math.tau / 8) * r,
                     128 + math.sin(angle + k * math.tau / 8) * r) for k in range(8)]
        d.polygon(vertices, fill=1 + (idx & 1))
        d.line(vertices + vertices[:1], fill=4 + idx % 8, width=3 if r > 70 else 2)
        for k in range(0, 8, 2):
            a = vertices[k]
            b = vertices[(k + 1) % 8]
            d.line((a, (a[0] * .55 + b[0] * .45, a[1] * .55 + b[1] * .45)), fill=15, width=1)
    # Spokes anchor the rotation; broken luminous marks suggest forward flow.
    for k in range(8):
        a = k * math.tau / 8
        d.line((128 + math.cos(a) * 16, 128 + math.sin(a) * 16,
                128 + math.cos(a) * 180, 128 + math.sin(a) * 180), fill=3)
        for r in [25, 44, 68, 98, 133, 176]:
            x, y = 128 + math.cos(a) * r, 128 + math.sin(a) * r
            d.rectangle((x - 1, y - 1, x + 1, y + 1), fill=14)
    d.ellipse((123, 123, 133, 133), fill=8)
    d.ellipse((126, 126, 130, 130), fill=15)
    return im


def sprites():
    im = Image.new('P', (256, 256), 0)
    d = ImageDraw.Draw(im)
    for n in range(3):
        x = n * 16
        d.polygon([(x+8, 0), (x+15, 11), (x+12, 24), (x+7, 31), (x, 20), (x+2, 8)], fill=5)
        d.polygon([(x+8, 0), (x+10, 13), (x+7, 31), (x+2, 8)], fill=9+n)
        d.polygon([(x+8, 0), (x+15, 11), (x+10, 13)], fill=15)
        d.polygon([(x+10, 13), (x+15, 11), (x+12, 24), (x+7, 31)], fill=3+n)
        d.line([(x+8, 1), (x+10, 13), (x+7, 29)], fill=14)
        d.line([(x+2, 8), (x+10, 13), (x+15, 11)], fill=12)
    return im


def frame_records():
    records = bytearray()
    for frame in range(FRAMES):
        t = frame / FRAMES
        a = math.tau * (2*t + .17*math.sin(math.tau*t))
        zoom = 2.15 + .49*math.sin(math.tau*t + .45) + .10*math.sin(math.tau*3*t)
        vx, vy = round(math.cos(a)*256/zoom), round(math.sin(a)*256/zoom)
        cx = 128 + 8*math.sin(math.tau*t)
        cy = 1152 + 6*math.cos(math.tau*2*t)
        sx = round(cx - (128*vx - 106*vy)/256)
        sy = round(cy - (128*vy + 106*vx)/256)
        records.extend(struct.pack('<hhhh', sx, sy, vx, vy))
        objects = []
        for n in range(6):
            orbit = math.tau * (t + n/6)
            depth = (math.sin(orbit) + 1)/2
            w = round(11 + 58*depth*depth)
            h = round(w*1.55)
            x = round(128 + math.cos(orbit)*(65 + 38*depth) - w/2)
            y = round(104 + math.sin(orbit)*43 - h/2)
            # Mode3 Y word: SZ=1 => source 16x32. X/Y are signed 10-bit.
            attr = struct.pack('<HBBHBB', (y & 1023) | 0x4000, h,
                               1+n%3, x & 1023, w, n%3)
            objects.append((depth, attr))
        for _, attr in sorted(objects, reverse=True, key=lambda item: item[0]):
            records.extend(attr)
        records.extend(bytes([frame % 32, (frame // 16) % 16]) + bytes(6))
    assert len(records) == FRAMES * 64
    return records


def generate():
    ASSETS.mkdir(parents=True, exist_ok=True)
    bg, sp = background(), sprites()
    (ASSETS/'background.bin').write_bytes(packed(bg))
    (ASSETS/'sprites.bin').write_bytes(packed(sp))
    (ASSETS/'motion.bin').write_bytes(frame_records())
    groups = palette()
    rows = ['; Generated RGB5 palette.']
    rows += ['initial_palette:', '    db '+','.join(str(c) for group in groups for rgb in group for c in rgb)]
    rows += ['pulse_palettes:']
    for p in range(32):
        rgb = []
        for n in range(8):
            f = .5 + .5*math.cos(math.tau*(n/8-p/32))
            rgb.extend((round(2+18*f*f), round(5+24*f), round(13+18*f)))
        rows.append('    db '+','.join(map(str, rgb)))
    rows += ['psg_notes:', '    dw 428,339,285,214,285,339,381,285,320,254,214,160,214,254,285,339']
    (ASSETS/'palettes.inc').write_text('\n'.join(rows)+'\n', encoding='ascii')
    # Static art sheet only: explicitly not an emulator result.
    bg.putpalette([c*255//31 for rgb in groups[0] for c in rgb] + [0]*(768-48))
    bg.resize((512,512), Image.Resampling.NEAREST).save(ASSETS/'background-art.png')
    sp.putpalette([c*255//31 for rgb in groups[1] for c in rgb] + [0]*(768-48))
    sp.crop((0,0,48,32)).resize((384,256), Image.Resampling.NEAREST).save(ASSETS/'crystal-art.png')
    (ASSETS/'layout.json').write_text(json.dumps({'frames':FRAMES,'frame_record_bytes':64,
        'background_vram':'0x20000-0x27FFF','sprite_patterns_vram':'0x28000-0x2FFFF',
        'attributes_vram':['0x10000','0x10200'],'display_pages':['0x00000','0x08000'],
        'max_sprites_per_scanline':6},indent=2)+'\n')


if __name__ == '__main__':
    generate()
