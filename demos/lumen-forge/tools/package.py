"""Rebuild and package only original demo files, no BIOS or emulator."""
from pathlib import Path
from zipfile import ZipFile,ZIP_DEFLATED
import hashlib,json,subprocess,sys
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'

if __name__=='__main__':
    before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*.rom')}
    subprocess.run([sys.executable,'tools/build.py'],cwd=ROOT,check=True)
    after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in OUT.glob('*.rom')}
    assert before==after
    report=json.loads((OUT/'verification.json').read_text())
    for r in report['verified']: assert r['sha256']==after[f'LUMEN_FORGE-V9968-{r["profile"]}.rom']
    internal=after['LUMEN_FORGE-V9968-legacy-openmsx-internal.rom']
    assert json.loads((OUT/'alpha-verification.json').read_text())['frozen_background_comparison']
    for name in ['alpha-verification.json','motion-verification.json','video-verification.json']:
        assert json.loads((OUT/name).read_text())['rom_sha256']==internal, name+' belongs to a different ROM'
    for profile in ['legacy-openmsx-internal','legacy-openmsx']:
        transform=json.loads((OUT/f'transform-verification-{profile}.json').read_text())
        assert transform['passed'] and transform['rom_sha256']==after[f'LUMEN_FORGE-V9968-{profile}.rom']
    (OUT/'reproducibility.json').write_text(json.dumps({'asset_regeneration_identical':True,'sha256':after},indent=2)+'\n')
    files=[ROOT/n for n in ['README.md','TECHNIQUES.md','COPYRIGHT.md','DISCLAIMER.md','THIRD_PARTY_NOTICES.md','requirements.txt','run-demo.cmd','.gitignore']]
    for folder in ['src','tools','assets']:
        files += [p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [p for p in OUT.iterdir() if p.suffix in ['.rom','.json','.gif','.png','.mp4'] and p.name!='emulator-first.png']
    target=OUT/'LUMEN_FORGE-source-and-ROM.zip'
    with ZipFile(target,'w',ZIP_DEFLATED) as z:
        for p in sorted(files): z.write(p,Path('LUMEN_FORGE')/p.relative_to(ROOT))
    with ZipFile(target) as z:
        assert z.testzip() is None
        assert not any('/work/' in n or n.endswith('.exe') or 'systemroms' in n for n in z.namelist())
    print(target)
