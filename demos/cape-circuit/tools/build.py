"""CAPE CIRCUIT: original autonomous LRMM race, 512 KiB ASCII8."""
from pathlib import Path
import math, struct, subprocess, json, hashlib, os, shutil
from PIL import Image, ImageDraw, ImageFont
R=Path(__file__).resolve().parents[1]; A=R/'assets'; W=R/'work'; O=R/'outputs'
for p in [A,W,O]:p.mkdir(exist_ok=True)
N=320
PAL=[(5,8,22),(12,19,43),(23,36,61),(36,57,79),(55,79,96),(92,117,125),(148,175,177),(231,250,240),(17,91,111),(22,166,182),(85,239,232),(86,47,133),(161,64,191),(252,118,189),(244,184,110),(255,233,171)]
CAT=[(0,0,0),(14,24,30),(29,43,48),(52,66,68),(77,92,89),(107,127,115),(148,168,147),(202,218,183),(236,242,210),(16,63,77),(35,113,139),(94,184,191),(217,123,44),(255,184,75),(234,61,46),(245,238,202)]
BUN=[(0,0,0),(28,20,51),(53,40,73),(87,72,108),(120,110,144),(156,150,175),(198,191,214),(229,222,240),(255,247,251),(81,28,91),(141,40,137),(244,109,199),(179,172,200),(239,234,251),(242,152,179),(255,255,255)]
def pack(im):
 b=bytes(im.getdata());return bytes((b[i]<<4)|b[i+1] for i in range(0,len(b),2))
def preview(im,pal,path):
 im=im.copy();im.putpalette(sum((list(c) for c in pal),[])+[0]*(768-len(pal)*3));im.save(path)
