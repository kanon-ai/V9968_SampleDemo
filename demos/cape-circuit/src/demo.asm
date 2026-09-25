; CAPE CIRCUIT: R800 + current V9968. Native projective LRMM floor.
VDP_BASE equ 098h
FRAME equ 0E000h
 org 08000h
 jp entry
entry:
 di
 xor a
 out (VDP_BASE+4),a
 ld e,1
 call reg_write
 ld a,01Fh
 ld e,20
 call reg_write
 ld a,03Ah
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
 cp 20
 jr nz,upload_bank
 ld hl,copy0
 call copy_sky
 ld hl,copy1
 call copy_sky
 call wait_command
 ld hl,0
 ld (frame_index),hl
 xor a
 ld (draw_page),a
 ; Quiet three-voice PSG arpeggio, joystick direction bits preserved.
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
 ld d,0
 ld e,9
 call psg_write
main_loop:
 call load_frame
 call render_sky
 ld hl,FRAME
 ld a,92
 ld (line_y),a
line_loop:
 call wait_command
 push hl
 ld de,4
 add hl,de
 ld a,47
 ld e,17
 call reg_write
 ld bc,4*256+VDP_BASE+3
 otir
 pop hl
 ld a,32
 ld e,17
 call reg_write
 ld bc,4*256+VDP_BASE+3
 otir
 inc hl
 inc hl
 inc hl
 inc hl
 xor a
 out (VDP_BASE+3),a
 out (VDP_BASE+3),a
 ld a,(line_y)
 out (VDP_BASE+3),a
 ld a,(draw_page)
 out (VDP_BASE+3),a
 xor a
 out (VDP_BASE+3),a
 inc a
 out (VDP_BASE+3),a
 out (VDP_BASE+3),a
 xor a
 out (VDP_BASE+3),a
 out (VDP_BASE+3),a
 out (VDP_BASE+3),a
 ld a,030h
 out (VDP_BASE+3),a
 ld a,(line_y)
 inc a
 ld (line_y),a
 cp 212
 jr nz,line_loop
 call wait_command
 ld a,(draw_page)
 add a,a
 ld h,a
 ld l,0
 ld a,4
 call vram_write_address
 ld hl,FRAME+960
 ld bc,56*256+VDP_BASE
 otir
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
presented:
 ld a,040h
 ld e,1
 call reg_write
 call audio
 ld a,(draw_page)
 xor 1
 ld (draw_page),a
 ld hl,(frame_index)
 inc hl
 ld a,h
 cp 1
 jr c,store_frame
 ld a,l
 cp 64
 jr c,store_frame
 ld hl,0
store_frame:
 ld (frame_index),hl
 jp main_loop
render_sky:
 ; Two bounded HMMM strips implement a panoramic wrap, preserving the HUD.
 call wait_command
 ld a,(FRAME+1016)
 ld (sky_command),a
 ld b,a
 neg
 ld (sky_command+8),a
 ld a,0
 jr nz,sky_width_ready
 inc a
sky_width_ready:
 ld (sky_command+9),a
 ld a,(draw_page)
 ld (sky_command+7),a
 xor a
 ld (sky_command+4),a
 ld hl,sky_command
 call copy_sky
 ld a,(FRAME+1016)
 or a
 ret z
 ld (sky_command+8),a
 neg
 ld (sky_command+4),a
 xor a
 ld (sky_command),a
 ld (sky_command+9),a
 ld hl,sky_command
 jp copy_sky
sky_command:
 dw 0,1810,0,18,256,74
 db 0,0,0D0h
copy_sky:
 call wait_command
 ld a,32
 ld e,17
 call reg_write
 ld bc,15*256+VDP_BASE+3
 otir
 ret
load_frame:
 ; Eight 1KiB records per ASCII8 bank, starting at bank20.
 ld hl,(frame_index)
 ld a,l
 and 7
 add a,a
 add a,a
 add a,060h
 ld d,a
 ld e,0
 srl h
 rr l
 srl h
 rr l
 srl h
 rr l
 ld a,l
 add a,20
 ld (06800h),a
 ex de,hl
 ld de,FRAME
 ld bc,1024
 ldir
 ret
psg_write:
 ld a,e
 out (0A0h),a
 ld a,d
 out (0A1h),a
 ret
audio:
 ld a,(frame_index)
 rrca
 rrca
 rrca
 and 7
 add a,a
 ld l,a
 ld h,0
 ld de,notes
 add hl,de
 ld d,(hl)
 ld e,0
 call psg_write
 inc hl
 ld d,(hl)
 inc e
 call psg_write
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
    ld a,2
    ld e,15
    call reg_write
wait_active:
    in a,(VDP_BASE+1)
    and 040h
    jr nz,wait_active
wait_blank:
    in a,(VDP_BASE+1)
    and 040h
    jr z,wait_blank
    ret

registers:
 db 0,06h,2,1Fh,5,03h,6,60h,7,0,8,08h,9,80h
 db 11,02h,18,0,19,0,23,0,25,0,26,0,27,0
 db 51,0,52,0,53,0,54,4,55,255,56,0,57,255,58,5
registers_end:
copy0:
 dw 0,1792,0,0,256,92
 db 0,0,0D0h
copy1:
 dw 0,1792,0,256,256,92
 db 0,0,0D0h
frame_index: dw 0
draw_page: db 0
line_y: db 0
notes: dw 428,339,285,214,320,254,214,160
 include "assets/palette.inc"
