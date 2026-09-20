# G3/G4 Scene接続 設計レビュー

**状態:** 設計是正完了・公開待ち。G3/G4 visual実装はこのreview公開後に再開する。

| 境界 | 固定した契約 | 禁止する救済 |
|---|---|---|
| View → annotation Scene | 明示`object/id/facet/endpoint`だけを投影し、facet未指定・actual欠損は診断 | plannedへの推測・最初の対象選択 |
| box → leader | 有限候補の最初の合法box、最近接矩形辺port、直交経路 | 手動座標・tail・waypoint・曲線 |
| leader → routing | mark／required label／確定boxを障害物、state数はLayout limitで打切り | 無制限探索・dependencyとの意味混同 |
| mark → lane Scene | View group/order、stable item順、最小non-overlap stackをSceneへ記録 | adapter再順序化・別group移動 |
| lane → adapter | adapterはstackIndex→縦offsetのみを担当 | 日程・label占有・stackの再解釈 |

## fixture受入

`presentation-g2-g4-design-v0.1.yaml`の二projectは長い日本語、actual欠損、candidate超過、
unsupported anchor、stack overflow、route limitを持つ。実装testはさらにbox port tie-break、
route state limit、facet未指定のdiagnostic、lane metadata不変性を検証する。

結論として、G3/G4の残実装に必要なauthoring owner、Scene出力、有限手順、diagnostic、禁止救済は一意に閉鎖した。
