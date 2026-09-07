"""Run the user-installed V9968 openMSX. Only this child process is controlled."""
from pathlib import Path
import subprocess, os, re

ROOT=Path(__file__).resolve().parents[1]
EXE=Path(os.environ.get('OPENMSX_EXE','C:/Program Files/openMSX/openmsx.exe'))

def run(script, profile='legacy-openmsx-internal', timeout=90):
    work=ROOT/'work/emulator'
    work.mkdir(parents=True,exist_ok=True)
    (work/'check-error.txt').unlink(missing_ok=True)
    guarded='if {[catch {\n'+script+'\n} err opts]} {set f [open check-error.txt w]; puts $f $err; puts $f $opts; close $f; exit}\n'
    (work/'check.tcl').write_text(guarded,encoding='utf-8')
    env=os.environ.copy()
    env.update(OPENMSX_SYSTEM_DATA=os.environ.get('OPENMSX_SYSTEM_DATA',str(EXE.parent/'share')),OPENMSX_HOME='./home',OPENMSX_USER_DATA='./user')
    args=[str(EXE),'-machine','Panasonic_FS-A1ST_V9968' if profile.endswith('internal') else 'Panasonic_FS-A1ST']
    if not profile.endswith('internal'): args+=['-ext','HRA_V9968']
    args+=['-cart',f'../../outputs/LUMEN_FORGE-V9968-{profile}.rom','-romtype','ASCII8','-script','check.tcl']
    result=subprocess.run(args,cwd=work,env=env,timeout=timeout,creationflags=subprocess.CREATE_NO_WINDOW)
    print('openMSX exit:',result.returncode)
    if (work/'check-error.txt').exists():
        raise RuntimeError((work/'check-error.txt').read_text())
    if result.returncode: raise RuntimeError('openMSX did not exit successfully')

if __name__=='__main__':
    symbols=(ROOT/'work/build/demo-legacy-openmsx-internal.symbols').read_text()
    address=int(re.search(r'frame_index\s+EQU 0([0-9A-F]+)H',symbols)[1],16)
    run('''set save_settings_on_exit false
set throttle false
set minframeskip 0
set maxframeskip 0
set renderer SDLGL-PP
set scale_factor 2
set scanline 0
set blur 0
set deinterlace true
proc capture {} { if {[catch {
  set f [open check-state.txt w]
  puts $f "machine=[machine_info config_name]"
  puts $f "cpu=[binary encode hex [debug read_block {CPU regs} 0 28]]"
  puts $f "s1990=[binary encode hex [debug read_block {S1990 regs} 0 16]]"
  puts $f "regs=[binary encode hex [debug read_block {VDP regs} 0 64]]"
  puts $f "frame=[debug read memory FRAME_ADDRESS],[debug read memory FRAME_NEXT]"
  puts $f "attributes=[binary encode hex [debug read_block {physical VRAM} 28672 120]]"
  puts $f "background=[binary encode hex [debug read_block {physical VRAM} 131072 32]]"
  close $f
  openmsx::internal_screenshot -raw ../../outputs/emulator-first.png
} err opts]} {set f [open check-error.txt w]; puts $f $err; puts $f $opts; close $f}; exit
}
after time 10 capture
'''.replace('FRAME_ADDRESS',str(address)).replace('FRAME_NEXT',str(address+1)))
