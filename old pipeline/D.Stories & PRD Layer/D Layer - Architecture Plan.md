# D Layer — Architecture Plan

**Слой:** D — Stories & PRD  
**Дата:** 2026-08-24  
**Ревизия:** R1  
**Статус:** ACTIVE BASELINE / PROMPT ALIGNMENT REQUIRED

**Основание:** существующие промпты D1–D7, publish-контракты Layers B/C и входные ожидания Layers E/F.

**Назначение документа:** задать архитектуру превращения проверенных требований в полный story corpus и publishable PRD без обхода upstream gates, потери per-story lineage и публикации неполного review-набора.

---

## 1. Назначение и границы слоя

Layer D формирует исполнимое продуктовое описание:

```text
Layer C approved requirements package
        ↓
story inventories
        ↓
structural validation
        ↓
detailed stories + acceptance criteria
        ↓
UX + feasibility + product/traceability reviews
        ↓
PRD gate
        ↓
immutable Layer D publish package
```

Слой отвечает за:

- исчерпывающий inventory user/system/global stories;
- осмысленное распределение requirements по stories;
- detailed story definition и Given/When/Then criteria;
- coverage matrix requirement→criterion;
- UX, logical feasibility и product traceability review;
- точный upstream routing при дефекте requirement;
- полноту и консистентность PRD package.

Layer D не:

- меняет Layer A invariants, Layer B aspects или Layer C requirements;
- проектирует UI, navigation, IA или visual system;
- выполняет инженерную декомпозицию;
- считает отсутствие review «допустимым предупреждением»;
- перезаписывает story revision без истории;
- публикует PRD до завершения всех применимых reviews.

---

## 2. Нормативные решения слоя

### Решение D-D1 — входом является approved Layer C package

D1 стартует только при наличии полного `layer_c_publish_manifest.yaml`, `LayerC.snapshot.yaml`, requirements set и C2 verdict `APPROVED | APPROVED_WITH_WARNINGS`. B8 package также доступен через pinned reference для полного aspect context.

Отсутствующий C2/B8 gate — `BLOCK`, а не warning-and-continue.

### Решение D-D2 — D1 владеет inventory structure

D1 — единственный writer трёх inventories. D3 не создаёт новые inventory rows и не декомпозирует story самостоятельно. При необходимости split/merge/reclassification D3 выпускает `d3_d1_revision_request.yaml`.

### Решение D-D3 — D2 является обязательным structural barrier

D3 запускается только по D2-approved inventory set. Отсутствующий, stale или returning D2 report блокирует детализацию.

### Решение D-D4 — story является versioned aggregate

Detailed story никогда не перезаписывается. Каждая ревизия имеет `story_revision`, source hashes и статус. Reviews привязаны к конкретной ревизии. Новая ревизия автоматически делает старые review receipts stale.

### Решение D-D5 — D3 не изменяет requirements

Дефект requirement маршрутизируется C1. D3 приостанавливает только затронутые work items и ждёт новый C2-approved package плюс обязательный D replay route.

### Решение D-D6 — reviewers образуют последовательный barrier

Нормативный порядок для каждой story revision:

```text
D3 detail → D4 UX → D5 feasibility → D6 product/traceability → D7
```

D5 использует D4 context, D6 использует D4 и D5. Это делает recommendations согласованными и устраняет неоднозначность optional inputs.

### Решение D-D7 — review applicability оформляется receipt

Для Global Story D4 может выдать `SKIP_NOT_APPLICABLE`, но обязан создать валидный receipt с rationale и story hash. Молчаливое отсутствие файла запрещено.

### Решение D-D8 — D7 требует complete review matrix

Каждая active inventory story должна иметь актуальный detailed story и все применимые review receipts. Missing, partial, stale или skipped-without-valid-reason review блокирует публикацию.

### Решение D-D9 — PRD index является индексом, не заменой corpus

`prd.index.yaml` указывает на versioned stories/reviews и содержит компактную traceability projection. Полные тексты остаются в story corpus.

### Решение D-D10 — UX и engineering attention разделены

Вместо неоднозначных `icl_complexity` и `layer_f_attention` используется:

