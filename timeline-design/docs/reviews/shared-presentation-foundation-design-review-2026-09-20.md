# 共通表現基盤 G0 設計整合レビュー

**結論:** G0の設計は実装開始可能な水準で閉じた。実装完了ではない。

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
