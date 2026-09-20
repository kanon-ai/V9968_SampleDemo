"""Check fixed-world light, enlarged area and six in-terrain animations."""
from pathlib import Path
import hashlib,json,math,struct
from build import PATCHES,WORLD_HEIGHT
ROOT=Path(__file__).resolve().parents[1]
A=ROOT/'assets';OUT=ROOT/'outputs'
motion=json.loads((A/'motion.json').read_text());records=(A/'motion.bin').read_bytes()
atlas=(A/'sprites.bin').read_bytes();terrain=(A/'background.bin').read_bytes()
assert len(terrain)==256*768//2 and len(atlas)==32768
assert WORLD_HEIGHT==768 and len(PATCHES)==6
def signed10(n):
 n&=1023
 return n-1024 if n>=512 else n
errors=[]
for i,m in enumerate(motion):
 a=m['angle'];z=m['zoom'];sx,sy=m['shadow_screen_offset'];wx,wy=m['shadow_world_offset']
 backx=(math.cos(a)*sx-math.sin(a)*sy)/z
 backy=(math.sin(a)*sx+math.cos(a)*sy)/z
 assert abs(backx-wx)<1e-10 and abs(backy-wy)<1e-10
 assert wx>0 and wy>0 and abs(wx/wy-.75)<1e-10
 hy,hh,_,hx,hw,_=struct.unpack_from('<HBBHBB',records,i*128+8+2*8)
 yy,h,_,xx,w,pattern=struct.unpack_from('<HBBHBB',records,i*128+8+4*8)
 actualx=signed10(xx)+w-(signed10(hx)+hw)
 actualy=signed10(yy)+h/2-(signed10(hy)+hh/2)
 errors.append(max(abs(actualx-sx),abs(actualy-sy)))
 assert errors[-1]<=1.01
 assert pattern in (132,134,136,138,140)
animation=[]
for n,(tx,ty) in enumerate(PATCHES):
 assert tx%2==0 and 0<=tx<=240 and 0<=ty<=752
 frames=[]
 for phase in range(8):
  index=phase*6+n;ax=64+(index%12)*16;ay=64+(index//12)*16
  frames.append(b''.join(atlas[(ay+y)*128+ax//2:(ay+y)*128+ax//2+8] for y in range(16)))
 unique=len(set(frames));assert unique>=4
 animation.append(dict(cat=n,unique_poses=unique,source_destination=[tx,ty]))
assert max(m['cy'] for m in motion)-min(m['cy'] for m in motion)==520
native=json.loads((OUT/'verification.json').read_text())
assert native['source_upload_and_all_8_animation_phases_exact'] and native['all_16_sampled_sprite_tables_exact']
rom=OUT/'SUPER_CAT-COASTAL_FLIGHT-V9968-legacy-openmsx-internal.rom'
report=dict(passed=True,world_area_multiplier=1.5,world_size=[256,768],
 camera_y_range=[min(m['cy'] for m in motion),max(m['cy'] for m in motion)],
 world_shadow_direction=[.6,.8],all_2048_light_vectors_verified=True,
 maximum_sprite_rounding_error_pixels=max(errors),boat_cats=animation,
 native_animation_phases_verified=8,native_sprite_tables_verified=16,
 rom_sha256=hashlib.sha256(rom.read_bytes()).hexdigest(),hardware_tested=False)
(OUT/'festival-verification.json').write_text(json.dumps(report,indent=2)+'\n')
print(json.dumps(report,indent=2))
