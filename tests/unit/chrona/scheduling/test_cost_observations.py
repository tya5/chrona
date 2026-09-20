from chrona.cost_observations import MemoryCostObservationStore, aggregate_cost_observations, record_cost_observation

def test_cost_records_are_cas_append_only_and_aggregate_by_units():
 s=MemoryCostObservationStore({"version":"chrona/cost-observation-set/v0.2","id":"p","observations":[]}); rev,_=s.read(); o={"id":"x","observedOn":"2027-01-04","quantity":8,"quantityUnit":"hour","rate":100,"rateUnit":"JPY"}
 assert record_cost_observation(s,rev,o).status=="accepted"; assert record_cost_observation(s,rev,o).diagnostics==("E_COMMAND_STALE_BASE_REVISION",)
 _,value=s.read(); assert aggregate_cost_observations(value).totals[0]["amount"]==800

def test_cost_rejects_duplicate_and_invalid_unit_without_project_input():
 s=MemoryCostObservationStore({"id":"p","observations":[{"id":"x"}]}); rev,_=s.read()
 assert record_cost_observation(s,rev,{"id":"x"}).diagnostics==("E_COST_DUPLICATE_ID",)
 assert aggregate_cost_observations({"observations":[{"quantity":1,"quantityUnit":"hour","rate":1,"rateUnit":"hour"}]}).diagnostics==("E_COST_UNIT_MISMATCH",)
