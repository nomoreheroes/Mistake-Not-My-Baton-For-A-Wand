# B Layer — Architecture Plan

**Слой:** B — Concept Coverage  
**Дата:** 2026-08-24  
**Ревизия:** R1  
**Статус:** ACTIVE BASELINE / PROMPT ALIGNMENT REQUIRED

**Основание:** существующие промпты B1–B8, publish-контракт Layer A и входные ожидания C1/C2.

**Назначение документа:** зафиксировать целевую архитектуру исполнения Layer B. План сохраняет роли агентов и смысл текущих артефактов, но устраняет неоднозначность patch-chain, неполный merged index и возможность запуска Layer C без положительного gate.

---

## 1. Назначение и границы слоя

Layer B превращает подтверждённый пакет Idea Note в проверенный каталог аспектов концепта:

```text
Layer A publish package
        ↓
owner-confirmed projection
        ↓
product + marketing + architecture + operations + governance coverage
        ↓
similarity resolution
        ↓
binary gate
        ↓
immutable Layer B publish package для C1
```

Слой отвечает на вопросы:

1. Какие аспекты необходимы, чтобы раскрыть утверждённый продуктовый замысел без изменения его границ?
2. Какие аспекты относятся к core loop, entities, scenarios, experiments, marketing, architecture, operations и governance?
3. Какие риски устранены, минимизированы или явно приняты владельцем?
4. Где аспекты дублируются, частично перекрываются либо состоят в отношении parent/child?
5. Достаточно ли каталога для детерминированного перевода в требования?

Layer B не:

- изменяет frozen invariants Layer A;
- расширяет MVP под видом «полноты»;
- формулирует требования, stories, IA или технические задачи;
- автоматически принимает спорные риски и merge-решения;
- использует similarity score как разрешение на удаление данных;
- заставляет downstream-агентов реконструировать состояние из произвольного набора патчей.

---

## 2. Нормативные решения слоя

### Решение B-D1 — входом является только валидная пара Layer A

B1 стартует при одновременном наличии:

- `final_gate_decision.yaml` со статусом `PROCEED`;
- `IdeaNoteLayer.snapshot.yaml`, hash которого указан в gate;
- `handoff_authorization.status: confirmed`.

Один файл без другого, несовпадающий hash или незавершённая owner-авторизация дают preflight `BLOCK` без содержательной работы.

### Решение B-D2 — roster B1–B8 сохраняется

Новые продуктовые роли не требуются. Оркестратор управляет запуском, версиями, checkpoints, barrier-проверками и публикацией. Агенты владеют содержательными артефактами; runner владеет manifest и атомарным переключением current package.

### Решение B-D3 — patches являются provenance, а не API слоя

B2–B7 выпускают immutable patches. Они нужны для аудита, replay и расследования решений, но Layer C не читает patch-chain. Единственным содержательным downstream-представлением становится `concept_catalog.yaml`, опубликованный B8.

### Решение B-D4 — полный aspect record хранится в каталоге

`aspect_index_additions` с одним metadata недостаточен: C1 и reviewers используют `goal_brief`, `mechanism_brief`, scope, risk и traceability. Поэтому каждая активная запись `concept_catalog.yaml` содержит полный нормализованный aspect record.

### Решение B-D5 — single writer и append-only lineage

Каждый исходный артефакт имеет одного writer. Старые версии и patches не перезаписываются. B8 материализует новую версию каталога в staging и публикует её только после валидации.

### Решение B-D6 — merge не удаляет происхождение

Решение `merge` создаёт:

- surviving canonical aspect;
- alias для каждого поглощённого `aspect_id`;
- union traceability и coverage;
- owner decision receipt;
- merge provenance с версиями исходных records.

`drop` допустим только для подтверждённого дубликата и также оставляет tombstone/alias. Locked aspect нельзя merge/drop/defer без возврата в Layer A.

### Решение B-D7 — similarity является candidate generator

Порог похожести формирует кандидата на проверку. Автоматический destructive merge или drop запрещён независимо от score. B7 задаёт владельцу один кластерный вопрос за раз.

### Решение B-D8 — две независимые оси scope

Каталог различает:

- `delivery_scope`: `core | supporting | post_mvp`;
- `debt_disposition`: `none | technical_debt`.

