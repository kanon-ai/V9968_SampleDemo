; V9968 VRAM read stability diagnostic. All timing kernels execute in RAM.
; No interrupt or display writes occur within a captured 256-byte read.
 include "src/graphics.inc"
 org 08000h
main:
 di
 ld sp,0f300h
 ld a,(002dh)
 cp 3
 ld a,0
 jr c,not_turbo
 inc a
not_turbo:
 ld (turbo),a
 call slow_cpu
 xor a
 out (VDP+4),a
 ld e,21
 call regwrite
 xor a
 ld e,20
 call regwrite
 ld a,1
 ld e,15
 call regwrite
 in a,(VDP+1)
 and 03eh
 ld (vdp_id),a
 cp 6
 jp nz,no_vdp
 call init_screen
 ld a,0ffh
 ld (oldkeys),a
restart:
 xor a
 ld hl,stats_begin
 ld de,stats_begin+1
 ld bc,stats_end-stats_begin-1
 ld (hl),a
 ldir
 ld a,1
 ld (phase),a
 call draw
 ; Write the whole region before verification: address aliases remain visible.
 ld a,1
 ld (bank),a
fill_bank:
 xor a
 ld (chunk),a
fill_chunk:
 call expected
 call set_write
 ld hl,expect
 ld b,0
fill_byte:
 ld a,(hl)
 out (VDP),a
 call gap_slow
 inc hl
 djnz fill_byte
 ld a,(chunk)
 inc a
 ld (chunk),a
 cp 64
 jr nz,fill_chunk
 ld a,(bank)
 inc a
 ld (bank),a
 cp 16
 jr nz,fill_bank
 ld a,2
 ld (phase),a
 ld a,1
 ld (bank),a
bank_loop:
 call draw
 call keys
 jp c,restart
 xor a
 ld (chunk),a
chunk_loop:
 call expected
 call slow_cpu
 call set_read
 call read_slow
 xor a
 ld (test_kind),a
 call compare
 call chosen_cpu
 ld a,4
 ld (repeat_count),a
repeat_read:
 call set_read
 ld a,(gap)
 or a
 jr z,use_fast
 dec a
 jr z,use_medium
 call read_spaced
 jr captured
use_medium:
 call read_medium
 jr captured
use_fast:
 call read_fast
captured:
 ld a,1
 ld (test_kind),a
 call compare
 ld a,(repeat_count)
 dec a
 ld (repeat_count),a
 jr nz,repeat_read
 call slow_cpu
 ld a,(chunk)
 inc a
 ld (chunk),a
 cp 64
 jr nz,chunk_loop
 ld a,(bank)
 inc a
 ld (bank),a
 cp 16
 jp nz,bank_loop
 ld hl,passes
 call saturate
 ld a,3
 ld (phase),a
finished:
 call draw
result_ready:
 call keys
 jp c,restart
 ld a,(continuous)
 or a
 jr z,result_ready
 ld hl,(errors)
 ld de,(baseline_errors)
 ld a,h
 or l
 or d
 or e
 jr nz,result_ready
 ld a,2
 ld (phase),a
 ld a,1
 ld (bank),a
 jp bank_loop
no_vdp:
 ; Report on host BIOS display, without writing V9968 memory.
 ld hl,missing
missing_loop:
 ld a,(hl)
 or a
 jr z,halted
 push hl
 call 00a2h
 pop hl
 inc hl
 jr missing_loop
halted:
 jr halted
regwrite:
 out (VDP+1),a
 ld a,e
 or 080h
 out (VDP+1),a
 ret
slow_cpu:
 ld a,(turbo)
 or a
 ret z
 ld a,080h
 call 0180h
 di
 ret
chosen_cpu:
 ld a,(turbo)
 or a
 ret z
 ld a,(cpu)
 or 080h
 call 0180h
 di
 ret
; R14 bank (A17..14) and chunk (A13..8). Explicit address each block.
set_read:
 xor a
 jr set_address
