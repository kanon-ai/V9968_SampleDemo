from pathlib import Path
import re,os,subprocess,json
P=Path(__file__).resolve().parent
sy=dict((n,int(v,16)) for n,v in re.findall(r'(?m)^(\w+)\s+EQU\s+0([0-9A-F]+)H',(P/'work/INTERNAL-98.sym').read_text()))
w=P/'work/controls';w.mkdir(exist_ok=True)
t=f'''set save_settings_on_exit false
set throttle false
set stage 0
set f [open result.txt w]
debug set_bp {sy['result_ready']} {{$::stage==0}} {{set ::stage 1;keymatrixdown 0 8;after time 0.02 {{keymatrixup 0 8}}}}
debug set_bp {sy['restart']} {{$::stage==1}} {{puts $::f [debug read memory {sy['cpu']}];close $::f;exit}}
after realtime 60 {{close $::f;exit}}
'''
(w/'check.tcl').write_text(t)
env=os.environ.copy();env['OPENMSX_HOME']=str(w/'home')
r=subprocess.run(['C:/Program Files/openMSX/openmsx.exe','-machine','Panasonic_FS-A1ST_V9968','-cart',str(P/'out/V9968-VRAM-DIAG-INTERNAL-98.rom'),'-romtype','Normal','-script','check.tcl'],cwd=w,env=env,capture_output=True,timeout=70)
assert (w/'result.txt').read_text().strip()=='2',(r.stderr,(w/'result.txt').read_text())
(P/'out/verification-controls.json').write_text(json.dumps(dict(key='3',matrix_row=0,matrix_mask=8,result_cpu=2,restart_after_release=True),indent=2))
print('Keyboard 3 -> R800 DRAM restart: OK')
