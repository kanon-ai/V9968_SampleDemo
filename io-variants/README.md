# 公開デモ：外付け88h版・内蔵98h版

2026-10-19版。公開済みの全6デモについて、V9968外付けカートリッジ用と内蔵置換用のROMを用意しました。絵・演出・音楽は変更していません。内蔵版は従来の公開ROMとバイト単位で一致します。CATSTRIDERとCAPE CIRCUITには公開済みのZ80最適化を含みます。

**全ROMはASCII8です。V9968が必要です。通常のMSX内蔵VDPやV9990では動作しません。外付け版はopenMSXの現行V9968構成で検証しました。今回の外付け版はBlueMSX Plus・実機では未確認です。従来の内蔵版の検証状況を外付け版に読み替えないでください。試作・無保証です。**

## ROMを選ぶ

- **EXTERNAL-88:** V9968を88h–8Chに接続した外付け2nd VDP用。映像は外付けV9968側の出力で確認してください。本体VDPの映像とは別です。
- **INTERNAL-98:** 本体VDPの代わりに98h–9Chを使用するV9968用。外付け88hカートリッジ用ではありません。
- **auto:** turbo RではR800を選択します。他機種はZ80で実行しますが、この追加版の検証機種はturbo Rです。
- **Z80:** turbo RでもZ80を選択する比較用ROMです。CATSTRIDER・CAPE CIRCUITに用意しました。

| デモ | 外付け88h / auto | 内蔵98h / auto | 容量 |
|---|---|---|---|
| PRISM FLIGHT | [ROM](roms/PRISM_FLIGHT-EXTERNAL-88-auto.rom) | [ROM](roms/PRISM_FLIGHT-INTERNAL-98-auto.rom) | 128KiB |
| SUPER CAT / COASTAL FLIGHT | [ROM](roms/SUPER_CAT-COASTAL_FLIGHT-EXTERNAL-88-auto.rom) | [ROM](roms/SUPER_CAT-COASTAL_FLIGHT-INTERNAL-98-auto.rom) | 512KiB |
| LUMEN FORGE | [ROM](roms/LUMEN_FORGE-EXTERNAL-88-auto.rom) | [ROM](roms/LUMEN_FORGE-INTERNAL-98-auto.rom) | 512KiB |
| MIST VALE | [ROM](roms/MIST_VALE-EXTERNAL-88-auto.rom) | [ROM](roms/MIST_VALE-INTERNAL-98-auto.rom) | 512KiB |
| CATSTRIDER | [ROM](roms/CATSTRIDER-EXTERNAL-88-auto.rom) | [ROM](roms/CATSTRIDER-INTERNAL-98-auto.rom) | 512KiB |
| CAPE CIRCUIT | [ROM](roms/CAPE_CIRCUIT-EXTERNAL-88-auto.rom) | [ROM](roms/CAPE_CIRCUIT-INTERNAL-98-auto.rom) | 512KiB |

| Z80固定版 | 外付け88h | 内蔵98h |
|---|---|---|
| CATSTRIDER | [ROM](roms/CATSTRIDER-EXTERNAL-88-Z80.rom) | [ROM](roms/CATSTRIDER-INTERNAL-98-Z80.rom) |
| CAPE CIRCUIT | [ROM](roms/CAPE_CIRCUIT-EXTERNAL-88-Z80.rom) | [ROM](roms/CAPE_CIRCUIT-INTERNAL-98-Z80.rom) |

[全16本のダウンロード](https://github.com/kanon-ai/V9968_SampleDemo/releases/tag/io-variants-20261019) · [ROMハッシュ・対応ソース](manifest.json)

VRAM READ LAB診断ROMの両版は[こちら](../diagnostics/vram-read-lab/README.md)です。診断ROMのみ32KiB通常ROMで、上記デモとはマッパーが異なります。旧互換モード向けの過去版は従来の場所に残しています。

## 外付けVDPの同期と割り込み

本体VDPと外付けVDPは別の同期源です。BIOSフックを使う場合、本体VDPの垂直同期に由来するH.TIMIを外付けVDPの同期として使うことはできません。

このデモ集ではBIOSのH.TIMI/H.KEYIを使用していません。

- PRISM FLIGHT / SUPER CAT / LUMEN FORGE / CAPE CIRCUIT: DI状態で、選択したVDPのステータスを直接ポーリングします。
- MIST VALE / CATSTRIDER: 独自IM2ハンドラーで、選択したVDPのステータスを読み、割り込みを処理・解除します。外付け版では本体VDPの割り込みを無効化します。MIST VALEのラスタ割り込みも外付け側を読みます。

単にH.TIMIをH.KEYIに置き換えたROMではありません。起動後はデモがVDPとCPUの割り込み処理を専有する構成です。

## 検証範囲

[検証結果](verification-openmsx.json)には使用エミュレーターのSHA-256と各ROMの結果を記載しています。

- 内蔵: Panasonic_FS-A1ST_V9968。外付け: Panasonic_FS-A1ST + [HRA_V9968拡張定義](../diagnostics/vram-read-lab/config/HRA_V9968.xml)。現行の`V9968`を使用し、旧互換モードは使用していません。
- 全16本を各デモの全周期＋2フレーム実行し、フレームの連続進行とループ復帰を確認。
- 全画面切り替えで、対象VDPが垂直帰線中かつコマンド完了後であることを確認。
- MIST VALEとCATSTRIDERの割り込みカウンターの進行を確認。
- 外付けauto版6本はV9968側の映像をキャプチャし、代表画面も確認。
- 各ROMの64・256フレーム目で、内蔵／外付けの描画領域と素材領域を比較。画面外の未使用ページ末尾はBIOS初期化の違いがあるため比較から除外しています。全フレームの画像一致を保証する試験ではありません。
- 内蔵版8本は既存公開ROMと完全一致。素材・動きのデータと起動コードは両版で維持。

更新速度はCPU・接続構成・エミュレーターのタイミングに依存します。特に今回のCAPE CIRCUITのR800測定値は内蔵／外付け構成で差があります。実機での速度・安定性を保証するものではありません。

## 再ビルド

リポジトリ全体、Python 3、Pasmoを使用します。

```powershell
$env:PASMO = 'C:\path\to\pasmo.exe'
python io-variants/build.py
python io-variants/verify_openmsx.py --openmsx 'C:\path\to\openmsx.exe'
```

ビルダーは公開ソースの`VDP_BASE`を選択して再アセンブルします。外付け時のIM2初期化は既存ソースの条件付き処理を使用します。内蔵版の完全一致をビルド時にも検査します。検証には利用者自身で用意した対応エミュレーター・マシン定義・BIOSが必要です。

## English

All six published graphics demos now have separate **external 88h–8Ch** and **internal 98h–9Ch** editions. All are ASCII8 ROMs and require V9968. Use the external V9968 video output for the external editions. The eight internal ROMs are byte-identical to their published baselines. CATSTRIDER and CAPE CIRCUIT retain the published CPU optimizations and include forced-Z80 editions.

The external editions were tested in current-specification openMSX, **not yet in BlueMSX Plus or on physical hardware**. Earlier internal-edition validation does not establish external-edition compatibility. Synchronization uses the selected VDP: direct status polling for four demos, private IM2 handlers for MIST VALE and CATSTRIDER. These demos do not use H.TIMI or H.KEYI. Hardware performance and continued support are not guaranteed.

[利用条件 / Copyright](../COPYRIGHT.md) · [免責 / Disclaimer](../DISCLAIMER.md)
