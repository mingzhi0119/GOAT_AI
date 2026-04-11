# Workbench Terminology Decision

Last updated: 2026-04-10

This document is a terminology decision record, not a runtime status page.

Its purpose is to keep backend, frontend, docs, and future storage design aligned on a small set of words that must not drift.

## Decision Summary

Use these terms distinctly:

- `asset`
- `artifact`
- `workspace output`
- `canvas document`

They are related, but they are not interchangeable.

## Canonical Definitions

### Asset

An `asset` is a shipped or operator-provided static resource that exists independently of any user task.

Examples:

- theme palette data
- school logos
- default templates
- bundled icons
- demo/example files

Rules:

- assets are part of the app/package/repo surface, not user-generated runtime output
- assets do not need task ids
- assets are usually addressed by stable file path or build path, not by runtime record id
- changing an asset is a product/repo change, not a user work-product change

### Artifact

An `artifact` is a persisted generated file produced by the system for a user, session, or task and intended to be downloaded, attached, or referenced later.

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

Decision:

- chat artifacts are the current canonical `artifact` baseline
- future workbench work should extend this concept, not invent a competing term for generated files

### Workspace Output

A `workspace output` is a task-produced result that belongs to a workbench execution context, whether or not it is downloadable as a file.

Examples:

- a task status summary
- a generated plan body
- a research notes block
- a structured result bundle containing text, links, and artifact references

Rules:

- workspace output is the umbrella runtime-result term
- an artifact can be one kind of workspace output
- a canvas document can be one kind of workspace output
- not every workspace output deserves an artifact record

Decision:

- use `workspace output` as the umbrella term for task results
- do not use `artifact` as the umbrella term for all workbench results

### Canvas Document

A `canvas document` is a structured, revisitable, editable work product inside the workbench domain.

Examples:

- a plan document with sections
- a research canvas with ordered blocks
- a draft the user can reopen and continue editing

Rules:

- a canvas document is document-oriented, not file-oriented
- it should have its own domain identity and schema
- it may optionally be exported to one or more artifacts
- it should not be modeled as “just another downloaded file”

Decision:

- `canvas document` is distinct from `artifact`
- if the user edits, reopens, or iterates in-product, that object should be modeled as a canvas document, not only an artifact

## Relationship Model

- `asset`: shipped input to the product
- `workspace output`: any runtime result produced by a task
- `artifact`: downloadable persisted file result
- `canvas document`: editable persisted document result

Containment:

- assets are outside the task-result hierarchy
- artifacts and canvas documents are both kinds of workspace output
- one task may produce zero or more workspace outputs
- one canvas document may later export one or more artifacts

## What Not To Do

- do not call bundled theme/logo/static resources `artifacts`
- do not call every task result an `artifact`
- do not collapse editable canvas state into chat-style file downloads
- do not use `workspace` and `canvas` as synonyms

## Modeling Direction

Recommended direction for future runtime/storage work:

- task records should treat outputs as references, not as ad hoc inline blobs
- lifecycle and step timelines should stay event-oriented
- richer output tables can land later, but the terminology should not change

Minimal implication:

- `workbench_task` remains task-oriented
- `workbench_task_event` remains timeline-oriented
- any future `workbench_task_output` or equivalent table should use `workspace output` as the umbrella concept

## Naming Recommendation

Use these names consistently:

- `asset` for bundled/static product resources
- `artifact` for generated downloadable files
- `workspace output` for the umbrella result category
- `canvas document` for editable structured work products
