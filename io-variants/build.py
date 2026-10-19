"""Build internal/external editions without changing published artwork or motion."""
from pathlib import Path
import hashlib, json, os, re, shutil, subprocess

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
NAMES = ['PRISM_FLIGHT', 'SUPER_CAT-COASTAL_FLIGHT', 'LUMEN_FORGE',
         'MIST_VALE', 'CATSTRIDER', 'CAPE_CIRCUIT']
CYCLES = [512, 2048, 1024, 1024, 1536, 320]

def main():
    pasmo = os.environ.get('PASMO') or shutil.which('pasmo')
    if not pasmo:
        raise SystemExit('Set PASMO or add pasmo to PATH.')
    (HERE/'roms').mkdir(parents=True, exist_ok=True)
    entries = []
    for name, cycle in zip(NAMES, CYCLES):
        optimized = name in ('CATSTRIDER', 'CAPE_CIRCUIT')
        source = ROOT/('demos/cape-circuit' if name == 'CAPE_CIRCUIT' else f'current/demos/{name}')
        asm = ROOT/f'z80/src/{name}.asm' if optimized else source/'src/demo.asm'
        original = asm.read_text()
        for profile, port in [('INTERNAL-98', '098h'), ('EXTERNAL-88', '088h')]:
            work = HERE/'work'/name/profile
            work.mkdir(parents=True, exist_ok=True)
            text, count = re.subn(r'(?m)^VDP_BASE\s+equ\s+(?:152|098h)\b', f'VDP_BASE equ {port}', original)
            assert count == 1, (name, 'VDP_BASE declaration')
            (work/'demo.asm').write_text(text)
            subprocess.run([pasmo, '--bin', str(work/'demo.asm'), str(work/'demo.bin'), str(work/'demo.symbols')], cwd=source, check=True)
            code = (work/'demo.bin').read_bytes()
            assert len(code) <= 24576
            for cpu in (['auto', 'Z80'] if optimized else ['auto']):
                baseline = ROOT/(f'z80/roms/{name}-{cpu}.rom' if optimized else f'current/roms/{name}-V9968-current-internal.rom')
                old = baseline.read_bytes()
                rom = old[:8192] + code.ljust(24576, b'\xff') + old[32768:]
                assert len(rom) == len(old)
                if profile == 'INTERNAL-98':
                    assert rom == old, (name, cpu, 'Internal ROM changed')
                file = f'roms/{name}-{profile}-{cpu}.rom'
                (HERE/file).write_bytes(rom)
                entries.append(dict(name=name, profile=profile, cpu=cpu, file=file,
                    bytes=len(rom), sha256=hashlib.sha256(rom).hexdigest(),
                    source=str(asm.relative_to(ROOT)).replace('\\', '/'),
                    baseline=str(baseline.relative_to(ROOT)).replace('\\', '/'),
                    baseline_sha256=hashlib.sha256(old).hexdigest(), frames=cycle,
                    synchronization='private IM2' if name in ('MIST_VALE','CATSTRIDER') else 'status polling'))
    (HERE/'manifest.json').write_text(json.dumps(entries, indent=2)+'\n')
    print(f'Built {len(entries)} ROMs; all internal editions byte-identical to published baselines.')

if __name__ == '__main__':
    main()
