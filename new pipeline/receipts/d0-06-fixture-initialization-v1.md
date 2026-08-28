# D0-06 — Canonical fixture initialization and binding v1

- **Status:** verified and bound
- **Canonical Pipeline source commit:** `3021a7c05bb685be671a2bf205cfcc7996ec45d7`
- **Fixture spec SHA-256:** `6b188e11fa1ea35dbd8b487956e82e0d2ad05d06f5121b1c330b56cd6b3f4a8a`
- **Materialized fixture commit:** `192a5b1e9e312b78c310184cde0fc3377c51ab1b`

## Triple binding

| Bound identity | Exact value |
|---|---|
| Pipeline commit containing canonical seed/spec | `3021a7c05bb685be671a2bf205cfcc7996ec45d7` |
| Pipeline tree | `8b60d12e418eb152bff1e25f86465eae6a7bbc58` |
| Fixture spec complete-file SHA-256 | `6b188e11fa1ea35dbd8b487956e82e0d2ad05d06f5121b1c330b56cd6b3f4a8a` |
| Fixture spec Git blob | `2a6d12ac2b6437cc8464eb826e9ad3da7a6b99ce` |
| Materialized fixture commit | `192a5b1e9e312b78c310184cde0fc3377c51ab1b` |
| Materialized fixture tree | `93a9b120c6284bb4b094ab1efd3784582597452d` |

The spec hash binds the materializer hash and expected-tree manifest hash. The manifest binds
all seven seed files by path, mode, and SHA-256 and declares the expected Git tree. The spec
also declares the deterministic fixture commit. Materialization fails if any of these values
differs.

## Repository boundaries

- The Pipeline repository is the root Git at `C:/Projects/1.Mistake Not My Baton For A Wand`.
- Canonical inputs are tracked under `new pipeline/tests/fixtures/canonical-v1/`.
- The materialized fixture is a separate Git at `projects/pipeline-v2-fixture`, ignored by the
  Pipeline Git through the exact root rule `/projects/`.
- `projects/swarm` is not the fixture. It remained clean at
  `3fb16d7fcf6c6078e41fa82d238a35eab6458b39` throughout D0-06.
- `research/old-swarm/` is identified only as the isolated read-only legacy research root. It
  was not inspected, copied, or used as a fixture input. Capability enforcement remains a
  later Foundation responsibility.

The fixture contains project-local ignore rules for active runtime, backups, previews, build,
and scratch paths. The exact future checkpoint path
`.pipeline/history/pipeline-checkpoint.sqlite3` remains allowed. Both YAML and Markdown fixture
scope records are tracked in `.pipeline/decisions/`.

## Non-self-referential sequence

1. Baseline Pipeline commit `e1130caab778c1fa2cbbf57902da11f132db66c3` was the parent.
2. Canonical seed/spec/materializer were committed as
   `3021a7c05bb685be671a2bf205cfcc7996ec45d7`.
3. That exact commit materialized fixture commit
   `192a5b1e9e312b78c310184cde0fc3377c51ab1b`.
4. This binding and its evidence are committed afterward. Their enclosing Pipeline commit is
   deliberately not embedded in their own blobs; it is obtained from Git history.

No K0a contract, prompt, SQLite schema, dispatcher, worker, or runtime was implemented.

Reproducibility evidence: `new pipeline/receipts/d0-06-fixture-reproducibility-v1.yaml`.
