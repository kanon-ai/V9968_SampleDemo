; openMSX 194a769: linear SCREEN8 + SP3; requires V9968_OLD register profile.
; LUMEN -- stationary SCREEN8 scene and live transformed translucent mode-3 art.
; Target: 194a769 V9968_OLD openMSX. SCREEN8 and mode-3 SAT use linear addresses.
    org 08000h
    jp entry
FRAME equ 0E000h
entry:
    di
    xor a
    out (VDP_BASE+4),a             ; unlock V9968 extended register access
    ld e,1
    call reg_write           ; screen off
    ld a,07Fh               ; EVR, ECOM, EPAL, SP3, ILNS, SVNS, HS
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
    ; SC5 raw upload: bg even / mode3 atlas / bg odd -> physical20000-37FFF.
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
    ld a,00Eh              ; switch to SCREEN8 after physical upload
    ld e,0
    call reg_write
    call init_surfaces      ; stationary background pages and two FG4 atlases
    ld hl,0
    ld (frame_index),hl
    xor a
    ld (draw_page),a
    ; Three very quiet PSG voices, preserve joystick direction bits.
    ld a,7
    out (0A0h),a
    in a,(0A2h)
    and 0C0h
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
main_loop:
    call load_frame
    call wait_command
    ld hl,primary_source_window
    call set_source_window
    ld a,47
    ld e,17
    call reg_write
    ld hl,FRAME+4
    ld bc,4*256+VDP_BASE+3
    otir                    ; VX, VY signed 8.8
    ld a,32
    ld e,17
    call reg_write
    ld hl,FRAME
    ld bc,4*256+VDP_BASE+3
    otir                    ; source start SX, SY
    xor a
    out (VDP_BASE+3),a            ; DX low
    out (VDP_BASE+3),a            ; DX high
    ld a,(draw_page)
    rrca
    out (VDP_BASE+3),a            ; DY low:00/80 -> FG4 rows1792/1920
    ld a,7
    out (VDP_BASE+3),a            ; DY high:7 -> physical38000/3C000
    ld a,128
    out (VDP_BASE+3),a            ; NX low=128, only left half of atlas
    xor a
    out (VDP_BASE+3),a            ; NX high
    ld a,128
    out (VDP_BASE+3),a            ; NY low
    xor a
    out (VDP_BASE+3),a            ; NY high
    out (VDP_BASE+3),a            ; COLOR outside source window
    ld a,080h
    out (VDP_BASE+3),a            ; ARG FG4: 4bpp physical atlas despite SCREEN8
    ld a,030h
    out (VDP_BASE+3),a            ; LRMM IMP starts here
    ; 194a769 mode3 reads a physical contiguous SAT in linear SCREEN8.
    ; Linear CPU writes go directly to the SAT at E000h/E400h.
    ld a,(draw_page)
    add a,a
    add a,a
    add a,020h
    ld h,a
    ld l,0
    ld a,3
    call vram_write_address
    ld hl,FRAME+8
    ld bc,112*256+VDP_BASE
    call write_sat_pairs
    ld hl,sprite_end
    ld b,8
    call write_sat_pairs
    call wait_command
    ; A second independent rotation decorates the crystal with an orbiting ring.
    ; Finish both commands before exposing either half of this atlas.
    ld hl,secondary_source_window
    call set_source_window
    ld a,47
    ld e,17
    call reg_write
    ld hl,FRAME+132
    ld bc,4*256+VDP_BASE+3
    otir                    ; secondary VX, VY signed 8.8
    ld a,32
    ld e,17
    call reg_write
    ld hl,FRAME+128
    ld bc,4*256+VDP_BASE+3
    otir                    ; secondary SX, SY
    ld a,128
    out (VDP_BASE+3),a            ; DX low: right half of atlas
    xor a
    out (VDP_BASE+3),a            ; DX high
    ld a,(draw_page)
    rrca
    out (VDP_BASE+3),a            ; DY low:00/80
    ld a,7
    out (VDP_BASE+3),a            ; DY high:1792/1920
    ld a,64
    out (VDP_BASE+3),a            ; NX low
    xor a
    out (VDP_BASE+3),a            ; NX high
    ld a,64
    out (VDP_BASE+3),a            ; NY low
    xor a
    out (VDP_BASE+3),a            ; NY high
    out (VDP_BASE+3),a            ; outside source window -> transparent index0
    ld a,080h
    out (VDP_BASE+3),a            ; ARG FG4
    ld a,030h
    out (VDP_BASE+3),a            ; LRMM IMP
    call wait_command
    call fresh_vblank
    ld a,(draw_page)
    or a
    ld a,01Fh
    jr z,page0
    ld a,03Fh
