# 表現設定外部化：実装計画

**現在: 設計・スキーマ・fixtureのみ。実装着手には次の依頼が必要。**

| フェーズ | 作業 | 終了条件 |
|---|---|---|
| P1 | v0.2設定解決、固定base、型検査、View/Style/Theme/Context接続、移行adapter | 欠落・循環・二重所有・unknown設定を拒否。現行YAMLを移行可能 |
| P2 | font metrics・locale・viewport・region solverの一本化 | 手動幅係数なし。日本語/長文、minmax、未解決資産を検証 |
| P3 | Theme全ロール、Detail文言、Layout全寸法をガントで消費 | 78項目群のスキーマ→resolved値→Scene消費が追跡可能 |
| P4 | 旧render、旧review、summary、notes、凡例を共通経路へ統合 | v0.2入力は全公開出力でsettingsのみを消費。v0.1は`E_PRESENTATION_LEGACY_ADAPTER`付きの明示legacy adapterへ正規化し、暗黙のv0.2補完をしない |
| P5 | 全設定変異テスト、異なるプリセット、実画像比較、再現性・性能レビュー | 未使用設定ゼロ、暗黙fallbackゼロ、基準SVG/PNG更新と公開 |

各フェーズは検証・レビュー後にGitHub連携でnon-force公開する。
設計漏れは該当実装を中断して所有仕様・schema・fixturesを先に更新する。
M23のsupplier表・追加dashboardは本計画の前提にも完了条件にもしない。

## テスト行列

- 値の範囲: 0/最小/大きい値/負/型違い/未知フィールド。
- 接続: View値不変、Actual独立、role解決、font資産変更、locale変更。
- 配置: landscape/portrait相当のviewport、長い工程名、多段group、密な依存。
- 文言: 日本語凡例、長いlabel、未知placeholder、悪意あるXML文字列。
- 互換: 旧surface移行、legacy renderer既定値preset化、二重指定拒否。
- 互換閉包: v0.1だけでfont metrics/viewportを推測しない。v0.2 settingsを明示するか、
  legacy adapter診断を出す。v0.1からv0.2への完全移行はcontent-addressed metrics入力を
  含む別migrationとして試験する。
- 検証: schema検査とsemantic診断とraster検査を別々に報告する。
- 監査: 数値/色/文言literalのAST棚卸し。数学定数・診断ID等のallowlistは
  理由付きで限定し、新しい見た目literalをCIで検出する。
