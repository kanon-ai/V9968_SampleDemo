"""CAPE CIRCUIT: original autonomous LRMM race, 512 KiB ASCII8."""
from pathlib import Path
import math, struct, subprocess, json, hashlib, os, shutil
from PIL import Image, ImageDraw, ImageFont
R=Path(__file__).resolve().parents[1]; A=R/'assets'; W=R/'work'; O=R/'outputs'
for p in [A,W,O]:p.mkdir(exist_ok=True)
N=320
CENTER_SPLIT=os.environ.get("CAPE_SPLIT", "0")=="1"
PAL=[(6,10,24),(13,22,39),(25,36,56),(34,48,67),(45,62,80),(59,78,96),(83,112,129),(165,204,210),(31,106,130),(69,181,197),(137,230,232),(39,30,62),(86,67,120),(177,123,187),(241,174,125),(249,222,181)]
CAT=[(0,0,0),(14,24,30),(29,43,48),(52,66,68),(77,92,89),(107,127,115),(148,168,147),(202,218,183),(236,242,210),(16,63,77),(35,113,139),(94,184,191),(217,123,44),(255,184,75),(234,61,46),(245,238,202)]
BUN=[(0,0,0),(28,20,51),(53,40,73),(87,72,108),(120,110,144),(156,150,175),(198,191,214),(229,222,240),(255,247,251),(81,28,91),(141,40,137),(244,109,199),(179,172,200),(239,234,251),(242,152,179),(255,255,255)]
def pack(im):
 b=bytes(im.getdata());return bytes((b[i]<<4)|b[i+1] for i in range(0,len(b),2))
def preview(im,pal,path):
 im=im.copy();im.putpalette(sum((list(c) for c in pal),[])+[0]*(768-len(pal)*3));im.save(path)
def world():
 # Supersample original vector artwork and quantize without ordered noise.
 # Low-contrast road surfaces and graded shoulders avoid isolated bright texels.
 S=4
 im=Image.new('RGB',(256*S,512*S),PAL[0]);d=ImageDraw.Draw(im)
 pts=[((128+82*math.sin(t*math.tau/2048))*S,(256-181*math.cos(t*math.tau/2048))*S) for t in range(2049)]
 for width,col in [(43,1),(39,11),(37,12),(35,8),(33,9),(31,10),(29,9),(27,4),(25,3),(22,2)]:
  d.line(pts,fill=PAL[col],width=width*S,joint='curve')
 # Broad sparse markers read as motion rather than flickering 1-texel detail.
 for i in range(0,2048,80):d.line(pts[i:i+13],fill=PAL[4],width=2*S)
 for t in [1.1,3.4,5.3]:
  cx=128+82*math.sin(t);cy=256-181*math.cos(t)
  fx,fy=82*math.cos(t),181*math.sin(t);le=math.hypot(fx,fy);fx/=le;fy/=le;rx,ry=-fy,fx
  for k in [-5,0,5]:
   d.line([((cx+rx*u+fx*(k-abs(u)*.45))*S,(cy+ry*u+fy*(k-abs(u)*.45))*S) for u in range(-9,10)],fill=PAL[9],width=2*S)
 # Quiet luminous infield architecture; no checkerboard or narrow grid lines.
 for x,y,rr in [(113,225,21),(140,289,28),(102,336,13),(151,177,17)]:
  for dr,col in [(0,11),(2,12),(4,11),(6,1)]:
   d.ellipse(((x-rr+dr)*S,(y-rr+dr)*S,(x+rr-dr)*S,(y+rr-dr)*S),fill=PAL[col])
 im=im.resize((256,512),Image.Resampling.LANCZOS)
 pal=Image.new('P',(1,1));pal.putpalette(sum((list(c) for c in PAL),[])*16)
 im=im.quantize(palette=pal,dither=Image.Dither.NONE)
 # Normalize duplicate palette indices so the 4bpp pack remains exact.
 im=im.point([i%16 for i in range(256)])
 preview(im,PAL,A/'course.png');return im

