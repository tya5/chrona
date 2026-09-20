from chrona.capacity import apply_leveling_proposal, evaluate_capacity, evaluate_leveling
from chrona.revision_store import MemoryRevisionStore


def test_capacity_derives_daily_overload_without_mutating_project():
    project={"version":"timeline/v0.1","project":{"id":"p"},"objects":{"task":{"type":"task","schedule":{"mode":"fixed","start":"2027-01-04","end":"2027-01-06"}}},"relations":[]}
    capacity={"resources":[{"id":"eng","unit":"engineer"}],"availability":[{"date":"2027-01-04","resourceId":"eng","amount":1},{"date":"2027-01-05","resourceId":"eng","amount":0}],"assignments":[{"objectId":"task","resourceId":"eng","demand":1,"unit":"engineer"}]}
    result=evaluate_capacity(project,capacity)
    assert [item["date"] for item in result.overloads]==["2027-01-05"]
    assert project["objects"]["task"]["schedule"]["start"]=="2027-01-04"


def test_capacity_rejects_unit_and_duplicate_availability():
    project={"version":"timeline/v0.1","project":{"id":"p"},"objects":{"m":{"type":"milestone","schedule":{"mode":"fixed","at":"2027-01-04"}}},"relations":[]}
    capacity={"resources":[{"id":"eng","unit":"engineer"}],"availability":[{"date":"2027-01-04","resourceId":"eng","amount":1},{"date":"2027-01-04","resourceId":"eng","amount":1}],"assignments":[{"objectId":"m","resourceId":"eng","demand":1,"unit":"machine"}]}
    assert {item.id for item in evaluate_capacity(project,capacity).diagnostics}=={"E_CAPACITY_AVAILABILITY","E_RESOURCE_UNIT_MISMATCH"}


def test_leveling_is_derived_then_applies_only_its_current_complete_proposal():
    project={"version":"timeline/v0.1","project":{"id":"p"},"objects":{"source":{"type":"milestone","schedule":{"mode":"fixed","at":"2027-01-04"}},"task":{"type":"task","schedule":{"mode":"scheduled","amount":"1d"}}},"relations":[{"type":"dependency","from":{"object":"source","endpoint":"at"},"to":{"object":"task","endpoint":"start"}}]}
    capacity={"resources":[{"id":"eng","unit":"engineer"}],"availability":[{"date":"2027-01-04","resourceId":"eng","amount":0},{"date":"2027-01-05","resourceId":"eng","amount":1}],"assignments":[{"objectId":"task","resourceId":"eng","demand":1,"unit":"engineer"}]}
    store=MemoryRevisionStore(project)
    result=evaluate_leveling(store,capacity,("task",))
    assert result.proposal and result.proposal["changes"]==[{"objectId":"task","start":"2027-01-05"}]
    assert store.read().project["objects"]["task"]["schedule"].get("anchor") is None
    assert apply_leveling_proposal(store,result.proposal,capacity)[0]=="accepted"
    assert store.read().project["objects"]["task"]["schedule"]["anchor"]["start"]=="2027-01-05"


def test_leveling_rejects_stale_or_anchored_scope():
    project={"version":"timeline/v0.1","project":{"id":"p"},"objects":{"source":{"type":"milestone","schedule":{"mode":"fixed","at":"2027-01-04"}},"task":{"type":"task","schedule":{"mode":"scheduled","amount":"1d"}}},"relations":[{"type":"dependency","from":{"object":"source","endpoint":"at"},"to":{"object":"task","endpoint":"start"}}]}
    capacity={"resources":[{"id":"eng","unit":"engineer"}],"availability":[{"date":"2027-01-04","resourceId":"eng","amount":0},{"date":"2027-01-05","resourceId":"eng","amount":1}],"assignments":[{"objectId":"task","resourceId":"eng","demand":1,"unit":"engineer"}]}
    store=MemoryRevisionStore(project)
    proposal=evaluate_leveling(store,capacity,("task",)).proposal
    assert proposal
    store.write(store.read().revision,project)
    assert apply_leveling_proposal(store,proposal,capacity)[1][0].id=="E_COMMAND_STALE_BASE_REVISION"
