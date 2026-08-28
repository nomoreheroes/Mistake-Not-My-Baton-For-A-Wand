# D0-06 — Fixture reproducibility evidence v1

- **Result:** pass
- **Started:** `2026-08-28T10:53:56.3628020+03:00`
- **Finished:** `2026-08-28T10:54:04.2593378+03:00`

## Test

A clean `--no-local` clone of the Pipeline Git was checked out detached at
`3021a7c05bb685be671a2bf205cfcc7996ec45d7`. The clone was clean, its tree was
`8b60d12e418eb152bff1e25f86465eae6a7bbc58`, and it contained no `projects/` directory.
The committed fixture spec had SHA-256
`6b188e11fa1ea35dbd8b487956e82e0d2ad05d06f5121b1c330b56cd6b3f4a8a`.

The materializer from that clone was run twice into different new directories with both the
expected spec hash and expected fixture commit supplied as fail-closed arguments. Both runs
reported:

```text
fixture_commit=192a5b1e9e312b78c310184cde0fc3377c51ab1b
fixture_tree=93a9b120c6284bb4b094ab1efd3784582597452d
object_format=sha1
status=clean
```

The official materialized repository at `projects/pipeline-v2-fixture` was then cloned with
`--no-local`. Its clone resolved to the same commit and tree and had clean status. `git fsck
--full --strict` passed for the Pipeline clone, both independently materialized repositories,
and the fixture clone.

The materialized commit object has the fixed identity and timestamp:

```text
author Pipeline Fixture <pipeline-fixture@example.invalid> 946684800 +0000
committer Pipeline Fixture <pipeline-fixture@example.invalid> 946684800 +0000
message Initialize Pipeline v2 canonical fixture v1
```

Git emitted warnings that the host global excludes file was unreadable. The warnings were
non-blocking: all statuses were clean, the clone spec hash matched, and the materializer sets
`GIT_CONFIG_NOSYSTEM=1`, an empty global config, `core.autocrlf=false`, `core.filemode=false`,
and `commit.gpgsign=false` for deterministic repository construction.

The temporary verification root was path-checked beneath the OS temporary directory before
scoped removal. The official fixture and both persistent worktrees remained clean afterward.
