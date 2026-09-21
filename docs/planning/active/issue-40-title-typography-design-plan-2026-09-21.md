# #40 設計計画（2026-09-21）

1. Layout Source Adapter、Theme typography role、Scene builder の測定／描画境界を確認する。
2. source ごとに描画 typography role を宣言し、測定時も同一 role の font size・line height・baseline を使用する設計を仕様化する。
3. required title slot の overflow 診断を既存 Layout engine の測定契約で確認する。
4. 旧 Settings/Theme 契約を導入しないこと、M28 closure と Scene primitive 契約を保つことを設計レビューする。
5. 実装計画、source adapter／CLI／builder／テストを更新し、公開レビューする。
