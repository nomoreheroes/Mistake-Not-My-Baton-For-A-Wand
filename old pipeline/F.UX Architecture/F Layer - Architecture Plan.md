# F Layer — Architecture Plan

**Слой:** F — UX Architecture  
**Дата:** 2026-08-24  
**Ревизия:** R1  
**Статус:** ACTIVE BASELINE / PROMPT ALIGNMENT REQUIRED

**Основание:** существующие промпты F1–F9, publish-контракты Layers D/E и ожидаемый handoff в `G.Visual System & UI`.

**Назначение документа:** определить проверяемую архитектуру surface map, navigation, information architecture и interaction patterns, убрать устаревшие ссылки на внутренние E-артефакты и сформировать единый immutable handoff в Layer G.

---

## 1. Назначение и границы слоя

Layer F превращает stories и подписанный design-system intent в UX-структуру продукта:

```text
Layer D PRD/story package + Layer E final design package
        ↓
surface map
        ↓
navigation and journeys
        ↓
information architecture
        ↓
interaction semantics
        ↓
cross-artifact QA
        ↓
PM + accessibility reviews
        ↓
owner architecture review
        ↓
gate + immutable Layer F package
        ↓
Layer G Visual System & UI
```

Слой отвечает за:

- canonical inventory продуктовых поверхностей;
- navigation model, entry points, journeys, back/exit behavior;
- информационные зоны, hierarchy и state intent;
- semantic actions, feedback, forms, recovery и interaction patterns;
- story/value/MVP coverage;
- accessibility архитектуру на структурном уровне;
- owner decisions по неоднозначным UX choices;
- готовность структуры к visual UI design.

Layer F не:

- создаёт visual layouts, component styling или pixel-perfect screens;
- определяет concrete token values;
- меняет stories/requirements/product scope;
- выполняет инженерную task decomposition;
- добавляет новую surface после F1 без возврата к F1;
- использует E4/E5…E10 как более сильный источник, чем E12 final pair;
- позволяет Layer G исправлять F-артефакты напрямую.

---

## 2. Нормативные решения слоя

### Решение F-D1 — обязательны два upstream publish packages

F1 стартует только при одновременном наличии:

- D7-published Layer D package с `PROCEED`;
- E12-published Layer E package с `PROCEED`;
- совпадающих source package refs и hashes.

Layer E package обязан ссылаться на тот же Layer D package, который передан F.

### Решение F-D2 — design authority ограничена final pair

Содержательные design inputs F:

- `design_tokens.json`;
- `design_grammar.yaml`.

`e11_gate_report.yaml`, `e12_gate_report.yaml`, snapshot и manifest используются для авторизации и carry-forward conditions. `design_intent_normalized.yaml`, mood sketches и E5–E9 reports не являются разрешёнными decision inputs.

### Решение F-D3 — устаревший `e9_gate_report` удаляется из контракта

E9 — frontend feasibility reviewer, а не финальный gate Layer E. Все поля вида `e9_constraints`, `e9_gate_report.verdict` и `layer_f_opening_instructions` заменяются ссылками на:

- `LayerE.snapshot.carry_forward_conditions`;
- `e12_gate_report`;
- правила/refs из `design_grammar.yaml`.

### Решение F-D4 — accessibility не читается из E6

E6 — PM Intent Reviewer. F7 проверяет signed accessibility intent в final grammar/tokens и carry-forward conditions E package. Прямое чтение `e6_review_report` или даже E8 internal review не требуется downstream.

### Решение F-D5 — F1 является единственным owner surface universe

F2–F9 не добавляют surface. Обнаруженная missing surface создаёт return request в F1. Это сохраняет ID, scope, coverage и revision lineage.

### Решение F-D6 — F2→F3→F4 является строгой структурной цепочкой

Navigation зависит от current surface universe; IA — от surface+navigation; interaction — от всех трёх. Изменение upstream автоматически инвалидирует downstream artifacts.

### Решение F-D7 — F6 и F7 независимы после F5

PM и accessibility reviews могут выполняться параллельно по одному immutable F1–F5 set. F8 запускается только после обоих current reports.

### Решение F-D8 — F8 фиксирует решения, но не переписывает архитектуру

