"""Meaning and remedy of the diagnostic codes an MCP tool emits beyond the plan-level table (#1892 row 4).

``skills/chrona/references/diagnostics.md`` explains the plan codes (``E_SCHEMA``, ``E_REFERENCE``, ...). The codes below are
the ones the MCP layer, the guided authoring transaction and the Store commands add. The server appends this catalogue to
``chrona://guide/diagnostics`` so an agent reads every code from one resource, and ``tests/unit/chrona/app/
test_agent_diagnostics.py`` fails when a code those layers emit has no entry here or in the skill table.
"""
from __future__ import annotations

# code -> (tools that emit it, what it means, what to change)
_ROWS: dict[str, tuple[str, str, str]] = {
    "E_MCP_INPUT_INVALID": ("any tool", "An argument breaks the tool's input schema; `sourceRef` is the JSON pointer of the violating node and the message gives the expected shape.", "Fix the argument at `sourceRef` to the shape named; the tool wrote nothing."),
    "E_MCP_INPUT_TOO_LARGE": ("tools taking a file or inline document", "The input is larger than the server reads.", "Send a smaller document or split the plan."),
    "E_MCP_PATH_SYNTAX": ("any tool with a path argument", "A path is absolute, has `..`, a backslash or another form the workspace does not accept.", "Use a '/'-separated path relative to the workspace root."),
    "E_MCP_PATH_CONTAINMENT": ("any tool with a path argument", "The path resolves (through a link or a Store root) outside the workspace, or does not exist inside it.", "Name a file that exists inside the workspace; the server never reads outside it."),
    "E_MCP_WORKSPACE_TOO_BROAD": ("server start", "The workspace root given to `chrona mcp --workspace` is a filesystem root or home directory.", "Start the server with the project directory."),
    "E_MCP_WRITE_DISABLED": ("apply_authoring_command, apply_project_command, apply_command, create_workspace, create_project, save_baseline, create_store, publish_resource", "The server was started without `--allow-write`; no file was opened.", "Ask the user to restart `chrona mcp --allow-write`; use `check_command` or read tools meanwhile."),
    "E_MCP_RESULT_TOO_LARGE": ("render and read tools", "The result is larger than the server returns.", "Ask for a smaller viewport, one format, or `inline: false`."),
    "E_MCP_UNAVAILABLE": ("chrona mcp", "The optional MCP SDK is not installed.", "`pip install 'chrona[mcp]'`."),
    "E_TOOL_FAILURE": ("any tool", "The tool failed for a reason with no stable code of its own; the message carries the cause.", "Quote the message to the user; do not retry blindly."),
    "W_DEADLINE": ("schedule_project (warnings)", "An object is planned to finish after its deadline; exit stays ok.", "Move the work, loosen the dependency, or change the deadline; it is not an error."),
    "E_INPUT_IO": ("tools taking a path", "A file does not exist or cannot be read.", "Fix the path."),
    "E_CLOSURE_KIND": ("validate_project", "The document's `kind` is not one `validate` checks, so it cannot be validated here.", "Use the tool the message names for that kind (`validate_workspace`, `check_command`, ...)."),
    "E_AUTHORING_WORKSPACE_EXISTS": ("create_workspace", "The destination directory already exists.", "Pick a new directory name; nothing was changed."),
    "E_AUTHORING_WORKSPACE_SCHEMA": ("validate_workspace, workspace_revision, apply_authoring_command, apply_project_command", "The workspace file is missing, not a regular file or violates the workspace schema.", "Fix the workspace at `sourceRef`, or create one with `create_workspace`."),
    "E_AUTHORING_BASE_REVISION": ("apply_authoring_command, apply_project_command", "`baseRevision` is not the workspace's (or Project's) current revision (another edit landed); nothing was written.", "Call `workspace_revision` (or `validate_project`, `projectRevision`), rebuild the command on the revision named in `expectedRevision`, and send it with a new `commandId`."),
    "E_AUTHORING_COMMAND_ID_REUSE": ("apply_authoring_command, apply_project_command", "This `commandId` already identifies a different request, and the first command was applied (`firstApplied`, `appliedRevision`, `revisionIsCurrent`).", "To retry the first command resend it unchanged (a replay carries `replayed: true`); for a new edit use a new `commandId`."),
    "E_AUTHORING_TARGET_MISMATCH": ("apply_authoring_command, apply_project_command", "`target.path` is not the workspace or Project file name.", "Use the file name only, for `guided/workspace.yaml` that is `workspace.yaml`, for `plans/project.yaml` it is `project.yaml`."),
    "E_AUTHORING_COMMAND": ("apply_authoring_command", "The command cannot apply to this workspace: the type is unknown, a removal names a task, actual or override set that is not there, a task still has an actual, or `index` is beyond the list or names an existing entry.", "Read the `detail`; use `setWorkspaceTask`, `removeWorkspaceTask`, `setWorkspaceActual`, `removeWorkspaceActual`, `selectPresentationPreset`, `setPresentationOverride`, `removePresentationOverride` or `materializePresentationPreset` on entries that exist (remove a task's actual first)."),
    "E_AUTHORING_COMMAND_SCHEMA": ("apply_authoring_command", "The command breaks `authoring-command/v0.1`; `sourceRef` points at the node.", "Fix the node at `sourceRef` to the shape the message gives."),
    "E_AUTHORING_EXPLICIT_MODE": ("apply_authoring_command", "A preset or materialize command needs a guided workspace and the workspace is in explicit mode.", "Use a guided workspace, or edit the explicit files directly."),
    "E_AUTHORING_PRESET_IDENTITY": ("apply_authoring_command", "`selectPresentationPreset` `id` and `version` do not equal those of the preset file at `path`.", "Send the id and version the message reports, or point `path` at the matching copy."),
    "E_AUTHORING_PRESET_SCHEMA": ("apply_authoring_command, create_workspace", "The preset at `path` is not readable or lacks a package version.", "Point at a copied preset directory, or create the workspace again from a builtin id."),
    "E_AUTHORING_MATERIALIZE_COLLISION": ("apply_authoring_command", "`materializePresentationPreset` would write into a directory that already exists.", "Choose another `directory`; nothing is overwritten."),
    "E_AUTHORING_MATERIALIZE_PATH": ("apply_authoring_command", "The `materializePresentationPreset` directory is unsafe or outside the workspace.", "Use a relative path below the workspace file's directory."),
    "E_AUTHORING_MATERIALIZE_OUTPUT_PROOF": ("apply_authoring_command", "The materialized preset files do not match the pinned preset.", "Re-select the preset and retry; report it if it repeats."),
    "E_AUTHORING_AGGREGATE_CANDIDATE": ("apply_authoring_command, apply_project_command", "The prepared edit could not be committed as one unit (internal consistency).", "Retry once with a fresh `workspace_revision`; report it if it repeats."),
    "E_AUTHORING_AGGREGATE_PATH": ("apply_authoring_command, apply_project_command", "The prepared edit names an unsafe output path.", "Report it; the command is not at fault."),
    "E_AUTHORING_AGGREGATE_RECOVERY": ("apply_authoring_command, apply_project_command", "An earlier write stopped half-way and the workspace needs recovery before another command.", "Retry the same command (it recovers first); do not edit the workspace files by hand."),
    "E_AUTHORING_REPLAY_UNAVAILABLE": ("apply_authoring_command, apply_project_command", "A stored replay receipt is missing, corrupt or does not match its request, so the server cannot say whether the command applied.", "Read `workspace_revision` and the workspace, compare with what you intended, and send a new `commandId` if the edit is absent."),
    "E_AUTHORING_LOCK_UNAVAILABLE": ("apply_authoring_command, apply_project_command", "The workspace lock file cannot be created (a link or a read-only directory).", "Make the workspace directory writable and retry."),
    "E_AUTHORING_LOCK_TIMEOUT": ("apply_authoring_command, apply_project_command", "Another writer held the workspace lock for too long.", "Retry after the other writer finishes."),
    "E_AUTHORING_PROJECT_SCHEMA": ("create_workspace", "The `project` object is not an object or has no non-empty `id`.", "Send `project` with `id` and tasks as the tool schema shows."),
    "E_WORKSPACE_PARENT": ("create_workspace, create_project", "The parent of `directory` is not an existing real directory.", "Create the parent first, or choose a directory directly below an existing one."),
    "E_WORKSPACE_FILE_PATH": ("create_workspace", "An initial file path is unsafe or not canonical.", "Report it; the arguments cannot cause it."),
    "E_WORKSPACE_FILE_SET": ("create_workspace", "The initial file set lacks `workspace.yaml`.", "Report it; the arguments cannot cause it."),
    "E_WORKSPACE_FILE_COLLISION": ("create_workspace", "A file appeared in the destination while it was being created; nothing existing was overwritten.", "Retry with a new directory name."),
    "E_PROJECT_EXISTS": ("create_project", "A file already exists at `file`; `create_project` never overwrites.", "Choose a new file name, or edit the existing Project with `apply_project_command`."),
    "E_BASELINE_FILE_EXISTS": ("save_baseline", "`baselines/<name>.yaml` beside the Project already holds other content; a baseline is never overwritten.", "Save under a new `name`; the same content again is a replay (`replayed: true`), not an error."),
    "E_BASELINE_DIRECTORY": ("save_baseline", "`baselines` beside the Project is a symlink or not a directory.", "Remove or rename that entry, or move the Project to a directory where `baselines` is free."),
    "E_STORE_CONFIG_EXISTS": ("create_store", "`.chrona/store.yaml` already exists with a different configuration (another identity, or one written by hand); it is never rewritten.", "Use the existing Store with `publish_resource`, or call `create_store` with the identity it already declares."),
    "E_STORE_DIRECTORY": ("create_store", "`.chrona` or `.chrona/store` is a symlink or not a directory.", "Remove or rename that entry, then call `create_store` again."),
    "E_STORE_RESOURCE_INVALID": ("publish_resource", "The resource is not a mapping of the requested `kind`, or its id is not one safe Store segment.", "Set `kind` to match the document and give it an id of letters, digits, '.', '_' and '-'."),
    "E_STORE_RESOURCE_EXISTS": ("publish_resource", "The Actual Set is already in the Store with other content, or a Store revision holds other bytes; a published resource is never overwritten.", "Change an Actual Set with `apply_command` (`applyActualIntakeBatch`); publish a changed Project again as a new revision."),
    "E_STORE_SELECTION": ("publish_resource", "The Store configuration declares no local Store of the given `store` identity, or several and none was named.", "Pass `store` with an identity the configuration declares."),
    "E_PROJECT_COMMAND": ("apply_project_command", "The command `type` is not one the tool applies, or the Project member it edits (`objects`, `relations`, `calendars`, `entities`, `fieldRoles`, `annotations`, `periods`, `scenarios`, `extensions`, `project`) has the wrong shape, or a `setExtension` declaration's `packageId` differs from the command's.", "Use one of `setObject`, `removeObject`, `setRelation`, `removeRelation`, `setCalendar`, `removeCalendar`, `setEntity`, `setFieldRole`, `setAnnotation`, `setProjectMeta`, `removeEntity`, `removeFieldRole`, `removeAnnotation`, `setExtension`, `removeExtension`, `setPeriod`, `removePeriod`, `setScenario`, `removeScenario`; fix a malformed member in the file first."),
    "E_PROJECT_COMMAND_SCHEMA": ("apply_project_command", "A command file breaks `project-command/v0.1`; `sourceRef` points at the node.", "Fix the node at `sourceRef` to the shape the message gives."),
    "E_PROJECT_OBJECT_MISSING": ("apply_project_command", "`removeObject` names an id that is not under `objects`, or `setAnnotation` anchors on one.", "Use an id the message lists, or read the Project first."),
    "E_PROJECT_OBJECT_REFERENCED": ("apply_project_command", "`removeObject` would leave a relation endpoint, a `parent`, an `attachesTo` or an annotation anchor pointing at a missing object.", "Change or remove the relations and children the message names first."),
    "E_PROJECT_RELATION_MISSING": ("apply_project_command", "`removeRelation` names an id that no relation declares (a relation without an `id` cannot be removed by id).", "Use a relation id the message lists, or read the Project first."),
    "E_PROJECT_CALENDAR_MISSING": ("apply_project_command", "`removeCalendar` names an id that is not under `calendars`.", "Use an id the message lists, or read the Project first."),
    "E_PROJECT_CALENDAR_REFERENCED": ("apply_project_command", "`removeCalendar` would leave `project.calendar`, an object's `calendar` or a relation's `lag.calendar` pointing at a missing calendar.", "Point the users the message names at another calendar first."),
    "E_PROJECT_ENTITY_MISSING": ("apply_project_command", "`removeEntity` names an id that is not under `entities`.", "Use an id the message lists, or read the Project first."),
    "E_PROJECT_ENTITY_REFERENCED": ("apply_project_command", "`removeEntity` would leave an object's or entity's `fields` value pointing at a missing entity.", "Change the fields the message names first."),
    "E_PROJECT_FIELD_ROLE_MISSING": ("apply_project_command", "`removeFieldRole` names a role that is not bound under `fieldRoles`.", "Use a role the message lists, or read the Project first."),
    "E_PROJECT_EXTENSION_MISSING": ("apply_project_command", "`removeExtension` names a `packageId` that no `extensions` entry declares.", "Use a package id the message lists, or read the Project first."),
    "E_PROJECT_EXTENSION_REFERENCED": ("apply_project_command", "`removeExtension` would leave an object `type` naming a profile the package defines.", "Change the object types the message names first."),
    "E_PROJECT_PERIOD_MISSING": ("apply_project_command", "`removePeriod` names an id that is not under `periods`.", "Use an id the message lists, or read the Project first."),
    "E_PROJECT_SCENARIO_MISSING": ("apply_project_command", "`removeScenario` names an id that is not under `scenarios`.", "Use an id the message lists, or read the Project first."),
    "E_PROJECT_RELATION_REFERENCED": ("apply_project_command", "`removeRelation` names a relation that a scenario's `relations.remove` still lists.", "Change the scenarios the message names first."),
    "E_SCENARIO_OBJECT_NOT_FOUND": ("apply_project_command", "`setScenario` removes (null) an object the Project does not have, at `/payload/scenario/objects/<id>`.", "Name an existing object or drop the removal."),
    "E_SCENARIO_RELATION_NOT_FOUND": ("apply_project_command", "`setScenario` lists in `relations.remove` a relation id the Project does not declare.", "Use a relation id the Project declares."),
    "E_SCENARIO_RELATION_DUPLICATE": ("apply_project_command", "`setScenario` adds a relation whose id the Project (after removals) already has.", "Give the added relation a new id."),
    "E_SCENARIO_INVALID": ("apply_project_command", "The Project with the scenario applied breaks a Core rule; the message is the first finding.", "Fix the overlay at the pointer the message gives."),
    "E_PROJECT_ANNOTATION_MISSING": ("apply_project_command", "`removeAnnotation` names an id that is not under `annotations`.", "Use an id the message lists, or read the Project first."),
    "E_INPUT_JSON": ("any tool", "An input that must be JSON is not valid JSON.", "Fix the JSON syntax."),
    "E_RESOURCE_SCHEMA": ("validate_project, render tools", "A resource (View, Theme, Preset, ...) breaks its schema; the reported code names the kind (`E_<KIND>_SCHEMA`) and `sourceRef` the node.", "Fix the node at `sourceRef` to the shape the message gives."),
    "E_PRESENTATION_REJECTED": ("render tools", "The presentation was refused without a more specific code.", "Read the message and change the View or Preset it names."),
    "E_AUTOMATION_OPERATION_UNSUPPORTED": ("check_command, apply_command", "The command `type` is not one the Store tools accept.", "Use `applyActualIntakeBatch`, `captureSnapshot`, `revertActualCommand` or `redoActualCommand`."),
    "E_AUTOMATION_BASE_REVISION": ("check_command, apply_command", "`baseRevision` differs from the target reference; nothing was written.", "Read the Store's current revision and rebuild the command."),
    "E_AUTOMATION_TARGET_CLOSURE": ("check_command, apply_command", "The target reference cannot be resolved or is no longer the Store's current revision.", "Fix the reference (store, address, revision, contentIdentity) to the one the message names."),
    "E_COMMAND_ID_REUSE": ("check_command, apply_command", "This `commandId` already identifies a different request.", "Use a new `commandId` for a new command; resend the first one unchanged to replay it."),
    "E_COMMAND_HISTORY_UNAVAILABLE": ("apply_command (revert, redo)", "The command to revert or redo is not in the replay ledger or its history is corrupt.", "Name a `commandId` this Store accepted."),
    "E_COMMAND_NOT_REVERSIBLE": ("apply_command (revert, redo)", "Only an accepted Actual mutation can be reverted, and only a revert can be redone.", "Revert the Actual command, not a snapshot or an intake that changed nothing."),
    "E_BASELINE_REFERENCE": ("compare_baseline", "The baseline, its project or the candidate reference cannot be resolved.", "Fix the reference the message names."),
    "E_BASELINE_EXISTS": ("apply_command (captureSnapshot)", "A baseline with this name already exists; nothing is overwritten.", "Capture under a new baseline name."),
    "E_ACTUAL_EXTERNAL_CONFLICT": ("apply_command (applyActualIntakeBatch)", "Different facts were sent for an external key that already exists; nothing is overwritten.", "Send the facts the Store holds, or a new external key."),
    "E_ACTUAL_ALIGNMENT": ("apply_command (applyActualIntakeBatch)", "An observation cannot be aligned to a task in the plan.", "Use an object id or alias that exists in the plan."),
    "E_STORE_ROOT_OUTSIDE_WORKSPACE": ("check_command, apply_command", "A Store root in the Store configuration lies outside the workspace.", "Edit the Store configuration so every root is inside the workspace."),
    "E_STORE_LOCK_UNAVAILABLE": ("apply_command", "Another writer holds the Store transaction lock.", "Retry after it finishes."),
}


def diagnostic_catalog() -> dict[str, tuple[str, str, str]]:
    """``code -> (emitted by, meaning, remedy)`` for the codes beyond the plan table."""
    return dict(_ROWS)


def catalog_markdown() -> str:
    """The catalogue as a Markdown section, generated from the table so it cannot drift from it."""
    lines = [
        "## Codes the MCP tools, guided authoring and Store commands add", "",
        "Read `code` and `sourceRef` as above. Every code an MCP tool emits is explained either in the tables above or here;",
        "a code in neither is unexpected, so quote it to the user.", "",
        "| Code | Emitted by | What it means | What to change |", "| --- | --- | --- | --- |",
    ]
    lines += [f"| `{code}` | {tools} | {meaning} | {remedy} |" for code, (tools, meaning, remedy) in sorted(_ROWS.items())]
    return "\n".join(lines) + "\n"
