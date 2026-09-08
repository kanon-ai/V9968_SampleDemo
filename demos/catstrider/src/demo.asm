; CATSTRIDER -- one scripted pseudo-3D flight for R800 + legacy V9968.
; SCREEN8 checker perspective uses 112 live LRMM scanlines and Sprite3 billboards.
    org 08000h
    jp entry
FRAME equ 0E000h

entry:
    di
    ; The external V9968 shares /INT with the unused native VDP.
    if VDP_BASE != 098h
    xor a
    out (099h),a
    ld a,080h
    out (099h),a
    xor a
    out (099h),a
    ld a,081h
    out (099h),a
    endif
    xor a
    out (VDP_BASE+4),a
    ld e,1
    call reg_write
    ld a,07Fh               ; legacy EVR, ECOM, EPAL, SP3, ILNS, SVNS, HS
    ld e,20
    call reg_write
    xor a
    ld e,21
    call reg_write
    ld hl,registers
    ld b,registers_end-registers
init_regs:
    ld e,(hl)
    inc hl
    ld a,(hl)
    inc hl
    call reg_write
    dec b
    djnz init_regs
    xor a
    ld e,16
    call reg_write
    ld hl,initial_palette
    ld d,3
    ld c,VDP_BASE+2
palette_upload:
    ld b,0
    otir
    dec d
    jr nz,palette_upload
    ; Upload physical20000h..37FFFh while SCREEN5 CPU addressing is linear.
    ; Data: background even plane / packed Sprite3 atlas / background odd plane.
    ld a,8
    ld hl,0
    call vram_write_address
    ld a,4
upload_bank:
    ld (06800h),a
    push af
    ld hl,06000h
    ld d,32
    ld c,VDP_BASE
upload_block:
    ld b,0
    otir
    dec d
    jr nz,upload_block
    pop af
    inc a
    cp 16
    jr nz,upload_bank
    ld a,00Eh               ; SCREEN8, no line interrupt
    ld e,0
    call reg_write
    ld hl,background_page0
    call issue_initial_copy
    ld hl,background_page1
    call issue_initial_copy
    call wait_command_init
    ; PSG voices; keep the joystick direction bits intact.
    ld a,7
    out (0A0h),a
    in a,(0A2h)
    and 0C0h
    ld (psg_mixer_io),a     ; preserve both joystick I/O direction bits
    or 038h
    ld d,a
    ld e,7
    call psg_write
    ld d,3
    ld e,8
    call psg_write
    ld d,2
    inc e
    call psg_write
    ld d,1
    inc e
    call psg_write
    call init_interrupts

; The recorded stage state, autopilot and renderer have separate entry points
; so a future interactive version can replace the scripted state producer.
main_loop:
    call load_frame
    call autopilot
    call render_floor
    call render_sprites
    call wait_command
    call fresh_vblank_pair
    di
    ld a,(draw_page)
    or a
    ld a,01Fh               ; SCREEN8 logical00000h, page0
    jr z,present_page0
    ld a,03Fh               ; SCREEN8 logical10000h, page1
present_page0:
    ld e,2
    call reg_write
present_page_written:
    ld a,(draw_page)
    add a,a
    add a,a
    add a,a
    or 0C3h
    ld e,5
    call reg_write
    ld a,060h               ; display on + vertical-blank interrupt
    ld e,1
    call reg_write
    ei
    call animate_palette
    call animate_audio
    ld a,(draw_page)
    xor 1
    ld (draw_page),a
    ld hl,(frame_index)
    inc hl
    ld a,h
    cp 6                    ; 1536 records, then repeat the complete stage
    jr c,store_frame_index
    ld hl,0
store_frame_index:
    ld (frame_index),hl
    jp main_loop

autopilot:
    ; Recorded input drives explicit hero state. Future controls can replace
    ; this producer and keep apply_hero_pose as the shared rendering entry point.
    ld a,(FRAME+242)
    ld (scene_id),a
    ld a,(FRAME+243)
    ld (hero_flags),a
    ld hl,FRAME+244
    ld de,hero_x
    ld bc,4
    ldir
    jp apply_hero_pose

