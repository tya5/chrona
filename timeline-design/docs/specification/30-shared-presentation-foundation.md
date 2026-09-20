# 共通表現基盤：採用境界と注釈の一般化

**状態:** D1/D2設計完了。ランタイム是正は未実装。
**根拠:** ADR-0019。既存仕様06/07/08/27/28/29を置き換えず、追加実装の採用境界を定める。

## 1. 目標と非目標

一つの計画から、表形式、バー付近のラベル、ゲート説明帯、チーム別レーンを、
共有機構の組み合わせとして構成する。画像生成案のピクセル再現は完成条件ではない。
任意図形エディタ、汎用制約言語、自由なスクリプト式、専用パネルの増殖は対象外。

## 2. 所有権と共通機構

| 関心事 | 正本・責務 | 禁止する重複 |
|---|---|---|
| 日程・実績・差分 | Project / Schedule / Actual / View Projection | レイアウトで日付・差分を再計算しない |
| 表示対象・グループ・注釈本文と論理参照 | View、意味注釈はProject | Layoutで独自に対象抽出しない |
| 事実から意味ロールへの対応 | Style | 色から状態を逆算しない |
| 色・線・文字・箱の装飾 | Theme | 注釈専用の独立テーマ系統を作らない |
| 文言・許可された書式 | Detail | renderer内の独自テンプレート言語を作らない |
| 領域・寸法・配置制約・探索方針 | Layout、既存Scene profileと正規化 | Viewにpixel座標を持たせない |
| 文字と記号の計測入力 | family×weightごとの明示Render Context固定資産 | 通常字体で太字を代用しない |
| 具体的な形状・位置・接続・出所 | Scene | SVG adapterで再配置しない |

共通の内部構成要素は、意味データを複製する新しい永続リソースではない。

- 時間スケール：Viewの期間から座標を計算し、複数領域が同じscaleを参照する。
- マーク：span/pointと計画/実績facetから形状と接続portを導出する。
- テキスト領域：本文を計測し、折返し、bounds、baselineを一度だけ確定する。
- アンカー解決：安定IDとfacet/endpointを投影済みの形状・portへ対応付ける。
- 配置：共通の領域境界・障害物・候補選択を適用する。
- 接続：依存線、注釈の引き出し線、説明矢印が経路探索機構を共有する。
  sourceKind、意味、可視性、端点規則、アクセシビリティは別々に保持する。

上記を組み立てる唯一の派生DTOを`ResolvedPresentationInput`と呼ぶ。DTOは
`semanticFacet`、`visualRole`、`slotId`、`projectionInstanceId`、測定要求、解決済み
Layout/Theme/Detail/Context、surface slot bounds、row bounds、lane track boundsを保持する。`projectionInstanceId`は
`slotId + sourceRef + semanticFacet + primitivePurpose`から決定的に導き、Scene primitiveの
`sceneId`はこれを接頭辞として用いる。visualRoleはfacetを上書きしない。同一objectを複数slotへ
投影してもinstanceは衝突せず、同座標の異なるfacet/roleも併合しない。DTO、測定結果、Sceneは
すべて派生物であり、ViewまたはLayoutへ永続化しない。

`content` region/trackの寸法は、上記テキスト領域などが確定した後に生成する一時の
`intrinsicBlocks` / `intrinsicTracks` 入力である。これをLayout又はViewへ永続化しない。
同じ入力closure・font asset・locale・Scene候補順なら同じintrinsic値となることを
受入条件とし、未計測値を固定pixel値へフォールバックしない。

## 3. 吹き出しの一般化

吹き出しを新しい特殊部品として導入しない。既存注釈を以下の構成へ投影する。

| 構成 | 役割 | 他の用途 |
|---|---|---|
| 対象参照 | どの項目・facet・端点を指すか | バー名、終了日、差分ラベル |
| テキスト領域 | 本文・許可書式・計測結果 | 表セル、凡例、ゲート説明 |
| 配置制約 | 対象の上/下/前/後、配置可能領域 | ラベルの外置き、説明帯 |
| Theme装飾 | 背景・枠・余白を持つ見た目 | 無枠ラベル、枠付き注記 |
| 任意の引き出し線 | 本文と対象の視覚的対応 | 日付注記、マイルストーン説明 |

最小受入用途は、(a)作業の実績終了端点に結び付いた注記、
(b)計画ゲートを別の説明領域から指す注記。同じ機構で両方を扱うこと。
説明帯は通常の領域にViewが選択した注釈を配置する合成であり、別の事実源ではない。

