"""Hold a rendered frame and compare translucent sprites against the same background."""
import re,json,hashlib
from pathlib import Path
from PIL import Image
from run_check import run,ROOT

def probe():
    work=ROOT/'work/alpha'; work.mkdir(parents=True,exist_ok=True)
    sym=(ROOT/'work/build/demo-legacy-openmsx-internal.symbols').read_text()
    main=int(re.search(r'main_loop\s+EQU 0([0-9A-F]+)H',sym)[1],16)
    script='''
set save_settings_on_exit false
set throttle true
set renderer SDLGL-PP
set minframeskip 0
set maxframeskip 0
set scanline 0
set blur 0
proc stop_motion {} {
    debug write memory MAIN 24
    debug write memory NEXT 254
    after time 0.15 full_capture
}
proc full_capture {} {
    openmsx::internal_screenshot -raw ../alpha/full.png
    set f [open ../alpha/registers.bin wb]; puts -nonewline $f [debug read_block {VDP regs} 0 64]; close $f
    set f [open ../alpha/vram.bin wb]; puts -nonewline $f [debug read_block {physical VRAM} 0 262144]; close $f
    debug write {VDP regs} 8 10
    after time 0.10 background_capture
}
proc background_capture {} {
    openmsx::internal_screenshot -raw ../alpha/background.png
    foreach base {28672 29184} {
        for {set i 0} {$i<14} {incr i} {
            set address [expr {$base+$i*8+3}]
            debug write {physical VRAM} $address [expr {[debug read {physical VRAM} $address]&63}]
        }
    }
    debug write {VDP regs} 8 8
    after time 0.10 opaque_capture
}
proc opaque_capture {} {
    openmsx::internal_screenshot -raw ../alpha/opaque.png
    exit
}
after time 10 stop_motion
'''.replace('MAIN',str(main)).replace('NEXT',str(main+1))
    run(script)
    full=Image.open(work/'full.png').convert('RGB')
    bg=Image.open(work/'background.png').convert('RGB')
    opaque=Image.open(work/'opaque.png').convert('RGB')
    regs=(work/'registers.bin').read_bytes(); vram=(work/'vram.bin').read_bytes()
    sat=0x7000 if regs[5]==0xc3 else 0x7200
    # Compare selected nontransparent interior pixels to the unmodified backdrop.
    # d884 / this machine's 320x240 raw output has active origin x33,y15.
    # The difference-mask assertion below checks this against observed pixels.
    samples={1:[],2:[],3:[]}
    occupied=set()
    for n in range(14):
        a=vram[sat+n*8:sat+n*8+8]
        x=(a[4]|((a[5]&3)<<8)); x=x-1024 if x&512 else x
        y=(a[0]|((a[1]&3)<<8)); y=y-1024 if y&512 else y
        w,h=a[6] or 256,a[2] or 256
        sy=16<<((a[1]>>6)&3); px=(a[7]&15)*16; py=(a[7]>>4)*16
        group,tp=a[3]&15,a[3]>>6
        for dy in range(h):
            yy=y+dy
            if not 0<=yy<212: continue
            for dx in range(w):
                xx=x+dx
                if not 0<=xx<256 or (xx,yy) in occupied: continue
                tx,ty=px+16*dx//w,py+sy*dy//h
                value=vram[(regs[6]<<11)+ty*128+tx//2]
                color=(value>>4) if tx%2==0 else (value&15)
                if color==0: continue
                occupied.add((xx,yy))
                source=tuple(c>>3 for c in opaque.getpixel((xx+33,yy+15)))
                before=bg.getpixel((xx+33,yy+15)); after=full.getpixel((xx+33,yy+15))
                dest=tuple(c>>3 for c in before)
                mixed=tuple(((3*s+d)>>2) if tp==1 else ((s+d)>>1) if tp==2 else ((s+3*d)>>2) for s,d in zip(source,dest))
                expected=tuple((c<<3)|(c>>2) for c in mixed)
                if expected!=before:
                    samples[tp].append(max(abs(a-b) for a,b in zip(after,expected)))
    observed={(x,y) for y in range(212) for x in range(256) if opaque.getpixel((x+33,y+15))!=bg.getpixel((x+33,y+15))}
    assert occupied==observed, 'Sprite coverage differs from the observed opaque image'
    report={'frozen_background_comparison':True,'opaque_reference_capture':True,'observed_coverage_matches':True,
      'rom_sha256':hashlib.sha256((ROOT/'outputs/LUMEN_FORGE-V9968-legacy-openmsx-internal.rom').read_bytes()).hexdigest(),'samples':{}}
    for tp,errors in samples.items():
        matches=sum(e==0 for e in errors)
        report['samples'][str(tp)]={'pixels':len(errors),'matching_rgb5_mix_exact':matches,
                                  'fraction':round(matches/len(errors),5) if errors else 0}
        assert errors and matches==len(errors),report
    (ROOT/'outputs/alpha-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__': probe()
