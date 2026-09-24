# C Layer — Architecture Plan

**Слой:** C — Requirements  
**Дата:** 2026-08-24  
**Ревизия:** R1  
**Статус:** ACTIVE BASELINE / PROMPT ALIGNMENT REQUIRED

**Основание:** существующие промпты C1/C2, целевой publish-контракт Layer B и фактические входы D1–D3.

**Назначение документа:** определить безопасный перевод canonical concept catalog в проверенный, версионированный requirements package и единый протокол возврата из Layer D.

---

## 1. Назначение и границы слоя

Layer C преобразует активные аспекты Layer B в атомарные, проверяемые требования трёх типов:

```text
Layer B published concept catalog
        ↓
C1 controlled translation + HITL
        ↓
USR + SSR + NFR + requirements index
        ↓
C2 independent validation
        ↓
immutable Layer C publish package
        ↓
Layer D
```

Слой отвечает за:

- полное покрытие active aspects ожидаемыми типами требований;
- точные acceptance criteria;
- измеримость NFR;
- стабильные IDs и traceability;
- явное MVP/debt/defer-позиционирование;
- обнаружение дубликатов, конфликтов и перегруженных требований;
- безопасное изменение требований по возврату C2 или D3.

Layer C не:

- меняет canonical aspects Layer B;
- создаёт stories или PRD;
- решает UX/архитектурные детали, отсутствующие в upstream intent;
- публикует частично обработанный requirements set;
- разрешает Layer D обходить C2;
- применяет downstream correction без повторной валидации.

---

## 2. Нормативные решения слоя

### Решение C-D1 — вход только из B8 publish package

C1 и C2 принимают:

- `layer_b_publish_manifest.yaml`;
- `LayerB.snapshot.yaml`;
- `b8_gate_report.yaml` с `PROCEED`;
- `concept_catalog.yaml` с совпадающим hash.

Base map и patches B2–B7 не являются разрешённым runtime input.

### Решение C-D2 — C1 является единственным writer требований

C2, D1, D2 и D3 не редактируют requirements. Они выпускают findings или revision request. C1 создаёт новую версию requirements set.

### Решение C-D3 — четыре файла публикуются как один logical set

`requirements_usr.yaml`, `requirements_ssr.yaml`, `requirements_nfr.yaml` и `requirements_index.yaml` имеют общий `set_id`. Нельзя считать актуальным отдельный файл вне опубликованного set manifest.

### Решение C-D4 — C2 является publish gate

Только решения `APPROVED` и `APPROVED_WITH_WARNINGS` разрешают публикацию. `RETURN_TO_C1`, missing report или stale report блокируют Layer D.

### Решение C-D5 — warnings являются carry-forward obligations

При `APPROVED_WITH_WARNINGS` каждое предупреждение получает ID, affected refs, severity, owner и ожидаемый downstream treatment. Warning не теряется при публикации.

### Решение C-D6 — requirement IDs стабильны

Обычная редактура сохраняет ID. Split создаёт новые IDs, а исходное требование получает `status: superseded` и `superseded_by`. Повторное использование удалённого ID запрещено.

### Решение C-D7 — scope и technical debt не смешиваются

Требование использует:

- `delivery_scope: core | supporting | post_mvp`;
- `debt_disposition: none | technical_debt`.

Legacy `mvp_scope` может экспортироваться как compatibility projection, но не является единственным источником scope.

### Решение C-D8 — D3 escalation всегда возвращается через C2

После изменения C1 по запросу D3 новый set обязан пройти C2. `d3_resume_signal.yaml` может быть опубликован только как часть успешного C publish package и не разрешает прямой bypass.

### Решение C-D9 — structural change вызывает D1/D2 replay

Split, merge, изменение `story_attention_scope`, type или delivery scope требует D1 impact update и D2 validation. Content-only change инвалидирует затронутые detailed stories и их reviews, но может не требовать перестройки всего inventory.

### Решение C-D10 — incremental HITL выполняется через staging/checkpoints

C1 может сохранять ответ после каждого аспекта, но не пишет partial данные в published requirements files. Current package меняется только атомарно после C2.

### Решение C-D11 — каждый requirement leaf имеет source binding

