# LUMEN / FORGE implementation notes

> 新仕様v2.0.0の起動方法・VRAM配置・確認環境は[新版の案内](../../current/README.md)を参照してください。以下の旧版に固有の設定・計測値とは区別しています。


## 現在の動作状況（2026-09-22）

**openMSX 194a769の `V9968_OLD` 互換モードで動作確認済みです。** `openmsx-194a769` 版ROMと互換XMLを組み合わせてください。[設定と対応ROM一覧](../../UPDATE-20260922.md)を参照できます。新版は[新仕様対応版の案内](../../current/README.md)を参照してください。実機動作は未確認です。

**English:** Verified in openMSX 194a769 with V9968_OLD compatibility mode and the matching 194a769 ROM. For the current-specification version, see the new-version guide above. Physical hardware remains untested.


This sample targets the d884c4b V9968 openMSX implementation. It is not a hardware benchmark.

## Rotation, scale, transparency

Sprite3 has scaling and transparency attributes; it has no angle attribute. The rotation in this demo comes from **LRMM with R45.FG4=1 (80h)**. FG4 lets the command engine manipulate packed 4bpp sprite patterns while SCREEN8 remains displayed.

Each update issues two LRMM IMP commands (R46=30h). The first rotates a 128×128 crystal; the second rotates a 64×64 halo independently. The outside-window colour is zero, and IMP writes it too, clearing old silhouette pixels. Sprite3 then resizes these transformed images through eight 16×128 strips and four 16×64 strips. Two further particles complete the fourteen planes.

The motion table carries signed 8.8 VX/VY vectors and source origins. Shape rotations run in opposite directions, with independent sprite width/height changes. The background is copied only at initialization and remains stationary. The source bitmaps contain one orientation per object; the command engine generates every displayed orientation.

The two transforms produce 20,480 destination pixels per update. This is a work count, not a measured hardware throughput claim. After both commands finish, VBlank presentation changes the sprite atlas base and SAT together. S0.F latches a fresh VBlank; S2.VR confirms the blank interval. A consumed flag prevents two presentations in one blank.

## VRAM allocation

| Purpose | Physical VRAM | FG4 coordinates / registers |
|---|---|---|
| SCREEN8 source even pixels | 20000h–27FFFh | SCREEN8 logical source20000h |
| Source crystal/halo/particles | 28000h–2BFFFh | Y1280–1407, stride128 bytes |
| Reserved source atlas lower half | 2C000h–2FFFFh | unused |
| SCREEN8 source odd pixels | 30000h–37FFFh | SCREEN8 logical source20000h |
| Sprite atlas A | 38000h–3BFFFh | DY1792, R6=70h |
| Sprite atlas B | 3C000h–3FFFFh | DY1920, R6=78h |

The crystal occupies X0–127/Y1280–1407. The halo occupies X128–191/Y1280–1343. Particles occupy X192–223/Y1280–1295. Initialization copies all256×128 source pixels to each destination atlas, so particles are present on both. Per-frame commands overwrite only the crystal and halo regions.

The display pages are logical00000h and10000h, each using only256×212 pixels. R2 selects3Fh/7Fh. Both are initialized from the same source. SCREEN8 logical address A maps to physical P in this emulator:

```text
P = (A & 20000h) | ((A & 1) << 16) | ((A >> 1) & FFFFh)
```

The d884 mode3 checker reads physical contiguous attribute bytes. The CPU writes every SAT byte twice to logicalE000h/E400h, filling physical7000h/7200h and duplicate17000h/17200h. These lie below the212 displayed rows. R11=01h; R5=C3h/CBh. The two atlases, source images, display and attributes do not overlap.

## Palette and transparency

The emulator's legacy R20=7Fh enables its extended feature map. SCREEN8 uses R0=0Eh, R1=40h. R16 selects one of256 palette entries; the palette port receives R/G/B bytes, each0–31. Background indices0–191 remain fixed; sprite indices192–255 can change without altering the room.

Sprite attribute byte3 bits7:6 select TP. For each RGB5 component, with sprite S and background D:

| TP | Transparent fraction | Output |
|---|---|---|
| 0 | 0% | S |
| 1 | 25% | (3S+D)>>2 |
| 2 | 50% | (S+D)>>1 |
| 3 | 75% | (S+3D)>>2 |

Only the winning sprite is mixed with the bitmap. The halo does not alpha-blend with the crystal behind it; crossings follow sprite priority. Pixel colour index 0 is transparent. The alpha probe freezes a dedicated emulator instance and compares normal, sprite-disabled and opaque captures of the same frame; distributed ROMs are never patched.

Current FPGA R20/R21 mapping differs from this emulator. The SCREEN8/Sprite3 attribute workaround must also be checked against hardware. Replacing register constants alone is not sufficient evidence of hardware compatibility.

## ROM and RAM

- Bank0: ASCII8 bootstrap, AB header.
- Banks1–3: runtime copied to internal RAM8000h–DFFFh; turbo R R800 DRAM mode.
- Banks4–15:96KiB original artwork upload.
- Banks16–47:1024 records×256bytes of motion parameters.
- Banks48–63: padding to512KiB.
- Frame bufferE000h–E0FFh, stackF300h; runtime/data end belowA000h.

Record bytes0–7 are primary SX/SY/VX/VY;8–119 are fourteen sprite attributes;120 is palette phase;121 is chord;128–135 are the secondary transform. Remaining bytes are reserved and zero.

## Checks

`verify_motion.py` checks all ROM bank offsets, loop boundaries and per-line sprite occupancy. `verify.py` runs both emulator profiles, checks the source upload, R800 state, animation progression and loop wrap, and records a native video. `verify_transform.py` inspects transformed atlas pixels and stationary backgrounds. `alpha_probe.py` compares actual RGB5 blend results. `package.py` rebuilds and requires the ROM hashes to match the verification records.

Reference for FG4: [V9968 programmer register manual, pinned revision](https://github.com/hra1129/V9968_Cartridge/blob/ceeecd7e3c2d25c20045f797617af0f70ca228c1/fpga/V9968_Cartridge_TangNano20K/src/v9968/manual/v9968_programmers_manual_register_map.pdf). The current manual describes the feature; runtime register compatibility is separately scoped above.