Owner decision, требующий изменения F1–F4, создаёт revision route. F8 не вносит скрытый patch в чужой artifact.

### Решение F-D9 — финальный handoff gate бинарный

`f9_gate_status: PROCEED | BLOCK` определяет возможность публикации. Отдельное поле `quality_grade: approved | approved_with_conditions` сохраняет существующую семантику nonblocking conditions.

### Решение F-D10 — conditions не могут маскировать barrier

`approved_with_conditions` допустим только если все conditions имеют `blocks_handoff: false`, downstream owner и treatment. Любой blocking condition приводит к `BLOCK` или Mode B resolution до публикации.

### Решение F-D11 — все артефакты version/hash-bound

F5/F6/F7/F8/F9 относятся к точным hashes F1–F4. Skip-existing допустим только при полном совпадении dependency manifest.

### Решение F-D12 — Layer G получает package, а не набор «последних файлов»

F9 публикует все current F artifacts, gate, snapshot и manifest атомарно. G не сканирует working directory и не выбирает latest по timestamp.

---

## 3. Общий поток исполнения

### 3.1 INITIAL

```text
D7 package + E12 package
  ↓ cross-package preflight
F1 Surface Map Architect
  → surface_map.yaml
  ↓
F2 Navigation & Flow Architect
  → navigation_map.yaml
  ↓
F3 Information Architecture Architect
  → ia_map.yaml
  ↓
F4 Interaction Pattern Architect
  → interaction_spec.yaml
  ↓
F5 UX Structure QA
  → ux_qa_report.yaml
  ↓
  ├─ F6 PM Flow & Story Reviewer ──────┐
  └─ F7 Accessibility Architecture ────┤
                                        ↓ barrier
F8 UX Architecture HITL Review
  → f8_owner_decisions.yaml
                                        ↓
F9 UX Architecture Gatekeeper
  ├─ BLOCK   → f9_gate_report.yaml + revision_route
  └─ PROCEED → LayerF.snapshot.yaml
                layer_f_publish_manifest.yaml
                                        ↓
                                       G1
```

### 3.2 Stage barriers

- F2: `surface_map.ready_for_f2 = true`.
- F3: navigation current/complete и нет blocking before F3.
- F4: IA current/complete и нет blocking before F4.
- F5: F1–F4 current, complete/complete_with_nonblocking_questions.
- F6/F7: F5 current и `ready_for_review`.
- F8: current F6/F7, нет unresolved return.
- F9: F1–F8 complete/current, HITL session завершена.

### 3.3 Revision flow

```text
F6/F7/F9/G return
  ↓ earliest restart_from
  ├─ F1 → F1→F2→F3→F4→F5→F6/F7→F8→F9
  ├─ F2 → F2→F3→F4→F5→F6/F7→F8→F9
  ├─ F3 → F3→F4→F5→F6/F7→F8→F9
  ├─ F4 → F4→F5→F6/F7→F8→F9
  └─ F8 → F8→F9
```

Если F8 decision изменяет structure, route идёт к F1–F4, а не остаётся F8-only.

---

## 4. Роли и ownership

| Агент | Ответственность | Output | HITL |
|---|---|---|---|
| F1 | Surface universe, roles, scope, story coverage | `surface_map.yaml` | Нет; вопросы маршрутизирует F8/owner |
| F2 | Navigation model, journeys, entries/exits | `navigation_map.yaml` | Нет |
| F3 | Information hierarchy/zones/states | `ia_map.yaml` | Нет |
| F4 | Semantic action/state/feedback patterns | `interaction_spec.yaml` | Нет |
| F5 | Cross-artifact QA/readiness | `ux_qa_report.yaml` | Нет |
| F6 | PM, story, MVP и value review | `f6_review_report.yaml` | Нет |
| F7 | Accessibility architecture review | `f7_review_report.yaml` | Нет |
| F8 | Owner walkthrough и decisions | `f8_owner_decisions.yaml` | Да |
| F9 | Aggregation, routing, gate, publish content | `f9_gate_report.yaml` | Conditional Mode B |
| Runner | Locks, dependency manifests, atomic package | control-plane | Нет |

Writer map:

