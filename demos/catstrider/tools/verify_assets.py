"""Audit the built CATSTRIDER bytes without regenerating the assets.

This is a static, exhaustive record/address audit. Runtime and physical hardware
claims require their separate evidence; source inspection is identified as such.
"""
from pathlib import Path
import argparse
import ast
import hashlib
import json
import math
import re
import struct

import stage

ROOT = Path(__file__).resolve().parents[1]
PROFILES = ("legacy-openmsx-internal", "legacy-openmsx")
FRAMES, RECORD_BYTES, BANK_BYTES = 1536, 256, 8192


def sha256(path):
    digest = hashlib.sha256()
    with Path(path).open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def data_sections(path):
    """Read plain numeric db/dw include data, not assembler instructions."""
    sections, name = {}, None
    for raw in path.read_text(encoding="ascii").splitlines():
        line = raw.split(";", 1)[0].strip()
        if not line:
            continue
        if line.endswith(":"):
            name = line[:-1]
            require(name not in sections, f"Duplicate data label: {name}")
            sections[name] = bytearray()
            continue
        match = re.fullmatch(r"(db|dw)\s+([0-9,\s]+)", line, re.I)
        require(name is not None and match is not None, f"Unsupported data line: {line}")
        width = 1 if match[1].lower() == "db" else 2
        for number in match[2].split(","):
            sections[name].extend(int(number).to_bytes(width, "little"))
    return {name: bytes(value) for name, value in sections.items()}


def source_layout(root):
    tree = ast.parse((root / "tools/generate.py").read_text(encoding="utf-8"))
    nodes = [node.value for node in tree.body if isinstance(node, ast.Assign)
             and any(isinstance(target, ast.Name) and target.id == "LAYOUT" for target in node.targets)]
    require(len(nodes) == 1, "Generator must have one literal LAYOUT")
    return ast.literal_eval(nodes[0])


def physical_sc8(x, y):
    # d884 Graphic7Mode::addressOf: X wraps at256 AFTER LRMM's window check.
    return ((x & 1) << 16) | ((y & 511) << 7) | ((x & 255) >> 1) | ((y & 512) << 8)


def signed10(value):
    value &= 1023
    return value - 1024 if value & 512 else value


def sprite(attr):
    yw, height, flags, xw, width, pattern = struct.unpack("<HBBHBB", attr)
    return {"x": signed10(xw), "y": signed10(yw), "w": width or 256, "h": height or 256,
            "source_h": 16 << (yw >> 14), "source_x": (pattern & 15) * 16,
            "source_y": (((xw >> 12) & 7) << 8) | ((pattern >> 4) * 16),
            "group": flags & 15, "flip_x": bool(flags & 16), "flip_y": bool(flags & 32),
            "tp": flags >> 6, "raw_y": yw & 1023}


def forward_motion(motion):
    """Measure encoded texture travel without re-running the projection code."""
    first, last = 240, 1200
    distances = [stage.travel(frame) for frame in range(first, last + 1)]
    require(all(math.isfinite(value) for value in distances), "Non-finite world travel")
    source_steps = [b - a for a, b in zip(distances, distances[1:])]
    require(min(source_steps) > 1.8, "Flight travel is below the requested world speed")
    # An integer SY step is quantized, so measure each line over the whole
    # interval. Mod64 unwraps the authored tile; bounds reject stalls, reverse
    # motion and arbitrary source jumps before the average is considered.
    line_speeds = []
    steps_seen = set()
    for line in range(112):
        positions = [motion[frame * 256 + line] - 128 for frame in range(first, last + 1)]
        steps = [(b - a) % 64 for a, b in zip(positions, positions[1:])]
        require(all(1 <= step <= 4 for step in steps), f"Floor line {line} stalled, reversed or jumped")
        speed = sum(steps) / (last - first)
        require(speed > 1.8, f"Stored floor line {line} advances too slowly")
        line_speeds.append(speed)
        steps_seen.update(steps)
    return {"frames": [first, last], "stored_scanlines_checked": 112,
            "minimum_source_units_per_frame": min(source_steps),
            "minimum_stored_average_units_per_frame": min(line_speeds),
            "maximum_stored_average_units_per_frame": max(line_speeds),
            "quantized_forward_steps": sorted(steps_seen)}


