"""Original limited-palette cosmic-cat supporting sprites.

``make_props()`` returns a dict keyed by prop name. Each value contains an RGBA
Pillow ``image``, its opaque RGB ``palette`` (at most 15 entries), a palette
``group``, integer ``size`` and ``anchor``, and a suggested hardware transparency
percentage. Alpha is binary: blending is left to the target VDP. No external
artwork, fonts, random state, or build/runtime modules are required.

Run this file to write only ``work/props-preview.png`` for visual review.
"""
from pathlib import Path
import math
from PIL import Image, ImageDraw, ImageFont


FISH = (
    (66, 43, 58), (109, 57, 66), (158, 74, 74), (200, 96, 84),
    (229, 127, 94), (246, 161, 112), (255, 191, 134), (255, 218, 164),
    (255, 245, 208), (43, 80, 88), (59, 124, 127), (93, 166, 157),
    (151, 206, 181), (242, 150, 157), (255, 196, 189),
)
METAL = (
    (12, 19, 34), (30, 44, 61), (53, 71, 87), (83, 105, 118),
    (132, 154, 160), (184, 204, 196), (242, 252, 218), (18, 71, 84),
    (30, 118, 127), (73, 191, 184), (146, 232, 212), (105, 37, 59),
    (185, 52, 73), (245, 108, 115), (255, 196, 146),
)
NEON = (
    (18, 24, 63), (37, 46, 111), (63, 66, 186), (84, 119, 238),
    (87, 208, 250), (149, 251, 244), (248, 255, 225), (116, 57, 178),
    (193, 65, 199), (252, 90, 180), (255, 151, 143), (255, 217, 114),
    (165, 232, 117), (72, 192, 153), (112, 145, 184),
)
SHADOW = ((11, 14, 28), (21, 25, 46), (35, 37, 64))


def _blank(size):
    return Image.new("RGBA", size, (0, 0, 0, 0))


def _color(palette, index):
    return (*palette[index], 255)


def _ellipsoid(image, box, palette, ramp, gloss=0.0):
    """Pixel-lit volume with a dark rim, warm upper highlight and cool underside."""
    x0, y0, x1, y1 = box
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
    rx, ry = (x1 - x0 + 1) / 2, (y1 - y0 + 1) / 2
    pixels = image.load()
    for y in range(max(0, y0), min(image.height, y1 + 1)):
        for x in range(max(0, x0), min(image.width, x1 + 1)):
            nx, ny = (x - cx) / rx, (y - cy) / ry
            q = nx * nx + ny * ny
            if q > 1:
                continue
            nz = math.sqrt(1 - q)
            light = max(0.0, -.39 * nx - .48 * ny + .76 * nz)
            shine = math.exp(-((nx + .28) ** 2 + (ny + .42) ** 2) * 65) * gloss
            value = min(.999, .08 + .82 * light + shine)
            if q > .94:
                value *= .55
            pixels[x, y] = _color(palette, ramp[int(value * len(ramp))])


def _ring(draw, center, radii, angle, palette, dark, middle, light, width=3):
    """A tilted metallic ring rendered with integer points, without filtering."""
    cx, cy = center
    rx, ry = radii
    co, si = math.cos(angle), math.sin(angle)
    points = []
    for step in range(97):
        t = step * math.tau / 96
        x, y = rx * math.cos(t), ry * math.sin(t)
        points.append((round(cx + x * co - y * si), round(cy + x * si + y * co)))
    draw.line(points, fill=_color(palette, dark), width=width + 2)
    draw.line(points, fill=_color(palette, middle), width=width)
    draw.line(points[45:86], fill=_color(palette, light), width=1)


