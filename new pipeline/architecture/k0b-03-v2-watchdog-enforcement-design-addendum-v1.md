# K0b-03 v2 trusted watchdog enforcement design addendum v1

Status: owner-authorized documentary alignment; pending separate fresh-context review. No implementation or runtime authority.

## Authority and immutable baseline

334d8682b144a8b2f82006f8babc91cc21ee6d3d
Tree: b55039570954b275b68e75f221aaa876c6e2bcb4
Parent: 24067ca6a8cb5fd437ca61d168a9b106163ae0c2

The exact owner approval permits five new design-alignment documents only. Historical design, freeze disposition, capability package and all existing files remain byte-identical. F01-F08, including F03, remain open; canonical K0b-03 remains blocked and G-K0B03-UNTRUSTED-SHAPES remains future_open.

## Normative precedence

This addendum is the sole new normative wording for the seven identified refinements below. The alignment matrix provides traceability and required future vectors. Historical requirements outside these explicit refinements remain unchanged. Unresolved conflicts block future implementation authority. Separate fresh-context review of this addendum is still required.

## Pinned inputs

I1: new pipeline/architecture/k0b-03-v2-remediation-design-v1.md; bytes=25193; SHA-256=b8a84cf7ca6064d7b1224c3ba57380caa5f297b638b344b567a239411ff2d7a3
I2: new pipeline/decisions/k0b-03-v2-remediation-design-freeze-owner-disposition-v1.yaml; bytes=3473; SHA-256=c034ec84f18aadd0823b29019fd31cc08af9279a31e319b5a02b5e01adcd80c9
I3: new pipeline/evidence/k0b-03-v2-remediation-feasibility-and-requirement-matrix-v1.yaml; bytes=8436; SHA-256=d6b4b61427b3bc7487ef6a4c08428331c78af0fcb8526d0cf42be0be86b24429
I4: new pipeline/requests/k0b-03-v2-windows-enforcement-trusted-cpu-watchdog-FR-WIN-07-integration-approval-request-v41.yaml; bytes=27785; SHA-256=d292c2831826d2de23ecb7126f03108a6823faaa79436051b9479378887cb2ef
I5: new pipeline/requests/k0b-03-v2-windows-enforcement-FR-WIN-08-09-trusted-pending-connect-watchdog-integration-approval-request-v47.yaml; bytes=30302; SHA-256=ff20c3bc4836f97f6801fd321b45d539c53289bdab711a4b1733692a1e59436b
I6: new pipeline/requests/k0b-03-v2-windows-enforcement-capability-prerequisite-completion-approval-request-v51.yaml; bytes=38282; SHA-256=9d3021e87b127bcdb8fb02b1a381c4385a9446dc7f1f22aedca39e51eb7f3c56
I7: new pipeline/evidence/k0b-03-v2-windows-enforcement-capability-qualification-summary-v1.yaml; bytes=78202; SHA-256=646df3c3f519c41be08fc2406ef65fb8af6c410d45e62b19deb6a02012293496
I8: new pipeline/reviews/k0b-03-v2-windows-enforcement-capability-security-review-v1.yaml; bytes=9594; SHA-256=bb4204e8e27932bb4056138bdd40add381104202834e1610f2e7059d64d84783
I9: new pipeline/decisions/k0b-03-v2-windows-enforcement-capability-prerequisite-owner-disposition-v1.yaml; bytes=6645; SHA-256=aa11791356c431d9d7b51a1e6febda9acbda6954cd1f489039adce0659f7aa0a

## WD-CPU-01

Historical design sections: 7,12. Findings: F03. Evidence inputs: I4, I7, I8, I9.

The trusted naturally non-Job supervisor shall retain the exact target process handle, account target user time through GetProcessTimes, arm the CPU watchdog before ResumeThread, terminate the owned Job fail-closed on budget breach and prove owned-tree quiescence. Wall timeout remains a separate control. Accounting failure or ambiguous target identity blocks; no native JOB_OBJECT_LIMIT_PROCESS_TIME or END_OF_PROCESS_TIME proof is inferred.

