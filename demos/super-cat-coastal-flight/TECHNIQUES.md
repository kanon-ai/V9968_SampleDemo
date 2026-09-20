# SUPER CAT / COASTAL FLIGHT — 技術解説

空飛ぶ猫が、提灯と肉球看板を掲げた屋形船のお祭りを見物します。映像の題材はジョークですが、**画面全体の回転・拡大縮小・前進は、実行中のV9968のLRMMコマンドで描画**しています。

この文書は公開版の [ビルド・素材・航路生成](tools/build.py)、[実行コード](src/demo.asm)、[起動処理](src/boot.asm)、[録画検証](tools/capture.py) に対応しています。検証対象は `Panasonic_FS-A1ST_V9968` のlegacy-openMSX内蔵VDP構成です。現行FPGAや実機で同じレジスター設定・速度になることを確認した資料ではありません。

## 1. CPUとVDPの役割

起動時にASCII8 ROMから実行コードをRAMの8000h〜DFFFhへコピーし、turbo RではR800 DRAMモードを選択します。地形とスプライト原画はVRAMへ一度転送します。

毎更新、CPUが行う主な仕事は128バイトのモーションレコードをROMから読み、変形係数とスプライト属性をVDPへ渡し、描画完了と表示タイミングを待つことです。画面の54,272画素をCPUで回転させて転送する方式ではありません。

地形は256×768画素の4bpp原画1枚を基本に、船上の猫の小領域を更新します。録画済みの全画面画像を次々に再生する方式でもありません。航路の三角関数や高度演出はPythonで事前計算し、ROMには小さな係数・属性の表を保存します。

## 2. 全画面を一つの変換で描く

表示はSCREEN5の256×212画素。表示座標を `(x, y)`、参照元の開始座標を `(sx, sy)` とすると、LRMMへ渡す変換は次の形です。

```text
source_x = sx + (x * vx - y * vy) / 256
source_y = sy + (x * vy + y * vx) / 256

vx = round(cos(angle) * 256 / zoom)
vy = round(sin(angle) * 256 / zoom)
```

`vx`、`vy`は符号付き8.8固定小数点です。`zoom`を大きくすると、少ない原画範囲を画面全体へ拡大するため低空に見えます。小さくすると広い地形を見渡せ、高空に見えます。

カメラ中心 `(cx, cy)` を画面中心 `(128, 106)` に合わせるため、開始座標を逆算します。

```text
sx = round(cx - (128 * vx - 106 * vy) / 256)
sy = round(1024 + cy - (128 * vy + 106 * vx) / 256)
```

`1024`はVRAM上の地形原画のY座標オフセットです。画面の移動・回転・拡縮を別々の画像処理として重ねるのではなく、この一つの座標変換にまとめています。1更新につき、描画先256×212のLRMMを1回発行します。

実行コードではR#47〜50へベクトル、R#32以降へ開始座標・描画先・サイズを書き、コマンド30hを発行します。原画ウィンドウはX=0〜255、Y=1024〜1791です。これは本ROMが使用するプロファイルの説明であり、他の仕様版への無条件な互換性を示すものではありません。

## 3. 回りながら前に進む航路

カメラ位置と画面の回転角を無関係に動かすと、横滑りや、その場で地面を回している印象になりがちです。本デモでは**進行方向を航路の接線から求める**ことで、猫が向く画面上方へ前進し続けます。

```text
theta = 2π * frame / 2048 * 2
cx = 128 + 52 * sin(theta)
cy = 384 + 260 * cos(theta)

dx = 52 * cos(theta)
dy = -260 * sin(theta)
angle = atan2(dx, -dy)
```

約34.18秒で拡張した楕円航路を2周します。猫の視点では向きを変えつつ前進し、地形が画面手前へ流れます。高度は別のキーフレーム列から補間します。

```text
ease = u * u * (3 - 2 * u)
zoom = start_zoom + (end_zoom - start_zoom) * ease
```

この補間は高度変化のつなぎ目を穏やかにします。航路の前進自体は止めません。原画の外を参照しないように必要な最小倍率も計算し、最終的な倍率は約1.50〜4.5倍です。生成した整数開始座標・固定小数点ベクトルでも、全2048レコードの四隅が原画内に収まることを検査しています。

航路上の隣接点の差分と前方ベクトルの内積も、ループの継ぎ目を含めて正であることを確認します。これは事前計算した航路の検査です。画素単位では開始座標の整数丸めや8.8係数の量子化があり、サブピクセル補間された映像ではありません。

## 4. 猫・マント・影・雲

Sprite mode3の16×64原画を横に2枚並べ、各要素を構成します。

