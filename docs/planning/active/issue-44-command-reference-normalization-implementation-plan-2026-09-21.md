# #44 コマンド参照正規化・実装計画（2026-09-21）

1. Command Request v0.2 schema から `expectedContentIdentity` の必須制約を外す。
2. `verify_reference` が返す正規化参照をコマンド検証・実行・結果・再実行台帳で一貫して使用する。
3. supplied identity の不一致と revision 不一致の既存拒否を維持する。
4. revision-only command と baseline capture が計算済み identity を結果に含めることを回帰テスト化する。
5. focused test と静的設計レビューを記録する。全 pytest は依頼者指定の別実行者の結果を待つ。
