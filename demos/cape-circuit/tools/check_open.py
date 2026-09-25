from pathlib import Path
import subprocess,os,re,json,csv,hashlib
R=Path(__file__).resolve().parents[1];w=R/'work/openmsx';w.mkdir(exist_ok=True)
sym=dict((n,int(v,16)) for n,v in re.findall(r'(?m)^(\w+)\s+EQU\s+0([0-9A-F]+)H',(R/'work/demo.symbols').read_text()))
s='''set save_settings_on_exit false
set throttle false
set renderer SDLGL-PP
set minframeskip 0
set maxframeskip 0
set scanline 0
set blur 0
set f [open frames.csv w]
puts $f "time,frame,page,status"
proc present {} {puts $::f "[machine_info time],[expr {[debug read memory FRAME]+256*[debug read memory NEXT]}],[debug read {VDP regs} 2],[debug read {VDP status regs} 2]"}
debug set_bp PRESENT {} {present}
'''
s=s.replace('FRAME',str(sym['frame_index'])).replace('NEXT',str(sym['frame_index']+1)).replace('PRESENT',str(sym['presented']))
for t in [5,10,15,20,25,30,40]:s+=f'after time {t} {{openmsx::internal_screenshot -raw shot-{t}.png}}\n'
s+='after time 7 {record start ./race.avi}\nafter time 34 {record stop}\n'
s+='after time 41 {close $::f;exit}\nafter realtime 140 {exit}\n'
(w/'check.tcl').write_text(s);env=os.environ.copy();env.update(OPENMSX_HOME=str(w/'home'),OPENMSX_SYSTEM_DATA='C:/Program Files/openMSX/share')
p=subprocess.run(['C:/Program Files/openMSX/openmsx.exe','-machine','Panasonic_FS-A1ST_V9968','-cart',str(R/'outputs/CAPE-CIRCUIT-V9968.rom'),'-romtype','ASCII8','-script','check.tcl'],cwd=w,env=env,capture_output=True,timeout=150,creationflags=subprocess.CREATE_NO_WINDOW)
print(p.returncode,p.stderr.decode(errors='replace'))
rows=list(csv.DictReader((w/'frames.csv').open()));print('frames',len(rows),'fps',(len(rows)-1)/(float(rows[-1]['time'])-float(rows[0]['time'])))

assert len(rows)>1000
assert all((int(b['frame'])-int(a['frame']))%320==1 for a,b in zip(rows,rows[1:]))
assert all(a['page']!=b['page'] for a,b in zip(rows,rows[1:]))
assert all(int(a['status'])&1==0 for a in rows)
assert any(int(b['frame'])<int(a['frame']) for a,b in zip(rows,rows[1:]))
result={'emulator':'openMSX installed current V9968','emulator_sha256':hashlib.sha256(Path('C:/Program Files/openMSX/openmsx.exe').read_bytes()).hexdigest(),'rom_sha256':hashlib.sha256((R/'outputs/CAPE-CIRCUIT-V9968.rom').read_bytes()).hexdigest(),'frames_checked':len(rows),'sequential':True,'loop':True,'alternating_pages':True,'command_complete_before_flip':True,'updates_per_emulated_second':(len(rows)-1)/(float(rows[-1]['time'])-float(rows[0]['time'])),'hardware_tested':False}
(R/'outputs/verification-openmsx.json').write_text(json.dumps(result,indent=2))
