from pathlib import Path
import re,os,subprocess,json
P=Path(__file__).resolve().parent
sy=dict((n,int(v,16)) for n,v in re.findall(r'(?m)^(\w+)\s+EQU\s+0([0-9A-F]+)H',(P/'work/INTERNAL-98.sym').read_text()))
w=P/'work/edges';w.mkdir(exist_ok=True)
t='set save_settings_on_exit false\nset throttle false\nset injected 0\n'
# Seed immediately before the first captured block, after counters are initialized.
t+=f'''debug set_bp {sy['restart']} {{}} {{debug write memory {sy['pattern']} 0;debug write memory {sy['continuous']} 1}}
debug set_bp {sy['captured']} {{$::injected<3}} {{
 if {{$::injected==0}} {{debug write memory {sy['errors']} 254;debug write memory {sy['errors']+1} 255;debug write memory {sy['bits_up']} 254;debug write memory {sy['bits_up']+1} 255}}
 debug write memory {sy['actual']+5} 129
 incr ::injected
}}
set donebp [debug set_bp {sy['result_ready']} {{}} {{debug remove_bp $::donebp;after time 0.2 {{set o [open ram.bin wb];fconfigure $o -translation binary;puts -nonewline $o [debug read_block memory 32768 16384];close $o;exit}}}}]
after realtime 60 {{exit}}
'''
(w/'check.tcl').write_text(t);env=os.environ.copy();env['OPENMSX_HOME']=str(w/'home')
r=subprocess.run(['C:/Program Files/openMSX/openmsx.exe','-machine','Panasonic_FS-A1ST_V9968','-cart',str(P/'out/V9968-VRAM-DIAG-INTERNAL-98.rom'),'-romtype','Normal','-script','check.tcl'],cwd=w,env=env,capture_output=True,timeout=70)
b=(w/'ram.bin').read_bytes()
def word(k,o=0):return int.from_bytes(b[sy[k]-32768+o:sy[k]-32768+o+2],'little')
assert word('errors')==65535 and word('bits_up')==65535 and word('bits_up',14)==3
assert word('passes')==1 and b[sy['phase']-32768]==3
(P/'out/verification-edges.json').write_text(json.dumps(dict(counter_saturation=True,auto_stops_after_error_pass=True,passes=1,errors=65535,bit0=65535,bit7=3),indent=2))
print('Saturation and auto-stop: OK')