```text
F1 owns surface map
F2 owns navigation map
F3 owns IA map
F4 owns interaction spec
F5 owns QA report
F6/F7 own their reviews
F8 owns owner decision receipts
F9 owns final gate
runner owns manifests/snapshot publication
```

---

## 5. Common envelope и architecture set

```yaml
artifact_meta:
  artifact_type: navigation_map
  schema_version: f.navigation.v1
  artifact_version: 2
  architecture_set_id: FSET-...
  layer: F
  producer: F2
  run_id: run-...
  cycle_id: cycle-...
  source_packages:
    layer_d: D-...
    layer_e: E-...
  status: complete
  derived_from: []
  content_sha256: "..."
```

F1 создаёт `architecture_set_id`; downstream artifacts наследуют его. Revision upstream создаёт новую версию set. Review binding:

```yaml
reviewed_architecture:
  architecture_set_id: FSET-...
  surface_map_sha256: "..."
  navigation_map_sha256: "..."
  ia_map_sha256: "..."
  interaction_spec_sha256: "..."
  ux_qa_report_sha256: "..."
```

---

## 6. Карта артефактов

```text
runs/<run_id>/layer-f/<cycle_id>/
├── inputs/
│   ├── layer_d.lock.yaml
│   └── layer_e.lock.yaml
├── f1/surface_map.yaml
├── f2/navigation_map.yaml
├── f3/ia_map.yaml
├── f4/interaction_spec.yaml
├── f5/ux_qa_report.yaml
├── f6/f6_review_report.yaml
├── f7/f7_review_report.yaml
├── f8/
│   ├── f8_session_checkpoint.yaml
│   └── f8_owner_decisions.yaml
├── f9/f9_gate_report.yaml
└── architecture_set_manifest.yaml
```

Published package:

```text
published/layer-f/<package_id>/
├── surface_map.yaml
├── navigation_map.yaml
├── ia_map.yaml
├── interaction_spec.yaml
├── ux_qa_report.yaml
├── f6_review_report.yaml
├── f7_review_report.yaml
├── f8_owner_decisions.yaml
├── f9_gate_report.yaml
├── LayerF.snapshot.yaml
└── layer_f_publish_manifest.yaml
```

---

## 7. Upstream input projection

### Обязательный preflight-набор

Из Layer D F1 получает одну согласованную группу:

- `layer_d_publish_manifest.yaml`;
- `LayerD.snapshot.yaml`;
- `d7_gate_report.yaml`;
- `prd.index.yaml`;
- inventories и detailed stories, перечисленные в manifest.

Из Layer E F1 получает одну согласованную группу:

- `layer_e_publish_manifest.yaml`;
- `LayerE.snapshot.yaml`;
- `e12_gate_report.yaml`;
- `design_tokens.json`;
- `design_grammar.yaml`.

Отсутствие одного обязательного файла, несовпадение hash или смешение package IDs блокирует F1 до содержательной обработки.

### Из Layer D

- story IDs/types/revisions;
- detailed main/alternate/error flows;
- acceptance criteria;
- delivery scope и debt disposition;
- requirements/aspects traceability;
- typed attention routes to F;
- PRD carry-forward obligations.

### Из Layer E

- tokens для concrete design constraints;
- grammar rules для surface/zone/role/status/interaction intent;
- E12 carry-forward conditions;
- exact parameter/token reference paths.

### Cross-package consistency

F preflight проверяет:

```text
E.source_layer_d_package_id = supplied D.package_id
D.gate = PROCEED
E.e12.gate = PROCEED
all referenced files/hashes exist
no package status is staging/partial/superseded
```

---

## 8. F1 — Surface Map

### 8.1 Surface discovery

F1 собирает explicit mentions и выявляет implicit surfaces, необходимые для:

- core value delivery;
- setup/onboarding;
- recovery/error;
- monitoring/status;
- administration/operation;
- audit/governance;
- system/global story visibility.

F1 не превращает каждую story в отдельный screen. Он нормализует продуктовые «места взаимодействия» в canonical surface IDs.

### 8.2 Две независимые оси

```yaml
inclusion_status: mvp_core | mvp_supporting | post_mvp | deferred
discovery_status: explicit | implicit
```

