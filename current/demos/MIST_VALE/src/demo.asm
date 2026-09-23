VDP_BASE equ 152
; Current V9968: linear SCREEN8 + SP3, R20=1Fh, R21=3Ah.
; MIST -- horizontal forest motion, translucent Sprite3 fog, and water raster.
; Target: current V9968, SCREEN8 / EPAL / Sprite3, R800 DRAM.
    org 08000h
    jp entry
FRAME equ 0E000h

entry:
    di
    ; An external V9968 shares the CPU interrupt line with the internal VDP.
    ; Its unused native display must not leave an unacknowledged interrupt.
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
    ld a,01Fh               ; current EPAL, SP3, ILNS, SVNS, HS
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
    ld d,3
    ld c,VDP_BASE+2
palette_upload:
    ld b,0
    otir
    dec d
    jr nz,palette_upload
    ; SCREEN5 CPU writes are physical: upload 128 KiB at 20000h..3FFFFh.
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
    ld a,00Eh
    ld e,0
    call reg_write
    ld hl,background_page0
    call issue_initial_copy
    ld hl,background_page1
    call issue_initial_copy
    call wait_command_init
    ; PSG: the quiet three-voice progression preserves joystick direction bits.
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
    call init_interrupts

main_loop:
    call load_frame
    ld hl,restore_forest_band
    call issue_page_command
    ; Four terrain segments share the trees' horizontal world phase.
    ; Draw the bank first so tree roots sit over its completed pixels.
    ld hl,FRAME+180
    call issue_optional_page_command
    call issue_optional_page_command
    call issue_optional_page_command
    call issue_optional_page_command
    ld hl,FRAME
    ld a,5
    ld (commands_remaining),a
tree_loop:
    call issue_optional_page_command
next_tree:
    ld a,(commands_remaining)
    dec a
    ld (commands_remaining),a
    jr nz,tree_loop
    ; Populate only the inactive physical SAT. The ISR never changes R14 or
    ; the VRAM address, so the data-byte stream can remain interruptible.
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
    ld hl,FRAME+80
    ld bc,96*256+VDP_BASE
    call write_sat_pairs
    ld hl,sprite_end
    ld b,8
    call write_sat_pairs
    call wait_command
    call fresh_vblank
    ; Page/SAT changes are short atomic control-port transactions in blank.
    di
    ld a,(draw_page)
    or a
    ld a,01Fh               ; SCREEN8 page0: R2 bit5 selects logical64KiB page
    jr z,present_page0
    ld a,03Fh               ; SCREEN8 page1; 3Fh/7Fh would both display page1
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
    ld a,(FRAME+178)
    ld (raster_phase),a
    call set_raster_pointer
    ld a,060h               ; display on, vertical-blank interrupt enabled
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
    and 3
    ld h,a
    ld (frame_index),hl
    jp main_loop

; A fully clipped tree or terrain segment has NX=0. Skip its descriptor,
; because sending NX=0 to the VDP would instead request a full-width copy.
; Both branches advance HL by exactly15 bytes to the next descriptor.
issue_optional_page_command:
    push hl
    ld de,8
    add hl,de
    ld a,(hl)
    inc hl
    or (hl)
    pop hl
    jp nz,issue_page_command
skip_tree:
    ld de,15
    add hl,de
    ret

; HL points to 15 bytes for R32..46. DY is page-relative in the ROM record;
; only its high byte is adjusted here, leaving FRAME available for verification.
; The ISR touches no R17, so the indirect command stream may be interrupted.
issue_page_command:
    call wait_command
    di
    ld a,32
    ld e,17
    call reg_write
    ei
    ld bc,7*256+VDP_BASE+3
    otir
    ld a,(draw_page)
    add a,(hl)
    out (VDP_BASE+3),a
    inc hl
    ld bc,7*256+VDP_BASE+3
    otir
page_command_started:
    ret

; Used only before EI; initial display copies do not adjust the destination.
issue_initial_copy:
    call wait_command_init
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

; E=register, A=value. Caller must have DI (entry, ISR, or an atomic section).
; The two control bytes must never be separated by an ISR status-register read.
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
    ; Select/read S2 atomically; the ISR also selects S0/S1 to acknowledge IRQs.
    di
    ld a,2
    ld e,15
    call reg_write
    in a,(VDP_BASE+1)
    and 1
    ei
    jr nz,wait_command
    ret

