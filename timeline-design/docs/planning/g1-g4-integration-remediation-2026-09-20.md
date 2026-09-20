# G1–G4 統合改善計画

状態: 提案。実装修正は未着手。レビュー対象revision `82e59f6e13fde8f6582f538da24b7523854c2cde`。
根拠: [横断レビュー](../reviews/g1-g4-integration-audit-2026-09-20.md)。
本書は既存「G1–G4完了」に対する是正提案であり、新機能拡張計画ではない。

## 原則

すべての設計是正を先に完了・検証・公開し、その後に実装する。sample名による分岐は禁止。
既存の純粋関数を活用し、巨大rendererを小さな純粋な処理へ分割する。公開API互換は入口adapterで担保する。
Core・Store・Commandの意味論は変更しない。計画の承認は実装完了を意味しない。

## 優先順と依存

| 順序 | フェーズ | 対象 | 成果／終了条件 |
|---|---|---|---|
| 1 | D0 完了判定是正 | R01–04 | 計画・レビューの完了撤回、再現ケース登録、対象SHA固定、失敗validatorの原因記録 |
| 2 | D1 全体境界設計 | R01,06,11,12 | 仕様08/09/29/30/31の依存と責務を統一。semantic facet / visual role / slot instance / Scene identityを定義 |
| 3 | D2 全アルゴリズム設計 | R04–10 | purpose別注釈、port例外、占有・lane pitch・行対応、軸band、metrics、routing診断・有限停止性を確定 |
| 4 | D3 設計同期・横断検証 | 全件 | owner schema・wire・正負fixture・migration・受入表・reviewを整合。base hash参照も更新。未決定ゼロで設計ゲート承認・公開 |
| 5 | I1 共通Scene構築 | R01,06,08,09,11 | 意味markを保持したまま測定済みText/Rect/Symbol/Pathを生成。viewport/manifest/出所付き |
| 6 | I2 配置・lane・routing接続 | R02,04,05,07,10 | 独立laneの高さ・offsetを最終Sceneに反映。注釈purpose・port・routeを共通実装へ |
| 7 | I3 公開adapter移行 | R01,02,06,08,09,12 | Gantt/review/minimalが同じSceneを描画。日付・配置・文言の独自計算を撤去。legacy分離 |
| 8 | V1 受入・完了レビュー | 全件 | 構造検査＋振舞い＋画像＋不変条件を通し、実装根拠付きで初めて完了に戻す |

D0→D1→D2→D3が完了するまでI1を開始しない。各フェーズで対象差分をレビューして公開する。
実装中に未設計事項が判明した場合も場当たり修正せず、影響を受ける設計一式を閉鎖してから再開する。

## D0 実施記録

対象revisionは `82e59f6e13fde8f6582f538da24b7523854c2cde` と固定する。従前のG1–G4完了表記は、本計画と
`g1-g4-integration-audit-2026-09-20.md` が示すR01–R04により撤回した。再現条件は、同revisionで
`PYTHONPATH=src python timeline-design/docs/fixtures/validate_presentation_g2_g4_design.py` を実行すること。
fixtureから削除済みの `E_PRESENTATION_STACK_SURFACE_INCOMPATIBLE` をvalidatorの期待集合だけが保持していたため、
line 23のAssertionErrorとなった。fixtureを再追加して診断を捏造せず、validator期待集合を現行fixtureへ同期した。
この同期はR03の全体是正ではなく、D1–D3でowner schema・wire・正負fixture・受入根拠を閉鎖するまでG1–G4を再完了扱いしない。

## D1/D2 実施記録

D1で仕様08/09/29/30/31に`ResolvedPresentationInput`、semantic facetとvisual roleの分離、slotを含むprojection instance、Scene identity、adapter非再解釈を固定した。D2で仕様30 §7.5を唯一の有限投影手順とし、TextLayoutの一回測定、purpose別primitive、shape由来port、lane式、route limitとunroutableの診断分離を固定した。D3ではこの規則をschema、fixture、受入表、validatorへ同期する。I1はD3完了前に開始しない。

## D3 実施記録

