# 共通表現基盤：実装計画

**状態:** G1.1着手可。設計根拠は仕様30・ADR-0019。  
**範囲:** 共通基盤だけを実装する。ASTER、Controller Z、画像案A〜Dの名前で分岐しない。

## 実装順序

| 単位 | 変更範囲 | 成果と検証 | 公開境界 |
|---|---|---|---|
| G1.1 軸プリミティブ | 新規の純粋Date-only軸モジュールとunit test | half-open window、月・四半期・ISO週・day区間、tick step、入力不変、範囲外診断 | この単位だけで公開 |
| G1.2 設定・metrics閉包 | presentation settings resolver、font metrics、layout solver、否定test | revision/hash照合、font weightごとの計測、content/fraction/min/max/gap、非暗黙fallback | この単位だけで公開 |
| G1.3 比較markの意味 | 新規mark/anchor projection、unit test | plan/actual/baseline、span/point、欠測、負/ゼロ/正差分、stable source identity | この単位だけで公開 |
| G1.4 Scene接続 | Scene構築とSVG adapterの境界、既存gantt移行adapter | adapterが日程・配置を再解釈しない。legacyを混ぜず出所metadataを維持 | この単位だけで公開 |
| G1.5 消費監査 | 設定変異表、literal棚卸し、raster/再現性検証 | G1対象の未消費設定と暗黙fallbackをゼロにする | G1完了として公開 |
| G2 | axis slot統合、labels、comparison mode、group×facet paint | 仕様30 §6–7のA/D共通表現 | 単位別に公開 |
| G3 | annotation box/leaderと説明slot | 同じ機構で作業注記と計画gate説明を通す | 単位別に公開 |
| G4 | stable lane stacking | label/mark/routeの共通occupancyを再利用 | 単位別に公開 |

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
