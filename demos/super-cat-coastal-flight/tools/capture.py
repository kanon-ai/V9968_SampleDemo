"""Capture actual private ROM execution, retaining native video cadence."""
from pathlib import Path
import re,json,shutil,subprocess,os,csv,hashlib
from capture_base import run,ROOT
sym={k:int(v,16) for k,v in re.findall(r'(?m)^(\w+)\s+EQU\s+0([0-9A-F]+)H',(ROOT/'work/build/demo.symbols').read_text())}
script=r'''
set save_settings_on_exit false
set throttle false
set minframeskip 0
set maxframeskip 0
set renderer SDLGL-PP
set scale_factor 2
set scanline 0
set blur 0
set ::started 0
set ::ending 0
set ::phases [dict create]
set ::attrs [dict create]
set ::f [open frames.csv w]
puts $::f "time,frame,r2,s2,cpu"
proc fail {err opts} {
 set f [open check-error.txt w]; puts $f $err; puts $f $opts; close $f
 catch {record stop}; exit
}
proc shot {n} {if {[catch {openmsx::internal_screenshot -raw "./shot-$n.png"} e o]} {fail $e $o}}
proc present {} {
 if {[catch {
  set phase [debug read memory FESTIVAL]
  if {![dict exists $::phases $phase]} {
   dict set ::phases $phase 1
   set f [open "phase-$phase.bin" wb]; puts -nonewline $f [debug read_block {physical VRAM} 131072 131072];close $f
  }
  set frame [expr {[debug read memory FRAME]+256*[debug read memory FRAMEHI]}]
  if {($frame % 128)==0 && ![dict exists $::attrs $frame]} {
   dict set ::attrs $frame 1
   set base [expr {65536+512*(([debug read {VDP regs} 2]>>5)&1)}]
   set f [open "attrs-$frame.bin" wb];puts -nonewline $f [debug read_block {physical VRAM} $base 88];close $f
  }
  puts $::f "[machine_info time],[expr {[debug read memory FRAME]+256*[debug read memory FRAMEHI]}],[debug read {VDP regs} 2],[debug read {VDP status regs} 2],[debug read {S1990 regs} 6]"
  if {!$::started} {
   set ::started 1
   record start ./native.avi
   foreach n {1 5 10 16 23 30} {after time $n "shot $n"}
   after time 36 finish
  }
  if {$::ending} {finish_at_present}
 } e o]} {fail $e $o}
}
proc finish {} {set ::ending 1}
proc finish_at_present {} {
 if {[catch {
  record stop; close $::f
  set f [open source.bin wb]; puts -nonewline $f [debug read_block {physical VRAM} 131072 131072];close $f
  set f [open final-phase.txt w];puts $f [debug read memory FESTIVAL];close $f
  exit
 } e o]} {fail $e $o}
}
debug set_bp PRESENT {} {present}
after time 20 {if {!$::started} {fail "No first frame" {}}}
'''.replace('FRAMEHI',str(sym['frame_index']+1)).replace('FRAME',str(sym['frame_index'])).replace('PRESENT',str(sym['presented'])).replace('FESTIVAL',str(sym['festival_phase']))
work=run(script,timeout=180)
print('Capture:',work,flush=True)
rows=list(csv.DictReader((work/'frames.csv').open()))
assert len(rows)>500
from build import PATCHES
ground=(ROOT/'assets/background.bin').read_bytes();atlas=(ROOT/'assets/sprites.bin').read_bytes()
def expected_source(phase):
 result=bytearray(ground)
 for n,(tx,ty) in enumerate(PATCHES):
  index=phase*6+n;ax=64+(index%12)*16;ay=64+(index//12)*16
  for yy in range(16):result[(ty+yy)*128+tx//2:(ty+yy)*128+tx//2+8]=atlas[(ay+yy)*128+ax//2:(ay+yy)*128+ax//2+8]
 return bytes(result)+atlas
for phase in range(8):assert (work/f'phase-{phase}.bin').read_bytes()==expected_source(phase),f'Boat animation phase {phase}'
assert (work/'source.bin').read_bytes()==expected_source(int((work/'final-phase.txt').read_text()))
motion=(ROOT/'assets/motion.bin').read_bytes()
for frame in range(0,2048,128):
 assert (work/f'attrs-{frame}.bin').read_bytes()==motion[frame*128+8:frame*128+88]+bytes([216,0,0,0,0,0,0,0]),frame
assert all(not int(r['s2'])&1 and int(r['s2'])&64 for r in rows)
assert all(int(r['cpu'])&96==0 for r in rows)
fps=(len(rows)-1)/(float(rows[-1]['time'])-float(rows[0]['time']))
cadence=[round((float(b['time'])-float(a['time']))*59.9227) for a,b in zip(rows,rows[1:])]
assert all(n==1 for n in cadence),'Presentation missed or duplicated a video frame'
assert all((int(b['frame'])-int(a['frame']))%2048==1 for a,b in zip(rows,rows[1:]))
out=ROOT/'outputs'
for p in work.glob('shot-*.png'):shutil.copy2(p,out/p.name)
candidates=list((ROOT.parent/'v9968-aurora-demo/work/encoder/imageio_ffmpeg/binaries').glob('ffmpeg*.exe'))
ffmpeg=os.environ.get('FFMPEG') or shutil.which('ffmpeg') or (str(candidates[0]) if candidates else '')
assert ffmpeg,'FFMPEG required'
def encode(args):
 p=subprocess.run([ffmpeg,'-y','-hide_banner',*map(str,args)],capture_output=True,text=True)
 assert p.returncode==0,p.stderr[-2000:]
 return p.stderr
encode(['-i',work/'native.avi','-vf','scale=960:720:flags=neighbor','-c:v','libx264','-crf','18','-pix_fmt','yuv420p','-an','-movflags','+faststart',out/'SUPER_CAT-COASTAL_FLIGHT.mp4'])
encode(['-ss','5','-t','8','-i',work/'native.avi','-filter_complex','fps=20,scale=480:360:flags=neighbor,split[a][b];[a]palettegen[p];[b][p]paletteuse','-an',out/'preview.gif'])
video=out/'SUPER_CAT-COASTAL_FLIGHT.mp4'
decode=encode(['-i',video,'-f','null','-'])
rate=float(re.search(r'(\d+(?:\.\d+)?) fps',decode)[1])
count=int(re.findall(r'frame=\s*(\d+)',decode)[-1])
assert 59<rate<61 and count>2100
(out/'video-verification.json').write_text(json.dumps(dict(decoded_without_error=True,fps=rate,frames=count,
    sha256=hashlib.sha256(video.read_bytes()).hexdigest(),audio=False,frame_interpolation=False),indent=2))
report=dict(native_capture=work.relative_to(ROOT).as_posix(),updates_per_second=fps,frames=len(rows),source_upload_and_all_8_animation_phases_exact=True,
 all_16_sampled_sprite_tables_exact=True,
 every_update_one_video_frame=True,
 safe_page_presentations=True,r800_dram=True,consecutive_motion_records=True,
 loop_wrap_seen=any(int(b['frame'])<int(a['frame']) for a,b in zip(rows,rows[1:])),hardware_tested=False,
 profile='legacy-openmsx-internal',frame_interpolation=False)
(out/'verification.json').write_text(json.dumps(report,indent=2))
print(json.dumps(report,indent=2))
