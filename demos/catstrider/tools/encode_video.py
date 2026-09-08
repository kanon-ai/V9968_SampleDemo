"""Encode a verified private run's actual AVI; never synthesize demo frames."""
import argparse
import io
import json
import os
from pathlib import Path
import re
import shutil
import subprocess

from PIL import Image, ImageDraw
from run_check import ROOT, PROFILES, sha256


def find_ffmpeg(override=None):
    selected = override or os.environ.get("FFMPEG") or shutil.which("ffmpeg")
    if selected:
        return str(selected)
    for folder in (ROOT / "work/encoder/imageio_ffmpeg/binaries",
                   ROOT.parent / "v9968-aurora-demo/work/encoder/imageio_ffmpeg/binaries"):
        candidates = sorted(folder.glob("ffmpeg*.exe"))
        if candidates:
            return str(candidates[0])
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except ImportError:
        raise RuntimeError("Set FFMPEG or --ffmpeg to an installed ffmpeg; the encoder is not distributed with the demo")


def verify_recording(run):
    """Require matching run, capture and current ROM hashes before encoding."""
    run = Path(run).resolve()
    invocation = json.loads((run / "invocation.json").read_text())
    verified = json.loads((run / "verification.json").read_text())
    assert verified["passed"] and verified["every_complete_update_112_strips"], "Run is not a verified 112-strip build"
    profile = invocation["profile"]
    assert profile in PROFILES and verified["profile"] == profile
    rom = ROOT / f"outputs/CATSTRIDER-V9968-{profile}.rom"
    rom_hash = sha256(rom)
    assert invocation["rom_sha256"] == verified["rom_sha256"] == rom_hash, "Capture belongs to an older/different ROM"
    assert invocation["emulator_sha256"] == verified["emulator_sha256"], "Emulator provenance differs between run and verification"
    name = verified.get("native_recording_file", "CATSTRIDER-native.avi")
    assert Path(name).name == name and name.lower().endswith(".avi"), "Recording must be an AVI inside the selected run"
    source = run / name
    assert source.is_file() and source.stat().st_size > 1024, "The selected run has no native recording"
    source_hash = sha256(source)
    assert verified["native_recording_sha256"] == source_hash, "AVI differs from the verified recording"
    return source, verified, {"rom_sha256": rom_hash, "native_recording_sha256": source_hash,
                              "emulator_sha256": verified["emulator_sha256"], "profile": profile}


