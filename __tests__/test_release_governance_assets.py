from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_release_workflow_verifies_requested_ref_and_resolved_sha() -> None:
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "release-governance.yml"
    ).read_text(encoding="utf-8")

    assert workflow.count("ref: ${{ inputs.release_ref }}") >= 3
    assert (
        "EXPECTED_GIT_SHA='${{ needs.release-manifest.outputs.resolved_sha }}'"
        in workflow
    )
    assert '--owner-id "${STAGING_OWNER_ID}"' in workflow
    assert '--owner-id "${PRODUCTION_OWNER_ID}"' in workflow


def test_deploy_scripts_sync_exact_requested_ref() -> None:
    deploy_sh = (REPO_ROOT / "deploy.sh").read_text(encoding="utf-8")
    deploy_ps1 = (REPO_ROOT / "deploy.ps1").read_text(encoding="utf-8")

    assert 'EXPECTED_GIT_SHA="${EXPECTED_GIT_SHA:-}"' in deploy_sh
    assert 'git show-ref --verify --quiet "refs/remotes/origin/${GIT_REF}"' in deploy_sh
    assert 'git reset --hard "origin/${GIT_REF}"' in deploy_sh
    assert 'git rev-parse --verify "${GIT_REF}^{commit}"' in deploy_sh

    assert "[string]$ExpectedGitSha = $env:EXPECTED_GIT_SHA" in deploy_ps1
    assert 'git show-ref --verify --quiet "refs/remotes/origin/$Ref"' in deploy_ps1
    assert 'git reset --hard "origin/$Ref"' in deploy_ps1
    assert 'git rev-parse --verify "$($Ref)^{commit}"' in deploy_ps1