Каждое утверждение, acceptance criterion и metric ссылается на source aspect/decision/risk либо маркируется как derived clarification с rationale. «Свободное» добавление продуктового факта запрещено.

### Решение C-D12 — один canonical validator vocabulary

C2 использует:

- `APPROVED`;
- `APPROVED_WITH_WARNINGS`;
- `RETURN_TO_C1`.

Operational `BLOCK` используется только для missing/stale/invalid input и не подменяет содержательный verdict.

---

## 3. Общий поток исполнения

### 3.1 INITIAL

```text
B8 published package
  ↓ preflight
C1 Requirements Translator [HITL, one aspect at a time]
  → staging requirements set
  → c1_translation_receipts.yaml
  ↓ complete-set barrier
C2 Requirements Validator
  ├─ RETURN_TO_C1 → c2_review_report.yaml + revision request
  ├─ BLOCK        → input/lineage correction
  └─ APPROVED / APPROVED_WITH_WARNINGS
          ↓ atomic publish
      requirements_usr.yaml
      requirements_ssr.yaml
      requirements_nfr.yaml
      requirements_index.yaml
      c2_review_report.yaml
      LayerC.snapshot.yaml
      layer_c_publish_manifest.yaml
          ↓
         D1
```

### 3.2 REVISION from C2

```text
C2 RETURN_TO_C1
  ↓ affected requirement/aspect IDs
C1 Mode B minimal revision
  ↓ new set_id, old IDs retained where semantics retained
C2 revalidation
  ↓
publish or repeat
```

### 3.3 REVISION from D3

```text
D3 pauses affected story
  → d3_c1_escalation.yaml
  ↓
C1 Mode B
  → candidate revised requirements set
  ↓
C2 mandatory validation
  ├─ RETURN → C1
  └─ APPROVE → publish new Layer C package + d3_resume_signal.yaml
                     ↓ impact classification
       ├─ structural → D1 → D2 → D3
       └─ content    → D3 affected stories → D4→D7 closure
```

Старый Layer C package остаётся доступен для аудита, но не может быть смешан с outputs нового cycle.

---

## 4. Роли и ownership

| Агент | Роль | Обязательные входы | Выходы | HITL |
|---|---|---|---|---|
| C1 | Aspect→requirements translation и controlled revision | Layer B package; при revision — C2/D3 request + current C set | staging requirements set, receipts, impact report | Да |
| C2 | Независимая полнота, качество, conflict и traceability validation | полный C1 candidate set + Layer B package | `c2_review_report.yaml` | Нет |
| Runner | checkpoints, set manifest, locks, hashes, atomic publish | outputs C1/C2 | manifests, snapshot, current pointer | Нет |

Writer map:

```text
C1 owns all requirement records and requirements_index content
C2 owns validation findings and verdict
runner owns set/package manifests and current publication
D3 owns escalation request, never requirement content
```

---

## 5. Common envelope и set identity

Каждый artifact использует общий envelope:

```yaml
artifact_meta:
  artifact_type: requirements_usr
  schema_version: c.requirements.v1
  artifact_version: 2
  set_id: CSET-...
  layer: C
  producer: C1
  run_id: run-...
  cycle_id: cycle-...
  status: staging | complete | superseded
  derived_from: []
  content_sha256: "..."
```

Инвариант set:

```text
USR.set_id = SSR.set_id = NFR.set_id = INDEX.set_id
INDEX hashes = фактические hashes трёх файлов
C2.reviewed_set_id = candidate set_id
publish_manifest.set_id = C2.reviewed_set_id
```

Несовпадение любого значения даёт `STALE_INPUT`.

---

## 6. Requirements data model

### 6.1 Base record

```yaml
requirement_id: USR-ASP-CORE-001-R01
type: USR
title: "..."
description: "Система должна ..."
rationale: "..."
status: active
delivery_scope: core
debt_disposition: none
story_attention_scope: user
source_bindings:
  - aspect_id: ASP-CORE-001
    aspect_version: 1
    aspect_sha256: "..."
    source_fields: [goal_brief, mechanism_brief]
acceptance_criteria:
  - criterion_id: AC-01
    statement: "..."
    verification_method: demonstration | test | inspection | measurement
    source_binding: ASP-CORE-001
traceability:
  decision_refs: []
  risk_refs: []
  guardrail_refs: []
supersedes: []
superseded_by: []
```

