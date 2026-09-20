"""Original coastal-flight study. Native LRMM, not rendered video playback."""
from pathlib import Path
import math, struct, random, subprocess, json, hashlib, os, shutil
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
A=ROOT/'assets'
FRAMES=2048
WORLD_HEIGHT=768
BOATS=((75,430),(80,128),(73,662))
PATCHES=[((cx-8)&~1,cy+offset) for cx,cy in BOATS for offset in (-31,14)]
GROUND=[(6,20,30),(13,42,58),(18,67,78),(35,98,99),(75,136,123),
 (171,170,126),(49,65,49),(67,91,55),(87,111,61),(117,132,77),
 (37,44,47),(70,79,77),(106,116,106),(158,171,156),(215,215,176),(224,147,65)]
HELI=[(0,0,0),(14,24,30),(29,43,48),(52,66,68),(77,92,89),(107,127,115),
 (148,168,147),(202,218,183),(236,242,210),(16,63,77),(35,113,139),(94,184,191),
 (217,123,44),(255,184,75),(234,61,46),(245,238,202)]
def packed(im):
    b=bytes(im.getdata());return bytes((b[i]<<4)|b[i+1] for i in range(0,len(b),2))
def terrain():
    im=Image.new('P',(256,WORLD_HEIGHT));p=im.load();rng=random.Random(9968)
    for y in range(WORLD_HEIGHT):
        coast=65+22*math.sin(y*.023)+10*math.cos(y*.067)
        for x in range(256):
            dist=x-coast
            relief=math.sin(x*.087+y*.029)+.6*math.sin(x*.18-y*.073)+.35*math.cos(y*.28)
            noise=rng.random()
            if dist<-16:c=1 if noise<.91 else 2
            elif dist<-7:c=2
            elif dist<-3:c=3 if noise<.8 else 4
            elif dist<2:c=5 if noise<.9 else 4
            else:c= max(6,min(9,round(7.4+relief*.6+(noise-.5)*.8)))
            p[x,y]=c
        if y==511:legacy_tree_state=rng.getstate()
    d=ImageDraw.Draw(im)
    for cy in (128,430,662):
        d.ellipse((-30,cy-67,114,cy+67),fill=4)
        d.ellipse((-32,cy-64,110,cy+64),fill=3)
        d.ellipse((-35,cy-60,105,cy+60),fill=2)
        d.ellipse((-38,cy-55,100,cy+55),fill=1)
    # Roads, embankments and concrete pads follow an original fictional coast.
    road=[(125,0),(126,92),(155,150),(156,245),(119,310),(123,420),(155,511),
          (163,569),(126,626),(126,704),(146,767)]
    d.line(road,fill=5,width=10);d.line(road,fill=10,width=6)
    for y in range(4,WORLD_HEIGHT-4,12):
        for i in range(len(road)-1):
            (ax,ay),(bx,by)=road[i:i+2]
            if ay<=y<by:
                x=round(ax+(bx-ax)*(y-ay)/(by-ay));d.line((x,y,x,y+3),fill=12)
    d.rectangle((156,170,240,286),fill=11)
    d.rectangle((180,174,198,283),fill=10)
    for y in range(180,282,12):d.rectangle((188,y,190,y+5),fill=14)
    for x in (183,194):
        d.line((x,178,x,187),fill=14);d.line((x,270,x,279),fill=14)
    def building(x,y,w,h):
        d.rectangle((x+3,y+4,x+w+3,y+h+4),fill=6)
        d.rectangle((x,y,x+w,y+h),fill=10)
        d.rectangle((x,y,x+w-2,y+h-3),fill=12)
        d.line((x,y,x+w-2,y),fill=14)
        for xx in range(x+3,x+w-2,4):d.line((xx,y+2,xx,y+h-5),fill=11)
        d.rectangle((x+w//2-2,y+h-3,x+w//2+2,y+h),fill=1)
    for x,y,w,h in [(205,183,20,15),(208,211,23,17),(209,246,19,22),
                      (158,186,15,24),(158,235,14,24),(98,343,17,23),
                      (146,344,21,16),(147,371,18,25),(175,355,22,17)]:building(x,y,w,h)
    # Harbour fingers and cargo, two stationary ships.
    d.rectangle((46,327,95,408),fill=11)
    for yy in (337,367,397):
        d.rectangle((16,yy,60,yy+5),fill=12);d.line((17,yy,59,yy),fill=14)
        for xx in range(51,85,9):d.rectangle((xx,yy-8,xx+5,yy-3),fill=15 if xx%2 else 10)
    # Giant pleasure boats: wooden decks, tiled gable roofs and warm lanterns.
    for x,y in BOATS:
        d.polygon([(x,y-37),(x-12,y-24),(x-13,y+26),(x,y+36),(x+13,y+26),(x+12,y-24)],fill=5)
        d.polygon([(x,y-33),(x-9,y-22),(x-10,y+24),(x,y+31),(x+10,y+24),(x+9,y-22)],fill=15)
        d.rectangle((x-7,y-23,x+7,y+22),fill=10)
        d.rectangle((x-10,y-19,x+10,y+18),fill=11)
        d.line((x,y-24,x,y+23),fill=14,width=2)
        for yy in range(y-18,y+19,4):
            d.line((x-9,yy,x-2,yy-3),fill=12);d.line((x+2,yy-3,x+9,yy),fill=12)
            d.point((x-11,yy),fill=14);d.point((x+11,yy),fill=14)
        # Festival lanterns hang outside both eaves: dark outline, amber
        # paper, warm centre, cap and tassel remain legible during rotation.
        for side in (-1,1):
            lx=x+side*15
            d.line((lx,y-24,lx,y+23),fill=14)
            for yy in range(y-20,y+21,10):
                d.line((x+side*10,yy-3,lx,yy-3),fill=10)
                d.ellipse((lx-3,yy-3,lx+3,yy+4),fill=10)
                d.ellipse((lx-2,yy-2,lx+2,yy+3),fill=15)
                d.line((lx,yy-1,lx,yy+2),fill=14)
                d.line((lx-1,yy-3,lx+1,yy-3),fill=14)
                d.point((lx,yy+5),fill=15)
        # Small pennants over the fore/aft decks, away from the roof tiles.
        for yy in (y-27,y+27):
            d.line((x-9,yy,x+9,yy),fill=14)
            for n in range(4):
                xx=x-8+n*4
                d.polygon([(xx,yy+1),(xx+3,yy+1),(xx+1,yy+5)],fill=15 if n%2 else 14)
        # The pleasure boat is hosting a completely unnecessary cat festival.
        d.rectangle((x-6,y-10,x+6,y+11),fill=10)
        d.rectangle((x-5,y-9,x+5,y+9),fill=15)
        d.ellipse((x-3,y,x+3,y+6),fill=14)
        for px,py in ((x-3,y-3),(x,y-5),(x+3,y-3)):
            d.ellipse((px-1,py-1,px+1,py+1),fill=14)
    for x,y in ((160,68),(189,81),(213,74),(212,103)):
        d.ellipse((x-7,y-5,x+9,y+9),fill=6)
        d.ellipse((x-8,y-8,x+6,y+6),fill=12);d.arc((x-7,y-7,x+5,y+5),180,300,fill=14,width=2)
        d.ellipse((x-3,y-3,x+1,y+1),fill=11)
    # Groves and rocky ridgelines, keeping flight corridor readable.
    rng.setstate(legacy_tree_state)
    for _ in range(220):
        x=rng.randrange(165,254);y=rng.randrange(512)
        if 160<y<290 or 330<y<403 or 50<y<115:continue
        d.ellipse((x,y,x+3,y+4),fill=6);d.point((x,y),fill=9)
    # Additional southern port and festival grounds, outside the original area.
    d.rectangle((25,589,100,605),fill=11)
    # Broad striped fabric awnings, hanging curtains and open food counters.
    # Three readable stalls replace the five tiny arrow-shaped gabled roofs.
    for n,xx in enumerate((29,55,81)):
        accent=(15,3,8)[n]
        d.rectangle((xx+3,579,xx+23,600),fill=6)
        d.rectangle((xx+1,578,xx+19,596),fill=10)
        d.rectangle((xx,575,xx+20,585),fill=10)
        for stripe in range(5):
            left=xx+1+stripe*4
            d.rectangle((left,576,left+3,584),fill=14 if stripe%2==0 else accent)
        d.line((xx+1,575,xx+19,575),fill=13)
        for panel in range(4):
            left=xx+2+panel*5
            d.rectangle((left,585,left+3,587+(panel%2)),fill=accent)
            d.point((left+1,586),fill=14)
        d.line((xx+1,585,xx+1,596),fill=5)
        d.line((xx+19,585,xx+19,596),fill=5)
        d.rectangle((xx+2,591,xx+18,595),fill=5)
        d.line((xx+2,591,xx+18,591),fill=14)
        # Pots/skewers, fish trays, and sweets give the counters distinct stock.
        for k in range(3):
            gx=xx+4+k*5
            d.rectangle((gx,592,gx+3,594),fill=10)
            if n==0:
                d.point((gx+1,592),fill=15);d.point((gx+2,593),fill=14)
            elif n==1:
                d.line((gx,593,gx+2,593),fill=14);d.point((gx+3,592),fill=13)
            else:
                d.ellipse((gx,592,gx+2,594),fill=14);d.point((gx+1,592),fill=15)
        d.line((xx+22,583,xx+22,590),fill=10)
        d.ellipse((xx+20,586,xx+24,591),fill=10)
        d.ellipse((xx+21,587,xx+23,590),fill=15)
        d.line((xx+22,588,xx+22,589),fill=14)
    for xx,yy,ww,hh in ((163,607,21,22),(191,611,22,18),(157,676,20,19),(189,676,23,21)):
        building(xx,yy,ww,hh)
    d.ellipse((169,531,229,587),fill=6)
    d.ellipse((173,535,225,583),fill=9)
    d.line((176,559,223,559),fill=5,width=3)
    d.line((199,537,199,581),fill=5,width=3)
    d.ellipse((190,550,208,568),fill=3);d.ellipse((194,554,204,564),fill=14)
    im.putpalette([c for rgb in GROUND for c in rgb]+[0]*720)
    im.resize((512,WORLD_HEIGHT*2),Image.Resampling.NEAREST).save(A/'terrain-art.png')
    return im
def sprites(ground):
    atlas=Image.new('P',(256,256));h=Image.new('P',(32,64));d=ImageDraw.Draw(h)
    # Original ginger cat seen from above/behind, paws stretched into flight.
    d.line((16,36,21,51,24,54,23,58,19,58),fill=12,width=3)
    d.ellipse((10,20,22,40),fill=12)
    d.ellipse((11,20,19,36),fill=13)
    d.ellipse((6,8,12,24),fill=12);d.ellipse((21,8,27,24),fill=12)
    d.ellipse((6,6,12,13),fill=15);d.ellipse((21,6,27,13),fill=15)
    d.polygon([(9,20),(8,9),(14,13),(21,13),(26,9),(24,24),(20,29),(13,28)],fill=12)
    d.polygon([(10,19),(10,13),(14,16),(20,16),(23,13),(23,22),(19,25),(14,24)],fill=13)
    d.line((14,15,15,19),fill=12);d.line((18,15,18,19),fill=12)
    d.line((11,28,21,28),fill=11,width=2)
    d.ellipse((10,35,14,43),fill=15);d.ellipse((19,35,23,43),fill=15)
    # Short cape is painted over the back, anchored below the neck.
    # Hind paws and tail remain visible beyond its lower edge.
    d.polygon([(11,28),(21,28),(25,39),(18,37),(10,40),(7,37)],fill=9)
    d.polygon([(12,29),(16,30),(13,37),(9,38)],fill=10)
    d.polygon([(18,29),(21,29),(23,37),(18,35)],fill=11)
    d.line((11,28,21,28),fill=11,width=1)
    atlas.paste(h,(0,0))
    for n,degrees in enumerate((-16,-8,0,8,16)):
        pose=h.rotate(degrees,resample=Image.Resampling.NEAREST,center=(16,28))
        atlas.paste(pose,(n*32,192))
        atlas.paste(pose.point(lambda v:1 if v else 0),(64+n*32,128))
    # Eight small cape-tail accents; no borrowed costume or emblem.
    for n in range(8):
        rotor=Image.new('P',(32,64));r=ImageDraw.Draw(rotor);flutter=round(2*math.sin(n*math.tau/8))
        r.line((9,35,8+flutter,38,12,37),fill=11)
        r.line((22,35,24+flutter,38,21,37),fill=10)
        atlas.paste(rotor,(32+n%7*32,0 if n<7 else 64))
    shadow=h.point(lambda v:1 if v else 0);atlas.paste(shadow,(0,128))
    cloud=Image.new('P',(32,64));cp=cloud.load()
    for yy in range(64):
        for xx in range(32):
            density=sum(math.exp(-((xx-cx)/rx)**2-((yy-cy)/ry)**2) for cx,cy,rx,ry in
                        [(8,30,7,13),(17,24,9,16),(23,36,8,13),(12,41,8,9)])
            cp[xx,yy]=min(15,round(density*5)) if density>.2 else 0
    atlas.paste(cloud,(32,128))
    # 48 precomposed 16x16 tiles occupy the unused 192x64 atlas rectangle.
    # HMMM copies six tiles into the terrain at 7.49 animation steps/second.
    commands=[]
    for phase in range(8):
        row=bytearray()
        for n,(tx,ty) in enumerate(PATCHES):
            tile=ground.crop((tx,ty,tx+16,ty+16));q=ImageDraw.Draw(tile)
            step=round(2*math.sin(phase*math.tau/8+n))
            xx=8+(step if n%2 else 0);yy=6+(abs(step)//2 if n%2 else 0)
            q.ellipse((xx-3,yy+5,xx+4,yy+8),fill=10)
            q.rectangle((xx-3,yy+1,xx+3,yy+6),fill=10)
            q.rectangle((xx-2,yy+1,xx+2,yy+5),fill=14)
            q.rectangle((xx-2,yy+2,xx+2,yy+4),fill=3)
            q.line((xx-1,yy+5,xx-3-step//2,yy+8),fill=14)
            q.line((xx+1,yy+5,xx+3+step//2,yy+8),fill=14)
            for arm in ((xx-2,yy+2,xx-5,yy+step-2),(xx+2,yy+2,xx+5,yy-step-2)):
                q.line(arm,fill=10,width=3);q.line(arm,fill=14,width=1)
            q.polygon([(xx-4,yy+1),(xx-4,yy-5),(xx-1,yy-3),(xx+1,yy-3),(xx+4,yy-5),(xx+4,yy+1)],fill=10)
            q.polygon([(xx-3,yy),(xx-3,yy-3),(xx-1,yy-2),(xx+1,yy-2),(xx+3,yy-3),(xx+3,yy)],fill=14)
            q.point((xx-1,yy-1),fill=10);q.point((xx+1,yy-1),fill=10)
            index=phase*6+n;ax=64+(index%12)*16;ay=64+(index//12)*16
            atlas.paste(tile,(ax,ay))
            row+=struct.pack('<HHHHHHBBB',ax,1792+ay,tx,1024+ty,16,16,0,0,0xD0)
        row+=bytes(128-len(row));commands.append(row)
    (A/'festival-commands.inc').write_text('festival_commands:\n'+''.join(' db '+','.join(map(str,row))+'\n' for row in commands))
    atlas.putpalette([c for rgb in HELI for c in rgb]+[0]*720)
    atlas.resize((512,512),Image.Resampling.NEAREST).save(A/'aircraft-art.png')
    return atlas
def motion():
    out=bytearray();meta=[]
    # Altitude cues are independent of the continuous forward flight path.
    cues=[(0,4.0,120,410,-.2),(3,2.4,110,370,.25),
          (6,1.45,128,285,.65),(9,1.65,128,190,2.6),
          (12,3.8,108,128,3.4),(15,2.3,125,205,3.5),
          (18,1.5,128,285,7.0),(21,2.2,120,370,8.8),
          (24,4.5,96,430,9.5),(27,2.4,118,330,10.7),
          (30,1.5,128,250,12.0),(FRAMES/59.9227,4.0,120,410,math.tau*2-.2)]
    def pair(x,y,w,h,pattern,tp=0,pal=1):
        return b''.join(struct.pack('<HBBHBB',(round(y)&1023)|0x8000,round(h),pal|(tp<<6),
              (round(x)+k*(w//2))&1023,w//2,pattern+k) for k in range(2))
    for i in range(FRAMES):
        t=i/FRAMES;phase=math.tau*t
        sec=i/59.9227
        a,b=next((a,b) for a,b in zip(cues,cues[1:]) if a[0]<=sec<b[0])
        u=(sec-a[0])/(b[0]-a[0]);ease=u*u*(3-2*u)
        zoom=a[1]+(b[1]-a[1])*ease
        # Two wider forward circuits. The LRMM heading follows the path tangent:
        # screen-up is (sin(angle),-cos(angle)) in source-map coordinates.
        theta=phase*2
        cx=128+52*math.sin(theta);cy=384+260*math.cos(theta)
        dx=52*math.cos(theta);dy=-260*math.sin(theta)
        angle=math.atan2(dx,-dy)
        ex=128*abs(math.cos(angle))+106*abs(math.sin(angle))
        ey=128*abs(math.sin(angle))+106*abs(math.cos(angle))
        zoom=max(zoom,ex/(min(cx,256-cx)-3),ey/(min(cy,WORLD_HEIGHT-cy)-3))
        vx=round(math.cos(angle)*256/zoom);vy=round(math.sin(angle)*256/zoom)
        sx=round(cx-(128*vx-106*vy)/256);sy=round(1024+cy-(128*vy+106*vx)/256)
        for x,y in ((0,0),(255,0),(0,211),(255,211)):
            xx=sx+(x*vx-y*vy)/256;yy=sy+(x*vy+y*vx)/256
            assert 0<=xx<256 and 1024<=yy<1024+WORLD_HEIGHT,(i,xx,yy)
        turn=-52*260/(dx*dx+dy*dy)*(math.tau*2*59.9227/FRAMES)
        bank=max(0,min(4,round(2-turn*2)))
        x=110+12*math.sin(phase*2)-turn*5;y=91+8*math.sin(phase*3)
        # Body and rotor stay near camera; distant ground shadow follows altitude.
        attrs=pair(x,y,36,72,192+bank*2)
        rotor=(i%8);pattern=2+rotor%7*2+(64 if rotor==7 else 0)
        attrs=pair(x,y,36,72,pattern,2)+attrs
        shadow_w=2*round((10+zoom*5)/2)
        # Fixed world-space sunlight from northwest; shadow points southeast.
        altitude=4+18*(4.5-zoom)
        world_shadow=(altitude*.6,altitude*.8)
        shadow_dx=zoom*(math.cos(angle)*world_shadow[0]+math.sin(angle)*world_shadow[1])
        shadow_dy=zoom*(-math.sin(angle)*world_shadow[0]+math.cos(angle)*world_shadow[1])
        attrs+=pair(x+18+shadow_dx-shadow_w/2,y+36+shadow_dy-shadow_w,shadow_w,shadow_w*2,132+bank*2,2)
        attrs+=pair(20+145*math.sin(phase*2),20+45*math.sin(phase*3),108,45,130,2,2)
        attrs+=pair(118+150*math.cos(phase*2),153+40*math.sin(phase*3),128,48,130,3,2)
        out+=struct.pack('<hhhh',sx,sy,vx,vy)+attrs+bytes(40)
        meta.append(dict(frame=i,zoom=zoom,angle=angle,cx=cx,cy=cy,
                         shadow_screen_offset=[shadow_dx,shadow_dy],shadow_world_offset=list(world_shadow),
                         forward_pixels_per_frame=math.hypot(dx,dy)*math.tau*2/FRAMES*zoom))
    assert len(out)==FRAMES*128
    (A/'motion.json').write_text(json.dumps(meta))
    return out
def main():
    A.mkdir(exist_ok=True)
    ground=terrain()
    (A/'background.bin').write_bytes(packed(ground))
    (A/'sprites.bin').write_bytes(packed(sprites(ground)))
    (A/'motion.bin').write_bytes(motion())
    cloudpal=[(0,0,0)]+[(105+i*9,135+i*7,158+i*6) for i in range(1,16)]
    pal=GROUND+HELI+cloudpal+HELI
    (A/'palettes.inc').write_text('initial_palette:\n db '+','.join(str(round(c*31/255)) for rgb in pal for c in rgb)+'\n')
    work=ROOT/'work/build';work.mkdir(parents=True,exist_ok=True)
    pasmo=os.environ.get('PASMO') or shutil.which('pasmo') or 'C:/Software/Pasmo/pasmo.exe'
    for src,name in [('src/boot.asm','boot'),('src/demo.asm','demo')]:
        subprocess.run([pasmo,'--bin',src,str(work/f'{name}.bin'),str(work/f'{name}.symbols')],cwd=ROOT,check=True)
    runtime=(work/'demo.bin').read_bytes();assert len(runtime)<24576
    rom=(work/'boot.bin').read_bytes()+runtime+bytes([255])*(24576-len(runtime))
    for name in ('background','sprites','motion'):rom+=(A/f'{name}.bin').read_bytes()
    assert len(rom)==425984
    rom+=bytes([255])*(524288-len(rom))
    target=ROOT/'outputs/SUPER_CAT-COASTAL_FLIGHT-V9968-legacy-openmsx-internal.rom';target.write_bytes(rom)
    (ROOT/'outputs/build-manifest.json').write_text(json.dumps(dict(sha256=hashlib.sha256(rom).hexdigest(),
        rom_bytes=len(rom),frames=FRAMES,world_size=[256,WORLD_HEIGHT],boat_cats=len(PATCHES),
        profile='legacy-openmsx-internal',hardware_tested=False),indent=2))
    print('Built',target)
if __name__=='__main__':main()
