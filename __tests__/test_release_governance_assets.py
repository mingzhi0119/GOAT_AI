from __future__ import annotations

from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


def test_release_workflow_promotes_one_immutable_bundle_with_promotion_evidence() -> (
    None
):
    workflow = (
        REPO_ROOT / ".github" / "workflows" / "release-governance.yml"
    ).read_text(encoding="utf-8")

    assert "python -m tools.build_release_bundle" in workflow
    assert workflow.count("actions/upload-artifact@v4") >= 4
    assert workflow.count("actions/download-artifact@v4") >= 4
    assert "release-bundle.tar.gz" in workflow
    assert "release-manifest.json" in workflow
    assert "RELEASE_BUNDLE=" in workflow
    assert "RELEASE_MANIFEST=" in workflow
    assert "staging-promotion-evidence.json" in workflow
    assert "production-promotion-evidence.json" in workflow
    assert '--owner-id "${STAGING_OWNER_ID}"' in workflow
    assert '--owner-id "${PRODUCTION_OWNER_ID}"' in workflow
    assert "SYNC_GIT=1" not in workflow


def test_deploy_scripts_support_bundle_installs_and_exact_ref_deploys() -> None:
    deploy_sh = (REPO_ROOT / "deploy.sh").read_text(encoding="utf-8")
    deploy_ps1 = (REPO_ROOT / "deploy.ps1").read_text(encoding="utf-8")

    assert 'EXPECTED_GIT_SHA="${EXPECTED_GIT_SHA:-}"' in deploy_sh
    assert 'RELEASE_BUNDLE="${RELEASE_BUNDLE:-}"' in deploy_sh
    assert 'RELEASE_MANIFEST="${RELEASE_MANIFEST:-}"' in deploy_sh
    assert (
        '"${PYTHON_BIN}" "${SCRIPT_DIR}/tools/install_release_bundle.py"' in deploy_sh
    )
    assert 'git show-ref --verify --quiet "refs/remotes/origin/${GIT_REF}"' in deploy_sh
    assert 'git reset --hard "origin/${GIT_REF}"' in deploy_sh
    assert 'git rev-parse --verify "${GIT_REF}^{commit}"' in deploy_sh

    assert "[string]$ExpectedGitSha = $env:EXPECTED_GIT_SHA" in deploy_ps1
    assert "[string]$ReleaseBundle = $env:RELEASE_BUNDLE" in deploy_ps1
    assert "[string]$ReleaseManifest = $env:RELEASE_MANIFEST" in deploy_ps1
    assert r"tools\install_release_bundle.py" in deploy_ps1
    assert 'git show-ref --verify --quiet "refs/remotes/origin/$Ref"' in deploy_ps1
    assert 'git reset --hard "origin/$Ref"' in deploy_ps1
    assert 'git rev-parse --verify "$($Ref)^{commit}"' in deploy_ps1