`implicit + mvp_core` требует owner resolution до F2. Nonblocking implicit supporting surface может пройти как provisional, но обязана быть разрешена F8 до F9.

### 8.3 Surface record

```yaml
surface:
  surface_id: SURF-ACTIVATION
  canonical_name: "..."
  primary_role: core | supporting | setup | recovery | monitoring | admin_operator | audit
  secondary_roles: []
  granularity: primary | secondary | ephemeral
  inclusion_status: mvp_core
  discovery_status: explicit
  inclusion_basis: "..."
  priority_tier: 1
  story_refs:
    - story_id: US-...
      story_revision: 2
      story_sha256: "..."
  requirement_ids: []
  aspect_ids: []
  design_grammar_refs: []
  carry_forward_condition_refs: []
  requires_owner_confirmation: false
```

### 8.4 Completeness

F1 проверяет value mechanism, critical journeys и system/global coverage. Status:

- `complete`;
- `complete_with_questions` — только nonblocking;
- `incomplete`.

`ready_for_f2` истинно только при status ≠ incomplete и нуле вопросов `must_resolve_before_f2`.

---

## 9. F2 — Navigation & Flow Architecture

F2 определяет:

- navigation model и rationale;
- top-level groups;
- allowed transitions;
- critical user journeys;
- entry points/deep links;
- back behavior;
- exits/cancellation;
- orphan surfaces, dead ends, depth/discoverability risks.

Transition record:

```yaml
transition:
  transition_id: NAV-TR-001
  from_surface_id: SURF-HOME
  to_surface_id: SURF-DETAIL
  trigger: "..."
  transition_type: direct | contextual | system_initiated | deep_link
  preconditions: []
  back_behavior: return_previous | return_parent | exit_flow | context_dependent
  failure_route: SURF-RECOVERY
  story_refs: []
```

Journey record содержит start/end, ordered transitions, alternate/recovery paths и completeness. F2 не создаёт IA blocks и не добавляет surface. Missing surface → F1 route.

---

## 10. F3 — Information Architecture

F3 задаёт для каждой surface:

- information purpose;
- zones и hierarchy;
- primary/secondary entities;
- actionable vs informational blocks;
- state intent;
- ephemeral overlays;
- relationship с navigation context;
- full/limited processing depth по scope.

```yaml
surface_ia:
  surface_id: SURF-DETAIL
  processing_depth: full | bounded | deferred
  information_goal: "..."
  zones:
    - zone_id: Z-PRIMARY
      role: primary_action | context | status | supporting | recovery
      content_entities: []
      priority: 1
      grammar_refs: []
  states:
    default: {}
    loading: {}
    empty: {}
    error: {}
    degraded: {}
    success: {}
  story_refs: []
```

F3 определяет semantic order, не visual layout, grid или component selection. Для MVP core/supporting требуется full processing; post-MVP не должен получать скрытую MVP детализацию.

---

## 11. F4 — Interaction Pattern Architecture

F4 определяет semantic interaction contract:

- actions и prerequisites;
- feedback class/timing;
- form/input behavior;
- validation/error recovery;
- loading/degraded/empty/success behavior;
- confirmation discipline;
- focus/context behavior;
- journey interaction completeness.

```yaml
interaction_action:
  action_id: ACT-SUBMIT
  surface_id: SURF-SETUP
  intent: "..."
  trigger_type: explicit | implicit | system
  preconditions: []
  result_state: success
  failure_state: error
  feedback:
    class: blocking_wait | non_blocking_progress | none
    grammar_refs: []
  alternatives: []
  accessibility_obligations: []
  story_criterion_refs: []
```

F4 не выбирает визуальный component, color или layout. Он ссылается на signed grammar/token semantics.

---

## 12. F5 — UX Structure QA

F5 проверяет согласованность, не повторяет проектирование:

1. Surface coverage chain D→F1→F4.
2. Surface ID consistency.
3. Navigation→IA alignment.
4. IA states→interaction states alignment.
5. Layer E final conditions traceability.
6. Агрегацию open questions, risks и limits.
7. Orphaned decisions.
8. Conflicting constraints.
9. Coverage blind spots.
10. Readiness для F6/F7 и provisional G readiness.

Canonical QA verdict:

