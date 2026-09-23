# MIST / VALE implementation notes

> 新仕様v2.0.0の起動方法・VRAM配置・確認環境は[新版の案内](../../current/README.md)を参照してください。以下の旧版に固有の設定・計測値とは区別しています。


## 現在の動作状況（2026-09-22）

**openMSX 194a769の `V9968_OLD` 互換モードで動作確認済みです。** `openmsx-194a769` 版ROMと互換XMLを組み合わせてください。[設定と対応ROM一覧](../../UPDATE-20260922.md)を参照できます。新版は[新仕様対応版の案内](../../current/README.md)を参照してください。実機動作は未確認です。

**English:** Verified in openMSX 194a769 with V9968_OLD compatibility mode and the matching 194a769 ROM. For the current-specification version, see the new-version guide above. Physical hardware remains untested.


This sample is scoped to the d884c4b V9968 openMSX implementation. Hardware operation and timing are unverified.

## Visual layers

The VDP displays one SCREEN8 bitmap and Sprite3. The sample constructs visual depth by compositing a scrolling foreground bank and tree images into a back buffer, then blending fog sprites with that completed bitmap. The sky, mountains and distant forest remain fixed.

Both display pages receive the complete static mountain/sky/water source at initialization. On each update HMMM restores Y48..143 of the inactive page, a96-line band. The opaque ground copy fully replaces Y144..171, avoiding a redundant background restoration there. Four command descriptors copy the foreground bank into Y136..171, followed by five descriptors for the48×96 tree images. The upper8 bank rows use LMMM TIMP, which skips colour index0; the lower28 rows contain only opaque pixels and use the faster HMMM copy with the same pixel result. Tree copies also use LMMM TIMP. Source/destination rectangles are clipped before command dispatch; a zero-width descriptor is skipped. TreeY is constant throughout all1024 records. Tree wrap occurs only when the entire tree is offscreen.

The bank uses a176×36 repeating tile stored as256×36 pixels, with its first80 columns repeated on the right. It occupies otherwise unused source rows724..759. Both ground and trees derive their horizontal displacement from `progress = floor(frame * 352 / 1024)`. The ground source phase is `progress % 176`, so the tile repeats twice over the352-pixel motion cycle. Each height band uses two horizontal copies: sourceX=phase with width256−phase at destinationX=0, then sourceX=80 with width=phase at destinationX=256−phase. The top band copies sourceY724..731 into destinationY136..143 using LMMM TIMP (98h); the lower band copies sourceY732..759 into destinationY144..171 using HMMM (D0h). Matching the exact integer position phase, rather than only average speed, keeps tree roots attached to the moving bank. The existing landscape's first212 source rows, tree artwork and shared palette remain unchanged.

Three fog wisps each use four16×32 sprite strips, scaled to224×45,208×42 and192×37 pixels. They move horizontally about1.6times faster than the trees with a small downward component. Each source contains32 rows; this is not a large stored animation. TP3 makes each visible fog pixel75% transparent, using `(S+3*D)>>2` in each RGB5 component. Colour index0 is fully transparent. Overlapping sprites do not form multiple alpha layers: the winning sprite blends with the bitmap.

## Actual raster control

An IM2 interrupt handler handles the VDP's vertical and line interrupts. R19 targets171,175,...211; writes occur around the transition into the following display line. The first ten events change R27 over the water, and the final event resets it to0. VBlank also resetsR27, rearmsR19=171 and resets the wave pointer.

The generated waveform has32 phases with11 values each, including a final zero. Values0..4 correspond to a2-pixel mean with±2-pixel displacement. R25.MSK masks the exposed left background edge. The art extends to the right display edge, so its border is not itself turned into a moving wave.

The mountains, foreground bank and trees occupy rows above172. Raster offsets therefore affect only the water region. Sprite3 fog does not follow background horizontal scroll. R20.ILNS makes line interrupt placement independent of vertical scroll; R20.SVNS similarly separates spriteY fromR23. R23 remains zero in this sample.

This is not a pre-rendered wavy animation: the background pixels in water VRAM remain unchanged while actualR27 register writes alter their displayed positions. `verify_scene.py` traces the completed register writes and the emulator's current beam position.

## Interrupt safety

The256-byte motion record is copied from ASCII8 ROM toE000h. The IM2 table occupiesE800h..E900h with repeatedE9h bytes, pointing every bus vector at theJP stubE9E9h. The runtime and palette data are belowA100h; the stack startsF300h.

The interrupt handler preservesAF/BC/DE/HL. It ownsS0/S1 acknowledgement and usesR15/R19/R27. It does not changeR14, R16, R17 or the VRAM address. Two-byte control-port writes and status selection/read pairs in the main loop are protected withDI/EI. Thus command-parameter, SAT and palette transfers can be interrupted without losing their stream position.

