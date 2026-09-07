"""Check all banked records, horizontal tree movement and invisible wrap boundaries."""
from pathlib import Path
import struct,json,hashlib
ROOT=Path(__file__).resolve().parents[1]
def signed10(x): return x-1024 if x&512 else x

def ground_mapping(record):
    """Decode actual copy descriptors into the source column seen at each X."""
    phases=[]
    for offsets,source_y,dest_y,height,command in (
            ((180,195),724,136,8,0x98),
            ((210,225),732,144,28,0xD0)):
        columns=[None]*256
        commands=0
        for offset in offsets:
            sx,sy,dx,dy,w,h,col,arg,cmd=struct.unpack_from('<6H3B',record,offset)
            assert (sy,dy,h,cmd)==(source_y,dest_y,height,command) and col==arg==0
            if w==0: continue
            assert 0<=sx<sx+w<=256 and 0<=dx<dx+w<=256
            commands+=1
            for x in range(w):
                assert columns[dx+x] is None, 'Ground descriptors overlap within a height band'
                # The atlas continues its 176px period through source X255.
                columns[dx+x]=(sx+x)%176
        assert all(x is not None for x in columns), 'Ground descriptors leave a gap in a height band'
        phase=columns[0]
        assert columns==[(x+phase)%176 for x in range(256)], 'Ground tile sequence breaks at a descriptor boundary'
        assert 1<=commands<=2
        phases.append(phase)
    assert phases[0]==phases[1], 'Transparent and opaque ground bands use different phases'
    return phases[0]