def _tuna():
    im = _blank((32, 64))
    d = ImageDraw.Draw(im)
    p = FISH
    # Soft fan, stubby fins and a tiny sleepy bubble; no pointed alien crest.
    for box in ((9, 13, 16, 24), (13, 11, 20, 24), (18, 14, 24, 25)):
        d.ellipse(box, fill=_color(p, 10))
    d.arc((10, 13, 23, 27), 180, 345, fill=_color(p, 12))
    d.line((15, 14, 16, 22), fill=_color(p, 11))
    d.ellipse((25, 4, 30, 9), outline=_color(p, 12))
    d.point((26, 5), fill=_color(p, 8))
    d.point((24, 12), fill=_color(p, 11))
    _ellipsoid(im, (0, 32, 9, 42), p, (9, 10, 11, 12), .10)
    _ellipsoid(im, (23, 33, 31, 43), p, (9, 10, 11, 12), .10)
    _ellipsoid(im, (8, 46, 16, 55), p, (9, 10, 11, 12), .05)
    _ellipsoid(im, (17, 46, 24, 55), p, (9, 10, 11, 12), .05)
    # A plump warm body with an ivory tummy and a glazed ceramic highlight.
    _ellipsoid(im, (3, 18, 29, 50), p, (1, 2, 3, 4, 5, 6, 7, 8), .12)
    _ellipsoid(im, (9, 33, 24, 47), p, (4, 5, 6, 7, 8), .06)
    d = ImageDraw.Draw(im)
    d.arc((7, 20, 25, 43), 207, 276, fill=_color(p, 8))
    d.arc((6, 30, 12, 43), 112, 243, fill=_color(p, 3))
    d.arc((22, 30, 28, 43), 300, 65, fill=_color(p, 3))
    # Small drooping lids leave the expression friendly and thoroughly unbothered.
    d.line([(8, 30), (10, 31), (12, 30)], fill=_color(p, 0))
    d.line([(20, 30), (22, 31), (24, 30)], fill=_color(p, 0))
    d.line((8, 28, 11, 28), fill=_color(p, 6))
    d.line((21, 28, 23, 28), fill=_color(p, 6))
    d.ellipse((6, 34, 11, 37), fill=_color(p, 13))
    d.ellipse((21, 34, 26, 37), fill=_color(p, 13))
    d.point((7, 34), fill=_color(p, 14))
    d.point((22, 34), fill=_color(p, 14))
    # A tiny pursed kiss, not an open dark mouth.
    d.line([(15, 36), (17, 37), (15, 38)], fill=_color(p, 2))
    d.point((16, 36), fill=_color(p, 13))
    d.point((16, 38), fill=_color(p, 14))
    return im