Это предотвращает потерю сигнала B4 `technical_debt` и запрещает трактовать технический долг как автоматический post-MVP.

### Решение B-D9 — B8 является единственным publish gate

B8 выдаёт бинарный `PROCEED | BLOCK`. При `PROCEED` он атомарно публикует каталог, snapshot, gate report и manifest. При `BLOCK` никакой новый current package не появляется.

### Решение B-D10 — C1/C2 не собирают virtual merge

Все правила применения B2–B7, alias resolution и status updates реализуются один раз в B8 materializer. Повторная реализация merge-логики в C запрещена.

### Решение B-D11 — owner decisions отделены от inference

Подтверждения B1 и B7 имеют decision receipts с реальным ответом, временем, затронутыми ID и исходной формулировкой вопроса. Агент не заполняет ответ за владельца.

### Решение B-D12 — accepted risk не исчезает из downstream

Принятый риск сохраняет rationale, owner, review trigger и `do_not_resurface` semantics. Флаг означает «не задавать тот же вопрос без нового сигнала», а не «игнорировать риск в требованиях или acceptance criteria».

---

## 3. Общий поток исполнения

### 3.1 INITIAL

```text
A6 PROCEED + confirmed handoff
  ↓ preflight: schema, hashes, lineage
B1 Snapshot Projection & Coverage Interview [HITL]
  → concept_coverage_map.yaml
  → b1_owner_decisions.yaml
  ↓
B2 Product Coverage Reviewer
  → patches/B2.patch.yaml
  ↓
B3 Marketing Coverage Reviewer
  → patches/B3.patch.yaml
  ↓
B4 Architecture Coverage Reviewer
  → patches/B4.patch.yaml
  ↓
B5 Risk & Operations Coverage Reviewer
  → patches/B5.patch.yaml
  ↓
B6 Ethics & Governance Coverage Reviewer
  → patches/B6.patch.yaml
  ↓
B7 Similarity Resolution [HITL]
  → patches/B7.patch.yaml
  → b7_owner_decisions.yaml
  ↓
B8 Gatekeeper + deterministic materializer
  ├─ BLOCK   → b8_gate_report.yaml + revision_route
  └─ PROCEED → concept_catalog.yaml
                LayerB.snapshot.yaml
                layer_b_publish_manifest.yaml
                                      ↓
                                     C1
```

### 3.2 Barrier rules

Следующий агент запускается только если:

1. Предыдущий обязательный output опубликован и имеет статус `complete`.
2. Его `derived_from` совпадает с текущей цепочкой.
3. Все входные hashes совпадают с manifest.
4. Нет `in_progress`, `partial` или незавершённой HITL-сессии.
5. Readiness-флаг предыдущего агента разрешает следующий этап.

B3–B6 идут последовательно: каждый видит предшествующие patches как контекст и обязан различать новый gap и уже зафиксированное покрытие. B7 запускается только после полного barrier B2–B6.

### 3.3 REVISION

```text
B8 BLOCK / downstream return
  ↓ revision_route.restart_from
  ├─ B1 → B1…B8
  ├─ B2 → B2…B8
  ├─ B3 → B3…B8
  ├─ B4 → B4…B8
  ├─ B5 → B5…B8
  ├─ B6 → B6…B8
  └─ B7 → B7→B8
```

Replay создаёт новый `cycle_id`; outputs старого цикла остаются immutable. downstream closure обязателен: нельзя использовать старый B8 report с новым B4 patch.

---

## 4. Роли и владение артефактами

| Агент | Ответственность | Основной output | HITL |
|---|---|---|---|
| B1 | Проекция Layer A, первичное покрытие и risk disposition | `concept_coverage_map.yaml` | Да |
| B2 | Product/functional coverage | `patches/B2.patch.yaml` | Нет |
| B3 | Value, activation, retention, acquisition, pricing, trust | `patches/B3.patch.yaml` | Нет |
| B4 | Integrity, durability, limits, security, observability | `patches/B4.patch.yaml` | Нет |
| B5 | Monitoring, incident, escalation, recovery, operating load | `patches/B5.patch.yaml` | Нет |
| B6 | Guardrails, enforcement, authorization, audit, revocation | `patches/B6.patch.yaml` | Нет |
| B7 | Similarity clusters и owner resolution | `patches/B7.patch.yaml` | Да |
| B8 | Gate, materialization, publication и routing | gate + catalog + snapshot | Нет |
| Runner | run state, locks, hashes, manifests, atomic publish | control-plane files | Нет |