```yaml
attention_routes:
  - target_layer: F
    concern_type: ux_architecture
    reason: "..."
  - target_layer: I
    concern_type: engineering_decomposition
    reason: "..."
```

F — UX Architecture. Инженерная декомпозиция и task graph относятся к I, а не к F.

### Решение D-D11 — D7 публикует только complete universe

Post-MVP stories могут входить в package с явным scope, но не исключаются из universe незаметно. D7 сравнивает inventory manifest, story manifest и review matrix по IDs.

### Решение D-D12 — revision replay определяется владельцем данных

Возврат к D1 инвалидирует D2–D7; возврат к D3 инвалидирует story-specific D4–D7; возврат к C1 проходит C2 и impact-driven D1/D2 replay.

---

## 3. Общий поток исполнения

### 3.1 INITIAL

```text
C2-approved Layer C package + B8 concept catalog
  ↓ preflight
D1 Story Inventory Architect [HITL only for genuine role ambiguity]
  → user_stories_inventory.yaml
  → system_stories_inventory.yaml
  → global_stories_inventory.yaml
  → story_inventory_manifest.yaml
  ↓
D2 Story Structure Validator
  ├─ RETURN_TO_D1 → D1 revision → D2
  └─ APPROVED / APPROVED_WITH_WARNINGS
         ↓
D3 Story Detailing Agent [HITL, per story]
  → detailed_stories/<story_id>/r<revision>.yaml
  → detailed_story_manifest.yaml
         ↓ per-story barriers
D4 UX Story Reviewer
  → reviews/<story_id>/d4-r<story_revision>.yaml
         ↓
D5 Logical Feasibility Reviewer
  → reviews/<story_id>/d5-r<story_revision>.yaml
         ↓
D6 Product & Traceability Reviewer
  → reviews/<story_id>/d6-r<story_revision>.yaml
         ↓ batch completeness barrier
D7 PRD Gatekeeper
  ├─ RETURN → d7_gate_report.yaml + revision_route
  └─ PROCEED → prd.index.yaml + LayerD.snapshot.yaml
                layer_d_publish_manifest.yaml
                                      ↓
                                     E1
```

### 3.2 Per-story pipeline и batch barriers

D3 может детализировать stories по очереди, а reviews разных completed stories могут исполняться независимо. Но для одной story порядок D4→D5→D6 строгий. D7 запускается только после закрытия universe barrier.

```text
Story A: D3 → D4 → D5 → D6 ┐
Story B: D3 → D4 → D5 → D6 ├→ D7
Story C: D3 → D4 → D5 → D6 ┘
```

### 3.3 Review return loop

```text
D4/D5/D6 RETURN_TO_D3
  ↓ exact story_id + story_revision + findings
D3 new story revision
  ↓
D4 → D5 → D6 replay for that story
  ↓
D7 full barrier
```

### 3.4 Upstream escalation loop

```text
D3 requirement defect
  → d3_c1_escalation.yaml
  ↓ C1 → C2
  ├─ structural impact → D1 → D2 → D3
  └─ content impact    → D3 affected stories
                           ↓ D4→D7
```

---

## 4. Роли и ownership

| Агент | Ответственность | Основные outputs | HITL |
|---|---|---|---|
| D1 | Inventory и role classification | 3 inventories + manifest | Только неоднозначность роли |
| D2 | Structural completeness/consistency | `d2_review_report.yaml` | Нет |
| D3 | Detailed story и acceptance | versioned detailed stories | Да |
| D4 | UX/value/journey review | per-story receipts + batch summary | Нет |
| D5 | Logical feasibility/NFR review | per-story receipts + batch summary | Нет |
| D6 | Product, scope и traceability review | per-story receipts + batch summary | Нет |
| D7 | Full-corpus gate и PRD publication | gate + index + snapshot | Нет |
| Runner | Locks, manifests, hashes, current package | control-plane | Нет |

Writer ownership:

```text
D1 owns inventories
D2 owns inventory review
D3 owns detailed story revisions
D4 owns UX receipts
D5 owns feasibility receipts
D6 owns product/traceability receipts
D7 owns gate and PRD index content
runner owns manifests and atomic publish
```

---

## 5. Common envelope и identities