- `READY_FOR_REVIEW`;
- `READY_WITH_NONBLOCKING_ITEMS`;
- `NOT_READY_FOR_REVIEW`.

При not-ready F5 указывает earliest precise `restart_from: F1 | F2 | F3 | F4` и affected IDs.

F5 report связан со всеми четырьмя architecture hashes. Он не исправляет найденные gaps.

---

## 13. F6 — PM Flow & Story Review

F6 проверяет:

- user/system/global story coverage;
- acceptance criteria alignment;
- MVP scope violations;
- post-MVP discipline;
- implicit surface decisions;
- core value delivery;
- target user fit;
- success/kill criteria risks;
- product-boundary items F5.

Recommendations:

- `PROCEED`;
- `PROCEED_WITH_NOTES`;
- `RETURN` с `restart_from F1–F4`;
- operational `BLOCK` для invalid/stale F5 input.

F6 — reviewer, не product authority. Дефект story/requirement маршрутизируется Layer D/C, а не «чинится» в F.

---

## 14. F7 — Accessibility Architecture Review

F7 проверяет:

- keyboard/focus navigation model;
- cognitive load и navigation depth;
- accessible entry points;
- logical information order;
- state differentiation;
- recovery paths;
- gesture/input alternatives;
- focus trap risks;
- feedback accessibility;
- signed accessibility grammar/tokens и E carry-forward conditions.

Recommendations совпадают с F6: `PROCEED | PROCEED_WITH_NOTES | RETURN`.

F7 остаётся на архитектурном уровне: он не вычисляет финальные contrast ratios по пикселям и не делает implementation audit. Но если signed token/grammar constraint уже проверяем на этом уровне, несоответствие является реальным finding.

Прямые ссылки `e6_review_report`/`e9_gate_report` удаляются.

---

## 15. F8 — UX Architecture HITL Review

### 15.1 Preconditions

F8 требует current F1–F7 artifacts и отсутствие reviewer `RETURN`. Если F6/F7 требуют revision, сначала выполняется closure до F7.

### 15.2 Session blocks

1. Surface overview.
2. Navigation overview.
3. Critical journeys.
4. Open decisions.
5. Risks and concerns.
6. Implicit surfaces.

Один блок и один ответ за раз. Agent не объявляет одобрение за owner.

### 15.3 Checkpoint и final output

Во время сессии пишется отдельный checkpoint. `f8_owner_decisions.yaml` публикуется только после завершения всех обязательных блоков.

```yaml
owner_decision:
  decision_id: F8-DEC-...
  question_id: F8-Q-...
  owner_response: "..."
  normalized_decision: confirm | adjust | reject | defer
  affected_artifacts: [F1]
  affected_ids: [SURF-...]
  structural_change_required: true
  revision_route:
    restart_from: F1
```

Mode B пересматривает только conditions, указанные F9. Предыдущие решения не открываются без evidence-based причины.

---

## 16. F9 — final gate

### 16.1 Aggregation checks

F9 проверяет:

- полный current input set F1–F8;
- F5 readiness;
- F6/F7 recommendations и stability;
- конфликты между PM и accessibility perspectives;
- выполнение owner decisions F8;
- реализацию Layer E carry-forward conditions;
- absence of critical orphan/gap/conflict;
- complete story/surface/journey/state/action traceability;
- отсутствующие или stale artifacts;
- handoff conditions для G.

F9 агрегирует evidence и не делает скрытый rereview F1–F4.

### 16.2 Gate model

```yaml
f9_gate:
  gate_status: PROCEED | BLOCK
  quality_grade: approved | approved_with_conditions | null
  checks: []
  reviewer_summary: {}
  owner_decision_summary: {}
  conditions:
    - condition_id: F9-C-001
      blocks_handoff: false
      target_layer: G
      owner: G1
      treatment: "..."
  revision_route:
    restart_from: F1 | F2 | F3 | F4 | F8 | multiple | null
    path: []
```

`PROCEED + approved_with_conditions` допустим только при нуле blocking conditions.

### 16.3 Mode B

F9 Mode B задаёт owner только gate-critical вопрос, не требующий изменения архитектуры. Если решение требует structural edit, verdict становится `BLOCK` и формируется route к F1–F4. F9 Mode B не компенсирует незавершённый F8.

