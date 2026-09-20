# G1–G4 ベース設計統合レビュー

対象revision: `82e59f6e13fde8f6582f538da24b7523854c2cde`（レビュー開始時の公開main）。
対象はG1〜G4であり、仕様11〜14のレビューではない。
状態: 要改善。既存のG1–G4一括完了判定は、本レビューの証拠に照らして維持できない。
方法: Astra独立レビューと主担当によるソース照合・回帰・設計validator実行。実装変更なし。

## 結論

共通化の方向は妥当だが、ベース仕様08の「配置済みSceneをrendererが消費する」境界まで統合されていない。
関数が存在することと、公開出力で設定が有効なことを同一視した完了判定が主要因である。
特にG4は計算器までで、独立レーンの可視化は未接続。G3にもpurpose別契約の未実装が残る。
164件のテスト成功は既存ケースの回帰証拠であり、仕様29〜31の網羅的適合証明ではない。

維持する点: Date-only軸・比較mark・設定解決・配置候補・lane割当の純粋関数化、Actualの計画代替禁止、
Theme/Detail/Layoutのauthoring所有権、固定参照検査、既存サンプル回帰。全面書き直しは不要。

## 実行した検証

| 検証 | 結果 | 解釈 |
|---|---|---|
| `PYTHONPATH=src python -m pytest -q` | 164 passed、既存警告2件 | 既存ケースのみ |
| `validate_presentation_g2_g4_design.py` | line 23 AssertionError | 削除済みnegative診断がexpectedに残存 |
| `validate_shared_presentation_foundation.py` | 成功 | wireの構造検査 |
| `validate_presentation_settings.py` | 2 schemas / 4 positive / 15 negative / 82 inventory groups成功 | 文言どおり設計構造のみ |
| 本文なしhighlightのbox投影 | `E_PRESENTATION_LABEL_INPUT` | 装飾だけのpurposeに本文計測を要求 |
| source/target付きexplanatory-arrowのanchor解決 | `E_PRESENTATION_ANCHOR_UNSUPPORTED` | 二端点入力がsingle anchor処理へ渡される |

実行Pythonは隣接chrona作業環境のvenv、import先は上記固定revision。テスト数以外は静的証拠か明示した直接probeであり、画像による全面QAは未実施。

## 指摘一覧

P0 = 完了・設計承認を妨げる問題。P1 = 宣言済み機能／構造の修復が必要。P2 = 拡張時の変更局所性・検証性を改善するもの。

