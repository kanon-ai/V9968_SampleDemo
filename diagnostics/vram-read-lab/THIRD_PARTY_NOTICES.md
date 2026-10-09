# 第三者情報 / Third-party notices

以下の公開資料・ツールを参照または使用しています。それぞれの権利と利用条件は各提供元に帰属します。

- [HRA! / V9968_Cartridge](https://github.com/hra1129/V9968_Cartridge)：V9968レジスタ仕様の参照元。
- [buppu3 / V9968対応openMSX](https://buppu3.github.io/)および[openMSX](https://openmsx.org/)：検証環境。
- [blueMSX Plus](https://github.com/Hesoten/blueMSX-plus)：追加検証の対象。確認状況はREADMEに記載。
- [Pasmo](https://pasmo.speccy.org/)：Z80アセンブラー。
- [Python](https://www.python.org/)：ビルド・検証スクリプトの実行環境。

BIOS、システムROM、エミュレーター実行ファイル、ステートファイル、第三者コンパイラーのランタイムは同梱していません。`config/HRA_V9968.xml` は外付け88h〜8Ch構成を表す検証用設定例であり、BIOSやFPGAビットストリームを含みません。フォントと表示用パターンは本診断ソフト用に作成したデータです。

Third-party tools and specifications retain their respective rights and terms. The package does not include BIOS images, system ROMs, emulator executables, saved states or compiler runtimes. The XML configuration is a test profile, not a BIOS image or FPGA bitstream. Font and display patterns were prepared for this diagnostic.
