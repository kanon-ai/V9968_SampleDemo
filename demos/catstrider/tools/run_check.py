"""Run only a private CATSTRIDER emulator child, using external user BIOS.

CLI screenshot times and duration are relative to the first presentation.
Every invocation keeps its Tcl, settings, event logs and media in a unique
work/emulator/run-* directory. No emulator or BIOS is copied into the project.
"""
from pathlib import Path
import argparse
import csv
import hashlib
import json
import os
import re
import struct
import subprocess
import tempfile

ROOT = Path(__file__).resolve().parents[1]
EXE = Path(os.environ.get("OPENMSX_EXE", "C:/Program Files/openMSX/openmsx.exe"))
PROFILES = ("legacy-openmsx-internal", "legacy-openmsx")


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def symbols(profile):
    source = (ROOT / f"work/build/demo-{profile}.symbols").read_text()
    return {name: int(value, 16) for name, value in re.findall(r"(?m)^(\w+)\s+EQU 0([0-9A-F]+)H", source)}


def user_data():
    """Existing configuration is a read-only input; never bundle its ROMs."""
    override = os.environ.get("OPENMSX_USER_DATA")
    if override:
        return str(Path(override).resolve())
    candidates = (Path.home() / "Documents/openMSX/share",
                  ROOT.parent / "v9968-mist-demo/work/emulator/user")
    return str(next((p for p in candidates if (p / "extensions/HRA_V9968.xml").exists()), candidates[0]))