Writer ownership:

```text
B1 owns base map + B1 receipts
B2 owns B2 patch
B3 owns B3 patch
B4 owns B4 patch
B5 owns B5 patch
B6 owns B6 patch
B7 owns B7 patch + B7 receipts
B8 owns gate report + materialized catalog + layer snapshot
runner owns run manifest + publish manifest + current pointer
```

Reviewers не редактируют base map и чужие patches. Ошибка upstream оформляется как `revision_request`, а не как скрытая коррекция.

---

## 5. Common artifact envelope

Каждый YAML-артефакт содержит:

```yaml
artifact_meta:
  artifact_type: concept_patch
  schema_version: b.concept-patch.v1
  artifact_version: 1
  layer: B
  producer: B4
  run_id: run-...
  cycle_id: cycle-...
  created_at: 2026-08-24T00:00:00Z
  status: complete
  derived_from:
    - artifact_type: concept_coverage_map
      artifact_version: 1
      sha256: "..."
  content_sha256: "..."
```

Обязательные правила:

- hash считается по канонически сериализованному content без поля самого hash;
- `artifact_version` монотонен в пределах logical artifact;
- `status: complete` выставляется только после schema/self-audit;
- вход без поддерживаемой schema version блокирует агента;
- timestamp не используется как единственный идентификатор версии;
- любой human response ссылается на `session_id` и `question_id`.

---

## 6. Карта артефактов

### 6.1 Working artifacts

```text
runs/<run_id>/layer-b/<cycle_id>/
├── inputs/
│   └── layer_a.lock.yaml
├── b1/
│   ├── concept_coverage_map.yaml
│   └── b1_owner_decisions.yaml
├── patches/
│   ├── B2.patch.yaml
│   ├── B3.patch.yaml
│   ├── B4.patch.yaml
│   ├── B5.patch.yaml
│   ├── B6.patch.yaml
│   └── B7.patch.yaml
├── b7/
│   ├── similarity_candidates.yaml
│   └── b7_owner_decisions.yaml
├── b8/
│   └── b8_gate_report.yaml
└── run_manifest.yaml
```

### 6.2 Published package

```text
published/layer-b/<package_id>/
├── concept_catalog.yaml
├── LayerB.snapshot.yaml
├── b8_gate_report.yaml
└── layer_b_publish_manifest.yaml
```

Только файлы published package являются контрактом Layer C. Working artifacts доступны для аудита, но не являются разрешённым способом запуска C1.

### 6.3 Compatibility mapping

На переходный период старые имена отображаются так:

| Legacy | Нормативное имя |
|---|---|
| `b2_patch.yaml` | `patches/B2.patch.yaml` |
| `concept_coverage_patch_B3.yaml` | `patches/B3.patch.yaml` |
| `concept_coverage_patch_B4.yaml` | `patches/B4.patch.yaml` |
| `concept_coverage_patch_B5.yaml` | `patches/B5.patch.yaml` |
| `concept_coverage_patch_B6.yaml` | `patches/B6.patch.yaml` |
| `concept_coverage_patch_B7.yaml` | `patches/B7.patch.yaml` |

Compatibility alias не создаёт вторую независимую копию и не участвует в hash-chain.

---

## 7. Контракт B1 — projection и owner coverage

B1 переносит факты Layer A без смыслового расширения и разделяет:

- `locked_invariants` — подтверждённые решения A;
- `coverage_aspects` — раскрытие этих решений для следующего слоя;
- `recommendations` — ещё не принятые варианты;
- `accepted_risks`;
- `deferred_items`;
- `decision_log`.

Базовая карта содержит shards:

```yaml
shards:
  core_loop: []
  entities: []
  scenarios: []
  experiments: []
  marketing: []
  architecture: []
  operations: []
  governance: []
```

Минимальный aspect record:

```yaml
aspect_id: ASP-CORE-001
canonical_title: "..."
shard: core_loop
category: value_mechanism
goal_brief: "..."
mechanism_brief: "..."
delivery_scope: core
debt_disposition: none
status: active
locked: false
source_refs:
  - artifact: IdeaNoteLayer.snapshot.yaml
    path: frozen_core.value_mechanism
    sha256: "..."
risk_refs: []
decision_refs: []
coverage_tags: []
expected_requirement_types: [USR, SSR]
```

