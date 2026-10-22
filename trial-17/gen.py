"""Trial 17 synthetic plan generator. Writes plan/<case>-<lang>-{project,baseline,actual}.yaml."""
import yaml, os, random, datetime as dt
OUT = os.path.dirname(os.path.abspath(__file__)) + '/plan'
os.makedirs(OUT, exist_ok=True)
D = dt.date; day = dt.timedelta(days=1)

EN_WORDS = ['Requirements', 'Architecture', 'Prototype', 'Integration', 'Validation', 'Rollout', 'Migration',
            'Hardening', 'Review', 'Pilot', 'Training', 'Audit', 'Telemetry', 'Packaging', 'Localization']
JA_WORDS = ['要件定義', '方式設計', '試作', '結合', '検証', '展開', '移行', '堅牢化', 'レビュー', '試行', '教育',
            '監査', '計測', '梱包', '多言語化']
EN_STREAMS = ['Platform', 'Mobile', 'Data', 'Go-to-market', 'Security', 'Support', 'Infrastructure', 'Finance']
JA_STREAMS = ['基盤', 'モバイル', 'データ', '市場投入', 'セキュリティ', 'サポート', 'インフラ', '財務']
EN_GATES = ['Kickoff', 'Design review', 'Alpha', 'Beta start', 'Security sign-off', 'Feature freeze', 'Code freeze',
            'Launch readiness', 'GA', 'Post-launch review', 'Q3 board review', 'Year-end close']
JA_GATES = ['キックオフ', '設計審査', 'アルファ', 'ベータ開始', 'セキュリティ承認', '機能凍結', 'コード凍結', '出荷判定',
            '一般提供', '出荷後レビュー', '第3四半期取締役会', '年度末締め']
EN_OWNERS = ['Ana', 'Ben', 'Chen', 'Dee', 'Eli', 'Fay', 'Gus', 'Hana']
JA_OWNERS = ['佐藤', '鈴木', '高橋', '田中', '伊藤', '渡辺', '山本', '中村']
LONG_EN_OWNERS = ['Maximiliana Konstantinopoulou-Oyelaran (Platform Reliability)',
                  'Bartholomew Featherstonehaugh-Nakamura III', 'Wolfgang Schwarzenegger-Rodriguez',
                  'Anastasiya Vasilyevna Kuznetsova-Pemberton']
LONG_JA_OWNERS = ['長谷川・ヴァンデンブルック 美智子（基盤信頼性グループ）', '勅使河原 左衛門三郎（品質保証部）',
                  '小鳥遊 久留美（モバイル開発統括）', '一二三 四五六七（データ基盤推進室）']
LONG_EN_TITLES = ['Consolidate the legacy authentication providers into a single gateway',
                  'Negotiate the enterprise data processing agreement with all EU customers',
                  'Migrate the reporting warehouse from nightly batch to streaming ingestion',
                  'Run the accessibility audit of every customer-facing mobile screen and fix',
                  'Prepare and rehearse the disaster-recovery failover across both regions',
                  'Rewrite the onboarding flow so that new users reach value within a session']
LONG_JA_TITLES = ['既存の認証基盤を単一のゲートウェイへ統合し旧方式を段階的に廃止する作業',
                  '欧州の全法人顧客とデータ処理契約を再交渉して署名を完了させるまでの手続き',
                  '夜間バッチ方式の集計基盤をストリーミング取り込み方式へ全面的に移行する計画',
                  '顧客向けモバイル画面すべてのアクセシビリティ監査を実施して指摘事項を修正する',
                  '両リージョン間の災害復旧切り替え手順を整備し本番相当の環境で予行演習を行う',
                  '新規利用者が最初の利用で価値を実感できるように導入フロー全体を作り直す作業']