Rendering and command completion finish before page/SAT presentation. The main loop waits for a fresh VBlank counter and checksS2.VR. It uses counters rather than pollingS0.F, since the interrupt handler acknowledges that flag. The external configuration disables the unused nativeVDP interrupt sources before enablingIM2, preventing an unacknowledged shared interrupt.

## VRAM layout

SCREEN8 logical addressA maps to physicalP in this emulator:

```text
P = (A & 20000h) | ((A & 1) << 16) | ((A >> 1) & FFFFh)
```

| Data | Address |
|---|---|
| Display0/1 | SCREEN8 logical00000h /10000h,256×212; R2=1Fh /3Fh |
| Static source landscape | logical20000h; physical20000h–27FFFh and30000h–37FFFh |
| Foreground bank256×36, repeating every176 pixels | logical2D400h–2F7FFh, sourceY724..759; unused rows after the212-line landscape |
| Tree atlas256×96 | logical30000h; physical28000h–2AFFFh and38000h–3AFFFh |
| Fog packed4bpp atlas | physical2C000h–2FFFFh, R6=58h |
| SAT0/1 | physical7000h /7200h, duplicate17000h /17200h |

The128KiB source block is uploaded while still in SCREEN5, where CPU writes address physical memory. SCREEN8 is selected afterward. SAT bytes are written twice to CPU logicalE000h/E400h because d884Sprite3 reads physical contiguous attributes despite SCREEN8's interleaving. These addresses are outside the212 displayed rows.

For this SCREEN8 configuration, R2 bit5 selects the two64KiB display pages. R2=1Fh displays logical00000h and R2=3Fh displays logical10000h. The previous3Fh/7Fh pair selected the same visible page, so drawing the supposed back buffer could erase and redraw trees during scanout. Completed VRAM images still looked correct after freezing. The pinned [display-page calculation](https://github.com/buppu3/openMSX/blob/d884c4b29d7e736d6e488aca5f28e124a410c19f/src/video/SDLRasterizer.cc#L595) masks the name-table value with `100h | displayY`; bit6 of R2 does not distinguish these two SCREEN8 pages.

## ROM and palette

Bank0 is the bootstrap; banks1–3 hold the runtime copied to RAM; banks4–19 hold128KiB of generated artwork; banks20–51 hold1024×256-byte motion records; banks52–63 pad the file to512KiB. The mapper isASCII8 and the CPU entersR800 DRAM mode.

The background, foreground bank and tree atlas share palette indices0–191. Index0 is the transparent key for the upper bank edge and tree copies; nontransparent art uses1–191. The lower28 bank rows contain no index0 pixels and are copied opaquely. Four sprite palette groups use192–255. Full palette entries areRGB5. Each frame updates only the64 sprite entries, leaving landscape colours stable.

Record offsets0–74 hold five15-byte tree command descriptors. Offsets80–175 hold12 eight-byte Sprite3 attributes;176 selects a palette phase,177 a quiet PSG chord,178 a raster phase. Offsets180–239 hold four15-byte bank command descriptors: two upper-edge LMMM TIMP copies and two opaque lower-bank HMMM copies, all dispatched before the tree descriptors. The remaining reserved bytes are zero.

## Validation

`verify_motion.py` checks every record, bank offset, constant tree height, fully offscreen tree wrap, matching ground/tree displacement, complete bank coverage and sprite-line occupancy. `verify.py` measures both emulator profiles over50 seconds includingloop wrap, checks original VRAM upload and interrupt counts, and records a native AVI.

`verify_scene.py --alpha` identifies the completed frame independently from image comparison, reconstructs the foreground-bank-and-tree composite pixel by pixel, verifies unchanged sky, water rows172..211 and source data, and traces real raster writes. It also freezes a private emulator instance and compares normal/background/opaque fog pixels with the RGB5 blend equation. Raster-boundary timing and the last clipped sprite column are identified separately from the interior blend comparison.

Page selection must be checked from the SCREEN8 display address, alongside continuous running captures. A correct completed VRAM buffer or frozen screenshot alone does not prove that active scanout avoided a buffer while it was being drawn.

Image captures use normal emulation speed with frame skipping disabled. A complete frozen VRAM image alone does not prove correct running display: the scanout check also observes actual command destinations and page presentation while the scene moves. Native recorder frames are retained without interpolation or speed changes.

The current FPGA register map differs from this legacy emulator. The SCREEN8/Sprite3 attribute workaround must be validated on hardware separately. See HRA!'s [V9968 register manual](https://github.com/hra1129/V9968_Cartridge/blob/ceeecd7e3c2d25c20045f797617af0f70ca228c1/fpga/V9968_Cartridge_TangNano20K/src/v9968/manual/v9968_programmers_manual_register_map.pdf) and [pinned emulator source](https://github.com/buppu3/openMSX/tree/d884c4b29d7e736d6e488aca5f28e124a410c19f).
