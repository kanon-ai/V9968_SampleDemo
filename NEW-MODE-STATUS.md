# V9968新モードの検証結果 — 2026-09-22

**openMSX 194a769の通常の `V9968` 新モードで、5デモすべてに表示不良を確認しました。新モード対応済みとは言えません。** 前回の `V9968_OLD` による回避は旧仕様互換の確認にとどまり、実機を目標とする対応ではありませんでした。推奨手順として撤回します。

今回の検証では互換モードを一切使用していません。インストール済み実行ファイルやユーザーのマシン設定も変更していません。新モードで正常表示できない検証用ROMは、正式な対応ROMとして配布していません。

## 検証条件

- openMSXソース：`194a769d98efd02c8a66a35e50e8e7790eb85efe`。調査時点の配布版・v9968ブランチ先頭。
- 実行ファイルSHA-256：`2ff553d82aee092a615e6a0431545eda5fe6e084ff6fecaa91bfb879339847f8`。
- FS-A1ST内蔵VDP構成、XMLは **`<version>V9968</version>`**。`V9968_OLD` は不使用。
- 全デモの初期化を新仕様の **R#20=1Fh、R#21=3Ah（V58=0）** に変更。18秒後のレジスター読出しでも両値を確認。
- SCREEN8の3本は、SP3時のリニアVRAM配置・属性1回書込みへ対応した素材と実装を使用。
- BIOSは既存のユーザー所有環境を使用。実機・FPGAでは未検証。

| デモ | 新モードでの結果 |
|---|---|
| PRISM FLIGHT | 背景が失われ、結晶も矩形状に崩れる |
| SUPER CAT | 地形の細部が失われる。猫や影が見えても合格とはしない |
| LUMEN / FORGE | 背景・結晶・光輪の表示不良 |
| MIST / VALE | 背景の繰り返し・分割などの表示不良 |
| CATSTRIDER | 床とキャラクターの表示不良 |

[検証値・検証ROMのハッシュ](compatibility/new-mode-194a769/verification.json)。画像：[PRISM](compatibility/new-mode-194a769/PRISM_FLIGHT.png)、[SUPER CAT](compatibility/new-mode-194a769/SUPER_CAT-COASTAL_FLIGHT.png)、[LUMEN](compatibility/new-mode-194a769/LUMEN_FORGE.png)、[MIST](compatibility/new-mode-194a769/MIST_VALE.png)、[CATSTRIDER](compatibility/new-mode-194a769/CATSTRIDER.png)。

## 確定できた阻害要因：新モードのVRAM容量

現行マシンXMLには `<vram>128</vram>` があり、従来のV9968実装はモデル選択時に256KiBを確保していました。しかし194a769の新モードでは、次の値を実際に確認しました。

```tcl
debug size {physical VRAM}
# 131072

debug write {physical VRAM} 196608 119
# Invalid address
```

全5デモは256KiBのVRAMを使用し、20000h以降に原画を置きます。この実行条件ではその領域自体が存在しません。新レジスター初期化後も容量は変わらず、VRAM配置を正しく直すだけでは解消できません。

ソースでは `hasEVR()` が `VM_V9968_OLD` のみに対してtrueになり、VDP初期化の256KiB確保がこの判定に依存しています。それ以外の経路ではXMLの容量を使用し、許容値は16/64/128/192KiBで、256KiBは含まれていません。このためXMLを単に256へ書き換える方法も、ソース上は受け付けられません。

さらにVDPコマンドの `setReadMask()` / `setWriteMask()` も `hasEVR()` から128KiB／256KiBの窓を選択しています。容量の確保だけでなく、CPUからのアクセスとコマンドのアドレス処理も、新モデルの能力と動作モードに沿って確認する必要があります。これが唯一の問題である、あるいは1箇所直せば全デモが通る、とはまだ断定していません。

これは**このエミュレーター版の新モデル経路に関する観測**です。V9968の実機設計や性能の不具合を示すものではありません。

## 今後の検証基準

新モードで256KiBが確保され、上位VRAMへのCPU転送・VDPコマンド・スプライト参照が一致することを先に確認します。その上で新仕様ROMの全ループ、両ページ、ラスタ、半透明、更新間隔を再検証します。互換モードへの切り替えを合格条件にはしません。エミュレーターでの合格と実機での合格も分けて記録します。

## English

All five demos **fail visual validation in the current-register `V9968` model** of openMSX 194a769. This test did not use `V9968_OLD`. Candidates explicitly initialized R20=1Fh and R21=3Ah, confirmed by register reads. The three SCREEN8 demos also used linear SP3 addressing.

A confirmed blocker is VRAM allocation: the supplied internal machine configuration produces only 131072 bytes of physical VRAM in the new model. Access at 196608 returns `Invalid address`, while the demos require 256KiB. In the source, `hasEVR()` recognizes only the old model, but both 256KiB allocation and command-window masks still depend on that predicate. Other access paths must also be audited before declaring this resolved.

The previous compatibility workaround is withdrawn as a recommendation for current-hardware development. Existing files remain historical evidence, not proof of current-model or FPGA compatibility. Failed candidates are not released as working ROMs. Physical hardware has not been tested.

## 一次資料

- [配布ページ](https://buppu3.github.io/)
- [VDP能力判定：VDP.hh](https://github.com/buppu3/openMSX/blob/194a769/src/video/VDP.hh)
- [VRAM確保・CPUアクセス：VDP.cc](https://github.com/buppu3/openMSX/blob/194a769/src/video/VDP.cc)
- [コマンドアクセス窓：VDPCmdEngine.cc](https://github.com/buppu3/openMSX/blob/194a769/src/video/VDPCmdEngine.cc)
