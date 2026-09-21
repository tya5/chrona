# #42 Actual cutoff 設計補遺（2026-09-21）

Actual set v0.1 には観測 cutoff を表す構造化フィールドがない。resource ID や observation の最大日付から as-of を推測してはならない。

`actual-set.body.asOf` を任意の Date-only field として追加する。存在する場合のみ、View が Actual を表示している review surface は `as-of` primitive を描く。存在しない場合、Scene は marker を作らない。既存 Actual set は互換的に cutoff を省略できる。

この field は外部観測の収集時点という Actual-set の事実であり、Project schedule、View window、Theme、immutable closure の責務を変えない。