| 要素 | 枚数 | 内容 |
|---|---:|---|
| マントの縁 | 2 | 小さな8段階の変化。TP2で背景と混色 |
| 猫と短いマント | 2 | 背中にマントを描いた原画。旋回に応じて5つの傾きを選択 |
| 地上の影 | 2 | 高度に応じて寸法と猫からの距離を変更。TP2 |
| 雲2組 | 4 | 独立して流れる拡大スプライト。TP2／TP3 |

全要素が同一走査線に並んでも最大10枚です。影は黒い板を置くのではなく、暗い色を背景へ混ぜます。上昇すると影が小さく遠ざかり、降下すると大きく近づきます。

半透明はスプライトと背景の混色です。任意の数の半透明レイヤーを順番に合成する一般的なRGBA処理ではありません。また猫の傾きは原画の選択であり、猫自体を毎更新LRMMで回転しているわけではありません。

提灯・飾り旗・肉球看板は地形原画に描き込んであります。そのため屋形船と同じ変換で自然に回転・拡縮・移動し、個別の追従スプライトは不要です。提灯の独立した点滅処理はありません。

## 5. 固定した光源と、地形に乗る猫のアニメーション

地形上の影は北西の光源と反対の南東へ伸びる設定です。高度から得た長さを `h` とすると、地形座標での変位を `(0.6*h, 0.8*h)` とします。これを画面へ逆回転・拡大してから、猫と影の中心間の差分に使用します。

```text
h = 4 + 18 * (4.5 - zoom)
world_dx = 0.6 * h
world_dy = 0.8 * h
screen_dx = zoom * (cos(angle)*world_dx + sin(angle)*world_dy)
screen_dy = zoom * (-sin(angle)*world_dx + cos(angle)*world_dy)
```

`h` は物理単位の高度ではなく、倍率から得る演出用の影の距離です。光源は地形座標に固定した平行光として扱い、光源そのものを旋回させません。

したがって旋回中に影が画面の同じ方向へ貼り付くことはありません。地形の建物の影と同じ南東方向を保ちます。すべての2048レコードを地形座標へ逆変換して光源方向の一致を検証し、整数スプライト座標の丸め誤差も1画素以内で確認しています。光の遮蔽や水面・屋根の高さまでは計算していません。

屋形船は3隻、それぞれ2匹の猫を配置しました。法被姿の猫が手を振ったり踊ったりする、お祭りの観客です。スプライトとして画面に浮かせるのではなく、船首・船尾の16×16画素の地形パッチを8段階で更新します。各段階の原画は甲板の背景込みなので、前の姿勢が残りません。

48枚のパッチをスプライト原画の未使用領域X=64〜255、Y=64〜127に格納し、8更新ごとに6回のHMMMで地形へコピーします。その後の全画面LRMMが猫ごと回転・拡縮するので、足元は甲板と一致します。アニメーションの刻みは約7.49回／秒、画面更新は約59.92回／秒です。船上の猫はハードウェアスプライト数を増やしません。

## 6. 描画途中を見せない切り替え

```text
モーションレコードを読み込む
  → 8更新に1回、船上の猫のパッチをHMMMで更新
  → 裏ページへLRMMを開始
  → 対応するスプライト属性表を転送
  → コマンド完了を待つ
  → VBlankを確認
  → 背景ページと属性表を切り替える
  → 次のレコードへ
```

背景だけでなく属性表も2組用意します。途中まで描いた背景や、異なる更新の猫が組み合わされるのを避ける構成です。`wait_command` はS#2のCE、表示待ちは同じステータスのVRを確認します。

今回の全画面LRMMで、コマンド完了時点が既にVBlank内だった場合は、そのVBlankを使用します。ここで一度アクティブ期間へ戻るのを待ってしまうと、間に合っている表示機会を捨て、1更新が2映像フレームへ延びることがありました。

この待ち方は本デモの描画量で検証したものです。小さなコマンドへ変更するときは、同じVBlank内で何度も更新しないよう、フレーム番号などによる制御を改めて検討する必要があります。

## 7. メモリー配置

| VRAMアドレス | 用途 |
|---|---|
| 00000h〜07FFFh | 背景ページ0 |
| 08000h〜0FFFFh | 背景ページ1 |
| 10000h／10200hから各88バイト | スプライト属性10枚＋終端、2組 |
| 20000h〜37FFFh | 256×768・4bppの地形原画、96KiB |
| 38000h〜3FFFFh | 256×256・4bppのスプライト原画、32KiB |

ASCII8 ROMは8KiB単位で次のように割り当てています。

| バンク | 用途 |
|---|---|
| 0 | 起動処理 |
| 1〜3 | RAMへ転送する実行コードとパレット。未使用領域を含む |
| 4〜15 | 地形原画 |
| 16〜19 | スプライト原画 |
| 20〜51 | 2048×128バイトのモーション表 |
| 52〜63 | パディング |

