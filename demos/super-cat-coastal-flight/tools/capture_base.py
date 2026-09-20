"""Run only a private SUPER CAT / COASTAL FLIGHT emulator child, using external user BIOS.

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
PROFILES = ("legacy-openmsx-internal",)


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
    return str(Path.home() / "Documents/openMSX/share")


def run(script, profile="legacy-openmsx-internal", timeout=180):
    """Return the private output directory. Script paths are relative to it."""
    if profile not in PROFILES:
        raise ValueError(f"Unsupported profile: {profile}")
    rom = ROOT / "outputs/SUPER_CAT-COASTAL_FLIGHT-V9968-legacy-openmsx-internal.rom"
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