set_write:
 ld a,040h
set_address:
 ld d,a
 ld a,(bank)
 ld e,14
 call regwrite
 xor a
 out (VDP+1),a
 ld a,(chunk)
 or d
 out (VDP+1),a
 ; Conservative first-byte setup delay, intentionally not the measured variable.
 call gap_slow
 ret
gap_slow:
 push bc
 ld b,16
gap_loop:
 nop
 djnz gap_loop
 pop bc
 ret
read_slow:
 ld hl,actual
 ld b,0
rs_loop:
 in a,(VDP)
 ld (hl),a
 inc hl
 call gap_slow
 djnz rs_loop
 ret
read_fast:
 ld hl,actual
 ld bc,VDP
 ; 256 unrolled INIs are generated below.
 include "src/fast.inc"
 ret
read_medium:
 ld hl,actual
 ld bc,VDP
 include "src/medium.inc"
 ret
read_spaced:
 ld hl,actual
 ld bc,VDP
 include "src/spaced.inc"
 ret
; Patterns 0=00,1=FF,2=AA/55,3=address XOR,4..11=walking 1.
expected:
 ld hl,expect
 ld b,0
 ld c,0
expected_loop:
 ld a,(pattern)
 or a
 jr z,store_expected
 cp 1
 jr nz,not_ff
 ld a,255
 jr store_expected
not_ff:
 cp 2
 jr nz,not_checker
 ld a,c
 and 1
 ld a,0aah
 jr z,store_expected
 cpl
 jr store_expected
not_checker:
 cp 3
 jr nz,walking
 ld a,(bank)
 rlca
 rlca
 xor c
 ld d,a
 ld a,(chunk)
 xor d
 jr store_expected
walking:
 sub 4
 ld e,a
 ld a,1
walk_loop:
 dec e
 jp m,store_expected
 rlca
 jr walk_loop
store_expected:
 ld (hl),a
 inc hl
 inc c
 djnz expected_loop
 ret
compare:
 ld hl,expect
 ld de,actual
 ld b,0
 ld c,0
compare_loop:
 ld a,(de)
 xor (hl)
 jp z,compare_next
 push bc
 push de
 push hl
 ld (err_xor),a
 ld a,(test_kind)
 or a
 jr nz,test_error
 ld hl,baseline_errors
 call saturate
 jr compare_restore
test_error:
 ld hl,errors
 call saturate
 ld a,(first_valid)
 or a
 jr nz,record_bits
 inc a
 ld (first_valid),a
 ld a,(bank)
 ld (first_bank),a
 ld a,(chunk)
 ld (first_chunk),a
 ld a,c
 ld (first_offset),a
 pop hl
 push hl
 ld a,(hl)
 ld (first_expected),a
 ld a,(de)
 ld (first_actual),a
 ld a,(err_xor)
 ld (first_xor),a
 push bc
 push de
 push hl
 call retry_first
 pop hl
 pop de
 pop bc
record_bits:
 ; Direction-specific counters for every mismatching bit.
 ld a,(de)
 ld (err_actual),a
 ld hl,bits_up
 ld b,8
bits_loop:
 ld a,(err_xor)
 rrca
 ld (err_xor),a
 jr nc,no_bit
 ld a,(err_actual)
 and 1
 jr nz,bit_up
 push hl
 ld de,16
 add hl,de
 call saturate
 pop hl
 jr no_bit
bit_up:
 call saturate
no_bit:
 ld a,(err_actual)
 rrca
 ld (err_actual),a
 inc hl
 inc hl
 djnz bits_loop
compare_restore:
 pop hl
 pop de
 pop bc
compare_next:
 inc hl
 inc de
 inc c
 dec b
 jp nz,compare_loop
 ld hl,blocks
 call saturate
 ret
retry_first:
 ld a,(bank)
 ld e,14
 call regwrite
 ld a,(first_offset)
 out (VDP+1),a
 ld a,(chunk)
 out (VDP+1),a
 call gap_slow
 in a,(VDP)
 ld (first_retry),a
 ret
