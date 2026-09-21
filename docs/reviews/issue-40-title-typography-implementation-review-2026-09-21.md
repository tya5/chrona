# #40 実装レビュー（2026-09-21）

承認。

- Source Adapter は source ごとの `typography_role` から resolved Theme v0.2 の font size・line height・baseline を導出する。
- CLI は title を `heading`、axis／legend／annotation 系を各 semantic role で登録する。
- Scene builder は title slot の block-start に heading の測定済み first baseline を加えて描画する。
- heading が body より大きい場合の extent と baseline を unit test で固定した。
- Layout の `overflow: diagnose` は更新された title minimum measurement を使うため、必要枠不足を既存 `E_LAYOUT_REQUIRED_OVERFLOW` として拒否する。
- Settings/旧 Theme 契約、M28 closure、M39 primitive 契約への依存追加はない。

静的整合検査は成功。全 pytest は依頼者が別実行者へ委譲済み。