### 16.4 Publish checks

До publication:

- all artifact hashes recomputed;
- source D/E package refs current;
- cross-file IDs resolve;
- owner session complete;
- gate status `PROCEED`;
- all conditions nonblocking.

---

## 17. Финальный package и handoff в G

`LayerF.snapshot.yaml`:

```yaml
layer_f_snapshot:
  package_id: F-...
  architecture_set_id: FSET-...
  source_packages:
    layer_d: D-...
    layer_e: E-...
  artifact_refs:
    surface_map: {sha256: "..."}
    navigation_map: {sha256: "..."}
    ia_map: {sha256: "..."}
    interaction_spec: {sha256: "..."}
  gate:
    status: PROCEED
    quality_grade: approved
    sha256: "..."
  counts:
    surfaces: 0
    journeys: 0
    actions: 0
  carry_forward_conditions: []
  handoff:
    target: G1
    authorized: true
```

Layer G получает:

- полный Layer F published package;
- pinned Layer E final pair через E package refs;
- Layer D PRD refs для traceability;
- nonblocking carry-forward conditions.

G не изменяет F artifacts. Structural problem оформляется как `downstream_return_request` с exact IDs/evidence.

---

## 18. Revision routing и invalidation

### 18.1 Earliest-owner table

| Проблема | Target |
|---|---|
| Missing/duplicate/scope surface | F1 |
| Navigation/orphan/dead-end/journey | F2 |
| Zone/hierarchy/state intent | F3 |
| Action/feedback/form/recovery semantics | F4 |
| QA logic/report error | F5 |
| PM review error | F6 |
| Accessibility review error | F7 |
| Owner decision ambiguity | F8 |
| Story/PRD defect | D3/D1 |
| Requirement defect | C1 |
| Signed design rule/value defect | E12 or earlier E owner |

### 18.2 Invalidation graph

```text
F1 → F2,F3,F4,F5,F6,F7,F8,F9
F2 → F3,F4,F5,F6,F7,F8,F9
F3 → F4,F5,F6,F7,F8,F9
F4 → F5,F6,F7,F8,F9
F5 → F6,F7,F8,F9
F6 or F7 → F8,F9
F8 → F9
```

Изменение D package обычно инвалидирует F1–F9. Изменение E final pair инвалидирует тот самый ранний F artifact, который использует изменённый rule/token, и весь downstream closure; impact analysis не может пропускать F5/F9.

---

## 19. State, concurrency и recovery

- Один active writer на каждый F1–F4 logical artifact.
- F6/F7 разрешено выполнять параллельно по immutable F5 binding.
- F8 session имеет append-only receipts и resumable checkpoint.
- Partial F8 artifact не видит F9.
- Outputs сначала staging, затем complete.
- Revision создаёт новую artifact version, старую не удаляет.
- Retry использует idempotency key.
- Current package меняется compare-and-swap после полного manifest validation.
- Crash during publish не создаёт mixed-version package.
- Stale upstream package вызывает `STALE_INPUT`, а не warning.

---

## 20. Инварианты слоя

1. Каждая canonical surface создаётся и версионируется F1.
2. Каждый MVP story flow покрыт surfaces/navigation/IA/interactions.
3. F2–F4 не добавляют surfaces.
4. Navigation transitions ссылаются на существующие surface IDs.
5. IA states имеют interaction treatment либо justified non-interactive status.
6. Reviews связаны с exact F1–F5 hashes.
7. F8 содержит только реальные owner responses.
8. F9 не публикует при missing/stale/return artifacts.
9. Final design authority — E12 tokens+grammar.
10. UX attention не смешивается с engineering decomposition.
11. Gate handoff binary и все published conditions nonblocking.
12. G получает единый immutable package.

---

## 21. Обязательные изменения промптов

### F1

- требовать D7/E12 packages и cross-package hash check;
- удалить `e9_gate_report`, E4/E10 direct inputs;
- заменить `e9_constraints` на E package condition/grammar refs;
- читать stories через D manifest;
- добавить common envelope/architecture set.

### F2