saturate:
 inc (hl)
 ret nz
 inc hl
 inc (hl)
 dec hl
 ret nz
 ld (hl),255
 inc hl
 ld (hl),255
 dec hl
 ret
init_screen:
 ld hl,registers
 ld e,0
init_regs:
 ld a,(hl)
 push hl
 call regwrite
 pop hl
 inc hl
 inc e
 ld a,e
 cp 24
 jr nz,init_regs
 ; Own ASCII font, no BIOS assets in ROM.
 ld a,0
 ld e,14
 call regwrite
 xor a
 out (VDP+1),a
 ld a,048h
 out (VDP+1),a
 ld hl,font
 ld de,2048
font_loop:
 ld a,(hl)
 out (VDP),a
 call gap_slow
 inc hl
 dec de
 ld a,d
 or e
 jr nz,font_loop
 ; UI background color: palette 4 = dark navy, standard 3-bit RGB.
 ld a,4
 ld e,16
 call regwrite
 ld a,002h
 out (VDP+2),a
 ld a,001h
 out (VDP+2),a
 ret
; Screen 0 text. No sprites. VRAM 00000..03FFF reserved, 04000..3FFFF tested.
registers:
 db 0,050h,0,0,1,0,0,0f1h,8,0,0,0,0,0,0,0,0,0,0,0,0,0,0,0
keys:
 ld a,0
 call 0141h
 di
 ld c,a
 ld a,(oldkeys)
 xor c
 and c
 ; Act on key RELEASE (stable edge), row0 digits 0..7.
 ld b,a
 ld a,c
 ld (oldkeys),a
 bit 0,b
 jr z,key1
 ld a,(continuous)
 xor 1
 ld (continuous),a
 scf
 ret
key1:
 bit 1,b
 jr z,key2
 xor a
 ld (cpu),a
 scf
 ret
key2:
 bit 2,b
 jr z,key3
 ld a,(turbo)
 or a
 ret z
 ld a,1
 ld (cpu),a
 scf
 ret
key3:
 bit 3,b
 jr z,key4
 ld a,(turbo)
 or a
 ret z
 ld a,2
 ld (cpu),a
 scf
 ret
key4:
 bit 4,b
 jr z,key5
 ld a,(gap)
 inc a
 cp 3
 jr c,gap_ok
 xor a
gap_ok:
 ld (gap),a
 scf
 ret
key5:
 bit 5,b
 jr z,key6
 ld a,(display_on)
 xor 1
 ld (display_on),a
 scf
 ret
key6:
 bit 6,b
 jr z,key7
 ld a,(pattern)
 inc a
 cp 12
 jr c,pat_ok
 xor a
pat_ok:
 ld (pattern),a
 scf
 ret
key7:
 bit 7,b
 jr z,no_key
 scf
 ret
no_key:
 or a
 ret
; Render a fixed 40x24 screen buffer, then write it with slow Z80 I/O.
draw:
 call slow_cpu
 ld hl,screen
 ld de,screen+1
 ld bc,959
 ld (hl),32
 ldir
 ld hl,memtitle
 ld de,screen
 call puts
 ld hl,labels
 ld de,screen+320
 call puts
 ld a,(cpu)
 add a,48
 ld (screen+326),a
 ld a,(gap)
 add a,48
 ld (screen+333),a
 ld a,(pattern)
 ld de,screen+343
 call hex8
 ld a,(phase)
 add a,48
 ld (screen+352),a
 ld hl,lab_counts
 ld de,screen+360
 call puts
 ld hl,(baseline_errors)
 ld de,screen+368
 call hex16
 ld hl,(errors)
 ld de,screen+381
 call hex16
 ld hl,(blocks)
 ld de,screen+393
 call hex16
 ld hl,lab_first
 ld de,screen+400
 call puts
 ld a,(first_bank)
 ; Address formatted as 5 hex digits, not bank:offset.
 ld c,a
 srl a
 srl a
 ld de,screen+406
 call nibble
 ld a,c
 and 3
 rrca
 rrca
 ld c,a
 ld a,(first_chunk)
 or c
 call hex8
 ld a,(first_offset)
 call hex8
 ld a,(first_expected)
 ld de,screen+415
 call hex8
 ld a,(first_actual)
 ld de,screen+424
 call hex8
 ld a,(first_xor)
 ld de,screen+432
 call hex8
 ld hl,lab_retry
 ld de,screen+440
 call puts
 ld a,(first_retry)
 ld de,screen+446
 call hex8
 ld hl,(passes)
 ld de,screen+456
 call hex16
 ld a,(continuous)
 add a,48
 ld (screen+466),a
 ld hl,lab_bits
 ld de,screen+480
 call puts
 ld hl,bits_up
 ld de,screen+520
 ld b,8
