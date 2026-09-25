# 第三者のツール・資料 / Third-party tools and references

本デモの実装では、HRA!氏のV9968仕様・FPGA実装、およびbuppu3氏のV9968対応openMSXを参照しました。資料・実装・検証環境を公開してくださった両氏に感謝します。

- [V9968_Cartridge — HRA!](https://github.com/hra1129/V9968_Cartridge)
- [V9968対応openMSX — buppu3](https://buppu3.github.io/)
- [openMSX](https://openmsx.org/)：エミュレーター。バイナリー、ソース、マシンXMLは本リポジトリに同梱していません。
- [BlueMSX Plus](https://github.com/Hesoten/blueMSX-plus)：V9968対応版で検証しました。本体・BIOS・保存状態は同梱していません。
- [FFmpeg](https://ffmpeg.org/)：実行動画のMP4変換に使用。本体は同梱していません。
- [Pasmo](https://pasmo.speccy.org/)：Z80アセンブラー。実行ファイルやランタイムは同梱・リンクしていません。
- [Python](https://www.python.org/)・[Pillow](https://python-pillow.org/)：素材生成・ビルドに使用。実行環境は同梱していません。

背景・ウサギ・動きのテーブルは `tools/build.py` で本デモ用に生成したものです。猫の元データは本プロジェクトのSUPER CATで作成した素材です。配布ROMは本プロジェクトのアセンブリーと生成データから構成され、BIOS、システムROM、エミュレーター、SDCC等のランタイムは含みません。

Thanks to HRA! for the V9968 specifications/FPGA implementation and buppu3 for the V9968-enabled openMSX. Third-party tools and documentation retain their respective rights and terms. They are referenced rather than redistributed here. The demo ROM contains the project's assembly and generated artwork/data; it does not bundle BIOS, emulator code or a third-party compiler runtime.
