"""Actual emulator execution, long-loop checks, source upload comparison and capture."""
from pathlib import Path
import re, json, hashlib
from PIL import Image
from run_check import run, ROOT, EXE

OUT=ROOT/'outputs'
CAP=ROOT/'work/capture'
CAP.mkdir(parents=True,exist_ok=True)

def execute(profile, capture=False):
    sym=(ROOT/f'work/build/demo-{profile}.symbols').read_text()
    addr=int(re.search(r'frame_index\s+EQU 0([0-9A-F]+)H',sym)[1],16)
    internal=profile.endswith('internal')
    regs='VDP regs' if internal else 'V9968 regs'
    vram='physical VRAM' if internal else 'physical V9968 VRAM'
    script='''
set save_settings_on_exit false
set throttle THROTTLE
set speed 100
set minframeskip 0
set maxframeskip 0
set renderer SDLGL-PP
set scale_factor 2
set scanline 0
set blur 0
set deinterlace true
VIDEO_SELECT
set ::prism_samples {}
set ::prism_count 0
set ::prism_capture 0
proc tick {} {
  if {[catch {
    set frame [expr {[debug read memory ADDRESS]+256*[debug read memory NEXT]}]
    lappend ::prism_samples [list $::prism_count $frame [debug read {S1990 regs} 6] [debug read {REGS} 20] [debug read {REGS} 2]]
    if {CAPTURE && $::prism_count>=72 && $::prism_count<216} {
      openmsx::internal_screenshot -raw [format ../capture/frame-%03d.png $::prism_capture]
      incr ::prism_capture
    }
    incr ::prism_count
    if {$::prism_count<480} {after time 0.083333333333 tick} else {
      set f [open samples-PROFILE.txt w]; puts $f $::prism_samples; close $f
      set f [open assets-PROFILE.bin wb]
      puts -nonewline $f [debug read_block {VRAM} 131072 65536]; close $f
      set f [open attrs-PROFILE.bin wb]
      puts -nonewline $f [debug read_block {VRAM} 65536 56]; close $f
      exit
    }
  } err opts]} {set f [open check-error.txt w]; puts $f $err; puts $f $opts; close $f; exit}
}
after time 2 tick
'''
    for a,b in {'THROTTLE':'true' if capture else 'false','VIDEO_SELECT':'' if internal else 'after time 1 {set videosource V9968}','ADDRESS':str(addr),'NEXT':str(addr+1),
                'REGS':regs,'VRAM':vram,'CAPTURE':str(int(capture)),'PROFILE':profile}.items():
        script=script.replace(a,b)
    run(script,profile,timeout=90)
    work=ROOT/'work/emulator'
    samples=[list(map(int,item.split())) for item in re.findall(r'\{([^{}]+)\}',(work/f'samples-{profile}.txt').read_text())]
    # Firmware startup plus initial VRAM upload takes about six seconds here.
    stable=samples[70:]
    assert all((row[2]&0x60)==0 and row[3]==0x7f and row[4] in [0x1f,0x3f] for row in stable)
    assert {row[4] for row in stable} == {0x1f,0x3f}, 'Display pages did not alternate'
    assert all(0<=row[1]<512 for row in stable)
    steps=[(b[1]-a[1])%512 for a,b in zip(stable,stable[1:])]
    assert min(steps)>0 and max(steps)<8, 'Frame counter stalled or jumped'
    assert any(b[1]<a[1] for a,b in zip(stable,stable[1:])), 'Loop boundary was not reached'
    original=(ROOT/'assets/background.bin').read_bytes()+(ROOT/'assets/sprites.bin').read_bytes()
    assert (work/f'assets-{profile}.bin').read_bytes()==original, 'VRAM upload differs from generated assets'
    attrs=(work/f'attrs-{profile}.bin').read_bytes()
    assert attrs[48:]==bytes([216,0,0,0,0,0,0,0])
    rom=OUT/f'PRISM_FLIGHT-V9968-{profile}.rom'
    return {'profile':profile,'sha256':hashlib.sha256(rom.read_bytes()).hexdigest(),
        'machine':'Panasonic_FS-A1ST_V9968' if internal else 'Panasonic_FS-A1ST + HRA_V9968',
        'emulated_seconds':42,'steady_demo_updates_per_second':round(sum(steps)/len(steps)*12,2),
        'loop_wrap_seen':True,'r800_dram':True,'asset_upload_byte_exact':True,'six_sprites_plus_terminator':True,
        'hardware_tested':False,'captures':144 if capture else 0}

if __name__=='__main__':
    results=[execute('legacy-openmsx-internal',True), execute('legacy-openmsx')]
    frames=[Image.open(p).convert('RGB') for p in sorted(CAP.glob('frame-*.png'))]
    assert len(frames)==144 and len({hashlib.sha256(im.tobytes()).digest() for im in frames})==144
    frames[36].save(OUT/'PRISM_FLIGHT-emulator.png')
    frames[0].save(OUT/'PRISM_FLIGHT-emulator.gif',save_all=True,append_images=frames[1:],duration=[80,80,90]*48,loop=0)
    report={'emulator_sha256':hashlib.sha256(EXE.read_bytes()).hexdigest(),'verified':results,
        'preview':'144 real emulator captures, 12 seconds at 12 fps; not rendered by the asset generator',
        'current_fpga_profile':'build only; not executed on current FPGA or matching emulator',
        'limitations':'Emulator command timing does not establish physical V9968 performance.'}
    (OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))
