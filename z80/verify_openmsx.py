"""Full-cycle comparison. Requires the user's V9968 machine definition and BIOS."""
from pathlib import Path
import argparse,csv,hashlib,json,os,re,subprocess
from build import HERE,DEMOS
def symbols(p):return dict((n,int(v,16)) for n,v in re.findall(r'(?m)^(\w+)\s+EQU\s+0([0-9A-F]+)H',p.read_text()))
def main():
 ap=argparse.ArgumentParser();ap.add_argument('--openmsx',required=True);ap.add_argument('--machine',default='Panasonic_FS-A1ST_V9968');args=ap.parse_args()
 exe=Path(args.openmsx).resolve();pasmo=os.environ.get('PASMO','pasmo');reports=[]
 for name,(source,baseline,cycle) in DEMOS.items():
  for version in ['before','after']:
   for cpu in ['Z80','R800']:
    w=HERE/'work/verify'/name/f'{version}-{cpu}';w.mkdir(parents=True,exist_ok=True)
    if version=='before':
     subprocess.run([pasmo,'--bin',str(source/'src/demo.asm'),str(w/'demo.bin'),str(w/'demo.symbols')],cwd=source,check=True)
     rom=baseline.read_bytes();sy=symbols(w/'demo.symbols')
    else:
     rom=(HERE/f'roms/{name}-auto.rom').read_bytes();sy=symbols(HERE/'work'/name/'demo.symbols')
    if cpu=='Z80':rom=rom[:8192].replace(bytes.fromhex('3e82cd8001'),bytes.fromhex('3e80cd8001'))+rom[8192:]
    (w/'test.rom').write_bytes(rom)
    tcl='''set save_settings_on_exit false
set throttle false
set renderer SDLGL-PP
set minframeskip 0
set maxframeskip 0
set scanline 0
set blur 0
set f [open frames.csv w]
set p [open flips.csv w]
puts $f "time,frame,cpu"
puts $p "status"
set count 0
proc sample {} {
 set fr [expr {[debug read memory INDEX]+256*[debug read memory NEXT]}]
 puts $::f "[machine_info time],$fr,[debug read {S1990 regs} 6]"
 if {$fr > 0 && $fr % 64 == 0} {
  set o [open vram-$fr.bin wb];fconfigure $o -translation binary
  puts -nonewline $o [debug read_block {physical VRAM} 0 262144];close $o
 }
 incr ::count
 if {$::count >= LIMIT} {close $::f;close $::p;exit}
}
debug set_bp MAIN {} {sample}
debug set_bp PRESENT {} {puts $::p [debug read {VDP status regs} 2]}
after realtime 180 {exit}
'''
    for a,b in dict(INDEX=sy['frame_index'],NEXT=sy['frame_index']+1,MAIN=sy['main_loop'],PRESENT=sy['page0'] if name=='CAPE_CIRCUIT' else sy['present_page0'],LIMIT=cycle+2).items():tcl=tcl.replace(a,str(b))
    (w/'check.tcl').write_text(tcl)
    env=os.environ.copy();env.update(OPENMSX_HOME=str(w/'home'),OPENMSX_SYSTEM_DATA=str(exe.parent/'share'))
    proc=subprocess.run([str(exe),'-machine',args.machine,'-cart',str(w/'test.rom'),'-romtype','ASCII8','-script','check.tcl'],cwd=w,env=env,capture_output=True,timeout=190,creationflags=getattr(subprocess,'CREATE_NO_WINDOW',0))
    rows=list(csv.DictReader((w/'frames.csv').open()));flips=list(csv.DictReader((w/'flips.csv').open()))
    assert len(rows)>=cycle+2,(name,version,cpu,proc.stderr)
    assert all((int(b['frame'])-int(a['frame']))%cycle==1 for a,b in zip(rows,rows[1:]))
    assert any(int(b['frame'])<int(a['frame']) for a,b in zip(rows,rows[1:]))
    assert flips and all(int(p['status'])&65==64 for p in flips),'Flip outside VBlank or before command completion'
    cpu_values=sorted(set(int(r['cpu']) for r in rows));assert cpu_values==([96] if cpu=='Z80' else [0])
    samples={}
    for p in w.glob('vram-*.bin'):
     assert p.stat().st_size==262144;samples[p.name]=hashlib.sha256(p.read_bytes()).hexdigest()
    assert len(samples)==(cycle-1)//64
    rows=rows[2:];fps=(len(rows)-1)/(float(rows[-1]['time'])-float(rows[0]['time']))
    reports.append(dict(name=name,version=version,cpu=cpu,rom_sha256=hashlib.sha256(rom).hexdigest(),updates_per_emulated_second=fps,frames_checked=len(rows),sequential=True,loop=True,flips_in_blank_and_command_idle=True,cpu_register6=cpu_values,samples=samples))
    print(name,version,cpu,round(fps,3),flush=True)
 for n in DEMOS:
  for c in ['Z80','R800']:
   pair=[r for r in reports if r['name']==n and r['cpu']==c]
   assert pair[0]['samples']==pair[1]['samples'],(n,c,'VRAM changed')
 result=dict(date='2026-10-05',machine=args.machine,emulator_sha256=hashlib.sha256(exe.read_bytes()).hexdigest(),hardware_tested=False,results=reports)
 (HERE/'verification-openmsx.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