def world():
 im=Image.new('P',(256,512),0);d=ImageDraw.Draw(im)
 for y in range(512):
  for x in range(256):
   im.putpixel((x,y),1 if (x//16+y//16)%2 else 0)
 for x in range(0,256,16):d.line((x,0,x,511),fill=2)
 for y in range(0,512,16):d.line((0,y,255,y),fill=2)
 pts=[(128+82*math.sin(t*math.tau/1024),256-181*math.cos(t*math.tau/1024)) for t in range(1025)]
 for width,col in [(40,11),(36,12),(33,10),(29,8),(27,3),(23,2)]:d.line(pts,fill=col,width=width,joint='curve')
 for i in range(0,1024,12):
  d.line(pts[i:i+5],fill=5,width=1)
 for i in range(0,1024,16):
  t=i*math.tau/1024
  for side in [-1,1]:
   x=128+(82+side*17)*math.sin(t);y=256-(181+side*17)*math.cos(t)
   d.ellipse((x-1,y-1,x+1,y+1),fill=15)
 # Custom start tiles, chevron acceleration pads, and islands.
 for x in range(112,145,4):
  for y in range(73,82,3):d.rectangle((x,y,x+3,y+2),fill=7 if (x//4+y//3)%2 else 3)
 for t in [1.1,3.4,5.3]:
  cx=128+82*math.sin(t);cy=256-181*math.cos(t)
  forward=(82*math.cos(t),181*math.sin(t));le=math.hypot(*forward);fx,fy=[q/le for q in forward];rx,ry=fy,-fx
  for k in [-3,0,3]:
   d.line([(cx+rx*u+fx*(k+abs(u)*.45),cy+ry*u+fy*(k+abs(u)*.45)) for u in range(-9,10)],fill=10,width=2)
 for x,y,r in [(113,225,21),(140,289,28),(102,336,13),(151,177,17)]:
  d.ellipse((x-r,y-r,x+r,y+r),fill=11);d.ellipse((x-r+3,y-r+3,x+r-3,y+r-3),fill=1)
  d.line((x-r,y,x+r,y),fill=12);d.line((x,y-r,x,y+r),fill=9)
 preview(im,PAL,A/'course.png');return im
def sky():
 im=Image.new('P',(256,256));d=ImageDraw.Draw(im)
 for y in range(92):d.line((0,y,255,y),fill=0 if y<32 else 1 if y<63 else 11)
 d.ellipse((173,29,207,63),fill=14)
 for y in range(47,64,4):d.line((172,y,209,y+1),fill=11,width=2)
 for i in range(38):
  x=(i*73+19)%256;y=23+(i*37)%38;d.point((x,y),fill=6 if i%3 else 10)
 for i in range(24):
  x=i*12-4;h=7+(i*13)%21;d.rectangle((x,91-h,x+8,91),fill=2);d.line((x,91-h,x+8,91-h),fill=8)
  for yy in range(94-h,89,5):d.point((x+3,yy),fill=10)
 d.rectangle((0,0,255,17),fill=0)
 d.text((7,3),'CAPE CIRCUIT',font=ImageFont.load_default(),fill=10)
 d.text((164,3),'AUTO / DUEL',font=ImageFont.load_default(),fill=13)
 d.line((7,17,249,17),fill=8)
 preview(im,PAL,A/'sky.png');return im
def sprites():
 # Reuse our original authored rear-view cat; no third-party character art.
 src=(A/'cat-source.bin').read_bytes()
 px=bytes(v for b in src for v in (b>>4,b&15));old=Image.frombytes('P',(256,256),px)
 cat=old.crop((0,0,32,64));bun=Image.new('P',(32,64));d=ImageDraw.Draw(bun)
 d.ellipse((9,20,23,42),fill=12);d.ellipse((10,20,21,39),fill=13)
 d.ellipse((8,0,14,23),fill=13);d.ellipse((19,0,25,23),fill=13)
 d.line((11,4,11,16),fill=14,width=2);d.line((22,4,22,16),fill=14,width=2)
 d.ellipse((7,16,25,31),fill=13);d.arc((8,18,24,30),0,150,fill=8,width=2)
 d.ellipse((3,24,10,33),fill=15);d.ellipse((23,24,29,33),fill=15)
 d.ellipse((8,38,15,48),fill=15);d.ellipse((19,38,25,48),fill=15)
 d.polygon([(10,30),(22,30),(27,44),(18,41),(9,44),(6,40)],fill=9)
 d.polygon([(12,31),(17,33),(12,42),(8,40)],fill=10);d.polygon([(20,31),(22,31),(25,41),(19,38)],fill=11)
 d.ellipse((14,43,20,49),fill=8)
 atlas=Image.new('P',(256,256))
 for n,angle in enumerate([-18,-9,0,9,18]):
  atlas.paste(cat.rotate(angle,resample=Image.Resampling.NEAREST,center=(16,29)),(n*32,0))
  atlas.paste(bun.rotate(angle,resample=Image.Resampling.NEAREST,center=(16,29)),(n*32,64))
 d=ImageDraw.Draw(atlas);d.ellipse((0,137,31,150),fill=1)
 # Cyan vapor streams use two more 16x64 columns.
 for j in range(2):
  x=64+j*16;d.polygon([(x+6,128),(x+10,128),(x+14,183),(x+8,191),(x+3,180)],fill=10+j)
 preview(atlas,CAT,A/'characters.png');return atlas
def records():
 out=bytearray()
 for f in range(N):
  t=math.tau*f/N;theta=t+.09*math.sin(3*t)
  x=128+82*math.sin(theta);y=256-181*math.cos(theta)
  fx,fy=82*math.cos(theta),181*math.sin(theta);ll=math.hypot(fx,fy);fx/=ll;fy/=ll;rx,ry=-fy,fx
  # Genuine per-scanline projective sampling of a persistent 2D world map.
  for sy in range(92,212):
   z=1740/(sy-72);scale=z/145
   sx=x+fx*z-rx*128*scale;wy=y+fy*z-ry*128*scale
   out+=struct.pack('<hhhh',round(sx),round(wy)+1024,round(rx*scale*256),round(ry*scale*256))
  sat=bytearray()
  def strip(x,y,w,h,pat,pal=1,tp=0):
   sat.extend(struct.pack('<HBBHBB',(round(y)&1023)|0x8000,round(h),pal|tp,round(x)&1023,round(w),pat))
  # The rival changes depth and lane; both participants remain visible.
  lead=math.sin(t*2+.5);bw=round(8+12*(lead+1)/2);bh=bw*4
  bx=128+43*math.sin(t*2+.9);by=108+24*(lead+1)/2
  # Rear-view bank follows actual road curvature plus lateral velocity.
  curvature=82*181/(82**2*math.cos(theta)**2+181**2*math.sin(theta)**2)
  turn_bank=-min(18,7*curvature)
  hero_bank=turn_bank+7*math.cos(t*2+.9)
  rival_bank=turn_bank-8*math.cos(t*2+.9)
  hero_pose=max(0,min(4,round((hero_bank+18)/9)))
  rival_pose=max(0,min(4,round((rival_bank+18)/9)))
  hx=128-14*math.sin(t*2+.9);hy=146+2*math.sin(t*12)
  # Vapor first in depth is handled by sprite order (hero in front).
  hero=[(hx-20,hy,20,64,hero_pose*2,1),(hx,hy,20,64,hero_pose*2+1,1)]
  rabbit=[(bx-bw,by,bw,bh,64+rival_pose*2,2),(bx,by,bw,bh,65+rival_pose*2,2)]
  for a in (rabbit+hero if by+bh>hy+64 else hero+rabbit):strip(*a)
  strip(hx-15,hy+43,13,42,132,0,0x40);strip(hx+3,hy+43,13,42,133,0,0x40)
  # Termination is explicit; remaining record bytes carry no sprite data.
  sat+=bytes([216,0,0,0,0,0,0,0])+bytes([round((math.atan2(fy,fx)+math.pi)*128/math.pi)%256])+bytes(7)
  assert len(sat)==64;out+=sat
 assert len(out)==N*1024;return out
def main():
 ground=world();atlas=sprites();back=sky()
 (A/'vram.bin').write_bytes(pack(ground)+pack(atlas)+pack(back))
 (A/'motion.bin').write_bytes(records())
 palette=PAL+CAT+BUN+[(0,0,0)]*16
 (A/'palette.inc').write_text('initial_palette:\n db '+','.join(str(round(c*31/255)) for rgb in palette for c in rgb)+'\n')
 pasmo=os.environ.get('PASMO') or shutil.which('pasmo') or 'C:/Software/Pasmo/pasmo.exe'
 for name in ['boot','demo']:subprocess.run([pasmo,'--bin',str(R/'src'/f'{name}.asm'),str(W/f'{name}.bin'),str(W/f'{name}.symbols')],cwd=R,check=True)
 code=(W/'demo.bin').read_bytes();assert len(code)<=24576
 rom=(W/'boot.bin').read_bytes()+code.ljust(24576,b'\xff')+(A/'vram.bin').read_bytes()+(A/'motion.bin').read_bytes()
 assert len(rom)<=524288;rom=rom.ljust(524288,b'\xff')
 name='CAPE-CIRCUIT-V9968.rom';(O/name).write_bytes(rom)
 (O/'build.json').write_text(json.dumps({'name':'CAPE CIRCUIT','rom':name,'bytes':len(rom),'sha256':hashlib.sha256(rom).hexdigest(),'frames':N,'rendering':'120 LRMM scanlines per frame, no prerecorded video','vdp':'V9968','r20':31,'r21':58},indent=2))
 print(len(code),len(rom),hashlib.sha256(rom).hexdigest())
if __name__=='__main__':main()
