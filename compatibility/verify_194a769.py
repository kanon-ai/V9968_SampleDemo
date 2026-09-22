from pathlib import Path
import os,subprocess,re,csv,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'work/verify-194a769'
BASE.mkdir(parents=True,exist_ok=True)
import shutil
for category in ('machines','extensions'):
 (BASE/'user'/category).mkdir(parents=True,exist_ok=True)
 for p in (ROOT/'compatibility'/category).glob('*.xml'):shutil.copy2(p,BASE/'user'/category/p.name)
EXE=Path(os.environ.get('OPENMSX_EXE','C:/Program Files/openMSX/openmsx.exe'))
SCRIPT=r'''
set save_settings_on_exit false
set throttle false
set renderer SDLGL-PP
set minframeskip 0
set maxframeskip 0
set scanline 0
set blur 0
VIDEO
set ::n 0
set ::f [open frames.csv w]
puts $::f "time,frame,page,status,cpu"
proc fail {err} {set f [open error.txt w];puts $f $err;close $f;exit}
proc present {} {
 if {[catch {
  set frame [expr {[debug read memory FRAME]+256*[debug read memory NEXT]}]
  set page [expr {([debug read {REGS} 2]>>5)&1}]
  puts $::f "[machine_info time],$frame,$page,[debug read {STATUS} 2],[debug read {S1990 regs} 6]"
  if {($::n%127)==0} {
   set f [open "sat-$::n.bin" wb];puts -nonewline $f [debug read_block {VRAM} [expr {57344+$page*1024}] SATSIZE];close $f
   set f [open "expected-$::n.bin" wb];puts -nonewline $f [debug read_block memory RECORD SATDATA];close $f
   set f [open "top-$::n.bin" wb];puts -nonewline $f [debug read_block {VRAM} [expr {$page*65536}] TOPSIZE];close $f
  }
  incr ::n
 } e]} {fail $e}
}
proc finish {} {
 if {[catch {
  close $::f
  set f [open upload.bin wb];puts -nonewline $f [debug read_block {VRAM} 131072 UPLOAD];close $f
  openmsx::internal_screenshot -raw ./shot.png
 } e]} {fail $e}
 exit
}
debug set_bp PRESENT {} {present}
CAPTURE
after time 65 finish
after realtime 170 {fail timeout}
'''
results=[]
for folder,name,offset,count,top,upload in [('demos/lumen-forge','LUMEN_FORGE',8,112,212*256,65536),('demos/mist-vale','MIST_VALE',80,96,48*256,131072),('demos/catstrider','CATSTRIDER',112,128,100*256,98304)]:
 r=ROOT/folder
 for internal in (True,False):
  profile='openmsx-194a769-'+('internal' if internal else 'external')
  w=BASE/('verify-'+name+'-'+str(internal));w.mkdir(exist_ok=True);(w/'home').mkdir(exist_ok=True)
  sym=dict((n,int(v,16)) for n,v in re.findall(r'(?m)^(\w+)\s+EQU\s+0([0-9A-F]+)H',(r/f'work/build-194a769/{profile}.symbols').read_text()))
  script=SCRIPT
  values={'VIDEO':'' if internal else 'after time 1 {set videosource V9968}', 'REGS':'VDP regs' if internal else 'V9968 regs','STATUS':'VDP status regs' if internal else 'V9968 status regs','VRAM':'physical VRAM' if internal else 'physical V9968 VRAM','FRAME':sym['frame_index'],'NEXT':sym['frame_index']+1,'PRESENT':sym['animate_palette'],'RECORD':57344+offset,'SATDATA':count,'SATSIZE':count+8,'TOPSIZE':top,'UPLOAD':upload,'CAPTURE':'after time 10 {record start ./native.avi}\nafter time 22 {record stop}' if internal else ''}
  for k in sorted(values,key=len,reverse=True):script=script.replace(k,str(values[k]))
  (w/'check.tcl').write_text('if {[catch {\n'+script+'\n} e]} {set f [open error.txt w];puts $f $e;close $f;exit}\n')
  env=os.environ.copy();env.update(OPENMSX_HOME=str(w/'home'),OPENMSX_USER_DATA=str(BASE/'user'),OPENMSX_SYSTEM_DATA='C:/Program Files/openMSX/share')
  rom=r/f'outputs/{name}-V9968-{profile}.rom'
  args=[str(EXE),'-machine','Panasonic_FS-A1ST_V9968_Demos_194a769' if internal else 'Panasonic_FS-A1ST']
  if not internal:args+=['-ext','HRA_V9968_Demos_194a769']
  args+=['-cart',str(rom),'-romtype','ASCII8','-script','check.tcl']
  subprocess.run(args,cwd=w,env=env,timeout=180,creationflags=subprocess.CREATE_NO_WINDOW,check=True)
  assert not (w/'error.txt').exists(),(w/'error.txt').read_text()
  rows=list(csv.DictReader((w/'frames.csv').open()));assert len(rows)>1500
  modulus=1536 if name=='CATSTRIDER' else 1024
  assert all((int(b['frame'])-int(a['frame']))%modulus==1 for a,b in zip(rows,rows[1:]))
  assert any(int(b['frame'])<int(a['frame']) for a,b in zip(rows,rows[1:]))
  assert all(a['page']!=b['page'] for a,b in zip(rows,rows[1:]))
  assert all(int(a['status'])&1==0 and int(a['cpu'])&96==0 for a in rows)
  expected=(r/'work/build-194a769/upload.bin').read_bytes()[:upload]
  assert (w/'upload.bin').read_bytes()==expected
  for sat in w.glob('sat-*.bin'):
   tag=sat.stem[4:];assert sat.read_bytes()==(w/f'expected-{tag}.bin').read_bytes()+bytes([216,0,0,0,0,0,0,0])
   assert (w/f'top-{tag}.bin').read_bytes()==(r/'assets/background-indexed.bin').read_bytes()[:top],tag
  intervals=[(float(b['time'])-float(a['time']))*59.92274 for a,b in zip(rows,rows[1:])]
  assert all(abs(t-(2 if name=='CATSTRIDER' else 1))<0.1 for t in intervals),(min(intervals),max(intervals))
  result=dict(demo=name,profile=profile,rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest(),emulator_sha256=hashlib.sha256(EXE.read_bytes()).hexdigest(),machine='V9968_OLD',seconds=65,updates=len(rows),updates_per_second=(len(rows)-1)/(float(rows[-1]['time'])-float(rows[0]['time'])),loop=True,alternating_pages=True,source_upload_exact=True,sampled_sat_exact=True,both_page_backgrounds_exact=True,hardware_tested=False)
  results.append(result);(BASE/'linear-verification.json').write_text(json.dumps(results,indent=2));print(result,flush=True)