```yaml
artifact_meta:
  artifact_type: detailed_story
  schema_version: d.detailed-story.v1
  artifact_version: 3
  layer: D
  producer: D3
  run_id: run-...
  cycle_id: cycle-...
  inventory_set_id: DINV-...
  requirements_set_id: CSET-...
  story_id: US-CORE-001
  story_revision: 2
  status: complete
  derived_from: []
  content_sha256: "..."
```

Review receipt дополнительно содержит:

```yaml
review_binding:
  story_id: US-CORE-001
  story_revision: 2
  story_sha256: "..."
  reviewer_prompt_revision: "..."
  upstream_package_ids:
    layer_b: B-...
    layer_c: C-...
```

Любое несовпадение story revision/hash делает review stale.

---

## 6. Карта рабочих и публикуемых артефактов

```text
runs/<run_id>/layer-d/<cycle_id>/
├── inventory/
│   ├── user_stories_inventory.yaml
│   ├── system_stories_inventory.yaml
│   ├── global_stories_inventory.yaml
│   └── story_inventory_manifest.yaml
├── d2/
│   └── d2_review_report.yaml
├── detailed_stories/
│   └── <story_id>/
│       ├── r1.yaml
│       └── r2.yaml
├── reviews/
│   └── <story_id>/
│       ├── d4-r2.yaml
│       ├── d5-r2.yaml
│       └── d6-r2.yaml
├── summaries/
│   ├── d4_batch_summary.yaml
│   ├── d5_batch_summary.yaml
│   └── d6_batch_summary.yaml
├── escalations/
└── d7/
    └── d7_gate_report.yaml
```

Published package:

```text
published/layer-d/<package_id>/
├── inventories/
├── detailed_stories/
├── review_receipts/
├── prd.index.yaml
├── d7_gate_report.yaml
├── LayerD.snapshot.yaml
└── layer_d_publish_manifest.yaml
```

---

## 7. D1 — inventory architecture

### 7.1 Input contract

D1 читает:

- Layer C publish manifest/snapshot/index и все active requirements;
- C2 warnings;
- Layer B catalog для aspect context;
- change impact report при Mode C.

### 7.2 Story types

- User Story — наблюдаемая пользовательская цель/результат.
- System Story — системная обязанность или внутреннее поведение.
- Global Story — сквозное quality/governance условие, не принадлежащее одному flow.

Story ID format остаётся стабильным:

```text
US-<DOMAIN>-<NNN>
SS-<DOMAIN>-<NNN>
GS-<DOMAIN>-<NNN>
```

### 7.3 Inventory record

```yaml
story_id: US-ACTIVATION-001
story_type: user
title: "..."
role: "..."
intent: "..."
delivery_scope: core
debt_disposition: none
story_attention_scope: user
source_requirement_ids: []
source_aspect_ids: []
coverage_intent: "..."
status: active
```

### 7.4 Modes

- Mode A — initial inventory.
- Mode B — correction from D2.
- Mode C — impact update after C1/C2 revision.

Mode C сохраняет unaffected story IDs. Split/merge documented через supersession/alias entries в inventory manifest.

---

## 8. D2 — structural gate

D2 проверяет:

1. Все active requirements назначены хотя бы одной story или justified global mapping.
2. Нет orphan stories без requirements/aspects.
3. Role и story type согласованы.
4. Scope не расширен.
5. Story boundaries не перегружены и не фрагментированы искусственно.
6. IDs уникальны; aliases/supersession валидны.
7. C2 warnings имеют treatment.
8. Manifest hashes совпадают.

Verdicts:

- `APPROVED`;
- `APPROVED_WITH_WARNINGS` — только nonblocking, carry-forward;
- `RETURN_TO_D1`;
- operational `BLOCK` для invalid inputs.

D3 требует current D2 report, относящийся к точному `inventory_set_id`.

---

## 9. D3 — detailed story contract

### 9.1 Story definition

