"""Encode original generated fish/can photos as binary-alpha Sprite3 artwork.

Only chroma-keying, proportional fitting and hardware palette conversion occur
here. The subject is not repainted or stretched. Fish and boss share the same
source and one15-colour palette; the tin has a separate15-colour palette.
"""
from pathlib import Path

from PIL import Image


def chroma_cutout(path):
    """Remove the generated magenta backdrop before resampling the photograph."""
    with Image.open(path) as opened:
        source = opened.convert("RGB")
    pixels = []
    for r, g, b in source.getdata():
        key = r > g + 65 and b > g + 45 and r > 160 and b > 130
        pixels.append((0, 0, 0, 0) if key else (r, g, b, 255))
    cutout = Image.new("RGBA", source.size)
    cutout.putdata(pixels)
    bounds = cutout.getchannel("A").getbbox()
    if bounds is None:
        raise ValueError(f"No subject remains after chroma key: {path}")
    return cutout.crop(bounds)


def fit_sprite(source, size):
    """Fit inside a one-pixel guard margin and center without changing aspect."""
    available = (size[0] - 2, size[1] - 2)
    scale = min(available[0] / source.width, available[1] / source.height)
    fitted = (max(1, min(available[0], round(source.width * scale))),
              max(1, min(available[1], round(source.height * scale))))
    # Premultiplied filtering prevents removed magenta from tinting the edges.
    small = source.convert("RGBa").resize(fitted, Image.Resampling.LANCZOS).convert("RGBA")
    small.putdata([(r, g, b, 255) if a >= 128 else (0, 0, 0, 0)
                   for r, g, b, a in small.getdata()])
    result = Image.new("RGBA", size)
    result.paste(small, ((size[0] - fitted[0]) // 2, (size[1] - fitted[1]) // 2))
    return result


def luminance(color):
    return 2126 * color[0] + 7152 * color[1] + 722 * color[2]


def hardware_rgb(color):
    """Use the displayed RGB5 colour for nearest-colour matching as well."""
    return tuple(round(round(component * 31 / 255) * 255 / 31) for component in color)


def average(colors):
    return tuple(round(sum(color[channel] for color in colors) / len(colors)) for channel in range(3))


def photo_palette(images):
    """Keep dark pupils/metal shadows and silver highlights in a15-colour set."""
    pixels = [rgba[:3] for image in images for rgba in image.getdata() if rgba[3] == 255]
    if not pixels:
        raise ValueError("Cannot quantize an empty photograph")
    ordered = sorted(pixels, key=luminance)
    tail = max(1, len(ordered) // 250)
    neutral = [rgb for rgb in ordered if max(rgb) - min(rgb) <= 32 and 80 <= sum(rgb) / 3 <= 220]
    if not neutral:
        neutral = ordered[len(ordered) // 2:len(ordered) // 2 + 1]
    # Fixed anchors protect tiny details that area-based quantization can merge
    # into the much larger pink scales or teal label. They come from the photo.
    anchors = [average(ordered[:tail]), average(ordered[-tail:]),
               average(neutral[len(neutral) * 3 // 4:])]
    swatch = Image.new("RGB", (len(pixels), 1))
    swatch.putdata(pixels)
    quantized = swatch.quantize(colors=12, method=Image.Quantize.MEDIANCUT,
                               dither=Image.Dither.NONE)
    raw = quantized.getpalette()[:36]
    candidates = anchors + [tuple(raw[index:index + 3]) for index in range(0, 36, 3)]
    palette = list(dict.fromkeys(hardware_rgb(color) for color in candidates))
    # RGB5 rounding can merge nearby entries. Fill any spare slots with source
    # colours furthest from the current palette, with deterministic tie breaks.
    available = sorted({hardware_rgb(color) for color in pixels} - set(palette))
    while len(palette) < 15 and available:
        selected = max(available, key=lambda color: (min(sum((a - b) ** 2 for a, b in zip(color, p))
                                                        for p in palette), color))
        palette.append(selected)
        available.remove(selected)
    while len(palette) < 15:
        palette.append(palette[-1])
    return tuple(palette[:15])


def make_photo_props(art_source):
    art_source = Path(art_source)
    fish_source = chroma_cutout(art_source / "fish-photo-key.png")
    can_source = chroma_cutout(art_source / "can-photo-key.png")
    fish = fit_sprite(fish_source, (32, 64))
    boss = fit_sprite(fish_source, (64, 128))
    can = fit_sprite(can_source, (32, 64))
    fish_palette = photo_palette((fish, boss))
    can_palette = photo_palette((can,))
    return {"fish": {"image": fish, "palette": fish_palette},
            "boss": {"image": boss, "palette": fish_palette},
            "can": {"image": can, "palette": can_palette}}