### 6.2 NFR extension

```yaml
quality_attribute: reliability
metric:
  name: "..."
  unit: percent
  target: 99.0
  measurement_window: 30d
  measurement_method: "..."
  threshold_origin: owner_confirmed | upstream_bound | derived_candidate
```

`derived_candidate` требует подтверждения C1 HITL до публикации, если target влияет на scope/cost/viability.

### 6.3 Deferred record

Post-MVP requirement может создаваться без детального HITL только если содержание является прямой трансляцией аспекта. Он всё равно имеет acceptance intent, source binding и explicit defer reason.

---

## 7. Type projection rules

Нормативная исходная матрица:

| Concept shard | Ожидаемые типы |
|---|---|
| `core_loop` | USR, SSR, NFR |
| `scenarios` | USR, SSR |
| `entities` | SSR, NFR; USR если сущность видима пользователю |
| `architecture` | SSR, NFR |
| `experiments` | SSR, NFR |
| `operations` | SSR, NFR |
| `governance` | SSR, NFR; USR если есть пользовательское consent/control поведение |
| `marketing` | USR, SSR; NFR только при измеримом quality constraint |

Матрица — baseline, а не механическое требование создавать бессодержательный record. Любое исключение фиксируется в `coverage_exceptions` с rationale и проверяется C2.

---

## 8. C1 — INITIAL protocol

### 8.1 Preflight

C1 проверяет:

- B8 verdict `PROCEED`;
- package/hash consistency;
- отсутствие unresolved alias;
- поддерживаемые catalog/schema versions;
- полный expected type metadata;
- отсутствие другого active writer lease.

### 8.2 Per-aspect work unit

Для каждого canonical active aspect C1:

1. читает полный record и связанные decisions/risks;
2. рассчитывает expected requirement types;
3. показывает owner краткий context и candidate split;
4. задаёт один значимый вопрос за раз;
5. фиксирует подтверждённые требования;
6. проверяет acceptance и source bindings;
7. сохраняет checkpoint.

Alias ID не обрабатывается как отдельный аспект, но сохраняется в traceability lookup.

### 8.3 Checkpoint

```yaml
c1_checkpoint:
  session_id: C1-SESSION-...
  catalog_sha256: "..."
  processed_aspect_ids: []
  current_aspect_id: ASP-...
  confirmed_requirement_ids: []
  pending_question: null
  status: in_progress
```

Checkpoint не является входом C2 и никогда не размещается в published package.

### 8.4 Candidate set completion

C1 завершает set только когда:

- каждый active aspect обработан либо имеет valid coverage exception;
- все requirements имеют acceptance criteria;
- все required owner questions закрыты;
- index совпадает с records;
- self-audit пройден.

---

## 9. `requirements_index.yaml`

Index является полным навигационным и coverage-контрактом:

```yaml
requirements_index:
  set_id: CSET-...
  source_catalog_ref:
    catalog_id: BCAT-...
    sha256: "..."
  by_requirement_id: {}
  by_aspect_id:
    ASP-CORE-001:
      expected_types: [USR, SSR, NFR]
      active_requirement_ids: []
      coverage_status: complete
  aliases: {}
  coverage_exceptions: []
  warnings_carried_forward: []
  file_refs:
    usr: {path: requirements_usr.yaml, sha256: "..."}
    ssr: {path: requirements_ssr.yaml, sha256: "..."}
    nfr: {path: requirements_nfr.yaml, sha256: "..."}
```

Index не дублирует полный текст requirement. Он содержит locator, status, type, source aspect, scope и hash record/file.

---

## 10. C2 validation contract

### 10.1 Structural checks

- четыре candidate files существуют;
- set IDs и hashes согласованы;
- IDs уникальны и соответствуют type;
- active/superseded relations валидны;
- index не содержит orphan/missing records;
- все source aspect IDs разрешаются через canonical catalog.

### 10.2 Coverage checks