- использовать только current F1 + D/E packages;
- удалить E internal drafts/mood inputs;
- запретить missing surface workaround;
- связать transitions/journeys со story revisions и grammar refs.

### F3

- требовать D detailed stories по PRD refs;
- заменить E9/E10 references на final grammar/tokens;
- формализовать processing depth и state coverage;
- блокировать stale F1/F2.

### F4

- заменить `approved_service_states` из mood/review на signed grammar refs;
- добавить story criterion refs и accessibility obligations;
- сохранить границу semantic interaction ≠ visual component.

### F5

- проверять Layer E final conditions, не E9 review;
- добавить exact dependency binding;
- унифицировать QA verdict/status;
- формировать precise earliest restart route.

### F6

- привязать report к architecture set/hash;
- нормализовать recommendation;
- маршрутизировать upstream product defects в D/C.

### F7

- удалить неверный accessibility input E6;
- не использовать E9 как gate;
- читать signed accessibility grammar/tokens;
- добавить exact dependency binding.

### F8

- добавить отдельный session checkpoint;
- писать final decisions только после всей сессии;
- не менять F1–F4, а формировать revision route;
- проверять current F6/F7 barrier.

### F9

- сделать все F1–F8 inputs обязательными и hash-bound;
- разделить binary gate и quality grade;
- запретить blocking condition при PROCEED;
- публиковать Layer F snapshot/manifest;
- агрегировать E12 conditions вместо E9/E11 drafts.

### G boundary

- требовать Layer F publish package;
- запретить выбор latest files;
- использовать typed return request и не редактировать F напрямую.

---

## 22. Валидация и тесты

### Input/lineage tests

- F1 блокируется без D7 или E12 gate;
- D/E package mismatch блокирует F1;
- F5 отвергает mixed F1–F4 versions;
- F9 отвергает F8 decision по старому architecture set.

### Surface/navigation tests

- duplicate canonical surface ID блокирует;
- implicit MVP-core surface требует owner decision до F2;
- navigation ref на missing surface возвращает F1;
- orphan/dead end/depth violation имеет route;
- каждый critical journey имеет recovery/exit semantics.

### IA/interaction tests

- MVP surface без full IA блокирует F5;
- IA state без interaction treatment обнаруживается;
- raw visual component/style в F4 помечается boundary violation;
- grammar/token refs разрешаются в exact E package.

### Review/HITL tests

- F6/F7 по разным F5 hashes не проходят barrier;
- F8 не стартует при reviewer RETURN;
- partial F8 session не создаёт final decision artifact;
- owner structural adjustment запускает F1–F4 replay;
- неверная ссылка F7 на E6/E9 отсутствует.

### Gate/handoff tests

- missing F7 report блокирует F9;
- `PROCEED` с blocking condition запрещён;
- package publish atomic under injected failure;
- G отвергает F files без manifest/gate;
- downstream return replay идёт от earliest owner до F9.

---

## 23. Порядок реализации

1. Утвердить F schemas, common envelope и architecture set manifest.
2. Перевести F1 input contract на D7+E12 packages.
3. Обновить F1 surface records и scope/traceability.
4. Добавить строгие lineage contracts F2–F4.
5. Перевести design refs на final tokens/grammar.
6. Обновить F5 QA binding и exact routing.
7. Унифицировать F6/F7 reports и исправить accessibility inputs.
8. Добавить F8 checkpoint/decision receipts.
9. Реализовать F9 binary gate + quality grade + atomic package.
10. Обновить G preflight и добавить revision/failure tests.

---

## 24. Definition of Done

Layer F готов, когда:

- F1 стартует только по согласованным D7/E12 packages;
- ни один F-agent не использует устаревший E9 gate или E6 accessibility role;
- F1–F4 образуют версионированную и трассируемую UX architecture chain;
- F5 проверяет current set, F6/F7 дают полный review barrier;
- F8 фиксирует реальные owner decisions и маршрутизирует structural changes;
- F9 публикует только complete, current, nonblocking set;
- final package содержит все F artifacts, snapshot, gate и hashes;
- Layer G потребляет package и E12 final pair, а не internal drafts;
- revision/recovery не теряют decisions и не создают mixed versions;
- prompts, schemas, runner и тесты соответствуют этому плану.
