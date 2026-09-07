"""Original pixel landscape, masked tree atlas, translucent fog and motion parameters."""
from pathlib import Path
import math,random,struct,json
from PIL import Image,ImageDraw,ImageFont
ROOT=Path(__file__).resolve().parents[1]
ASSETS=ROOT/'assets'; FRAMES=1024; TAU=math.tau

def mix(a,b,t): return tuple(round(x+(y-x)*max(0,min(1,t))) for x,y in zip(a,b))
def clamp(x): return max(0,min(255,round(x)))

def pine(draw,x,base,height,width,colors,seed):
    rng=random.Random(seed); trunk,shadow,body,tip=colors
    draw.line((x,base-height*.80,x,base),fill=trunk,width=2 if width>25 else 1)
    for layer in range(12):
        f=layer/12; y=base-height+height*f*.89
        half=width*.5*(.06+.94*f)*(1+rng.uniform(-.10,.10))
        drop=height*.14*(.4+.6*f)
        pts=[(x,y-height*.035),(x-half*.55,y+drop*.42),(x-half,y+drop),
             (x-half*.33,y+drop*.88),(x-half*.57,y+drop*1.2),(x,y+drop*.99),
             (x+half*.74,y+drop*1.2),(x+half*.43,y+drop*.77),(x+half,y+drop),
             (x+half*.36,y+drop*.33)]
        draw.polygon(pts,fill=shadow)
        draw.polygon([(x,y-height*.03),(x-half*.8,y+drop*.79),(x-half*.24,y+drop*.63),(x+half*.34,y+drop*.73)],fill=body)
        if width>22:
            draw.line((x,y,x-half*.69,y+drop*.63),fill=tip,width=1)
            for _ in range(3):
                xx=x+rng.uniform(-half*.66,half*.48)
                draw.point((int(xx),int(y+drop*rng.uniform(.65,.95))),fill=body)

def artwork():
    im=Image.new('RGB',(256,256),(5,13,23)); px=im.load()
    for y in range(172):
        base=mix((41,47,91),(232,166,151),(y/151)**.8)
        for x in range(256):
            halo=math.exp(-((x-183)**2+(y-59)**2)/1350)
            cloud=math.exp(-((y-(37+7*math.sin(x/57)))/3.4)**2)*(.3+.7*(math.sin(x/36)*.5+.5))
            px[x,y]=mix(base,(255,216,171),min(.9,halo*.52+cloud*.20))
    d=ImageDraw.Draw(im)
    d.ellipse((173,45,195,67),fill=(255,226,182))
    d.ellipse((176,48,192,64),fill=(255,236,201))
    # Irregular ridges, branching gullies and broken snowfields create rock texture.
    controls=[(0,112),(20,102),(37,110),(56,91),(72,77),(82,86),(99,79),(108,68),(117,78),(130,70),(143,57),(154,76),(171,104),(182,91),(193,80),(211,108),(236,92),(255,111)]
    ridge=[]
    for x in range(256):
        j=next(i for i in range(len(controls)-1) if controls[i][0]<=x<=controls[i+1][0])
        a,b=controls[j],controls[j+1]; f=(x-a[0])/(b[0]-a[0])
        ridge.append(round(a[1]+(b[1]-a[1])*f+1.6*math.sin(x*1.07)+.9*math.sin(x*2.3)))
    peaks=[(72,77),(108,68),(143,57),(193,80),(236,92)]
    for x in range(256):
        for y in range(ridge[x],151):
            peak=min(peaks,key=lambda p:abs(x-p[0])+.35*abs(ridge[x]-p[1]))
            depth=y-ridge[x]
            folded=math.sin(x*.25+depth*.17)+.52*math.sin(x*.78-depth*.31)+.21*math.sin(x*1.91+y*.81)
            face=.48+.22*math.tanh((peak[0]-x)/(7+depth*.24))+.10*folded
            rock=mix((49,66,104),(130,133,160),face)
            snow_depth=max(0,97-ridge[x])*.52
            snow=depth<snow_depth+4.1*math.sin(x*.44+depth*.16)+2.0*math.sin(x*1.17)
            if snow: rock=mix((155,152,176),(248,211,195),.32+.48*face)
            haze=max(0,(y-109)/66)
            px[x,y]=mix(rock,(112,131,149),haze*.44)
    ridge2=[(0,123),(24,114),(43,123),(63,109),(86,127),(108,115),(134,132),(153,119),(178,134),(197,119),(223,135),(244,123),(255,126)]
    d.polygon(ridge2+[(255,166),(0,166)],fill=(42,69,96))
    for y in range(134,165):
        col=mix((52,85,106),(87,126,138),(y-134)/31)
        d.line((0,y,255,y),fill=col)
    rng=random.Random(99681)
    for x in range(-3,262,5):
        pine(d,x,151+rng.randrange(5),rng.randrange(9,25),rng.randrange(5,13),[(45,82,96),(46,83,98),(65,99,111),(85,119,128)],x+17)
    # Distant bank and shadowed near bank support the moving tree bases.
    d.polygon([(0,151),(30,149),(68,155),(106,148),(146,156),(189,150),(221,155),(255,148),(255,173),(0,173)],fill=(23,52,66))
    d.line([(0,168),(45,171),(98,168),(139,171),(182,168),(229,171),(255,169)],fill=(130,159,155))
    # Static reflected artwork; runtime raster offsets supply the moving ripples.
    px=im.load()
    for y in range(173,212):
        sy=142-round((y-173)*1.42)
        for x in range(256):
            col=mix(im.getpixel((x,sy)),(21,48,68),.57)
            light=math.exp(-((x-184)/max(9,6+(y-173)*.47))**2)*.33
            px[x,y]=mix(col,(226,191,155),light)
    d=ImageDraw.Draw(im)
    for n in range(75):
        y=rng.randrange(176,211); x=rng.randrange(6,247); w=rng.randrange(2,14)
        col=(85,124,136) if n%3 else (121,151,155)
        d.line((x,y,min(251,x+w),y),fill=col)
    # R25.MSK masks the exposed left edge; the artwork fills the right edge.
    font=ImageFont.load_default(size=9)
    d.text((11,7),'MIST / VALE',font=font,fill=(208,209,216))
    d.text((216,8),'9968',font=font,fill=(145,157,187))
    trees=Image.new('RGBA',(256,96),(0,0,0,0)); td=ImageDraw.Draw(trees)
    for n,(height,width) in enumerate([(92,44),(79,42),(88,46),(71,38),(95,44)]):
        pine(td,n*48+24,95,height,width,[(16,37,46,255),(11,35,46,255),(22,64,69,255),(52,97,93,255)],100+n)
        td.line((n*48+24,92,n*48+23,95),fill=(22,40,46,255),width=2)
    return im,trees