up_loop:
 push bc
 push hl
 ld c,(hl)
 inc hl
 ld h,(hl)
 ld l,c
 call hex16
 inc de
 pop hl
 inc hl
 inc hl
 pop bc
 djnz up_loop
 ld hl,bits_down
 ld de,screen+600
 ld b,8
down_loop:
 push bc
 push hl
 ld c,(hl)
 inc hl
 ld h,(hl)
 ld l,c
 call hex16
 inc de
 pop hl
 inc hl
 inc hl
 pop bc
 djnz down_loop
 ld hl,lab_down
 ld de,screen+560
 call puts
 ld hl,help
 ld de,screen+720
 call puts
 ld a,(display_on)
 add a,48
 ld (screen+848),a
 call dashboard
 ld hl,footer
 ld de,screen+880
 call puts
 xor a
 ld e,14
 call regwrite
 xor a
 out (VDP+1),a
 ld a,040h
 out (VDP+1),a
 ld hl,screen
 ld de,960
screen_loop:
 ld a,(hl)
 out (VDP),a
 call gap_slow
 inc hl
 dec de
 ld a,d
 or e
 jr nz,screen_loop
 ld a,050h
 ld e,1
 call regwrite
 ; During read testing only, optionally disable display fetches.
 ld a,(phase)
 cp 2
 ret nz
 ld a,(display_on)
 or a
 ret nz
 ld a,010h
 ld e,1
 call regwrite
 ret
dashboard:
 ; Stable white-on-navy palette, including failures. No timing-kernel changes.
 ld a,0f4h
 ld e,7
 call regwrite
 ld hl,status_fill
 ld a,(phase)
 cp 1
 jr z,status_selected
 ld hl,status_read
 cp 2
 jr z,status_selected
 ld hl,status_good
status_selected:
 ld de,(errors)
 ld a,d
 or e
 jr nz,status_bad
 ld de,(baseline_errors)
 ld a,d
 or e
 jr z,status_ready
status_bad:
 ld hl,status_error
status_ready:
 ld de,screen+280
 call puts
 ; Fifteen 16 KiB banks. Each box represents a bank, not a timing sample.
 ld ix,screen+40
 ld c,1
 ld b,3
map_row:
 push bc
 ld b,5
map_cell:
 push bc
 push ix
 pop de
 ld a,c
 call hex8
 ld hl,bank_suffix
 call puts
 ld a,tile_empty
 ld d,a
 ld a,(phase)
 cp 1
 jr z,map_symbol
 ld a,(bank)
 cp c
 jr z,map_symbol
 jr c,map_symbol
 ld d,tile_full
map_symbol:
 ld a,(first_valid)
 or a
 jr z,map_not_first
 ld a,(first_bank)
 cp c
 jr nz,map_not_first
 ld d,'X'
map_not_first:
 push ix
 pop hl
 ld bc,40
 add hl,bc
 ld b,7
