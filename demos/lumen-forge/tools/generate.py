"""Original light installation: stable SCREEN8 chamber and live FG4 crystal."""
from pathlib import Path
import math, struct, json
from PIL import Image, ImageDraw, ImageFilter, ImageChops, ImageFont
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'assets'
TAU=math.tau
FRAMES=1024
def clamp(v): return max(0,min(255,round(v)))

def artwork():
    im=Image.new('RGB',(256,256)); px=im.load()
    for y in range(212):
        for x in range(256):
            c=math.exp(-((x-51)**2/4300+(y-98)**2/7800))
            r=math.exp(-((x-210)**2/3400+(y-113)**2/8000))
            h=math.exp(-((x-128)**2/1900+(y-119)**2/6100))
            px[x,y]=(clamp(3+13*c+38*r+13*h),clamp(4+25*c+5*r+12*h),clamp(12+39*c+38*r+29*h))
    d=ImageDraw.Draw(im)
    for side in (-1,1):
        def poly(points,fill): d.polygon([(128+side*x,y) for x,y in points],fill=fill)
        poly([(80,33),(110,24),(127,46),(127,170),(79,159)],(10,14,29))
        poly([(91,46),(110,35),(110,149),(91,155)],(18,28,45) if side<0 else (38,21,44))
        poly([(110,35),(118,44),(118,158),(110,149)],(6,10,23))
        poly([(79,57),(85,52),(85,145),(79,147)],(27,43,57))
    d.polygon([(0,174),(90,149),(164,149),(255,176),(255,211),(0,211)],fill=(7,11,24))
    d.polygon([(48,188),(83,166),(171,166),(209,188),(173,204),(83,204)],fill=(18,27,40))
    d.polygon([(48,188),(83,195),(173,195),(209,188),(173,204),(83,204)],fill=(7,18,30))
    d.polygon([(61,186),(90,169),(165,169),(197,186),(170,197),(87,197)],fill=(11,28,39))
    lights=Image.new('RGB',(256,256)); l=ImageDraw.Draw(lights)
    for side,col in [(-1,(22,148,193)),(1,(213,60,104))]:
        for x in [83,110]: l.line([(128+side*x,45),(128+side*x,151)],fill=col)
        l.line([(128+side*125,171),(128+side*73,154)],fill=col)
        for n in range(4):
            x=128+side*(91+n*5); l.line([(x,153),(x,157)],fill=col)
    for radius in [52,68,83]:
        l.arc((128-radius,100-radius,128+radius,100+radius),205,335,fill=(24,51,79))
        l.arc((128-radius,100-radius,128+radius,100+radius),25,155,fill=(43,31,64))
    for y in [49,61,139,151]:
        l.line((84,y,172,y),fill=(33,58,79)); l.line((124,y,132,y),fill=(99,156,169))
    l.line((128,39,128,160),fill=(28,63,78))
    for x in [0,30,68,188,226,255]: l.line((128+(x-128)*.31,155,x,211),fill=(13,46,61))
    l.line([(49,187),(84,166),(171,166),(208,187)],fill=(37,146,169))
    l.line([(63,190),(87,197),(170,197),(193,189)],fill=(31,96,128))
    l.arc((84,173,172,190),0,359,fill=(73,191,210)); l.arc((97,177,159,186),0,359,fill=(109,213,222))
    l.line((114,181,142,181),fill=(206,239,227))
    im=ImageChops.add(ImageChops.add(im,lights.filter(ImageFilter.GaussianBlur(3))),lights)
    d=ImageDraw.Draw(im); font=ImageFont.load_default(size=10)
    d.text((12,9),'LUMEN / FORGE',font=font,fill=(172,205,214)); d.text((198,10),'V9968',font=font,fill=(98,139,159))
    d.line((12,23,243,23),fill=(36,51,68)); d.rectangle((12,22,45,23),fill=(54,193,213)); d.rectangle((235,22,243,23),fill=(232,85,133))
    bayer=((0,8,2,10),(12,4,14,6),(3,11,1,9),(15,7,13,5)); px=im.load()
    for y in range(256):
        for x in range(256):
            k=(bayer[y%4][x%4]+.5)/16
            px[x,y]=tuple(round(min(31,max(0,math.floor(c*31/255+k)))*255/31) for c in px[x,y])
    q=im.quantize(colors=192,method=Image.Quantize.MEDIANCUT); rgb=q.getpalette()[:576]
    return q,[tuple(round(rgb[i+k]*31/255) for k in range(3)) for i in range(0,576,3)]