def quantize(bg,trees):
    joined=Image.new('RGB',(256,352),(0,0,0)); joined.paste(bg,(0,0)); joined.paste(trees.convert('RGB'),(0,256))
    # Stable ordered quantization into RGB5, then one shared background palette.
    bayer=((0,8,2,10),(12,4,14,6),(3,11,1,9),(15,7,13,5)); px=joined.load()
    for y in range(352):
        for x in range(256):
            th=(bayer[y%4][x%4]+.5)/16
            px[x,y]=tuple(round(min(31,max(0,math.floor(c*31/255+th)))*255/31) for c in px[x,y])
    q=joined.quantize(colors=191,method=Image.Quantize.MEDIANCUT)
    pal=q.getpalette()[:573]; palette=[(0,0,0)]+[tuple(round(pal[i+k]*31/255) for k in range(3)) for i in range(0,573,3)]
    values=q.tobytes(); b=bytes(v+1 for v in values[:65536]); alpha=trees.getchannel('A').tobytes()
    t=bytes(v+1 if alpha[i] else 0 for i,v in enumerate(values[65536:]))
    return b,t,palette

def ground_art(palette):
    """A seamless 176px bank, sharing the existing palette and tree world phase."""
    period,height=176,36
    im=Image.new('RGBA',(period,height),(0,0,0,0)); px=im.load()
    surface=[round(4+2*math.sin(TAU*x/period)+math.sin(3*TAU*x/period+.3)) for x in range(period)]
    rng=random.Random(996836)
    for x in range(period):
        for y in range(surface[x],height):
            depth=y-surface[x]
            col=mix((27,62,64),(14,36,49),min(1,depth/21))
            if depth<2: col=mix(col,(53,86,80),.38)
            if rng.randrange(19)==0: col=mix(col,(42,70,73),.32)
            px[x,y]=(*col,255)
    # Wrapped features give the soil trackable landmarks, without a tile seam.
    d=ImageDraw.Draw(im)
    for n in range(28):
        x=rng.randrange(period); y=surface[x]+rng.randrange(1,8)
        length=rng.randrange(2,6)
        for shift in (-period,0,period):
            d.line((x+shift,y,x+shift+length,y),fill=(35,70,68,255))
            if n%3==0:
                d.line((x+shift+1,y,x+shift,y-2),fill=(49,85,77,255))
    for x,y,w in [(14,14,5),(47,23,3),(83,17,6),(122,25,4),(160,13,4)]:
        for shift in (-period,0,period):
            d.ellipse((x+shift-1,y,x+shift+w+1,y+3),fill=(10,30,41,255))
            d.polygon([(x+shift,y+1),(x+shift+1,y-1),(x+shift+w-1,y-1),(x+shift+w,y+1)],fill=(51,74,82,255))
            d.line((x+shift+1,y-1,x+shift+w-2,y-1),fill=(78,96,98,255))
    # The entire shoreline belongs to this bank and travels with its trees.
    for x in range(period):
        rim=31+round(math.sin(TAU*x/period*2)+.6*math.sin(TAU*x/period*5))
        for y in range(rim,height): px[x,y]=(15,36,48,255)
        px[x,rim]=(91,119,120,255)
        if x%7<3: px[x,rim+1]=(45,79,88,255)
    # Map only the new bank to the existing RGB5 palette; other art stays exact.
    colors=[tuple(round(c*255/31) for c in p) for p in palette]
    cache={}; out=bytearray(256*height)
    for y in range(height):
        for x in range(period):
            color=px[x,y]
            if color[3]:
                rgb=color[:3]
                if rgb not in cache:
                    cache[rgb]=min(range(1,len(colors)),key=lambda i:sum((a-b)**2 for a,b in zip(rgb,colors[i])))
                out[y*256+x]=cache[rgb]
        # Continue the 176px period through the 80 spare columns. This lets
        # a 256px screen strip wrap with at most two VDP copy commands.
        out[y*256+period:(y+1)*256]=out[y*256:y*256+80]
    assert all(out[y*256+x] for y in range(8,36) for x in range(256))
    return bytes(out)

