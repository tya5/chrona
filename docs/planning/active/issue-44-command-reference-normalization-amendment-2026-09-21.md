# #44 コマンド参照正規化の設計補遺（2026-09-21）

## 発見した乖離

仕様 42 は、コマンドの `expectedContentIdentity` を任意の楽観ロック条件として定める。一方、現行の Command Request v0.2 schema とコマンド実装は、この値とターゲット参照の `contentIdentity` を必須としていた。

## 決定

- `expectedContentIdentity` は Command Request v0.2 の任意フィールドにする。
- ターゲットおよび payload の resource reference は仕様 42 の任意 `contentIdentity` を継承する。
- `baseRevision` は引き続き必須で、検証済み参照の immutable revision と一致しなければならない。
- `expectedContentIdentity` が供給された場合だけ、検証済み参照の計算済み identity と比較して不一致を `E_AUTOMATION_BASE_REVISION` とする。
- コマンド結果の `inputs`、ベースラインの `resultTarget`、再実行台帳への対象は、読取後に計算済み identity を付与した正規化参照を用いる。

これにより、revision-only の要求は immutable revision により安全に再現可能であり、任意の byte pin を供給した利用者には従来どおり厳密な楽観ロックが提供される。拡張パッケージの identity 必須規則は変更しない。
