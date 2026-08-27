# D0-01 — Rough full-route and checkpoint forecast

**Source YAML:** `new pipeline/decisions/d0-01-full-route-forecast.yaml`  
**Record ID:** `d0-01-full-route-forecast`  
**Status:** revision 2 validated; non-return findings N-01…N-12 applied as owner-disposition inputs; ready for owner disposition  
**Forecast class:** recalculable order-of-magnitude reference model, not a price or repository-size promise

## Corrected outcome

Revision 1 closed the original blockers. The second independent review approved the model with local changes and found two remaining forecast errors: fixture bytes had been carried into the Swarm DB, and window-driven publications did not include all replay/time boundaries. Revision 2 separates project chains, derives the full window minimum and keeps every downstream row after a storage threshold conditional.

| Measure | Nominal | Worst case |
|---|---:|---:|
| LLM invocations, including layer-plan author/reviewer calls | 288 | 722 |
| Human sessions | 28 | 59 |
| Blocking human decisions | 50 | 111 |
| Active human time | 1,550 min / 25.8 h | 3,630 min / 60.5 h |
| Checkpoint publications summed across phases | 200 | 611 |

There is deliberately no expected Git-pack number before K0-b. The raw sum produced by `checkpoint × phase publications × no_delta_factor 1.0` is an **ungated no-delta upper bound**—13.72 GiB nominal and 243.57 GiB planning-worst—not a reachable scenario and not a prediction of repository size.

## Invocation derivation

Every new layer/shared-plane plan costs at least one author call and one fresh-context reviewer call. The bounded worst case includes two revision-return rounds. Delta plans use the same nominal pair and a smaller worst-case return allowance.

| Phase | Plan/design calls | Runtime/dialogue calls | Total nominal/worst |
|---|---:|---:|---:|
| K0-a | 6 / 18 | 3 / 6 | 9 / 24 |
| K0-b | 6 / 12 | 16 / 30 | 22 / 42 |
| N1 | 12 / 36 | 18 / 36 | 30 / 72 |
| S1 | 8 / 18 | 42 / 180 | 50 / 198 |
| V1 | 8 / 20 | 39 / 84 | 47 / 104 |
| AT1 | 4 / 8 | 20 / 40 | 24 / 48 |
| I1 | 2 / 4 | 28 / 50 | 30 / 54 |
| Q1 | 2 / 4 | 18 / 36 | 20 / 40 |
| X1 | 8 / 32 | 30 / 70 | 38 / 102 |
| M1 | 2 / 6 | 16 / 32 | 18 / 38 |

These phase rows are aggregate envelopes. Every plan/runtime budget now has a unique `package_id`; overlapping backlog work items remain only `covers_work_items` and do not identify the budget. Package-level profiles are normative: `light 12/20`, `standard 30/50`, and exact owner-authorized `deep`.

Human attention is likewise budgeted per package. Phase `human_attention_envelope_profile` is only a label for the sum and never creates a capacity approval by itself. The package budgets below reconcile exactly to every phase total; `high` packages require an exact owner-capacity receipt before that package runs.

| Package | Human profile | Sessions n/w | Decisions n/w | Active min n/w | Max session | Batchable |
|---|---|---:|---:|---:|---:|---|
| K0a-plan-bootstrap | standard | 1 / 2 | 1 / 3 | 20 / 60 | 30 | yes |
| K0a-runtime-F00 | light | 0 / 0 | 0 / 0 | 0 / 0 | 30 | yes |
| K0b-plan-deltas | light | 1 / 1 | 1 / 2 | 30 / 30 | 30 | yes |
| K0b-runtime-operational | standard | 1 / 3 | 2 / 4 | 30 / 120 | 60 | no |
| N1-plan-batch | standard | 2 / 3 | 2 / 4 | 60 / 120 | 60 | yes |
| N1-runtime-nonvisual | high | 1 / 3 | 2 / 6 | 60 / 180 | 60 | no |
| S1-plan-batch | standard | 1 / 2 | 2 / 4 | 60 / 120 | 60 | yes |
| S1-runtime-dialogues | high | 2 / 4 | 4 / 8 | 120 / 300 | 90 | no |
| S1-runtime-discovery | standard | 1 / 2 | 2 / 4 | 60 / 120 | 60 | yes |
| V1-plan-batch | standard | 1 / 2 | 2 / 4 | 60 / 120 | 60 | yes |
| V1-runtime-GH | high | 2 / 4 | 4 / 8 | 180 / 360 | 90 | yes |
| V1-runtime-G-interactive | high | 3 / 6 | 6 / 12 | 240 / 480 | 90 | no |
| AT1-plan-deltas | standard | 1 / 1 | 2 / 2 | 30 / 60 | 60 | yes |
| AT1-runtime-final | high | 1 / 3 | 2 / 6 | 60 / 180 | 60 | no |
| I1-plan-delta | standard | 1 / 1 | 1 / 2 | 30 / 60 | 60 | yes |
| I1-runtime-implementation | high | 1 / 4 | 3 / 8 | 90 / 240 | 60 | no |
| Q1-plan-delta | standard | 1 / 1 | 2 / 2 | 30 / 60 | 60 | yes |
| Q1-runtime-audit | high | 1 / 3 | 2 / 6 | 60 / 180 | 60 | no |
| X1-plan-deltas | standard | 1 / 2 | 2 / 4 | 60 / 120 | 60 | yes |
| X1-runtime-evidence-triggered | high | 3 / 8 | 6 / 16 | 180 / 480 | 60 | no |
| M1-plan-new | standard | 1 / 1 | 1 / 2 | 30 / 60 | 60 | yes |
| M1-runtime-full | high | 1 / 3 | 1 / 4 | 60 / 180 | 60 | no |

