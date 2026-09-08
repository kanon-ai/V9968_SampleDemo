# 第三者のツール・資料 / Third-party tools and references

本デモでは、HRA!氏のV9968仕様・FPGA実装、およびbuppu3氏のV9968対応openMSXを参照しています。資料・実装・検証環境を公開してくださった両氏に感謝します。

- [V9968_Cartridge — HRA!](https://github.com/hra1129/V9968_Cartridge)：仕様・FPGA実装の参照先。
- [V9968対応openMSX — buppu3](https://buppu3.github.io/)：対象エミュレーター。
- [openMSX](https://openmsx.org/)：エミュレーター。バイナリー、ソース、マシンXMLは同梱していません。
- [Pasmo](https://pasmo.speccy.org/)：Z80アセンブラー。実行ファイルやランタイムは同梱・リンクしていません。
- [Python](https://www.python.org/)・[Pillow](https://python-pillow.org/)：素材生成、色変換、ビルド、検証に使用。実行環境は同梱していません。
- [FFmpeg](https://ffmpeg.org/)：プレビュー動画の変換用ツール。実行ファイル・ライブラリーは同梱していません。

ネコ素材はAI生成です。

魚と猫缶の素材もAI生成です。銀色と淡いピンクの鯛、肉球ラベルの架空の猫缶を元画像として、ハードウェア用のサイズ・パレットへ変換しています。巨大魚にも写真調の魚素材を使用します。魚と猫缶の生成記録は `art-source/ENEMY_PROMPTS.md` にあります。

光の効果、周辺背景、動きのデータは本デモ向けのプログラム生成です。既存ゲームの画面や楽曲を同梱していません。配布ROMは本プロジェクトのアセンブリーと生成データから構成され、BIOS、システムROM、エミュレーター、第三者コンパイラーのランタイムは含みません。

Thanks to HRA! for the V9968 specifications/FPGA implementation and buppu3 for the V9968-enabled openMSX. Third-party tools and documentation retain their respective rights and terms. They are referenced rather than redistributed here.

The cat asset is AI-generated.

The fish and cat-food tin assets are also AI-generated. The sources depict a silver-and-pink sea bream and a generic metal tin with a paw label, converted to hardware sprite sizes and palettes by `tools/photo_props.py`. The giant fish also uses the photographic fish artwork. Prompts are recorded in `art-source/ENEMY_PROMPTS.md`.

Visual effects, surrounding scenery and motion data are procedurally generated for this sample. User photographs, existing game screens and music are not redistributed. The ROM contains the project's assembly and generated data; it does not bundle system ROMs, emulator code or a third-party compiler runtime.