def verify():
    motion=(ROOT/'assets/motion.bin').read_bytes(); assert len(motion)==1024*256
    rom=(ROOT/'outputs/MIST_VALE-V9968-legacy-openmsx-internal.rom').read_bytes()
    ground=(ROOT/'assets/ground-indexed.bin').read_bytes(); assert len(ground)==256*36
    background=(ROOT/'assets/background-indexed.bin').read_bytes()
    assert background[212*256:248*256]==ground, 'Ground source rows differ from their atlas'
    assert all(ground[y*256+176:(y+1)*256]==ground[y*256:y*256+80]
               for y in range(36)), 'Ground padding does not repeat the first 80 source columns'
    assert all(ground[y*256+x] for y in range(8,36) for x in range(256)), \
        'Opaque HMMM ground rows contain transparent colour 0'
    tree_art=(ROOT/'assets/trees-indexed.bin').read_bytes(); assert len(tree_art)==256*96
    trees=[[] for _ in range(5)]; fog=[[] for _ in range(3)]; max_line=0
    ground_phases=[]; root_columns=[set() for _ in range(5)]
    root_contacts=0; visible_root_contacts=0
    for frame in range(1024):
        data=motion[frame*256:(frame+1)*256]
        addr=(20+frame//32)*8192+(frame&31)*256
        assert rom[addr:addr+256]==data
        ground_phase=ground_mapping(data)
        ground_phases.append(ground_phase)
        for n in range(5):
            sx,sy,dx,dy,w,h,col,arg,cmd=struct.unpack_from('<HHHHHHBBB',data,n*15)
            assert sy==768 and h==96 and cmd==0x98 and col==arg==0
            assert 48<=dy and dy+h<=168
            if w: assert 0<=dx<256 and dx+w<=256 and n*48<=sx<sx+w<=(n+1)*48
            left=dx-(sx-n*48)
            trees[n].append((left,dy,48))
            # Recover motion from descriptor positions, independently of the
            # generator's progress variable. The 352px object wrap equals two
            # terrain periods, so this remains valid for offscreen tree wraps.
            tree_phase=(288-left-n*70)%352
            assert tree_phase==frame*352//1024, 'Tree speed differs from its specified progress'
            assert ground_phase==tree_phase%176, 'Ground slides relative to a tree'
            root_source_x=(left+24+ground_phase)%176
            root_columns[n].add(root_source_x)
            # Both the trunk's bottom pixel and the soil behind/below it must
            # exist; matching coordinates alone could leave roots floating.
            root_y=dy+95
            assert tree_art[95*256+n*48+24]!=0, 'Tree trunk has no bottom contact pixel'
            assert 136<=root_y<171
            assert ground[(root_y-136)*256+root_source_x]!=0 \
                and ground[(root_y+1-136)*256+root_source_x]!=0, 'Tree root is not supported by opaque ground'
            root_contacts+=1
            visible_root_contacts+=0<=left+24<256
        lines=[0]*212
        for n in range(12):
            yy,h,attr,xx,w,pattern=struct.unpack_from('<HBBHBB',data,80+n*8)
            y=signed10(yy&1023); x=signed10(xx&1023)
            assert yy&0xc000==0x4000 and attr>>6==3 and pattern==n
            for line in range(max(0,y),min(212,y+h)): lines[line]+=1
            if n%4==0: fog[n//4].append((x,y,[224,208,192][n//4]))
        max_line=max(max_line,max(lines))
    wraps=0
    for records in trees+fog:
        for a,b in zip(records,records[1:]+records[:1]):
            if b[0]>a[0]:
                assert a[0]+a[2]<=0 and b[0]>=256, 'Visible object jumped at wrap'
                wraps+=1
    assert all(len({v[1] for v in records})==1 for records in trees), 'Trees must not move vertically'
    assert all(len(columns)==1 for columns in root_columns), 'Terrain under a tree root changes across frames'
    transition_steps=[]
    for frame in range(1024):
        following=(frame+1)%1024
        step=(ground_phases[following]-ground_phases[frame])%176
        assert step in (0,1), 'Ground jumps by more than one pixel, including at the loop boundary'
        assert all((records[frame][0]-records[following][0])%352==step for records in trees), 'Ground/tree step mismatch'
        transition_steps.append(step)
    assert max_line<=16
    raster=(ROOT/'assets/raster-offsets.bin').read_bytes(); assert len(raster)==352
    assert all(0<=v<=4 for v in raster) and all(raster[n*11+10]==0 for n in range(32))
    baseline=ROOT/'work/ground-before/assets'
    preservation={'checked':baseline.exists()}
    if baseline.exists():
        assert (ROOT/'assets/background-indexed.bin').read_bytes()[:256*212]==(baseline/'background-indexed.bin').read_bytes()[:256*212], 'Fixed background pixels changed'
        for name in ['trees-indexed.bin','fog.bin','palettes.inc']:
            assert (ROOT/'assets'/name).read_bytes()==(baseline/name).read_bytes(), name+' changed outside ground scope'
        preservation.update(fixed_background_first_212_rows_exact=True,tree_art_exact=True,fog_art_exact=True,palette_exact=True)
    report={'rom_sha256':hashlib.sha256(rom).hexdigest(),'records_checked':1024,'all_bank_offsets_exact':True,
      'tree_y_constant_for_every_record':True,'tree_vertical_positions':[r[0][1] for r in trees],
      'invisible_wraps_checked':wraps,'maximum_sprite_planes_per_line':max_line,'raster_phases_checked':32,
      'nominal_pixels_per_second_at_60_updates':{'trees':20.625,'ground':20.625,'fog_horizontal':33.75},
      'ground_sync':{'passed':True,'records_checked':1024,'loop_transitions_checked':1024,
                     'tile_period_pixels':176,'screen_columns_covered_exactly_once':256,
                     'source_Y_range':[724,759],'destination_Y_range':[136,171],
                     'height_bands_checked':2,'ground_command_descriptors_per_record':4,
                     'transparent_copy_rows':8,'opaque_copy_rows':28,
                     'opaque_copy_source_pixels_nonzero':256*28,
                     'repeated_padding_pixels_checked':80*36,
                     'phase_matches_all_five_trees':True,'root_anchor_source_columns':[next(iter(c)) for c in root_columns],
                     'root_contacts_checked':root_contacts,'visible_root_contacts_checked':visible_root_contacts,
                     'root_contact_and_below_ground_nonzero':True,
                     'loop_wrap_step_pixels':transition_steps[-1],'total_progress_pixels':sum(transition_steps)},
      'baseline_preservation':preservation}
    (ROOT/'outputs/motion-verification.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps(report,indent=2))

if __name__=='__main__': verify()