def build(case, lang, nstreams, ntasks, ngates, ndeps, nann, start, horizon_days, title,
          long_titles=False, long_owners=False, long_note=False, asof=None, seed=17):
    rnd = random.Random(seed)
    ja = lang == 'ja'
    streams = (JA_STREAMS if ja else EN_STREAMS)[:nstreams]
    words = JA_WORDS if ja else EN_WORDS
    owners = (LONG_JA_OWNERS if ja else LONG_EN_OWNERS) if long_owners else (JA_OWNERS if ja else EN_OWNERS)
    ltitles = LONG_JA_TITLES if ja else LONG_EN_TITLES
    objs, rels, tasks = {}, [], []
    per = ntasks // nstreams; extra = ntasks - per * nstreams
    for si, sn in enumerate(streams):
        sid = f's{si+1}'
        objs[sid] = {'type': 'group', 'title': sn, 'schedule': {'mode': 'rollup'}}
        n = per + (1 if si < extra else 0)
        seg = horizon_days / n
        cur = start + dt.timedelta(days=int(rnd.uniform(0, seg * 0.3)))
        for k in range(n):
            tid = f'{sid}t{k+1}'
            dur = max(2, int(seg * rnd.uniform(0.6, 1.1)))
            end = cur + dt.timedelta(days=dur)
            if long_titles and k < len(ltitles):
                tt = ltitles[(k + si) % len(ltitles)]
            else:
                w = words[(k + si * 3) % len(words)]
                tt = f'{sn} {w} {k+1}' if not ja else f'{sn}{w}{k+1}'
            objs[tid] = {'type': 'task', 'title': tt, 'parent': sid,
                         'fields': {'owner': owners[(si + k) % len(owners)]},
                         'schedule': {'mode': 'fixed-span', 'start': str(cur), 'end': str(end)}}
            tasks.append((tid, cur, end))
            cur = end + dt.timedelta(days=int(rnd.uniform(0, seg * 0.25)))
    gnames = JA_GATES if ja else EN_GATES
    gates = []
    for gi in range(ngates):
        at = start + dt.timedelta(days=int(horizon_days * (gi + 1) / (ngates + 1)))
        gid = f'g{gi+1}'
        objs[gid] = {'type': 'gate', 'title': gnames[gi % len(gnames)], 'schedule': {'mode': 'fixed-point', 'at': str(at)}}
        gates.append((gid, at))
    # dependencies: consistent (pred end <= succ start); mix of within-stream, cross-stream and task->gate
    cands = []
    for a in tasks:
        for b in tasks:
            if a[0] != b[0] and a[2] <= b[1] and (b[1] - a[2]).days <= 30:
                cands.append((a[0], b[0], a[0].split('t')[0] == b[0].split('t')[0]))
    rnd.shuffle(cands)
    within = [c for c in cands if c[2]]; cross = [c for c in cands if not c[2]]
    ng = min(4, ngates); nd = ndeps - ng
    chosen = within[: nd * 6 // 10] + cross[: nd - nd * 6 // 10]
    seen = set()
    for a, b, _ in chosen:
        if (a, b) in seen: continue
        seen.add((a, b))
        rels.append({'id': f'd-{a}-{b}', 'type': 'dependency', 'from': {'object': a, 'endpoint': 'end'},
                     'to': {'object': b, 'endpoint': 'start'}, 'lag': '0d'})
    # a few task->gate deps
    for gid, at in gates[:max(0, min(4, ngates))]:
        pred = max((t for t in tasks if t[2] <= at), key=lambda t: t[2], default=None)
        if pred and len(rels) < ndeps:
            rels.append({'id': f'd-{pred[0]}-{gid}', 'type': 'dependency', 'from': {'object': pred[0], 'endpoint': 'end'},
                         'to': {'object': gid, 'endpoint': 'at'}, 'lag': '0d'})
    ann = {}
    notes_en = ['Vendor contract still unsigned', 'Two engineers on leave', 'Scope cut agreed with sponsor',
                'Rate limits block load test', 'Waiting for legal review', 'Hardware arrives late']
    notes_ja = ['ベンダー契約が未締結', '技術者2名が休暇', 'スポンサーと範囲縮小に合意', 'レート制限で負荷試験が停止',
                '法務レビュー待ち', 'ハードウェアの納入遅れ']
    LN_EN = ('The external security assessor has asked for a second penetration test round after the gateway '
             'redesign, which pushes sign-off into the following sprint and delays the beta cohort invitation.')
    LN_JA = ('ゲートウェイ再設計の後に外部のセキュリティ評価者から二回目の侵入試験を求められたため、承認が次のスプリントへずれ込み、'
             'ベータ参加者への招待も遅れる見込みです。')
    nl = notes_ja if ja else notes_en
    for i in range(nann):
        t = tasks[(i * 7 + 3) % len(tasks)][0] if i % 3 else gates[i % len(gates)][0] if gates else tasks[i][0]
        text = (LN_JA if ja else LN_EN) if (long_note and i == 0) else nl[i % len(nl)]
        ann[f'a{i+1}'] = {'kind': 'risk' if i % 2 else 'note', 'text': text, 'anchor': {'object': t}}
    doc = {'version': 'timeline/v0.7',
           'project': {'id': f'trial17-{case}', 'title': title, 'calendar': 'office'},
           'fieldRoles': {'responsible': 'owner'},
           'calendars': {'office': {'working_days': ['mon', 'tue', 'wed', 'thu', 'fri']}},
           'objects': objs, 'relations': rels}
    if ann: doc['annotations'] = ann
    # baseline: earlier plan: ~15% of tasks end 5-10 days earlier, one task absent
    base = yaml.safe_load(yaml.safe_dump(doc))
    for i, (tid, s, e) in enumerate(tasks):
        if i % 7 == 2:
            base['objects'][tid]['schedule']['end'] = str(e - dt.timedelta(days=rnd.randint(5, 10)) if (e - s).days > 12 else e)
    if len(tasks) > 4:
        base['objects'].pop(tasks[-2][0])
        base['relations'] = [r for r in base['relations'] if tasks[-2][0] not in (r['from']['object'], r['to']['object'])]
        base['annotations'] = {k: v for k, v in base.get('annotations', {}).items() if v['anchor']['object'] != tasks[-2][0]}
        if not base['annotations']: base.pop('annotations')
    # actuals
    asof = asof or (start + dt.timedelta(days=int(horizon_days * 0.35)))
    obs = []
    for i, (tid, s, e) in enumerate(tasks):
        if s > asof: continue
        shift = rnd.choice([-3, 0, 0, 2, 5])
        a_s = s + dt.timedelta(days=rnd.choice([0, 0, 1]))
        a_e = e + dt.timedelta(days=shift)
        if a_e <= asof and a_e > a_s:
            act = {'start': str(a_s), 'finish': str(a_e), 'progress': 1}
        else:
            act = {'start': str(a_s), 'openUntil': 'asOf', 'progress': round(rnd.uniform(0.1, 0.8), 2)}
        obs.append({'id': f'{tid}-1', 'sequence': 1, 'projectObjectId': tid, 'actual': act})
    actual = {'version': 'chrona/actual-set/v0.3', 'kind': 'actual-set', 'id': f'trial17-{case}-observed',
              'body': {'asOf': str(asof), 'observations': obs}}
    p = f'{OUT}/{case}-{lang}'
    yaml.safe_dump(doc, open(p + '-project.yaml', 'w'), sort_keys=False, allow_unicode=True)
    yaml.safe_dump(base, open(p + '-baseline.yaml', 'w'), sort_keys=False, allow_unicode=True)
    yaml.safe_dump(actual, open(p + '-actual.yaml', 'w'), sort_keys=False, allow_unicode=True)
    print(case, lang, 'tasks', len(tasks), 'gates', len(gates), 'deps', len(rels), 'ann', len(ann), 'obs', len(obs))


for lang in ('en', 'ja'):
    ja = lang == 'ja'
    build('A', lang, 8, 80, 12, 41, 6, D(2027, 1, 4), 270, 'ネバダ製品群 統合計画' if ja else 'Nevada product family plan')
    build('B', lang, 4, 16, 4, 12, 3, D(2027, 1, 4), 120,
          # 50 characters (en) / 30+ (ja)
          '全社統合認証基盤と顧客向けモバイル刷新計画二〇二七年度版' if ja else
          'Unified identity platform and mobile refresh, 2027',
          long_titles=True, long_owners=True, long_note=True)
    build('C', lang, 4, 24, 5, 16, 4, D(2027, 1, 4), 150, '新アプリ立ち上げ計画' if ja else 'Nova app launch plan')
    build('D', lang, 1, 3, 1, 2, 1, D(2027, 3, 1), 14, '小規模修正リリース' if ja else 'Hotfix release')
    build('E', lang, 5, 30, 6, 15, 3, D(2027, 1, 4), 3 * 365, '三か年工場移転計画' if ja else 'Three-year plant relocation')
