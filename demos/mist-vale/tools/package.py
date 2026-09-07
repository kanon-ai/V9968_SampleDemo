"""Package original MIST / VALE files after verified, source-only reproduction.

All emulator checks must already have passed for the current ROMs. This script
does not launch the emulator or copy any BIOS, XML, executable or work files.
"""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "outputs"
PROFILES = ("legacy-openmsx-internal", "legacy-openmsx")
PREFIX = "MIST_VALE"
ROOT_FILES = (
    "README.md", "TECHNIQUES.md", "COPYRIGHT.md", "DISCLAIMER.md",
    "THIRD_PARTY_NOTICES.md", "requirements.txt", "run-demo.cmd", ".gitignore",
)
TREE_EXTENSIONS = {
    "src": {".asm", ".inc"},
    "tools": {".py", ".tcl"},
    "assets": {".bin", ".inc", ".json", ".png"},
}
OUTPUT_FILES = (
    "build-manifest.json", "motion-verification.json", "verification.json",
    "video-verification.json", "scene-verification-legacy-openmsx-internal.json",
    "scene-verification-legacy-openmsx.json", "MIST_VALE-emulator.png",
    "MIST_VALE-emulator.gif", "MIST_VALE-smooth.mp4",
)


def require(condition, message):
    if not condition:
        raise RuntimeError(message)


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(name):
    return json.loads((OUT / name).read_text(encoding="utf-8"))


def rom_name(profile):
    return f"{PREFIX}-V9968-{profile}.rom"


def verified_hashes():
    hashes = {rom_name(profile): sha(OUT / rom_name(profile)) for profile in PROFILES}
    manifest = read_json("build-manifest.json")
    require({row["profile"] for row in manifest} == set(PROFILES) and len(manifest) == 2,
            "Build manifest must contain exactly the internal and external profiles")
    for row in manifest:
        name = rom_name(row["profile"])
        require(row["file"] == name and row["sha256"] == hashes[name],
                f"Build manifest does not match {name}")
        require(row["rom_bytes"] == (OUT / name).stat().st_size == 524288,
                f"{name} must be exactly 512 KiB")
        require(row["mapper"] == "ASCII8", f"Unexpected mapper in {name}")

    internal = hashes[rom_name(PROFILES[0])]
    motion = read_json("motion-verification.json")
    video = read_json("video-verification.json")
    for name, report in (("motion", motion), ("video", video)):
        require(report["rom_sha256"] == internal, f"{name} report belongs to a different ROM")
    require(motion["records_checked"] == 1024 and motion["all_bank_offsets_exact"]
            and motion["tree_y_constant_for_every_record"], "Motion checks are incomplete")
    ground_sync = motion.get("ground_sync", {})
    require(ground_sync.get("passed") is True
            and ground_sync.get("records_checked") == 1024
            and ground_sync.get("loop_transitions_checked") == 1024,
            "Ground/tree position and loop synchronization checks are incomplete")
    require(video["mp4_frames"] > 0 and video["gif_frames"] > 0
            and not video["mp4_frame_interpolation"], "Native video verification is incomplete")

    verification = read_json("verification.json")
    require(verification["native_recording_rom_sha256"] == internal,
            "Native recording verification belongs to a different ROM")
    require(video["native_recording_sha256"] == verification["native_recording_sha256"],
            "Video was not encoded from the verified native recording")
    require(video["mp4_sha256"] == sha(OUT / "MIST_VALE-smooth.mp4")
            and video["gif_sha256"] == sha(OUT / "MIST_VALE-emulator.gif"),
            "MP4/GIF bytes do not match video verification")

    runs = verification["verified"]
    require({row["profile"] for row in runs} == set(PROFILES) and len(runs) == 2,
            "Both emulator profiles must be verified")
    for run in runs:
        require(run["sha256"] == hashes[rom_name(run["profile"])],
                f"Runtime verification is stale: {run['profile']}")
        require(all(run[key] for key in (
            "loop_wrap_seen", "r800_dram", "asset_upload_byte_exact",
            "twelve_sprites_plus_terminator")), f"Incomplete runtime check: {run['profile']}")
        require(run["vblank_interrupts"] > 0 and run["raster_interrupts"] > 0,
                f"No measured raster interrupts: {run['profile']}")

    for profile in PROFILES:
        scene = read_json(f"scene-verification-{profile}.json")
        require(scene["profile"] == profile and scene["passed"]
                and scene["rom_sha256"] == hashes[rom_name(profile)],
                f"Scene verification is missing, failed or stale: {profile}")
        require(scene["source_128KiB_unchanged"] and len(scene["background_pages"]) == 2,
                f"Scene source/page checks are incomplete: {profile}")
        require(all(page["mismatches"] == 0 and page["fixed_sky_and_water_VRAM_exact"]
                    and page["SAT_duplicate_exact"] for page in scene["background_pages"]),
                f"Scene pixel comparison failed: {profile}")
        require(scene.get("ground_composite", {}).get("passed") is True,
                f"Foreground ground/tree composite verification is missing or failed: {profile}")
        raster = scene["raster"]
        require(raster["actual_register_writes_observed"] and raster["scheduled_values_exact"]
                and raster["nonzero_scroll_in_top_region"] == 0,
                f"Raster verification failed: {profile}")
        scanout = scene.get("scanout", {})
        require(scanout.get("passed") is True
                and scanout.get("command_events", 0) > 0
                and scanout.get("presentation_events", 0) > 0
                and scanout.get("writes_to_visible_page") == 0
                and scanout.get("wrong_display_page_presentations") == 0
                and scanout.get("unfinished_command_presentations") == 0
                and scanout.get("visible_display_pages") == [0, 1],
                f"Running display-page verification is missing or failed: {profile}")
        fog = scene.get("fog", {})
        require(fog.get("observed_coverage_exact") and fog.get("frozen_background_comparison"),
                f"Run verify_scene.py --profile {profile} --alpha before packaging")
        samples = fog.get("samples", {})
        require(samples and all(sample["pixels"] > 0
                                and sample["pixels"] == sample["exact_rgb5_mix"]
                                for sample in samples.values()),
                f"Fog RGB5 blending comparison failed: {profile}")
    return hashes


