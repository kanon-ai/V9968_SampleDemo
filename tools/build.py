"""Build both explicit V9968 register profiles with Pasmo; never include BIOS."""
from pathlib import Path
import os
import subprocess
import hashlib
import json
import shutil
import generate

ROOT = Path(__file__).resolve().parents[1]


def build():
    generate.generate()
    out, work = ROOT/'outputs', ROOT/'work/build'
    out.mkdir(exist_ok=True)
    work.mkdir(parents=True, exist_ok=True)
    pasmo = os.environ.get('PASMO') or shutil.which('pasmo') or 'C:/Software/Pasmo/pasmo.exe'
    if not Path(pasmo).exists():
        raise SystemExit('Set PASMO to the Pasmo assembler executable.')
    subprocess.run([pasmo,'--bin','src/boot.asm',str(work/'boot.bin')],cwd=ROOT,check=True)
    boot=(work/'boot.bin').read_bytes()
    assert len(boot)==8192 and boot[:2]==b'AB'
    results=[]
    for profile in ['current','legacy-openmsx','legacy-openmsx-internal']:
        source=ROOT/'src/demo.asm'
        wrapper=f'LEGACY equ {int(profile.startswith("legacy"))}\nVDP_BASE equ {0x98 if profile.endswith("internal") else 0x88}\ninclude "src/demo.asm"\n'
        (work/'profile.asm').write_text(wrapper,encoding='ascii')
        binary=work/f'demo-{profile}.bin'
        symbols=work/f'demo-{profile}.symbols'
        subprocess.run([pasmo,'--bin',str(work/'profile.asm'),str(binary),str(symbols)],cwd=ROOT,check=True)
        runtime=binary.read_bytes()
        assert len(runtime)<=0x6000,'Runtime exceeds 8000-DFFF'
        rom=boot+runtime+bytes([255])*(0x6000-len(runtime))
        for name in ['background.bin','sprites.bin','motion.bin']:
            data=(ROOT/'assets'/name).read_bytes()
            assert len(data)==32768
            rom+=data
        assert len(rom)==131072
        name=f'PRISM_FLIGHT-V9968-{profile}.rom'
        (out/name).write_bytes(rom)
        results.append({'file':name,'mapper':'ASCII8','rom_bytes':len(rom),'runtime_bytes':len(runtime),
            'profile':profile,'sha256':hashlib.sha256(rom).hexdigest(),
            'display':'SCREEN5 256x212, RGB5 palettes, LRMM, Sprite mode3',
            'runtime_validation':'see verification.json for matching ROM hash','hardware_validation':False})
    (out/'build-manifest.json').write_text(json.dumps(results,indent=2)+'\n',encoding='utf-8')
    print(json.dumps(results,indent=2))


if __name__=='__main__':
    build()
