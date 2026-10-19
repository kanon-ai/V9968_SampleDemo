"""Full-cycle tests of both VDP profiles. Requires separately installed BIOS/emulator."""
from pathlib import Path
import argparse, csv, hashlib, json, os, re, shutil, subprocess
from build import HERE, ROOT

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--openmsx', required=True)
    ap.add_argument('--name')
    args = ap.parse_args()
    exe = Path(args.openmsx).resolve()
    reports = []
    for item in json.loads((HERE/'manifest.json').read_text()):
        name, profile, cpu = (item[k] for k in ('name','profile','cpu'))
        if args.name and name != args.name:
            continue
        external = profile == 'EXTERNAL-88'
        w = HERE/'work/verify'/name/f'{profile}-{cpu}'
        w.mkdir(parents=True, exist_ok=True)
        sy = dict((n,int(v,16)) for n,v in re.findall(r'(?m)^(\w+)\s+EQU\s+0([0-9A-F]+)H', (HERE/f'work/{name}/{profile}/demo.symbols').read_text()))
        vram = 'physical V9968 VRAM' if external else 'physical VRAM'
        status = 'V9968 status regs' if external else 'VDP status regs'
        present = sy.get('page0',sy.get('present_page0'))
        assert present is not None, name
        counters = [k for k in ('irq_counts','vblank_counts','raster_counts') if k in sy]
        counter_code = '\n'.join(f'puts $o "{k} [expr {{[debug read memory {sy[k]}]+256*[debug read memory {sy[k]+1}]}}]"' for k in counters)
        tcl = '''set save_settings_on_exit false
set throttle false
set renderer SDLGL-PP
set minframeskip 0
set maxframeskip 0
set f [open frames.csv w]
set p [open flips.csv w]
puts $f "time,frame,cpu"
puts $p "status"
set count 0
proc sample {} {
 set fr [expr {[debug read memory @INDEX@]+256*[debug read memory @NEXT@]}]
 puts $::f "[machine_info time],$fr,[debug read {S1990 regs} 6]"
 if {$::count == 64 || $::count == 256} {
  set o [open vram-$::count.bin wb];fconfigure $o -translation binary
  puts -nonewline $o [debug read_block {@VRAM@} 0 262144];close $o
 }
 incr ::count
 if {$::count >= @LIMIT@} {
  debug remove_bp $::samplebp
  debug remove_bp $::flipbp
  close $::f;close $::p
  set o [open counters.txt w]
  @COUNTERS@
  close $o
  exit
 }
}
set samplebp [debug set_bp @MAIN@ {} {sample}]
set flipbp [debug set_bp @PRESENT@ {} {puts $::p [debug read {@STATUS@} 2]}]
after realtime 180 {exit}
'''
        for key,value in dict(INDEX=sy['frame_index'],NEXT=sy['frame_index']+1,VRAM=vram,LIMIT=item['frames']+2,COUNTERS=counter_code,VIDEO='V9968' if external else 'MSX',MAIN=sy['main_loop'],PRESENT=present,STATUS=status).items():
            tcl = tcl.replace('@'+key+'@',str(value))
        (w/'check.tcl').write_text(tcl)
        env = os.environ.copy()
        env.update(OPENMSX_HOME=str(w/'home'), OPENMSX_SYSTEM_DATA=str(exe.parent/'share'))
        cmd = [str(exe),'-machine','Panasonic_FS-A1ST' if external else 'Panasonic_FS-A1ST_V9968']
        if external:
            user = w/'user'
            (user/'extensions').mkdir(parents=True,exist_ok=True)
            shutil.copyfile(ROOT/'diagnostics/vram-read-lab/config/HRA_V9968.xml',user/'extensions/HRA_V9968.xml')
            env['OPENMSX_USER_DATA'] = str(user)
            cmd += ['-ext','HRA_V9968']
        cmd += ['-cart',str(HERE/item['file']),'-romtype','ASCII8','-script','check.tcl']
        result = subprocess.run(cmd,cwd=w,env=env,capture_output=True,timeout=190,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
        (w/'stderr.txt').write_bytes(result.stderr)
        rows = list(csv.DictReader((w/'frames.csv').open()))
        flips = list(csv.DictReader((w/'flips.csv').open()))
        assert len(rows) == item['frames']+2, (name,profile,len(rows),result.stderr)
        assert all((int(b['frame'])-int(a['frame']))%item['frames']==1 for a,b in zip(rows,rows[1:])), name
        assert any(int(b['frame'])<int(a['frame']) for a,b in zip(rows,rows[1:])), name
        assert flips and all(int(r['status'])&65==64 for r in flips), (name,profile,'unsafe flip')
        assert set(int(r['cpu']) for r in rows) == ({96} if cpu=='Z80' else {0})
        counts = dict((k,int(v)) for k,v in (line.split() for line in (w/'counters.txt').read_text().splitlines()))
        assert all(v>0 for v in counts.values()), counts
        # 256x212 bitmap page tails are outside the displayed image. The
        # internal BIOS initializes these; the second VDP starts independently.
        samples = {}
        for p in sorted(w.glob('vram-*.bin')):
            data=p.read_bytes()
            assert len(data)==262144
            if name in ('MIST_VALE','LUMEN_FORGE','CATSTRIDER'):
                visible_and_assets=data[:54272]+data[65536:119808]+data[131072:]
            else:
                visible_and_assets=data[:27136]+data[32768:59904]+data[65536:]
            samples[p.name]=hashlib.sha256(visible_and_assets).hexdigest()
        assert len(samples)==2
        fps = (len(rows)-3)/(float(rows[-1]['time'])-float(rows[2]['time']))
        reports.append(dict(name=name,profile=profile,cpu=cpu,rom_sha256=item['sha256'],frames_checked=len(rows),sequential=True,loop=True,flips_in_blank_and_command_idle=True,irq_counters=counts,updates_per_emulated_second=fps,vram_samples=samples))
        print(name,profile,cpu,round(fps,3),'OK',flush=True)
    for entry in reports:
        if entry['profile']=='EXTERNAL-88':
            baseline=next(r for r in reports if r['name']==entry['name'] and r['cpu']==entry['cpu'] and r['profile']=='INTERNAL-98')
            entry['vram_matches_internal']=entry['vram_samples']==baseline['vram_samples']
            assert entry['vram_matches_internal'], (entry['name'],'VRAM differs')
    output = HERE/('verification-'+args.name+'.json' if args.name else 'verification-openmsx.json')
    output.write_text(json.dumps(dict(date='2026-10-19',emulator_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),hardware_tested=False,external_bluemsx_tested=False,results=reports),indent=2)+'\n')

if __name__ == '__main__':
    main()