def sky():
 # Original dusk panorama: atmospheric ridges, varied skyline and quiet lights.
 # All colors reuse the road palette; its values and runtime are unchanged.
 S=4
 rgb=Image.new('RGB',(256*S,92*S),PAL[0]);d=ImageDraw.Draw(rgb)
 stops=[(18,PAL[0]),(36,PAL[11]),(62,PAL[12]),(78,PAL[13]),(92,PAL[12])]
 bayer=((0,8,2,10),(12,4,14,6),(3,11,1,9),(15,7,13,5))
 for y in range(18,92):
  for (ya,ca),(yb,cb) in zip(stops,stops[1:]):
   if ya<=y<=yb: u=(y-ya)/(yb-ya);break
  for x in range(256):
   color=cb if u>(bayer[y%4][x%4]+.5)/16 else ca
   d.rectangle((x*S,y*S,(x+1)*S-1,(y+1)*S-1),fill=color)
 for i in range(20):
  x=(i*73+19)%256;y=23+(i*37)%19
  d.rectangle((x*S,y*S,x*S+2,y*S+2),fill=PAL[6])
 # Periodic silhouettes ensure the horizontally wrapped panorama has no seam.
 for base,amp,col,phase in [(71,7,11,.6),(79,5,3,1.2)]:
  ridge=[(x*S,(base-amp*(.5+.3*math.sin(x*math.tau/128+phase)+.2*math.sin(x*math.tau/43)))*S) for x in range(257)]
  d.polygon(ridge+[(256*S,92*S),(0,92*S)],fill=PAL[col])
 for i in range(31):
  x=(i*29)%256;w=3+(i*7)%7;h=4+(i*11)%12
  d.rectangle((x*S,(88-h)*S,(x+w)*S,91*S),fill=PAL[2])
 # Foreground skyline has recognizable stepped roofs rather than repeated blocks.
 for i,x in enumerate([3,22,39,58,85,109,133,154,181,211,232]):
  w=[10,8,13,18,11,14,9,17,12,10,12][i];h=[16,22,13,26,18,11,29,17,24,14,19][i]
  y=92-h
  d.rectangle((x*S,y*S,(x+w)*S,92*S),fill=PAL[1])
  d.rectangle(((x+2)*S,(y-3)*S,(x+w-2)*S,y*S),fill=PAL[1])
  d.line(((x+2)*S,(y-3)*S,(x+w-2)*S,(y-3)*S),fill=PAL[8],width=S)
  if i%3==0:d.line(((x+w//2)*S,(y-7)*S,(x+w//2)*S,y*S),fill=PAL[6],width=S)
  for xx in range(x+2,x+w-1,3):
   for yy in range(y+3,89,4):
    if (xx+yy+i)%5:d.rectangle((xx*S,yy*S,xx*S+S-1,yy*S+S-1),fill=PAL[8 if i%3 else 6])
 d.line((0,91*S,256*S,91*S),fill=PAL[2],width=S)
 rgb=rgb.resize((256,92),Image.Resampling.LANCZOS)
 pal=Image.new('P',(1,1));pal.putpalette(sum((list(c) for c in PAL),[])*16)
 q=rgb.quantize(palette=pal,dither=Image.Dither.NONE).point([i%16 for i in range(256)])
 im=Image.new('P',(256,256));im.paste(q,(0,0));d=ImageDraw.Draw(im)
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
 d.line((9,5,9,18),fill=12);d.line((20,5,20,18),fill=12)
 d.line((12,4,12,17),fill=15);d.line((23,4,23,17),fill=15)
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
 # One celestial sprite, outside the horizontally repeated panorama.
 # Mode3 scales this 16x64 cell into a small, round disc.
 d.ellipse((0,192,15,255),fill=14)
 d.ellipse((1,196,14,251),fill=15)
 d.ellipse((3,207,5,216),fill=14)
 d.ellipse((9,230,12,241),fill=14)
 preview(atlas,CAT,A/'characters.png');return atlas
def records():
 out=bytearray()
 for f in range(N):
  t=math.tau*f/N;theta=t+.09*math.sin(3*t)
  x=128+82*math.sin(theta);y=256-181*math.cos(theta)
  fx,fy=82*math.cos(theta),181*math.sin(theta);ll=math.hypot(fx,fy);fx/=ll;fy/=ll;rx,ry=-fy,fx
  # Genuine per-scanline projective sampling of a persistent 2D world map.
  for sy in range(92,212):
   lift=max(0.0,math.sin(t-.45))**4
   # Smooth rise exposes more of the course, followed by a low flyby.
   z=(1740+2600*lift)/(sy-72);scale=z/(145-12*lift)
   # First-order banked-plane projection around the scanline center.
   # Limit near-horizon depth variation to avoid folding the road.
   bank=.18*(.5+.5*math.cos(theta*2))
   slope=-z*math.tan(bank)/(sy-72)
   slope=max(-z*.24/128,min(z*.24/128,slope))
   ux=rx*scale+fx*slope;uy=ry*scale+fy*slope
   sx=x+fx*z;wy=y+fy*z
   if not CENTER_SPLIT: sx-=ux*128;wy-=uy*128
   if CENTER_SPLIT:
    vx,vy=round(ux*256),round(uy*256)
   else:
    # Compensate integer start rounding at the central viewing region.
    vx=round((ux+(sx-round(sx))/128)*256)
    vy=round((uy+(wy-round(wy))/128)*256)
   out+=struct.pack('<hhhh',round(sx),round(wy)+1024,vx,vy)
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
  hx=128-14*math.sin(t*2+.9);hy=146-12*max(0.0,math.sin(t-.45))**4+2*math.sin(t*12)
  # Vapor first in depth is handled by sprite order (hero in front).
  hero=[(hx-20,hy,20,64,hero_pose*2,1),(hx,hy,20,64,hero_pose*2+1,1)]
  rabbit=[(bx-bw,by,bw,bh,64+rival_pose*2,2),(bx,by,bw,bh,65+rival_pose*2,2)]
  for a in (rabbit+hero if by+bh>hy+64 else hero+rabbit):strip(*a)
  strip(hx-15,hy+43,13,42,132,0,0x40);strip(hx+3,hy+43,13,42,133,0,0x40)
  # A single moon drifts gently; it never wraps with the panorama.
  strip(183+18*math.sin(t),30,27,28,192,3)
  # Seven sprites plus an explicit terminator; its unused final byte holds pan.
  sat+=bytes([216,0,0,0,0,0,0,round((math.atan2(fy,fx)+math.pi)*128/math.pi)%256])
  assert len(sat)==64;out+=sat
 assert len(out)==N*1024;return out
def main():
 (A/'options.inc').write_text('CENTER_SPLIT equ '+str(int(CENTER_SPLIT))+'\n')
 ground=world();atlas=sprites();back=sky()
 (A/'vram.bin').write_bytes(pack(ground)+pack(atlas)+pack(back))
 (A/'motion.bin').write_bytes(records())
 palette=PAL+CAT+BUN+PAL
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
