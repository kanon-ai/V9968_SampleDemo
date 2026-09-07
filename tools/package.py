"""Package only the original demo, excluding emulator, BIOS and temporary files."""
from pathlib import Path
from zipfile import ZipFile, ZIP_DEFLATED
import hashlib, json, subprocess, sys

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'outputs'

if __name__=='__main__':
    roms=sorted(OUT.glob('*.rom'))
    before={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in roms}
    subprocess.run([sys.executable,'tools/build.py'],cwd=ROOT,check=True)
    after={p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in roms}
    assert before==after,'Rebuild changed the ROMs'
    report=json.loads((OUT/'verification.json').read_text())
    for item in report['verified']:
        assert after[f'PRISM_FLIGHT-V9968-{item["profile"]}.rom']==item['sha256']
    (OUT/'reproducibility.json').write_text(json.dumps({'same_after_asset_regeneration':True,'sha256':after},indent=2)+'\n')
    files=[ROOT/name for name in ['README.md','run-demo.cmd','requirements.txt','COPYRIGHT.md','DISCLAIMER.md','THIRD_PARTY_NOTICES.md','.gitignore','.gitattributes']]
    for folder in ['src','tools','assets']:
        files += [p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts]
    files += [p for p in OUT.iterdir() if p.suffix in ['.rom','.json','.gif','.png'] and p.name!='emulator-first.png']
    archive=OUT/'PRISM_FLIGHT-source-and-ROM.zip'
    with ZipFile(archive,'w',ZIP_DEFLATED) as z:
        for p in sorted(files): z.write(p,Path('PRISM_FLIGHT')/p.relative_to(ROOT))
    with ZipFile(archive) as z:
        assert z.testzip() is None
        assert not any(name.lower().endswith('.exe') or 'systemroms' in name.lower() for name in z.namelist())
    print(archive)