```yaml
story_definition:
  story_id: US-ACTIVATION-001
  story_revision: 2
  story_type: user
  title: "..."
  role: "..."
  narrative: "Как ..., я хочу ..., чтобы ..."
  delivery_scope: core
  debt_disposition: none
  story_attention_scope: user
  source_requirement_ids: []
  source_aspect_ids: []
  preconditions: []
  trigger: "..."
  main_flow: []
  alternate_flows: []
  error_recovery: []
  postconditions: []
  out_of_scope: []
```

### 9.2 Acceptance criteria

User/System stories используют Given/When/Then. Global stories используют property/condition/guarantee.

```yaml
acceptance_criteria:
  - criterion_id: AC-01
    given: "..."
    when: "..."
    then: "..."
    covers_requirement_ids: [USR-...]
    covers_requirement_criteria: [USR-...#AC-01]
```

Нормативный диапазон 3–10 критериев является quality heuristic. Если requirement coverage требует больше, story следует пересмотреть на перегрузку, а не терять критерии.

### 9.3 Coverage matrix

```yaml
coverage_matrix:
  requirements:
    USR-...:
      criterion_ids: [AC-01, AC-02]
      coverage: complete
  uncovered: []
```

### 9.4 Questions и escalation

`blocking` question приостанавливает story. `nonblocking` question может переноситься только с explicit assumption, risk и downstream owner.

Если отсутствует или противоречив requirement:

```yaml
d3_c1_escalation:
  escalation_id: D3-C1-...
  story_id: US-...
  story_revision: 1
  requirement_ids: []
  issue_type: missing | ambiguous | conflicting | untestable | wrong_scope
  evidence: []
  requested_outcome: "..."
```

Если нужна другая story structure, target — D1, не C1.

---

## 10. D4 — UX Story Review

D4 проверяет только story-level UX intent:

- ясность user goal;
- continuity и recovery;
- value/Aha alignment;
- лишнюю friction;
- наличие system support для user outcome;
- отсутствие преждевременной UI детализации.

Canonical recommendation:

- `PROCEED`;
- `PROCEED_WITH_NOTES`;
- `RETURN_TO_D3`;
- `SKIP_NOT_APPLICABLE` — только Global story с rationale.

`BLOCK` используется только при invalid input. Review содержит precise finding IDs и suggested outcome, но не переписывает story.

---

## 11. D5 — Logical Feasibility Review

D5 оценивает реализуемость на логическом уровне:

- согласованность states/transitions;
- полноту system obligations;
- NFR pressure;
- integrity, concurrency, durability и limit implications;
- observability/recovery requirements;
- конфликт с architecture aspects;
- уровень инженерного внимания без проектирования решения.

Recommendations:

- `PROCEED`;
- `PROCEED_WITH_NOTES`;
- `RETURN_TO_D3`;
- `ESCALATE_UPSTREAM` с target `C1 | B4`.

Вместо неоднозначного `implementation_complexity`:

```yaml
implementation_attention:
  level: low | medium | high | critical
  reasons: []
  route_to_layer_i: true
```

Layer F не является engineering decomposition target.

---

## 12. D6 — Product & Traceability Review

D6 проверяет:

- соответствие value mechanism и MVP;
- requirement/aspect/criterion coverage;
- отсутствие scope creep;
- согласованность D4/D5 recommendations;
- treatment risks, warnings и kill criteria;
- необходимость downstream UX/engineering attention.

Recommendations:

- `PROCEED`;
- `PROCEED_WITH_NOTES`;
- `RETURN_TO_D3`;
- `BLOCK_UPSTREAM_CONFLICT`.

D6 не читает поля, которых нет в D5 schema. Все dependencies версионируются в `review_binding`.

Пример routes:

```yaml
attention_routes:
  - target_layer: F
    concern_type: complex_user_recovery
    source_finding_ids: [D4-F-03]
  - target_layer: I
    concern_type: high_concurrency_pressure
    source_finding_ids: [D5-F-02]
```

---

## 13. Review matrix и completeness barrier

Runner строит матрицу:

| Story | Revision | D3 | D4 | D5 | D6 | Ready for D7 |
|---|---:|---|---|---|---|---|
| US-001 | 2 | complete | proceed | proceed | proceed | yes |
| SS-002 | 1 | complete | proceed | notes | proceed | yes |
| GS-003 | 1 | complete | valid skip | proceed | proceed | yes |

