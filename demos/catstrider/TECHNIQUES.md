# CATSTRIDER implementation notes

This document describes the native ROM implementation verified in the d884c4b V9968-enabled openMSX. Both internal and external configurations completed 54-second runs including a full stage and loop restart. Physical hardware and the current FPGA configuration are unverified.

## Scene and rendering

The sample is an automatic single-stage presentation with an introduction, a middle section, a giant photographic fish encounter and a finale. Its 1536 records run at a measured 29.9614 scene updates per second in both tested emulator configurations, giving an approximately 51.3-second loop. This measurement describes the emulator scene update rate. The display refresh rate and physical hardware performance are separate.

The renderer uses SCREEN8 with the V9968 extended 256-entry palette. Sky entries 0–127 remain fixed while floor entries 128–191 animate independently. Sprite mode3 uses entries 192–255 as four groups of 15 opaque colours plus transparent index 0. Up to 16 sprite planes are shared between characters and effects. A source image may span multiple planes; sixteen planes does not mean sixteen independent large characters.

The floor consists of 112 individually projected scanlines, Y100 through Y211. Each live LRMM command draws one row. A fixed 560-byte geometry table contains 112 five-byte entries: SX, signed 8.8 VX low/high, DX and NX low. Per-row phase compensation uses DX=0..4 and NX=256−DX; R25 masks the left 8 pixels as a guard. The generated horizontal phase error is at most 0.4942 pixels, reducing zigzags in the neon grid. The frame record supplies 112 SY bytes. Source Y advances with the same world travel used by the approaching objects. Sprite3 supplies live billboard scaling and selected transparency for the hero, supporting characters and effects. The hardware combines these pieces during playback.

The world moves more quickly through these coordinates while the scene update cadence remains about 30 per second. Expanding portal rings, side star streaks and a long rainbow reinforce depth and speed. Each of the three beams retains its emission position, then uses a perspective factor `q` to move toward the vanishing point or target and shrink with distance. Plane priority and transparency are scheduled within the 16-plane limit.

The hero keeps the original rear flight source throughout. Left/right banking remains, and the finale sends the rear-facing cat into the distance.

The floor transformation and scene positions are prepared in advance. The ROM does not evaluate a general polygon scene, perspective mesh, camera matrix or physics simulation every frame. It also does not store a sequence of complete rendered screens. The distinction matters: the ROM spends capacity on compact scene commands, while the VDP performs the repeated drawing and scaling.

## Source artwork and palettes

ネコ素材はAI生成です。

The cat asset is AI-generated.

The renderer uses the rear flight source `art-source/cat-flight-key.png`. Chroma-key conversion and 15-colour hardware quantization prepare it for Sprite3. The runtime keeps this rear pose for the full sequence, including the ending. `art-source/PROMPTS.md` contains the public asset notice.

`art-source/cat-front-sunglasses-key.png` supplies a front-facing cat wearing sunglasses, retained in an unused atlas slot. No stage record selects this front asset. The original `art-source/cat-key.png` is used only as the stable palette seed.

The fish and cat-food tin assets are also AI-generated. `art-source/fish-photo-key.png` depicts a silver-and-pink sea bream; `art-source/can-photo-key.png` depicts a generic metal cat-food tin with a paw label. The giant fish uses the photographic fish artwork as well. `tools/photo_props.py` prepares these sources for native sprite dimensions and palette conversion. Their generation prompts are recorded in `art-source/ENEMY_PROMPTS.md`.

The active scene takes procedural rainbow, laser, shadow and flare effects from `tools/props.py`. Fish and tin artwork is supplied by `tools/photo_props.py`. Each sprite group has at most 15 opaque colours plus transparency. Suggested transparency is metadata for the hardware; it is not baked into the source alpha channel.

`tools/effects.py` supplies the 64×64 portal ring and mirrored 16×64 incoming star streaks using the existing NEON palette. Their alpha is binary; hardware settings control blending. The portal has a transparent center and several coloured rim filaments.

