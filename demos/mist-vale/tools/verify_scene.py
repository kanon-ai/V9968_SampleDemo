"""Check actual SCREEN8 tree compositing, raster writes, and optional fog mixing.

The command reference reads shipped source assets and motion records, never the
rendered destination. Debugger breakpoints observe R27 *after* ISR writes and
record the VDP's actual beam position. No ROM file or external emulator is changed.
"""
import argparse
import csv
import hashlib
import io
import json
import os
import re
import struct
import subprocess
from collections import defaultdict

from run_check import EXE, ROOT


def digest(data):
    return hashlib.sha256(data).hexdigest()


def symbols(profile):
    text = (ROOT / f"work/build/demo-{profile}.symbols").read_text()
    return {name: int(value, 16) for name, value in
            re.findall(r"(?m)^(\w+)\s+EQU 0([0-9A-F]+)H", text)}


def run_private(script, profile, timeout):
    """Do not race the recording harness's work/emulator/check.tcl."""
    work = ROOT / f"work/scene-{profile}-emulator"
    work.mkdir(parents=True, exist_ok=True)
    error = work / "check-error.txt"
    error.unlink(missing_ok=True)
    guarded = ('if {[catch {\n' + script + '\n} err opts]} {'
               'set f [open check-error.txt w]; puts $f $err; puts $f $opts; close $f; exit}\n')
    (work / "scene-check.tcl").write_text(guarded, encoding="utf-8")
    env = os.environ.copy()
    env.update(OPENMSX_SYSTEM_DATA=os.environ.get("OPENMSX_SYSTEM_DATA", str(EXE.parent / "share")),
               OPENMSX_HOME="./home", OPENMSX_USER_DATA=str(ROOT / "work/emulator/user"))
    args = [str(EXE), "-machine", "Panasonic_FS-A1ST_V9968" if profile.endswith("internal") else "Panasonic_FS-A1ST"]
    if not profile.endswith("internal"):
        args += ["-ext", "HRA_V9968"]
    args += ["-cart", f"../../outputs/MIST_VALE-V9968-{profile}.rom", "-romtype", "ASCII8", "-script", "scene-check.tcl"]
    result = subprocess.run(args, cwd=work, env=env, timeout=timeout, creationflags=subprocess.CREATE_NO_WINDOW)
    if error.exists():
        raise RuntimeError(error.read_text())
    if result.returncode:
        raise RuntimeError(f"openMSX returned {result.returncode}")


def address8(x, y):
    return ((x & 1) << 16) | ((y & 511) << 7) | ((x & 255) >> 1) | ((y & 512) << 8)


def display_page(r2):
    # Pinned d884 SDLRasterizer::drawDisplay / SCREEN8 scanout, not the command
    # engine address mapping: vramLine = ((R2 << 10 | 0x3ff) >> 7) & (0x100 | Y).
    # Thus bit 5 selects the displayed 256-line page. 3Fh and 7Fh both select 1!
    return (((r2 << 10) | 0x3FF) >> 7 & 0x100) >> 8


def bitmap(vram, y0, height=212):
    return bytes(vram[address8(x, y0 + y)] for y in range(height) for x in range(256))