def sprite_art():
    im=Image.new('P',(256,256),0); d=ImageDraw.Draw(im)
    def point(r,a): return (round(63.5+r*math.cos(a)),round(63.5+r*math.sin(a)))
    for n in range(3):
        a=-math.pi/2+n*TAU/3
        tip=point(60,a); outer=point(53,a+.49); shoulder=point(30,a+.91)
        root=point(12,a+.82); inner=point(22,a-.27); ridge=point(38,a+.25)
        d.polygon([tip,outer,shoulder,root,inner],fill=2+n*4)
        d.polygon([tip,outer,ridge,inner],fill=3+n*4)
        d.polygon([outer,shoulder,root,ridge],fill=1+n*4)
        d.polygon([ridge,root,inner],fill=4+n*4)
        d.line([tip,outer,shoulder],fill=15); d.line([tip,ridge,root],fill=13); d.line([inner,tip],fill=14)
        px,py=point(52,a+1.22)
        d.polygon([(px,py-4),(px+3,py),(px,py+4),(px-3,py)],fill=12-n*3); d.point((px,py-3),fill=15)
    center=[point(15,-math.pi/2+i*TAU/6) for i in range(6)]
    for i in range(6): d.polygon([(64,64),center[i],center[(i+1)%6]],fill=[15,7,3,10,5,13][i])
    d.line(center+[center[0]],fill=14)
    # Independent 64x64 engraved halo, transformed by a second live LRMM.
    d.ellipse((130,2,189,61),fill=6)
    d.ellipse((132,4,187,59),fill=13)
    d.ellipse((135,7,184,56),fill=8)
    d.ellipse((138,10,181,53),fill=0)
    for n in range(4):
        a=n*TAU/4
        points=[(round(159.5+r*math.cos(a+da)),round(31.5+r*math.sin(a+da))) for r,da in [(31,0),(27,.15),(23,0),(27,-.15)]]
        d.polygon(points,fill=15)
    for n in range(3):
        a=n*TAU/3
        points=[(round(159.5+r*math.cos(a+da)),round(31.5+r*math.sin(a+da))) for r,da in [(19,0),(17,.34),(19,.56)]]
        d.line(points,fill=12,width=1)
    for y in range(16):
        for x in range(16):
            dx,dy=x-7.5,y-7.5; rr=abs(dx)+abs(dy)
            if rr<7.5: im.putpixel((192+x,y),min(15,round(3+12*(1-rr/7.5))))
            glow=max(math.exp(-(dx/1.1)**2-(dy/5)**2),math.exp(-(dy/1.1)**2-(dx/5)**2))
            if glow>.08: im.putpixel((208+x,y),round(3+12*glow))
    return im

def sprite_palettes(phase):
    f=math.sin(TAU*phase/32)*.5+.5
    crystal=[(0,0,0),(22,76,133),(39,136,201),(89,219,239),(156,245,249),(76,38,144),(136,66,204),(191,131,239),(232,198,253),(153,44,80),(220,83,91),(255,156,106),(255,220,158),(110,228,244),(194,238,255),(255,250,223)]
    result=[tuple(round(min(255,c+((1-f)*7 if k==0 else f*7))*31/255) for k,c in enumerate(col)) if i else (0,0,0) for i,col in enumerate(crystal)]
    for color in [(50,210,245),(235,107,176),(235,191,110)]:
        result.append((0,0,0))
        for i in range(1,16):
            t=i/15; white=max(0,(t-.65)/.35)
            result.append(tuple(round((c*(.25+.75*t)+(255-c)*white)*31/255) for c in color))
    return result

