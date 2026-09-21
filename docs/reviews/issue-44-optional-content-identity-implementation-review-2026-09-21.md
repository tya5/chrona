# #44 optional contentIdentity 実装レビュー（2026-09-21）

## 結論

承認。仕様 42 と補遺の全決定を実装へ反映した。

## 確認結果

- revision-store resource reference と Render Context v0.5/v0.6 の `contentIdentity` は任意。
- 通常読取は計算済み SHA-256 を使い、指定値のみ `E_CONTENT_IDENTITY` で検証する。
- Store 設定の `integrity: required` と CLI の `--require-content-identity` は省略値を `E_CONTENT_IDENTITY_REQUIRED` で拒否する。
- closure、operation verification、baseline capture、command result は計算済み identity を保持または返す。
- Command Request v0.2 の `expectedContentIdentity` は任意で、指定時のみ optimistic lock として照合する。
- extension package の identity 必須規則、immutable revision 制約、削除済み旧 Settings/Theme 契約には変更がない。

## 検証

公開済み 9 ファイルの静的整合検査を実施し、schema・strict reader・baseline propagation・command normalization・CLI flag の全チェックが成功した。回帰テストを追加済み。全 pytest は依頼者が別実行者へ委譲済みのため、この実装段階では実行しない。
