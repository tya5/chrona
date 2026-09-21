# #40 実装計画（2026-09-21）

1. `SourceInput` に typography role を持たせ、`ThemeTokenView.typography` で source ごとの測定値と baseline を導出する。
2. CLI の source 入力を semantic role に対応付ける。
3. Scene builder の title baseline を title Measurement の first baseline に変更する。
4. heading が body より大きい場合の measurement・overflow・baseline を unit test で固定する。
5. focused review を公開する。全 pytest は依頼者指定の別実行者へ委譲する。