fresh_vblank:
    ; S0 is owned by the ISR. A new counter plus S2.VR prevents presentation
    ; during active display, without throwing away a still-usable blank.
    di
    ld hl,(vblank_counts)
    ld de,(presented_vblank)
    or a
    sbc hl,de
    jr z,blank_not_ready
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
    jr fresh_vblank

load_frame:
    ; 1024 records x256 bytes. Banks20..51, 32 records in each 8 KiB bank.
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
    add a,20
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
    ld a,(FRAME+176)
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
    add hl,de
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
    ld a,(FRAME+177)
    add a,a
    ld l,a
    ld h,0
    ld d,h
    ld e,l
    add hl,hl
    add hl,de
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

init_interrupts:
    ; A repeated-byte IM2 table accepts any interrupt bus vector, including FF.
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
    call set_raster_pointer
    ld a,1
    ld e,15
    call reg_write
    in a,(VDP_BASE+1)
    xor a
    ld e,15
    call reg_write
    in a,(VDP_BASE+1)
    ld a,2
    ld e,15
    call reg_write
    ld a,01Eh               ; SCREEN8 and IE1 line interrupts
    ld e,0
    call reg_write
    ld a,020h               ; IE0 enabled; screen stays off until first frame
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
    ld a,1
    ld e,15
    call reg_write
    in a,(VDP_BASE+1)
    and 1
    call nz,irq_raster
    ; Also acknowledge F if both sources became pending together.
    xor a
    ld e,15
    call reg_write
    in a,(VDP_BASE+1)
    and 080h
    call nz,irq_vblank
    ld a,2
    ld e,15
    call reg_write
    pop hl
    pop de
    pop bc
    pop af
    ei
    reti

irq_raster:
    ld hl,(raster_counts)
    inc hl
    ld (raster_counts),hl
    ld hl,(raster_pointer)
    ld a,(hl)
    inc hl
    ld (raster_pointer),hl
    ld e,27
raster_scroll_write:
    call reg_write
raster_scroll_written:
    ld a,(raster_index)
    inc a
    ld (raster_index),a
    cp 11
    jr nc,raster_finished
    add a,a
    add a,a
    add a,171
    jr raster_schedule
raster_finished:
    ld a,255                ; blank at212 re-arms171 before this can fire
raster_schedule:
    ld e,19
    call reg_write
    ret

irq_vblank:
    ld hl,(vblank_counts)
    inc hl
    ld (vblank_counts),hl
    xor a
    ld (raster_index),a
    ld e,27
irq_blank_scroll_reset:
    call reg_write
irq_blank_scroll_written:
    call set_raster_pointer
    ld a,171
    ld e,19
    call reg_write
    ret

set_raster_pointer:
    ld a,(raster_phase)
    ld l,a
    ld h,0
    ld d,h
    ld e,l
    add hl,hl               ; phase*2
    add hl,de               ; phase*3
    add hl,hl               ; phase*6
    add hl,hl               ; phase*12
    or a
    sbc hl,de               ; phase*11
    ld de,raster_offsets
    add hl,de
    ld (raster_pointer),hl
    ret

registers:
    db 0,06h, 2,1Fh, 5,0C3h, 6,78h, 7,0, 8,08h, 9,80h
    db 11,01h, 18,0, 19,171, 23,0, 25,02h, 26,0, 27,0
registers_end:
background_page0:
    dw 0,512, 0,0, 256,212
    db 0,0,0D0h
background_page1:
    dw 0,512, 0,256, 256,212
    db 0,0,0D0h
restore_forest_band:
    ; Restore only the band not fully replaced by the opaque ground below.
    dw 0,560, 0,48, 256,96
    db 0,0,0D0h
sprite_end:
    db 216,0,0,0,0,0,0,0
frame_index:
    dw 0
draw_page:
    db 0
commands_remaining:
    db 0
irq_counts:
    dw 0
vblank_counts:
    dw 0
raster_counts:
    dw 0
presented_vblank:
    dw 0
raster_phase:
    db 0
raster_index:
    db 0
raster_pointer:
    dw 0
    include "assets/palettes.inc"
