from chrona.collaboration import submit,replica_status
from chrona.revision_store import MemoryRevisionStore
def test_stale_and_policy_are_explicit():
 s=MemoryRevisionStore({'version':'timeline/v0.1','project':{'id':'p'},'objects':{},'relations':[]}); c={'commandId':'x','baseRevision':'old','actor':{'principal':'a'},'payload':{}}
 assert submit(s,c,{'decision':'deny'},'2027').diagnostic=='E_AUTHORIZATION_DENIED'; assert submit(s,c,{'decision':'allow'},'2027').conflict['kind']=='semantic'
def test_replica_never_claims_unseen_tip(): assert replica_status('r1','r2').diagnostic=='I_REPLICA_BEHIND'