B1 задаёт один вопрос за раз и пишет финальный decision receipt только после реального ответа. Checkpoint может хранить прогресс с `status: in_progress`, но не подменяет итоговый output.

Readiness B1 требует:

- полного projection frozen core;
- подтверждения locked items;
- явного disposition каждого Layer A risk;
- mitigation aspect для каждого `minimize`;
- rationale и review trigger для каждого `accept`;
- отсутствия blocking owner question.

---

## 8. Контракты B2–B6 — domain patches

Общий patch format:

```yaml
patch:
  patch_id: B4-P-001
  base_catalog_ref:
    artifact_version: 1
    sha256: "..."
  prior_patch_refs: []
  add_aspects: []
  update_metadata: []
  conflicts: []
  cross_domain_gaps: []
  reviewer_findings: []
  readiness:
    status: ready_for_next | return_upstream | blocked
  self_audit: {}
```

Разрешённые изменения:

- добавить аспект в собственный shard;
- дополнить non-authoritative metadata своего аспекта;
- зарегистрировать gap другого домена;
- зарегистрировать contradiction или Layer A conflict.

Запрещённые изменения:

- удалять или переписывать существующий аспект;
- расширять MVP;
- изменять locked invariant;
- принимать risk за owner;
- перемещать аспект между shards без routing;
- скрывать overlap ради локальной «чистоты».

Специализация:

| Агент | Shard | Обязательная перспектива |
|---|---|---|
| B2 | `core_loop`, `entities`, `scenarios`, `experiments` | функциональная полнота, сценарии, состояния, измеримость эксперимента |
| B3 | `marketing` | ценность, category framing, Aha, onboarding, retention, acquisition, pricing, trust |
| B4 | `architecture` | integrity, concurrency, durability, observability, containment, limits, security |
| B5 | `operations` | detection, monitoring, diagnostics, response, escalation, recovery, operating load |
| B6 | `governance` | guardrail→enforcement, authorization, auditability, revocation, misuse prevention |

`cross_domain_gaps` не означает, что агент сам добавляет запись в чужой shard. Соответствующий downstream owner рассматривает gap и явно отмечает `adopted | already_covered | rejected_with_reason | route_upstream`.

---

## 9. Контракт B7 — similarity resolution

### 9.1 Candidate graph

B7 строит граф без мутации данных:

```yaml
similarity_cluster:
  cluster_id: SIM-001
  member_ids: [ASP-MKT-003, ASP-CORE-008]
  relation: near_duplicate | partial_overlap | parent_child
  evidence:
    semantic_score: 0.88
    shared_coverage_tags: [activation]
    distinct_obligations: []
  suggested_options: [merge, keep_separate, defer_one]
```

Score является объяснимым сигналом, не решением.

### 9.2 Owner resolutions

Допустимые решения:

- `merge`;
- `keep_separate`;
- `drop_duplicate`;
- `defer`;
- `route_upstream`.

Для каждого решения записываются owner response, rationale, affected IDs и resulting canonical ID. В одном вопросе рассматривается один кластер.

### 9.3 Merge transaction

```yaml
merge_operation:
  operation_id: MERGE-001
  survivor_id: ASP-CORE-008
  absorbed_ids: [ASP-MKT-003]
  merged_fields:
    source_refs: union
    requirement_expectations: union
    coverage_tags: union
  aliases:
    ASP-MKT-003: ASP-CORE-008
  owner_decision_ref: DEC-B7-014
```

Если тексты records противоречат друг другу, B7 не синтезирует «среднюю» формулировку молча: он запрашивает точный canonical wording либо возвращает к владельцу исходного аспекта.

---

## 10. Canonical `concept_catalog.yaml`

Каталог материализуется детерминированно из base map и упорядоченных patches B2→B7.

```yaml
concept_catalog:
  catalog_id: BCAT-...
  source_layer_a:
    package_id: A-...
    snapshot_sha256: "..."
    gate_sha256: "..."
  aspects:
    ASP-CORE-001:
      # полный aspect record
  aliases:
    ASP-MKT-003:
      canonical_id: ASP-CORE-008
      reason: merged
      operation_ref: MERGE-001
  tombstones: []
  locked_invariants: []
  accepted_risks: []
  deferred_items: []
  decisions: []
  coverage_summary: {}
```