wire schemaのrouting入力を`gridOffset`、`clearance`、`portOffset`、`bendPenalty`、`limit`へ閉鎖し、正負fixtureとvalidatorで検証する。row-alignedはstack 0制限を撤回し、Scene metadataとしてstackIndexを保持する。D1/D2で定めた境界と有限手順に対し、owner schema・wire・正負fixtureの矛盾は残さない。I1は仕様08/30の`ResolvedPresentationInput`から完成Sceneを構築し、adapterが意味・幾何を再解釈しないことを最初の受入条件とする。

## 提案する内部構造

1. 入力解決: View/Style/Theme/Detail/Layout/Contextの型・固定参照を検査し、source selectionを一度だけ決定。
2. 意味投影: semantic facetと観測値を保持。baseline等の視覚表現を別属性とする。
3. 測定: role・family・weight・locale・固定資産を受け、TextLayout（bounds、baseline、line、選択資産）を生成。
4. 幾何配置: scale、axis band、item row／lane、labels、annotationsを有限手順で確定。
5. 経路: 測定済みobstacleと形状portから有限経路を探索。dependency/leader/explanatory-arrowの意味はpolicyで分離。
6. Scene確定: primitive、stable identity、sourceKind、bounds、z-order、manifest、diagnosticsをimmutableに保持。
7. 出力: SVG等はprimitiveを直列化。日付計算・anchor選択・再測定・再配置を禁止。

既存`scene.py`と`presentation_scene.py`を無条件に並立させず、semantic入力DTOと幾何Sceneの役割を命名・型で区別する。
永続authoring形式を増やさない。typed internal DTOは派生データであり、Scheduleの第二正本にしない。

## 必須受入ケース

| 分類 | ケース | 合格条件 |
|---|---|---|
| G1軸 | quarter/month/week/day、clip、ISO年境界、複数slot | 全宣言levelのlabel/bandが出力され、共通scale上の位置が一致 |
| G1比較 | point Actual、片端欠測、baseline＋planned annotation | Actualを捨てず、補完せず、表示modeでanchor identityが変わらない |
| G2測定 | 太字、日本語、letter spacing、長文、maxCandidates変更 | 描画と衝突判定が同一TextLayoutを使い、探索数が契約どおり |
| G3purpose | note/callout/highlight/二端点arrow、leaderなし | 各purposeのprimitive構成・sourceKind・参照が一致 |
| G3port | body/start/finish/point、複数slot、同座標別mark | source IDに基づく除外。最初の出口segment以外で障害物内部を通らない |
| G4 | 重なるplanned/actual/必須label、point記号、group順 | 計測済みgeometryからstack決定。track高不足は診断、group移動なし |
| G4出力 | 同じprojectionでrow-alignedと独立laneを切替 | SVGのy座標とtrack背景が設計どおり変化。metadataだけの差を合格にしない |
| 全経路 | Gantt/review/minimal、設定変異 | サポート設定が出力に作用するか、明示非対応診断。無言無視なし |
| Reactive | 同一source複数slot、単一object更新 | sceneId衝突なし、無関係scopeの全再生成を要求しない |
| 検証 | 全design validators＋unit＋integration＋画像 | validatorを通常CIへ含め、golden更新前に意味値・source ID・boundsを検証 |

## 最終完了条件

- 各受入ケースを仕様節・schema path・実装symbol・test・出力artifactに対応付ける。
- ASTER/Controller Zに加えsample非依存ケースを用いる。入力Project/Schedule/Actual不変を確認。
- 画像差分を人間が確認できる形で保存し、golden再生成だけで合格にしない。
- 設定消費表に「消費済み／明示非対応」を記載し、未消費を完了扱いしない。
- 設計reviewと実装reviewを区別し、証拠・対象revision・未対応範囲を固定して公開。

全面刷新、自由座標DSL、個別sample用renderer、任意拡張framework、新しい時間モデルは本計画に含めない。
所要時間の精密な見積りはD3で変更面が閉じてから行う。現段階の最大リスクはScene移管に伴うAPIとgoldenの変更量である。
