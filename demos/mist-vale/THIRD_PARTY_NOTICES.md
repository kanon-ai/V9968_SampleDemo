# 第三者のツール・資料 / Third-party tools and references

本デモの実装では、HRA!氏のV9968仕様・FPGA実装、およびbuppu3氏のV9968対応openMSXを参照しました。資料・実装・検証環境を公開してくださった両氏に感謝します。

- [V9968_Cartridge — HRA!](https://github.com/hra1129/V9968_Cartridge)
- [V9968対応openMSX — buppu3](https://buppu3.github.io/)
- [openMSX](https://openmsx.org/)：エミュレーター。バイナリー、ソース、マシンXMLは本リポジトリに同梱していません。
- [Pasmo](https://pasmo.speccy.org/)：Z80アセンブラー。実行ファイルやランタイムは同梱・リンクしていません。
- [FFmpeg](https://ffmpeg.org/)：録画からMP4・GIFへの変換に使用。実行ファイル・ライブラリーは同梱していません。Used for video/GIF encoding; binaries and libraries are not bundled.
- [Python](https://www.python.org/)・[Pillow](https://python-pillow.org/)：素材生成・ビルド・画像検証に使用。実行環境は同梱していません。

背景・木々・霧の画像と動きのテーブルは `tools/generate.py` で本デモ用に生成したものです。配布ROMは本プロジェクトのアセンブリーと生成データから構成され、BIOS、システムROM、エミュレーター、SDCC等のランタイムは含みません。

Thanks to HRA! for the V9968 specifications/FPGA implementation and buppu3 for the V9968-enabled openMSX. Third-party tools and documentation retain their respective rights and terms. They are referenced rather than redistributed here. The demo ROM contains the project's assembly and generated artwork/data; it does not bundle BIOS, emulator code or a third-party compiler runtime.
