# #41 explicit rows and callouts 実装レビュー（2026-09-21）

承認。

- explicit ReviewRow member は View の `visibility.labels` に従い、独立した member-label primitive を得る。
- mark size は Theme metric `timeline.mark.blockSize` に固定され、member count では縮小しない。
- snapshot は `snapshot` visual role で描画され、例示 Theme の `snapshot.fill` に束縛される。
- relation は member mark ports を使用する。同一行ではその行だけを route obstacle から外し、coincident／one-point path は `E_PRESENTATION_ROUTE_UNAVAILABLE` で renderer 前に拒否する。
- object callout は annotations rail に配置し、timeline rows は rail 候補の障害物にしない。
- focused regression tests を追加し、公開済みファイルの静的整合検査に成功した。全 pytest は依頼者指定の別実行者に委譲済み。
- #42 の overlay、group header、calendar、legend、拡張 label vocabulary は未着手であり、#41 に混在させていない。