Failure boundary: CPU overrun beyond the declared watchdog contract, late/missing arm, accounting error, handle ambiguity, failed termination or quiescence mismatch.

## WD-NET-01

Historical design sections: 7,12. Findings: F03. Evidence inputs: I5, I7, I8, I9.

AppContainer identity with zero network capability SIDs remains mandatory and distinct from Job limits. The trusted parent pending-connect watchdog shall enforce the pinned IPv4 and IPv6 controlled scenarios through ordered bounded checkpoints, rejection of connection readiness/success/listener acceptance, owned-tree termination and bounded quiescence. A timeout alone is not denial proof. No WSAEACCES, exact WFP component or universal absence of network effects is inferred.

Failure boundary: Any successful connect, readiness, listener acceptance, unexpected terminal error, missed checkpoint, missed or overrun watchdog deadline, failed required owned-Job termination, or quiescence mismatch. Expected bounded firing with reason trusted_pending_connect_watchdog_deadline is compatible success only when all required checkpoints, zero listener acceptance, exact owned-Job termination and bounded quiescence satisfy pinned I5; timeout alone remains insufficient.

## WD-TRUST-01

Historical design sections: 7,10,12. Findings: F03, F08. Evidence inputs: I4, I5, I7, I8, I9.

Every watchdog guarantee is conditional on the pinned trusted supervisor, exact executable/environment/target identities, naturally non-Job launch, declared policy parameters, working watchdog and the observed qualified host/scope. Policy parameters and deadlines must be explicitly bound by admitted closed policy; no ambient constants or caller assertion may substitute for admission. Evidence does not generalize to another host or arbitrary workloads.

Failure boundary: Missing or conflicting trust/pin/host/policy binding, stale qualification or ambiguous launch identity.

## WD-ATT-01

Historical design sections: 10. Findings: F08, F03. Evidence inputs: I1, I7, I8, I9.

Attestation compatibility shall distinguish observed identity, mechanism, qualified scope, evidence digests, trust assumptions and missing guarantees. Watchdog evidence shall not satisfy a request for native process-time, END_OF_PROCESS_TIME, WSAEACCES or a stronger egress guarantee. Stronger incompatible requirements block. K0b-04 retains the actual attestation-limit decision.

Failure boundary: Native/stronger requirement accepted using only watchdog evidence, cross-scope hash substitution, stale/missing/conflicting attestation.

## WD-FAIL-01

Historical design sections: 7,8. Findings: F03, F05, F07. Evidence inputs: I1, I4, I5, I8.

Missing checkpoints, watchdog/API failures, target ambiguity, missed or overrun watchdog deadlines, failed required owned-Job termination, exceeded quiescence deadlines, unexpected network dispositions and cleanup mismatches shall fail closed or enter an explicit blocked/unknown disposition. Expected bounded pending-connect watchdog firing with reason trusted_pending_connect_watchdog_deadline is not itself a failure when every pinned I5 checkpoint, zero-acceptance, termination and quiescence obligation is satisfied; timeout alone does not establish success. Unknown external effects remain unresolved; process disappearance is not absence-of-effect proof. Owned cancellation shall not broaden to unrelated processes. Evidence shall be preserved within bounds and no automatic retry shall occur.

Failure boundary: Unknown effect treated as success, retry without authority, lost required evidence, cleanup mismatch ignored or cancellation of an unowned target.

## WD-CP-01

Historical design sections: 12. Findings: F03. Evidence inputs: I6, I7, I8, I9.

Capability completion is the limited documentary acceptance already recorded by I9. It is not production launcher implementation, proof of all failure paths, closure of F03 or a canonical transition. Existing evidence may support an explicitly compatible mechanism claim; future implementation still needs its own pinned authority, coverage, validation and non-author review.

Failure boundary: Capability evidence relabeled as implementation validation, native equivalence, F03 closure or runtime authority.