### Dialogue calls

P2 and E2 use the explicit reference formula:

```text
topics × rounds per topic × active agent roles per round
```

For each route this gives `4 × 1 × 3 = 12` nominal and `12 × 2 × 3 = 72` worst-case calls. The two routes therefore contribute 24/144 S1 calls. G interactive work declares two/four artifacts, three/eight total sessions and three calls per session, giving 9/24 V1 calls.

## Checkpoint-size model

Root-Pipeline layer-plan calls affect program cost and receive Pipeline-Git ledger entries, but are not inserted into a project DB. Fixture phases K0-a→N1 and Swarm phases S1→M1 are independent checkpoint chains, each starting from zero. The planning model uses:

- 2/4 replay points per checkpointed invocation;
- 16/64 KiB new unique bytes per replay point for nominal/planning-worst;
- an additional 256 KiB sensitivity branch, because chunk/delta context deduplication is not an architectural guarantee;
- explicitly **asserted**, not derived, fixed non-binary growth per phase;
- explicit G/Q binary aggregate;
- accumulated prior unrounded checkpoint size;
- display rounded upward to whole MiB.

```text
checkpoint[project, n]
  = checkpoint[the same project, n-1]
  + checkpointed calls × replay points/call × new unique bytes/point
  + asserted fixed non-binary phase growth
  + new binary payload
```

The fixed component contributes 68/134 MiB across phase rows and has `derivation: none_before_k0b`; this is now an explicit limitation rather than hidden arithmetic. The 256 KiB sensitivity ends fixture N1 at 96 MiB and reaches 200 MiB at Swarm S1. None of these values becomes an expected estimate before K0-b.

## Publication derivation

`max_publications_per_run = 12` is a guard, not a phase estimate. Publications are per phase. Window replay points include model boundaries, human answer/approval, external tool intent/result and irreversible side-effect intent/result. The window minimum is:

```text
max(ceil(total replay points / 10),
    ceil(publisher-eligible runtime minutes / 5),
    ceil(new DB bytes / 32 MiB))
```

Before K0-b the model takes no overlap credit between that minimum and the other boundaries. Estimated phase runs/tool interactions and asserted irreversible/migration/gate publication counts have `derivation: none_before_k0b`; they are postulates to be measured or explicitly retained in K0-b, not observed facts:

- top-level run completion;
- human wait/process exit;
- irreversible side-effect boundaries;
- migration/phase gates;
- replay-point/time/DB-growth window limits.

K0-a has no Git checkpoint publisher and is explicitly exempt from publication-window enforcement. Its counterfactual window pressure is still calculated as 2/5, but its effective `window_limit` and publications are 0. From K0-b onward, each phase declares estimated runs/tool interactions, asserted side-effect/gate counts, all replay-point components, time/byte minima and the trigger sum. S1 planning-worst therefore requires 108 window publications and 138 total, not 4/34.

## Storage projection and thresholds