def fog_art():
    im=Image.new('P',(256,128)); px=im.load()
    for n in range(3):
        for y in range(32):
            for x in range(64):
                xx=x/63; yy=y/31
                envelope=math.sin(math.pi*xx)**.7
                center=.48+.12*math.sin(xx*TAU+n*.8)
                strand=math.exp(-((yy-center)/(.12+.09*math.sin(xx*math.pi)))**2)
                strand+=.30*math.exp(-((yy-center-.18*math.sin(xx*8+n))/.075)**2)
                fibers=.76+.24*math.sin(xx*15+yy*7+n)
                value=envelope*strand*fibers
                if value>.12: px[x+n*64,y]=min(15,max(1,round(value*13)))
    return im

def sprite_palettes(phase):
    out=[]
    for n in range(4):
        out.append((0,0,0))
        for i in range(1,16):
            f=i/15; pulse=math.sin(TAU*phase/32)*2
            col=mix((78+2*n,113+2*n,124+2*n),(221,231,219),f)
            out.append(tuple(round(max(0,min(255,c+pulse))*31/255) for c in col))
    return out

def motion():
    result=bytearray()
    for frame in range(FRAMES):
        record=bytearray(256)
        for n in range(5):
            progress=(frame*352//FRAMES+n*70)%352; left=288-progress; top=52+[-4,0,4,2,-2][n]
            dx=max(0,left); sx=n*48+max(0,-left); width=max(0,min(256,left+48)-dx)
            record[n*15:n*15+15]=struct.pack('<HHHHHHBBB',sx,768,dx,top,width,96,0,0,0x98)
        for n in range(3):
            progress=(frame*576//FRAMES+n*192)%576
            left=288-progress; top=[72,100,127][n]+progress*18//576
            width=[224,208,192][n]; height=[45,42,37][n]
            edges=[round(left+width*k/4) for k in range(5)]
            for k in range(4):
                attr=struct.pack('<HBBHBB',(top&1023)|0x4000,height,(12+n)|(3<<6),edges[k]&1023,edges[k+1]-edges[k],n*4+k)
                offset=80+(n*4+k)*8; record[offset:offset+8]=attr
        record[176]=(frame//8)%32; record[177]=(frame//64)%16; record[178]=(frame//2)%32
        # One world position for tree trunks, soil, grass, rocks and shore.
        phase=(frame*352//FRAMES)%176
        # Only the upper grassy contour needs transparent copying. The solid
        # soil/shore below uses HMMM, preserving the same pixels with less work.
        for band,(sy,dy,height,command) in enumerate([(724,136,8,0x98),(732,144,28,0xD0)]):
            for part,(sx,dx,width) in enumerate([(phase,0,256-phase),(80,256-phase,phase)]):
                offset=180+(band*2+part)*15
                record[offset:offset+15]=struct.pack('<HHHHHHBBB',sx,sy,dx,dy,width,height,0,0,command)
        result.extend(record)
    return result

def generate():
    ASSETS.mkdir(exist_ok=True); bg,trees=artwork(); background,tree,palette=quantize(bg,trees); fog=fog_art()
    ground=ground_art(palette)
    background=background[:212*256]+ground+background[248*256:]
    pixels=fog.tobytes(); packed=bytes((pixels[i]<<4)|pixels[i+1] for i in range(0,len(pixels),2))
    upload=bytearray(131072)
    upload[0:32768]=background[::2]; upload[65536:98304]=background[1::2]
    upload[0x8000:0xB000]=tree[::2]; upload[0x18000:0x1B000]=tree[1::2]
    upload[0xC000:0x10000]=packed
    (ASSETS/'vram-upload.bin').write_bytes(upload); (ASSETS/'background-indexed.bin').write_bytes(background)
    (ASSETS/'trees-indexed.bin').write_bytes(tree); (ASSETS/'fog.bin').write_bytes(packed); (ASSETS/'motion.bin').write_bytes(motion())
    (ASSETS/'ground-indexed.bin').write_bytes(ground)
    full=palette+sprite_palettes(0); rows=['initial_palette:']
    for start in range(0,256,16): rows.append('    db '+','.join(str(c) for p in full[start:start+16] for c in p))
    rows+=['pulse_palettes:']
    for phase in range(32): rows.append('    db '+','.join(str(c) for p in sprite_palettes(phase) for c in p))
    rows+=['chords:']
    for chord in [(428,856,285),(381,856,285),(339,678,254),(285,678,214),(320,640,214),(339,640,254),(381,762,254),(428,762,285)]*2:
        rows.append('    dw '+','.join(map(str,chord)))
    raster=[]; rows+=['raster_offsets:']
    for phase in range(32):
        offsets=[round(2+2*math.sin(TAU*phase/32+n*.79)) for n in range(10)]+[0]
        raster.append(offsets); rows.append('    db '+','.join(map(str,offsets)))
    (ASSETS/'palettes.inc').write_text('\n'.join(rows)+'\n',encoding='ascii')
    (ASSETS/'raster-offsets.bin').write_bytes(bytes(c for row in raster for c in row))
    pal=[round(c*255/31) for p in full for c in p]
    preview=Image.frombytes('P',(256,256),background); preview.putpalette(pal)
    preview.crop((0,0,256,212)).resize((768,636),Image.Resampling.NEAREST).save(ASSETS/'landscape-art.png')
    tp=Image.frombytes('P',(256,96),tree); tp.putpalette(pal); tp.resize((768,288),Image.Resampling.NEAREST).save(ASSETS/'trees-art.png')
    gp=Image.frombytes('P',(256,36),ground); gp.putpalette(pal); gp.crop((0,0,176,36)).resize((704,144),Image.Resampling.NEAREST).save(ASSETS/'ground-art.png')
    fog.putpalette([round(c*255/31) for p in sprite_palettes(0)[:16] for c in p]+[0]*720)
    fog.crop((0,0,192,32)).resize((768,128),Image.Resampling.NEAREST).save(ASSETS/'fog-art.png')
    (ASSETS/'layout.json').write_text(json.dumps({'mode':'SCREEN8 + EPAL + Sprite3 + R19 raster','frames':1024,'record_bytes':256,'motion_rom_first_bank':20,'tree_count':5,'fog_sprite_count':12,'maximum_sprites_per_line':12,'source_background_logical':'0x20000','source_trees_logical':'0x30000','source_ground_y':724,'ground_period_pixels':176,'ground_display_band':[136,171],'ground_command_record_offset':180,'ground_command_count':4,'ground_transparent_rows':8,'ground_opaque_rows':28,'ground_phase':'floor(frame*352/1024) modulo 176, shared with trees','fog_atlas_physical':'0x2c000-0x2ffff','tree_restore_band':[48,143],'foreground_composite_band':[48,171],'water_raster_lines':[172,211],'raster_offset_pixels':[0,4],'hardware_tested':False},indent=2)+'\n')

if __name__=='__main__': generate()
