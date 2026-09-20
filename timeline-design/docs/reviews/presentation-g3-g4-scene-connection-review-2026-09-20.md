# G3/G4 Scene接続 設計レビュー

**状態:** G3 anchor obstacle是正を反映済み・公開待ち。G3/G4 visual実装は仕様・wire contract・正負fixture・本review・計画の公開確認後に再開する。

| 境界 | 固定した契約 | 禁止する救済 |
|---|---|---|
| View → annotation Scene | 明示`object/id/facet/endpoint`だけを投影し、facet未指定・actual欠損は診断 | plannedへの推測・最初の対象選択 |
| box → leader | 有限候補の最初の合法box。box候補時のみ自身のanchor markを除外し、他mark／required label／確定boxは衝突対象に残す。最近接矩形辺portを使う | 手動座標・tail・waypoint・曲線・anchor mark以外の除外 |
| leader → routing | 全mark／required label／確定boxを障害物、source mark境界に触れ得る最初の外向きsegmentだけ許可。state数はLayout limitで打切り | 無制限探索・dependencyとの意味混同・source mark全体の透過 |
| annotation → lane | annotation boxはlane occupancyから除外。box同士の衝突は安定annotation順でG3が解く | box配置とlane stackの循環・adapterでの再解釈 |
| mark → lane Scene | View group/order、stable item順、最小non-overlap stackをSceneへ記録 | adapter再順序化・別group移動 |
| lane → adapter | row-alignedはstackIndexをmetadataとして保持し、independent-lane-trackはScene由来pitch/track boundsでstackIndex→縦offset | 日程・label占有・stackの再解釈・row対応の暗黙破壊 |

## G4 surface境界

`row-aligned`は既存table/timelineの行対応を保つ互換surfaceであり、stackIndexをScene metadataとして保持する。`independent-lane-track`だけがgroupごとの派生trackを生成し、`scene-mark-extent-plus-clearance`で決まるpitch、trackPadding、trackGapを消費する。これによりstackを視覚的に無視したり、adapterが行高を推測する余地をなくす。

## 循環の閉鎖

`labels.anchorObstaclePolicy = exclude-own-anchor-from-box-collision` はbox配置だけの局所規則、`annotations.laneOccupancy = exclude-annotation-boxes` はG4 occupancy境界である。したがってG3は確定済みboxだけを後続boxの障害物として扱い、G4はmarkとrequired labelだけからstackを決める。双方が相手の未確定出力を待たないため、順序は一意で停止性を保つ。

## fixture受入

`presentation-g2-g4-design-v0.1.yaml`の二projectは長い日本語、actual欠損、candidate超過、
unsupported anchor、stack overflow、route limitを持つ。実装testはさらにbox port tie-break、
route state limit、facet未指定のdiagnostic、lane metadata不変性を検証する。

結論として、G3/G4の残実装に必要なauthoring owner、Scene出力、有限手順、diagnostic、禁止救済は一意に閉鎖した。
