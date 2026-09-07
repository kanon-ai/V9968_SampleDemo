"""Build 512KiB ASCII8 ROMs, keeping user BIOS outside the project."""
from pathlib import Path
import os,shutil,subprocess,hashlib,json
import generate
ROOT=Path(__file__).resolve().parents[1]

def build():
    generate.generate()
    out,work=ROOT/'outputs',ROOT/'work/build'
    out.mkdir(exist_ok=True); work.mkdir(parents=True,exist_ok=True)
    pasmo=os.environ.get('PASMO') or shutil.which('pasmo') or 'C:/Software/Pasmo/pasmo.exe'
    subprocess.run([pasmo,'--bin','src/boot.asm',str(work/'boot.bin')],cwd=ROOT,check=True)
    boot=(work/'boot.bin').read_bytes(); assert len(boot)==8192 and boot[:2]==b'AB'
    report=[]
    for profile,port in [('legacy-openmsx-internal',0x98),('legacy-openmsx',0x88)]:
        (work/'profile.asm').write_text(f'VDP_BASE equ {port}\ninclude "src/demo.asm"\n')
        binary=work/f'demo-{profile}.bin'
        subprocess.run([pasmo,'--bin',str(work/'profile.asm'),str(binary),str(work/f'demo-{profile}.symbols')],cwd=ROOT,check=True)
        runtime=binary.read_bytes(); assert len(runtime)<=24576
        upload=(ROOT/'assets/vram-upload.bin').read_bytes(); motion=(ROOT/'assets/motion.bin').read_bytes()
        assert len(upload)==131072 and len(motion)==262144
        rom=boot+runtime+bytes([255])*(24576-len(runtime))+upload+motion
        assert len(rom)==425984
        rom+=bytes([255])*(524288-len(rom))
        name=f'MIST_VALE-V9968-{profile}.rom'; (out/name).write_bytes(rom)
        report.append({'file':name,'mapper':'ASCII8','rom_bytes':len(rom),'runtime_bytes':len(runtime),
          'sha256':hashlib.sha256(rom).hexdigest(),'profile':profile,'hardware_verified':False})
    (out/'build-manifest.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__': build()
