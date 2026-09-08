"""Package CATSTRIDER only after current byte/runtime/media evidence passes.

The allowlisted archive is rebuilt in a fresh retained work/rebuild directory.
This script neither publishes to GitHub nor starts an emulator. --check-only
checks prerequisites without building or creating a ZIP.
"""
from pathlib import Path
import argparse
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import unquote, urlsplit
import zipfile

from verify_assets import ROOT, PROFILES, require, sha256, verify

ARCHIVE = "CATSTRIDER-V9968-source.zip"
PACKAGE_REPORT = "outputs/package-verification.json"
ART_SOURCES = {"cat-key.png", "cat-flight-key.png", "PROMPTS.md",
               "cat-front-sunglasses-key.png", "fish-photo-key.png", "can-photo-key.png", "ENEMY_PROMPTS.md"}
ASSET_SUFFIXES = {".bin", ".inc", ".json", ".png"}
OUTPUT_SUFFIXES = {".rom", ".json", ".png", ".gif", ".mp4", ".txt", ".md"}


def read_json(path):
    require(path.is_file(), f"Required report is not ready: {path.name}")
    return json.loads(path.read_text(encoding="utf-8"))


def check_evidence(root=ROOT):
    root = Path(root).resolve()
    out = root / "outputs"
    current = verify(root)
    recorded = read_json(out / "asset-verification.json")
    require(recorded == current, "Asset verification is missing or stale; run tools/verify_assets.py")
    manifest = read_json(out / "build-manifest.json")
    hashes = {entry["profile"]: entry["sha256"] for entry in manifest}
    runtimes = {}
    for profile in PROFILES:
        evidence = read_json(out / f"runtime-verification-{profile}.json")
        require(evidence["profile"] == profile and evidence["rom_sha256"] == hashes[profile],
                f"Runtime report does not identify the current {profile} ROM")
        require(evidence["passed"] and evidence["loop_wrap_seen"], f"Complete-loop runtime verification has not passed: {profile}")
        require(evidence["every_complete_update_112_strips"] and evidence["lrmm_command_geometry_exact"]
                and evidence["every_presentation_two_vblanks"] and evidence["frame_indices_consecutive"],
                f"Runtime geometry/cadence evidence is incomplete: {profile}")
        require(evidence["writes_to_visible_page"] == 0 and evidence["unsafe_presentations"] == 0
                and evidence["source_upload_byte_exact"] and evidence["both_sat_terminators_exact"]
                and evidence["r800_dram_and_r20_7f"], f"Runtime safety/initialization evidence differs: {profile}")
        require(evidence.get("hardware_tested") is False, "Emulator report must not claim physical hardware validation")
        runtimes[profile] = evidence
    media = read_json(out / "video-verification.json")
    internal = "legacy-openmsx-internal"
    require(media["passed"] and media["profile"] == internal and media["rom_sha256"] == hashes[internal],
            "Media verification does not identify the current internal-profile ROM")
    require(media["emulator_sha256"] == runtimes[internal]["emulator_sha256"]
            and media["native_recording_sha256"] == runtimes[internal]["native_recording_sha256"],
            "Media and runtime verification refer to different emulator recordings")
    require(media["native_frames_preserved"] and media["mp4_frame_interpolation"] is False
            and media.get("hardware_tested") is False, "Media provenance/cadence claims differ")
    for filename, key in (("CATSTRIDER-smooth.mp4", "mp4_sha256"),
                          ("CATSTRIDER-emulator.gif", "gif_sha256")):
        require(sha256(out / filename) == media[key], f"Media hash mismatch: {filename}")
    sheet = out / "CATSTRIDER-contact-sheet.png"
    if sheet.exists() or "contact_sheet_sha256" in media:
        require(sheet.is_file() and sha256(sheet) == media.get("contact_sheet_sha256"), "Contact sheet is missing/stale")
    return {"rom_sha256": hashes, "runtime_profiles": list(PROFILES), "both_runtime_loops_observed": True,
            "asset_report_sha256": sha256(out / "asset-verification.json"),
            "runtime_report_sha256": {p: sha256(out / f"runtime-verification-{p}.json") for p in PROFILES},
            "media_report_sha256": sha256(out / "video-verification.json"), "hardware_tested": False}