128バイトのレコードは、先頭8バイトが `sx, sy, vx, vy`、続く80バイトが10枚の属性、残り40バイトが予約領域です。1バンクに64レコードが収まるので、レコード途中でバンクを跨ぎません。ROM全体は512KiBです。

## 8. 確認したことと限界

- [実行検証](outputs/verification.json)：36秒、2159回、約59.9227更新／秒。全更新間隔が1映像フレーム相当、ページ交互切り替え、CE解除後のVBlank表示、R800 DRAM、ループを確認。
- [航路検証](outputs/motion-verification.json)：全レコードの変換範囲、前進方向、ループ継ぎ目、スプライト数を確認。
- [再現性](outputs/reproducibility.json)：ソースから再生成したROMが録画対象ROMとSHA-256で一致。
- [動画検証](outputs/video-verification.json)：MP4全体をデコード。約59.92fpsを保持し、補間・再生速度変更なし。
- [追加演出の検証](outputs/festival-verification.json)：固定光源の全2048方向、拡張地形、6匹の姿勢差、全8段階の地形更新、16箇所のスプライト属性を検証。

数値は対象エミュレーターでの結果です。実機・フラッシュカートリッジ・現行FPGA・外付け構成の互換性や性能は未検証です。通常のV9958向け機能の説明でもありません。現在のROMは `R#20=7Fh` などlegacy-openMSX用の初期化を使用します。

ゲーム化する場合は、事前計算した航路を入力に応じたカメラ位置・角度へ置き換え、固定小数点の係数計算、衝突判定、音、敵などを追加する必要があります。本デモで表示できた速度だけから、その追加処理を含むゲームの速度を保証することはできません。

## English technical summary

**Live transform, compact control data.** The Z80/R800-side code reads one 128-byte record per update. V9968 LRMM transforms a 256×768, 4bpp terrain image into a 256×212 back buffer. The source mapping is `X=sx+(x*vx-y*vy)/256`, `Y=sy+(x*vy+y*vx)/256`, with signed 8.8 vectors. Motion tables contain parameters and sprite attributes, not rendered video frames. Trigonometry is computed offline by the Python builder.

**Forward motion follows the heading.** An elliptical camera path makes two wider circuits per 2048-update loop. The heading is derived from its tangent with `atan2(dx,-dy)`, so forward flight continues during turns. Altitude cues independently vary zoom using smoothstep interpolation. Minimum zoom is constrained to keep all transformed corners inside the source image. Positive forward displacement is checked across every path step, including the loop seam; integer coordinate and 8.8 coefficient quantization still apply to raster output.

**Sprites provide depth.** Ten Sprite mode3 entries form cape accents, the banked cat, its shadow and two clouds. Each element uses two 16×64 source strips. The cat has five precomputed bank poses. Shadow size/offset vary with altitude, while TP2/TP3 blend effects with the background. This is not arbitrary multi-layer RGBA compositing. Festival lanterns and paw banners are painted into the terrain and therefore share its transform at no additional sprite cost.

**World-space light and deck animation.** A fixed southeast shadow vector is rotated back into screen space using the camera heading and zoom. Its direction therefore remains consistent with terrain lighting during turns. Six 16×16 deck patches animate cats on three boats. Eight precomposed phases reside in the unused sprite atlas area; six HMMM copies update the terrain every eight display updates. The subsequent LRMM transforms cats and decks together. The CPU does not upload new animation pixels every frame. All eight native animation phases and 16 sampled sprite tables were checked byte-for-byte.

**Presentation is synchronized.** The runtime renders into the other background page, prepares the matching sprite attribute table, waits for command completion, then presents during VBlank. A completion already inside VBlank uses that opportunity rather than waiting an extra frame. This behavior was verified for the full-screen workload; smaller workloads need their own guard against multiple updates in a single blanking period.

**Layout and limits.** The 512KiB ASCII8 ROM contains a boot bank, three runtime banks, twelve terrain banks, four sprite banks, 32 motion banks and 12 padding banks. Each 128-byte record consists of four 16-bit transform values, ten 8-byte sprite entries and 40 reserved bytes. There is no per-frame CPU upload of the full screen.

**Evidence is emulator-specific.** The 36-second run recorded 2159 updates at approximately 59.9227 updates/s, consecutive motion records, alternating pages, completed commands during VBlank, exact source/animation upload and a loop wrap. The ROM reproduced byte-for-byte. These results apply to the internal legacy-openMSX V9968 profile; hardware, current FPGA and external configurations remain unverified. Adding interactive camera control, collision, sound and enemies would require additional implementation and performance measurement.

See [references](THIRD_PARTY_NOTICES.md), [terms](COPYRIGHT.md) and [disclaimer](DISCLAIMER.md).
