# 共通表現基盤：実装計画

**状態:** G1.4を再オープン。G1.5監査で未移行SVG adapterを検出。設計根拠は仕様30・ADR-0019。  
**範囲:** 共通基盤だけを実装する。ASTER、Controller Z、画像案A〜Dの名前で分岐しない。

## 実装順序

| 単位 | 変更範囲 | 成果と検証 | 公開境界 |
|---|---|---|---|
| G1.1 軸プリミティブ | 新規の純粋Date-only軸モジュールとunit test | half-open window、月・四半期・ISO週・day区間、tick step、入力不変、範囲外診断 | この単位だけで公開 |
| G1.2 設定・metrics閉包 | presentation settings resolver、font metrics、layout solver、否定test | revision/hash照合、family×weightごとの計測、明示intrinsic入力によるcontent/fraction/min/max/gap、非暗黙fallback | この単位だけで公開 |
| G1.3 比較markの意味 | 新規mark/anchor projection、unit test | plan/actual/baseline、span/point、欠測、負/ゼロ/正差分、stable source identity | この単位だけで公開 |
| G1.4 Scene接続 | Scene構築と**全公開SVG adapter**の境界、既存gantt/review/minimal移行adapter | adapterが日程・配置を再解釈しない。legacyを混ぜず出所metadataを維持 | この単位だけで公開 |
| G1.5 消費監査 | 設定変異表、literal棚卸し、raster/再現性検証 | G1対象の未消費設定と暗黙fallbackをゼロにする | G1完了として公開 |
| G2 | axis slot統合、labels、comparison mode、group×facet paint | 仕様30 §6–7のA/D共通表現 | 単位別に公開 |
| G3 | annotation box/leaderと説明slot | 同じ機構で作業注記と計画gate説明を通す | 単位別に公開 |
| G4 | stable lane stacking | label/mark/routeの共通occupancyを再利用 | 単位別に公開 |

### G1.1 完了記録

`src/chrona/presentation_axis.py`に、描画器非依存のDate-only intervalを追加した。
month、quarter、ISO week、dayの半開区間をclipし、natural calendar bucketのlabelと
stable indexを返す。既存SVG rendererはまだこのモジュールを呼ばない。
`tests/test_presentation_axis.py`はwindow境界、ISO週年、tick step、異常入力、
再現性を検証する。135 tests passed（既存のRefResolver deprecation warnings 2件）。

### G1.2 完了記録

base presetはidだけでなくrevisionとexact-byte SHA-256を照合し、family×weightの
font assetだけを選択する。`content` region/trackは明示intrinsic入力がなければ
診断し、fixed/content→fractionとgap/min/maxを決定的に解決する。Aster 5枚と
Controller Zの設定を新しいfont asset配列へ移行した。139 tests passed（既存の
RefResolver deprecation warnings 2件）。

### G1.3 完了記録

`presentation_marks.py`はspan/pointのplanned・actual・baseline・finish-deltaを
renderer非依存で投影する。span Actualはstart/finishがともに観測された場合だけを
受理し、片端をplannedから補わない。差分は符号を保ち、zero表示も明示policyである。

### G1.4 完了記録

`PresentationScene`がView windowからaxis interval・tick・comparison markを構築し、
table/timeline SVG adapterはその結果を座標とSVGへ変換する。Scene inputのaxisは半開区間を
そのまま出力し、旧rendererが落としていた末尾月を補正した。実績の片端欠損はactual markを
作らず、planned endpointで補わない。ASTER基準SVGを再生成し、148 tests passed。

### G1.4 再オープン記録

G1.5の静的消費監査で、`render_review_svg` と `render_svg` が依然としてaxis・planned/actual
markを直接生成していることを確認した。当初の「existing gantt」表現は仕様29の全公開SVG経路
という完了条件を満たしていなかった。G1.4はこれら二adapterを`PresentationScene`消費へ移行し、
同じ欠損actual・半開axis契約を適用するまで完了に戻さない。

## G1.1 の契約

`presentation_axis.py`はレンダラー非依存で、Date-onlyの`[windowStart, windowEnd)`を
有限のaxis interval列へ変換する。返すintervalは`start`、`end`、`level`、`label`、
`index`だけを持ち、座標・色・フォント・SVG文字列・locale fallbackを持たない。

- weekはISO-8601、月曜日開始である。
- month/quarter/week/dayの境界はwindow外へ伸ばさず、最初と最後をwindowでclipする。
- labelはintervalの自然境界から導く。clip後のstartで月や週を付け替えない。
- `end <= start`、未知level、tickStepが正でない値は安定したValueErrorを返す。
- tick stepはinterval列を間引くだけで、time windowやlabelの意味を変えない。
- 同じ入力は同じ順序・値を返し、入力objectを変更しない。

G1.1は既存rendererへまだ接続しない。従って既存PNGのpixel変更はない。これは
未使用の設定を「対応済み」と扱わず、単体の意味契約を先に固定するためである。

## G1.2–G1.5の中断規則

実装中に仕様30と既存29の間に新たな所有権・schema・migration上の矛盾が見つかった
場合、該当単位を中断し、仕様・schema・fixture・この計画を先に更新して公開する。
見栄えのためのsample固有分岐、環境フォントへの暗黙fallback、SVG内の再配置は受理しない。

## 完了判定

各単位は以下を満たすまで完了としない。

1. 正常、境界、異常入力のテストがある。
2. 既存の意味値または入力を変更しないことを検証する。
3. 同じ入力で決定的に再現する。
4. 対象差分だけをレビューしてnon-force公開する。
5. 未対応範囲を完了と報告しない。