def receding_projectiles(beams):
    """Check stored SAT trajectories during the fixed-aim part of the stage.

    Six-frame emissions live for18 frames. Match the same emission across
    records, then require shrinking area and approach to the vanishing point;
    this deliberately does not reproduce the generator's perspective formula.
    """
    tracks = 0
    for emission in range(240, 861, 6):
        if not stage.laser_active(emission):
            continue
        track = []
        for age in range(18):
            frame = emission + age
            newest = frame - frame % 6
            active = [f for f in (newest, newest - 6, newest - 12) if stage.laser_active(f)]
            require(len(beams[frame]) == len(active), f"Projectile lifetime/count differs at frame {frame}")
            track.append(beams[frame][active.index(emission)])
        start, end = track[0], track[-1]
        distance = lambda s: math.hypot(s["x"] + s["w"] / 2 - 128, s["y"] + s["h"] / 2 - 91)
        require(distance(end) < distance(start), f"Emission {emission} does not recede toward the fixed aim point")
        require(end["w"] * end["h"] < start["w"] * start["h"], f"Emission {emission} does not shrink with distance")
        tracks += 1
    require(tracks > 50, "Too few independent projectile tracks checked")
    return {"stored_emissions_checked": tracks, "records_per_emission": 18,
            "fixed_aim_screen_position": [128, 91], "all_shrink_and_approach_aim": True,
            "method": "Match stored opaque streak SAT entries across emission lifetimes; compare endpoint area and distance"}