apply_hero_pose:
    ; The on-screen48x64 source uses three16-pixel strips. Destination width is
    ; 3*hero_width. Keep each strip's source size, palette and pattern fields.
    ld hl,FRAME+112
    ld a,(hero_x)
    ld c,a
    ld b,3
hero_sprite_loop:
    ld a,(hero_y)
    ld (hl),a               ; Y low
    inc hl
    ld a,(hl)
    and 0FCh                ; clear Y high bits; preserve SZ/source flags
    ld (hl),a
    inc hl
    ld a,(hero_height)
    ld (hl),a               ; destination height
    inc hl                  ; palette/TP/flip flags stay intact
    inc hl
    ld (hl),c               ; X low
    inc hl
    ld a,(hl)
    and 0FCh                ; clear X high bits; preserve pattern-set flags
    ld (hl),a
    inc hl
    ld a,(hero_width)
    ld (hl),a               ; destination width of this one strip
    inc hl                  ; pattern number stays intact
    inc hl
    add a,c
    ld c,a
    djnz hero_sprite_loop
    ret

render_floor:
    ld hl,floor_geometry
    ld (floor_geometry_ptr),hl
    ld hl,FRAME
    ld a,100
    ld (floor_y),a
floor_loop:
    call wait_command
    ; The ISR does not touch R17: only the two-byte pointer write needs DI.
    di
    ld a,47
    ld e,17
    call reg_write
    ei
    push hl
    ld hl,(floor_geometry_ptr)
    ld d,(hl)               ; fixed per-line SX; reg_write and ISR preserve D
    inc hl
    ld bc,2*256+VDP_BASE+3
    otir                    ; signed8.8 VX; VY remains zero from initialization
    ld a,(hl)
    ld (floor_dx),a         ; sub-texel phase correction in destination pixels
    inc hl
    ld a,(hl)
    ld (floor_nx),a         ; (256-DX) low byte; zero means256 pixels
    inc hl
    ld (floor_geometry_ptr),hl
    pop hl
    di
    ld a,32
    ld e,17
    call reg_write
    ei
    ld a,d
    out (VDP_BASE+3),a       ; SX low: repeated texture phase0..63
    xor a
    out (VDP_BASE+3),a       ; SX high
    ld a,(hl)
    out (VDP_BASE+3),a       ; SY low:128..191 -> logicalY640..703
    inc hl
    ld a,2
    out (VDP_BASE+3),a       ; SY high
    ld a,(floor_dx)
    out (VDP_BASE+3),a       ; DX low:0..4; MSK hides the unwritten left edge
    xor a
    out (VDP_BASE+3),a       ; DX high
    ld a,(floor_y)
    out (VDP_BASE+3),a       ; DY low:100,101,...211
    ld a,(draw_page)
    out (VDP_BASE+3),a       ; DY high:0/1, always the inactive page
    ld a,(floor_nx)
    out (VDP_BASE+3),a       ; NX low
    cp 1
    ld a,0
    adc a,0                 ; NX high=1 only when the low byte is zero
    out (VDP_BASE+3),a       ; NX=256-DX, keeping the right edge at255
    ld a,1
    out (VDP_BASE+3),a       ; NY low:one independently projected scanline
    xor a
    out (VDP_BASE+3),a       ; NY high
    out (VDP_BASE+3),a       ; outside-window colour0 (valid records avoid it)
    out (VDP_BASE+3),a       ; ARG: normal SCREEN8, positive destination axes
    ld a,030h
    di                      ; keep IRQ service after the observable launch edge
    out (VDP_BASE+3),a       ; LRMM IMP
floor_command_started:
page_command_started:
    ei                      ; otherwise a VBlank ISR may finish NY1 before this hook
    ld a,(floor_y)
    inc a
    ld (floor_y),a
    cp 212
    jp nz,floor_loop
    ret

