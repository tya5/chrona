# 共通表現基盤 G2–G4 設計ゲート

**状態:** G2設計・実装済み。G3/G4のScene接続設計を是正中。G3/G4 visual実装は、この文書・owner schema・正負fixture・横断レビューが揃うまで開始しない。

## 1. 一意なauthoring所有者

| 値 | owner | renderer入力 | 禁止事項 |
|---|---|---|---|
| label本文source・テンプレート | Detail | resolved Detail | 任意式・renderer文言 |
| label候補・max候補・overflow | Layout | resolved Layout | object ID分岐・無限探索 |
| annotation本文・typed anchor | View | resolved View | pixel座標・手動waypoint |
| box/leaderのpaint | Theme | resolved Theme | 注釈専用Theme系統 |
| facet paint | Theme | resolved Theme | group背景とのmap混在 |
| lane group/stack/max | Layout | resolved Layout | rendererでのgroup移動 |
| route grid/clearance/limit | Layout | resolved Layout | sourceKindの意味混同 |

## 2. G2：ラベル・facet paint・axis slot

`detail.labelRules[]` は `{id, source, facet, endpoint, required}`、
`layout.labelPlacement` は `{candidateSides, maxCandidates, overflow}` を持つ。
sourceは`title`、閉じたdate formatter、`comparison-delta`、`annotation-text`のみ。
candidateSidesは最大16個で、source安定ID→rule順→候補順で評価する。`inside`は測定済み
text boundsがmark boundsに収まる場合だけ合法。必須labelが置けなければ
`E_PRESENTATION_LABEL_UNPLACEABLE`、optionalは`overflow`の明示policyに従う。

`theme.facetPaints` は`{default: {planned, actual, baseline, variance}, groups: {groupId: {...}}}`。
解決順はgroups[groupId][facet]、default[facet]、既存global roleであり、最後のglobal roleは
resolved Themeの正規化段階で必ず具体paintになる。rendererはこの順を再実装しない。

axis slotは`layout.slots`のsource `timeline-axis` を使い、timeline slotと同一`scaleId`を
要求する。異なるwindow又はscaleの共有は`E_PRESENTATION_SCALE_MISMATCH`で拒否する。

## 3. G3：注釈とleader

初期対象はViewのobject anchorだけである。既存Viewのtyped reference形式に合わせ、anchorは
`{kind: "object", id, facet, endpoint}`、facetは
planned/actual、endpointはstart/finish/at/body。actualが無い場合のplanned代替は禁止する。
relation/group/temporal anchorは入力を保持するが初期実装では
`E_PRESENTATION_ANCHOR_UNSUPPORTED`、対象facet/endpoint/投影instanceが無い場合は
`E_PRESENTATION_ANCHOR_MISSING`である。

annotation purposeはcallout/note/highlight/explanatory-arrow。callout/noteはrect boxと任意の
直交leader、highlightはboxのみ、explanatory-arrowは二つのobject anchorを持つpathだけを
許す。leaderはmax one source/target、手動座標・曲線・tail・waypointを許さない。
候補生成はlabelと同じ有限順、routeはLayout routingのlimitで停止する。

`theme.annotation` は `{boxFill, boxStroke, leader}` の三つのconcrete paintを持つ。boxの寸法・
候補side・leaderの探索上限はThemeに置かず、既存Layoutが所有する。purposeによる別Theme系統は作らない。

Sceneはannotationごとに`{annotationId, objectId, facet, endpoint, boxBounds, leader}`を出す。
boxBoundsは共有label配置器の最初の合法候補であり、leaderのbox側portはanchorに最も近い矩形辺の中点
（同距離は`above, below, end, start`順）とする。leaderはanchor portからbox portへの直交pathで、mark、
required label、確定済みannotation boxを障害物に含める。`routing.limit`はvisibility-gridで展開するstate数の
上限であり、超過は`E_PRESENTATION_ROUTE_LIMIT`。`highlight`はleaderを出さず、`explanatory-arrow`は二つの
明示object anchorが揃う場合だけ出す。facetを省略した既存View annotationは保存互換のためschemaで受理するが、
G3 Scene投影は`E_PRESENTATION_ANCHOR_MISSING`としplannedを推測しない。

## 4. G4：stable lane stacking

lane順はView group/order、同一laneの投入順は`(mark.start or mark.at, stable object ID)`。
各itemのoccupancyはmark boundsとrequired label boundsの和集合であり、最小の重ならない
stack indexを採用する。`maxStack`超過又はrequired label未配置は
`E_PRESENTATION_STACK_OVERFLOW`。別groupへの移動、暗黙の縮小、隠蔽は行わない。

Sceneは各投影markに`laneGroupId`と`stackIndex`を付加する。Viewのgroup/orderがlaneGroupId順を定め、
同一groupでは`(start or at, stable object ID)`順で割り当てる。adapterはstackIndexを縦offsetへ変換するだけで、
再選択・再順序化・別groupへの移動をしてはならない。

## 5. 設計完了チェック

G2–G4実装の前に以下を完了する。

1. 上記fieldを既存View/Theme/Detail/Layout v0.2 schemaへ配置し、wire schemaは対応表だけに保つ。
2. 各fieldのvalid/invalid fixture（候補>16、actual anchor欠損、group facet override、stack overflow、route limit）を追加する。
3. `E_PRESENTATION_*`診断の入力・owner・禁止救済をreviewで照合する。
4. sample固有ID/名称を持たない二プロジェクト受入例と、長い日本語/実績欠損の再現性を確認する。

これらが終わるまで、G2のlabel/facet paint、G3のannotation、G4のlaneのPython実装は行わない。
