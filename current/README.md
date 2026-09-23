# V9968 Sample Demos v2.0.0 — 新仕様対応版

**2026年9月23日、公開済みv2.0.0の全5本をV9968対応BlueMSX PlusとopenMSX V9968 c620b69の双方で動作確認しました。新版はどちらでも実行できます。openMSXでは新仕様の `V9968` を使用し、互換モードは使用しません。** 旧バージョンはopenMSXの互換モードで動作可能です。[旧版の起動方法](https://github.com/kanon-ai/V9968_SampleDemo/blob/main/UPDATE-20260922.md)を参照してください。

実機を目標に現行V9968仕様へ対応した試作技術デモです。実機での動作・性能は未確認です。無保証で、継続的な修正やサポートを約束するものではありません。[免責事項](../DISCLAIMER.md)・[利用条件](../COPYRIGHT.md)を参照してください。

## 収録デモ

| デモ | 内容 | ROM |
|---|---|---|
| PRISM FLIGHT | 全画面変形と拡縮する結晶 | [128KiB](roms/PRISM_FLIGHT-V9968-current-internal.rom) |
| SUPER CAT / COASTAL FLIGHT | 回転・拡縮・前方スクロール、仮想光源の影、お祭り船の猫 | [512KiB](roms/SUPER_CAT-COASTAL_FLIGHT-V9968-current-internal.rom) |
| LUMEN / FORGE | 回転する結晶、拡縮と半透明の重ね合わせ | [512KiB](roms/LUMEN_FORGE-V9968-current-internal.rom) |
| MIST / VALE | 森と岸辺の同期スクロール、半透明の霧、水面ラスター | [512KiB](roms/MIST_VALE-V9968-current-internal.rom) |
| CATSTRIDER | 猫・魚・猫缶の疑似3D飛行、112走査線の遠近描画 | [512KiB](roms/CATSTRIDER-V9968-current-internal.rom) |

全ROMはASCII8、自動再生デモです。ネコ素材はAI生成です。CATSTRIDERの魚と猫缶もAI生成です。

## 起動方法

1. **V9968に対応したBlueMSX Plus**を使用してください。検証対象は[experimental/v9968ブランチ](https://github.com/Hesoten/blueMSX-plus/tree/experimental/v9968)のコミット `7f7a2572604dcd3dc82ba4cc7a8b7f6c9b3a9d92` をローカルビルドしたRelease x64版です。通常配布版すべてにV9968が含まれるという意味ではありません。
2. MSX turbo R（FS-A1ST相当）の機種で、VDPを **V9968、VRAMを256KB** に設定します。内蔵VDPのI/O 98h～9Chを使用します。
3. 上表の `current-internal.rom` をカートリッジスロットへ読み込み、マッパーを **ASCII8** に指定してください。
4. エミュレーション速度・VDP速度はともに100%を基準にしてください。起動後は自動再生します。

BIOSとエミュレータ本体は同梱していません。所有するBIOSを各自の環境で使用してください。旧版の互換モード用ROMと新版ROMを混在させないでください。

## openMSXでの起動・今後の検証

[openMSX V9968 c620b69](https://buppu3.github.io/) と `Panasonic_FS-A1ST_V9968` を使用し、公開ROMをASCII8で読み込んでください。VDPは `V9968`、内蔵98h–9Ch、timing=0です。`V9968_OLD` は使用しません。

今後の変更はBlueMSX PlusとopenMSXの両方で検証します。どちらか未検証の場合はその範囲を明記します。[追加検証の詳細](OPENMSX-20260923.md)。ROMと既存リリースZIPは変更していません。

Future changes will be checked with both emulators; any untested scope will be stated explicitly. Physical hardware remains untested.

## 今回の対応

- 現行のモードレジスターで初期化します。R20=1Fh、R21=3Ah、V58=0。
- SCREEN8とSprite mode3ではリニアVRAM配置を使用し、表示ページ・属性表・原画領域を分離しています。
- 既存の原画・航路・猫や船のアニメーション・音を維持しています。描画量や画質を削減する更新ではありません。

## 検証の範囲

5本ともBlueMSX Plusで起動・描画を確認しました。保存状態からVRAM256KB、R20/R21、R800 DRAM、原画転送、生成済みモーションと表示スプライト属性の一致を確認しています。SUPER CATの船上アニメーションが書き換える領域は、固定原画との比較対象から除いています。サンプリングによる検証であり、全フレームや実機での動作保証ではありません。

[ROMハッシュ](manifest.json)・[BlueMSX Plus検証記録](verification.json)を収録しています。エミュレータのSHA-256は `0066629d0fbfd2902cf3cda8ba20fe5c45b7de1639fa088bf4bc0ff841192c32` です。

[CATSTRIDER動画](previews/CATSTRIDER-blueMSX-100percent.mp4)・[SUPER CAT動画](previews/SUPER-CAT-blueMSX-100percent.mp4)はBlueMSX Plusの実行録画から各25秒を抜粋しました。音声保持、早回し・フレーム補間なし。設定は100%ですが録画負荷により速度表示が一時96%になる場面があり、実機FPSの測定資料ではありません。動画の60fpsとデモ内部の描画更新頻度は別です。

## 再ビルド

Python 3とPasmoを用意し、環境変数 `PASMO` にPasmo実行ファイルを指定するか、PATHへ追加してください。このディレクトリで `python build.py` を実行すると5本を再ビルドし、配布ROMのSHA-256との一致を検証します。収録する確定済み素材から再構築するため、画像生成サービスやBIOSは不要です。

## English

**As of September 23, 2026, all five v2.0.0 demos have been verified with both V9968-capable BlueMSX Plus and openMSX V9968 c620b69. Either tested emulator can run this version; use current-specification V9968 mode in openMSX, not compatibility mode. The previous version remains runnable in openMSX compatibility mode.**

Version 2.0.0 targets the current V9968 specification. It includes five automatic ASCII8 demos for MSX turbo R, using an internal V9968 at ports 98h–9Ch with 256KB VRAM. The tested emulator is a local Release x64 build of the linked experimental/v9968 branch at the commit above, not a claim that every regular BlueMSX Plus release supports V9968. Artwork and choreography are preserved. Source and frozen generated assets rebuild into the exact verified ROMs.

Validation covers natural execution, visual inspection, and sampled VRAM/register/sprite-attribute comparisons. Physical hardware and physical-hardware performance remain untested. These are experimental, noninteractive demos supplied without warranty or a commitment to ongoing support. BIOS and emulator binaries are not included.
