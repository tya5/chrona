import csv
rows = []
def g(i,en,ja): rows.append(dict(id=i,title_en=en,title_ja=ja,type="group"))
def t(i,en,ja,dur,parent,preds="",start="",prog="",ast="",afin=""):
    rows.append(dict(id=i,title_en=en,title_ja=ja,type="task",duration=dur,parent=parent,predecessors=preds,start=start,progress=prog,actual_start=ast,actual_finish=afin))
def m(i,en,ja,parent,preds="",start="",ast=""):
    rows.append(dict(id=i,title_en=en,title_ja=ja,type="gate",parent=parent,predecessors=preds,start=start,actual_start=ast))
m("kickoff","Programme kickoff","キックオフ","", start="2027-01-04", ast="2027-01-04")
g("discovery","Discovery","調査")
t("stakeholder","Stakeholder interviews","関係者ヒアリング","8wd","discovery","kickoff",prog="1",ast="2027-01-04",afin="2027-01-13")
t("market","Market scan","市場調査","6wd","discovery","kickoff",prog="1",ast="2027-01-05",afin="2027-01-14")
t("current","Current-state audit","現状監査","10wd","discovery","kickoff",prog="1",ast="2027-01-04",afin="2027-01-19")
t("needs","Requirements catalogue","要件一覧","7wd","discovery","stakeholder, market",prog="1",ast="2027-01-15",afin="2027-01-26")
t("business-case","Business case","事業計画","5wd","discovery","needs",prog="1",ast="2027-01-27",afin="2027-02-03")
m("gate-1","Gate 1: scope agreed","G1 範囲合意","discovery","business-case, current",ast="2027-02-04")
g("design","Design","設計")
t("arch","Target architecture","目標アーキテクチャ","10wd","design","gate-1",prog="1",ast="2027-02-04",afin="2027-02-18")
t("data-model","Data model","データモデル","8wd","design","arch.start +3wd",prog="1",ast="2027-02-09",afin="2027-02-19")
t("ux","Service design","サービス設計","12wd","design","gate-1",prog="1",ast="2027-02-04",afin="2027-02-22")
t("security","Security review","セキュリティ審査","5wd","design","arch",prog="1",ast="2027-02-19",afin="2027-02-26")
t("vendor","Vendor selection","ベンダー選定","9wd","design","gate-1",prog="1",ast="2027-02-05",afin="2027-02-18")
t("plan","Delivery plan","実行計画","4wd","design","ux, security, vendor",prog="1",ast="2027-03-01",afin="2027-03-04")
m("gate-2","Gate 2: design signed off","G2 設計承認","design","plan, data-model",ast="2027-03-05")
g("build","Build","開発")
t("platform","Platform setup","基盤構築","10wd","build","gate-2",prog="1",ast="2027-03-08",afin="2027-03-22")
t("integration","Integration layer","連携層","15wd","build","platform",prog="0.6",ast="2027-03-23")
t("portal","Customer portal","顧客ポータル","20wd","build","platform",prog="0.45",ast="2027-03-24")
t("backoffice","Back-office tools","業務ツール","14wd","build","platform",prog="0.3",ast="2027-03-29")
t("migration","Data migration scripts","移行スクリプト","12wd","build","platform +5wd",prog="0.2",ast="2027-04-05")
t("reports","Reporting","帳票","8wd","build","integration")
t("docs","User documentation","利用者マニュアル","10wd","build","portal.start +10wd")
m("code-freeze","Code freeze","コード凍結","build","reports, portal, backoffice, migration")
g("verify","Verification","検証")
t("sit","System integration test","結合テスト","10wd","verify","code-freeze")
t("perf","Performance test","性能テスト","6wd","verify","sit.start +4wd")
t("pentest","Penetration test","侵入テスト","5wd","verify","code-freeze +2wd")
t("uat","User acceptance test","受入テスト","10wd","verify","sit")
t("dress","Migration rehearsal","移行リハーサル","5wd","verify","uat.start +3wd")
t("training","Staff training","社員研修","8wd","verify","docs")
m("gate-3","Gate 3: go-live approval","G3 稼働承認","verify","uat, perf, pentest, dress, training")
g("rollout","Rollout","展開")
t("pilot","Pilot region","先行地域","10wd","rollout","gate-3")
t("wave-1","Wave 1 regions","第1波","10wd","rollout","pilot")
t("wave-2","Wave 2 regions","第2波","10wd","rollout","wave-1")
t("comms","Change communications","周知活動","15wd","rollout","gate-3")
t("decom","Legacy decommission","旧系停止","8wd","rollout","wave-2")
t("hypercare","Hypercare","安定化支援","10wd","rollout","wave-1 +5wd")
m("close","Programme close","プログラム完了","rollout","decom, hypercare, comms")

slip = {"integration":"19wd","portal":"24wd","migration":"15wd","uat":"12wd"}
cols = ["id","title","type","start","duration","parent","predecessors","progress","actual_start","actual_finish"]
def write(path, lang, current):
    with open(path,"w",newline="") as f:
        w = csv.DictWriter(f, fieldnames=cols); w.writeheader()
        for r in rows:
            d = {k:r.get(k,"") for k in cols}
            d["title"] = r["title_"+lang]
            if current and r["id"] in slip: d["duration"]=slip[r["id"]]
            if not current: d["progress"]=d["actual_start"]=d["actual_finish"]=""
            w.writerow(d)
for lang in ("en","ja"):
    write(f"plan-{lang}.csv",lang,True); write(f"baseline-{lang}.csv",lang,False)
print(sum(1 for r in rows if r["type"]=="task"),"tasks", sum(1 for r in rows if r["type"]=="gate"),"gates")