- каждый active aspect имеет ожидаемые types или justified exception;
- governance aspect имеет enforcement requirement;
- experiment aspect имеет metric/decision requirement;
- accepted/minimized risks отражены там, где создают obligation;
- post-MVP records не закрывают MVP coverage формально.

### 10.3 Quality checks

- description атомарна и однозначна;
- acceptance проверяема;
- NFR metric имеет unit, target, window и method;
- нет hidden design solution без upstream основания;
- нет дубликатов, конфликтов и чрезмерной перегрузки;
- `story_attention_scope` согласован с type/поведением;
- delivery scope и debt disposition не конфликтуют с B.

### 10.4 Verdict rules

`APPROVED`:

- нет critical/significant findings;
- нет предупреждений, требующих downstream action.

`APPROVED_WITH_WARNINGS`:

- нет blocking finding;
- каждое warning имеет owner и carry-forward treatment;
- warning не означает незавершённое требование.

`RETURN_TO_C1`:

- отсутствует coverage;
- acceptance/metric непроверяемы;
- есть конфликт, duplicate overload или unsupported inference;
- нарушены traceability/scope/governance rules.

Operational `BLOCK`:

- вход отсутствует, partial, stale или schema-invalid.

---

## 11. C1 Mode B — controlled revisions

Mode B получает точный request:

```yaml
revision_request:
  request_id: C-REV-...
  source: C2 | D3
  reviewed_set_id: CSET-...
  issue_type: traceability | structure | content | coverage | conflict | governance | experiment | d3_conflict
  affected_requirement_ids: []
  affected_aspect_ids: []
  requested_outcome: "..."
  evidence_refs: []
```

Правила Mode B:

- неизменённые records копируются byte-equivalent либо с явно вычисленным envelope update;
- semantic edit сохраняет ID;
- split создаёт новые IDs и supersession graph;
- merge требований требует сохранения aliases/supersedes;
- изменение source concept невозможно: формируется return в B;
- C1 выпускает `change_impact_report.yaml`.

```yaml
change_impact:
  classification: content_only | acceptance_only | structural | scope | source_conflict
  changed_requirement_ids: []
  added_requirement_ids: []
  superseded_requirement_ids: []
  affected_story_ids: []
  required_d_replay_from: D1 | D3 | null
```

---

## 12. Publish package и handoff в D

```text
published/layer-c/<package_id>/
├── requirements_usr.yaml
├── requirements_ssr.yaml
├── requirements_nfr.yaml
├── requirements_index.yaml
├── c2_review_report.yaml
├── LayerC.snapshot.yaml
├── layer_c_publish_manifest.yaml
└── d3_resume_signal.yaml          # только revision from D3
```

`LayerC.snapshot.yaml`:

```yaml
layer_c_snapshot:
  package_id: C-...
  set_id: CSET-...
  source_layer_b_package_id: B-...
  gate:
    verdict: APPROVED | APPROVED_WITH_WARNINGS
    report_sha256: "..."
  requirement_counts:
    USR: 0
    SSR: 0
    NFR: 0
  active_count: 0
  warnings: []
  handoff:
    target: D1
    authorized: true
```

D1 не запускается при отсутствии любого обязательного файла, при mismatch hash/set или `RETURN_TO_C1`.

---

## 13. Downstream resume semantics

`d3_resume_signal.yaml` содержит не команду «продолжай немедленно», а подтверждённый route:

```yaml
d3_resume_signal:
  source_escalation_id: D3-C1-...
  new_layer_c_package_id: C-...
  c2_verdict: APPROVED
  impact_classification: structural
  resume_after:
    - D1
    - D2
  affected_story_ids: []
  invalidated_review_types: [D4, D5, D6, D7]
```

Оркестратор проверяет выполненный `resume_after` barrier. D3 не может самостоятельно объявить upstream closure завершённым.

---

## 14. Revision matrix

| Изменение | Обязательный replay |
|---|---|
| Acceptance wording без смены смысла | C1 → C2 → affected D3 → D4→D7 |
| Requirement description semantics | C1 → C2 → affected D3 → D4→D7 |
| Split/merge/type change | C1 → C2 → D1 → D2 → D3→D7 |
| Delivery scope/story attention change | C1 → C2 → D1 → D2 → D3→D7 |
| Source aspect conflict | Layer B revision → C1 → C2 → D1→D7 |
| C2-only warning metadata | C2 → republish → D carry-forward, если content hashes прежние |

