# Workbench Terminology Decision

Last updated: 2026-04-10

This document sets the working terminology for future workbench/task runtime work.

It exists to prevent the backend and frontend from using the same words for different persistence and UX concepts.

## Decision summary

The product should distinguish all four terms below:

- `asset`
- `artifact`
- `workspace output`
- `canvas document`

They are related, but they are not interchangeable.

## Canonical definitions

### Asset

An `asset` is a shipped or operator-provided static resource that exists independently of any user task.

Examples:

- theme palette data
- school logos
- default templates
- bundled icons
- demo data

Rules:

- assets are part of the app/package/repo surface, not user-generated runtime output
- assets do not need task ids
- assets are usually addressed by stable file path or build path, not by runtime record id
- changing an asset is a product/repo change, not a user work product change

### Artifact

An `artifact` is a persisted generated file produced by the system for a user/session/task and intended to be downloaded, attached, or referenced later.

Examples:

- generated `brief.md`
- generated `table.csv`
- exported `report.docx`
- any file served from `GET /api/artifacts/{artifact_id}`

Rules:

- artifacts are runtime-generated, not bundled
- artifacts have durable server identity and metadata
- artifacts may be linked to a session, message, or future workbench task
- artifacts are file-oriented and transport-oriented first

Current GOAT AI meaning:

- chat artifacts already exist and are the current canonical `artifact` baseline
- future workbench work should extend this concept, not invent a competing term for generated files

### Workspace output

A `workspace output` is a task-produced result that belongs to a workbench execution context, whether or not it is downloadable as a file.

Examples:

- a task status summary
- a generated plan body
- a research notes block
- a structured result bundle containing text, links, and artifact references

Rules:

- workspace output is the broadest runtime result term
- an artifact can be one kind of workspace output
- a canvas document can be one kind of workspace output
- not every workspace output deserves an artifact record

Decision:

- use `workspace output` as the umbrella term for task results
- do not use `artifact` as the umbrella term for all workbench results

### Canvas document

A `canvas document` is a structured, revisitable editable work product inside the workbench domain.

Examples:

- a plan document with sections
- a research canvas with ordered blocks
- a draft that the user can reopen and continue editing

Rules:

- a canvas document is document-oriented, not file-oriented
- it should have its own domain identity and schema
- it may optionally be exported to one or more artifacts
- it should not be modeled as “just another downloaded file”

Decision:

- `canvas document` is distinct from `artifact`
- if the user edits/reopens/iterates in-product, that object should be a canvas document, not only an artifact

## Relationship model

- `asset`: shipped input to the product
- `workspace output`: any runtime result produced by a task
- `artifact`: downloadable persisted file result
- `canvas document`: editable persisted document result

Containment:

- assets are outside the task-result hierarchy
- artifacts and canvas documents are both kinds of workspace output
- one task may produce zero or more workspace outputs
- one canvas document may later export one or more artifacts

## What not to do

- do not call bundled theme/logo/static resources `artifacts`
- do not call every task result an `artifact`
- do not collapse editable canvas state into chat-style file downloads
- do not use `workspace` and `canvas` as synonyms

## Minimal data-model implication

For the next workbench slice, task records should treat outputs as references, not inline ad hoc blobs.

Recommended direction:

- `workbench_task`
  - `task_id`
  - `task_kind`
  - `status`
  - `prompt`
  - `session_id`
  - `project_id`
  - `created_at`
  - `updated_at`
  - `error_detail`
- `workbench_task_event`
  - durable lifecycle and step timeline
  - stable event names and per-task ordering
  - metadata for progress, retrieval stages, and future output refs
- `workbench_task_output` can wait until richer execution exists

Before execution lands, the task record only needs enough shape to support:

- creation
- polling
- future linkage to outputs

After minimal execution lands, the next shared runtime seam should be event-oriented before output-oriented.

Current companion seam:

- `workbench source registry`
  - declarative inventory for `web`, `knowledge`, and future connector-backed retrieval
  - task requests should resolve source ids through this registry instead of treating connector strings as opaque input

## Immediate implication for the next step

The minimal task-status skeleton is now landed. The next workbench slice should preserve the same terminology while extending execution cautiously.

Current Phase 17B reality:

1. `POST /api/workbench/tasks`
   returns `task_id`, `task_kind`, `status`, `created_at`
2. `GET /api/workbench/tasks/{task_id}`
   returns lifecycle metadata plus optional `error_detail` and, for completed `plan` tasks, a minimal inline markdown `result`
3. `GET /api/workbench/tasks/{task_id}/events`
   returns a durable ordered event timeline for lifecycle polling
4. status enum remains:
   `queued`, `running`, `completed`, `failed`
5. `task_kind = plan` was the first execution slice, but it is no longer the only runnable task kind
6. inline `plan` result is a narrow MVP compromise, not a license to treat every future workspace output as an inline task blob

Current Phase 17C reality:

1. `browse` and `deep_research` now run a minimal retrieval pipeline over the shared source registry
2. retrieval progress is recorded as task events before terminal completion/failure
3. completed browse/research results may include citations, but they still return as inline task results for now
4. `web` remains registered but not runtime-ready; `knowledge` is the current runnable retrieval source
5. this is still a bridge phase, not the final `workspace output` model

## Naming recommendation

Use these names consistently:

- `asset` for bundled/static product resources
- `artifact` for generated downloadable files
- `workspace output` for the umbrella result category
- `canvas document` for editable structured work products

If only one new runtime table lands next, it should be task-oriented, not canvas-oriented and not artifact-oriented.
