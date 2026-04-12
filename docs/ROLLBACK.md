# GOAT AI Rollback Runbook

This runbook covers rollback on the shared-host deployment path.

## Scope

- Preferred rollback target: previous known-good release bundle + manifest
- Fallback rollback target: previous known-good ref when an artifact is unavailable
- Deploy scripts: canonical files under `ops/deploy/`, with supported repository-root wrappers `deploy.sh` and `deploy.ps1`
- Database rollback companion: [BACKUP_RESTORE.md](BACKUP_RESTORE.md)

## 1) Pick a known-good rollback target

Prefer the most recent retained release artifact that passed the post-deploy contract check.

Use these sources in order:

1. The release workflow artifacts for the known-good run (`release-bundle.tar.gz`, `release-manifest.json`).
2. The currently deployed host metadata:
   - `<project>/release-manifest.previous.json`
   - `<project>/release-manifest.json`
3. A verified ref or tag only when the matching artifact is unavailable.

## 2) Stop the current deployment gracefully

Use the deploy script stop path first. It waits for a graceful drain before forcing cleanup.

Linux:

```bash
kill "$(cat logs/fastapi.pid)"
```

Windows:

```powershell
Stop-Process -Id (Get-Content .\logs\fastapi.pid)
```

If the process does not exit within the configured wait window, the deploy scripts fall back to forced cleanup.

## 3) Prefer artifact-first rollback

Linux:

```bash
PROJECT_DIR=/srv/goat-ai \
RELEASE_BUNDLE=/tmp/release-bundle.tar.gz \
RELEASE_MANIFEST=/tmp/release-manifest.json \
EXPECTED_GIT_SHA=<known-good-sha> \
bash deploy.sh
```

Windows:

```powershell
.\deploy.ps1 -ProjectDir C:\GOAT_AI -ReleaseBundle C:\temp\release-bundle.tar.gz -ReleaseManifest C:\temp\release-manifest.json -ExpectedGitSha <known-good-sha>
```

This path reinstalls the retained bundle and does not rebuild the frontend on the host.

## 4) Use explicit ref rollback only as a fallback

If no retained artifact exists, use an explicit ref instead of `main` so the deploy script stays on the rollback target.

Linux:

```bash
GIT_REF=<known-good-ref> SYNC_GIT=0 bash deploy.sh
```

Windows:

```powershell
.\deploy.ps1 -GitRef <known-good-ref>
```

If the rollback target is a tag or detached commit, keep `SYNC_GIT=0` and do not reset to `origin/main`.

## 5) Reuse the existing virtualenv when possible

If dependency files did not change, the existing environment can usually be reused.

If dependencies changed, reinstall them before the deploy check:

```bash
python -m pip install -r requirements.txt
```

## 6) Validate the rollback

Run the same post-deploy contract check that production uses:

```bash
python scripts/post_deploy_check.py --base-url http://127.0.0.1:62606
```

For data-bearing rollbacks, rehearse the SQLite side separately before the maintenance window:

```bash
python -m scripts.exercise_recovery_drill --src /path/to/chat_logs.db --backup-dir /path/to/backups --required-table sessions --required-table session_messages
```

For code artifact rollback rehearsal, exercise the bundle flow against a scratch project tree:

```bash
python -m scripts.exercise_release_rollback_drill \
  --known-good-bundle /path/to/known-good-release-bundle.tar.gz \
  --known-good-manifest /path/to/known-good-release-manifest.json \
  --candidate-bundle /path/to/candidate-release-bundle.tar.gz \
  --candidate-manifest /path/to/candidate-release-manifest.json \
  --project-dir /tmp/goat-release-rollback-drill
```

Confirm at least:

- `GET /api/health`
- `GET /api/system/runtime-target`
- `POST /api/chat` streams SSE again with at least one `token` or `thinking` frame (same rule as `scripts/post_deploy_check.py`)

## 7) If data was affected

If the rollback is caused by a database change, restore the latest safe backup after the code rollback succeeds.

Follow [BACKUP_RESTORE.md](BACKUP_RESTORE.md) for the backup and restore drill.

## 8) If rollback fails

- Return to the last working artifact or ref
- Inspect `logs/fastapi.log`, deploy output, and the desktop/runtime promotion evidence
- Re-run the post-deploy contract check before trying another rollback target
