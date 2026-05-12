# Bootstrap Audit Report

## 1. Audit Status

FAIL

## 2. Workspace Validation

- Workspace path matches spec: PASS
- Workspace not in forbidden location: PASS
- Required directories exist: PASS

## 3. Artifact Transfer Validation

- Staging YAML transferred: PASS
- Staging Markdown transferred: PASS
- Transferred files valid: PASS

## 4. Script Validation

- Required scripts exist: PASS
- Forbidden operations detected: PASS
- Detected forbidden patterns: []

## 5. SQLite Validation

- SQLite validation mode: static_and_runtime
- Required tables exist: PASS
- Schema matches spec: PASS
- Undocumented tables: []

## 6. Pipeline Graph Validation

- Graph valid: FAIL (missing file)

## 7. Runtime Files Validation

- README valid: PASS
- .gitignore valid: PASS
- pyproject.toml valid: PASS

## 8. Security Validation

- Secrets detected: PASS
- Destructive operations detected: PASS
- Workspace created under owner path: PASS

## 9. Idempotency Validation

- Rerun safe: PASS
- Overwrite risks detected: PASS

## 10. Drift Detection

- Undocumented directories: []
- Undocumented files: []
- Undocumented tables: []
- Undocumented graph changes: []

## 11. Warnings

- Undocumented scripts: Additional scripts generated beyond required ones

## 12. Failures

- Missing pipeline graph: pipeline_graph.yaml is missing despite bootstrap_result claiming it exists (critical)
- Execution plan location: bootstrap_execution_plan.yaml is in pipeline/generated/ instead of artifacts/machine/P0/ (major)

## 13. Readiness for P0.4

Not ready due to critical failures.