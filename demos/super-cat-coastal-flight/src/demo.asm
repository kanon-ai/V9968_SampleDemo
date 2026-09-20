LEGACY equ 1
VDP_BASE equ 098h
; COASTAL FLIGHT -- original Supercat flight study.
; Internal legacy-openMSX V9968 profile: ports 98h-9Ch.
    org 08000h
    jp entry
FRAME equ 0E000h
entry:
    di
    xor a
    out (VDP_BASE+4),a             ; unlock V9968 extended register access
    ld e,1
    call reg_write           ; screen off
IF LEGACY
    ld a,07Fh               ; EVR, ECOM, EPAL, SP3, ILNS, SVNS, HS
ELSE
    ld a,01Fh               ; current mode5: EPAL, SP3, ILNS, SVNS, HS
ENDIF
    ld e,20
    call reg_write
IF LEGACY
    xor a
ELSE
    ld a,03Ah               ; current V58=0 + designer-specified fixed bits
ENDIF
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
    ld bc,192*256+VDP_BASE+2
    otir
    ; Background and sprite sheet: ROM banks4-15 -> VRAM20000-37FFF.
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
    ld hl,0
    ld (frame_index),hl
    xor a
    ld (draw_page),a
    ; PSG channel A, preserve joystick direction bits in mixer.
    ld a,7
    out (0A0h),a
    in a,(0A2h)
    and 0C0h
    or 03Eh
    ld d,a
    ld e,7
    call psg_write
    ld d,0
    ld e,8
    call psg_write
main_loop:
    call load_frame
    call wait_command
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
    out (VDP_BASE+3),a            ; DY low
    ld a,(draw_page)
    out (VDP_BASE+3),a            ; DY high:0 or1 -> page0/1
    xor a
    out (VDP_BASE+3),a            ; NX low
    inc a
    out (VDP_BASE+3),a            ; NX high=1 ->256
    ld a,212
    out (VDP_BASE+3),a            ; NY low
    xor a
    out (VDP_BASE+3),a            ; NY high
    out (VDP_BASE+3),a            ; COLOR outside source window
    out (VDP_BASE+3),a            ; ARG
    ld a,030h
    out (VDP_BASE+3),a            ; LRMM IMP starts here
    ; Double-buffered sprite attributes match each transformed background.
    ld a,(draw_page)
    add a,a
    ld h,a
    ld l,0
    ld a,4
    call vram_write_address
    ld hl,FRAME+8
    ld bc,80*256+VDP_BASE
    otir
    ld hl,sprite_end
    ld bc,8*256+VDP_BASE
    otir
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
    or 3
    ld e,5
    call reg_write
    ; fixed terrain palette
    ; quiet flight study
    ld a,040h
    ld e,1
    call reg_write
presented:
    ld a,(draw_page)
    xor 1
    ld (draw_page),a
    ld hl,(frame_index)
    inc hl
    ld a,h
    and 7
    ld h,a
    ld (frame_index),hl
    jp main_loop

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
    ld a,2
    ld e,15
    call reg_write
    ; A full 256x212 LRMM spans the active interval. If completion lands
    ; inside VBlank, present now instead of discarding this entire VBlank.
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
    ld b,a
    ld a,l
    rlca
    rlca
    and 3
    or b
    add a,16
    ld (06800h),a
    ld a,l
    and 03Fh
    ld l,a
    ld h,0
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    add hl,hl
    ld de,06000h
    add hl,de
    ld de,FRAME
    ld bc,128
    ldir
    ret

psg_write:
    ld a,e
    out (0A0h),a
    ld a,d
    out (0A1h),a
    ret

registers:
    db 0,06h, 2,1Fh, 5,03h, 6,60h, 7,0, 8,08h, 9,80h
    db 11,02h, 18,0, 19,0, 23,0, 25,0, 26,0, 27,0
    ; LRMM source window: X0..255, Y1024..1279.
    db 51,0, 52,0, 53,0, 54,4, 55,255, 56,0, 57,255, 58,5
registers_end:
sprite_end:
    db 216,0,0,0,0,0,0,0
frame_index:
    dw 0
draw_page:
    db 0
    include "assets/palettes.inc"
