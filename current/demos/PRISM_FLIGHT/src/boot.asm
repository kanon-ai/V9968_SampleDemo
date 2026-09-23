; ASCII8 bank 0: map internal RAM into page 2 and copy the demo to it.
    org 04000h
    db "AB"
    dw start
    dw 0,0,0,0,0,0
start:
    di
    ld sp,0F300h
    xor a
    ld (06000h),a
    in a,(0A8h)
    rlca
    rlca
    and 3
    ld c,a
    ld b,0
    ld hl,0FCC1h
    add hl,bc
    ld a,(hl)
    and 080h
    jr z,primary_ram
    ld hl,0FCC5h
    add hl,bc
    ld a,(hl)
    and 0C0h
    rrca
    rrca
    rrca
    rrca
    or 080h
primary_ram:
    or c
    ld h,080h
    call 0024h
    di
    ld a,1
    ld de,08000h
copy_bank:
    ld (06800h),a
    ld hl,06000h
    ld bc,02000h
    ldir
    inc a
    cp 4
    jr nz,copy_bank
    ld a,(0002Dh)
    cp 3
    jr c,no_turbo
    ld a,082h
    call 0180h
no_turbo:
    di
    ld sp,0F300h
    jp 08000h
    defs 02000h-($-04000h),0FFh