def package_files():
    files = [ROOT / name for name in ROOT_FILES]
    for folder, extensions in TREE_EXTENSIONS.items():
        files.extend(path for path in (ROOT / folder).rglob("*")
                     if path.is_file() and path.suffix.lower() in extensions
                     and "__pycache__" not in path.parts)
    files.extend(OUT / name for name in OUTPUT_FILES)
    files.extend(OUT / rom_name(profile) for profile in PROFILES)
    require(all(path.is_file() for path in files), "A required package file is missing")
    require(all(not path.is_symlink() and path.resolve().is_relative_to(ROOT.resolve())
                for path in files), "Package files must be regular workspace files")
    return sorted(set(files))


def write_archive(target, files):
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, Path(PREFIX) / path.relative_to(ROOT))
    with ZipFile(target) as archive:
        require(archive.testzip() is None, "ZIP integrity check failed")
        names = archive.namelist()
        require(len(names) == len(set(names)), "Duplicate ZIP entries")
        require(not any("/work/" in name.lower() or "systemroms" in name.lower()
                        or Path(name).suffix.lower() in {".exe", ".dll", ".xml"}
                        for name in names), "Unexpected third-party/runtime file in ZIP")


def reproduce_from_archive(archive_path, expected_hashes, files):
    """Rebuild the exact archived sources with all generated assets removed."""
    work = (ROOT / "work").resolve()
    work.mkdir(exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="package-rebuild-", dir=work)).resolve()
    require(temporary.is_relative_to(work) and temporary != work, "Unsafe rebuild directory")
    expected_assets = {path.relative_to(ROOT / "assets").as_posix(): sha(path)
                       for path in files if path.is_relative_to(ROOT / "assets")}
    try:
        with ZipFile(archive_path) as archive:
            for entry in archive.infolist():
                require((temporary / entry.filename).resolve().is_relative_to(temporary),
                        "Unsafe ZIP entry")
            archive.extractall(temporary)
        copied = temporary / PREFIX
        for folder in (copied / "assets", copied / "outputs"):
            require(folder.resolve().is_relative_to(temporary), "Unsafe generated-data directory")
            for path in folder.rglob("*"):
                if path.is_file():
                    path.unlink()
        subprocess.run([sys.executable, "tools/build.py"], cwd=copied, check=True)
        rebuilt_hashes = {rom_name(profile): sha(copied / "outputs" / rom_name(profile))
                          for profile in PROFILES}
        require(rebuilt_hashes == expected_hashes, "Archived source rebuild changed ROM bytes")
        rebuilt_assets = {path.relative_to(copied / "assets").as_posix(): sha(path)
                          for path in (copied / "assets").rglob("*") if path.is_file()}
        require(rebuilt_assets == expected_assets, "Generated assets did not reproduce byte for byte")
        return {"asset_regeneration_identical": True, "source_archive_rebuild_identical": True,
                "source_archive_assets_removed_before_build": True,
                "generated_assets_checked": len(expected_assets), "sha256": rebuilt_hashes,
                "asset_sha256": rebuilt_assets,
                "method": "Extract the packaged source, remove generated assets/output, build with Python and Pasmo, compare all ROM and generated-asset bytes"}
    finally:
        # Only this freshly created directory may be recursively removed.
        require(temporary.resolve().is_relative_to(work) and temporary.resolve() != work,
                "Refusing to clean an unsafe rebuild directory")
        shutil.rmtree(temporary)


def main():
    hashes = verified_hashes()
    files = package_files()
    snapshot = {path.relative_to(ROOT).as_posix(): sha(path) for path in files}
    pending = OUT / f"{PREFIX}-source-and-ROM.pending.zip"
    target = OUT / f"{PREFIX}-source-and-ROM.zip"
    write_archive(pending, files)
    report = reproduce_from_archive(pending, hashes, files)
    require(snapshot == {path.relative_to(ROOT).as_posix(): sha(path) for path in files},
            "Project files changed during packaging; rerun after all edits and checks finish")
    require(verified_hashes() == hashes, "Verification changed during packaging")
    report["packaged_file_sha256"] = snapshot
    report_path = OUT / "reproducibility.json"
    report_path.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    write_archive(pending, sorted(files + [report_path]))
    os.replace(pending, target)
    print(json.dumps({"archive": str(target), "bytes": target.stat().st_size,
                      "sha256": sha(target), "source_rebuild_identical": True}, indent=2))


if __name__ == "__main__":
    main()