; Called only before EI. Both pages receive the same immutable sky initially.
issue_initial_copy:
    call wait_command_init
    ld a,32
    ld e,17
    call reg_write
    ld bc,15*256+VDP_BASE+3
    otir
    ret

render_sprites:
    ; d884 Sprite3 reads contiguous physical SAT bytes even in SCREEN8.
    ; Duplicate CPU writes populate both planes outside the212 visible rows.
    ld a,(draw_page)
    add a,a
    add a,a
    add a,020h
    ld h,a
    ld l,0
    ld a,3
    di
    call vram_write_address
    ei
    ld hl,FRAME+112
    ld bc,128*256+VDP_BASE
    call write_sat_pairs
    ld hl,sprite_end
    ld b,8
    call write_sat_pairs
    ret

write_sat_pairs:
    ld a,(hl)
    out (c),a
    out (c),a
    inc hl
    djnz write_sat_pairs
    ret

; E=register, A=value. Caller has DI (entry, ISR, or a short atomic section).
reg_write:
    out (VDP_BASE+1),a
    ld a,e
    or 080h
    out (VDP_BASE+1),a
    ret

; A=VRAM address bits14..17, HL=low14bits. Caller has DI.
vram_write_address:
    ld e,14
    call reg_write
    ld a,l
    out (VDP_BASE+1),a
    ld a,h
    and 03Fh
    or 040h
    out (VDP_BASE+1),a
    ret

wait_command_init:
    ld a,2
    ld e,15
    call reg_write
wait_ce_init:
    in a,(VDP_BASE+1)
    and 1
    jr nz,wait_ce_init
    ret

wait_command:
    ; S2 select/read is atomic because the ISR owns S0 acknowledgement.
    di
    ld a,2
    ld e,15
    call reg_write
    in a,(VDP_BASE+1)
    and 1
    ei
    jr nz,wait_command
    ret

fresh_vblank_pair:
    ; Target one presentation per two NTSC blanks. If rendering misses its
    ; deadline, wait for a new blank edge. An already-latched blank could be
    ; about to end and would leave too little time for the page/SAT updates.
    di
    ld hl,(vblank_counts)
    ld (wait_started_vblank),hl
    ei
wait_vblank_pair:
    di
    ld hl,(vblank_counts)
    ld de,(wait_started_vblank)
    or a
    sbc hl,de
    jr z,blank_not_ready
    ld hl,(vblank_counts)
    ld de,(presented_vblank)
    or a
    sbc hl,de
    ld a,h
    or a
    jr nz,check_blank
    ld a,l
    cp 2
    jr c,blank_not_ready
check_blank:
    ld a,2
    ld e,15
    call reg_write
    in a,(VDP_BASE+1)
    and 040h
    jr z,blank_not_ready
    ld hl,(vblank_counts)
    ld (presented_vblank),hl
    ei
    ret
blank_not_ready:
    ei
    jr wait_vblank_pair

load_frame:
    ; 1536x256 bytes in banks16..63, with32 aligned records per8KiB bank.
    ld hl,(frame_index)
    ld a,h
    add a,a
    add a,a
    add a,a
    ld b,a
    ld a,l
    rlca
    rlca
    rlca
    and 7
    or b
    add a,16
    ld (06800h),a
    ld a,l
    and 01Fh
    add a,060h
    ld h,a
    ld l,0
    ld de,FRAME
    ld bc,256
    ldir
    ret

animate_palette:
    ld a,(FRAME+240)
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    ld d,h
    ld e,l
    add hl,hl
    add hl,de               ; phase*192 bytes
    push hl                 ; share the same phase with the Sprite3 palettes
    ld de,floor_palettes
    add hl,de
    di
    ld a,128                ; floor colours128..191; sky0..127 stays untouched
    ld e,16
    call reg_write
    ei
    ld bc,192*256+VDP_BASE+2
    otir                    ; ISR never changes R16 or the palette data port
    pop hl
    ld de,pulse_palettes
    add hl,de
    di
    ld a,192
    ld e,16
    call reg_write
    ei
    ld bc,192*256+VDP_BASE+2
    otir
    ret

