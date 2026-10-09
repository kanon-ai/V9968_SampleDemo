from pathlib import Path
import re,os,subprocess,json,hashlib,shutil
P=Path(__file__).resolve().parent
EXE=Path('C:/Program Files/openMSX/openmsx.exe')
reports=[]
def run(name,cpu=0,gap=0,pattern=3,display=1,external=False,inject=False,baseline=False,passes=1):
 variant='EXTERNAL-88' if external else 'INTERNAL-98'
 sy=dict((n,int(v,16)) for n,v in re.findall(r'(?m)^(\w+)\s+EQU\s+0([0-9A-F]+)H',(P/f'work/{variant}.sym').read_text()))
 w=P/'work/verify'/name;w.mkdir(parents=True,exist_ok=True)
 t='''set save_settings_on_exit false
set throttle false
set renderer SDLGL-PP
set minframeskip 0
set maxframeskip 0
set injected 0
set modes {}
proc done {} {
 debug remove_bp $::donebp
 set v [catch {set videosource V9968} msg]
 set q [open video.txt w];puts $q [openmsx_info setting videosource];puts $q "$v $msg";puts $q [help screenshot];close $q
 set o [open ram.bin wb];fconfigure $o -translation binary;puts -nonewline $o [debug read_block memory 32768 16384];close $o
 set o [open modes.txt w];puts $o $::modes;close $o
 set throttle true
 after realtime 0.5 {screenshot -raw -size 640 screen.png;exit}
}
'''
 setup=';'.join(f'debug write memory {sy[k]} {v}' for k,v in dict(cpu=cpu,gap=gap,pattern=pattern,display_on=display,continuous=int(passes>1)).items())
 t+=f'debug set_bp {sy["restart"]} {{}} {{{setup}}}\n'
 t+=f'set donebp [debug set_bp {sy["result_ready"]} {{[debug read memory {sy["passes"]}]>={passes}}} {{done}}]\n'
 if external:
  t+='catch {set videosource V9968}\n'
 t+=f'debug set_watchpoint read_io {136 if external else 152} {{[reg PC]>={sy["read_fast"]} && [reg PC]<{sy["expected"]} && [llength $::modes]==0}} {{lappend ::modes [debug read {{S1990 regs}} 6]}}\n'
 if inject:
  target=sy['compare'] if baseline else sy['captured']
  cond=f'[debug read memory {sy["test_kind"]}]==0 && ' if baseline else ''
  t+=f'debug set_bp {target} {{{cond}$::injected==0}} {{debug write memory {sy["actual"]+5} 129;set ::injected 1}}\n'
 t+='after realtime 90 {exit}\n'
 (w/'check.tcl').write_text(t)
 env=os.environ.copy();env['OPENMSX_HOME']=str(w/'home')
 args=[str(EXE),'-machine','Panasonic_FS-A1ST' if external else 'Panasonic_FS-A1ST_V9968']
 if external:
  user=w/'user';(user/'extensions').mkdir(parents=True,exist_ok=True)
  shutil.copyfile(P/'config/HRA_V9968.xml',user/'extensions/HRA_V9968.xml')
  env['OPENMSX_USER_DATA']=str(user);args+=['-ext','HRA_V9968']
 args+=['-cart',str(P/f'out/V9968-VRAM-DIAG-{variant}.rom'),'-romtype','Normal','-script','check.tcl']
 r=subprocess.run(args,cwd=w,env=env,capture_output=True,timeout=100)
 (w/'stderr.txt').write_bytes(r.stderr)
 assert (w/'ram.bin').exists(),(name,r.stderr)
 ram=(w/'ram.bin').read_bytes()
 def byte(k):return ram[sy[k]-32768]
 def word(k):return int.from_bytes(ram[sy[k]-32768:sy[k]-32768+2],'little')
 result=dict(rom_sha256=hashlib.sha256((P/f'out/V9968-VRAM-DIAG-{variant}.rom').read_bytes()).hexdigest(),name=name,cpu=cpu,gap=gap,pattern=pattern,display=display,external=external,injected=inject,baseline_fault=baseline,passes=word('passes'),blocks=word('blocks'),baseline_errors=word('baseline_errors'),errors=word('errors'),first={k:byte('first_'+k) for k in ['valid','bank','chunk','offset','expected','actual','xor','retry']},bits_up=[int.from_bytes(ram[sy['bits_up']-32768+i*2:sy['bits_up']-32768+i*2+2],'little') for i in range(8)],bits_down=[int.from_bytes(ram[sy['bits_down']-32768+i*2:sy['bits_down']-32768+i*2+2],'little') for i in range(8)],cpu_status=(w/'modes.txt').read_text().strip())
 assert result['passes']==passes and result['blocks']==4800*passes,result
 assert result['cpu_status']==str([96,64,0][cpu]),result
 if inject:
  assert result['baseline_errors']==int(baseline) and result['errors']==int(not baseline),result
  if not baseline:
   ex=0 if pattern==0 else 255
   assert result['first']==dict(valid=1,bank=1,chunk=0,offset=5,expected=ex,actual=129,xor=ex^129,retry=ex),result
   assert result['bits_up']==([1,0,0,0,0,0,0,1] if ex==0 else [0]*8),result
   assert result['bits_down']==([0,1,1,1,1,1,1,0] if ex==255 else [0]*8),result
 else:assert result['errors']==0 and result['baseline_errors']==0,result
 reports.append(result);print(name,'OK',flush=True)
 (P/'out/verification-openmsx.json').write_text(json.dumps(dict(emulator_sha256=hashlib.sha256(EXE.read_bytes()).hexdigest(),hardware_tested=False,tests=reports),indent=2))
if __name__=='__main__':
 for cpu in range(3):
  for gap in range(3):run(f'cpu{cpu}-gap{gap}',cpu,gap)
 run('display-off',2,0,3,0)
 run('external',2,0,external=True)
 run('inject-up',2,0,0,inject=True)
 run('inject-down',2,0,1,inject=True)
 run('inject-baseline',2,0,0,inject=True,baseline=True)
 for pattern in [2,4,5,6,7,8,9,10,11]:run(f'pattern{pattern}',2,0,pattern)
 run('continuous-two-passes',2,0,passes=2)
