# D0-04 — Legacy Swarm relocation and product-tree hygiene receipt

**Status:** verified relocation and product hygiene  
**Verified:** 2026-08-26T13:34:19.8174398+03:00  
**Human authorization:** explicit workspace-owner approval in the current conversation; no stable approval envelope existed yet

## Sequence note

The planned order placed final D0-01 decision disposition before D0-03/D0-04. The owner explicitly authorized the relocation first so that 199 MiB of legacy material could not enter a greenfield baseline while the forecast was under review. No Pipeline baseline commit, product implementation or prompt execution was performed out of order; the preserved research destination was not deleted.

## Result

The legacy snapshot was physically removed from the greenfield Swarm product tree and preserved at the separate research root:

```text
C:/Projects/1.Mistake Not My Baton For A Wand/projects/swarm/old swarm
→ C:/Projects/1.Mistake Not My Baton For A Wand/research/old-swarm
```

The initial atomic directory move was rejected by Windows with `MoveDirectoryItemIOError / access denied`. The fallback copied the exact tree, verified it, and only then removed the source. One real legacy file named `swarm-core/nul` required a Win32 extended path while cleaning the copied source because `nul` is a reserved Windows name. The destination copy still exists and is 83 bytes; it was not discarded.

## Before/after verification

| Check | Before at source | After at destination | Result |
|---|---:|---:|---|
| Files | 12,504 | 12,504 | equal |
| Bytes | 208,572,020 | 208,572,020 | equal |
| Directories including root | 1,716 | 1,716 | equal |
| Nested `.git` markers | 6 | 6 | equal |
| Source exists | yes | no | required |
| Destination exists | no | yes | required |

Nested Git inventory was preserved:

- `swarm-core/.git`
- `swarm-docs/.git`
- `swarm-gateway/.git`
- `swarm-infra/.git`
- `swarm-schemas/.git`
- `swarm-ui/.git`

The copy reported zero failed files. File count, byte count and nested Git inventory were checked before source cleanup and rechecked at the destination afterward.

A deterministic post-relocation manifest over `relative path + size + content SHA-256` for all 12,504 files has SHA-256 `5dcf97baaa9e2a8198faf7174667c3fca286e6d1ee3ac323fc8457c9985a9e48`. Because a pre-move content-manifest hash was not captured, this strengthens destination provenance but does not retroactively claim a cryptographic before/after comparison.

## Product-tree hygiene

`projects/swarm` now contains only:

- the product repository root `.git`;
- the new project-local `.gitignore`.

The scan found:

- zero nested Git markers below the product root;
- zero legacy/runtime/build roots from the D0 denylist;
- zero untracked bulk entries;
- one expected untracked control file: `.gitignore`.

The project-local ignore protects `old swarm/`, Pipeline runtime/backups and checkpoint temporary files. It deliberately does not ignore the exact tracked checkpoint `.pipeline/history/pipeline-checkpoint.sqlite3`.

The root Git ignores `research/old-swarm/`, so no legacy payload enters the Pipeline repository.

## Boundary and pending enforcement

The research snapshot is policy-classified as a separate read-only research capability: product agents must not access or execute it; a designated importer may read it. This is currently a policy statement, not an enforced fact. Filesystem ACLs were not rewritten, and harness enforcement plus its adversarial proof remain a K0-b task.

No Git commit was created by this operation. The Swarm `.gitignore` belongs to the project Git; the root `.gitignore`, plans and this YAML+Markdown receipt belong to the Pipeline Git. Their commits remain separate.