animate_audio:
    ld a,(FRAME+241)
    add a,a
    ld l,a
    ld h,0
    ld d,h
    ld e,l
    add hl,hl
    add hl,de               ; chord*6 bytes,32 three-voice steps
    ld de,chords
    add hl,de
    ld e,0
    ld b,6
audio_register:
    ld d,(hl)
    call psg_write
    inc hl
    inc e
    djnz audio_register
    ; Authored per-update dynamics: A melody, B bass, C tone/percussion.
    ld hl,FRAME+248
    ld e,8
    ld b,3
audio_volume:
    ld a,(hl)
    and 00Fh                ; fixed volume0..15, no unintended envelope select
    ld d,a
    call psg_write
    inc hl
    inc e
    djnz audio_volume
    ld a,(hl)               ; FRAME+251: noise period0..31
    and 01Fh
    ld d,a
    ld e,6
    call psg_write
    inc hl
    ld a,(hl)               ; FRAME+252: six tone/noise mixer switches
    and 03Fh
    ld d,a
    ld a,(psg_mixer_io)
    or d
    ld d,a
    ld e,7
    call psg_write
    ret

psg_write:
    ld a,e
    out (0A0h),a
    ld a,d
    out (0A1h),a
    ret

init_interrupts:
    ; Any interrupt bus vector maps through the repeated-byte table to E9E9h.
    ld hl,0E800h
    ld (hl),0E9h
    ld de,0E801h
    ld bc,256
    ldir
    ld a,0C3h
    ld (0E9E9h),a
    ld hl,irq_handler
    ld (0E9EAh),hl
    ld a,0E8h
    ld i,a
    im 2
    xor a
    ld e,15
    call reg_write
    in a,(VDP_BASE+1)
    ld a,2
    ld e,15
    call reg_write
    ld a,020h               ; IE0 enabled, screen off until first presentation
    ld e,1
    call reg_write
    ei
    ret

irq_handler:
    push af
    push bc
    push de
    push hl
    ld hl,(irq_counts)
    inc hl
    ld (irq_counts),hl
    xor a
    ld e,15
    call reg_write
    in a,(VDP_BASE+1)
    and 080h
    jr z,irq_done
    ld hl,(vblank_counts)
    inc hl
    ld (vblank_counts),hl
irq_done:
    ld a,2
    ld e,15
    call reg_write
    pop hl
    pop de
    pop bc
    pop af
    ei
    reti

registers:
    db 0,06h, 2,1Fh, 5,0C3h, 6,50h, 7,0, 8,08h, 9,80h
    db 11,01h, 18,0, 19,0, 23,0, 25,02h, 26,0, 27,0
    ; R25 MSK hides leftmost8 pixels, including the0..4-pixel LRMM phase gap.
    db 47,0, 48,1, 49,0, 50,0
    ; Window clipping precedes physical X wrapping. Allow X0..511 so a
    ; 256-pixel-wide source can repeat once; Y remains in the floor texture.
    db 51,0, 52,0, 53,128, 54,2, 55,255, 56,1, 57,255, 58,2
registers_end:
background_page0:
    dw 0,512, 0,0, 256,212
    db 0,0,0D0h
background_page1:
    dw 0,512, 0,256, 256,212
    db 0,0,0D0h
sprite_end:
    db 216,0,0,0,0,0,0,0
frame_index:
    dw 0
draw_page:
    db 0
floor_y:
    db 100
floor_geometry_ptr:
    dw 0
floor_dx:
    db 0
floor_nx:
    db 0
scene_id:
    db 0
hero_flags:
    db 0
hero_x:
    db 0
hero_y:
    db 0
hero_width:
    db 16                   ; width of one strip; complete hero is3 times this
hero_height:
    db 64
psg_mixer_io:
    db 0                    ; R7 bits6..7 captured once before music starts
irq_counts:
    dw 0
vblank_counts:
    dw 0
presented_vblank:
    dw 0
wait_started_vblank:
    dw 0
    include "assets/palettes.inc"
    include "assets/floor-geometry.inc"