### 3.1 限定範囲

初期実装は既存選択済みobjectのspan/pointを対象とする。本文は既存Viewの
注釈文字列、または許可済み事実ソースの書式化結果である。遅延原因を推論しない。
関係・グループ・時間座標アンカーは既存仕様が定める概念として保持するが、
未対応の入力は診断し、objectへの曖昧な代替はしない。

矩形本文領域＋任意の直交leaderで十分な用途だけを採用する。漫画的な尾、
複数対象を一つの注釈から指す線、任意画像の埋め込み、手動waypointは初期範囲外。
本文と対象が接している場合に線を省略できるか等も、暗黙判断でなく明示policyにする。

### 3.2 参照と意味

- planned/actualのfacetを明示して解決する。実績アンカーが欠けた場合に計画へ移さない。
- Viewの`finish`とScheduleの`end`は意味対応表で正規化する。文字列一致で処理しない。
- 選択外の対象へ勝手に線を伸ばさない。境界表現は既存View契約で明示された場合だけ。
- Project意味注釈とView局所注釈は配置機構を共有するが、出所・編集対象は別である。
- 同一対象を複数slotへ投影する場合、sceneIdにはslotの安定IDを含める。
  接続先の投影インスタンスが曖昧なら診断し、最初に見つかったものへ接続しない。
- 注釈を削除・移動・装飾しても日程・Actual・dependency集合は変わらない。

### 3.3 配置と失敗の処理

1. 入力閉包・参照・capability・所有者を検証する。
2. 共有時間スケールと基礎マークの形状・bounds・portを確定する。
3. 計測資産で本文を測り、ラベルを含む必要領域を作る。
4. sourceの安定順と明示された候補順で、有限の配置候補を評価する。
5. 確定した文字領域を障害物に含め、意味別policyで接続線を解く。
6. 必須内容・境界・線端・アクセシビリティ・出所を検証してSceneを出力する。

基本マークを注釈に合わせて時間方向へ移動しない。線を置いた結果から本文を
無制限に再配置する循環探索は初期実装で行わない。必要な解が見つからない場合は
配置不能・経路不能の診断を返す。合法な配置が存在するすべての図を解けるとは保証しない。
文字の隠蔽、勝手な縮小、アンカー切断、入力にない説明領域の追加で救済しない。

仕様06の旧「希望側→above/below/end/start」は互換移行で明示候補順へ展開する。
新しい設定と旧profileの両方から探索順を採用しない。候補生成・探索上限・tie-breakの
アルゴリズム版は固定する。最終的な候補生成と診断IDは設計ゲートで確定する。

## 4. 他の候補機能への適用

- Aの週軸：既存axis契約の実装。暦の週境界・localeとラベル密度を閉じる。
- Dの近接ラベル：共通テキスト領域・アンカー・配置の最初の利用先。
- Bの説明帯：共通領域＋共有scale＋選択されたpoint＋注釈として合成。
  View選択とDetailのmilestones一覧の重複権限はschema変更前に解消する。
- Cのレーン：仕様06のstable stackingを具体化し、文字領域を含む占有判定を検討する。
  1項目1行とレーン内積み上げの違いはLayout方針とし、別rendererにしない。
- チーム色：安定group参照と意味ロールの組でThemeを解決する。
  source IDに基づくデータ上の指定は許容するが、renderer内のID分岐は禁止する。

## 5. 設計整合レビューと実装ゲート

| 既存契約 | 確認結果 | 実装前に閉じること |
|---|---|---|
| 06 View §9 / View schema | 既存注釈と論理的placementを再利用可能 | facet、endpoint正規化、旧入力移行、非対応anchor診断 |
| 07 Style / 29 Theme | 意味ロールと具体的装飾を分離可能 | group×facet色の所有者と解決優先順位 |
| 08 Scene §5–6 | Rect/Text/Path等で合成可能 | 投影インスタンスIDと共通内部IRへの接続 |
| 27 Layout | slot/regionで説明領域を構成可能 | scale共有、内容寸法依存、候補生成、制約のschema |
| 28 Detail | point説明の意図は既に存在 | View選択とmilestone一覧の単一正本化 |
| 29 settings | 計測・決定性・非暗黙fallbackと整合 | legacy除外と全経路完了条件の矛盾、二重所有禁止の適用 |
| 現行gantt | 共通機構の利用先にできる | 直接SVG内の計測・配置・経路処理をScene構築へ移す |

