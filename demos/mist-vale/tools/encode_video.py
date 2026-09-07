"""Convert native emulator AVI, preserving its frame rate; create a 30fps GIF preview."""
from pathlib import Path
import os,shutil,subprocess,json,re,hashlib
from PIL import Image
from run_check import ROOT

def encode():
    candidates=list((ROOT/'work/encoder/imageio_ffmpeg/binaries').glob('ffmpeg*.exe'))
    ffmpeg=os.environ.get('FFMPEG') or shutil.which('ffmpeg') or (str(candidates[0]) if candidates else None)
    if not ffmpeg: raise SystemExit('Set FFMPEG to ffmpeg.exe; encoder is not bundled with the demo.')
    source=ROOT/'work/capture/MIST_VALE-native.avi'
    out=ROOT/'outputs'
    verification=json.loads((out/'verification.json').read_text())
    rom_sha=hashlib.sha256((out/'MIST_VALE-V9968-legacy-openmsx-internal.rom').read_bytes()).hexdigest()
    source_sha=hashlib.sha256(source.read_bytes()).hexdigest()
    assert verification['native_recording_sha256']==source_sha, 'AVI differs from the verified recording'
    assert verification['native_recording_rom_sha256']==rom_sha, 'AVI belongs to an older ROM'
    def run(args):
        p=subprocess.run([ffmpeg,'-y','-hide_banner',*map(str,args)],capture_output=True,text=True)
        if p.returncode: raise RuntimeError(p.stderr[-5000:])
        return p.stderr
    # No -r: retain the real NTSC VDP cadence from openMSX, about 59.92 fps.
    log=run(['-i',source,'-vf','scale=960:720:flags=neighbor','-c:v','libx264','-crf','18','-preset','medium',
             '-pix_fmt','yuv420p','-c:a','aac','-b:a','128k','-movflags','+faststart',out/'MIST_VALE-smooth.mp4'])
    run(['-i',source,'-filter_complex',
         '[0:v]fps=30,split[a][b];[a]palettegen=stats_mode=diff[p];[b][p]paletteuse=dither=bayer:bayer_scale=3',
         '-an',out/'MIST_VALE-emulator.gif'])
    info=run(['-i',out/'MIST_VALE-smooth.mp4','-f','null','-'])
    rate=re.search(r'Video:.*?, ([\d.]+) fps',info)
    assert rate and float(rate[1])>59
    frames=re.findall(r'frame=\s*(\d+)',info)
    assert frames and int(frames[-1])>=710
    gif=Image.open(out/'MIST_VALE-emulator.gif'); durations=[]
    for i in range(gif.n_frames): gif.seek(i); durations.append(gif.info['duration'])
    assert 350<=gif.n_frames<=365 and 11800<=sum(durations)<=12200
    report={'source':'openMSX internal recorder, actual ROM execution','mp4_fps':float(rate[1]),
      'mp4_frames':int(frames[-1]),'mp4_audio':'PSG recording, AAC','mp4_frame_interpolation':False,
      'gif_frames':gif.n_frames,'gif_duration_ms':sum(durations),'gif_target_fps':30,
      'rom_sha256':rom_sha, 'native_recording_sha256':source_sha,
      'mp4_sha256':hashlib.sha256((out/'MIST_VALE-smooth.mp4').read_bytes()).hexdigest(),
      'gif_sha256':hashlib.sha256((out/'MIST_VALE-emulator.gif').read_bytes()).hexdigest()}
    (out/'video-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__': encode()
