# GOAT AI Rollback Runbook

This runbook covers application rollback on the shared-host deployment path.

## Scope

- App rollback targets: previous known-good commit, tag, or maintenance branch
- Deploy scripts: `deploy.sh` and `deploy.ps1`
- Database rollback companion: [BACKUP_RESTORE.md](BACKUP_RESTORE.md)

## 1) Pick a known-good ref

Prefer the most recent release tag or a verified commit that passed the post-deploy contract check.

Examples:

```bash
git log --oneline --decorate -n 10
git tag --sort=-creatordate
```

## 2) Stop the current deployment gracefully

Use the deploy script stop path first. It now waits for a graceful drain before forcing cleanup.

Linux:

```bash
kill "$(cat logs/fastapi.pid)"
```

Windows:

```powershell
Stop-Process -Id (Get-Content .\logs\fastapi.pid)
```

If the process does not exit within the configured wait window, the deploy scripts fall back to forced cleanup.

## 3) Roll back the code checkout

Use an explicit ref instead of `main` so the deploy script stays on the rollback target.

Linux:

```bash
GIT_REF=<known-good-ref> SYNC_GIT=0 bash deploy.sh
```

Windows:

```powershell
.\deploy.ps1 -GitRef <known-good-ref>
```

If the rollback target is a tag or detached commit, keep `SYNC_GIT=0` and do not reset to origin/main.

## 4) Reuse the existing virtualenv when possible

If dependency files did not change, the existing environment can usually be reused.

If dependencies changed, reinstall them before the deploy check:

```bash
python -m pip install -r requirements.txt
cd frontend
npm ci
```

## 5) Validate the rollback

Run the same post-deploy contract check that production uses:

```bash
python scripts/post_deploy_check.py --base-url http://127.0.0.1:62606
```

Confirm at least:

- `GET /api/health`
- `GET /api/system/runtime-target`
- `POST /api/chat` streams SSE again with at least one `token` or `thinking` frame (same rule as `scripts/post_deploy_check.py`)

## 6) If data was affected

If the rollback is caused by a database change, restore the latest safe backup after the code rollback succeeds.

Follow [BACKUP_RESTORE.md](BACKUP_RESTORE.md) for the backup and restore drill.

## 7) If rollback fails

- Return to the last working ref
- Inspect `logs/fastapi.log` and the deploy output
- Re-run the post-deploy contract check before trying another ref