def _saucer_can():
    im = _blank((32, 64))
    d = ImageDraw.Draw(im)
    p = METAL
    # Antennae/pull tab, then the far half of a metal flying-saucer ring.
    d.line((15, 8, 15, 19), fill=_color(p, 3), width=2)
    d.ellipse((10, 4, 21, 15), fill=_color(p, 1), outline=_color(p, 5))
    d.ellipse((13, 7, 18, 11), fill=(0, 0, 0, 0))
    d.line((12, 5, 17, 4), fill=_color(p, 6))
    _ring(d, (15.5, 34), (14.5, 8), -.16, p, 0, 3, 6, 3)
    # Engine bells and little pale thrusters are part of the can, not a backdrop.
    for cx in (10, 22):
        d.polygon([(cx - 3, 45), (cx + 3, 45), (cx + 2, 51), (cx - 2, 51)], fill=_color(p, 1))
        d.line((cx - 2, 49, cx + 2, 49), fill=_color(p, 8))
        d.polygon([(cx - 1, 51), (cx + 1, 51), (cx + 2, 56), (cx, 63), (cx - 2, 56)], fill=_color(p, 8))
        d.polygon([(cx, 51), (cx + 1, 55), (cx, 59), (cx - 1, 55)], fill=_color(p, 10))
        d.line((cx, 52, cx, 55), fill=_color(p, 6))
    # The cylindrical side has discrete metal bands, not a flat rectangle.
    d.ellipse((5, 37, 27, 49), fill=_color(p, 1), outline=_color(p, 3))
    side = [1, 2, 3, 4, 5, 6, 5, 4, 3, 3, 2, 2, 3, 4, 4, 3, 2, 2, 1, 1, 2]
    for x, tone in enumerate(side, 6):
        d.line((x, 23, x, 43), fill=_color(p, tone))
    # Red seam, rich teal label and an original, unmistakable white fish mark.
    d.rectangle((7, 27, 25, 42), fill=_color(p, 7))
    d.rectangle((9, 28, 24, 41), fill=_color(p, 8))
    d.line((9, 29, 9, 39), fill=_color(p, 9))
    d.line((23, 28, 24, 41), fill=_color(p, 7))
    d.line((7, 28, 7, 41), fill=_color(p, 12))
    d.line((8, 29, 8, 39), fill=_color(p, 13))
    d.polygon([(11, 33), (13, 35), (11, 38), (15, 36), (17, 38),
               (22, 36), (23, 34), (20, 32), (17, 32), (15, 34)], fill=_color(p, 6))
    d.point((21, 34), fill=_color(p, 0))
    d.line((16, 36, 20, 37), fill=_color(p, 5))
    d.line((12, 40, 19, 40), fill=_color(p, 10))
    # The label itself looks politely bored; the fish mark becomes a moustache.
    d.line((12, 29, 14, 29), fill=_color(p, 0))
    d.line((19, 29, 21, 29), fill=_color(p, 0))
    d.point((10, 32), fill=_color(p, 13))
    d.point((24, 32), fill=_color(p, 13))
    # Raised lid, concentric rolled lip, a scored opening and tiny metal glints.
    _ellipsoid(im, (4, 16, 27, 27), p, (1, 2, 3, 4, 5, 6), .20)
    d = ImageDraw.Draw(im)
    d.ellipse((6, 17, 25, 25), outline=_color(p, 1))
    d.arc((7, 18, 24, 25), 170, 335, fill=_color(p, 6))
    d.arc((10, 19, 22, 24), 170, 340, fill=_color(p, 3))
    d.line((12, 20, 17, 20), fill=_color(p, 6))
    d.ellipse((13, 20, 19, 23), fill=_color(p, 2), outline=_color(p, 4))
    d.line((15, 21, 17, 21), fill=_color(p, 0))
    d.arc((5, 37, 27, 49), 5, 165, fill=_color(p, 5))
    d.arc((6, 38, 26, 47), 10, 164, fill=_color(p, 2))
    # The ring's near arc passes in front of the tin.
    d.line([(0, 36), (4, 40), (10, 42), (17, 42), (24, 39), (31, 34)], fill=_color(p, 0), width=3)
    d.line([(1, 36), (5, 39), (11, 41), (17, 41), (24, 38), (30, 34)], fill=_color(p, 4))
    d.line([(2, 36), (6, 38), (11, 39)], fill=_color(p, 6))
    for x, y in ((3, 37), (16, 41), (28, 36)):
        d.point((x, y), fill=_color(p, 13))
    return im


