# 免責事項 / Disclaimer

**試作・無保証 / EXPERIMENTAL — AS IS, WITHOUT WARRANTY**

V9968 VRAM READ LABは、VRAM読み出しの不一致を調べるための非公式な実験用診断ソフトです。ハードウェアの合否を認証する製品ではありません。V9968の製作者、エミュレーターの開発者、MSX機器メーカーによる認定、保証、後援を意味しません。

## 検証範囲

- 検証記録が対象とするのは、明記されたソフトウェア版、エミュレーター、機種設定、条件のみです。
- エミュレーターでの正常終了は、実機・FPGA・Flashカートリッジでの動作、電気的な安全性、信号タイミングの余裕を保証しません。
- 故障注入による確認は、診断ロジックの検出能力の確認です。実機の不具合を再現したことにはなりません。
- エラーがゼロでもハードウェアが完全に正常とは限りません。エラーが出ても、原因がVRAMや特定の回路であるとは断定できません。検査対象外の領域や条件はREADMEに記載しています。
- BlueMSX Plusおよび実機の確認状況はREADMEと検証記録に従います。記録にない環境で確認済みと解釈しないでください。

## 利用時の注意と保証の範囲

本ソフトは診断のためRAM・VRAMの内容とVDP設定を変更します。作業中の状態を保持するためのソフトではありません。利用者は対象機器の設定と接続を確認し、必要なデータを事前に保存してください。

適用法で認められる範囲で、現状のまま無保証で提供します。正確性、完全性、商品性、特定目的への適合性、不具合がないことを保証しません。利用または利用不能に伴う機器・データの損害、業務中断、診断結果への依存等について責任を負いません。法令により排除・制限できない保証、責任、利用者の権利を除外するものではありません。

更新、不具合修正、問い合わせやバグ報告への対応は約束していません。BIOS、システムROM、エミュレーター等は利用者がそれぞれの利用条件に従って用意してください。

## English

V9968 VRAM READ LAB is an unofficial experimental diagnostic, not a hardware certification tool. Emulator results apply only to the documented versions and configurations and do not establish physical-hardware compatibility, electrical safety or timing margins. Injected faults validate detection logic, not reproduction of a physical fault. Zero errors do not prove that hardware is fault-free; detected errors do not uniquely identify a failing component.

The program changes RAM, VRAM and VDP state during diagnosis. Save any needed work beforehand. To the extent permitted by applicable law, it is provided **AS IS, WITHOUT WARRANTY**, including warranties of accuracy, completeness, merchantability or fitness for a particular purpose. Liability for damages arising from use, inability to use or reliance on diagnostic results is disclaimed, subject to rights and liabilities that cannot lawfully be excluded. Updates, support and responses to bug reports are not promised. Obtain external BIOS files and tools under their applicable terms. No endorsement by hardware or emulator developers is implied.
