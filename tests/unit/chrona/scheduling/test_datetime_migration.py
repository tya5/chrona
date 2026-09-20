import pytest
from chrona.scheduling.datetime_migration import MigrationError,migrate_v1_to_v2,downgrade_v2_to_v1
def test_migrate_explicit_policy_and_zero_lag():
 p={"version":"timeline/v0.1","project":{"id":"p"},"objects":{"a":{"type":"milestone","schedule":{"mode":"fixed","at":"2027-01-01"}},"b":{"type":"task","schedule":{"mode":"scheduled","amount":"2d","anchor":{"start":"2027-01-02"}}}},"relations":[{"type":"dependency","from":{"object":"a","endpoint":"at"},"to":{"object":"b","endpoint":"start"}}]}
 out=migrate_v1_to_v2(p,"r1",{"zone":"UTC","localTime":"09:00","disambiguation":"reject"});assert out["relations"][0]["lag"]["value"]=="0d" and out["objects"]["a"]["schedule"]["at"]["local"]=="2027-01-01T09:00"
 with pytest.raises(MigrationError,match="E_MIGRATION_DOWNGRADE"):downgrade_v2_to_v1(out)

def test_migration_rejects_unanchored_or_unsupported_source_without_output():
 base={"version":"timeline/v0.1","project":{"id":"p"},"objects":{"b":{"type":"task","schedule":{"mode":"scheduled","amount":"1d"}}},"relations":[]}
 with pytest.raises(MigrationError,match="E_MIGRATION_UNSUPPORTED"):migrate_v1_to_v2(base,"r",{"zone":"UTC","localTime":"09:00","disambiguation":"reject"})
 base["annotations"]={}
 with pytest.raises(MigrationError,match="E_MIGRATION_UNSUPPORTED"):migrate_v1_to_v2(base,"r",{"zone":"UTC","localTime":"09:00","disambiguation":"reject"})
