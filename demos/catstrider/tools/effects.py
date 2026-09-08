"""Original V9968 portal and perspective streak sprites using props.NEON.

make_effects() returns image/metadata dictionaries like make_props(). All source
images use binary alpha and only the existing fifteen-colour NEON palette.
Run this module to write work/effects-preview.png; no build assets are changed.
"""
from pathlib import Path
import math
from PIL import Image, ImageDraw, ImageFont

if __package__:
    from .props import NEON
else:
    from props import NEON


def _color(index):
    return (*NEON[index], 255)


def _ring():
    im = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    px = im.load()
    cyan = (1, 2, 3, 4, 5, 6)
    magenta = (1, 7, 8, 9, 10, 6)
    for y in range(64):
        for x in range(64):
            dx, dy = x - 31.5, y - 31.5
            radius = math.hypot(dx, dy)
            if not 22.0 <= radius <= 31.0:
                continue
            angle = math.atan2(dy, dx)
            # The broad body, inner filament and outer rim have distinct radii.
            # Their empty gaps keep this from being a solid coloured doughnut.
            spine = math.exp(-((radius - 27.0) / .90) ** 2)
            glow = .35 * math.exp(-((radius - 27.0) / 2.0) ** 2)
            inner = .42 * math.exp(-((radius - 22.6) / .35) ** 2)
            outer = .45 * math.exp(-((radius - 30.0) / .40) ** 2)
            gleam = .72 + .24 * math.cos(angle + 2.2)
            value = max(spine + glow, inner, outer) * gleam
            if value < .095:
                continue
            ramp = cyan if dx < 0 else magenta
            tone = ramp[min(5, max(0, int(value * 4.7)))]
            px[x, y] = _color(tone)
    d = ImageDraw.Draw(im)
    # Broken inner rails and a few short radial connectors suggest an energized
    # machine aperture, with a completely transparent central opening.
    for start, stop, radius, tone in (
        (195, 241, 23, 4), (247, 266, 23, 5),
        (279, 315, 23, 9), (325, 344, 23, 8),
        (16, 48, 23, 9), (61, 92, 23, 10),
        (105, 143, 23, 4), (153, 172, 23, 5),
        (199, 235, 30, 5), (278, 310, 30, 9),
    ):
        points = []
        for degree in range(start, stop + 1):
            t = math.radians(degree)
            points.append((round(31.5 + radius * math.cos(t)),
                           round(31.5 + radius * math.sin(t))))
        d.line(points, fill=_color(tone))
    for degree, tone in ((180, 5), (220, 6), (262, 5), (311, 9), (44, 10), (118, 4)):
        t = math.radians(degree)
        a = (round(31.5 + 25 * math.cos(t)), round(31.5 + 25 * math.sin(t)))
        b = (round(31.5 + 29 * math.cos(t)), round(31.5 + 29 * math.sin(t)))
        d.line((a, b), fill=_color(tone))
    # White-hot, localized reflections retain visible hue around the rest.
    for degree in (209, 212, 216, 246, 303, 36):
        t = math.radians(degree)
        x, y = round(31.5 + 27 * math.cos(t)), round(31.5 + 27 * math.sin(t))
        d.point((x, y), fill=_color(6))
    return im


def _streak_right():
    im = Image.new("RGBA", (16, 64), (0, 0, 0, 0))
    px = im.load()
    for y in range(64):
        t = y / 63
        center = 1 + 13 * t
        radius = .6 + 2.1 * t ** 1.5
        for x in range(16):
            distance = abs(x - center)
            if distance > radius + 1.3:
                continue
            # A long tapered tail accelerates toward a hot head at the bottom
            # outer corner; its side filaments have different coloured glows.
            intensity = math.exp(-(distance / radius) ** 2) * (.28 + .9 * t)
            if intensity < .12:
                continue
            ramp = (1, 2, 3, 4, 5, 6) if x <= center else (1, 7, 8, 9, 5, 6)
            tone = ramp[min(5, int(intensity * 5.5))]
            if distance < .42 and y > 21:
                tone = 6
            px[x, y] = _color(tone)
    d = ImageDraw.Draw(im)
    # Short, separate ribbons give an expanded sprite more than one flat line.
    for start, stop, offset, tone in ((10, 21, 3, 3), (24, 41, 3, 9),
                                      (39, 57, -3, 4), (49, 61, -4, 5)):
        points = [(round(1 + 13 * y / 63 + offset), y) for y in range(start, stop + 1)]
        d.line(points, fill=_color(tone))
    d.line([(round(1 + 13 * y / 63), y) for y in range(44, 64)], fill=_color(6))
    d.point((5, 38), fill=_color(5))
    d.point((8, 55), fill=_color(4))
    return im


def make_effects():
    right = _streak_right()
    images = {
        "ring": _ring(),
        "streak_left": right.transpose(Image.Transpose.FLIP_LEFT_RIGHT),
        "streak_right": right,
    }
    result = {}
    for name, im in images.items():
        pixels = list(im.get_flattened_data())
        used = {rgba[:3] for rgba in pixels if rgba[3]}
        assert {rgba[3] for rgba in pixels} <= {0, 255}
        assert 0 < len(used) <= 15 and used <= set(NEON), (name, used)
        result[name] = {
            "image": im, "palette": NEON, "group": "neon", "size": im.size,
            "anchor": (32, 32) if name == "ring" else ((1, 63) if name == "streak_left" else (14, 63)),
            "suggested_transparency_percent": 0, "opaque_colors_used": len(used),
        }
    # A centered 44px-diameter disk is empty, exceeding the required38px opening.
    ring = images["ring"]
    assert all(ring.getpixel((x, y))[3] == 0 for y in range(64) for x in range(64)
               if math.hypot(x - 31.5, y - 31.5) < 22)
    assert images["streak_left"].tobytes() == right.transpose(Image.Transpose.FLIP_LEFT_RIGHT).tobytes()
    return result


def write_preview(path=None):
    path = Path(path) if path else Path(__file__).resolve().parents[1] / "work/effects-preview.png"
    props = make_effects()
    sheet = Image.new("RGB", (900, 440), (8, 11, 26))
    d = ImageDraw.Draw(sheet)
    font = ImageFont.load_default()
    d.text((20, 15), "CATSTRIDER / LIVE PORTAL AND INCOMING STAR STREAKS", font=font, fill=(198, 223, 235))
    for name, xy, scale in (("ring", (25, 62), 5), ("streak_left", (409, 62), 5),
                            ("streak_right", (540, 62), 5)):
        entry = props[name]
        im = entry["image"].resize((entry["size"][0] * scale, entry["size"][1] * scale), Image.Resampling.NEAREST)
        sheet.paste(im, xy, im)
        d.text((xy[0], xy[1] + im.height + 12), name, fill=(153, 177, 200), font=font)
    # Show the portal's intended expanded billboard aspect without interpolation.
    ring = props["ring"]["image"].resize((240, 180), Image.Resampling.NEAREST)
    sheet.paste(ring, (648, 131), ring)
    d.text((651, 327), "wide billboard example", fill=(153, 177, 200), font=font)
    path.parent.mkdir(parents=True, exist_ok=True)
    sheet.save(path)
    return path


if __name__ == "__main__":
    print(write_preview())
