"""Deterministic original assets and V9968 motion records for CATSTRIDER.

Photographic source is generated, then chroma-keyed/quantized solely for ROM
encoding. No supplied reference photographs or commercial game assets ship.
"""
from pathlib import Path
import math, random, struct, json, hashlib, colorsys
from PIL import Image, ImageDraw, ImageFont
import props, stage, effects, photo_props

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT/'assets'
FRAMES = stage.FRAMES
LAYOUT = {
    'cat': (0,0,48,64,12),
    'cat_flight': (0,64,48,64,12),
    'fish': (48,0,32,64,13),
    'can': (80,0,32,64,14),
    'boss': (112,0,64,128,13),
    'rainbow': (176,0,16,64,15),
    'laser': (192,0,16,128,15),
    'shadow': (208,0,16,16,15),
    'flare': (224,0,16,32,15),
    'ending': (0,128,128,32,15),
    'ring': (128,128,64,64,15),
    'streak_left': (208,32,16,64,15),
    'streak_right': (224,32,16,64,15),
}


def mix(a,b,t):
    t = max(0,min(1,t))
    return tuple(round(x+(y-x)*t) for x,y in zip(a,b))


def rgb5(c):
    return tuple(round(v*31/255) for v in c)


def sky_and_ground():
    rng = random.Random(99682026)
    im = Image.new('RGB',(256,256),(5,6,20))
    p = im.load()
    # Original analytic nebula, no stock photo. Its dark voids keep the main
    # character and approaching objects distinct at the real 256px resolution.
    for y in range(100):
        for x in range(256):
            u,v=x/256,y/100
            cloud_y=62-35*u+8*math.sin(u*7)
            dust=math.exp(-((y-cloud_y)/16)**2)
            filaments=.46+.20*math.sin(x*.083+y*.107)+.18*math.sin(x*.181-y*.124)+.10*math.sin(x*.38+y*.273)
            cloud=max(0,dust*filaments)
            base=mix((5,5,20),(24,13,44),v)
            color=mix(base,(177,36,216),cloud*.95)
            cyan=math.exp(-((x-172)**2/2200+(y-30)**2/280))*(.4+.6*filaments)
            color=mix(color,(32,212,237),cyan*.82)
            p[x,y]=color
    d=ImageDraw.Draw(im)
    for i in range(210):
        x,y=rng.randrange(256),rng.randrange(4,98)
        col=rng.choice([(61,74,114),(87,124,152),(186,204,221),(242,218,194)])
        d.point((x,y),fill=col)
        if i<8:
            d.line((x-2,y,x+2,y),fill=mix(col,(9,9,28),.55))
            d.line((x,y-2,x,y+2),fill=mix(col,(9,9,28),.55))
            d.point((x,y),fill=(242,242,218))
    # An original small copper moon with a sharply lit crescent and cloud bands.
    cx,cy,r=49,43,23
    for yy in range(-r,r+1):
        for xx in range(-r,r+1):
            q=(xx*xx+yy*yy)/r**2
            if q<=1:
                nx,ny=xx/r,yy/r
                nz=math.sqrt(1-q)
                light=max(0,-.65*nx-.37*ny+.67*nz)
                stripe=.8+.12*math.sin(yy*.8+xx*.17)+.06*math.sin(yy*1.8)
                col=mix((25,12,31),(237,157,116),light*stripe)
                if .90<q<1 and xx<0: col=mix(col,(255,212,170),.55)
                p[cx+xx,cy+yy]=col
    # Horizon glow. Ground is a separate repeating64x64 source at logical640.
    for y in range(89,100):
        for x in range(256):
            glow=math.exp(-((y-98)/4)**2)
            p[x,y]=mix(p[x,y],(70,155,202),glow*.75)
    for y in range(128,256):
        for x in range(256):
            u,v=x%64,y%64
            dark=((u//8)+(v//8))%2
            col=(20,16,57) if dark else (44,54,135)
            if u%8==0 or v%8==0:
                col=(43,140,178) if dark else (71,205,222)
            if u%16==0 and v%16==0: col=(236,246,214)
            if (u+3)%16==0 and (v+3)%16==0: col=mix(col,(235,75,198),.60)
            p[x,y]=col
    font=ImageFont.load_default(size=9)
    d=ImageDraw.Draw(im)
    d.text((8,6),'CATSTRIDER',font=font,fill=(221,205,206),stroke_width=0)
    d.text((196,6),'DEMO 01',font=ImageFont.load_default(size=8),fill=(170,191,205))
    d.text((8,88),'THE ORBITAL PANTRY',font=ImageFont.load_default(size=8),fill=(137,163,183))
    return im


def quantize_background(im):
    sky=im.crop((0,0,256,128)).quantize(colors=128,method=Image.Quantize.MEDIANCUT)
    ground=im.crop((0,128,256,256)).quantize(colors=64,method=Image.Quantize.MEDIANCUT)
    colors=(sky.getpalette()+[0]*384)[:384]+(ground.getpalette()+[0]*192)[:192]
    palette=[rgb5(colors[n:n+3]) for n in range(0,576,3)]
    return sky.tobytes()+bytes(v+128 for v in ground.tobytes()),palette


def cat_image(name):
    source=Image.open(ROOT/'art-source'/name).convert('RGB')
    # Hardware chroma-key conversion, not alteration of the generated artwork.
    # Generated background may have tiny codec variations; hue separation keeps
    # the complete orange/cream/green photographic subject.
    data=list(source.getdata())
    mask=[0 if r>g+65 and b>g+45 and r>160 and b>130 else 255 for r,g,b in data]
    alpha=Image.new('L',source.size); alpha.putdata(mask)
    source=source.convert('RGBA'); source.putalpha(alpha)
    source=source.crop(alpha.getbbox())
    source.thumbnail((46,62),Image.Resampling.LANCZOS)
    cat=Image.new('RGBA',(48,64)); cat.paste(source,((48-source.width)//2,(64-source.height)//2))
    return cat


def map_sprite(im,palette):
    out=Image.new('P',im.size); result=[]; cache={}
    for rgba in im.getdata():
        if rgba[3]<128:
            result.append(0); continue
        rgb=rgba[:3]
        if rgb not in cache:
            cache[rgb]=1+min(range(15),key=lambda n:sum((a-b)**2 for a,b in zip(rgb,palette[n])))
        result.append(cache[rgb])
    out.putdata(result)
    return out


def make_atlas():
    cat=cat_image('cat-front-sunglasses-key.png')
    palette_cat=cat_image('cat-key.png')
    flight=cat_image('cat-flight-key.png')
    # Keep the accepted flight palette byte-identical: the optional front edit
    # uses the existing palette and is not a new colour-quantization sample.
    # Reserve the tiny pupils and green irises so quantization does not turn
    # the photographic expression into an indistinct brown face.
    samples=[c[:3] for im in (palette_cat,flight) for c in im.getdata() if c[3]>=128 and c[0]>c[1]*1.10]
    sample=Image.new('RGB',(len(samples),1)); sample.putdata(samples)
    q=sample.quantize(colors=11,method=Image.Quantize.MEDIANCUT)
    pp=q.getpalette()[:33]
    catpal=[tuple(pp[k:k+3]) for k in range(0,33,3)]+[(16,18,22),(85,108,39),(181,188,83),(234,241,205)]
    pp=props.make_props()
    photos=photo_props.make_photo_props(ROOT/'art-source')
    palettes=[catpal,list(photos['fish']['palette']),list(photos['can']['palette']),list(props.NEON)]
    atlas=Image.new('P',(256,256))
    images={'cat':cat,'cat_flight':flight,'fish':photos['fish']['image'],'can':photos['can']['image'],
            'boss':photos['boss']['image'],'rainbow':pp['rainbow_plume']['image'],
            'laser':pp['laser']['image'],'shadow':pp['shadow']['image'],'flare':pp['flare']['image']}
    images.update({key:value['image'] for key,value in effects.make_effects().items()})
    end=Image.new('RGBA',(128,32)); d=ImageDraw.Draw(end)
    d.rounded_rectangle((0,1,127,30),radius=3,fill=(*props.NEON[0],255),outline=(*props.NEON[4],255))
    d.text((21,4),'STAY CURIOUS.',font=ImageFont.load_default(size=11),fill=(*props.NEON[6],255))
    d.text((14,18),'ONE CAT.  NO EXPLANATION.',font=ImageFont.load_default(size=8),fill=(*props.NEON[11],255))
    images['ending']=end
    for key,im in images.items():
        x,y,w,h,group=LAYOUT[key]
        assert im.size==(w,h)
        atlas.paste(map_sprite(im,palettes[group-12]),(x,y))
    full=[]
    for pal in palettes: full += [(0,0,0)]+[rgb5(c) for c in pal]
    return atlas,full,images


def attrs_for(key,x,y,w,h,tp=0,flip=False):
    ax,ay,sw,sh,ps=LAYOUT[key]
    if h<1 or w<sw//16 or x+w<0 or x>255 or y+h<0 or y>211:
        return []
    y=round(y); x=round(x); w=round(w); h=round(h)
    assert 1<=h<=256 and -512<=x<=511 and -512<=y<=511
    assert y!=216
    sz={16:0,32:1,64:2,128:3}[sh]
    columns=sw//16
    result=[]
    edges=[round(x+w*k/columns) for k in range(columns+1)]
    for k in range(columns):
        pattern=((ay//16)<<4)|(ax//16+(columns-1-k if flip else k))
        attr=struct.pack('<HBBHBB',(y&1023)|(sz<<14),h%256,ps|(tp<<6)|(0x10 if flip else 0),edges[k]&1023,edges[k+1]-edges[k],pattern)
        result.append(attr)
    return result


def floor_geometry():
    result=[]
    for line in range(112):
        scale=min(1.75,stage.CAMERA_HEIGHT/(100+line-stage.HORIZON))
        vx=round(scale*256)
        exact_start=32-vx/2
        source_start=math.ceil(exact_start)
        dx=round((source_start-exact_start)/(vx/256))
        assert 0<=dx<=4
        result.append((source_start%64,vx,dx,256-dx))
    return result


def build_motion():
    motion=bytearray(); stats=[]
    hidden=struct.pack('<HBBHBB',300,1,15,0,1,0)
    for frame in range(FRAMES):
        record=bytearray(256)
        for band,(sx,vx,dx,nx) in enumerate(floor_geometry()):
            y=100+band
            world_z=stage.FOCAL*stage.CAMERA_HEIGHT/(y-stage.HORIZON)
            sy=128+(round(world_z+stage.travel(frame))%64)
            record[band]=sy
            assert 0<=sx<=63 and 128<=sy<=191 and 16<=vx<=448
            assert sx+(((nx-1)*vx)>>8)<=511
        x,y,stride,h=stage.autopilot(frame)
        attrs=attrs_for('cat_flight',x,y,3*stride,h,flip=x+stride*1.5>128)
        assert len(attrs)==3
        record[244:248]=bytes((x,y,stride,h))
        # The accepted rear photo and left/right bank remain; no front turn.
        light=stage.laser_active(frame)
        big=stage.boss(frame)
        # Perspective projectiles retain their emission position. Increasing Z
        # pulls their head AND tail toward the vanishing/aim point and reduces
        # their projected width; these are not vertical screen-space columns.
        for trail in range(3):
            age=frame%6+trail*6
            emission=frame-age
            if not stage.laser_active(emission): continue
            ex,ey,es,eh=stage.autopilot(emission)
            origin_x=ex+es*(1.05 if ex+es*1.5>128 else 1.95)+(3 if (emission//6)%2 else -3)
            origin_y=ey+eh*.20
            aim_x=big['x']+big['w']*.5 if big else 128
            aim_y=big['y']+big['h']*.45 if big else stage.HORIZON-5
            near=20/(20+age*8)
            far=20/(20+(age+1.8)*8)
            near_x=aim_x+(origin_x-aim_x)*near
            near_y=aim_y+(origin_y-aim_y)*near
            far_x=aim_x+(origin_x-aim_x)*far
            far_y=aim_y+(origin_y-aim_y)*far
            pad=max(1,round(3*near))
            bx=round(min(near_x,far_x))-pad; by=round(min(near_y,far_y))-pad
            bw=max(2,round(abs(near_x-far_x))+pad*2)
            bh=max(3,round(abs(near_y-far_y))+pad*2)
            key='streak_left' if origin_x<aim_x else 'streak_right'
            attrs+=attrs_for(key,bx,by,bw,bh,tp=0)
        ring_phase=(frame-170)%190
        portal=120<frame<1350 and ring_phase<24
        if big:
            if frame>=1060 and frame%12<5:
                attrs+=attrs_for('flare',big['x']+big['w']//2-18,big['y']+round(big['h']*.45)-24,36,48,tp=2)
            attrs+=attrs_for('boss',big['x'],big['y'],big['w'],big['h'])
        else:
            if portal:
                rw=min(360,round(6400/(250-ring_phase*10))); rh=min(250,round(rw*.72))
                attrs+=attrs_for('ring',128-rw//2,96-round(rh*.45),rw,rh,tp=2)
            for obj in stage.world_objects(frame):
                candidate=attrs_for(obj['kind'],obj['x'],obj['y'],obj['w'],obj['h'])
                if len(attrs)+len(candidate)<=12: attrs+=candidate
        # Rainbow jet and its glow are actual translucent Sprite3 planes.
        tail_y=y+h-9
        attrs+=attrs_for('rainbow',x+stride-4,tail_y,19,90,tp=0)
        if len(attrs)<16: attrs+=attrs_for('rainbow',x+stride-12,tail_y-4,36,112,tp=3)
        # Short, rapidly expanding streaks pass the sides of the camera. They
        # use spare planes; hero/projectiles/world objects always take priority.
        for star in range(4):
            if len(attrs)>=16 or frame>=1440: break
            age=(frame+star*9)%35
            q=(age/34)**2
            right=(star+frame//140)%2==0
            cx=128+(1 if right else -1)*(18+151*q)
            sy=45+(star%2)*31+76*q
            attrs+=attrs_for('streak_right' if right else 'streak_left',round(cx),round(sy),
                             max(2,round(3+21*q)),max(4,round(5+52*q)),tp=2)
        if frame>=1440:
            ending=attrs_for('ending',64,184,128,32)
            if len(attrs)+len(ending)<=16: attrs+=ending
        active=len(attrs)
        assert active<=16,(frame,active)
        attrs += [hidden]*(16-active)
        record[112:240]=b''.join(attrs)
        record[240]=(frame//4)%32
        record[241]=(frame//5)%32
        record[242]=stage.scene(frame)
        record[243]=1 | (2 if light else 0)
        beat=frame%10
        drum=beat<2
        record[248:253]=bytes((9-frame%5,8 if beat<3 else 6,
                              (7 if frame//10%4==0 else 5) if drum else 3,
                              (23-beat*7) if drum and frame//10%4==0 else 1,
                              0x1C if drum else 0x38))
        for slot in range(16):
            assert struct.unpack_from('<H',record,112+slot*8)[0]&1023!=216
        motion.extend(record)
        stats.append({'frame':frame,'scene':record[242],'sprites':active,'hero':(x,y,stride,h),
                      'laser':light,'boss':big is not None})
    return motion,stats


def palette_phases(sprite_palette):
    result=[]
    for phase in range(32):
        # Preserve the photo cat colors; only metallic props and light pulse.
        row=list(sprite_palette)
        for i in range(16,64):
            if i%16==0: continue
            amount=(math.sin(phase*math.tau/32)*.06 if i<48 else math.sin(phase*math.tau/32)*.10)
            row[i]=tuple(max(0,min(31,round(c*(1+amount)))) for c in row[i])
        result.append(row)
    return result


def floor_palette_phases(floor_palette):
    phases=[]
    for phase in range(32):
        row=[]
        for color in floor_palette:
            r,g,b=[v/31 for v in color]
            hue,sat,value=colorsys.rgb_to_hsv(r,g,b)
            rgb=colorsys.hsv_to_rgb((hue+.16*math.sin(phase*math.tau/32))%1,sat,value)
            row.append(tuple(round(v*31) for v in rgb))
        phases.append(row)
    return phases


def generate():
    ASSETS.mkdir(exist_ok=True)
    (ROOT/'work').mkdir(exist_ok=True)
    bg,bgpal=quantize_background(sky_and_ground())
    atlas,spritepal,images=make_atlas()
    a=atlas.tobytes(); packed=bytes((a[n]<<4)|a[n+1] for n in range(0,len(a),2))
    upload=bytearray(98304)
    upload[:32768]=bg[::2]
    upload[32768:65536]=packed
    upload[65536:98304]=bg[1::2]
    motion,stats=build_motion()
    assert len(motion)==1536*256
    (ASSETS/'vram-upload.bin').write_bytes(upload)
    (ASSETS/'background-indexed.bin').write_bytes(bg)
    (ASSETS/'sprite-atlas.bin').write_bytes(packed)
    (ASSETS/'motion.bin').write_bytes(motion)
    full=bgpal+spritepal
    lines=['initial_palette:']
    for start in range(0,256,16): lines.append('    db '+','.join(str(c) for p in full[start:start+16] for c in p))
    lines.append('pulse_palettes:')
    for row in palette_phases(spritepal): lines.append('    db '+','.join(str(c) for p in row for c in p))
    lines.append('floor_palettes:')
    for row in floor_palette_phases(bgpal[128:192]): lines.append('    db '+','.join(str(c) for p in row for c in p))
    # Original brisk180BPM eight-note phrase with a small PSG rhythm section.
    def period(note): return round(1789773/(16*440*2**((note-69)/12)))
    melody=list(map(period,[64,67,71,74,71,67,76,74,64,67,69,71,69,67,62,64,
                            72,67,64,67,74,72,71,67,74,69,66,69,72,71,67,66]))
    bass=list(map(period,[40]*8+[43]*8+[36]*8+[38]*8))
    harmony=list(map(period,[71,67,76,67,71,67,74,67,74,71,79,71,74,71,76,71,
                             67,64,72,64,67,64,76,64,69,66,74,66,69,66,78,66]))
    lines.append('chords:')
    for trio in zip(melody,bass,harmony): lines.append('    dw '+','.join(map(str,trio)))
    (ASSETS/'palettes.inc').write_text('\n'.join(lines)+'\n',encoding='ascii')
    geom=['floor_geometry:']
    for sx,vx,dx,nx in floor_geometry():
        geom.append(f'    db {sx},{vx&255},{vx>>8},{dx},{nx&255}')
    (ASSETS/'floor-geometry.inc').write_text('\n'.join(geom)+'\n',encoding='ascii')
    (ASSETS/'palette-rgb5.bin').write_bytes(bytes(c for p in full for c in p))
    preview=Image.frombytes('P',(256,256),bg)
    preview.putpalette([round(c*255/31) for p in full for c in p])
    preview.crop((0,0,256,100)).resize((1024,400),Image.Resampling.NEAREST).save(ASSETS/'sky-art.png')
    atlasview=Image.new('RGB',(256,256),(8,9,21))
    for key,(x,y,w,h,ps) in LAYOUT.items():
        tile=atlas.crop((x,y,x+w,y+h)); tile.putpalette([round(c*255/31) for p in [(0,0,0)]+full[ps*16+1:ps*16+16] for c in p]+[0]*(768-48))
        mask=Image.frombytes('L',tile.size,bytes(255 if i else 0 for i in tile.tobytes()))
        atlasview.paste(tile.convert('RGB'),(x,y),mask)
    atlasview.resize((768,768),Image.Resampling.NEAREST).save(ASSETS/'sprite-atlas-art.png')
    summary={'frames':FRAMES,'target_scene_fps':30,'stage_seconds_nominal':FRAMES/30,
      'motion_bytes':len(motion),'upload_bytes':len(upload),'maximum_sprites':max(s['sprites'] for s in stats),
      'lrmm_commands_per_update':112,'lrmm_strip_height':1,
      'phases':stage.PHASES,'layout':LAYOUT,'cat_source_sha256':hashlib.sha256((ROOT/'art-source/cat-key.png').read_bytes()).hexdigest(),
      'cat_flight_source_sha256':hashlib.sha256((ROOT/'art-source/cat-flight-key.png').read_bytes()).hexdigest(),
      'cat_front_source_sha256':hashlib.sha256((ROOT/'art-source/cat-front-sunglasses-key.png').read_bytes()).hexdigest(),
      'fish_source_sha256':hashlib.sha256((ROOT/'art-source/fish-photo-key.png').read_bytes()).hexdigest(),
      'can_source_sha256':hashlib.sha256((ROOT/'art-source/can-photo-key.png').read_bytes()).hexdigest(),
      'all_sat_early_terminators_avoided':True,'all_lrmm_source_coordinates_in_window':True}
    (ASSETS/'generation-report.json').write_text(json.dumps(summary,indent=2)+'\n')
    (ROOT/'work/stage-states.json').write_text(json.dumps(stats))
    print(json.dumps(summary,indent=2))


if __name__=='__main__': generate()