| ID | 優先度 | 指摘と証拠 | 影響／対応 |
|---|---|---|---|
| R01 | P0 | `presentation_scene.py:15–22`は軸・意味mark・laneだけ。`gantt_surface.py:78–383`が計測、配置、purpose解釈、routingとSVG生成を実施。仕様08 §3/5/7と30 §2に不一致 | 共通Sceneは未完成。配置済みprimitiveと出所をSceneへ集約し、rendererを直列化に限定 |
| R02 | P0 | `lane_stack_offset`は`presentation_lanes.py:83`で定義されるが呼出はtestのみ。SVGは`lane_tracks`を消費せず`gantt_surface.py:219–309`で常に1項目1行 | independent-lane-track設定が可視化されない。G4.2完了判定を再開し公開SVGまで接続 |
| R03 | P0 | validator line23が実際に失敗。仕様31はrow-aligned metadata保持へ変更したがsettings/wire/preset schema説明は「stack 0 only」のまま | 仕様・schema・fixture・レビューの同時閉鎖が未達。設計検証を通常CIの必須ゲートへ |
| R04 | P0 | `presentation_annotations.py:64–99`は全purposeにsingle anchorとtext boxを適用。`gantt_surface.py:357–382`も同じ処理 | highlightと二端点説明矢印を正しく描けない。purpose別の閉じた型と投影に分離 |
| R05 | P1 | `gantt_surface.py:238–254,307–308,378–380`にbody/point中心と固定offset。`obstacles if b != own`は所有者IDでなく座標一致除外。resolverは候補の先頭を選択 | 他markの誤除外、内部portによる経路不能、複数slotで誤接続。slot/source/facet/purpose付きgeometry IDと形状由来portへ |
| R06 | P1 | `presentation_marks.py:39`で比較modeによってplannedをbaselineへ改名。anchor resolverはplanned/actual完全一致。point ActualはSceneにあるがganttのpoint分岐はplannedだけ | 見た目変更で参照が壊れ、実績を落とす。semantic facetとvisual roleを分離し、全公開adapterで同じmarkを消費 |
| R07 | P1 | `presentation_scene.py:37–44`のLaneItemはplanned日付のみ。required label/actual/point記号幅未投入。pointを1日占有へ変換 | 画面上の衝突を時間区間だけでは判定できない。共通scale上の測定済み占有を使い、pointの日付意味を変更しない |
| R08 | P1 | `gantt_surface.py:314–321`はmonth/quarterのみ描画。設定にweek/dayを許容。月表示とscale/row寸法もadapterで再計算 | 軸primitive生成済みでもG1の公開表示未達。band bounds/labelを共通Sceneに確定 |
| R09 | P1 | Ganttは`resolve_font_metrics`をweight省略で一度選択。太字出力にも同じ計測。actualHeight、point size、maxCandidates等の設定未消費、固定4/5/9/12/17などが残る | schema受理と出力の不一致。roleごとに計測と描画を共有し、全設定の変異テストを追加 |
| R10 | P1 | annotation routeはlimitだけ受け取りclearance/gridOffset/portOffset/bendPenaltyを消費しない。既存dependency routerは別実装。解なしをlimit超過と同じ診断にする | 共通routing方針が分裂。探索核を共有し、sourceKind別policyと失敗理由を保持 |
| R11 | P2 | Scene primitiveのstable sceneId、slot instance、input manifestとの統合が不十分。source_refだけでは複数primitiveを区別できない | Reactive UIや別backend追加で再実装が増える。仕様08/09のScene identityへ統一し、差分の局所性を検証 |
| R12 | P1 | `gantt_surface.py:122–124`はslotのsourceでなくtable/timeline等のキー名に依存。`:339`はv0.2でも旧profileでroutingを制御。`:356,387–391`はannotations slotを使わず、Project注釈をnotesへ別列挙 | 正規化した設定・View選択を迂回する経路が残る。sourceによるslot解決とcapability検証を前段へ統合 |

Astra独立レビューもR01/R02/R04を完了阻害と判定した。Astra側の指摘はコード追跡であり、上記の実行結果は主担当が同じrevisionで確認したもの。

## レイヤー整合評価

| 境界 | 評価 | 設計で確定すべきこと |
|---|---|---|
| Core/Schedule → View Projection | 独立性を維持する方針は良い | 表示modeで意味facetを改名しない。新たな日付補完は禁止 |
| View/Style/Theme/Detail/Layout → resolved input | 所有者分離はあるが出力まで未徹底 | 設定の唯一の消費者と適用範囲を一覧化 |
| resolved input → geometric Scene | 最大の欠落 | 測定・配置・routingを完結し、adapterに日付やViewの再解釈を要求しない |
| Scene → SVG / 他backend | Gantt/review/minimalで機能差 | 同一primitiveとcapability検証。legacyを別境界に隔離 |
| schema → fixture → test → 完了判定 | 不一致を検出できない | validator成功だけでなく、宣言した設定がgeometryへ作用する証拠 |

## 拡張性と考慮漏れ

「共通化」は新しい万能DSLや任意プラグインの追加ではない。既存primitiveと測定結果の共有を優先する。
重点の組合せは、Actual欠損／point Actual、baseline表示＋planned anchor、複数slotの同一object、長い日本語・太字、
mark同座標・必須label衝突、lane高さ不足、route探索限界、全公開SVG経路である。
G4のlabel配置とstack割当も循環し得るため、単にannotation boxを除外するだけで停止性を証明した扱いにしない。
局所座標で有限候補を評価してからstackを確定する等の規範的手順を先に設計する。
track pitchはbarだけでなくpoint・必要textの縦extentを包含する必要があり、現行式のmarkExtentの定義を閉鎖する。

## レビュー範囲の限界

Core全体のStable昇格、DateTime/DST、capacity、Federation等の完了判定は今回の対象外。
古いSTATUSを根拠にそれらが未実装と断定しない。本書の指摘はG1–G4と接続先に限定する。
対応順・受入条件は[改善計画](../planning/g1-g4-integration-remediation-2026-09-20.md)に示す。