def run(script, profile="legacy-openmsx-internal", timeout=180):
    """Return the private output directory. Script paths are relative to it."""
    if profile not in PROFILES:
        raise ValueError(f"Unsupported profile: {profile}")
    rom = ROOT / f"outputs/CATSTRIDER-V9968-{profile}.rom"
    if not EXE.is_file() or not rom.is_file():
        raise FileNotFoundError("Build the ROM and select an installed V9968 openMSX with OPENMSX_EXE")
    base = ROOT / "work/emulator"
    base.mkdir(parents=True, exist_ok=True)
    work = Path(tempfile.mkdtemp(prefix=f"run-{profile}-", dir=base))
    (work / "home").mkdir()
    (work / "settings.xml").write_text("<!DOCTYPE settings SYSTEM 'settings.dtd'>\n"
                                       "<settings><settings/><bindings/><shortcuts/></settings>\n", encoding="utf-8")
    guarded = ('if {[catch {\n' + script + '\n} err opts]} {\n'
               'set f [open check-error.txt w]; puts $f $err; puts $f $opts; close $f; exit\n}\n')
    (work / "check.tcl").write_text(guarded, encoding="utf-8")
    env = os.environ.copy()
    env.update(OPENMSX_SYSTEM_DATA=os.environ.get("OPENMSX_SYSTEM_DATA", str(EXE.parent / "share")),
               OPENMSX_HOME=str(work / "home"), OPENMSX_USER_DATA=user_data())
    args = [str(EXE), "-machine", "Panasonic_FS-A1ST_V9968" if profile.endswith("internal") else "Panasonic_FS-A1ST"]
    if not profile.endswith("internal"):
        args += ["-ext", "HRA_V9968"]
    args += ["-cart", os.path.relpath(rom, work).replace("\\", "/"), "-romtype", "ASCII8",
             "-setting", "settings.xml", "-script", "check.tcl"]
    manifest = {"profile": profile, "rom_sha256": sha256(rom), "emulator_sha256": sha256(EXE)}
    (work / "invocation.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    result = subprocess.run(args, cwd=work, env=env, timeout=timeout,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    error = work / "check-error.txt"
    if error.exists():
        raise RuntimeError(f"{work}: {error.read_text()}")
    if result.returncode:
        raise RuntimeError(f"openMSX returned {result.returncode}; diagnostics: {work}")
    assert sha256(rom) == manifest["rom_sha256"], "ROM changed during capture"
    return work


def capture_script(profile, seconds, screenshots, avi):
    sym = symbols(profile)
    vdp = "VDP" if profile.endswith("internal") else "V9968"
    text = r'''
set save_settings_on_exit false
set throttle true
set speed 100
set minframeskip 0
set maxframeskip 0
set renderer SDLGL-PP
set scale_factor 2
set scanline 0
set blur 0
set deinterlace true
__VIDEO__
set ::started 0
set ::finished 0
set ::avi __AVI__
set ::present_file [open presentations.csv w]
puts $::present_file "time,vdpf,frame,vblank,y,x,r2,draw,r20,s2,s1990,scene,hero,r25"
set ::command_file [open commands.csv w]
puts $::command_file "time,vdpf,frame,y,r2,draw,s2,cmd,dx,dy,nx,ny,vx,sx"
proc word {address} {expr {[debug read memory $address] + 256 * [debug read memory [expr {$address+1}]]}}
proc regword {address} {expr {[debug read {__VDP__ regs} $address] + 256 * [debug read {__VDP__ regs} [expr {$address+1}]]}}
proc fail {err opts} {
    set f [open check-error.txt w]; puts $f $err; puts $f $opts; close $f
    catch {record stop}; exit
}
proc snapshot {name} {
    if {[catch {openmsx::internal_screenshot -raw "./$name.png"} err opts]} {fail $err $opts}
}
proc present {} {
    if {[catch {
        puts $::present_file "[machine_info time],[machine_info __VDP___frame_count],[word __FRAME__],[word __VB__],[machine_info __VDP___msx_y_pos],[machine_info __VDP___msx_x256_pos],[debug read {__VDP__ regs} 2],[debug read memory __DRAW__],[debug read {__VDP__ regs} 20],[debug read {__VDP__ status regs} 2],[debug read {S1990 regs} 6],[debug read memory __SCENE__],[debug read memory __HERO__],[debug read {__VDP__ regs} 25]"
        if {!$::started} {
            set ::started 1
            if {$::avi} {record start ./CATSTRIDER-native.avi}
            __SHOTS__
            after time __SECONDS__ finish
        }
    } err opts]} {fail $err $opts}
}
proc command {} {
    if {[catch {
        puts $::command_file "[machine_info time],[machine_info __VDP___frame_count],[word __FRAME__],[machine_info __VDP___msx_y_pos],[debug read {__VDP__ regs} 2],[debug read memory __DRAW__],[debug read {__VDP__ status regs} 2],[debug read {__VDP__ regs} 46],[regword 36],[regword 38],[regword 40],[regword 42],[regword 47],[regword 32]"
    } err opts]} {fail $err $opts}
}
proc finish {} {
    if {[catch {
        set ::finished 1
        if {$::avi} {record stop}
        snapshot final
        close $::present_file; close $::command_file
        set f [open state.txt w]
        puts $f "machine=[machine_info config_name]"
        puts $f "cpu=[binary encode hex [debug read_block {CPU regs} 0 28]]"
        puts $f "s1990=[binary encode hex [debug read_block {S1990 regs} 0 16]]"
        puts $f "regs=[binary encode hex [debug read_block {__VDP__ regs} 0 64]]"
        puts $f "status=[binary encode hex [debug read_block {__VDP__ status regs} 0 16]]"
        puts $f "frame=[word __FRAME__]"
        puts $f "vblank=[word __VB__]"
        puts $f "sat0=[binary encode hex [debug read_block {physical __VDP__ VRAM} 28672 136]]"
        puts $f "sat1=[binary encode hex [debug read_block {physical __VDP__ VRAM} 29184 136]]"
        close $f
        set f [open source-upload.bin wb]
        puts -nonewline $f [debug read_block {physical __VDP__ VRAM} 131072 98304]; close $f
        set f [open floor-geometry.bin wb]
        puts -nonewline $f [debug read_block memory __GEOMETRY__ 560]; close $f
        exit
    } err opts]} {fail $err $opts}
}
debug set_bp __PRESENT__ {} {present}
debug set_bp __COMMAND__ {} {command}
after time 20 {if {!$::started} {fail "No presentation within 20 seconds" {}}}
'''
    replacements = {"__VIDEO__": "" if vdp == "VDP" else "after time 1 {set videosource V9968}",
                    "__VDP__": vdp, "__AVI__": int(avi), "__SECONDS__": seconds,
                    "__FRAME__": sym["frame_index"], "__VB__": sym["vblank_counts"],
                    "__DRAW__": sym["draw_page"], "__SCENE__": sym["scene_id"], "__HERO__": sym["hero_flags"],
                    "__PRESENT__": sym["present_page_written"], "__COMMAND__": sym["floor_command_started"],
                    "__GEOMETRY__": sym["floor_geometry"],
                    "__SHOTS__": "\n            ".join(f'after time {t:.9f} {{snapshot stage-{t:06.2f}}}' for t in screenshots)}
    for key, value in replacements.items():
        text = text.replace(key, str(value))
    # Native debug name is "physical VRAM", while the cartridge includes V9968.
    return text.replace("physical VDP VRAM", "physical VRAM")


def rows(path):
    return [{key: float(value) if key == "time" else int(value) for key, value in row.items()}
            for row in csv.DictReader(path.open())]


def analyze(work, profile, seconds, avi):
    presentations = rows(work / "presentations.csv")
    commands = rows(work / "commands.csv")
    geometry_bytes = (work / "floor-geometry.bin").read_bytes()
    assert len(geometry_bytes) == 112 * 5, "Captured geometry must contain112 five-byte rows"
    geometry = [(sx, vx, dx, nx or 256) for sx, vx, dx, nx in struct.iter_unpack("<BHBB", geometry_bytes)]
    assert all(0 <= sx <= 63 and 16 <= vx <= 448 and 0 <= dx <= 4 and dx + nx == 256
               for sx, vx, dx, nx in geometry), "Loaded geometry has invalid bounds"
    geometry_rom_offset = 8192 + symbols(profile)["floor_geometry"] - 0x8000
    rom = (ROOT / f"outputs/CATSTRIDER-V9968-{profile}.rom").read_bytes()
    geometry_exact = rom[geometry_rom_offset:geometry_rom_offset + 560] == geometry_bytes
    assert len(presentations) >= 5, "Insufficient presentation events"
    deltas = [b["vdpf"] - a["vdpf"] for a, b in zip(presentations, presentations[1:])]
    steps = [(b["frame"] - a["frame"]) % 1536 for a, b in zip(presentations, presentations[1:])]
    # Initial page0 is prepared before the display is enabled. From the first
    # presentation onwards, every live LRMM must target the other page.
    live = [row for row in commands if row["time"] > presentations[0]["time"]]
    bad_writes = [r for r in live if ((r["r2"] >> 5) & 1) == (r["dy"] >> 8)]
    bad_present = [r for r in presentations if ((r["r2"] >> 5) & 1) != r["draw"]
                   or r["s2"] & 1 or not r["s2"] & 64 or 0 <= r["y"] < 212]
    command_shape = all(r["cmd"] == 0x30 and r["ny"] == 1 and (r["dy"] & 255) in range(100, 212)
                        and (r["dy"] >> 8) == r["draw"]
                        and (r["sx"], r["vx"], r["dx"], r["nx"]) == geometry[(r["dy"] & 255) - 100]
                        for r in commands)
    groups = []
    for row in commands:
        if (row["dy"] & 255) == 100:
            groups.append([])
        if groups:
            groups[-1].append(row["dy"] & 255)
    completed = groups[:-1]  # Last update may be partway through rendering.
    strips_exact = bool(completed) and all(g == list(range(100, 212)) for g in completed)
    upload_exact = (work / "source-upload.bin").read_bytes() == (ROOT / "assets/vram-upload.bin").read_bytes()
    state = dict(line.split("=", 1) for line in (work / "state.txt").read_text().splitlines())
    left_mask = all(r["r25"] & 2 for r in presentations) and bool(bytes.fromhex(state["regs"])[25] & 2)
    terminator = bytes([216, 0, 0, 0, 0, 0, 0, 0])
    sat_terminators = all(bytes.fromhex(state[name])[128:136] == terminator for name in ("sat0", "sat1"))
    stable_regs = all(r["r20"] == 0x7F and r["s1990"] & 0x60 == 0 for r in presentations)
    elapsed = presentations[-1]["time"] - presentations[0]["time"]
    report = {**json.loads((work / "invocation.json").read_text()), "passed": False,
              "hardware_tested": False, "stage_seconds": seconds,
              "presentations": len(presentations), "updates_per_second": round((len(presentations) - 1) / elapsed, 4),
              "presentation_vdp_frame_deltas": sorted(set(deltas)), "every_presentation_two_vblanks": all(d == 2 for d in deltas),
              "frame_indices_consecutive": all(step == 1 for step in steps),
              "loop_wrap_seen": any(b["frame"] < a["frame"] for a, b in zip(presentations, presentations[1:])),
              "command_events": len(commands), "complete_updates_with_112_strips": len(completed),
              "every_complete_update_112_strips": strips_exact, "lrmm_command_geometry_exact": command_shape,
              "loaded_floor_geometry_byte_exact": geometry_exact, "loaded_floor_geometry_sha256": sha256(work / "floor-geometry.bin"),
              "left_edge_mask_enabled": left_mask,
              "writes_to_visible_page": len(bad_writes), "unsafe_presentations": len(bad_present),
              "source_upload_byte_exact": upload_exact, "both_sat_terminators_exact": sat_terminators,
              "r800_dram_and_r20_7f": stable_regs,
              "cpu_registers_hex": state["cpu"], "vdp_registers_hex": state["regs"],
              "screenshots": sorted(p.name for p in work.glob("*.png")),
              "presentation_log_sha256": sha256(work / "presentations.csv"),
              "command_log_sha256": sha256(work / "commands.csv"),
              "limitations": "Pinned openMSX observations; not evidence of physical V9968 timing."}
    report["passed"] = all((report["every_presentation_two_vblanks"], report["frame_indices_consecutive"],
                            strips_exact, command_shape, not bad_writes, not bad_present, upload_exact,
                            sat_terminators, stable_regs, geometry_exact, left_mask,
                            seconds < 53 or report["loop_wrap_seen"]))
    if avi:
        video = work / "CATSTRIDER-native.avi"
        assert video.stat().st_size > 1024, "AVI recording is missing or empty"
        report.update(native_recording_seconds=seconds, native_recording_sha256=sha256(video),
                      native_recording_file=video.name)
    (work / "verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (ROOT / f"outputs/runtime-verification-{profile}.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", choices=PROFILES, default=PROFILES[0])
    parser.add_argument("--seconds", type=float, help="Duration after first presentation (default: 12, or 54 with AVI)")
    parser.add_argument("--screenshots", default="2,6,10", help="Comma-separated stage seconds")
    parser.add_argument("--full-stage-avi", action="store_true")
    args = parser.parse_args()
    seconds = args.seconds if args.seconds is not None else (54 if args.full_stage_avi else 12)
    screenshots = [float(t) for t in args.screenshots.split(",") if t.strip()]
    if seconds <= 0 or any(t <= 0 or t >= seconds for t in screenshots):
        parser.error("Screenshot times must be positive and earlier than the capture duration")
    (ROOT / f"outputs/runtime-verification-{args.profile}.json").unlink(missing_ok=True)
    work = run(capture_script(args.profile, seconds, screenshots, args.full_stage_avi), args.profile,
               timeout=max(120, 3 * (seconds + 20)))
    report = analyze(work, args.profile, seconds, args.full_stage_avi)
    print(json.dumps({"work": str(work), **report}, indent=2))
    if not report["passed"]:
        raise SystemExit("Runtime verification failed; inspect the retained event logs")


if __name__ == "__main__":
    main()