| Phase/project chain | Calls nominal/worst | Publications nominal/worst | Checkpoint MiB nominal/worst | No-delta phase bound MiB nominal/worst | Checkpoint status nominal/worst | Pack status nominal/worst |
|---|---:|---:|---:|---:|---|---|
| K0-a / fixture | 9 / 24 | 0 / 0 | 3 / 6 | 0 / 0 | below / below | unavailable / unavailable |
| K0-b / fixture | 22 / 42 | 14 / 34 | 7 / 21 | 98 / 714 | below / below | below / warning |
| N1 / fixture | 30 / 72 | 18 / 44 | 14 / 42 | 252 / 1,848 | below / below | below / hard |
| S1 / Swarm | 50 / 198 | 27 / 138 | 12 / 65 | 324 / 8,970 | below / warning | below / hard |
| V1 / Swarm | 47 / 104 | 30 / 87 | 63 / 426 | 1,890 / 37,062 | warning / hard | hard / hard |
| AT1 / Swarm | 24 / 48 | 15 / 40 | 70 / 446 | 1,050 / 17,840 | warning / hard | hard / hard |
| I1 / Swarm | 30 / 54 | 26 / 69 | 79 / 475 | 2,054 / 32,775 | warning / hard | hard / hard |
| Q1 / Swarm | 20 / 40 | 16 / 42 | 109 / 720 | 1,744 / 30,240 | hard / hard | hard / hard |
| X1 / Swarm | 38 / 102 | 32 / 101 | 120 / 757 | 3,840 / 76,457 | hard / hard | hard / hard |
| M1 / Swarm | 18 / 38 | 22 / 56 | 127 / 777 | 2,794 / 43,512 | hard / hard | hard / hard |

Threshold status has independent checkpoint and phase-pack axes under the 100 MiB / 1 GiB limits. Nominal pack first reaches hard stop at V1 and nominal Swarm checkpoint at Q1. Planning-worst pack first reaches hard stop at fixture N1; planning-worst checkpoint first reaches hard stop at Swarm V1. In the 256 KiB replay sensitivity, Swarm checkpoint hard-stops already at S1.

Consequently:

- N1 and later worst-case rows require prior owner storage disposition;
- V1 cannot start past V1-00 on the current nominal no-delta model;
- AT1 and later rows are counterfactual branches conditional on the selected §9.5.1 owner route;
- summing these rows does not describe an executable repository history.

The ungated no-delta sums are approximately 13.72 GiB nominal and 243.57 GiB planning-worst. They are intentionally retained only as a stress signal. `expected_delta_factor`, `expected_pack_growth` and policy-reachable total remain unknown until K0-b and subsequent owner routes.

No credit is taken for Git delta compression. The model explicitly recognizes SQLite page churn, full-file rewrites such as `VACUUM`, and potentially incompressible media BLOBs.

## Binary-payload seed

| Owner | Objects nominal/worst | Assumed mean nominal/worst | Hard cap | Aggregate nominal/worst |
|---|---:|---:|---:|---:|
| G | 20 / 40 | 2 / 8 MiB | 8 MiB | 40 / 320 MiB |
| Q | 12 / 28 | 2 / 8 MiB | 8 MiB | 24 / 224 MiB |

The policy-permitted maximum and fail-closed runtime aggregate limits are 320 MiB for G and 224 MiB for Q. Per-object and aggregate caps are enforced independently. G and Q plans must retain or replace these inputs and reconcile every variance.

## Decision impact

This revision supports only the following pre-runtime conclusion:

1. The layer composition is a staged deep program, not one run.
2. SQLite plus a tracked checkpoint remains the current hypothesis, not a validated cost result.
3. K0-b measurement must establish real replay/fixed bytes, tool/time window pressure, delta, publication-time and clone behavior separately for each project chain.
4. Every predicted warning/hard crossing needs `narrow/batching`, an evidence-backed threshold change, checkpoint-storage migration that reopens V2-D22, or pause.
5. Capacity authorization is package-scoped. V1 has two `high_attention` runtime packages totalling approximately 7–14 active owner hours plus a standard plan package; both high packages need exact receipts before execution.

## Gate status

The first independent review returned revision 0. The second fresh-context review returned `approve_with_changes`; this is revision-return round 2 of the maximum 2. The listed changes passed mechanical validation, no third autonomous review-return is permitted, and the five previously blocked decisions are ready for owner disposition. The later source `d0-01-d0-02-owner-disposition-input-03.txt` is therefore classified as findings N-01…N-12 for owner disposition, not a third return; its accepted document-level corrections are applied without changing any proposed decision.