map_pixels:
 ld (hl),d
 inc hl
 djnz map_pixels
 ld bc,8
 add ix,bc
 pop bc
 inc c
 djnz map_cell
 ld de,40
 add ix,de
 ld a,c
 pop bc
 ld c,a
 djnz map_row
 ; Eight fault indicators use the accumulated counters, not decorative data.
 ld hl,alarm_label
 ld de,screen+640
 call puts
 ld hl,bits_up
 ld ix,bits_down
 ld de,screen+680
 ld b,8
alarm_loop:
 ld a,(hl)
 inc hl
 or (hl)
 inc hl
 or (ix+0)
 or (ix+1)
 inc ix
 inc ix
 ld c,tile_led_off
 jr z,alarm_store
 ld c,'X'
alarm_store:
 ld a,c
 ld (de),a
 inc de
 ld a,b
 neg
 add a,8+48
 ld (de),a
 inc de
 ld a,c
 ld (de),a
 inc de
 inc de
 inc de
 djnz alarm_loop
 ret
memtitle: db "V9968 MEMORY DIAGNOSTICS      READ 0.2",0
bank_suffix: db ":16K",0
status_fill: db "INITIALIZING / REFERENCE WRITE",0
status_read: db "SCANNING / VRAM READ IN PROGRESS",0
status_good: db "COMPLETE / NO MISMATCH IN TESTED AREA",0
status_error: db "MISMATCH DETECTED / SEE VALUES BELOW",0
alarm_label: db "BIT FAULT MAP / BIT0 TO BIT7",0
puts:
 ld a,(hl)
 or a
 ret z
 ld (de),a
 inc hl
 inc de
 jr puts
hex16:
 ld a,h
 call hex8
 ld a,l
hex8:
 push af
 rrca
 rrca
 rrca
 rrca
 call nibble
 pop af
nibble:
 and 15
 add a,48
 cp 58
 jr c,digit
 add a,7
digit:
 ld (de),a
 inc de
 ret
title: db "V9968 VRAM READ LAB 0.2",0
subtitle: db "240 KiB / CPU READ / ALL VALUES HEX",0
labels: db "CPU = 0 GAP= 0 PATTERN=00 PHASE=0",0
lab_counts: db "BASEERR=0000 TESTERR=0000 BLOCKS=0000",0
lab_first: db "FIRST=00000 EX=00   GOT=00  XOR=00",0
lab_retry: db "RETRY=00 PASSES=0000 AUTO=0",0
lab_bits: db "0->1 BIT 0  1    2    3    4    5    6 7",0
lab_down: db "1->0 BIT 0  1    2    3    4    5    6 7",0
help:
 db "1 Z80  2 R800-ROM  3 R800-DRAM          "
 db "4 GAP  5 DISPLAY  6 PATTERN  7 RESTART  "
 db "0 AUTO   GAP 0=INI 1=4NOP 2=16NOP       "
 db "DISPLAY=1  MAP FILLED=SCANNED X=FIRST   "
 db 0
footer:
 db "BASEERR=REFERENCE / TESTERR=FAST READ   "
 db "240KiB / COUNTS HEX / FFFF=SATURATED    "
 db 0
missing: db 13,10,"V9968 ID NOT FOUND. CHECK I/O VARIANT.",0
turbo: db 0
vdp_id: db 0
cpu: db 0
gap: db 0
pattern: db 3
display_on: db 1
continuous: db 0
oldkeys: db 255
phase: db 0
bank: db 0
chunk: db 0
repeat_count: db 0
test_kind: db 0
err_xor: db 0
err_actual: db 0
stats_begin:
passes: dw 0
baseline_errors: dw 0
errors: dw 0
blocks: dw 0
first_valid: db 0
first_bank: db 0
first_chunk: db 0
first_offset: db 0
first_expected: db 0
first_actual: db 0
first_xor: db 0
first_retry: db 0
bits_up: defs 16,0
bits_down: defs 16,0
stats_end:
expect: defs 256,0
actual: defs 256,0
screen: defs 960,32
font: incbin "src/font.bin"
