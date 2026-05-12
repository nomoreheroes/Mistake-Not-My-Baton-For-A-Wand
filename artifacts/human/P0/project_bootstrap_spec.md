# Project Bootstrap Spec

## 1. Project Identity

- Project name: `1.Mistake Not My Baton For A Wand`
- Project slug: `1-mistake-not-my-baton-for-a-wand`
- Local workspace path: `C:\Projects\software_workflow 2.0\Projects\1.Mistake Not My Baton For A Wand`
- Path source: explicit owner input only

## 2. Output Files and Handoff to P0.2

This P0.1 output produces both machine-readable and human-readable bootstrap spec artifacts.

- Machine-readable spec path: `./pipeline_staging/project_bootstrap_spec.yaml`
- Human-readable spec path: `./pipeline_staging/project_bootstrap_spec.md`
- Next node: P0.2 Bootstrap Script Generator

P0.2 is expected to use these artifacts to initialize the real project workspace and move the bootstrap files from staging.

## 3. Directory Structure

Required structure under the project root:

- `artifacts/`
  - `machine/`
  - `human/`
  - `snapshots/`
  - `audits/`
  - `meta/`
- `pipeline/`
  - `prompts/`
    - `meta_audit/`
  - `schemas/`
  - `tests/`
  - `generated/`
  - `pipeline_graph.yaml`
- `pipeline_state/`
  - `pipeline.db`
  - `events.jsonl`
- `scripts/`
- `logs/`
- `README.md`
- `.gitignore`
- `pyproject.toml`

## 4. Artifact Storage Policy

- Machine-readable artifacts are preferred in YAML, with JSON as a secondary option.
- Human-readable artifacts are stored as Markdown.
- Artifact versioning policy is immutable, and overwrites must not occur without backup.

## 5. SQLite State Database

- Database engine: `sqlite`
- Database path: `pipeline_state/pipeline.db`
- Event log path: `pipeline_state/events.jsonl`

The schema includes required tables for products, pipeline_runs, artifacts, artifact_links, events, decisions, issues, revision_requests, hitl_signoffs, prompt_versions, meta_audits, and pipeline_patches.

## 6. Git Policy

- Initialize repository: `true`
- Default branch: `main`
- Remote URL: `null`
- Initial commit: `false`

Ignore patterns include:

- `.venv/`
- `__pycache__/`
- `*.pyc`
- `.env`
- `*.sqlite-wal`
- `*.sqlite-shm`

## 7. Runtime Policy

- Primary language: `python`
- Python version: `3.11`
- Package manager: `uv`
- Virtual environment path: `.venv`

## 8. Security and Idempotency

- Do not store secrets in the repository.
- `.env` files are allowed locally but must not be committed.
- `env.example` files may be committed.
- Destructive operations are disallowed without explicit owner confirmation.
- Network operations are not allowed by default.
- Existing directory use is allowed, but existing files must not be overwritten without backup.

## 9. Required Bootstrap Checks

Required checks before P0.4 include:

- Git repository initialization
- SQLite database creation
- Required SQLite tables presence
- Artifact directory presence
- Prompt registry presence
- `pipeline_graph.yaml` validity

## 10. Open Questions

No open questions remain for this bootstrap spec.

## 11. Readiness for P0.2

The bootstrap spec is ready for P0.2.

- Staging artifacts have been saved.
- Handoff to P0.2 is defined with the required inputs and start condition.
- Self-audit confirms readiness for the next node.