Детерминированный порядок применения:

1. B1 base records.
2. B2 additions.
3. B3 additions.
4. B4 additions.
5. B5 additions.
6. B6 additions.
7. B7 status, alias и merge operations.
8. Normalization и integrity validation.

Все `source_refs`, risk refs и decision refs сохраняются. Alias resolution не должна образовывать циклы.

---

## 11. B8 gate и публикация

### 11.1 Gate checks

B8 проверяет:

1. Valid Layer A pair и неизменность locked invariants.
2. Полноту mandatory shards относительно текущего продукта.
3. Наличие полного record для каждого active aspect.
4. Уникальность IDs и отсутствие alias cycles.
5. Разрешение всех destructive similarity candidates.
6. Traceability accepted risks и mitigations.
7. Guardrail→enforcement coverage.
8. Отсутствие unresolved critical contradiction.
9. Отсутствие несанкционированного MVP expansion.
10. Совпадение всех versions/hashes текущего cycle.

### 11.2 Gate result

```yaml
layer_b_gate:
  verdict: PROCEED | BLOCK
  checks: []
  findings:
    critical: []
    significant: []
    advisory: []
  revision_route:
    restart_from: B1 | B2 | B3 | B4 | B5 | B6 | B7 | null
    issue_ids: []
  publish_authorized: true
```

`critical` всегда блокирует. `significant` блокирует, если нарушает completeness, traceability, scope или downstream determinism. `advisory` переносится в snapshot и не маскирует незавершённое решение.

### 11.3 Atomic publication

При `PROCEED` runner:

1. создаёт package в staging;
2. записывает catalog, snapshot и gate report;
3. проверяет schema и hashes;
4. создаёт publish manifest;
5. атомарно переключает current pointer.

При любой ошибке staging остаётся непубликованным. Предыдущий published package не меняется.

---

## 12. `LayerB.snapshot.yaml` и handoff в C

Snapshot — компактная control projection, а не второй каталог:

```yaml
layer_b_snapshot:
  package_id: B-...
  catalog_ref:
    path: concept_catalog.yaml
    sha256: "..."
  gate_ref:
    path: b8_gate_report.yaml
    sha256: "..."
  source_layer_a_package_id: A-...
  active_aspect_count: 0
  alias_count: 0
  accepted_risk_count: 0
  deferred_count: 0
  carry_forward:
    advisory_findings: []
  handoff:
    target: C1
    authorized: true
```

C1 preflight принимает только manifest, snapshot, gate и catalog одного package. Отдельные B1/B2…B7 файлы запрещены как operational input C1/C2.

---

## 13. Revision, invalidation и routing

### 13.1 Data-owner routing

| Проблема | Owner / restart |
|---|---|
| Ошибка frozen invariant | Layer A |
| Ошибка base projection/risk disposition | B1 |
| Functional coverage | B2 |
| Marketing coverage | B3 |
| Architecture coverage | B4 |
| Operations coverage | B5 |
| Governance coverage | B6 |
| Similarity/alias/status | B7 |
| Materialization/gate logic | B8/runner |

### 13.2 Invalidation

Изменение B1 инвалидирует B2–B8. Изменение любого patch инвалидирует все downstream patches, которые читали его, B7 и B8. Любое изменение B7 инвалидирует B8 package.

Downstream return из C должен содержать:

```yaml
return_request:
  source_layer: C
  target_layer: B
  restart_from: B2
  issue_ids: []
  affected_aspect_ids: []
  evidence_refs: []
  requested_change: "..."
```

C не редактирует catalog самостоятельно.

---

## 14. Consistency, locking и recovery

- На один `project_id + layer + cycle_id` действует один active writer lease.
- HITL checkpoint обновляется атомарно и не считается published artifact.
- После сбоя runner продолжает с последнего подтверждённого checkpoint.
- Agent output сначала получает `status: staging`, затем валидируется, затем становится `complete`.
- `current` никогда не указывает на staging/partial package.
- Повторный запуск с тем же idempotency key возвращает существующий результат или безопасно продолжает его.
- Конфликт версий приводит к `STALE_INPUT`, а не к last-write-wins.