現行の注釈コマンドは入力検査が限定的であり、受理されたことを描画可能性の証明にしない。
wire schema・正負fixture・互換性行列・診断catalog・受入条件を本節以降で閉じる。

## 6. v0.1 wire 契約と将来の所有リソース

`schemas/shared-presentation-foundation-v0.1.schema.json` は、G1で既存の
View/Theme/Detail/Layoutへ分配される値の**設計検証用wire契約**である。永続的な
第二authoring resourceでもrenderer入力でもない。実装で一つのJSONを読むことを
認めない。fixtureは同schemaで検証する。

| wire区分 | v0.2での唯一のauthoring owner | 移行先 | rendererが読む値 |
|---|---|---|---|
| `scale` | Layout | `layout.axis` と `layout.scale` | 解決済みLayoutのみ |
| `marks.comparisonModes` | Layout | `layout.bars.comparisonMode` | 解決済みLayoutのみ |
| `marks.pointKinds` | Theme | pointのplan/actual/baseline symbol定義 | 解決済みThemeのみ |
| `facetColors` | Theme | `groupPaints`ではなく`facetPaints[groupId][facet]` | 解決済みThemeのみ |
| `labels` | Detail（本文）＋Layout（候補・overflow） | `detail.labelRules`、`layout.labelPlacement` | 解決済みDetail/Layoutのみ |
| `annotations` | View（本文・anchor）＋Layout（候補）＋Theme（box/leader） | 既存View annotations、Layout/Theme追加 | 解決済み三者のみ |
| `lanes` | Layout | `layout.lanes` | 解決済みLayoutのみ |
| `routing` | Layout | `layout.routing` | 解決済みLayoutのみ |

`groupPaints` はグループ背景用の既存契約として残す。計画/実績のグループ別色を
追加する場合、同一group keyのmapで背景とfacetを混在させない。全groupに色を
要求しない。解決順は `Theme.facetPaints[group][facet]`、次に
`Theme.facetPaints.default[facet]`、最後に既存のglobal facet paintである。
これは完全なresolved Theme内で確定し、rendererはID分岐を持たない。

## 7. 規範的な表示・配置規則

### 7.1 時間軸

- Date-only v0.1のweekはISO-8601週、月曜日開始、ラベルは`YYYY-Www`である。
  localeは月名等の文言に使うがweek startを暗黙に変えない。
- `levels`は粗い順（quarter, month, week, day）に一意に列挙し、`bandHeights`は
  同じ個数でなければならない。未対応level、順序違反、重複は診断する。
- `tickUnit`と`tickStep`はgrid cadenceだけを定める。band labelを消して時刻の意味を
  変更しない。minorVisible=falseでも必要なaxis labelを黙って消さない。
- 全slotが同じ`scaleId`を参照する場合、同じView windowとpaddingから同じdate→xを
  導く。slotごとのx origin/widthは異なってよいが、同じdateは各slot内で同じ正規化
  位置を持つ。scale共有を要求したslotが異なるwindowを要求した場合は診断する。
- spanは常に`[start,end)`、pointは`at`に投影する。人間向けの終端表示だけが
  `end - 1 day`を使える。geometry・差分・dependency端点は変えない。

### 7.2 計画・実績・差分

`comparisonMode`は`stacked`、`overlaid`、`baseline-and-actual`だけを初期値とする。
stackedは同じrow内の別band、overlaidは同じcenterline上のz-order別mark、
baseline-and-actualは計画を細い基準mark、actualを主markにする。いずれもActualが
なければ計画をactualとして描かず、`missingActual` policyだけを適用する。

point ActualはActualの`at`が存在する場合にのみpoint markを出す。span Actualは
start/finishが揃った場合にのみspan markを出す。片端だけの観測は既存facetに従い
テキストまたはpatternで表示し、開始/終了を推測しない。終了差分はactual finishと
planned endのcalendar-day差であり、負、0、正を別roleで表現できる。0の可視化は
`showZero`に従う。actualHeight、point size/shape、variance marker幅はThemeの値を
必ず消費する。

### 7.3 ラベルと注釈

label ruleは本文source、対象facet/endpoint、候補side順、必須性、overflow policyを
持つ。本文はtitle、閉じたdate formatter、comparison delta、または既存annotation
textだけであり、任意式を評価しない。placement候補は最大16個で、source順、rule順、
候補順、stable source IDで解く。`inside`は対象markのtext boundsが収まる場合だけ合法。