def compose(source, record):
    """LMMM TIMP in Graphic7: copy a nonzero source byte, preserve zero holes.

    The fixed background is the initial state. The runtime restores Y48..143,
    copies four ground segments, then the five trees. With unchanged
    pixels above48 and below172, and opaque ground fully replacing Y144..171,
    this reference does not depend on prior frames.
    """
    result = bytearray(bitmap(source, 512))
    copied = transparent = 0
    commands = []
    ground = {"commands": [], "nonzero_source_writes": 0, "transparent_source_skips": 0}
    ground_coverage = [0] * (256 * 36)
    exposed_ground = set()
    for layer, offsets in (("ground", (180, 195, 210, 225)), ("trees", range(0, 75, 15))):
        for offset in offsets:
            sx, sy, dx, dy, nx, ny, color, arg, command = struct.unpack_from("<6H3B", record, offset)
            if nx == 0:
                continue  # The runtime explicitly skips NX=0, unlike the VDP itself.
            assert command in (0x98, 0xD0) and arg == 0, "Expected forward SCREEN8 copy"
            assert nx > 0 and ny > 0 and 0 <= sx < 256 and 0 <= dx < 256
            assert sx + nx <= 256 and dx + nx <= 256, "Unexpected horizontal command clipping"
            descriptor = {"SX": sx, "SY": sy, "DX": dx, "DY": dy, "NX": nx, "NY": ny}
            if layer == "ground":
                assert (sy, dy, ny, command) in ((724, 136, 8, 0x98), (732, 144, 28, 0xD0))
                ground["commands"].append(descriptor)
                for y in range(dy, dy + ny):
                    for x in range(dx, dx + nx):
                        ground_coverage[(y - 136) * 256 + x] += 1
            else:
                assert command == 0x98, "Tree holes require transparent copying"
                assert 768 <= sy and sy + ny <= 864 and 40 <= dy and dy + ny <= 168
                commands.append(descriptor)
            for y in range(ny):
                for x in range(nx):
                    value = source[address8(sx + x, sy + y)]
                    position = (dy + y) * 256 + dx + x
                    if command == 0xD0:
                        assert value != 0, "Fast ground copy must be entirely opaque"
                    if value or command == 0xD0:
                        result[position] = value
                        copied += 1
                        if layer == "ground":
                            exposed_ground.add(position)
                            ground["nonzero_source_writes"] += 1
                        else:
                            exposed_ground.discard(position)
                    else:
                        transparent += 1
                        if layer == "ground":
                            ground["transparent_source_skips"] += 1
    assert ground_coverage == [1] * (256 * 36), "Ground copies do not cover each display pixel exactly once"
    assert ground["nonzero_source_writes"] and exposed_ground, "Ground must produce visible foreground pixels"
    ground["unoccluded_ground_pixels"] = len(exposed_ground)
    ground["screen_columns_covered_exactly_once"] = True
    ground["screen_pixels_covered_exactly_once"] = 256 * 36
    assert commands and copied and transparent, "The captured tree frame must exercise both copy and transparency"
    return bytes(result), {"commands": commands, "ground": ground, "nonzero_source_writes": copied,
                           "transparent_source_skips": transparent}


