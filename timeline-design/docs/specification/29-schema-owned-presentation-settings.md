# 表現固定値のスキーマ所有設計 v0.2

**状態: 設計契約。ランタイム未実装。**

## 1. 目的・対象

描画コードに残るデザイン上の選択をすべて宣言データへ移す。
対象は `gantt_surface.py`、`layout.py`、`review_svg.py`（旧レビュー・summary・
書式化ヘルパーを含む）、`render.py`（旧最小SVG）の全公開出力経路。
最新ガントのみを移行して旧経路の固定値を残すことは完了とみなさない。

正本は `presentation-settings-v0.2.schema.json` の各所有者 `$defs`。
固定値棚卸しは `../planning/presentation-fixed-value-inventory-v0.2.json`。
各項目はコード上の出所、移行先、型、代表値、除去方針を持つ。
78項目群にはフォントロール14種、色ロール13種、線ロール6種などを含む。
JSONファイルはYAMLと同じデータモデルの検証成果物であり、ユーザー入力はYAMLでよい。

「すべて」は全デザイン選択を意味する。日数差・暦・端点・アクセス可能性の意味、
XMLエスケープ、配列添字、中心座標の1/2、図形の正規化頂点などは、
デザイン値ではなく不変の計算規則である。設定によって意味や安全性を変更しない。

## 2. 一意な所有者と既存設計への統合

| 所有者 | 正本となる設定 | 統合・廃止対象 |
|---|---|---|
| View | 選択・順序・グループ・表示期間・列の事実ソース | 変更なし。Layoutにコピーしない |
| Style | 事実から意味ロールへの対応 | 変更なし。新設定の数値・文言を持たせない |
| Theme | 色、透明度、書体、サイズ、ウェイト、行間、字間、線幅、破線、角丸、記号寸法、パターン | `surface.fontSize/titleSize/groupFontSize/barHeight`、各adapterのfallbackを統合 |
| Layout | 領域・トラック・余白・整列・行高・列配分・軸帯高・バー間隔・障害物余白・経路評価・凡例flow | 名前依存のheader/footer分岐、density分岐、固定Rect、手動ベースラインを廃止 |
| Detail (`28`) | 凡例、説明、欠測文言、アクセシブル説明、書式、summary表示名 | `surface.groupLabel`とコード中の英語文字列を統合 |
| Render Context | 実際のviewport寸法・locale・固定されたフォント計測リソース | canvasの比率→寸法辞書を廃止。寸法の二重正本を禁止 |
| Output | SVG座標精度、フォント出力方針、overflow適合方針 | 出力adapterの固定精度や暗黙clipを廃止 |

`presentation-settings` の外側のobjectは検証・fixture用の集約形式であり、
新しい所有者ではない。各 `$defs/theme|layout|detail|context|output` は既存
リソースのv0.2 body内の `settings` に配置する。同じ設定を複数bodyへ書かない。
View/Styleの意味スキーマ、Project/Actual/Summaryの事実スキーマは変更しない。
Render Contextの旧 `viewport`・`evaluation.locale` と新settingsは同時に許可せず、
移行時に一度だけ移す。旧layoutMetrics refは `context.fontMetrics` に統合する。
ContextのasOfDateやrevision参照など、移動対象でない既存の値は保持する。

既存Theme token→role解決は、今回の具体値契約に正規化する前段として残す。
token alias/cycle/typeの検証後に完全なTheme設定を得る。schema対象のresolved設定
に未解決token文字列は残さない。Layout距離はLayout所有であり、Themeに重複保存しない。
Styleが生成したroleにThemeが未対応なら診断する。groupPaintsのキーは安定IDであり、
グループ数・タイトル・サンプル名による分岐は禁止。

## 3. 既定値・上書き・互換性

既定値はバージョンと内容hashで固定された**完全なYAMLプリセット**に置く。
schemaの `default` は実行時注入機能として使用しない。renderer内の
`get(..., 数字/色/文言)` による欠落救済は禁止。解決後の全項目がrequired。
継承順は「固定base → ユーザーoverride」のみ。objectはキー単位merge、arrayは
全置換、nullでの削除は禁止。未知フィールドはエラー。循環baseはエラー。
authoring schemaは `presentation-preset-v0.2.schema.json`。完全なsettings、または
固定base参照＋部分overridesのどちらか一方を許可する。array内の要素は完全な形を要求。
YAML例 `presentation-preset-override-v0.2.yaml` は日本語ラベル・角丸・文字・余白・
経路評価を上書きする。これは作者向け集約形式であり、解決後は各所有リソースに分配する。
現在のdefaults fixtureは設計例であり、フォント資産identityは説明用である。
実装時に実在する計測資産へ束縛するまでrender-readyと主張してはならない。

v0.1は変更せずに存続する。v0.2は明示的な移行・opt-inのみ。
旧 `surface` の値を同時に残すと `E_PRESENTATION_DUPLICATE_AUTHORITY`。
旧数値の移行先:

- fontSize → Theme typography.body/tableHeader/month、titleSize → heading、
  groupFontSize → group、barHeight → plannedHeight/actualHeight。
- groupMode/fraction/gap → Layout group、axisLevels → Layout axis.levels。
- barGap → Layout bars.gap、showVariance → Layout variance.visible。
- groupLabel → Detail groupLabel。旧固定凡例 → Detail legend。
- canvas aspectRatio → Context viewport寸法を明記したプリセット。
  margin/density名は移行時に既定設定へ展開し、runtime分岐に使わない。