def selected_files(root=ROOT):
    root = Path(root).resolve()
    selected = set(root.glob("*.md")) | set(root.glob("*.cmd"))
    selected.update((root / "src").rglob("*.asm"))
    selected.update(path for path in (root / "tools").rglob("*.py") if "__pycache__" not in path.parts)
    selected.update(root / "art-source" / name for name in ART_SOURCES)
    for path in (root / "assets").rglob("*"):
        if path.is_file():
            require(path.suffix.lower() in ASSET_SUFFIXES, f"Unapproved asset type: {path.name}")
            selected.add(path)
    for path in (root / "outputs").rglob("*"):
        if not path.is_file() or path.suffix.lower() == ".zip" or path == root / PACKAGE_REPORT:
            continue
        require(path.suffix.lower() in OUTPUT_SUFFIXES, f"Unapproved output type: {path.name}")
        if path.suffix.lower() == ".rom":
            require(path.name in {f"CATSTRIDER-V9968-{p}.rom" for p in PROFILES}, "Only this demo's two ROMs may be distributed")
        selected.add(path)
    result = []
    for path in sorted(selected):
        require(path.is_file() and not path.is_symlink(), f"Missing file or symlink in package: {path}")
        relative = path.relative_to(root).as_posix()
        require(path.resolve().is_relative_to(root), f"Package path escapes project: {relative}")
        require(not {part.lower() for part in Path(relative).parts}.intersection({"work", ".git", "__pycache__"}),
                f"Private directory in package: {relative}")
        require(path.suffix.lower() not in {".exe", ".dll", ".xml", ".zip", ".sys"}
                and "bios" not in path.name.lower(), f"Forbidden distribution file: {relative}")
        result.append((relative, path))
    require(result, "No package files selected")
    return result


def check_links(root, files):
    """Check local Markdown destinations; external sites and heading anchors are not fetched."""
    checked = 0
    for relative in files:
        if not relative.lower().endswith(".md"):
            continue
        doc = root / relative
        text = re.sub(r"```.*?```", "", doc.read_text(encoding="utf-8"), flags=re.S)
        targets = [match[0] or match[1] for match in re.findall(r"\]\(\s*(?:<([^>]+)>|([^\s)]+))(?:\s+[^)]*)?\)", text)]
        targets += [match[0] or match[1] for match in re.findall(r"(?m)^\s*\[[^\]]+\]:\s*(?:<([^>]+)>|([^\s]+))", text)]
        for target in targets:
            url = urlsplit(target)
            if url.scheme or url.netloc or not url.path:
                continue
            path = (doc.parent / unquote(url.path)).resolve()
            require(path.is_relative_to(root), f"Local documentation link leaves package: {relative} -> {target}")
            # This download exists beside the source package, not recursively inside itself.
            archive_link = path == root / "outputs" / ARCHIVE
            require(path.exists() or archive_link, f"Broken local documentation link: {relative} -> {target}")
            checked += 1
    return checked


def inventory(files):
    return {relative: {"bytes": path.stat().st_size, "sha256": sha256(path)} for relative, path in files}


