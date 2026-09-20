# I3 公開surface adapter 完成計画

**状態:** 設計閉鎖中。I3-A実装は、この計画・仕様08 §5.3・派生fixture・設計レビューを公開し、
矛盾がないことを確認してから開始する。

## 目的

`table-timeline`、`review`、`minimal` の各SVG adapterを完成Sceneの直列化器に限定する。adapterが
日付、行順、slot、余白、font計測、lane、route、文言、比較facetを再解釈する経路を段階的に撤去する。
これは新しいrendererやauthoring形式を追加しないI3是正である。

## 設計済み入力・出力境界

入力は仕様08 §3.3の一つの `ResolvedPresentationInput` だけである。Scene Builderは公開surfaceごとに
slot/row/group/trackと、`sceneId`、`projectionInstanceId`、`surfaceId`、purpose、source、facet、role、
bounds、Text payload/baseline、z-orderを持つprimitiveを出力する。adapter入力は選択した
`SceneSurface`、解決済みtoken値、target capabilityだけであり、Project、Schedule、View、settings、
投影item列を受け取らない。

同一`scaleId`は正規化時間位置だけを共有する。surface間のorigin、width、dayWidth、row height、
title/axis/timeline boundsを共有してはならない。欠損は次の診断で停止する。

| 欠損 | 診断 | adapterの禁止救済 |
|---|---|---|
| named surface | `E_PRESENTATION_SURFACE_MISSING` | 他surfaceの選択、settingsからの生成 |
| slot / row / required primitive | `E_PRESENTATION_PRIMITIVE_MISSING` | margin/dayWidth/row順からの補完 |
| facetが投影不能 | 既存のfacet/anchor診断 | plannedへの代替 |

## 全移行順と公開境界

| 単位 | Scene Builderの責務 | adapterから撤去する責務 | 受入条件 | 公開 |
|---|---|---|---|---|
| I3-A | surface primitive DTO、identity、title/axis/tick/mark/item-label投影 | なし。contract testのみ | 3 surfaceで同じsemantic入力が別のsurface geometryを持つ。facet欠損を捏造しない | 設計公開後に実装単独公開 |
| I3-B | I3-A core primitiveの全surface実体化 | なし。Sceneの完成性を検証 | axis/mark/Textがsurface primitiveとして一意、row/slot不足は診断 | 単独公開 |
| I3-C | table/group/cellとdependency/annotation/legend/summary primitive | table-timelineの座標、計測、route、文言生成 | Ganttは全primitiveを直列化するだけ | 単独公開 |
| I3-D | review向けI3-A core primitiveを消費する選択API | reviewのdate→X、row→Y、axis/tick/mark/title/item label計算 | settings/item列なしで同一SVG意味値を出す | 単独公開 |
| I3-E | minimal向けI3-A core primitiveを消費する選択API | minimalのdate→X、row→Y、axis/tick/mark/title/item label計算 | settings/item列なしで同一SVG意味値を出す | 単独公開 |
| I3-F | 未移行のreview/minimal connector、annotation、summary及びtableとの差分primitive | 上記残存のprivate geometry | 全3 surface adapterにgeometry計算がない | 単独公開 |
| V1 | input manifest、structural/behavior/image evidence | 完了根拠の推測 | 設定変異、Actual欠損、point、複数slot、長文、lane、routeを全経路で検証 | I3完了公開 |

### I3-C〜I3-F 完全設計閉鎖

I3-Cは`table-timeline`だけを対象に、table frame/header/column、group/row、table cell、semantic
dependency、View annotation、project note、legend/coverageをScene primitiveへ移す。各table cellのidentityは
`(table-slot, objectId, columnId, table-cell)`、connectorは`(relationId, fromProjectionInstanceId,
toProjectionInstanceId, dependency-connector)`、annotationは`(annotationId, purpose, box|text|leader)`、
legendは`(legend-slot, role, swatch|label)`、coverageは`(legend-slot, coverage-text)`である。TextはI3-Bの
`TextLayout`を再利用し、port/route/obstacle/line wrapもScene Builderだけが確定する。

I3-DとI3-Eは新しいprimitiveを作らない。選択surfaceのI3-A/B coreだけを受けるserializerへreview、minimalを
それぞれ縮退する。I3-Fはその二surfaceのconnector/annotation/summaryと、未移行のsurface差分familyを同じ
identity規則で追加する。全unitで、slot不在・visibility `none`・source不在はoptional familyを出さず、
sourceが認可済みでrequired memberが無い場合だけ`E_PRESENTATION_PRIMITIVE_MISSING`で停止する。

z-orderは`background/frame → band/group/row → rule/tick → mark → label → connector → annotation →
legend/note → summary`に固定する。adapterは再ソート、date/row/port/route/text measurement、table wrap、
legend wrap、summaryの値・文言生成を一切行わない。この節、仕様08 §5.3、derived fixture validatorをI3-C以降
すべての実装前設計ゲートとする。

I3-BからI3-Fの実装中に、新しいprimitive family、identity入力、TextLayout、port、diagnostic、または
surface所有権が必要と判明した場合は、実装を停止する。仕様08、仕様30、派生fixture、設計レビュー、
この計画を同一の設計公開で閉鎖してから当該単位へ戻る。

### I3-B 再オープン：単一点表示window

初回I3-B実装で、標準baseの`singlePointSpanDays: 1`では、測定済みmonth labelとitem labelを
置けないことを検出した。これはadapter内の幅救済ではなくLayoutの表示window契約である。仕様29を
補正し、標準baseは7日を明示する。`presentation_scene_from_schedule`はこの値を表示windowに適用し、
不足時は`E_LAYOUT_REQUIRED_OVERFLOW:text`で停止する。I3-Bはこの設計公開を親にしてTextLayoutを
完成させるまで完了扱いにしない。

このbase fixture改訂ではpresetの`base.contentIdentity`も同じrevisionのSHA-256へ更新し、設計validatorが
実ファイルのdigestと照合する。参照同期が失敗した場合はI3-Bの実装検証へ進まない。

## 完了判定

1. adapterの関数シグネチャと依存グラフから、authoring resourceとsettingsを受け取らないことを示す。
2. surfaceごとに完成primitiveのidentity、bounds、Text payload/baseline、z-orderを構造検査する。
3. 3 surfaceの同一semantic inputについて、同一facetが保持され、surface固有geometryだけが異なることを検証する。
4. SVGの既存goldenに対する意味値・source ID・bounds検査と画像確認を行う。
5. 全回帰、presentation design validator、fixture validatorを通し、対象SHAと未移行範囲を記録する。

I3完了前に、metadataだけがScene由来でSVG geometryがadapter私有の状態を完了扱いにしてはならない。
