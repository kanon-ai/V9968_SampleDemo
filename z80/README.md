# Z80 optimization update — 2026-10-05

**CATSTRIDERとCAPE CIRCUITを、画面の内容を維持してZ80向けに最適化しました。**
V9968は引き続き必要です。通常のMSX2内蔵VDP向け移植ではありません。
各ROMは512 KiB / ASCII8、現行仕様V9968・256 KiB VRAM・98h–9Chポート用です。

## ダウンロード

|デモ|通常版|Z80固定版|
|---|---|---|
|CATSTRIDER|[auto ROM](roms/CATSTRIDER-auto.rom)|[Z80 ROM](roms/CATSTRIDER-Z80.rom)|
|CAPE CIRCUIT|[auto ROM](roms/CAPE_CIRCUIT-auto.rom)|[Z80 ROM](roms/CAPE_CIRCUIT-Z80.rom)|

通常は **auto版** を使用してください。turbo Rでは従来どおりR800 DRAMを選択します。
Z80固定版はturbo RでもZ80で動かし、描画負荷や動きを比較するためのものです。
turbo R以外のBIOSではCPU切り替えを呼びません。ただし今回の検証はFS-A1ST相当の
Z80/R800切り替えによるもので、各MSX2機や外付けV9968との互換性を保証するものではありません。

## 効果

openMSXのFS-A1ST + 現行V9968、標準Z80モードでの計測です。
ホストPC側の描画fpsではなく、エミュレートされた時間あたりのデモ更新回数です。

|デモ|変更前 Z80|変更後 Z80|変更前 R800|変更後 R800|
|---|---:|---:|---:|---:|
|CATSTRIDER|19.97|29.96|29.96|29.96|
|CAPE CIRCUIT|19.97|29.96|28.57|28.57|

両方ともZ80で約50%改善しました。R800の結果は維持しています。
動作・音楽は従来どおりデモのフレーム番号に連動するため、Z80での進行も速くなります。
画数や解像度を減らす変更、画像・キャラクター・動きのデータの差し替えはありません。

PRISM FLIGHT / SUPER CAT / MIST VALE / LUMEN FORGEは短い基準測定で既に約60更新/秒でした。
今回の試行では表示速度の改善を確認できなかったため、これらの公開ROMは変更しません。
[短時間の測定値](unchanged-demos.json)は全区間・全機種で60fpsを保証するものではありません。

## 変更点

- フレームデータのメモリコピーを16バイト単位のLDIに展開し、LDIRの反復コストを削減。
- CATSTRIDER: ISRがS2選択を復元する性質を利用し、コマンド待ちの各反復での再選択を省略。
  走査線ループのR17設定も直接書き込みにし、呼び出しコストを削減。
- CAPE CIRCUIT: 走査線ループのR17設定を直接化し、4バイトの間接レジスタ転送をOUTIに展開。
  元の安全なVBlank待ちを維持。
- VRAMのアップロード手順、画像データ、割り込みハンドラー、表示ページ構成は維持。

## 検証範囲

- openMSX: 両デモ・変更前後・Z80/R800の全8条件で一周以上。
  フレーム順序、ループ、VBlank中かつコマンド完了後の画面切り替えを検証。
- 同じフレーム位置で256 KiBの物理VRAM全体を比較。
  CATSTRIDERは23地点、CAPE CIRCUITは4地点で変更前後が一致。
- BlueMSX Plus: 最終4ROMの起動、継続するアニメーション、保存状態のCPUモード、
  R20/R21、256 KiB VRAMを確認。速度の前後比較表はopenMSXの計測であり、BlueMSXの計測ではありません。
- **実機未検証・試作・無保証**。[免責事項](../DISCLAIMER.md)が適用されます。

[openMSX検証データ](verification-openmsx.json) · [BlueMSX Plus検証データ](verification-blueMSX.json)
· [ROMのSHA-256](manifest.json)

## 再ビルド

リポジトリ全体を取得し、Python 3とPasmoを用意してください。
既存デモの固定アセットと起動コードを参照するので、このフォルダーだけではビルドできません。

```powershell
$env:PASMO = 'C:/Software/Pasmo/pasmo.exe'
python z80/build.py
python z80/verify_openmsx.py --openmsx 'C:/Program Files/openMSX/openmsx.exe'
```

検証には利用者のV9968対応エミュレータ、マシン定義、BIOSが必要です。
BIOS、エミュレータ、セーブステートは同梱しません。
従来版は比較・再現用に保持してあります。

## English

CPU-optimized editions of CATSTRIDER and CAPE CIRCUIT, still requiring current-spec V9968.
Both improve from approximately 20 to 30 updates per emulated second in turbo R Z80 mode.
R800 performance is preserved. Artwork and motion data are unchanged. Use the auto ROM normally;
the Z80 ROM forces Z80 on turbo R for comparison. This is not a port to the standard MSX2 VDP.

Full-cycle openMSX checks include frame order, VBlank-safe presentation, command completion,
and matching full physical VRAM at sampled frame positions. BlueMSX Plus boot, animation and
CPU/VDP-state checks also passed. Physical hardware and individual MSX2 machines remain unverified.
The existing five v2.0.0 ROMs and previous CAPE CIRCUIT ROM remain available unchanged.