def package(root=ROOT, python=sys.executable):
    root = Path(root).resolve()
    evidence = check_evidence(root)
    files = selected_files(root)
    before = inventory(files)
    # Every run gets a fresh directory. Nothing in an earlier run is deleted.
    base = root / "work/rebuild"
    base.mkdir(parents=True, exist_ok=True)
    run = Path(tempfile.mkdtemp(prefix="package-", dir=base)).resolve()
    require(run.is_relative_to(base.resolve()), "Rebuild diagnostics directory escapes work/rebuild")
    archive, extracted = run / ARCHIVE, run / "extracted"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        for relative, path in files:
            bundle.write(path, relative)
    with zipfile.ZipFile(archive) as bundle:
        require(bundle.testzip() is None and set(bundle.namelist()) == set(before), "Initial archive integrity/membership differs")
        for member in bundle.infolist():
            destination = (extracted / member.filename).resolve()
            require(destination.is_relative_to(extracted.resolve()), "Unsafe archive extraction path")
            require(member.file_size == before[member.filename]["bytes"], "Archive length differs from source")
        bundle.extractall(extracted)
    # Support the generator's private diagnostics even in a clean source ZIP.
    (extracted / "work").mkdir(exist_ok=True)
    # A report link may be present in the final docs before this run's report is written.
    (extracted / PACKAGE_REPORT).write_text("{}\n", encoding="utf-8")
    links = check_links(extracted, before)
    result = subprocess.run([str(python), "tools/build.py"], cwd=extracted, capture_output=True,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    (run / "rebuild.stdout.log").write_bytes(result.stdout)
    (run / "rebuild.stderr.log").write_bytes(result.stderr)
    require(result.returncode == 0, f"Extracted-source rebuild failed; diagnostics retained at {run}")
    rebuilt = read_json(extracted / "outputs/build-manifest.json")
    rebuilt_hashes = {entry["profile"]: sha256(extracted / "outputs" / entry["file"]) for entry in rebuilt}
    require(rebuilt_hashes == evidence["rom_sha256"], f"Extracted-source ROM rebuild differs; diagnostics: {run}")
    for relative, record in before.items():
        if relative.startswith("assets/"):
            require(sha256(extracted / relative) == record["sha256"], f"Regenerated asset differs: {relative}; diagnostics: {run}")
    rebuilt_assets = verify(extracted)
    require(rebuilt_assets["passed"] and rebuilt_assets["rom_sha256"] == evidence["rom_sha256"], "Rebuilt static verification differs")
    # Recheck the original tree, including evidence, after a potentially long rebuild.
    require(inventory(selected_files(root)) == before, "Project changed during packaging; rerun after edits settle")
    require(check_evidence(root) == evidence, "Verification evidence changed during packaging")
    report = {"passed": True, "archive": ARCHIVE, **evidence,
              "rebuild_rom_sha256": rebuilt_hashes, "rebuild_byte_identical": True,
              "regenerated_assets_byte_identical": True, "local_document_links_checked": links,
              "link_check_scope": "Local file destinations; no network requests or heading-anchor validation",
              "included_file_count": len(before) + 1, "source_members": before,
              "excluded": ["work", "BIOS", "emulator executables", "machine XML", "other ZIP archives"],
              "rebuild_diagnostics": run.relative_to(root).as_posix(), "python_version": sys.version.split()[0]}
    encoded = (json.dumps(report, indent=2) + "\n").encode("utf-8")
    with zipfile.ZipFile(archive, "a", compression=zipfile.ZIP_DEFLATED, compresslevel=9) as bundle:
        bundle.writestr(PACKAGE_REPORT, encoded)
    with zipfile.ZipFile(archive) as bundle:
        require(bundle.testzip() is None and len(bundle.namelist()) == len(before) + 1, "Final ZIP integrity differs")
        require(bundle.read(PACKAGE_REPORT) == encoded, "Packaged report differs")
        for relative, record in before.items():
            require(hashlib.sha256(bundle.read(relative)).hexdigest() == record["sha256"], f"Packaged member hash differs: {relative}")
    # Keep the diagnostic candidate and atomically replace only the named product.
    publication = run / "publish.zip"
    shutil.copyfile(archive, publication)
    (root / PACKAGE_REPORT).write_bytes(encoded)
    os.replace(publication, root / "outputs" / ARCHIVE)
    return {"passed": True, "archive": str(root / "outputs" / ARCHIVE),
            "archive_sha256": sha256(root / "outputs" / ARCHIVE), "included_files": len(before) + 1,
            "rebuild_diagnostics": str(run), "rebuild_rom_sha256": rebuilt_hashes}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check-only", action="store_true", help="Require current verification evidence; do not build or package")
    parser.add_argument("--python", default=sys.executable, help="Python with Pillow used for extracted-source rebuild")
    args = parser.parse_args()
    result = check_evidence() if args.check_only else package(python=args.python)
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