def motion():
    data=bytearray()
    for frame in range(FRAMES):
        t=TAU*frame/FRAMES; angle=t*2
        vx,vy=round(math.cos(angle)*256),round(math.sin(angle)*256)
        sx=round(64-64*(vx-vy)/256); sy=round(1344-64*(vx+vy)/256)
        data.extend(struct.pack('<hhhh',sx,sy,vx,vy)); sprites=[]
        for n in range(2):
            a=t+n*TAU/2; x=round(127+89*math.cos(a)); y=round(108+58*math.sin(a))
            width=round(6+8*(1+math.sin(a))*.5)
            sprites.append(struct.pack('<HBBHBB',y&1023,width,(13+n)|(3<<6),x&1023,width,12+n))
        # The orbiting halo is a separate angle/size transform, at higher priority.
        width=round(90+17*math.sin(t+.8)); height=round(width*(.80+.16*math.cos(t)))
        left=round(164+12*math.cos(t)-width/2); top=round(113+9*math.sin(t)-height/2)
        edges=[round(left+width*k/4) for k in range(5)]
        for k in range(4): sprites.append(struct.pack('<HBBHBB',(top&1023)|0x8000,height,15|(1<<6),edges[k]&1023,edges[k+1]-edges[k],8+k))
        size=round(139+22*math.sin(t-.7)); cx=112; cy=96+4*math.sin(t)
        left,top=round(cx-size/2),round(cy-size/2); edges=[round(left+size*k/8) for k in range(9)]
        for k in range(8): sprites.append(struct.pack('<HBBHBB',(top&1023)|0xc000,size,12|(2<<6),edges[k]&1023,edges[k+1]-edges[k],k))
        data.extend(b''.join(sprites)); data.extend(bytes([(frame//8)%32,(frame//64)%16])+bytes(6))
        vx2,vy2=round(math.cos(-t*3)*256),round(math.sin(-t*3)*256)
        sx2=round(160-32*(vx2-vy2)/256); sy2=round(1312-32*(vx2+vy2)/256)
        data.extend(struct.pack('<hhhh',sx2,sy2,vx2,vy2)+bytes(120))
    assert len(data)==262144
    return data

def generate():
    ASSETS.mkdir(exist_ok=True); bg,pal=artwork(); sp=sprite_art(); bgbytes=bg.tobytes(); pixels=list(sp.getdata())
    spbytes=bytes((pixels[i]<<4)|pixels[i+1] for i in range(0,65536,2))
    (ASSETS/'vram-upload.bin').write_bytes(bgbytes[::2]+spbytes+bgbytes[1::2]); (ASSETS/'background-indexed.bin').write_bytes(bgbytes)
    (ASSETS/'sprites.bin').write_bytes(spbytes); (ASSETS/'motion.bin').write_bytes(motion())
    rgb=pal+sprite_palettes(0); rows=['initial_palette:']
    for start in range(0,256,16): rows.append('    db '+','.join(str(c) for p in rgb[start:start+16] for c in p))
    rows+=['pulse_palettes:']
    for phase in range(32): rows.append('    db '+','.join(str(c) for p in sprite_palettes(phase) for c in p))
    rows+=['chords:']
    for chord in [(428,856,285),(381,856,285),(339,678,254),(285,678,214),(320,640,214),(339,640,254),(381,762,254),(428,762,285)]*2: rows.append('    dw '+','.join(map(str,chord)))
    (ASSETS/'palettes.inc').write_text('\n'.join(rows)+'\n',encoding='ascii')
    bg.putpalette([round(c*255/31) for p in rgb for c in p]); bg.crop((0,0,256,212)).resize((768,636),Image.Resampling.NEAREST).save(ASSETS/'chamber-art.png')
    sp.putpalette([round(c*255/31) for p in sprite_palettes(0)[:16] for c in p]+[0]*720); sp.crop((0,0,224,128)).resize((896,512),Image.Resampling.NEAREST).save(ASSETS/'crystal-art.png')
    (ASSETS/'layout.json').write_text(json.dumps({'mode':'SCREEN8 + EPAL + Sprite3 + FG4 LRMM','frames':FRAMES,'record_bytes':256,'maximum_sprites_per_line':14,'background_physical':['0x20000-0x27fff','0x30000-0x37fff'],'source_atlas_physical':'0x28000-0x2bfff','rotated_atlas_physical':['0x38000-0x3bfff','0x3c000-0x3ffff'],'SAT_physical':['0x07000','0x07200'],'SAT_cpu_logical':['0x0e000','0x0e400'],'SAT_upload':'each attribute byte written twice; d884 mode3 physical reader workaround','rotation':'two live FG4 LRMM transforms, 128x128 and64x64; no stored rotation frames','scaling':'Sprite3 destination width and height','background':'stationary','hardware_validation':False},indent=2)+'\n')
if __name__=='__main__': generate()