Любой replay использует новый cycle и не переписывает предыдущий package.

---

## 15. State, concurrency и recovery

- Один active C1 session на project/catalog version.
- Owner answers пишутся в append-only receipt log.
- Candidate set создаётся в staging directory.
- C2 работает по immutable candidate set hash.
- Изменение candidate после начала C2 делает review stale.
- Publish использует compare-and-swap current package version.
- Повторный request с тем же idempotency key не создаёт дубликаты IDs.
- Recovery продолжает HITL с последнего committed aspect checkpoint.

---

## 16. Инварианты слоя

1. Каждый active requirement связан хотя бы с одним canonical aspect.
2. Каждый active aspect покрыт expected types либо valid exception.
3. Requirement ID никогда не переназначается другой семантике.
4. Supersession graph ацикличен.
5. Published requirements set всегда полный и согласованный.
6. C2 reviewed hash равен published hash.
7. D не получает package со статусом `RETURN_TO_C1`.
8. D3 escalation не обходит C2.
9. Technical debt сохраняется отдельной осью.
10. Warning имеет явный downstream treatment.
11. NFR target измерим и имеет provenance.
12. Downstream не редактирует requirements.

---

## 17. Обязательные изменения промптов

### C1

- заменить base+patch reconstruction на B publish package;
- ввести common envelope, set ID и staging checkpoints;
- исправить mapping `technical_debt`;
- формализовать immutable IDs, split/supersession;
- добавить full source binding;
- после D3 escalation публиковать только после C2;
- добавить `change_impact_report`.

### C2

- требовать B gate/package и полный candidate set manifest;
- проверять hashes/set identity;
- различать operational `BLOCK` и semantic verdict;
- формализовать carry-forward warnings;
- выпускать точный revision route;
- валидировать debt/scope, aliases и supersession.

### D1/D2/D3 boundary

- сделать C2 approval обязательным;
- запретить продолжение с warning об отсутствующем C2;
- после C revision соблюдать impact-driven replay;
- связывать inventories/stories с `layer_c_package_id`.

---

## 18. Валидация и тесты

### Schema и set tests

- mismatch set IDs блокируется;
- missing one of four files блокируется;
- duplicate requirement ID блокируется;
- invalid supersession/alias cycle блокируется;
- NFR без unit/window/method возвращается C1.

### Coverage tests

- active governance aspect без enforcement SSR/NFR блокирует;
- experiment без metric блокирует;
- post-MVP record не засчитывается для core aspect;
- justified coverage exception проходит и виден D.

### Revision tests

- content edit сохраняет ID;
- split создаёт IDs и D1 replay route;
- D3 escalation всегда проходит C2;
- stale C2 report не публикуется;
- crash после третьего аспекта возобновляется без повторного owner answer.

### Handoff tests

- D1 отвергает C package без manifest;
- D1 отвергает APPROVED report с неверным requirements hash;
- warnings доступны в D snapshot context;
- Layer B alias корректно виден через requirement source binding.

---

## 19. Порядок реализации

1. Утвердить requirement schemas и common envelope.
2. Реализовать Layer B package preflight.
3. Ввести set staging/checkpoint в C1.
4. Обновить ID/split/debt/source-binding rules.
5. Расширить C2 set, semantic и lineage validation.
6. Реализовать atomic Layer C publish package.
7. Исправить D1/D3 boundary и resume protocol.
8. Добавить revision/failure/lineage tests.

---

## 20. Definition of Done

Layer C готов, когда:

- C1 работает только от B8-published canonical catalog;
- requirements создаются как единый versioned set;
- каждый record атомарен, проверяем и трассируем;
- C2 является обязательным gate для initial и revision;
- partial HITL state никогда не виден Layer D;
- IDs и supersession сохраняют историю;
- D3 escalation проходит полный validation/replay route;
- `APPROVED_WITH_WARNINGS` переносит явные obligations;
- публикация атомарна, воспроизводима и hash-linked;
- prompts, schemas, runner и тесты согласованы с планом.