The original 180 BPM PSG arrangement uses volume envelopes and channel C noise percussion. R7 writes preserve its upper I/O-control bits. Surrounding artwork, stage motion and music are made for this sample; user photographs and existing game graphics or music are not packaged.

## ROM layout

| ASCII8 banks | Content | Size |
|---|---|---|
| 0 | Bootstrap | 8 KiB |
| 1–3 | Runtime copied into RAM, with padding | 24 KiB |
| 4–15 | Initial VRAM artwork/data | 96 KiB |
| 16–63 | 1536 scene records, 256 bytes each | 384 KiB |

Total ROM size is 512 KiB. The scene records occupy the whole final 384 KiB bank range. Capacity figures describe this implementation and are not an assertion that further stages fit without redesign or compression.

The two builds target the legacy d884c4b openMSX register behaviour: I/O 98h for the internal V9968 machine, I/O 88h for the external expansion. The present FPGA register layout differs. These builds must not be described as validated current-FPGA hardware ROMs.

## Keeping future controls separate

`tools/stage.py` produces the stage sequence independently from rendering. Runtime autopilot writes explicit RAM hero state: `hero_x`, `hero_y`, `hero_width` and `hero_height`. `hero_width` is the destination width of one strip; the current hero uses three strips. `apply_hero_pose` applies this state to the hero's Sprite3 attributes.

This separation leaves a place to substitute input-driven state later. It does not implement player controls, collision detection, scoring or a complete game. Those would require their own design and verification. No future game or support commitment is implied by the hook.

## Validation status and boundaries

The [internal runtime report](outputs/runtime-verification-legacy-openmsx-internal.json) and [external runtime report](outputs/runtime-verification-legacy-openmsx.json) each record 54 emulated seconds and 1618 presentations at 29.9614 scene updates per second. Every presentation followed exactly two VDP frames; every complete update issued 112 LRMM rows. The full 1536-record sequence wrapped correctly. There were no writes to the visible bitmap page and no presentation while the command engine was busy or outside VBlank. Loaded floor geometry and physical VRAM upload matched their generated bytes. Both reports identify the tested ROM and installed emulator by SHA-256.

The [static asset audit](outputs/asset-verification.json) checked all 1536 records, both ROM bank mappings, sprite addresses and palette components. It verified the rear-only hero sequence, the shrinking departure and 74 emitted-beam lifetimes approaching their aim. The [artwork replacement audit](outputs/photo-enemy-change-verification.json) confirms that changes stayed within the photographic fish/can/boss regions, their palette groups and the unused front-cat sunglasses region. Runtime code, motion banks, rear-cat pixels and effect regions remained byte-identical to their recorded baselines. These are static comparisons, separate from emulator execution.

The [video report](outputs/video-verification.json) ties the internal ROM to its 54-second native AVI. The MP4 retains all 3236 display frames at 59.92 fps and recorded PSG audio, with no frame interpolation. The GIF contains 450 frames at a target 30 fps, a 15-second excerpt starting at 5 seconds. Media hashes and the source recording hash are included. These emulator observations do not establish physical V9968 timing or compatibility with the current FPGA implementation.

The Windows launch helper runs the internal configuration. Existing system ROMs and machine definitions remain external. The build uses Python/Pillow and Pasmo; their executables and libraries are not included in the ROM.

## References

- [HRA! V9968 specifications and FPGA project](https://github.com/hra1129/V9968_Cartridge)
- [buppu3 V9968-enabled openMSX](https://buppu3.github.io/)
- [Pinned d884c4b emulator source](https://github.com/buppu3/openMSX/tree/d884c4b29d7e736d6e488aca5f28e124a410c19f)

See [usage terms](COPYRIGHT.md), [disclaimer](DISCLAIMER.md) and [third-party notices](THIRD_PARTY_NOTICES.md).
