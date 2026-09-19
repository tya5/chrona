"""Explicit M12 collaboration boundary; no last-writer-wins."""
from dataclasses import dataclass
from hashlib import sha256
import json

@dataclass(frozen=True)
class CollaborationResult:
 status:str; diagnostic:str|None=None; conflict:dict|None=None

def fingerprint(command): return 'sha256:'+sha256(json.dumps(command,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def submit(store, command, decision, now):
 if decision.get('decision')!='allow': return CollaborationResult('rejected','E_AUTHORIZATION_DENIED')
 approval=command.get('approval')
 if approval and (approval.get('commandFingerprint')!=fingerprint(command.get('payload',{}))): return CollaborationResult('rejected','E_APPROVAL_FINGERPRINT_MISMATCH')
 if approval and approval.get('expiresAt','')<=now: return CollaborationResult('rejected','E_APPROVAL_EXPIRED')
 snap=store.read()
 if snap.revision!=command.get('baseRevision'):
  return CollaborationResult('conflict','E_COMMAND_STALE_BASE_REVISION',{'id':'conflict:'+command['commandId'],'parents':[command['baseRevision'],snap.revision],'path':'project','kind':'semantic','provenance':{'actor':command['actor']['principal']}})
 return CollaborationResult('accepted')

def replica_status(known_revision, remote_revision):
 return CollaborationResult('behind','I_REPLICA_BEHIND') if known_revision!=remote_revision else CollaborationResult('current')
