# SUPER CAT / COASTAL FLIGHT

マント猫が海岸と巨大屋形船の上を飛ぶ、**MSX turbo R＋V9968の全画面回転・拡大縮小・前方スクロールデモ**です。なぜか巨大屋形船は、提灯と肉球飾りで猫のお祭り中。空飛ぶ猫がお祭り見物に来た、というジョーク仕立てです。低空で駆け抜け、上昇して広く見渡し、旋回しながら前進を続けます。自動再生の技術サンプルで、操作するゲームではありません。

![Actual V9968 openMSX capture](outputs/preview.gif)

**[36秒の実行動画・約59.92fps／無音](outputs/SUPER_CAT-COASTAL_FLIGHT.mp4)** · [ROM・ソースZIP](outputs/SUPER_CAT-COASTAL_FLIGHT-source-and-ROM.zip) · [ROM](outputs/SUPER_CAT-COASTAL_FLIGHT-V9968-legacy-openmsx-internal.rom)

動画はV9968対応openMSXでROMを実行して内蔵録画したものです。フレーム補間や速度変更はありません。GIFは20fpsの短いプレビューです。**実機動作・実機性能は未確認**です。[免責事項](DISCLAIMER.md)・[利用条件](COPYRIGHT.md)をご確認ください。

**[技術解説：座標変換・航路・半透明・メモリー配置 / Technical explanation](TECHNIQUES.md)**

## 見どころと実装

- SCREEN5の256×212画面全域を、V9968のLRMMで毎更新変形。256×512の地形原画から回転・拡縮・移動を同時に描画します。
- 航路の接線方向に画面を向け、旋回中も常に前進します。約34.18秒で海岸を4周し、高度は独立に変化します。
- 地形倍率は約1.47〜4.5倍。猫の傾き、背中に重なる短いマント、影の大きさと距離、半透明の雲を組み合わせています。
- Sprite mode3を最大10枚使用。地形を裏ページに描画し、コマンド終了後のVBlankに表示します。
- ROMのモーション表に収めるのは変形係数とスプライト属性です。完成映像のフレームをROMから再生しているわけではありません。
- 512KiB ASCII8 ROM、2048更新のループ。猫・地形・船は本デモ用のコード描画です。

## 起動と検証

V9968対応openMSXの `Panasonic_FS-A1ST_V9968` マシンに、上記ROMを **ASCII8** 指定で読み込みます。数秒の原画転送後に始まります。通常のV9968未対応openMSXでは動作しません。

このROMは**内蔵VDPのlegacy-openMSXレジスタープロファイル専用**です。現行FPGAや外付けV9968構成用の検証済みROMではありません。BIOS・エミュレーター・マシンXMLは同梱していません。

36秒のエミュレーター実行で2158回、約59.92回／秒の更新を確認しました。全2157更新間隔は1映像フレームで、ループ境界、原画のVRAM転送一致、R800 DRAM、コマンド終了後のVBlank表示も検証しています。`outputs/verification.json`、`motion-verification.json`、`video-verification.json`、`reproducibility.json`を参照してください。これらは実機の性能保証ではありません。

## 再ビルド

Python 3.13、Pillow、Pasmoを使用しています。録画にはV9968対応openMSXとFFmpegも必要です。ツールは同梱しません。

```powershell
python -m pip install -r requirements.txt
$env:PASMO = 'C:/path/to/pasmo.exe'
python tools/build.py
$env:OPENMSX_EXE = 'C:/Program Files/openMSX/openmsx.exe'
$env:FFMPEG = 'C:/path/to/ffmpeg.exe'
python tools/capture.py
```

`OPENMSX_USER_DATA` で手元のopenMSXユーザーデータを指定できます。録画は本デモ専用の子プロセスで行い、既に起動しているエミュレーターを操作しません。

## English

**SUPER CAT / COASTAL FLIGHT** is an original automatic MSX turbo R + V9968 technical demo: full-screen rotation, zoom and continuous forward scrolling over a coast with oversized pleasure boats hosting a lantern-lit cat festival. The premise is deliberately silly; the full-screen transforms run on the emulated V9968. A cat wearing a short cape on its back banks into turns while translucent clouds and an altitude-dependent shadow provide depth cues.

The 512 KiB ASCII8 ROM uses a live 256×212 LRMM transform and up to ten Sprite mode3 entries. Terrain is a static source image; the ROM stores motion parameters rather than completed video frames. A 2048-update loop follows four forward circuits with independent altitude changes.

The 36-second MP4 is an actual emulator recording at approximately 59.92 fps without interpolation or speed changes. The GIF is a 20 fps preview. Only the internal `Panasonic_FS-A1ST_V9968` legacy-openMSX profile has been tested. Physical hardware, flash cartridges and current FPGA compatibility/performance are unverified. This experimental sample is supplied without warranty or a commitment to updates, fixes or support.

See [third-party references](THIRD_PARTY_NOTICES.md), [terms](COPYRIGHT.md) and [disclaimer](DISCLAIMER.md).
