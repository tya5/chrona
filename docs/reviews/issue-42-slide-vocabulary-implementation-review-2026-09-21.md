# #42 slide-grade review vocabulary 実装レビュー（2026-09-21）

承認。

- ReviewRow item の `shared` track は snapshot → planned → actual の安定順に重なり、Actual を特殊モデル化しない。
- group header と member indent は View grouping から Scene が導出する。Project presentation field は追加していない。
- locale-aware calendar axis は既存 interval/formatter を利用し、quarter band を追加する。
- as-of は Actual-set の明示 `asOf` のみから描画し、ID/現在日付/最大観測日から推測しない。
- calendar closure shading は Project calendar の working days と exceptions のみを読む。
- Detail Profile legend は schema で authoring 可能になり、Scene swatch は Theme role から描画する。
- #41 の mark labels/callout rail を語彙として再利用し、別契約を作らない。
- focused regression tests と公開ファイルの静的整合検査に成功した。全 pytest と committed SVG 再生成は依頼者指定の別実行者に委譲済み。
