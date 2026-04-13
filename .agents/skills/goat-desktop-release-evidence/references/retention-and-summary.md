# Retention and Summary Contracts

Primary tests:

- [test_desktop_release_governance.py](../../../../__tests__/desktop/test_desktop_release_governance.py)
- [test_packaged_shell_fault_smoke.py](../../../../__tests__/desktop/test_packaged_shell_fault_smoke.py)
- [test_installed_windows_desktop_fault_smoke.py](../../../../__tests__/desktop/test_installed_windows_desktop_fault_smoke.py)

Important retained evidence concepts:

- packaged PR failures should keep build logs, packaged smoke logs, and `summary.json`
- installed release and drill failures should keep `desktop-installed-smoke/*/summary.json`
- top-level summary fields such as installer kind, workflow context, healthy launch status, and primary failure should stay aligned with the runbooks

If workflows, tools, and runbooks disagree about what is retained or how it is summarized, treat that as a governance gap rather than a documentation-only nit.