page0:
    ld e,2
    call reg_write
    ld a,(draw_page)
    add a,a
    add a,a
    add a,a
    or 0C3h
    ld e,5
    call reg_write
    ld a,(draw_page)
    add a,a
    add a,a
    add a,a
    or 070h
    ld e,6
    call reg_write               ; atomically present completed Sprite3 atlas
    call animate_palette
    call animate_audio
    ld a,040h
    ld e,1
    call reg_write
    ; Consume this blank's flag so there is at most one presentation per frame.
    xor a
    ld e,15
    call reg_write
    in a,(VDP_BASE+1)
    ld a,(draw_page)
    xor 1
    ld (draw_page),a
    ld hl,(frame_index)
    inc hl
    ld a,h
    and 3
    ld h,a
    ld (frame_index),hl
    jp main_loop

; Copy the static SCREEN8 scene once, then transform only the foreground.
; FG4 uses physical 4bpp rows: 128 bytes per row, independent of SCREEN8 planes.
init_surfaces:
    call wait_command
    ld a,47
    ld e,17
    call reg_write
    ld hl,identity_vectors
    ld bc,4*256+VDP_BASE+3
    otir
    ld hl,background_page0
    call issue_initial_copy
    ld hl,background_page1
    call issue_initial_copy
    call wait_command
    ; Full-width copy includes two textures and particles at X192/208.
    ld hl,atlas_source_window
    call set_source_window
    ld hl,atlas_page0
    call issue_initial_copy
    ld hl,atlas_page1
    call issue_initial_copy
    call wait_command
    ret

; HL points to R51..58. Call only when CE is clear.
; Index0 outside each source window erases old transformed pixels to transparency.
set_source_window:
    ld a,51
    ld e,17
    call reg_write
    ld bc,8*256+VDP_BASE+3
    otir
    ret

; HL points to R32..46; wait before changing any active command registers.
issue_initial_copy:
    call wait_command
    ld a,32
    ld e,17
    call reg_write
    ld bc,15*256+VDP_BASE+3
    otir
    ret

write_sat_pairs:
    ld a,(hl)
    out (c),a
    inc hl
    djnz write_sat_pairs
    ret

; E=register, A=value; preserves BC,HL,DE.
reg_write:
    out (VDP_BASE+1),a
    ld a,e
    or 080h
    out (VDP_BASE+1),a
    ret

; A=VRAM address bits14-17, HL=low14bits. Preserves HL,BC,D.
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

wait_command:
    ld a,2
    ld e,15
    call reg_write
wait_ce:
    in a,(VDP_BASE+1)
    and 1
    jr nz,wait_ce
    ret

fresh_vblank:
    ; S0.F remembers a new blank even if rendering completed inside that blank.
    ; The old active->blank wait discarded such a usable blank and stuttered.
    xor a
    ld e,15
    call reg_write
wait_new_frame:
    in a,(VDP_BASE+1)
    and 080h
    jr z,wait_new_frame
    ld a,2
    ld e,15
    call reg_write
wait_blank:
    in a,(VDP_BASE+1)
    and 040h
    jr z,wait_blank
    ret

load_frame:
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
    ld a,(FRAME+120)
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl               ; phase*64
    ld d,h
    ld e,l
    add hl,hl
    add hl,de               ; phase*192
    ld de,pulse_palettes
    add hl,de
    ld a,192
    ld e,16
    call reg_write
    ld bc,192*256+VDP_BASE+2
    otir
    ret

animate_audio:
    ld a,(FRAME+121)
    add a,a
    ld l,a
    ld h,0
    ld d,h
    ld e,l
    add hl,hl
    add hl,de               ; chord*6
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
    ret

psg_write:
    ld a,e
    out (0A0h),a
    ld a,d
    out (0A1h),a
    ret

registers:
    db 0,06h, 2,1Fh, 5,0C3h, 6,70h, 7,0, 8,08h, 9,80h
    db 11,01h, 18,0, 19,0, 23,0, 25,0, 26,0, 27,0
    ; LRMM source window: X0..255, Y512..767.
    db 51,0, 52,0, 53,0, 54,2, 55,255, 56,0, 57,255, 58,2
registers_end:
identity_vectors:
    dw 256,0
atlas_source_window:
    db 0,0, 0,6, 255,0, 127,6
primary_source_window:
    db 0,0, 0,6, 127,0, 127,6
secondary_source_window:
    db 128,0, 0,6, 191,0, 63,6
background_page0:
    dw 0,512, 0,0, 256,212
    db 0,0,030h
background_page1:
    dw 0,512, 0,256, 256,212
    db 0,0,030h
atlas_page0:
    dw 0,1536, 0,1792, 256,128
    db 0,080h,030h
atlas_page1:
    dw 0,1536, 0,1920, 256,128
    db 0,080h,030h
sprite_end:
    db 216,0,0,0,0,0,0,0
frame_index:
    dw 0
draw_page:
    db 0
    include "assets/palettes.inc"
