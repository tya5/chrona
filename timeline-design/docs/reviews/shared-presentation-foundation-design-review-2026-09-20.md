# 共通表現基盤 G0 / G2–G4 設計整合レビュー

**結論:** G0は閉鎖済み。G2–G4は `31-presentation-g2-g4-design-gate.md`、各owner schema、正負fixtureを
照合し、実装開始可能な設計水準で閉じた。実装完了ではない。

## 確認した整合

| 境界 | 結論 | 根拠 |
|---|---|---|
| 注釈 | 一般化可能 | 既存Viewのanchor/text、SceneのRect/Text/Path、Layout slotを組み合わせる |
| 特例防止 | 機構はサンプル・preset名を読まない | ADR-0019の採用ゲートとwire fixtureのowner分離 |
| 時間軸 | 複数slotの同期が可能 | View window由来のnormalized scaleと明示scaleId契約 |
| 意味分離 | dependencyとleaderは同じ経路器を再利用できる | sourceKind、端点、role、アクセシビリティを別に保持 |
| Detail milestones | 説明帯の第二本文源にしない | point listは派生surface、本文はView annotation |
| legacy | 新機能と混ぜない | 仕様29のlegacy adapter診断を保持 |

## 判断

吹き出しは「対象参照、測定済みtext bounds、有限候補、任意の直交leader」として
採用する。特殊な尾、手動座標、手動折れ点、任意形状、無制限探索は非採用とする。
これによりバー外ラベル、作業注記、ゲート説明の二用途以上を共通実装で扱える。

初期実装でrelation/group/temporal annotation anchorを描画しない決定は意図的である。
schemaが受理する既存conceptをobjectへ曖昧に置換せず、明示診断で保留する。

## fixture確認

`fixtures/validate_shared_presentation_foundation.py`はwire schemaとfixtureを検証し、
owner、週軸、注釈leader/routing、Scene/Layoutの責務分離を確認する。
これは設計fixtureの検証であり、SVGや配置器の動作証明ではない。

## 残る実装前提

- G1で既存v0.2設定の未消費項目とfont/metrics問題を是正する。
- G2でschemaを各authoring ownerへ実装し、移行adapterと否定fixtureを追加する。
- G3/G4はG2の共通テキスト、anchor、occupancy、routingを再利用できた項目だけ採用する。

実装中にこの契約を満たせない表現が判明した場合、当該実装を中断して設計を更新する。

## G2–G4 横断照合

| 境界 | 結論 | schema / fixture evidence |
|---|---|---|
| label text と配置 | 本文はDetail、有限候補・overflowはLayout。rendererは任意式・無限探索を持たない | `detail.labelRules`、`layout.labelPlacement`、候補数超過fixture |
| facet paint | group override、default、正規化済みglobal roleの順。group背景mapと混在しない | `theme.facetPaints`、group override fixture |
| axis slot | `timeline-axis` はtimelineと同一scaleを共有し、異なるscaleは診断 | `layout.slots`、仕様31の `E_PRESENTATION_SCALE_MISMATCH` |
| annotation | Viewのtyped object referenceのみを初期描画対象にし、手動座標・waypointは受理しない | `view-v0.1` のfacet付きanchor、actual欠損／unsupported anchor fixture |
| leader routing | 直交leaderはLayoutの有界route limitを使い、意味dependencyと別roleのまま経路器を共有 | `layout.routing.limit`、route-limit fixture |
| lane stack | View group/orderに従い、markとrequired labelのoccupancyから最小stackを選ぶ | `layout.lanes`、stack-overflow fixture |

## 診断と禁止救済

| diagnostic | owner | 禁止する救済 |
|---|---|---|
| `E_PRESENTATION_LABEL_UNPLACEABLE` | Layout | required labelのclip、無制限候補探索 |
| `E_PRESENTATION_SCALE_MISMATCH` | Layout | slotごとの別window/scale |
| `E_PRESENTATION_ANCHOR_MISSING` | View projection | actual欠損時のplanned代替 |
| `E_PRESENTATION_ANCHOR_UNSUPPORTED` | View / adapter | relation・group・temporalをobjectへ曖昧変換 |
| `E_PRESENTATION_STACK_OVERFLOW` | Layout | 別group移動、暗黙縮小、隠蔽 |
| `E_PRESENTATION_ROUTE_LIMIT` | Layout | limit超過の無制限探索 |

`validate_presentation_g2_g4_design.py` は、固有IDに依存しない二つのproject、長い日本語、actual欠損、
5種のnegative diagnosticを検査する。これは設計入力の検証であり、配置・SVG描画の動作証明は後続実装testで行う。
