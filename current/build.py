"""Rebuild v2.0.0 from checked-in assembly and frozen generated artwork.
Python 3 + Pasmo, no BIOS or emulator required. Set PASMO or add pasmo to PATH.
"""
from pathlib import Path
import hashlib,json,os,shutil,struct,subprocess
ROOT=Path(__file__).resolve().parent
def main():
 pasmo=os.environ.get('PASMO') or shutil.which('pasmo')
 if not pasmo:raise SystemExit('Set PASMO to your Pasmo executable, or add pasmo to PATH.')
 results=[]
 for item in json.loads((ROOT/'manifest.json').read_text()):
  n=item['name'];d=ROOT/'demos'/n;a=d/'assets';w=ROOT/'work'/n;w.mkdir(parents=True,exist_ok=True)
  for name in ['boot','demo']:
   subprocess.run([pasmo,'--bin',str(d/'src'/f'{name}.asm'),str(w/f'{name}.bin'),str(w/f'{name}.symbols')],cwd=d,check=True)
  if n in ['PRISM_FLIGHT','SUPER_CAT-COASTAL_FLIGHT']:
   data=b''.join((a/f'{x}.bin').read_bytes() for x in ['background','sprites','motion'])
  else:
   bg=(a/'background-indexed.bin').read_bytes();motion=bytearray((a/'motion.bin').read_bytes())
   if n=='LUMEN_FORGE':
    upload=bg+(a/'sprites.bin').read_bytes()[:16384]+bytes(16384)
    for i in range(1024):
     for o in [2,130]:
      p=i*256+o;v=struct.unpack_from('<h',motion,p)[0];struct.pack_into('<h',motion,p,v+256)
   elif n=='MIST_VALE':upload=bg+(a/'trees-indexed.bin').read_bytes()+bytes(24576)+(a/'fog.bin').read_bytes()
   else:upload=bg+(a/'sprite-atlas.bin').read_bytes()
   data=upload+motion
  boot=(w/'boot.bin').read_bytes();code=(w/'demo.bin').read_bytes()
  assert len(boot)==8192 and boot[:2]==b'AB' and len(code)<=24576
  rom=boot+code+bytes([255])*(24576-len(code))+data
  assert len(rom)<=item['bytes'];rom+=bytes([255])*(item['bytes']-len(rom))
  digest=hashlib.sha256(rom).hexdigest();assert digest==item['sha256'],(n,digest)
  target=ROOT/item['file'];target.parent.mkdir(exist_ok=True);target.write_bytes(rom)
  results.append(dict(name=n,sha256=digest,bytes=len(rom)))
 print(json.dumps(results,indent=2))
if __name__=='__main__':main()