View annotationは既存のtyped anchor/purpose/textを維持する。`callout`/`note`は
box/leaderを要求または禁止するTheme/Layout policyを受けるが、自由なtail形状を
持たない。`highlight`は本文を必要としないmark周囲の装飾として別primitiveにし、
leaderを出さない。`explanatory-arrow`は既存source/targetの二anchorだけを使用し、
semantic dependencyと同じpath型を使ってもsourceKindを混同しない。

anchorのendpoint正規化表は次の通りである。

| View endpoint | planned span | actual span | point |
|---|---|---|---|
| `start` | planned.start | actual.start（存在時のみ） | 不可 |
| `finish` | planned.end | actual.finish（存在時のみ） | 不可 |
| `at` | 不可 | 不可 | planned.at / actual.at（facet明示時のみ） |
| `body` | mark bounds center | mark bounds center | symbol center |

`finish`はProjectの`end`に正規化する。actual欠測をplannedに代替しない。関係・
group・temporal anchorのv0.1入力は保持するが、G3初期ではobject以外を
`E_PRESENTATION_ANCHOR_UNSUPPORTED`で拒否する。これにより曖昧な描画を導入しない。

### 7.4 レーン、障害物、経路

View groupとorderが論理lane順を決める。各itemは確定mark boundsに、必須label boundsを
加えた占有範囲が重ならない最小stack indexへ置く。同一開始位置はstable object IDで
決める。maxStackを超える、またはlabelを入れられない場合はoverflow診断であり、
無関係なgroupへ移動しない。

lane surfaceはLayoutの`lanes.surface`で明示する。既存table/timelineの行対応を保つ
`row-aligned`は1項目1行の既存surfaceであり、各markをその項目行へ描画する。このsurfaceではstackIndexを再配置の入力にせず、Scene metadataとして保持する。複数stackを一つの論理lane内で可視化するのは`independent-lane-track`だけが担う。このsurfaceはView groupごとに
一つの派生trackを持ち、track内の`stackIndex`を縦offsetへ一対一に変換する。`pitchPolicy`
`scene-mark-extent-plus-clearance`はSceneが解決済みThemeの比較mark block extentとLayout routing
clearanceから一意のpitchを導く。track高は`2 * trackPadding + markExtent + maxStackIndex * pitch`、
lane間隔は`trackGap`である。tableが併置される場合でもrow対応を暗黙に維持せず、別slotとして
扱う。adapterはこの派生geometryを再順序化・再計算しない。

dependency、annotation leader、explanatory arrowはいずれも有限の直交visibility gridを
使える。しかしsourceKindごとにstroke layer、端点、意味、アクセシビリティを保持する。
必須mark/本文/box/arrowheadは障害物であり、path同士は障害物にしない。探索は
gridOffset、clearance、portOffset、bendPenalty、limitとstable tie-breakを明示入力と
する。limit超過または解なしは`E_CONNECTOR_UNROUTABLE`である。

## 7.5 D2 幾何・目的別投影アルゴリズム

Scene Builderは次の有限順序でのみ投影する。後段が前段を再解釈・再測定することはない。

1. Layoutのregion/track solverから、選択された公開surface instanceごとのtitle、timeline、axis、ordered row、lane trackのboundsを作る。`table-timeline`、`review`、`minimal`は別instanceであり、同じscaleを共有しても座標を共有しない。
2. 一つのDate scaleからaxis band、tick、各surface slotのdate-to-x変換を作り、mark/Text/Pathの完成boundsへ反映する。
3. semantic facetを保ったmark boundsとshape由来portを作る。
4. `TextLayout {bounds, baseline, lines, family, weight, assetIdentity}`を一度だけ測定し、label、障害物、SVG Textが同一値を使う。
5. 必須labelを含むmark occupancyからstable lane stackとtrack boundsを作る。
6. annotation purposeごとにprimitive候補を作り、確定済み障害物に対して有限routeを解く。
7. sceneId、sourceKind、bounds、z-order、manifest、diagnosticsを確定して出力する。

axis bandは`(scaleId, level, naturalInterval.index, slotId)`、markは`(projectionInstanceId, facet, markRole)`、Textは`(projectionInstanceId, textRole)`をidentityに含める。slotは同じscaleを参照しても独立したinstanceを持つ。adapterはband高さ、x/y、baseline、track、routeを再計算しない。特にreview/minimal adapterは設定のmargin/dayWidth/row heightや投影列順から座標を再構成せず、選択surface instanceの完成primitiveだけを直列化する。

