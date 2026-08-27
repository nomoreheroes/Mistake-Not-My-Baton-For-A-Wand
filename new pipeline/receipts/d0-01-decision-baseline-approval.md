# D0-01 — Owner approval of the decision baseline

**Source envelope:** `new pipeline/receipts/d0-01-decision-baseline-approval.yaml`  
**Approval type:** `d0_decision_baseline`  
**Decision:** approved  
**Owner:** `workspace_owner` / `human_owner`  
**Captured at:** `2026-08-27T17:38:02.0365116+03:00`  
**Provenance:** explicit owner message in the current conversation; conversational-only until authenticated approval runtime exists

## Approved records

| Role | YAML SHA-256 | Markdown SHA-256 |
|---|---|---|
| dispositions | `ff4b045966be8fb57d6e4243bed59bae72d7b7aced5be7efb766bd08d1aa59ab` | `3946add7b50aeb37a2a29ad151587702d21bb8930b34448f6177199193f85b76` |
| forecast | `7e8a8da36c982b21bc25e1bbd1b1dd495f36f92446e7afbef4c6ce8cc8683840` | `5861e3cca7c6e45a248f38a978219802539158c81859dfca72b0a880e83bc0d7` |
| gate contract | `1bf92c755912a95ecf46e691454512f22a48fe97b59a5f7a676ac07e054478c4` | `5442d6366f9fabe6e3ce41e98fa3f366f5ff70d074695253869297be11acfb16` |
| checkpoint policy | `8e9696916c939c6d9fa337c7bddc8b022c7657a2c105c0e51773b4c6ba1a67f3` | `02ddee381cf51ce2f4966feb107f963440581dc4d26f5577de9cffad6194eabf` |

The owner accepted the proposed disposition `accepted` for the exact set V2-D01…V2-D39, including application of non-return findings N-01…N-12. No field override or deferred decision was introduced.

## Authorized next action

The owner authorized creation of this conversational approval envelope and execution of D0-05: commit the current root Pipeline governance baseline. The same instruction authorizes keeping repository boundaries intact by committing the project-local `.gitignore` separately in the previously empty `projects/swarm` Git repository.

The approved input records remain byte-immutable. Approval is represented by the separate YAML envelope rather than by editing those records and invalidating their approved hashes.

## Provenance limitations

- the current bootstrap environment has no authenticated approval runtime;
- no stable external message identifier is exposed to the workspace;
- Git authorship and the conversational actor are not cryptographically linked;
- the exact owner-approved record hashes and the eventual Git commit hashes provide the available reproducibility boundary.