def _boss_spacefish():
    im = _blank((64, 128))
    d = ImageDraw.Draw(im)
    p = FISH
    # A crooked halo is all the grandeur this overinflated sleepy fish needs.
    _ring(d, (34, 23), (24, 9), -.24, p, 2, 6, 8, 3)
    d.ellipse((52, 7, 58, 13), outline=_color(p, 12))
    d.point((53, 8), fill=_color(p, 8))
    d.ellipse((58, 20, 61, 23), outline=_color(p, 11))
    # A round scalloped dorsal fan and miniature floppy flippers.
    for box in ((21, 27, 32, 47), (28, 24, 40, 45), (37, 29, 47, 48)):
        _ellipsoid(im, box, p, (9, 10, 11, 12), .06)
    _ellipsoid(im, (0, 62, 16, 83), p, (9, 10, 11, 12), .05)
    _ellipsoid(im, (48, 65, 63, 85), p, (9, 10, 11, 12), .05)
    _ellipsoid(im, (17, 94, 31, 110), p, (9, 10, 11, 12), .06)
    _ellipsoid(im, (33, 96, 47, 111), p, (9, 10, 11, 12), .06)
    # Oversized round belly with warm coral shadows, never a black facial cavity.
    _ellipsoid(im, (4, 36, 59, 102), p, (1, 2, 3, 4, 5, 6, 7, 8), .12)
    _ellipsoid(im, (13, 68, 51, 96), p, (4, 5, 6, 7, 8), .08)
    d = ImageDraw.Draw(im)
    d.arc((10, 39, 51, 86), 205, 275, fill=_color(p, 8), width=2)
    d.arc((9, 62, 23, 89), 104, 232, fill=_color(p, 3))
    d.arc((41, 62, 55, 89), 308, 64, fill=_color(p, 3))
    for x, y in ((20, 85), (29, 89), (38, 85)):
        d.arc((x, y, x + 5, y + 3), 10, 165, fill=_color(p, 6))
    # Tiny half-asleep eyes and faint sagging lids, not protruding eyeballs.
    for cx, cy in ((21, 59), (43, 60)):
        d.arc((cx - 5, cy - 4, cx + 4, cy + 3), 193, 335, fill=_color(p, 5))
        d.line([(cx - 3, cy), (cx - 1, cy + 1), (cx + 2, cy)], fill=_color(p, 0))
        d.point((cx, cy + 1), fill=_color(p, 1))
    # Chubby cheeks and a tiny closed puckered smile.
    d.ellipse((12, 65, 24, 72), fill=_color(p, 13))
    d.ellipse((40, 66, 52, 73), fill=_color(p, 13))
    d.arc((13, 65, 24, 73), 190, 282, fill=_color(p, 14))
    d.arc((41, 66, 52, 74), 195, 280, fill=_color(p, 14))
    d.line([(30, 71), (33, 73), (30, 75)], fill=_color(p, 2))
    d.line((31, 71, 32, 71), fill=_color(p, 13))
    d.line((30, 76, 33, 75), fill=_color(p, 14))
    # One little belly button is ridiculous at this scale without being a face.
    d.arc((30, 86, 33, 90), 100, 310, fill=_color(p, 5))
    d.line((10, 16, 10, 22), fill=_color(p, 8))
    d.line((7, 19, 13, 19), fill=_color(p, 8))
    return im


def _rainbow_plume():
    im = _blank((16, 64))
    px = im.load()
    stripe = (9, 10, 11, 12, 5, 3, 8)
    for y in range(64):
        center = 7.5 + math.sin(y * .19) * min(2.1, y / 15)
        half = min(6.5, 2.4 + y * .19) * (1 if y < 49 else (65 - y) / 16)
        for x in range(16):
            u = (x - center) / half
            if abs(u) > 1:
                continue
            tone = stripe[min(6, max(0, int((u + 1) * 3.5)))]
            if y > 50 and (x + y) % 4 == 0:
                continue
            px[x, y] = _color(NEON, tone)
    d = ImageDraw.Draw(im)
    d.line([(7, 0), (8, 4), (8, 10), (7, 16)], fill=_color(NEON, 6))
    for x, y in ((1, 17), (14, 30), (2, 44), (12, 57)):
        d.point((x, y), fill=_color(NEON, 6))
        d.point((x, y + 1), fill=_color(NEON, 5))
    return im


def _laser():
    im = _blank((16, 128))
    d = ImageDraw.Draw(im)
    # Concentric stepped beam contours and a continuous white-hot core.
    for box, tone in (((3, 4, 12, 123), 1), ((4, 1, 11, 126), 2),
                      ((5, 0, 10, 127), 8), ((6, 0, 9, 127), 4),
                      ((7, 1, 8, 126), 6)):
        d.rounded_rectangle(box, radius=3, fill=_color(NEON, tone))
    d.line((6, 8, 6, 118), fill=_color(NEON, 5))
    for y in (13, 40, 73, 105):
        d.line([(4, y), (1, y + 3), (3, y + 7), (2, y + 11)], fill=_color(NEON, 3))
        d.line([(11, y + 2), (14, y + 5), (12, y + 8)], fill=_color(NEON, 9))
        d.point((0, y + 8), fill=_color(NEON, 5))
    return im