`Ready for D7 = yes` только если:

- story является active в current inventory;
- story revision/hash current;
- D4 receipt current либо valid skip;
- D5 receipt current и не return/escalate;
- D6 receipt current и не return/block;
- все batch summaries включают story ID.

Incomplete rows не исключаются из denominator.

---

## 14. D7 gate

### 14.1 Gate checks

D7 проверяет:

1. B/C source packages и gates валидны.
2. D2 approved current inventory set.
3. Каждая active inventory story имеет current detail.
4. Review matrix полна.
5. Нет return/escalate/block recommendations.
6. Requirement→story→criterion traceability замкнута.
7. Все C2/D2 warnings обработаны или перенесены.
8. Scope/debt axes согласованы.
9. Нет unresolved blocking question.
10. PRD refs указывают на существующие immutable revisions.

### 14.2 Gate vocabulary

Нормативный verdict бинарный:

- `PROCEED` — publication разрешена;
- `BLOCK` — publication запрещена, route обязателен.

Nonblocking notes переносятся в package, но не создают третий gate status.

### 14.3 Revision route

```yaml
revision_route:
  restart_from: C1 | D1 | D3 | D4 | D5 | D6
  affected_story_ids: []
  affected_requirement_ids: []
  finding_ids: []
  required_closure: []
```

D7 не исправляет artifacts и не делает partial PRD.

---

## 15. `prd.index.yaml`

```yaml
prd_index:
  prd_id: PRD-...
  source_packages:
    layer_b: B-...
    layer_c: C-...
  inventory_set_id: DINV-...
  stories:
    US-ACTIVATION-001:
      story_type: user
      story_revision: 2
      story_sha256: "..."
      path: detailed_stories/US-ACTIVATION-001/r2.yaml
      delivery_scope: core
      debt_disposition: none
      source_requirement_ids: []
      source_aspect_ids: []
      review_receipts:
        D4: {sha256: "...", recommendation: PROCEED}
        D5: {sha256: "...", recommendation: PROCEED}
        D6: {sha256: "...", recommendation: PROCEED}
      attention_routes: []
  traceability_summary: {}
  carry_forward: []
```

Index не содержит сырые review рассуждения и не заменяет story files.

---

## 16. Publish package и handoff

`LayerD.snapshot.yaml`:

```yaml
layer_d_snapshot:
  package_id: D-...
  prd_ref: {path: prd.index.yaml, sha256: "..."}
  gate_ref: {path: d7_gate_report.yaml, sha256: "..."}
  source_layer_c_package_id: C-...
  story_counts:
    user: 0
    system: 0
    global: 0
  delivery_scope_counts: {}
  attention_routes_summary:
    F: []
    I: []
  carry_forward: []
  handoff:
    target: E1
    authorized: true
```

Layers E и F используют только published D package. F может читать детальные stories по manifest, но не сканирует произвольный каталог и не выбирает «последнюю» ревизию самостоятельно.

---

## 17. Revision и invalidation matrix

| Restart | Обязательный closure |
|---|---|
| C1 structural | C1→C2→D1→D2→affected/all D3→D4→D5→D6→D7 |
| C1 content | C1→C2→affected D3→D4→D5→D6→D7 |
| D1 | D1→D2→affected/all D3→D4→D5→D6→D7 |
| D3 | D3→D4→D5→D6→D7 |
| D4 | D4→D5→D6→D7 |
| D5 | D5→D6→D7 |
| D6 | D6→D7 |

Изменение одной story инвалидирует только её downstream receipts плюс corpus-level batch summaries/gate, если inventory и shared globals не изменились.

---

## 18. State, concurrency и recovery

- D1 publish inventories atomically as one set.
- D3 имеет lease на конкретный `story_id`.
- Разные stories могут обрабатываться параллельно, одна story — только одним writer.
- Per-story review запускается по committed story revision.
- Review retry с тем же idempotency key не создаёт дубликат.
- Batch summary является projection manifests, не самостоятельным источником статуса.
- Crash в HITL D3 возобновляется с checkpoint; partial story не видит D4.
- Compare-and-swap защищает current story revision и published package.

---

## 19. Инварианты слоя

