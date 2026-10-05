"""Build CPU-optimized editions from assembly and the frozen public assets."""
from pathlib import Path
import hashlib,json,os,shutil,subprocess
HERE=Path(__file__).resolve().parent
ROOT=HERE.parent
DEMOS={
 'CATSTRIDER':(ROOT/'current/demos/CATSTRIDER',ROOT/'current/roms/CATSTRIDER-V9968-current-internal.rom',1536),
 'CAPE_CIRCUIT':(ROOT/'demos/cape-circuit',ROOT/'demos/cape-circuit/outputs/CAPE-CIRCUIT-V9968.rom',320),
}
def main():
 pasmo=os.environ.get('PASMO') or shutil.which('pasmo')
 if not pasmo:raise SystemExit('Set PASMO or add pasmo to PATH.')
 (HERE/'roms').mkdir(exist_ok=True);manifest=[]
 for name,(source,baseline,frames) in DEMOS.items():
  w=HERE/'work'/name;w.mkdir(parents=True,exist_ok=True)
  subprocess.run([pasmo,'--bin',str(HERE/'src'/f'{name}.asm'),str(w/'demo.bin'),str(w/'demo.symbols')],cwd=source,check=True)
  subprocess.run([pasmo,'--bin',str(source/'src/boot.asm'),str(w/'boot.bin')],cwd=source,check=True)
  code=(w/'demo.bin').read_bytes();assert len(code)<=24576
  if name=='CATSTRIDER':
   a=source/'assets'
   data=b''.join((a/f).read_bytes() for f in ['background-indexed.bin','sprite-atlas.bin','motion.bin'])
  else:data=(source/'assets/vram.bin').read_bytes()+(source/'assets/motion.bin').read_bytes()
  old=baseline.read_bytes();assert data==old[32768:32768+len(data)]
  boot=(w/'boot.bin').read_bytes();assert boot==old[:8192]
  for cpu in ['auto','Z80']:
   b=boot
   if cpu=='Z80':
    # turbo R CHGCPU: 82h=R800 DRAM; 80h=Z80. Older BIOS skips this call.
    marker=bytes.fromhex('3e82cd8001');assert b.count(marker)==1
    b=b.replace(marker,bytes.fromhex('3e80cd8001'))
   rom=(b+code.ljust(24576,b'\xff')+data).ljust(len(old),b'\xff')
   assert len(rom)==524288
   file=f'roms/{name}-{cpu}.rom';(HERE/file).write_bytes(rom)
   manifest.append(dict(name=name,cpu=cpu,file=file,bytes=len(rom),sha256=hashlib.sha256(rom).hexdigest(),frames=frames))
 (HERE/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
 print(json.dumps(manifest,indent=2))
if __name__=='__main__':main()