- 旧最小幅920/960とデータ件数による自動canvas拡張は廃止し、移行adapterが
  明示Context viewportを受け取る。必要サイズが収まらなければoverflow診断する。
  v0.1の呼出形は互換presetで維持するが、自動拡張のpixel互換は保証しない。
- 明示された旧Context viewportと異なる旧canvas寸法を同時指定している場合は、
  勝手に片方を採用せず診断する。名前によるheader/footer寸法はregion.blockへ展開。

旧経路は最後に互換adapterとして同じresolved設定→Scene→SVGへ統合する。
旧出力の既知不具合はpixel互換の名目で維持しない。意図した変更はレビューに記録。

## 4. 計測・配置の閉じ方

文字幅推定の `.58`、ベースラインの `.34`、固定文字幅112/60/57は、
調整つまみに置き換えず**固定されたfont metricsによる実測**へ置き換える。
フォントのascent/descentとTheme lineHeightからbaselineを導出し、同じ計測結果を
折返し・overflow・障害物判定・SVGに使う。fallbackも宣言された順だけを用いる。
計測資産・fallback選択結果・locale資産のidentityをmanifestに含める。

region.blockはfixed/fraction/contentとmin/max。名前は意味を持たない。
fixed/contentの確定後、残りをfractionの重みで分割する。contentは計測済みの
intrinsic bounds。循環するcontent依存、min>max、負の残余は診断し、隠れた縮小はしない。
slotはregionとtrack indexを明示する。同じtrackの多重配置はoverlay以外で診断。
table/timelineは同じ行gridを共有。columnTracksが空の場合だけ等分配する。
表示時間はViewが決め、scale paddingは時間を追加せず描画余白だけを増やす。
単一point windowの表示用spanは設定できるが、意味上の日付を変更しない。

凡例は計測済みswatch＋label＋gapのflow。文字列ごとの150/145/220等の幅を廃止。
summary/notesも同じ測定flowに統合する。文字やデータが増えた場合は行折返し・
明示overflow規則を使い、外部パネルを勝手に生成しない。

経路評価のbendPenalty、clearance、portOffset、gridOffsetは宣言可能。
shapeに応じたport位置を算出し、端点種別start/end/atは必ず元relationを保持。
矢印寸法、stroke、文字領域を障害物判定に反映する。探索の安定tie-breakや探索上限は
バージョン化された安全なアルゴリズム契約であり、任意コードや無制限探索は許可しない。

## 5. 文言・書式・アクセシビリティ

テンプレートは文字列と許可された `{identifier}` の置換のみ。
共通識別子: windowStart, windowLastVisible, selectedCount, unmatchedCount, missingCount。
titleのみ追加でtitle、unmatchedActualのみunmatchedIds、
summaryEntryのみlabel/value、coverageRatioのみactualCountを許可する。
unmatchedIdsはlistSeparatorで結合する。Summaryの分母0はformatting.unknownを使う。
titleの空文字は不可。Summary値は意味型に従いdate/numberを整形してから置換し、
一般の整数を一律に「差分日数」として整形する旧挙動は廃止する。
式、属性アクセス、関数、HTML/SVG、evalは認めない。置換結果は必ずescapeする。
欠測表示名・summary表示名を変更しても、データ欠測の意味・分母は変化しない。
月名・四半期・日付は閉じたformatter enum＋明示localeから生成する。
windowLastVisibleは日付window終端の表示用契約を明記して算出する。
DateTime/DSTの計算は既存Coreに委譲し、日付用処理を流用して再定義しない。

Detail legendは既存`28`のlegendの唯一の正本。Layoutは配置だけ、Themeはswatchだけ。
groupDetails、supplier observations、milestone digestは引き続き低優先で未実装。
そのpanelを実装する場合も共通text/paint/layoutを使い、固定値を再導入しない。
凡例から特定roleを除いても、必要な意味説明はaria/desc/テキスト等に残す。
空のaccessible description、出所metadataの除去、意味のないclipは受理しない。

## 6. 検証境界と診断

schema: 型・未知フィールド・enum・正の寸法・opacity・有限の上限を検証。
上限は安全な入力範囲であり、現在の見た目の既定値ではない。
semantic closure validator（実装計画対象）:

- resource version/hash・base循環・未解決token・重複所有者。
- region ID一意性、slot参照、track index、track bounds、軸level/height対応。
- marker inset<width、radius<=bar bounds、clearanceとportの到達可能性。
- formatter/templateの未登録識別子、role重複、必須説明の不足。
- フォント計測資産・locale資産・出力capabilityの存在。
- viewport内の必要領域、文字・矢印head・variance・欠測labelの衝突。

代表診断: E_PRESENTATION_SETTINGS_REQUIRED、E_PRESENTATION_DUPLICATE_AUTHORITY、
E_PRESENTATION_REFERENCE、E_PRESENTATION_TEMPLATE、E_FONT_METRICS_UNAVAILABLE、
E_LAYOUT_REQUIRED_OVERFLOW、E_CONNECTOR_UNROUTABLE、E_OUTPUT_CAPABILITY_MISSING。
schema通過のみでsemantic closureや描画品質を保証したとは扱わない。

## 7. 完了条件

全公開SVG経路に対する固定値台帳の全行が「外部化」「計測導出」「不変規則」に分類済み。
rendererがresolved設定しか読まず、未指定値を救済しない。YAMLだけでテーマ、言語、
余白、文字、記号、凡例順・文言、軸、ルーティング傾向を変更する受入例が通る。
同じclosure/metrics/locale/output版ならSVGがbyte-identical。
基準ガント画像に加え、長い日本語、欠測多数、長い凡例、異なるviewportで検証する。
現在の104テストは基準であり、新機能実装の証明ではない。
