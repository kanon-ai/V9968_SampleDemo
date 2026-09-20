"""Audit and package only this demo's sources, ROM and verification reports."""
from pathlib import Path
import csv, hashlib, json, math, re, struct, subprocess, sys, zipfile
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'
ROM=OUT/'SUPER_CAT-COASTAL_FLIGHT-V9968-legacy-openmsx-internal.rom'
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
    report=json.loads((OUT/'verification.json').read_text())
    work=ROOT/report['native_capture']
    invocation=json.loads((work/'invocation.json').read_text())
    assert sha(ROM)==invocation['rom_sha256']
    before=sha(ROM)
    subprocess.run([sys.executable,str(ROOT/'tools/build.py')],check=True)
    assert sha(ROM)==before,'Rebuild differs from captured ROM'
    subprocess.run([sys.executable,str(ROOT/'tools/verify_extensions.py')],check=True)
    (OUT/'reproducibility.json').write_text(json.dumps(dict(passed=True,rom_sha256=before,
        rebuilt_from_sources=True),indent=2)+'\n')
    motion=json.loads((ROOT/'assets/motion.json').read_text())
    raw=(ROOT/'assets/motion.bin').read_bytes()
    assert len(motion)==2048 and len(raw)==2048*128
    forward=[]
    for i,a in enumerate(motion):
        b=motion[(i+1)%len(motion)]
        dx=b['cx']-a['cx'];dy=b['cy']-a['cy']
        forward.append(dx*math.sin(a['angle'])-dy*math.cos(a['angle']))
        sx,sy,vx,vy=struct.unpack_from('<hhhh',raw,i*128)
        for x,y in ((0,0),(255,0),(0,211),(255,211)):
            assert 0<=sx+(x*vx-y*vy)/256<256
            assert 1024<=sy+(x*vy+y*vx)/256<1792
        for slot in range(10):
            yy,h,pal,xx,w,pattern=struct.unpack_from('<HBBHBB',raw,i*128+8+slot*8)
            assert yy>>14==2 and 0<h<256 and 0<w<256 and pal&15 in (1,2)
    assert min(forward)>0,'Forward flight reverses or stops, including loop seam'
    (OUT/'motion-verification.json').write_text(json.dumps(dict(passed=True,records=2048,
        loop_seam_checked=True,all_steps_forward=True,minimum_forward_source_step=min(forward),
        all_transform_corners_in_source=True,max_sprites_per_scanline_upper_bound=10,
        zoom_range=[min(x['zoom'] for x in motion),max(x['zoom'] for x in motion)],
        forward_pixels_per_frame_range=[min(x['forward_pixels_per_frame'] for x in motion),
                                        max(x['forward_pixels_per_frame'] for x in motion)]),indent=2)+'\n')
    rows=list(csv.DictReader((work/'frames.csv').open()))
    assert all(round((float(b['time'])-float(a['time']))*59.9227)==1 for a,b in zip(rows,rows[1:]))
    assert all(int(a['r2'])!=int(b['r2']) for a,b in zip(rows,rows[1:]))
    report.update(rom_sha256=before,emulator_sha256=invocation['emulator_sha256'],
                  all_display_pages_alternate=True)
    (OUT/'verification.json').write_text(json.dumps(report,indent=2)+'\n')
    video=OUT/'SUPER_CAT-COASTAL_FLIGHT.mp4'
    assert sha(video)==json.loads((OUT/'video-verification.json').read_text())['sha256']
    files=[p for folder in ('src','tools','assets') for p in (ROOT/folder).glob('*') if p.is_file()]
    files += [ROOT/n for n in ('README.md','TECHNIQUES.md','COPYRIGHT.md','DISCLAIMER.md','THIRD_PARTY_NOTICES.md','requirements.txt')]
    files += [ROM]+list(OUT.glob('*verification.json'))+[OUT/'reproducibility.json',OUT/'build-manifest.json']
    files=list(dict.fromkeys(files))
    target=OUT/'SUPER_CAT-COASTAL_FLIGHT-source-and-ROM.zip'
    with zipfile.ZipFile(target,'w',zipfile.ZIP_DEFLATED,compresslevel=9) as z:
        for p in sorted(files):
            assert p.suffix not in ('.exe','.dll','.pyc')
            z.write(p,'SUPER_CAT-COASTAL_FLIGHT/'+p.relative_to(ROOT).as_posix())
    with zipfile.ZipFile(target) as z:
        assert z.testzip() is None
        assert hashlib.sha256(z.read('SUPER_CAT-COASTAL_FLIGHT/outputs/'+ROM.name)).hexdigest()==before
    print(json.dumps(dict(rom_sha256=before,archive_sha256=sha(target),files=len(files)),indent=2))
if __name__=='__main__':main()
