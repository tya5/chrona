# G3/G4 Scene接続 設計レビュー

**状態:** 従前のG3/G4完了記録。統合監査 `g1-g4-integration-audit-2026-09-20.md` により完了判定は撤回され、R01–R04の是正設計が完了するまで本書は歴史的記録としてのみ扱う。

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

従前の結論として、G3/G4の残実装に必要なauthoring owner、Scene出力、有限手順、diagnostic、禁止救済は一意に閉鎖したと記録した。しかしR01–R04の再現により、公開出力までの接続と証拠閉包は未達である。


## 実装確認

G3は明示facet anchor、box候補時のown-anchor除外、全障害物leader routingをSVG adapterへ接続した。G4はView group順をSceneへ保持し、independent-lane-trackのtrack高とstack offsetを導出する。row-alignedは既存の1項目1行を保持する。全回帰は164 passed（既存DeprecationWarning 2件）。この回帰数だけではR01–R04の受入証拠にならない。
