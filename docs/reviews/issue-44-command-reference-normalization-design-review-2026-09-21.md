# #44 コマンド参照正規化・設計レビュー（2026-09-21）

## 結論

承認。補遺は仕様 42 と整合する。

- immutable Store + revision + address は必須のまま保持される。
- 省略可能なのは exact-byte pin のみであり、指定時の不一致検出を弱めない。
- すべての成功結果は検証済み・計算済みの identity を戻す。
- Extensions の package identity 要件、削除済み旧 Settings/Theme 契約、M28 の closure 境界には変更を加えない。

実装は schema、command verification、capture result/replay input、回帰テストを同時に更新する。