| purpose | 許されるprimitive | anchor | 禁止 |
|---|---|---|---|
| callout / note | Text + Rect + optional Path leader | object 1個 | leaderをsemantic dependencyへ変換 |
| highlight | Rect / Symbol decorationのみ。本文・leaderなし | object 1個 | text boxを要求、anchor推測 |
| explanatory-arrow | Path + arrowheadのみ | source/target object 2個 | single-anchorへの縮退 |

object portは`start`、`finish`、`at`、`body`のいずれかで、span/pointの形状境界から導く。port、obstacle、primitiveはsourceRefだけでなくprojectionInstanceIdで識別する。box候補時だけ当該annotationのanchor markを除外できる。routeでは全mark、必須label、既定annotation boxを障害物に復帰し、source portから外向きの最初のsegmentだけ境界接触を許す。同座標の別object/slot/facetを除外してはならない。

occupancyは測定済みmark boundsと必須TextLayout boundsの和集合である。pointを一日spanへ意味変換してはならない。`row-aligned`はstackをmetadataだけに保ち、`independent-lane-track`は`trackPadding + stackIndex * pitch`を唯一のy offsetとして使う。`pitch = markExtent + routing.clearance`、`trackHeight = 2*trackPadding + markExtent + maxStackIndex*pitch`である。不足、maxStack超過、必須label不能は`E_PRESENTATION_STACK_OVERFLOW`で停止する。

routeは`gridOffset`、`clearance`、`portOffset`、`bendPenalty`、`limit`を全て入力にし、座標・方向・bend数・stable IDでtie-breakする有限visibility gridである。state数がlimitを超えた場合は`E_PRESENTATION_ROUTE_LIMIT`、探索完了後に経路が無い場合は`E_CONNECTOR_UNROUTABLE`である。両者を同じ診断へ潰してはならない。

## 8. 移行と二重指定

v0.1 Viewのannotationsは論理anchor/textとしてそのままv0.2 Viewに移す。v0.1
`layoutIntent.itemStacking: stable`は`layout.lanes.stacking`へ一方向移行する。
v0.1 Scene Profileのrouting/collisionはv0.2 Layoutに移し、同一render closure内で
両方を受理しない。旧profileと新Layoutが注釈候補、scale、routing、lane stackingを
二重指定した場合は`E_PRESENTATION_DUPLICATE_AUTHORITY`で拒否する。

v0.2 Detailに既に存在する`milestones`面は、View-selected point object IDだけを
表示する派生surfaceとして残す。説明帯はDetail独自の座標や本文を持たず、View
annotationをannotations slotへ投影する。Detail milestonesとView annotationsが同じ
pointを参照しても別primitiveであり、統合・重複除去を暗黙に行わない。

仕様29のlegacy adapterはG1完了まで保持する。legacy出力はv0.2 Layout/Theme/Detail/
Scene経路と混ぜず、`E_PRESENTATION_LEGACY_ADAPTER`を必ず出す。新機能はlegacy
rendererに追加しない。

## 9. 診断と設計fixture

| ID | 条件 | 禁止される救済 |
|---|---|---|
| `E_PRESENTATION_AXIS_INVALID` | levels/bandHeights、順序、week設定が不正 | 暗黙のmonth軸 |
| `E_PRESENTATION_SCALE_MISMATCH` | 共有scale slot間のwindow/scaleが不一致 | 片方を勝手に採用 |
| `E_PRESENTATION_ANCHOR_UNSUPPORTED` | 初期範囲外anchor | objectへの曖昧な置換 |
| `E_PRESENTATION_ANCHOR_MISSING` | facet/endpoint/投影instanceが存在しない | plannedへの代替 |
| `E_PRESENTATION_LABEL_UNPLACEABLE` | 全候補で必須textが置けない | 縮小・隠蔽・切断 |
| `E_PRESENTATION_STACK_OVERFLOW` | maxStackまたは独立lane track boundsを超える | group移動・重なり |
| `E_PRESENTATION_DUPLICATE_AUTHORITY` | 旧新policyの同時指定 | merge・暗黙優先 |
| `E_CONNECTOR_UNROUTABLE` | 有限探索でleader/dependencyが解けない | freeform path |

`fixtures/shared-presentation-foundation-v0.1.json`はowner、週軸、比較mark、
ラベル、object annotation、stable stacking、sourceKind別routingを検証する。
`shared-presentation-foundation-invalid-v0.1.json`は順序違反・非ISO週開始を含み、
schemaが否定することを確認する。validatorはruntimeではなく設計fixtureの整合だけを
確認する。実装開始時には各診断の正負fixture、二プロジェクト、長い日本語、実績欠測、
再現性を追加する。