def verify(root=ROOT):
    root = Path(root).resolve()
    assets, out = root / "assets", root / "outputs"
    report = {"passed": False, "validation": "Static built-byte/address audit; no emulator or hardware execution",
              "hardware_tested": False, "frames_checked": FRAMES}
    generation = json.loads((assets / "generation-report.json").read_text())
    manifest = json.loads((out / "build-manifest.json").read_text())
    require(len(manifest) == 2 and {entry["profile"] for entry in manifest} == set(PROFILES),
            "Exactly the internal and external profile builds are required")
    motion = (assets / "motion.bin").read_bytes()
    upload = (assets / "vram-upload.bin").read_bytes()
    background = (assets / "background-indexed.bin").read_bytes()
    atlas = (assets / "sprite-atlas.bin").read_bytes()
    require(len(motion) == FRAMES * RECORD_BYTES, "Motion is not1536 aligned256-byte records")
    require(len(upload) == 98304 and len(background) == 65536 and len(atlas) == 32768,
            "VRAM asset sizes differ from the96KiB interleaved upload contract")
    require(upload == background[::2] + atlas + background[1::2], "SC8 plane/atlas upload packing differs")
    require(max(background) < 192, "Bitmap uses a Sprite3 palette entry")
    require(max(background[:32768]) < 128 and min(background[32768:]) >= 128,
            "Sky/floor bitmap palette ranges are not independent")
    palettes = data_sections(assets / "palettes.inc")
    initial, pulse, floor_palette, chords = (palettes[key] for key in
                                            ("initial_palette", "pulse_palettes", "floor_palettes", "chords"))
    require(len(initial) == 256 * 3 and len(pulse) == len(floor_palette) == 32 * 64 * 3 and len(chords) == 32 * 6,
            "Palette/music include dimensions differ")
    require(max(initial + pulse + floor_palette) <= 31, "Loaded palette contains a value outside RGB5")
    require(all(pulse[phase * 192:phase * 192 + 48] == initial[192 * 3:208 * 3] for phase in range(32)),
            "Sprite palette animation changes the accepted cat colors")
    floor_palette_variants = len({floor_palette[phase * 192:(phase + 1) * 192] for phase in range(32)})
    require(floor_palette_variants > 1, "Floor color animation has no changing palette")
    require(initial == (assets / "palette-rgb5.bin").read_bytes(), "Initial palette binary/include differ")
    require(all(1 <= period <= 4095 for (period,) in struct.iter_unpack("<H", chords)),
            "A PSG tone period is outside the12-bit range")
    geom = data_sections(assets / "floor-geometry.inc")["floor_geometry"]
    require(len(geom) == 112 * 5, "Expected112 five-byte static scanline geometry records")
    geometry = [(sx, vx, dx, nx or 256) for sx, vx, dx, nx in struct.iter_unpack("<BHBB", geom)]
    require(all(0 <= sx <= 63 and 16 <= vx <= 448 and 0 <= dx <= 4 and nx + dx == 256
                for sx, vx, dx, nx in geometry), "SX/VX/DX/NX outside authored bounds")
    center_errors = []
    for sx, vx, dx, nx in geometry:
        scale = vx / 256
        ideal = 32 - vx / 2
        # The source texture repeats every64 texels. Compare equivalent phases
        # before converting the residual into destination-screen pixels.
        error = ((sx - dx * scale - ideal + 32) % 64 - 32) / scale
        require(abs(error) <= 0.6, "A floor scanline has excessive center-phase error")
        center_errors.append(abs(error))
    samples = [[sx + ((x * vx) >> 8) for x in range(nx)] for sx, vx, dx, nx in geometry]
    require(all(0 <= x <= 511 for line in samples for x in line), "LRMM X exceeds window before wrapping")
    floor_addresses = set()
    for line, xs in enumerate(samples):
        ys = {512 + motion[frame * 256 + line] for frame in range(FRAMES)}
        require(all(640 <= y <= 703 for y in ys), f"Scanline{line} SY exceeds source texture")
        floor_addresses.update(physical_sc8(x, y) for x in xs for y in ys)
    require(all(0x20000 <= a < 0x28000 or 0x30000 <= a < 0x38000 for a in floor_addresses),
            "Floor sample aliases the Sprite3 atlas or an uninitialized address")
    require(all(upload[a - 0x20000] == background[((a & 0xFFFF) << 1) | ((a >> 16) & 1)]
                for a in floor_addresses), "Physical floor pixels differ from the indexed source")

    layout = source_layout(root)
    require({name: list(extent) for name, extent in layout.items()} == generation["layout"],
            "Built LAYOUT differs from generator source")
    occupied = set()
    old_laser = layout["laser"]
    for name, (x, y, width, height, group) in layout.items():
        require(x % 16 == y % 16 == width % 16 == 0 and height in (16, 32, 64, 128), f"Unaligned atlas extent: {name}")
        require(0 <= x < x + width <= 256 and 0 <= y < y + height <= 256 and 12 <= group <= 15,
                f"Atlas extent out of bounds: {name}")
        pixels = {row * 256 + col for row in range(y, y + height) for col in range(x, x + width)}
        require(not occupied.intersection(pixels), f"Overlapping LAYOUT region: {name}")
        occupied.update(pixels)

    phases = stage.PHASES
    require(stage.FRAMES == FRAMES and len(phases) == 4 and phases[0]["start"] == 0
            and phases[-1]["end"] == FRAMES, "Stage must have four phases covering one complete loop")
    require(all(p["id"] == i and p["start"] < p["end"] for i, p in enumerate(phases))
            and all(a["end"] == b["start"] for a, b in zip(phases, phases[1:])), "Stage has a gap, overlap or reordered phase")
    require(generation["phases"] == phases, "Built phase table differs from source")
    require(phases[0]["end"] == 120 and phases[3]["start"] == 1320, "Introduction/departure timing differs")
    travel = forward_motion(motion)
    active_max, line_max = 0, 0
    sprite_min, sprite_max = 0x40000, 0
    usage = {name: 0 for name in layout}
    boss_heights, finale_frames, scene_counts = [], [], [0] * 4
    hero_poses, hero_flips = set(), set()
    beam_records = []
    volume_values, noise_values, mixer_values = [set() for _ in range(3)], set(), set()
    for frame in range(FRAMES):
        record = motion[frame * 256:(frame + 1) * 256]
        require(record[240] < 32 and record[241] < 32, f"Palette/music index at frame{frame}")
        expected_scene = next(p["id"] for p in phases if p["start"] <= frame < p["end"])
        require(record[242] == expected_scene and record[243] & 1, f"Scene/autopilot flag at frame{frame}")
        require(record[243] & ~3 == 0 and not any(record[253:]), f"Unknown metadata at frame{frame}")
        require(all(value <= 15 for value in record[248:251]) and record[251] <= 31 and record[252] <= 63,
                f"PSG volume/noise/mixer metadata out of range at frame{frame}")
        for voice, volume in enumerate(record[248:251]):
            volume_values[voice].add(volume)
        noise_values.add(record[251]); mixer_values.add(record[252])
        require(all(math.isfinite(value) for value in stage.autopilot(frame)), f"Non-finite hero state at frame{frame}")
        scene_counts[record[242]] += 1
        hero_x, hero_y, stride, hero_h = record[244:248]
        require(1 <= stride <= 85 and hero_x + 3 * stride <= 256 and hero_y < 212 and hero_h > 0,
                f"Invalid hero RAM state at frame{frame}")
        active, lines, hero_sources, beams = 0, [0] * 212, [], []
        for slot in range(16):
            attr = record[112 + slot * 8:120 + slot * 8]
            s = sprite(attr)
            require(s["raw_y"] != 216, f"Early Sprite3 terminator at frame{frame} slot{slot}")
            first = 0x28000 + s["source_y"] * 128 + s["source_x"] // 2
            last = first + (s["source_h"] - 1) * 128 + 7
            require(0x28000 <= first <= last <= 0x2FFFF, f"Atlas pointer escapes at frame{frame} slot{slot}")
            sprite_min, sprite_max = min(sprite_min, first), max(sprite_max, last)
            visible = s["x"] < 256 and s["x"] + s["w"] > 0 and s["y"] < 212 and s["y"] + s["h"] > 0
            require(not (s["group"] == 12 and s["source_y"] == 0), f"Front-facing cat source referenced at frame{frame} slot{slot}")
            require(not (s["source_x"] == old_laser[0] and s["source_y"] == old_laser[1]
                         and s["source_h"] == old_laser[3] and s["group"] == old_laser[4]),
                    f"Old vertical laser source referenced at frame{frame} slot{slot}")
            if slot < 3:
                require((s["x"], s["y"], s["w"], s["h"]) == (hero_x + slot * stride, hero_y, stride, hero_h),
                        f"Hero metadata and SAT differ at frame{frame} slot{slot}")
                require(s["source_h"] == 64 and s["group"] == 12 and s["tp"] == 0 and not s["flip_y"],
                        f"Hero source/opaque palette contract at frame{frame} slot{slot}")
                hero_sources.append((s["source_x"], s["source_y"], s["flip_x"]))
            if not visible:
                continue
            active += 1
            for y in range(max(0, s["y"]), min(212, s["y"] + s["h"])):
                lines[y] += 1
            matches = [name for name, (x, y, width, height, group) in layout.items()
                       if x <= s["source_x"] and s["source_x"] + 16 <= x + width
                       and y == s["source_y"] and height == s["source_h"] and group == s["group"]]
            require(len(matches) == 1, f"Visible sprite does not refer to its declared artwork at frame{frame} slot{slot}")
            kind = matches[0]
            require(kind != "laser", f"Old full-height vertical laser referenced at frame{frame} slot{slot}")
            usage[kind] += 1
            if kind in ("streak_left", "streak_right") and s["tp"] == 0:
                require(s["source_h"] == 64 and s["w"] < 64 and s["h"] < 64,
                        f"Perspective projectile became a full-height column at frame{frame} slot{slot}")
                beams.append(s)
            if kind == "boss":
                boss_heights.append((frame, s["h"]))
            if kind == "ending":
                finale_frames.append(frame)
        sy = 64
        flip = hero_sources[0][2]
        require(hero_sources == [(16 * (2 - k if flip else k), sy, flip) for k in range(3)],
                f"Hero three-strip orientation/pose mismatch at frame{frame}")
        hero_poses.add(sy); hero_flips.add(flip)
        beam_records.append(beams)
        active_max, line_max = max(active_max, active), max(line_max, max(lines))
        require(active <= 16 and max(lines) <= 16, f"Sprite3 scanline capacity exceeded at frame{frame}")
        # Reproduce the Z80 bank arithmetic, then compare actual bytes below.
        hi, lo = frame >> 8, frame & 255
        rotated = ((lo << 3) | (lo >> 5)) & 255
        bank, cpu_address = 16 + ((rotated & 7) | (hi * 8)), 0x6000 + ((lo & 31) << 8)
        require(bank == 16 + frame // 32 and cpu_address + 256 <= 0x8000, f"Bank boundary at frame{frame}")
    require(active_max <= generation["maximum_sprites"] <= 16, "Sprite count report understates the active maximum")
    require(hero_poses == {64} and hero_flips == {False, True}, "Rear-only hero source and both banking orientations must appear")
    require(usage["cat"] == usage["laser"] == 0, "Unused front cat or vertical laser appears in the stage")
    require(all(usage[name] for name in ("fish", "can", "rainbow", "ring", "streak_left", "streak_right")),
            "Stage lacks a required world event or motion effect")
    projectiles = receding_projectiles(beam_records)
    departure = [motion[frame * 256 + 244:frame * 256 + 248] for frame in range(1320, FRAMES)]
    require(all(b[2] <= a[2] and b[3] <= a[3] for a, b in zip(departure, departure[1:]))
            and departure[-1][2] < departure[0][2] and departure[-1][3] < departure[0][3]
            and departure[-1][1] < departure[0][1], "Ending hero must shrink and fly away, not zoom toward the camera")
    require(boss_heights and min(f for f, _ in boss_heights) >= 900 and max(h for _, h in boss_heights) >= 128,
            "Giant-fish climax does not occur in the authored encounter")
    require(finale_frames and min(finale_frames) >= 1440 and FRAMES - 1 in finale_frames,
            "Finale card must follow the encounter and remain on the final record")
    require(motion[242] == 0 and motion[(FRAMES - 1) * 256 + 242] == 3,
            "Stage does not start at the introduction and end at the finale")

    source_fields = {"cat-key.png": "cat_source_sha256", "cat-flight-key.png": "cat_flight_source_sha256",
                     "cat-front-sunglasses-key.png": "cat_front_source_sha256",
                     "fish-photo-key.png": "fish_source_sha256", "can-photo-key.png": "can_source_sha256"}
    source_hashes = {name: sha256(root / "art-source" / name) for name in source_fields}
    require(all(source_hashes[name] == generation[field] for name, field in source_fields.items()),
            "Original photographic source SHA differs from the assets used for this build")
    rom_hashes = {}
    for entry in manifest:
        require(entry["file"] == f"CATSTRIDER-V9968-{entry['profile']}.rom", "Unexpected manifest ROM filename")
        path = out / entry["file"]
        rom = path.read_bytes()
        require(len(rom) == 524288 and rom[:2] == b"AB" and entry["rom_bytes"] == len(rom), "ROM size/header differs")
        require(sha256(path) == entry["sha256"] and entry["mapper"] == "ASCII8", "Manifest ROM hash/mapper differs")
        require(entry["upload_banks"] == [4, 15] and entry["motion_banks"] == [16, 63]
                and entry["motion_records"] == FRAMES, "Manifest bank layout differs")
        length = entry["runtime_bytes"]
        require(0 < length <= 24576 and rom[8192 + length:32768] == b"\xff" * (24576 - length),
                "Runtime padding does not fit the24KiB RAM load")
        require(bytes.fromhex("3e01110080") in rom[:8192]
                and bytes.fromhex("320068210060010020edb03cfe04") in rom[:8192],
                "Boot no longer copies banks1..3 from6000h to8000h..DFFFh")
        require(rom[32768:131072] == upload and rom[131072:] == motion, "ROM upload/motion bytes differ from assets")
        runtime = rom[8192:8192 + length]
        for name, data in (("initial_palette", initial), ("pulse_palettes", pulse), ("floor_palettes", floor_palette),
                           ("chords", chords), ("floor_geometry", geom)):
            require(runtime.count(data) == 1, f"Runtime data section is missing or ambiguous: {name}")
        for frame in range(FRAMES):
            bank, offset = 16 + frame // 32, (frame & 31) * 256
            require(rom[bank * 8192 + offset:bank * 8192 + offset + 256] == motion[frame * 256:(frame + 1) * 256],
                    f"Loaded record differs at frame{frame}")
        rom_hashes[entry["profile"]] = entry["sha256"]
    source = (root / "src/demo.asm").read_text(encoding="utf-8")
    require(all(re.search(rf"(?m)^{label}:", source) for label in
                ("autopilot", "apply_hero_pose", "hero_x", "hero_y", "hero_width", "hero_height")),
            "Explicit future input/rendering labels are missing")
    report.update(passed=True, rom_sha256=rom_hashes, source_sha256=source_hashes,
                  asset_sha256={path.name: sha256(path) for path in sorted(assets.iterdir()) if path.is_file()},
                  source_code_sha256={name: sha256(root / name) for name in ("src/demo.asm", "src/boot.asm", "tools/generate.py", "tools/stage.py", "tools/props.py", "tools/photo_props.py", "tools/effects.py")},
                  bank_mapping_records_checked=FRAMES * len(manifest), source_window_x=[0, 511], source_window_y=[640, 767],
                  floor_scanlines_per_update=112, floor_scanlines_checked=FRAMES * 112,
                  floor_geometry_record_bytes=5, floor_maximum_center_error_pixels=max(center_errors),
                  floor_dx_range=[min(g[2] for g in geometry), max(g[2] for g in geometry)],
                  floor_right_edge_always_256=True,
                  floor_physical_address_range=[min(floor_addresses), max(floor_addresses)],
                  sprite_attributes_checked=FRAMES * 16, sprite_source_address_range=[sprite_min, sprite_max],
                  maximum_visible_sprites=active_max, maximum_sprites_per_scanline=line_max,
                  no_early_y216=True, layout_nonoverlapping=True, all_palette_components_rgb5=True,
                  scene_frame_counts=scene_counts, phase_sequence=[0, 1, 2, 3], boss_maximum_height=max(h for _, h in boss_heights),
                  first_finale_card_frame=min(finale_frames), artwork_plane_usage=usage,
                  hero_rear_only=True, departure_shrinks_and_rises=True, forward_motion=travel, projectiles=projectiles,
                  floor_palette_variants=floor_palette_variants, cat_palette_animation_preserves_original=True,
                  psg_metadata={"voice_volume_values": [sorted(values) for values in volume_values],
                                "noise_period_values": sorted(noise_values), "mixer_low_six_values": sorted(mixer_values),
                                "reserved_253_255_zero": True},
                  hero_metadata_matches_three_attrs=True, future_hero_hook_validation="Source labels and recorded SAT/state consistency only; no live-input experiment",
                  loop_validation="All1536 ordered records checked; runtime wrap is verified separately by run_check.py")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.parse_args()
    target = ROOT / "outputs/asset-verification.json"
    target.parent.mkdir(exist_ok=True)
    try:
        report = verify()
    except Exception as error:
        report = {"passed": False, "error": f"{type(error).__name__}: {error}", "hardware_tested": False}
        target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        raise
    target.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
