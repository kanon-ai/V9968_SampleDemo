"""Compare frozen physical VRAM against an independent d884 LRMM reference.

Only a private emulator instance is patched in RAM; the ROM is never changed.
The reference uses the pinned emulator's integer coordinate rules, not the
generator's artwork or motion functions. A frame is identified from FRAME/SAT,
before looking at the transformed pixels, so a visually similar frame cannot
be chosen just because it happens to match.
"""
import argparse
import hashlib
import json
import re
import struct

from run_check import EXE, ROOT, run

COMMIT = "d884c4b29d7e736d6e488aca5f28e124a410c19f"
SOURCE = f"https://github.com/buppu3/openMSX/blob/{COMMIT}/src/video/VDPCmdEngine.cc"
FRAME_BYTES = 256
FRAME_COUNT = 1024


def sha256(data):
    return hashlib.sha256(data).hexdigest()


def signed(value, bits):
    value &= (1 << bits) - 1
    return value - (1 << bits) if value & (1 << (bits - 1)) else value


def trunc256(value):
    # C++ signed division truncates toward zero, including negative fractions.
    return value // 256 if value >= 0 else -((-value) // 256)


def pixel4(data, base, x, y):
    value = data[base + y * 128 + x // 2]
    return (value >> 4) if x % 2 == 0 else (value & 15)


def reference(template, vector, width, height, window):
    """FG4, EVR, IMP, positive destination directions, XHR clear, COL=0.

    startLrmmHs sign-extends SX to 12 bits and SY to 13 bits; executeLrmmHs
    adds (VX,VY) along each row and (-VY,VX) between row origins. Graphic4Mode
    uses 128 physical bytes per row and high nibble for an even X coordinate.
    Inclusive source clipping happens before address wrapping or reading VRAM.
    """
    sx, sy, vx, vy = vector
    sx, sy = signed(sx, 12), signed(sy, 13)
    x0, y0, x1, y1 = window
    output = bytearray()
    outside = []
    for y in range(height):
        for x in range(width):
            tx = trunc256(sx * 256 + x * vx - y * vy)
            ty = trunc256(sy * 256 + x * vy + y * vx)
            if x0 <= tx <= x1 and y0 <= ty <= y1:
                output.append(pixel4(template, 0, tx, ty - 1280))
            else:
                outside.append(len(output))
                output.append(0)
    return bytes(output), outside


def capture(profile, seconds, work):
    symbols = (ROOT / f"work/build/demo-{profile}.symbols").read_text()
    def address(name):
        match = re.search(rf"\b{name}\s+EQU 0([0-9A-F]+)H", symbols)
        if not match:
            raise ValueError(f"Missing build symbol: {name}")
        return int(match[1], 16)

    main, frame, index = (address(n) for n in ("main_loop", "FRAME", "frame_index"))
    vdp = "VDP" if profile.endswith("internal") else "V9968"
    physical = "physical VRAM" if profile.endswith("internal") else "physical V9968 VRAM"
    relative = "../" + work.name
    script = r'''
set save_settings_on_exit false
set throttle false
set renderer SDLGL-PP
set minframeskip 0
set maxframeskip 0
proc write_binary {name value} {
    set f [open "__WORK__/$name" wb]
    puts -nonewline $f $value
    close $f
}
proc fail_capture {err opts} {
    set f [open check-error.txt w]
    puts $f $err
    puts $f $opts
    close $f
    exit
}
proc freeze_motion {} {
    if {[catch {
        debug write memory __MAIN__ 24
        debug write memory __NEXT__ 254
        after time 0.15 capture_frozen
    } err opts]} {fail_capture $err $opts}
}
proc capture_frozen {} {
    if {[catch {
        write_binary vram.bin [debug read_block {__PHYSICAL__} 0 262144]
        write_binary registers.bin [debug read_block {__VDP__ regs} 0 64]
        write_binary frame.bin [debug read_block memory __FRAME__ 256]
        write_binary frame-index.bin [debug read_block memory __INDEX__ 2]
        write_binary patched-loop.bin [debug read_block memory __MAIN__ 2]
        set f [open "__WORK__/capture.txt" w]
        puts $f "machine=[machine_info config_name]"
        puts $f "requested_freeze_seconds=__SECONDS__"
        puts $f "settle_seconds=0.15"
        close $f
    } err opts]} {fail_capture $err $opts}
    exit
}
after time __SECONDS__ freeze_motion
'''
    replacements = {"__WORK__": relative, "__MAIN__": main, "__NEXT__": main + 1,
                    "__PHYSICAL__": physical, "__VDP__": vdp, "__FRAME__": frame,
                    "__INDEX__": index, "__SECONDS__": seconds}
    for key, value in replacements.items():
        script = script.replace(key, str(value))
    run(script, profile, timeout=max(90, seconds * 5))


def analyze(profile, seconds, work):
    vram = (work / "vram.bin").read_bytes()
    regs = (work / "registers.bin").read_bytes()
    frame = (work / "frame.bin").read_bytes()
    index = int.from_bytes((work / "frame-index.bin").read_bytes(), "little")
    motion = (ROOT / "assets/motion.bin").read_bytes()
    template = (ROOT / "assets/sprites.bin").read_bytes()
    background = (ROOT / "assets/background-indexed.bin").read_bytes()
    assert len(vram) == 262144 and len(regs) == 64 and len(frame) == FRAME_BYTES
    assert len(motion) == FRAME_COUNT * FRAME_BYTES and len(template) == 32768
    assert len(background) == 65536
    assert (work / "patched-loop.bin").read_bytes() == b"\x18\xfe"
    records = [motion[n:n + FRAME_BYTES] for n in range(0, len(motion), FRAME_BYTES)]
    matches = [n for n, record in enumerate(records) if record == frame]
    assert len(matches) == 1, f"FRAME must uniquely identify the last loaded record: {matches}"
    presented = matches[0]
    assert index == (presented + 1) % FRAME_COUNT, (index, presented)
    assert regs[5] in (0xC3, 0xCB) and regs[6] in (0x70, 0x78)
    active = 0 if regs[6] == 0x70 else 1
    assert regs[5] == (0xC3, 0xCB)[active] and regs[2] == (0x3F, 0x7F)[active]
    assert regs[0] == 0x0E and regs[20] == 0x7F and regs[45] == 0x80
    assert regs[44] == 0 and regs[46] == 0, "Final command must be complete (CE/CMD cleared)"

    errors = []
    source_unchanged = vram[0x28000:0x30000] == template
    if not source_unchanged:
        errors.append("The source atlas was modified or uploaded incorrectly")
    report = {
        "passed": False, "profile": profile, "hardware_validation": False,
        "requested_freeze_seconds": seconds, "settle_seconds": 0.15,
        "emulator_sha256": sha256(EXE.read_bytes()),
        "rom_sha256": sha256((ROOT / f"outputs/LUMEN_FORGE-V9968-{profile}.rom").read_bytes()),
        "reference": {"commit": COMMIT, "source": SOURCE,
                      "functions": ["startLrmmHs", "executeLrmmHs", "Graphic4Mode::addressOf", "Graphic4Mode::point"],
                      "rounding": "signed division truncates toward zero; inclusive source window; COL=0; IMP"},
        "frame_identification": {"FRAME_exact_record": presented, "next_frame_index": index,
                                 "active_atlas": hex(regs[6] << 11),
                                 "method": "FRAME and SAT equality with motion records, independent of transformed pixels"},
        "source_atlas_unchanged": source_unchanged, "atlases": [], "background_pages": [],
        "snapshot_sha256": {name: sha256((work / name).read_bytes()) for name in
                            ("vram.bin", "registers.bin", "frame.bin", "frame-index.bin")},
    }
    for page, (base, sat) in enumerate(((0x38000, 0x7000), (0x3C000, 0x7200))):
        attributes = vram[sat:sat + 112]
        found = [n for n, record in enumerate(records) if record[8:120] == attributes]
        # Quantized SAT positions can repeat on adjacent frames. FRAME is unique;
        # the alternating page protocol determines the preceding inactive frame.
        # Verify that record against SAT without selecting it by image similarity.
        number = presented if page == active else (presented - 1) % FRAME_COUNT
        assert number in found, f"SAT at {sat:#x} disagrees with frame {number}: {found}"
        assert vram[sat + 112:sat + 120] == bytes([216]) + bytes(7)
        assert vram[sat:sat + 120] == vram[sat + 0x10000:sat + 0x10000 + 120]
        atlas = {"physical_base": hex(base), "active": page == active, "SAT_record": number,
                 "records_with_identical_SAT": found,
                 "SAT_duplicate_plane_exact": True, "transforms": {}}
        for name, offset, size, dx, window in (
            ("primary", 0, 128, 0, (0, 1280, 127, 1407)),
            ("secondary", 128, 64, 128, (128, 1280, 191, 1343)),
        ):
            vector = struct.unpack_from("<hhhh", records[number], offset)
            expected, outside = reference(template, vector, size, size, window)
            actual = bytes(pixel4(vram, base, dx + x, y) for y in range(size) for x in range(size))
            original = bytes(pixel4(template, 0, dx + x, y) for y in range(size) for x in range(size))
            mismatch = [n for n, (a, e) in enumerate(zip(actual, expected)) if a != e]
            changed = sum(a != b for a, b in zip(actual, original))
            outside_zero = all(actual[n] == 0 for n in outside)
            packed_actual = bytes((actual[n] << 4) | actual[n + 1] for n in range(0, len(actual), 2))
            packed_expected = bytes((expected[n] << 4) | expected[n + 1] for n in range(0, len(expected), 2))
            result = {"size": [size, size], "SX_SY_VX_VY": list(vector), "pixels": len(actual),
                      "exact_pixels": len(actual) - len(mismatch), "mismatches": len(mismatch),
                      "packed_bytes_exact": packed_actual == packed_expected,
                      "outside_source_window_pixels": len(outside), "outside_pixels_all_zero": outside_zero,
                      "pixels_different_from_unrotated_template": changed,
                      "first_mismatches": [{"x": n % size, "y": n // size,
                                             "actual": actual[n], "expected": expected[n]} for n in mismatch[:8]]}
            atlas["transforms"][name] = result
            if mismatch or not outside_zero or not outside or not changed or vector[3] == 0:
                errors.append(f"{base:#x} {name}: transform or nontrivial-rotation check failed")
        static = [(x, y) for y in range(128) for x in range(128, 256)
                  if not (x < 192 and y < 64)]
        static_errors = sum(pixel4(vram, base, x, y) != pixel4(template, 0, x, y) for x, y in static)
        atlas["static_area"] = {"pixels": len(static), "mismatches": static_errors,
                                 "includes_both_particle_patterns": True}
        if static_errors:
            errors.append(f"{base:#x}: static particle area changed")
        report["atlases"].append(atlas)

    for page in (0, 1):
        actual = bytes(vram[((x & 1) << 16) | (((y + page * 256) & 511) << 7) | (x >> 1)]
                       for y in range(212) for x in range(256))
        expected = background[:256 * 212]
        mismatches = sum(a != b for a, b in zip(actual, expected))
        report["background_pages"].append({"page": page, "pixels": len(actual), "mismatches": mismatches,
                                            "actual_sha256": sha256(actual), "source_sha256": sha256(expected)})
        if mismatches:
            errors.append(f"Background page {page} differs from the original")
    report["errors"] = errors
    report["passed"] = not errors
    output = ROOT / f"outputs/transform-verification-{profile}.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    if errors:
        raise AssertionError("; ".join(errors))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("legacy-openmsx-internal", "legacy-openmsx"),
                        default="legacy-openmsx-internal")
    parser.add_argument("--seconds", type=float, default=10)
    parser.add_argument("--analyze-only", action="store_true", help="Recheck this profile's existing snapshot")
    args = parser.parse_args()
    if args.seconds <= 0:
        parser.error("--seconds must be positive")
    work = ROOT / f"work/transform-{args.profile}"
    work.mkdir(parents=True, exist_ok=True)
    if not args.analyze_only:
        capture(args.profile, args.seconds, work)
    analyze(args.profile, args.seconds, work)


if __name__ == "__main__":
    main()
