"""Build the original CATSTRIDER assets and two 512 KiB ASCII8 ROMs."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess

import generate

ROOT = Path(__file__).resolve().parents[1]
PROFILES = (("legacy-openmsx-internal", 0x98), ("legacy-openmsx", 0x88))


def build():
    generate.generate()
    out, work = ROOT / "outputs", ROOT / "work/build"
    out.mkdir(exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    pasmo = os.environ.get("PASMO") or shutil.which("pasmo") or "C:/Software/Pasmo/pasmo.exe"
    subprocess.run([pasmo, "--bin", "src/boot.asm", str(work / "boot.bin")], cwd=ROOT, check=True)
    boot = (work / "boot.bin").read_bytes()
    assert len(boot) == 8192 and boot[:2] == b"AB", "Invalid ASCII8 boot bank"
    upload = (ROOT / "assets/vram-upload.bin").read_bytes()
    motion = (ROOT / "assets/motion.bin").read_bytes()
    assert len(upload) == 12 * 8192, "Upload must occupy banks 4..15 (96 KiB)"
    assert len(motion) == 1536 * 256, "Motion must occupy banks 16..63"
    report = []
    for profile, port in PROFILES:
        wrapper = work / f"profile-{profile}.asm"
        wrapper.write_text(f'VDP_BASE equ {port}\ninclude "src/demo.asm"\n', encoding="utf-8")
        binary = work / f"demo-{profile}.bin"
        subprocess.run([pasmo, "--bin", str(wrapper), str(binary), str(work / f"demo-{profile}.symbols")],
                       cwd=ROOT, check=True)
        runtime = binary.read_bytes()
        assert len(runtime) <= 3 * 8192, "Runtime exceeds the three RAM-loaded banks"
        rom = boot + runtime + bytes([255]) * (3 * 8192 - len(runtime)) + upload + motion
        assert len(rom) == 512 * 1024
        assert rom[4 * 8192:16 * 8192] == upload
        assert rom[16 * 8192:] == motion
        name = f"CATSTRIDER-V9968-{profile}.rom"
        (out / name).write_bytes(rom)
        report.append({"file": name, "mapper": "ASCII8", "rom_bytes": len(rom),
                       "runtime_bytes": len(runtime), "sha256": hashlib.sha256(rom).hexdigest(),
                       "profile": profile, "upload_banks": [4, 15], "motion_banks": [16, 63],
                       "motion_records": 1536, "hardware_verified": False})
    (out / "build-manifest.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


if __name__ == "__main__":
    build()
