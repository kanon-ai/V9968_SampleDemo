"""Build separate 194a769 linear-VRAM ROMs; retain d884 artifacts unchanged.
Requires the V9968_OLD XML register profile (see UPDATE-20260922.md).
"""
from pathlib import Path
import hashlib,json,os,shutil,struct,subprocess
ROOT=Path(__file__).resolve().parents[1]
DEMO='LUMEN_FORGE'
def build():
 out=ROOT/'outputs';work=ROOT/'work/build-194a769';work.mkdir(parents=True,exist_ok=True)
 assets=ROOT/'assets';bg=(assets/'background-indexed.bin').read_bytes();motion=bytearray((assets/'motion.bin').read_bytes())
 if DEMO=='LUMEN_FORGE':
  sprites=(assets/'sprites.bin').read_bytes();upload=bg+sprites[:16384]+bytes(16384)
  for n in range(1024):
   for offset in (2,130):
    addr=n*256+offset;v=struct.unpack_from('<h',motion,addr)[0];struct.pack_into('<h',motion,addr,v+256)
 elif DEMO=='MIST_VALE':
  upload=bg+(assets/'trees-indexed.bin').read_bytes()+bytes(24576)+(assets/'fog.bin').read_bytes()
 else:upload=bg+(assets/'sprite-atlas.bin').read_bytes()
 assert len(upload)==(131072 if DEMO=='MIST_VALE' else 98304)
 pasmo=os.environ.get('PASMO') or shutil.which('pasmo') or 'C:/Software/Pasmo/pasmo.exe'
 subprocess.run([pasmo,'--bin','src/boot.asm',str(work/'boot.bin')],cwd=ROOT,check=True)
 reports=[]
 for profile,port in [('openmsx-194a769-internal',0x98),('openmsx-194a769-external',0x88)]:
  wrapper=work/(profile+'.asm');wrapper.write_text(f'VDP_BASE equ {port}\ninclude "src/demo-194a769.asm"\n')
  binary=work/(profile+'.bin');symbols=work/(profile+'.symbols')
  subprocess.run([pasmo,'--bin',str(wrapper),str(binary),str(symbols)],cwd=ROOT,check=True)
  runtime=binary.read_bytes();assert len(runtime)<=24576
  rom=(work/'boot.bin').read_bytes()+runtime+bytes([255])*(24576-len(runtime))+upload+motion
  assert len(rom)<=524288;rom+=bytes([255])*(524288-len(rom))
  name=DEMO+'-V9968-'+profile+'.rom';(out/name).write_bytes(rom)
  reports.append(dict(file=name,sha256=hashlib.sha256(rom).hexdigest(),bytes=len(rom),vdp_xml='V9968_OLD',emulator='194a769',hardware_tested=False))
 (work/'upload.bin').write_bytes(upload);(work/'motion.bin').write_bytes(motion)
 (out/'build-194a769.json').write_text(json.dumps(reports,indent=2)+'\n')
 print(json.dumps(reports))
if __name__=='__main__':build()