---

## 15. Инварианты слоя

1. Frozen facts Layer A не меняются в Layer B.
2. Каждый active aspect имеет полный record и уникальный canonical ID.
3. Каждый non-canonical ID разрешается ровно в один canonical ID или tombstone.
4. Alias graph ацикличен.
5. Locked aspect не подвергается destructive resolution.
6. Каждый accepted risk имеет owner decision и review trigger.
7. Каждый minimized risk связан хотя бы с одним mitigation aspect.
8. Каждый governance guardrail имеет enforcement intent либо явный blocking gap.
9. Patch не меняет данные другого writer.
10. B8 materialization воспроизводима из зафиксированных inputs.
11. Layer C получает только B8-published package.
12. `PROCEED` невозможен при unresolved blocking HITL item.

---

## 16. Обязательные изменения существующих промптов

### B1

- добавить обязательный A gate и проверку hash/authorization;
- добавить common envelope и decision receipts;
- нормализовать scope в две оси;
- запретить прямую публикацию partial HITL output.

### B2–B6

- унифицировать имена и schema patches;
- добавить `base_catalog_ref`, prior patch refs и content hashes;
- формализовать owner shard и cross-domain routing;
- использовать полный `add_aspects` record;
- запретить расширение MVP и upstream mutation.

### B7

- отделить candidates от resolutions;
- определить atomic merge operation, aliases и tombstones;
- запретить автоматические destructive actions;
- добавить owner decision receipt и checkpoint/resume.

### B8

- сделать gate строгим binary;
- материализовать полный `concept_catalog.yaml`;
- публиковать `LayerB.snapshot.yaml` и manifest;
- классифицировать severity и формировать точный revision route;
- проверять versions/hashes, alias graph и полный records.

### C1/C2 boundary

- удалить reconstruction base+patches;
- требовать `layer_b_publish_manifest.yaml`, `LayerB.snapshot.yaml`, `b8_gate_report.yaml`, `concept_catalog.yaml` одного package.

---

## 17. Валидация и тесты

### 17.1 Schema tests

- envelope обязателен для каждого YAML;
- full aspect record валиден;
- patch operations соответствуют allow-list;
- decision receipt не содержит пустого/синтетического owner response;
- catalog aliases ссылаются на существующие records.

### 17.2 Lineage tests

- изменённый hash Layer A блокирует B1;
- B4 с неверным prior B3 hash блокируется;
- B8 не принимает patches разных cycles;
- C1 не принимает каталог без соответствующего gate/manifest.

### 17.3 Semantic invariants

- попытка изменить locked invariant даёт return в A;
- technical debt не превращается в post-MVP;
- accepted risk сохраняется после merge;
- merge объединяет traceability;
- orphan mitigation и unenforced guardrail блокируют gate.

### 17.4 Revision tests

- return к B4 повторяет B4→B8;
- B7 Mode B не переспрашивает unaffected clusters;
- сбой во время publish не меняет current package;
- stale review не может участвовать в gate.

### 17.5 Golden-path acceptance

```text
A package → B1 interview → B2…B6 → B7 interview → B8 PROCEED
→ published catalog/snapshot/gate/manifest
→ C1 preflight succeeds without patch reconstruction
```

---

## 18. Порядок реализации

1. Утвердить common envelope и schemas base/patch/catalog/gate.
2. Исправить A→B preflight в B1.
3. Унифицировать B2–B7 patch protocol и filenames.
4. Реализовать deterministic materializer и alias graph validation.
5. Добавить B8 atomic publish package.
6. Перевести C1/C2 на новый handoff.
7. Добавить HITL checkpoints B1/B7.
8. Добавить lineage, revision и failure-injection tests.

---

## 19. Definition of Done

Layer B архитектурно готов, когда:

- B1 не запускается без подтверждённого Layer A package;
- B2–B7 создают immutable, hash-linked patches;
- B7 не теряет traceability при merge/drop/defer;
- B8 воспроизводимо строит полный canonical catalog;
- `PROCEED` публикует атомарный package, а `BLOCK` не меняет current;
- C1/C2 не знают о внутреннем patch-chain;
- все active aspects, risks, decisions и aliases валидны и трассируемы;
- revision replay идёт от владельца данных до B8;
- prompts, schemas, runner и тесты соответствуют этому плану.

