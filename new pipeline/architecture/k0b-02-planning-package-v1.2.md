# K0b-02 artifact/event planning package v1.2

Status: implemented fixture architecture; runtime authority remains none.

## Authority and scope

This package implements only the bounded K0b-02 fixture artifact/event workflow approved by request `b04ae991fbc6358eeb26b2feda00ff85abad7eadb378c4e188072431fa97c75d`. It does not activate Alpha0, F15, model execution, dispatch, deployment, or any remote Git effect.

The authored source is `alpha0-routing-contract-v2.json`. Compiler A owns six registry and routing outputs, including the projection checkpoint profile. Compiler B consumes the complete A receipt and all six A hashes, then owns three resource and checkpoint outputs. The integrated manifest binds both receipts and all nine physical files. The resource policy v3 changes identity, predecessor, and its phase-fence locator only; its numerical policy remains unchanged.

## Durable workflow

A single SQLite writer commits the canonical decision version, the unchanged `projection.requested` v1 event payload, and one outbox row in a short `BEGIN IMMEDIATE` transaction. A canonical duplicate returns the original identifiers. A conflicting duplicate and any pair stem other than the exact singleton `fixture-decision` fail before mutation.

The projector claims ordered outbox work and creates a deterministic LF JSON-as-YAML file plus a Markdown peer containing the complete source and hash headers. Each same-directory candidate is closed, flushed, read back, and atomically replaced. A pair becomes ready only after both peers agree on source sequence, profile, and bytes. Projection receipt sequencing remains separate from canonical source sequencing.

The publisher records a durable intent, creates a closed and verified SQLite backup, atomically installs the checkpoint, stages exactly the checkpoint and two projection peers, commits those three paths in a fixture-only Git repository, reads back the footer, tree, blobs, and worktree bytes, and only then records the SQLite publication result. The next checkpoint may contain the previous verified result; it cannot contain its own future commit identity.

Every normal fixture repository sets local `core.autocrlf=false` and `core.eol=lf`, disables hooks and signing, uses an explicit temporary identity, and has no remote before a publisher or replay effect. Both projection worktree hashes must equal their Git blob hashes. The two isolated EOL tests may deliberately use `core.autocrlf=true`; they perform one seed commit, no publication, and are discarded with the case root.

## Replay and reconciliation

Replay clones only the coordination fixture with `--no-hardlinks --no-checkout`, applies and verifies the LF policy, removes the generated local origin, then checks out. The initially seeded invocation envelope is immutable and externally hash-bound. The current source cut comes from the verified checkpoint, pair, and publication lineage. Restore always targets an admitted new file. Missing or changed envelopes, incompatible schemas, corruption, and ambiguous begun effects block.

Reconciliation distinguishes no known external effect, one uniquely identified Git effect, an already terminal result, and an ambiguous effect. A known commit can be recorded once; the design makes no general exactly-once claim across SQLite, files, and Git.

## Phase and budget boundaries

The fixture has two chronological exhaustive phases: `K0b-runtime-operational` and `K0b-F15-exact-measurement`. The successor requires a terminal predecessor seal and reconciled high water. Seals are immutable. Tests preserve the exact four F15 trigger identifiers, label all F15 counters synthetic, record zero provider/model calls, and reject post-F15 calls.

The unchanged budget uses an assumed mean of 372736 bytes, a 655360-byte hard producer-object bound, 7864320 size-stress binary bytes, 22020096 nonbinary bytes, a 30408704-byte rounded checkpoint stress, 34 publications, planning pack factor one, and zero credits. A checkpoint must remain strictly below 104857600 bytes; phase warning and hard limits are 536870912 and 1073741824 bytes; a batch contains at most twelve publications. The fixture p95 bounds are strictly below ten seconds for publication and 120 seconds for clone-only restore.

## Failure and validation model

Exception injection and actual owned-process termination cover the twelve approved durability boundaries. Recovery is assessed from independent SQLite, filesystem, Git commit, Git blob, clone file, footer, counter, and seal readbacks. The two locked environments compile byte-identical canonical outputs and run all 80 named cases without skips. Binary SQLite files are compared by logical and typed identity while their actual environment-specific complete hashes are retained.

The state materialization changes exactly the twelve approved fields, leaves seven open and ten closed gate records unchanged, and keeps global and K0b-02 runtime authority at `none`.
