"""Check every banked record and the full loop's scanline load."""
from pathlib import Path
import struct,json,hashlib
ROOT=Path(__file__).resolve().parents[1]

def verify():
    motion=(ROOT/'assets/motion.bin').read_bytes()
    rom=(ROOT/'outputs/LUMEN_FORGE-V9968-legacy-openmsx-internal.rom').read_bytes()
    assert len(motion)==1024*256
    counts=[]; sizes=[]
    for n in range(1024):
        address=(16+n//32)*8192+(n&31)*256
        assert rom[address:address+256]==motion[n*256:(n+1)*256]
        attrs=motion[n*256+8:n*256+120]; lines=[0]*212
        for i in range(14):
            a=attrs[i*8:i*8+8]; y=a[0]|((a[1]&3)<<8)
            y=y-1024 if y&512 else y
            for yy in range(max(0,y),min(212,y+(a[2] or 256))): lines[yy]+=1
        counts.append(max(lines)); sizes.append(attrs[6*8+2])
    assert max(counts)<=16
    for start in [0,128]:
        records=[struct.unpack_from('<hhhh',motion,n*256+start) for n in range(1024)]
        delta=[max(abs(a-b) for a,b in zip(records[n],records[(n+1)%1024])) for n in range(1024)]
        assert delta[-1]<=max(delta[:-1])
    report={'motion_records':1024,'record_bytes':256,'all_ascii8_offsets_checked':True,
      'max_sprite_planes_per_line':max(counts),'main_destination_size_pixels':[min(sizes),max(sizes)],
      'loop_boundary_no_larger_jump':True,'rom_sha256':hashlib.sha256(rom).hexdigest()}
    (ROOT/'outputs/motion-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__': verify()
