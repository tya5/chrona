# 表現固定値外部化：設計レビュー

対象基準: `e65dc56d01ba9abc85b28b5c9c2a673a1e0d3829`。
今回の変更は設計文書・スキーマ・設計fixtureとその検証のみ。srcは変更しない。

## 接続確認

- Viewの選択・順序・日付とStyleの意味roleを保持し、設定の二重正本を作らない。
- Themeに外観、Layoutに配置、Detailに文言、Contextに実行寸法、Outputに出力方針を集約。
- 既存27/28仕様を29の統合契約へ接続。既存v0.1を黙って変更せずv0.2へ明示移行する。
- 最新ガント、旧review、summary、最小SVGの4経路を移行対象に含めた。
- プリセットは完全値または固定base＋部分上書き。配列全置換、null削除不可、未知キー拒否。
- 文字計測は固定係数の設定化ではなく実測へ置換。意味・安全性・数学規則は不変。
- Controller Z固有のPython分岐や専用描画命令は設計に含めない。
- P4是正として、v0.1資源だけからfont metrics／viewportを暗黙推測してv0.2へ昇格しない
  ことを明記した。v0.1は診断付きlegacy adapter、v0.2品質は明示settings閉包のみとする。

## 実行した検証

- `fixtures/validate_presentation_settings.py`: 2スキーマ、4正常例、11不正例、78項目群の台帳と既定値の一致を確認。
- `fixtures/validate_conformance.py`: temporal reference fixtures PASS。
- 既存pytest: 104 passed。既存RefResolver非推奨警告2件。

## 残る実装ゲート（設計検証で代用しない）

P1〜P5は `planning/presentation-settings-implementation-plan.md` に定義。
実在フォント・locale資産への束縛、参照hash、semantic closure、全設定の消費、
AST固定値監査、SVG再現性、画像比較は実装時に検証する。
fixtureのゼロhashは説明用であり、実行可能な資産参照ではない。
現時点で「実装から固定値を除去済み」「YAMLだけで全設定が反映される」とは主張しない。
