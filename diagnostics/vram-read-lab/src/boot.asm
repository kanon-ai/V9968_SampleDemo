org 04000h
 db "AB"
 dw start
 dw 0,0,0,0,0,0
start:
 di
 ld sp,0f300h
 in a,(0a8h)
 rlca
 rlca
 and 3
 ld c,a
 ld b,0
 ld hl,0fcc1h
 add hl,bc
 ld a,(hl)
 and 080h
 jr z,primary
 ld hl,0fcc5h
 add hl,bc
 ld a,(hl)
 and 0c0h
 rrca
 rrca
 rrca
 rrca
 or 080h
primary:
 or c
 ld h,080h
 call 0024h
 di
 ld hl,04100h
 ld de,08000h
 ld bc,03f00h
 ldir
 jp 08000h
 defs 0100h-($-04000h),0ffh
