# #42 Actual cutoff 実装補遺計画（2026-09-21）

1. Actual-set v0.1 schema に任意 `body.asOf` Date-only を追加する。
2. normalized SurfaceContent に optional as-of Date を保持し、CLI が closed Actual set を渡す。
3. Scene は window 内の as-of を vertical Path primitive として描く。Theme `as-of.stroke` を使う。
4. example Actual set と Theme binding、focused test を追加する。
