from chrona.capacity import evaluate_capacity


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