## WD-COV-01

Historical design sections: 11,13,14. Findings: F03, F07, F08. Evidence inputs: I1, I3, I8.

Preserve exactly 70 candidate paths and 256 executed cases in each of two environments with partition 96/40/48/32/32/8, all passed and zero failure/error/skip. The authored coverage map must bind every aligned normative obligation to exact cases, expectations and proof artifacts. Mandatory vectors may not be hidden by test counts, aliases or reduced assertions. If complete vectors cannot fit the partition, stop for separately authorized design change.

Failure boundary: Coverage obligation unmapped, required vector omitted, partition/path count silently changed, count-only sufficiency claim or candidate code created during alignment.

## Unchanged controls and scope

Suspended creation, Job assignment before resume, kill-on-close, active-process and memory caps, wall timeout, bounded output, repository/tool/environment admission, AppContainer identity, canaries, owned-tree cancellation, ACL/profile/root cleanup and unknown-effect handling remain mandatory. Job Objects do not provide egress isolation. No firewall mutation, external isolation product, external network/DNS, persistent OS policy or new dependencies are authorized.

The supervisor, host, environment, policy parameters, checkpoint grammar, deadlines and evidence bindings are trusted and explicitly admitted. This text does not establish the missing guarantees listed below and does not transfer K0b-04 attestation-limit authority.

Unproven: 
native JOB_OBJECT_LIMIT_PROCESS_TIME; native END_OF_PROCESS_TIME; native WSAEACCES; exact WFP filter/component attribution; universal absence of all network effects
.

## Coverage and candidate inventory

Preserve 70 exact candidate paths from section 13 of pinned I1, 256 cases in each of two fresh environments, partition 96/40/48/32/32/8, zero failures/errors/skips and deterministic results/outputs. All 70 candidate paths are absent at preparation time; none is created by this stage. Exact case IDs and sufficiency require a future authored coverage map and independent review. If mandatory vectors cannot fit, stop for separate design change.

Required consumers and future vectors are enumerated in 
new pipeline/evidence/k0b-03-v2-watchdog-enforcement-requirement-coverage-alignment-v1.yaml
. No vector listed there is an executed test or an assertion of current implementation coverage.

## Retained findings and evidence limits

- CAP-V50-PROVENANCE [retained_not_closed]: An additional distinct A execution was initially presented as B. It was not the originally authorized single A repeat and is not B. Acceptance is not retroactive runtime authorization. Actual B was separately authorized after the mismatch.
- CAP-V50-INVENTORY [retained_not_closed]: The wrapper computes all post-run entry hashes but its success predicate compares inventory count and paths only; content pins cover probe, worker, v17, v50 and Python. Later 52-file verification establishes current preservation, not immutable immediate post-execution preservation.
- CAP-V50-WRAPPER [retained_not_closed]: No outer wait timeout; copy-task failure may lose partial capture; wrapper parent termination does not provide comprehensive emergency root/profile cleanup. Successful A/B cleanup is not proof of every failure path.
- CAP-V50-WATCHDOG [retained_not_closed]: Trusted CPU and pending-connect watchdog enforcement only. Native JOB_OBJECT_LIMIT_PROCESS_TIME, END_OF_PROCESS_TIME and WSAEACCES are not proven; no universal absence-of-network-effect guarantee.

Qualification-wrapper limits are not permission to reproduce those defects in a future launcher. This documentation does not repair them or prove every emergency failure path. Later inventory checks do not create immediate historical attestation. Raw source attachments remain external pinned dependencies. Acceptance of extra A evidence is not retrospective runtime authorization.

## Review and authority boundary

This addendum still requires separately authorized fresh-context review. It does not close F03 or any other finding/gate, change canonical state, grant implementation/runtime authority, authorize candidate creation, or advance K0b-03/K0b-04/K0b-05/N1/Swarm. Stop after documentary checks and report exact output hashes/sizes. Staging and commit require separate authority.