def ffmpeg_run(ffmpeg, args, binary=False):
    result = subprocess.run([ffmpeg, "-y", "-hide_banner", *map(str, args)], capture_output=True,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
    log = result.stderr.decode("utf-8", errors="replace")
    if result.returncode:
        raise RuntimeError(log[-6000:])
    return result.stdout if binary else log


def media_info(log):
    # The first Video/Duration lines belong to the input stream. The completed
    # decode/remux frame counter establishes the number actually read.
    rate = re.search(r"Video:.*?, ([\d.]+) fps", log)
    duration = re.search(r"Duration: (\d+):(\d+):([\d.]+)", log)
    counts = re.findall(r"frame=\s*(\d+)", log)
    assert rate and duration and counts, "ffmpeg did not report input cadence, duration and completed frame count"
    return {"fps": float(rate[1]), "frames": int(counts[-1]),
            "seconds": int(duration[1]) * 3600 + int(duration[2]) * 60 + float(duration[3])}


def contact_sheet(ffmpeg, source, times, target):
    panels = []
    for seconds in times:
        png = ffmpeg_run(ffmpeg, ["-ss", seconds, "-i", source, "-frames:v", "1", "-f", "image2pipe",
                                   "-c:v", "png", "pipe:1"], binary=True)
        with Image.open(io.BytesIO(png)) as decoded:
            image = decoded.convert("RGB")
        height = round(image.height * 384 / image.width)
        panel = Image.new("RGB", (384, height + 24), (12, 17, 30))
        panel.paste(image.resize((384, height), Image.Resampling.NEAREST), (0, 24))
        ImageDraw.Draw(panel).text((8, 5), f"CATSTRIDER  {seconds:05.2f}s", fill=(217, 236, 255))
        panels.append(panel)
    width, height = panels[0].size
    result = Image.new("RGB", (width * 4, height * 2))
    for index, panel in enumerate(panels):
        result.paste(panel, ((index % 4) * width, (index // 4) * height))
    result.save(target)


def encode(run, ffmpeg=None, gif_start=24, gif_seconds=15, width=768, sheet=False, sheet_times=None):
    source, verified, provenance = verify_recording(run)
    ffmpeg = find_ffmpeg(ffmpeg)
    out = ROOT / "outputs"
    expected_seconds = verified["native_recording_seconds"]
    assert gif_start >= 0 and gif_seconds > 0 and gif_start + gif_seconds <= expected_seconds, "Highlight exceeds the verified recording"
    assert width > 0 and width % 2 == 0, "MP4 width must be a positive even number"
    times = sheet_times if sheet_times is not None else [1, 8, 16, 24, 32, 40, 46, 51]
    assert not sheet or (len(times) == 8 and all(0 <= t < expected_seconds for t in times)), "Contact sheet needs eight valid recording times"
    (out / "video-verification.json").unlink(missing_ok=True)
    # Fast packet pass measures the original AVI without transforming frames.
    original = media_info(ffmpeg_run(ffmpeg, ["-i", source, "-map", "0:v:0", "-c", "copy", "-f", "null", "-"]))
    assert 59.8 <= original["fps"] <= 60.1, "Expected the native NTSC VDP recording cadence"
    assert abs(original["seconds"] - expected_seconds) <= 0.15, "AVI duration differs from the recorded interval"
    mp4 = out / "CATSTRIDER-smooth.mp4"
    gif = out / "CATSTRIDER-emulator.gif"
    # No -r, fps filter, or interpolation in the MP4: preserve native capture
    # frames, including each pair displayed by the 30 Hz renderer.
    ffmpeg_run(ffmpeg, ["-i", source, "-map", "0:v:0", "-map", "0:a:0?",
                        "-vf", f"scale={width}:-2:flags=neighbor,setsar=1", "-fps_mode", "passthrough",
                        "-c:v", "libx264", "-crf", "18", "-preset", "medium", "-pix_fmt", "yuv420p",
                        "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", mp4])
    ffmpeg_run(ffmpeg, ["-ss", gif_start, "-t", gif_seconds, "-i", source, "-filter_complex",
                        "[0:v]fps=30,split[a][b];[a]palettegen=stats_mode=diff[p];"
                        "[b][p]paletteuse=dither=bayer:bayer_scale=3", "-loop", "0", "-an", gif])
    decoded_log = ffmpeg_run(ffmpeg, ["-i", mp4, "-f", "null", "-"])
    decoded = media_info(decoded_log)
    assert decoded["frames"] == original["frames"], "MP4 dropped or added captured frames"
    assert decoded["fps"] == original["fps"], "MP4 cadence differs from the native recording"
    assert re.search(r"Audio: aac", decoded_log), "MP4 is missing the recorded PSG audio"
    assert re.search(r"Video: h264.*yuv420p", decoded_log), "MP4 codec/pixel format differs from the requested output"
    with Image.open(gif) as preview:
        durations = []
        for frame in range(preview.n_frames):
            preview.seek(frame)
            durations.append(preview.info["duration"])
    assert abs(sum(durations) - gif_seconds * 1000) <= 50, "GIF duration differs from its selected interval"
    assert len(durations) <= round(gif_seconds * 30) + 1 and all(d > 0 for d in durations)
    report = {**provenance, "passed": True, "source": "Actual openMSX native AVI from the selected verified run",
              "native_recording_file": source.name, "native_recording_seconds": original["seconds"],
              "mp4_fps": decoded["fps"], "mp4_frames": decoded["frames"], "native_frames_preserved": True,
              "mp4_audio": "Recorded PSG, AAC", "mp4_frame_interpolation": False, "mp4_width": width,
              "mp4_sha256": sha256(mp4), "gif_sha256": sha256(gif), "gif_frames": len(durations),
              "gif_duration_ms": sum(durations), "gif_target_fps": 30, "gif_start_seconds": gif_start,
              "hardware_tested": False}
    if sheet:
        target = out / "CATSTRIDER-contact-sheet.png"
        contact_sheet(ffmpeg, source, times, target)
        report.update(contact_sheet_times_seconds=times, contact_sheet_sha256=sha256(target))
    (out / "video-verification.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True, help="Private run directory containing AVI and verification.json")
    parser.add_argument("--ffmpeg", help="Path to an installed ffmpeg executable")
    parser.add_argument("--gif-start", type=float, default=24)
    parser.add_argument("--gif-seconds", type=float, default=15)
    parser.add_argument("--width", type=int, default=768)
    parser.add_argument("--contact-sheet", action="store_true", help="Extract eight actual AVI frames")
    parser.add_argument("--sheet-times", help="Eight comma-separated recording times; default 1,8,16,24,32,40,46,51")
    args = parser.parse_args()
    times = [float(t) for t in args.sheet_times.split(",")] if args.sheet_times else None
    encode(args.run, args.ffmpeg, args.gif_start, args.gif_seconds, args.width, args.contact_sheet, times)


if __name__ == "__main__":
    main()
