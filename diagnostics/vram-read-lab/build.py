from pathlib import Path
import subprocess,hashlib,json,os,shutil
P=Path(__file__).resolve().parent
PASMO=os.environ.get('PASMO') or shutil.which('pasmo') or 'C:/Software/Pasmo/pasmo.exe'
(P/'work').mkdir(exist_ok=True)
(P/'out').mkdir(exist_ok=True)
rows=json.loads((P/'src/font.json').read_text())
data=bytearray()
for c in range(128):
 data.extend([int(r,2)<<3 for r in rows.get(chr(c).upper(),['00000']*7)]+[0])
# Monochrome graphic dashboard, still SCREEN 0: no sprite or bitmap load.
pixels=[[0]*240 for _ in range(32)]
def line(x0,y0,x1,y1):
 if x0==x1:
  for y in range(y0,y1+1):pixels[y][x0]=1
 else:
  for x in range(x0,x1+1):pixels[y0][x]=1
def box(x,y,w,h):
 line(x,y,x+w-1,y);line(x,y+h-1,x+w-1,y+h-1);line(x,y,x,y+h-1);line(x+w-1,y,x+w-1,y+h-1)
def text(x,y,value,scale=1):
 for ch in value:
  for yy,row in enumerate(rows.get(ch,['00000']*7)):
   for xx,v in enumerate(row):
    if v=='1':
     for dy in range(scale):
      for dx in range(scale):pixels[y+yy*scale+dy][x+xx*scale+dx]=1
  x+=6*scale
box(0,0,240,32)
text(8,5,'VRAM',3)
line(88,4,88,27)
text(98,4,'V9968');text(98,15,'READ LAB')
text(155,4,'0.2');text(155,15,'HEX')
box(192,5,31,22)
text(199,12,'IO')
for x in range(196,222,5):line(x,2,x,4);line(x,27,x,29)
for y in range(9,25,5):line(188,y,191,y);line(223,y,227,y)
tiles={};header=[]
def tile_id(t):
 key=bytes(t)
 if key not in tiles:tiles[key]=128+len(tiles)
 return tiles[key]
for cy in range(4):
 for cx in range(40):
  header.append(tile_id([sum(pixels[cy*8+y][cx*6+x]<<(7-x) for x in range(6)) for y in range(8)]))
extra={
 'tile_empty':[0,0xfc,0x84,0x84,0x84,0x84,0xfc,0],
 'tile_full':[0,0xfc,0xfc,0xfc,0xfc,0xfc,0xfc,0],
 'tile_led_off':[0,0x30,0x48,0x84,0x84,0x48,0x30,0],
 'tile_led_on':[0,0x30,0x78,0xfc,0xfc,0x78,0x30,0],
 'tile_rule':[0,0,0,0xfc,0,0,0,0]}
constants={k:tile_id(v) for k,v in extra.items()}
assert len(tiles)<=128,len(tiles)
for t in tiles:data.extend(t)
data.extend(bytes(2048-len(data)))
(P/'src/font.bin').write_bytes(data)
(P/'src/header.bin').write_bytes(bytes(header))
(P/'src/graphics.inc').write_text('\n'.join(f'{k} equ {v}' for k,v in constants.items()))

boot='''org 04000h
 db "AB"
 dw start
 dw 0,0,0,0,0,0
start:
 di
 ld sp,0f300h
 in a,(0a8h)
 rlca
 rlca
 and 3
 ld c,a
 ld b,0
 ld hl,0fcc1h
 add hl,bc
 ld a,(hl)
 and 080h
 jr z,primary
 ld hl,0fcc5h
 add hl,bc
 ld a,(hl)
 and 0c0h
 rrca
 rrca
 rrca
 rrca
 or 080h
primary:
 or c
 ld h,080h
 call 0024h
 di
 ld hl,04100h
 ld de,08000h
 ld bc,03f00h
 ldir
 jp 08000h
 defs 0100h-($-04000h),0ffh
'''
(P/'src/boot.asm').write_text(boot)
subprocess.run([PASMO,'--bin','src/boot.asm','work/boot.bin'],cwd=P,check=True)
manifest=[]
for port,name in [(0x88,'EXTERNAL-88'),(0x98,'INTERNAL-98')]:
 text=f'VDP equ {port}\n'+(P/'src/main.asm').read_text()
 (P/'work/main.asm').write_text(text)
 subprocess.run([PASMO,'--bin','work/main.asm',f'work/{name}.bin',f'work/{name}.sym'],cwd=P,check=True)
 payload=(P/f'work/{name}.bin').read_bytes();assert len(payload)<=0x3f00
 rom=((P/'work/boot.bin').read_bytes()+payload).ljust(32768,b'\xff')
 out=P/f'out/V9968-VRAM-DIAG-{name}.rom';out.write_bytes(rom)
 manifest.append(dict(file=out.name,bytes=len(rom),sha256=hashlib.sha256(rom).hexdigest(),port=port))
(P/'out/manifest.json').write_text(json.dumps(manifest,indent=2))
print(json.dumps(manifest,indent=2))
