# Legacy Pipeline successor blob-provenance corrigendum

Corrigendum ID: `pipeline-v2.legacy-pipeline-successor-blob-provenance-corrigendum-v1`; version `1.0.0`.

Recorded: 2026-09-25.

Status: `owner-approved append-only documentation remediation materialized; LSR-F01 remains open pending fresh-context independent re-review; runtime authority none`.

This corrigendum adds reproducible Git-blob provenance for the immutable Legacy Pipeline successor package. It neither replaces nor edits the original manifest or its historical evidence. It does not revise semantic-delta results, applicability, a plan, state, a gate, implementation, or runtime authority.

## 1. Authority and exact evidence

| Input | SHA-256 | Bytes | Role |
|---|---|---:|---|
| `requests/legacy-pipeline-successor-blob-provenance-corrigendum-approval-request-v1.yaml` | `e232ee0fc3fc8351a29cf4488a2d7e167319e9035b944743d644a349bfe6491c` | 261616 | exact-scope authority and exhaustive 170-row binding registry |
| `decisions/legacy-pipeline-successor-blob-provenance-corrigendum-owner-disposition-v1.yaml` | `edceb0e58fafd7854f0165c53a1ade4b15e2bba6fdb345c3488d0c25a7e4a9f5` | 6956 | owner disposition and closure boundary |
| `evidence/legacy-pipeline-successor-blob-provenance-corrigendum-v1.yaml` | `027f808fc052910f9984ce1418d63c3696495358d415fcae945ee69f37026bfe` | 13714 | materialized projection and verification evidence |
| `reviews/legacy-pipeline-successor-snapshot-independent-review-v1.yaml` | `83cbd72df6f6755b6ab606384b06278a2f18a9698062f2ed18189ab6d0b1f03b` | 17609 | source of blocking finding `LSR-F01` |
| `references/legacy-pipeline-successor-2026-09-23/manifest-v1.yaml` | `37a18ca9935948511eaf757660f4485bf11ea9f06a59158f42293f985fdee880` | 178435 | immutable historical successor manifest; not rewritten |

The package baseline is HEAD `9ed4a396412038098887245ad2e83b8f66723e72`, parent `1129f160b2d62af422d64b7c38fbb5ec19c708aa`, tree `a875e12ee01f91b85358cd0cdf21b8a2e62b9e2e`.

The approval request's `git_blob_read_set.entries` array is the single exhaustive registry for all 170 baseline Git blob object IDs, SHA-256 values and byte sizes and for all 21 committed normalized overlay bindings. Its `mismatch_inventory.exact_mismatches` array is the single exhaustive 51-row mismatch registry. The evidence document projects and verifies those bound facts without creating a competing registry.

## 2. Cause and correction

The independent review found that 51 `base_raw` bindings in the historical manifest describe checkout-observed bytes affected by line-ending conversion rather than the exact LF blobs committed at baseline `84b390ef281a31caa119023c5dee61fceaa25439`. The historical roots are internally consistent with their captured bytes, so this corrigendum preserves them and corrects only their provenance interpretation.

The corrected roles are:

| Historical root | Preserved SHA-256 | Correct role |
|---|---|---|
| base manifest | `73afe757944d57be910727ab4ebc580941eb741b95ad7e318ea629d65b903597` | worktree-observed base provenance at successor capture |
| successor raw manifest | `2ea156ba85b5387b3ccea02392dd13a974fb529b600fc6634609044290da83f8` | mixed 149 worktree-observed unchanged plus 21 external-source raw changed provenance |
| unchanged raw subset | `ce227e2575a3694e13721752addbc77accfebb6a47018516493806a30e581697` | worktree-observed 149-path unchanged-subset provenance |

No historical root, manifest row, review record or prior evidence is deleted, edited or silently reinterpreted as a Git-blob root.

## 3. Reproducible projection profiles

