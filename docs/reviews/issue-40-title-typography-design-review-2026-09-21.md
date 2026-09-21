# #40 設計レビュー（2026-09-21）

承認。測定と描画の typography role を一致させ、baseline を Layout 測定値から配置する。

- title の heading role を body metric で測る経路を撤去する。
- required overflow は既存 Layout engine の slot measurement 判定で扱い、renderer に新しい裁量を持ち込まない。
- resolved Theme v0.2 のみを入力とし、削除済み Settings/Theme 契約を復活させない。
- M28 closure、M39 semantic primitive の API は維持する。