def _shadow():
    im = _blank((16, 16))
    d = ImageDraw.Draw(im)
    d.ellipse((0, 5, 15, 13), fill=_color(SHADOW, 2))
    d.ellipse((2, 6, 13, 12), fill=_color(SHADOW, 1))
    d.ellipse((4, 7, 11, 11), fill=_color(SHADOW, 0))
    return im


def _flare():
    im = _blank((16, 32))
    d = ImageDraw.Draw(im)
    p = NEON
    d.polygon([(8, 0), (10, 12), (15, 16), (10, 19), (8, 31), (5, 19), (0, 16), (5, 12)], fill=_color(p, 2))
    d.polygon([(8, 3), (9, 13), (14, 16), (9, 18), (8, 29), (6, 18), (1, 16), (6, 13)], fill=_color(p, 9))
    d.ellipse((3, 11, 12, 21), fill=_color(p, 4))
    d.ellipse((5, 13, 10, 19), fill=_color(p, 5))
    d.line((8, 2, 8, 29), fill=_color(p, 6))
    d.line((1, 16, 14, 16), fill=_color(p, 6))
    d.line((5, 12, 11, 20), fill=_color(p, 6))
    d.point((3, 8), fill=_color(p, 5))
    d.point((13, 24), fill=_color(p, 9))
    return im


def make_props():
    """Return original RGBA props plus hardware-oriented metadata.

    Anchors are in unscaled source pixels. The caller may quantize related
    sprites to a shared palette; these images already obey a15-colour limit.
    Suggested transparency is a display setting, never baked into alpha.
    """
    specifications = (
        ("tuna", _tuna, FISH, "fish", (16, 33), 0),
        ("saucer_can", _saucer_can, METAL, "can", (16, 31), 0),
        ("boss_spacefish", _boss_spacefish, FISH, "fish", (32, 65), 0),
        ("rainbow_plume", _rainbow_plume, NEON, "neon", (8, 0), 0),
        ("laser", _laser, NEON, "neon", (8, 127), 25),
        ("shadow", _shadow, SHADOW, "shadow", (8, 9), 75),
        ("flare", _flare, NEON, "neon", (8, 16), 25),
    )
    props = {}
    for name, create, palette, group, anchor, transparency in specifications:
        im = create()
        pixels = list(im.get_flattened_data())
        used = {rgba[:3] for rgba in pixels if rgba[3]}
        assert im.mode == "RGBA" and {rgba[3] for rgba in pixels} <= {0, 255}
        assert 0 < len(used) <= 15 and used <= set(palette), (name, used)
        assert 0 <= anchor[0] < im.width and 0 <= anchor[1] < im.height
        props[name] = {"image": im, "palette": palette, "group": group,
                       "size": im.size, "anchor": anchor,
                       "suggested_transparency_percent": transparency,
                       "opaque_colors_used": len(used)}
    return props


def write_preview(path=None):
    """Write an enlarged nearest-neighbour contact sheet for inspecting pixels."""
    path = Path(path) if path else Path(__file__).resolve().parents[1] / "work/props-preview.png"
    props = make_props()
    sheet = Image.new("RGB", (1024, 690), (9, 13, 27))
    d = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    d.text((24, 18), "COSMIC CAT / ORIGINAL V9968 SUPPORTING SPRITES", fill=(205, 228, 237), font=font)
    positions = {
        "tuna": (28, 72, 5), "saucer_can": (222, 72, 5),
        "boss_spacefish": (442, 72, 4), "rainbow_plume": (740, 72, 4),
        "laser": (862, 72, 4), "shadow": (55, 492, 5), "flare": (232, 448, 5),
    }
    for name, entry in props.items():
        x, y, scale = positions[name]
        im = entry["image"].resize((entry["size"][0] * scale, entry["size"][1] * scale), Image.Resampling.NEAREST)
        sheet.paste(im, (x, y), im)
        label = f"{name}\n{entry['size'][0]}x{entry['size'][1]} / {entry['opaque_colors_used']} colors"
        d.multiline_text((x, y + im.height + 10), label, fill=(153, 178, 198), font=font, spacing=3)
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    return path


if __name__ == "__main__":
    print(write_preview())