The new profiles use exact bytes returned by `git cat-file blob`, held in memory. Baseline bytes resolve from `84b390ef281a31caa119023c5dee61fceaa25439:old pipeline/<relative_path>`. The 21 changed successor bytes resolve from committed LF-normalized overlay blobs at `b7887957c854825044b448a0ff6a1e84e2ab6562`. No checkout, live source or temporary target participates.

Each manifest line is `relative_path<TAB>lowercase_sha256<TAB>decimal_bytes<LF>`, encoded UTF-8 without BOM, sorted with .NET `StringComparer.Ordinal`, and terminated by exactly one LF.

| Profile | Paths | Content bytes | Manifest bytes | Manifest SHA-256 |
|---|---:|---:|---:|---|
| `baseline_git_blob_base_manifest_v1` | 170 | 11017109 | 21817 | `038069326933d295d67ea32d98c07c7ff4e5c389283ed519c8566b9c921b454e` |
| `baseline_git_blob_unchanged_subset_manifest_v1` | 149 | 7539344 | 19215 | `7bab2c12c9633c03f1ab32d879f26741b42d99004aeea8a6899f486a3e36bb8f` |
| `baseline_git_blob_plus_committed_normalized_overlay_successor_manifest_v1` | 170 | 11313521 | 21818 | `c90e1b0854ffbc78661ae728a4581a8c1aae91cc0ca84a09e10f3bb23bafc2c2` |

The combined profile is deliberately not called `successor_raw`: its changed side consists of normalized committed overlay blobs, while its unchanged side consists of exact baseline blobs. The path partition is complete and disjoint: 170 total, 149 unchanged and 21 changed-overlay paths.

## 4. Finding disposition

This package materializes the proposed append-only remediation for `LSR-F01`. It does not close the finding. Closure requires a separately authorized fresh-context, read-only, non-author independent re-review and then a separate owner disposition based on that result.

The correction is provenance-only. Existing normalized roots, the 148/3 prompt-snapshot partition, all three `K0b04_impact` semantic-delta classifications, the 21-row applicability routing, development and architecture plans, K0b-03 planning package v1.1, state, STATE projection, renderer/profile, statuses and gates remain unchanged.

`LSR-F02` through `LSR-F05` remain recorded without remediation:

- `LSR-F02`: worktree line-ending and `core.autocrlf` reproducibility risk remains under separate maintenance authority.
- `LSR-F03`: explicit BOM transform-order hygiene remains a future request-contract concern.
- `LSR-F04`: historical authority-chain uniformity remains immutable; this package uses a uniform confirmed-request hash.
- `LSR-F05`: development-plan v0.14 adoption remains a separate transaction.

## 5. Single-source and authority boundaries

The new projection profiles are documentary reproducibility evidence, not a prompt registry, plan, implementation input, runtime allowlist or authority to import legacy text. Their only purpose is to make the predecessor and combined successor bytes reproducible from committed objects.

The original successor manifest remains historical evidence. The corrigendum has precedence only for the provenance role of the three historical roots and for the new Git-blob profiles. It does not supersede raw external-source provenance, normalized overlay bindings, applicability categories or semantic classifications.

The live `C:/Projects/software_workflow` source was not read. No `.gitattributes`, `.git/config`, `core.autocrlf`, worktree normalization, code, test, dependency, network, locked environment or temporary target was used or changed.

## 6. Re-review and stop boundary

The next logical checkpoint is mandatory independent re-review. The reviewer must be fresh-context, read-only and non-author; must reproduce all 170 baseline and 21 overlay bindings, the 170/149/21 partition, 51 mismatches and three roots from Git blobs; and must verify that no historical document changed. A reviewer recommendation is not owner approval.

Use stops on any baseline, object ID, blob hash, size, path partition, mismatch set, manifest profile, root, package inventory, plan, state or gate mismatch. It also stops if a live source read, checkout-byte substitution, repository-code execution, network, dependency, locked environment, temporary target or runtime effect is required.

Runtime authority remains `none`. `G-K0B03-UNTRUSTED-SHAPES` remains open, and no K0b-03, K0b-04, K0b-05 or N1 execution is authorized.
