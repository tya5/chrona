# #41 explicit rows and callouts 設計計画（2026-09-21）

1. M28 ReviewRow、View visibility／grouping、Theme role、Scene primitive、annotation routing の既存契約を横断確認する。
2. 明示行の member label、固定 mark size、同一行 relation anchor、snapshot paint を一般化して仕様化する。
3. object-anchored callout を annotations rail へ配置する責務と required/optional の失敗規則を仕様化する。
4. #42 の overlay/group header/legend 等と責務が重複しない境界をレビューする。
5. 設計レビュー後に実装計画を公開し、View／Theme schema、projection/Scene builder、renderer、tests を更新する。
