# Contributing to GOAT AI

## Environment variables

When adding or renaming runtime configuration, update [`.env.example`](.env.example) in the same change so operators can discover new keys. Never commit real secrets; use placeholders only.

## Secret scanning

CI may run an informational Gitleaks pass on pushes and pull requests. If it flags a false positive, adjust `.gitleaksignore` with a narrow justification in the PR description.
