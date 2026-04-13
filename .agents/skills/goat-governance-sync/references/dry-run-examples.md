# Dry-Run Examples

## Example 1

User asks:
- "This slice looks landed now; should the wording move into `ROADMAP.md`, `PROJECT_STATUS.md`, or an ops doc?"

First moves:
- read [doc-ownership-map.md](doc-ownership-map.md), [status-vs-roadmap-rules.md](status-vs-roadmap-rules.md), and [governance-edit-checklist.md](governance-edit-checklist.md)
- confirm the proof is already landed in code, workflows, or tests before choosing a document owner
- keep repo-internal proof separate from external blockers

Expected output:
- identify the owning document
- explain why the other governance docs should not move yet
- name the proof files or tests that justify the wording

Validate with:
- reread the owning doc after editing and rerun any governance or ops-asset tests tied to that truth surface

## Example 2

User asks:
- "Read-only triage: we just forward-tested the repo-native skills; what should change in governance docs, and what should stay as future work?"

First moves:
- treat the live forward-test results as landed proof for the completed slice
- keep shipped-status language out of `ROADMAP.md` unless the only change is narrowing the remaining work
- avoid promoting the skill layer into `PROJECT_STATUS.md` until the roadmap follow-on says it is stable enough

Expected output:
- say whether the update belongs in `ROADMAP.md`, `PROJECT_STATUS.md`, or neither
- name the remaining follow-on work after the completed forward-test pass
- call out any external or non-repo blockers separately

Validate with:
- re-read the touched governance docs and keep their roles consistent with `AGENTS.md`
