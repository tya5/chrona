# I3 公開surface adapter 設計レビュー

**対象:** `be455b796ee63957cd1b0af7fd023e6042ac543f` のI3第2設計補正後の再開境界。
**結論:** 要修正だったprimitive data contractと移行完了条件を仕様08 §5.3、派生fixture、
I3完成計画へ追加した。これらの成果物が同一revisionで検証・公開されるまで実装は開始しない。

## 確認した不整合

| ID | 検出内容 | 設計上の原因 | 是正 |
|---|---|---|---|
| I3-R01 | Sceneにsurface slot/rowはあるが、surface別のaxis/tick/mark/Text primitive contractが無い | adapterがgeometryを再構成できる余地が残る | 仕様08 §5.3とderived fixtureにcore primitive set、identity、Text payload/baselineを追加 |
| I3-R02 | table-timeline、review、minimalのどこまでを同じI3で移行するか曖昧 | core primitive移行だけでI3完了と誤認し得る | I3-A〜F/V1の順序、未移行family、全adapter完了条件を計画化 |
| I3-R03 | Scene不足時のfailure contractが一般論のみ | adapterがsettings fallbackを正当化できる | surface/primitive欠損の安定診断と禁止救済を固定 |

## レイヤー整合

`ResolvedPresentationInput → SceneSurface → SVG adapter` の一方向を固定する。surface instanceは
Scene Builderが所有し、adapterは選択と直列化のみを行う。core primitive familyと後続familyを分けても、
両方がScene Builder所有であることを明示したため、table/review/minimalにadapter私有geometryの例外は残らない。

## 実装着手条件

- `validate_presentation_scene_input.py`、`validate_presentation_g2_g4_design.py`、shared presentation validatorが成功する。
- 仕様08 §5.3、I3完成計画、派生fixtureのsurface/diagnostic/primitive表が矛盾しない。
- この設計単位をGitHub `main`へ直列公開し、そのSHAをI3-Bの親として固定する。

上記を満たした後の最初の実装はI3-Bだけである。review/minimalのadapter書換え、connector、annotation、
table cellはI3-Bの範囲外であり、同時実装しない。