1. Каждый active requirement покрыт story и acceptance criterion.
2. Каждая active story имеет хотя бы один requirement/aspect source.
3. D3 не меняет inventory или requirements.
4. Review связан с точной story revision/hash.
5. Missing review не равен skip.
6. Global D4 skip оформлен receipt.
7. D7 рассматривает весь inventory universe.
8. PRD не содержит stale story/review refs.
9. UX attention маршрутизируется F, engineering attention — I.
10. Published package имеет единый D gate/hash lineage.
11. Upstream changes вызывают обязательный downstream closure.
12. `PROCEED` невозможен при blocking question/escalation.

---

## 20. Обязательные изменения промптов

### D1

- сделать B8/C2 packages обязательными;
- ввести inventory set/manifest и atomic staging;
- формализовать Mode C impact replay;
- добавить source aspect IDs и debt axis.

### D2

- связывать report с exact inventory set/hash;
- формализовать warning carry-forward;
- блокировать D3 при absence/stale report.

### D3

- унифицировать Modes A–D;
- запретить прямое изменение inventory/decomposition;
- использовать immutable story revisions;
- добавить `story_attention_scope`, source aspect IDs и coverage matrix;
- запретить delete/overwrite review files;
- разделить C1 и D1 escalations.

### D4–D6

- унифицировать recommendation vocabulary;
- сделать inputs и review dependency chain обязательными;
- привязать receipts к story hash;
- оформить Global skip;
- исправить field mismatches D5→D6.

### D7

- заменить «исключить incomplete» на blocking universe check;
- сделать gate бинарным;
- добавить immutable refs/hashes и publish package;
- заменить `icl_complexity`/ошибочный Layer F task graph на typed attention routes.

### E/F boundary

- требовать Layer D manifest/snapshot/gate;
- выбирать detailed story только через PRD ref;
- не читать working copies и stale reviews.

---

## 21. Валидация и тесты

### Inventory tests

- missing requirement mapping возвращает D1;
- duplicate story ID блокирует D2;
- split сохраняет supersession history;
- D3 не стартует без D2 current approval.

### Story tests

- каждый requirement criterion покрыт story criterion;
- missing `story_attention_scope` блокирует completion;
- story overwrite отклоняется;
- blocking question не позволяет review.

### Review tests

- новая story revision делает старые D4/D5/D6 stale;
- D5 не стартует без applicable D4 receipt;
- D6 не стартует без current D5;
- Global D4 valid skip принимается, отсутствующий файл — нет;
- incomplete story остаётся в D7 denominator.

### Gate/handoff tests

- D7 не публикует при missing review;
- D7 не публикует при mixed C package hashes;
- PRD refs разрешаются и hashes совпадают;
- E1 отвергает D package без `PROCEED`;
- crash during publish сохраняет предыдущий current package.

### Revision tests

- D3 return переигрывает D4→D7 только для affected story плюс batch barriers;
- C1 split запускает D1/D2;
- C1 content change не использует stale story;
- D5 architecture escalation корректно маршрутизируется B4 через orchestrator.

---

## 22. Порядок реализации

1. Утвердить inventory/story/review schemas и common envelope.
2. Сделать B/C preflight обязательным в D1.
3. Реализовать inventory set manifest и D2 barrier.
4. Перевести D3 на immutable per-story revisions/checkpoints.
5. Ввести version-bound review receipts и sequential dependencies.
6. Реализовать complete review matrix.
7. Обновить D7 binary gate, PRD index и atomic package.
8. Исправить typed attention routes и E/F contracts.
9. Добавить failure, stale-input и revision tests.

---

## 23. Definition of Done

Layer D готов, когда:

- D1 не работает без approved B/C packages;
- D2 является реальным barrier;
- inventories и stories имеют стабильные IDs и immutable revisions;
- D3 не меняет upstream/inventory data;
- D4→D5→D6 дают полный current receipt set;
- D7 блокирует missing/stale/return artifacts;
- requirement→story→criterion traceability замкнута;
- PRD package атомарен, versioned и hash-linked;
- F и I routes семантически разведены;
- E/F потребляют только published D package;
- prompts, schemas, runner и тесты соответствуют плану.