def capture(profile, seconds, alpha, work):
    sym = symbols(profile)
    required = ("main_loop", "FRAME", "frame_index", "raster_scroll_written",
                "irq_blank_scroll_written", "raster_index", "raster_phase",
                "irq_counts", "vblank_counts", "raster_counts", "raster_offsets")
    missing = [name for name in required if name not in sym]
    if missing:
        raise ValueError(f"Runtime observation labels missing: {missing}")
    # Labels are optional in older builds. The fallbacks are immediately after
    # R2's CALL reg_write and the final command OTIR; validate their opcodes.
    runtime = (ROOT / f"work/build/demo-{profile}.bin").read_bytes()
    present_hook = sym.get("present_page_written", sym["present_page0"] + 5)
    command_hook = sym.get("page_command_started", sym["issue_initial_copy"] - 1)
    assert runtime[present_hook - 0x8000] == 0x3A and runtime[command_hook - 0x8000] == 0xC9
    vdp = "VDP" if profile.endswith("internal") else "V9968"
    physical = "physical VRAM" if profile.endswith("internal") else "physical V9968 VRAM"
    template = r'''
set save_settings_on_exit false
set throttle __THROTTLE__
set speed 100
set renderer SDLGL-PP
set minframeskip 0
set maxframeskip 0
set scanline 0
set blur 0
set deinterlace true
__VIDEOSELECT__
set ::scene_trace 0
set ::scene_events "kind,time,frame,y,x,r27,r19,step,phase,irq,vblank,raster\n"
set ::scene_scanout "kind,time,y,x,r2,draw,frame,cmd,dy\n"
proc word {addr} {expr {[debug read memory $addr] + 256*[debug read memory [expr {$addr+1}]]}}
proc save_binary {name data} {
    set f [open "__WORK__/$name" wb]
    puts -nonewline $f $data
    close $f
}
proc failed {err opts} {
    set f [open check-error.txt w]
    puts $f $err
    puts $f $opts
    close $f
    exit
}
proc state_snapshot {tag} {
    save_binary $tag-vram.bin [debug read_block {__PHYSICAL__} 0 262144]
    save_binary $tag-registers.bin [debug read_block {__VDP__ regs} 0 64]
    save_binary $tag-frame.bin [debug read_block memory __FRAME__ 256]
    save_binary $tag-index.bin [debug read_block memory __frame_index__ 2]
    set f [open "__WORK__/$tag-cpu.txt" w]
    puts $f "PC=[reg PC] SP=[reg SP] loop=[binary encode hex [debug read_block memory __main_loop__ 2]]"
    close $f
}
proc raster_event {kind} {
    if {!$::scene_trace} {return}
    if {[catch {
        append ::scene_events "$kind,[machine_info time],[machine_info __VDP___frame_count],[machine_info __VDP___msx_y_pos],[machine_info __VDP___msx_x256_pos],[debug read {__VDP__ regs} 27],[debug read {__VDP__ regs} 19],[debug read memory __raster_index__],[debug read memory __raster_phase__],[word __irq_counts__],[word __vblank_counts__],[word __raster_counts__]\n"
    } err opts]} {failed $err $opts}
}
proc scanout_event {kind} {
    if {!$::scene_trace} {return}
    if {[catch {
        append ::scene_scanout "$kind,[machine_info time],[machine_info __VDP___msx_y_pos],[machine_info __VDP___msx_x256_pos],[debug read {__VDP__ regs} 2],[debug read memory __draw_page__],[word __frame_index__],[debug read {__VDP__ regs} 46],[expr {[debug read {__VDP__ regs} 38]+256*[debug read {__VDP__ regs} 39]}]\n"
    } err opts]} {failed $err $opts}
}
debug set_bp __raster_scroll_written__ {} {raster_event water}
debug set_bp __irq_blank_scroll_written__ {} {raster_event blank}
debug set_bp __PRESENT_HOOK__ {} {scanout_event present}
debug set_bp __COMMAND_HOOK__ {} {scanout_event command}
proc freeze_scene {} {
    if {[catch {
        debug write memory __main_loop__ 24
        debug write memory __MAINNEXT__ 254
        after time 0.15 capture_scene
    } err opts]} {failed $err $opts}
}
proc capture_scene {} {
    if {[catch {
        set ::scene_trace 0
        save_binary vram.bin [debug read_block {__PHYSICAL__} 0 262144]
        save_binary registers.bin [debug read_block {__VDP__ regs} 0 64]
        save_binary frame.bin [debug read_block memory __FRAME__ 256]
        save_binary frame-index.bin [debug read_block memory __frame_index__ 2]
        save_binary patched-loop.bin [debug read_block memory __main_loop__ 2]
        save_binary raster-offsets.bin [debug read_block memory __raster_offsets__ 352]
        save_binary counters.bin "[debug read_block memory __irq_counts__ 2][debug read_block memory __vblank_counts__ 2][debug read_block memory __raster_counts__ 2]"
        set f [open "__WORK__/raster-events.csv" w]
        puts -nonewline $f $::scene_events
        close $f
        set f [open "__WORK__/scanout-events.csv" w]
        puts -nonewline $f $::scene_scanout
        close $f
        if {__ALPHA__} {
            state_snapshot full
            openmsx::internal_screenshot -raw __WORK__/full.png
            debug write {__VDP__ regs} 8 [expr {[debug read {__VDP__ regs} 8] | 2}]
            after time 0.10 capture_background
        } else {exit}
    } err opts]} {failed $err $opts}
}
proc capture_background {} {
    if {[catch {
        state_snapshot background
        openmsx::internal_screenshot -raw __WORK__/background.png
        foreach base {28672 29184} {
            for {set i 0} {$i<12} {incr i} {
                set addr [expr {$base+$i*8+3}]
                debug write {__PHYSICAL__} $addr [expr {[debug read {__PHYSICAL__} $addr]&63}]
            }
        }
        debug write {__VDP__ regs} 8 [expr {[debug read {__VDP__ regs} 8] & 253}]
        after time 0.10 capture_opaque
    } err opts]} {failed $err $opts}
}
proc capture_opaque {} {
    if {[catch {state_snapshot opaque; openmsx::internal_screenshot -raw __WORK__/opaque.png} err opts]} {failed $err $opts}
    exit
}
after time __TRACE_START__ {set ::scene_trace 1}
after time __SECONDS__ freeze_scene
'''
    values = {name: value for name, value in sym.items()}
    values.update(VDP=vdp, PHYSICAL=physical, WORK="../" + work.name,
                  MAINNEXT=sym["main_loop"] + 1, SECONDS=seconds,
                  PRESENT_HOOK=present_hook, COMMAND_HOOK=command_hook,
                  TRACE_START=max(0, seconds - 0.5), ALPHA=int(alpha), THROTTLE="true" if alpha else "false",
                  VIDEOSELECT="" if vdp == "VDP" else "after time 1 {set videosource V9968}")
    for key, value in values.items():
        template = template.replace(f"__{key}__", str(value))
    assert not re.search(r"__\w+__", template), "Unexpanded Tcl placeholder"
    rom = next((ROOT / "outputs").glob(f"*-V9968-{profile}.rom"))
    manifest = {"profile": profile, "rom_sha256": digest(rom.read_bytes()),
                "emulator_sha256": digest(EXE.read_bytes()), "seconds": seconds,
                "alpha": alpha, "throttle": alpha,
                "assets": {name: digest((ROOT / "assets" / name).read_bytes())
                           for name in ("vram-upload.bin", "motion.bin")}}
    (work / "capture-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (ROOT / f"outputs/scene-verification-{profile}.json").unlink(missing_ok=True)
    run_private(template, profile, timeout=max(90, seconds * 5))


def scanout_report(path):
    events = list(csv.DictReader(io.StringIO(path.read_text())))
    for event in events:
        for key in ("y", "x", "r2", "draw", "frame", "cmd", "dy"):
            event[key] = int(event[key])
    commands = [event for event in events if event["kind"] == "command"]
    presents = [event for event in events if event["kind"] == "present"]
    visible_writes = [e for e in commands if display_page(e["r2"]) == ((e["dy"] >> 8) & 1)]
    wrong_presents = [e for e in presents if display_page(e["r2"]) != e["draw"]]
    unfinished = [e for e in presents if e["cmd"] != 0]
    active_presents = [e for e in presents if 0 <= e["y"] < 212]
    pages = sorted({display_page(e["r2"]) for e in presents})
    passed = (len(commands) >= 20 and len(presents) >= 5 and pages == [0, 1]
              and not visible_writes and not wrong_presents and not unfinished and not active_presents)
    return {"passed": passed, "command_events": len(commands), "presentation_events": len(presents),
            "visible_display_pages": pages, "writes_to_visible_page": len(visible_writes),
            "wrong_display_page_presentations": len(wrong_presents),
            "unfinished_command_presentations": len(unfinished), "active_scan_presentations": len(active_presents),
            "first_visible_page_writes": visible_writes[:3], "first_wrong_presentations": wrong_presents[:3],
            "page_oracle": "d884 SDLRasterizer SCREEN8: (((R2<<10)|0x3ff)>>7)&(0x100|displayY); bit5 selects page",
            "reference": "https://github.com/buppu3/openMSX/blob/d884c4b29d7e736d6e488aca5f28e124a410c19f/src/video/SDLRasterizer.cc",
            "event_log_sha256": digest(path.read_bytes())}


def raster_report(work):
    offsets = (work / "raster-offsets.bin").read_bytes()
    assert len(offsets) == 352 and all(value <= 4 for value in offsets)
    events = list(csv.DictReader(io.StringIO((work / "raster-events.csv").read_text())))
    assert events, "No actual R27 write events observed"
    frames = defaultdict(list)
    for event in events:
        for field in ("frame", "y", "x", "r27", "r19", "step", "phase", "irq", "vblank", "raster"):
            event[field] = int(event[field])
        frames[event["frame"]].append(event)
    water = [event for event in events if event["kind"] == "water"]
    blank = [event for event in events if event["kind"] == "blank"]
    assert water and blank, "Both the raster ISR and VBlank reset must execute"
    assert all(event["r27"] == 0 for event in blank), "R27 was not reset at VBlank"
    assert all(not (0 <= event["y"] < 212) for event in blank), "VBlank reset occurred in the visible picture"
    mismatches = []
    top_intrusions = []
    for event in water:
        phase, step = event["phase"], event["step"]
        if not (0 <= phase < 32 and 0 <= step < 11 and event["r27"] == offsets[phase * 11 + step]):
            mismatches.append(event)
        # A write after the right edge affects the following scanline. A write
        # during/just before visible pixels affects this scanline instead.
        affected_y = event["y"] + (event["x"] >= 256)
        if event["r27"] and 0 <= affected_y < 172:
            top_intrusions.append(event)
    assert not mismatches, f"R27 differs from the scheduled phase/step: {mismatches[:3]}"
    assert not top_intrusions, f"Nonzero fine scroll escaped the water region: {top_intrusions[:3]}"
    assert all(171 <= event["y"] <= 211 or
               (event["step"] == 10 and event["r27"] == 0 and event["y"] in (212, 213))
               for event in water), "Raster handler ran outside the water/end boundary"
    complete = [group for group in frames.values()
                if {e["step"] for e in group if e["kind"] == "water"} == set(range(11))]
    assert len(complete) >= 5, "Need at least five complete raster sequences"
    assert len({event["r27"] for event in water}) > 1 and any(event["r27"] for event in water)
    # Each completed sequence must follow the eleven consecutive R19 positions.
    for group in complete:
        rows = [event for event in group if event["kind"] == "water"]
        assert [event["step"] for event in rows] == list(range(11))
        assert [event["r19"] for event in rows] == list(range(171, 212, 4))
    return {"actual_register_writes_observed": True, "events": len(events),
            "water_writes": len(water), "blank_resets": len(blank),
            "complete_eleven_step_frames": len(complete),
            "observed_values": sorted({event["r27"] for event in water}),
            "beam_y_range": [min(e["y"] for e in water), max(e["y"] for e in water)],
            "scheduled_values_exact": True, "nonzero_scroll_in_top_region": 0,
            "source": "post-write ISR breakpoints: actual R27, beam X/Y, VDP frame, R19, phase and step",
            "event_log_sha256": digest((work / "raster-events.csv").read_bytes())}


def fog_report(work, vram, regs, sat):
    from PIL import Image
    full, bg, opaque = [Image.open(work / name).convert("RGB")
                        for name in ("full.png", "background.png", "opaque.png")]
    assert full.size == bg.size == opaque.size == (320, 240)
    # d884's sprite origin is one pixel to the right of the bitmap's left edge.
    # In this 320-wide raw output sprite X255 falls at X288, beyond the bitmap's
    # right clipping edge. Keep this real clipping separate from image alignment.
    ox, oy = 33, 15
    sprite_left = 8 if regs[25] & 2 else 0  # R25.MSK extends the left border.
    base = (regs[6] & 127) << 11
    occupied = set()
    results = defaultdict(lambda: {"pixels": 0, "exact_rgb5_mix": 0})
    for n in range(12):
        attr = vram[sat + n * 8:sat + (n + 1) * 8]
        x, y = attr[4] | ((attr[5] & 3) << 8), attr[0] | ((attr[1] & 3) << 8)
        x = x - 1024 if x & 512 else x
        y = y - 1024 if y & 512 else y
        width, height = attr[6] or 256, attr[2] or 256
        source_height, tp = 16 << (attr[1] >> 6), attr[3] >> 6
        px, py = (attr[7] & 15) * 16, (attr[7] >> 4) * 16 + ((attr[5] >> 4) & 7) * 256
        assert tp in (2, 3), "Expected TP2/TP3 fog"
        for dy in range(height):
            yy = y + dy
            if not 0 <= yy < 212:
                continue
            for dx in range(width):
                xx = x + dx
                if not sprite_left <= xx < 255 or (xx, yy) in occupied:
                    continue
                tx = px + 16 * (width - 1 - dx if attr[3] & 16 else dx) // width
                ty = py + source_height * (height - 1 - dy if attr[3] & 32 else dy) // height
                value = vram[base + ty * 128 + tx // 2]
                color = (value >> 4) if tx % 2 == 0 else (value & 15)
                if not color:
                    continue
                occupied.add((xx, yy))
                source = tuple(c >> 3 for c in opaque.getpixel((xx + ox, yy + oy)))
                dest = tuple(c >> 3 for c in bg.getpixel((xx + ox, yy + oy)))
                mixed = tuple((s + d) >> 1 if tp == 2 else (s + 3 * d) >> 2 for s, d in zip(source, dest))
                expected = tuple((c << 3) | (c >> 2) for c in mixed)
                results[tp]["pixels"] += 1
                results[tp]["exact_rgb5_mix"] += full.getpixel((xx + ox, yy + oy)) == expected
    # Raster IRQ latency changes a few pixels on water band boundaries even with
    # fixed phase/VRAM. This snapshot's fog is entirely above those raster lines;
    # require that explicitly instead of silently ignoring overlapping fog.
    assert all(y < 171 for x, y in occupied), "Fog overlaps the live raster region; choose another capture time"
    observed = {(x, y) for y in range(171) for x in range(sprite_left, 255)
                if opaque.getpixel((x + ox, y + oy)) != bg.getpixel((x + ox, y + oy))}
    assert occupied == observed, "Fog mask differs from the actual opaque/background difference"
    assert results and all(value["pixels"] == value["exact_rgb5_mix"] for value in results.values())
    return {"observed_coverage_exact": True, "frozen_background_comparison": True,
            "samples": dict(results), "raw_capture_origin": [ox, oy],
            "left_border_mask_pixels": sprite_left,
            "sprite_right_edge_clips_X255": True, "fog_entirely_above_live_raster": True,
            "image_comparison_Y_range": [0, 170], "raster_verified_separately": True}


def analyze(profile, work, alpha=False):
    vram = (work / "vram.bin").read_bytes()
    regs = (work / "registers.bin").read_bytes()
    frame = (work / "frame.bin").read_bytes()
    next_index = int.from_bytes((work / "frame-index.bin").read_bytes(), "little")
    upload = (ROOT / "assets/vram-upload.bin").read_bytes()
    motion = (ROOT / "assets/motion.bin").read_bytes()
    manifest_path = work / "capture-manifest.json"
    manifest = json.loads(manifest_path.read_text()) if manifest_path.exists() else None
    if manifest:
        assert manifest["profile"] == profile
        assert all(digest((ROOT / "assets" / name).read_bytes()) == sha
                   for name, sha in manifest["assets"].items()), "Assets changed since capture; rerun the emulator"
        assert not alpha or manifest["alpha"], "This snapshot has no synchronized alpha captures"
    assert len(vram) == 262144 and len(upload) == 131072 and len(motion) == 262144
    assert (work / "patched-loop.bin").read_bytes() == b"\x18\xfe"
    source = bytes(131072) + upload
    assert vram[0x20000:] == upload, "Source background, trees or fog atlas was modified"
    records = [motion[n:n + 256] for n in range(0, len(motion), 256)]
    number = (next_index - 1) % 1024
    assert frame == records[number], "FRAME and frame_index disagree after presentation"
    assert regs[5] in (0xC3, 0xCB) and regs[6] == 0x58
    active = display_page(regs[2])
    assert regs[5] == (0xC3, 0xCB)[active]
    report = {"passed": False, "profile": profile, "hardware_validation": False,
              "emulator_sha256": manifest["emulator_sha256"] if manifest else digest(EXE.read_bytes()),
              "rom_sha256": manifest["rom_sha256"] if manifest else digest(next((ROOT / "outputs").glob(f"*-V9968-{profile}.rom")).read_bytes()),
              "FRAME_record": number, "next_frame_index": next_index,
              "source_128KiB_unchanged": True, "background_pages": [],
              "reference": "SCREEN8 mapping, LMMM TIMP (zero skips) and opaque ground HMMM",
              "raster": raster_report(work), "scanout": scanout_report(work / "scanout-events.csv")}
    original = bitmap(source, 512)
    for page, sat in enumerate((0x7000, 0x7200)):
        record_number = number if page == active else (number - 1) % 1024
        record = records[record_number]
        assert vram[sat:sat + 96] == record[80:176], "SAT differs from its presented motion record"
        assert vram[sat + 96:sat + 104] == bytes([216]) + bytes(7)
        assert vram[sat:sat + 104] == vram[sat + 0x10000:sat + 0x10000 + 104]
        expected, details = compose(source, record)
        actual = bitmap(vram, page * 256)
        mismatches = [i for i, (a, e) in enumerate(zip(actual, expected)) if a != e]
        fixed_ranges = ((0, 48), (172, 212))
        fixed_exact = all(actual[a * 256:b * 256] == original[a * 256:b * 256] for a, b in fixed_ranges)
        details["ground"]["pixels_compared"] = 256 * 36
        details["ground"]["pixel_mismatches"] = sum(
            actual[n] != expected[n] for n in range(136 * 256, 172 * 256))
        result = {"page": page, "active": page == active, "record": record_number,
                  "pixels": len(actual), "mismatches": len(mismatches),
                  "first_mismatches": [{"x": i % 256, "y": i // 256, "actual": actual[i],
                                         "expected": expected[i]} for i in mismatches[:8]],
                  "fixed_sky_and_water_VRAM_exact": fixed_exact, "SAT_duplicate_exact": True, **details}
        report["background_pages"].append(result)
    report["ground_composite"] = {
        "passed": all(page["ground"]["pixel_mismatches"] == 0 for page in report["background_pages"]),
        "pixels_compared": 2 * 256 * 36, "destination_Y_range": [136, 171],
        "source_Y_range": [724, 759], "composition_order": "fixed backdrop, ground TIMP/HMMM, tree TIMP, Sprite3 fog"}
    if alpha:
        report["fog"] = fog_report(work, vram, regs, (0x7000, 0x7200)[active])
    report["passed"] = report["scanout"]["passed"] and all(
        not p["mismatches"] and p["fixed_sky_and_water_VRAM_exact"] for p in report["background_pages"])
    output = ROOT / f"outputs/scene-verification-{profile}.json"
    output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    assert report["passed"], "Moving scanout or independent tree composite check failed"
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=("legacy-openmsx-internal", "legacy-openmsx"), default="legacy-openmsx-internal")
    parser.add_argument("--seconds", type=float, default=10)
    parser.add_argument("--alpha", action="store_true", help="Also capture and compare actual TP2/TP3 fog pixels")
    parser.add_argument("--analyze-only", action="store_true")
    args = parser.parse_args()
    if args.seconds <= 0.5:
        parser.error("--seconds must exceed 0.5")
    work = ROOT / f"work/scene-{args.profile}"
    work.mkdir(parents=True, exist_ok=True)
    if not args.analyze_only:
        capture(args.profile, args.seconds, args.alpha, work)
    analyze(args.profile, work, args.alpha)


if __name__ == "__main__":
    main()
