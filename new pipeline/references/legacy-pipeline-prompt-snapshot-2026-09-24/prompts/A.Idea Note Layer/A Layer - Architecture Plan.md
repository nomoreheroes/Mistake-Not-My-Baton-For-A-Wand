# A Layer — Architecture Plan

**Слой:** A — Idea Note  
**Дата:** 2026-08-24  
**Ревизия:** R1  
**Статус:** ACTIVE BASELINE / PROMPT ALIGNMENT REQUIRED

**Основание:** существующие промпты A1 v7, A2 v5, A3 v5, A4 v4, A5 v4 и A6 v1.3, а также входной контракт B1.

**Назначение документа:** зафиксировать целевую архитектуру исполнения Layer A, не переписывая сами промпты. Раздел 14 перечисляет изменения, необходимые для полного соответствия промптов этому плану.

---

## 1. Назначение и границы слоя

Layer A превращает исходное намерение владельца продукта в проверенный, версионированный и пригодный для передачи в Concept Layer пакет:

```text
намерение владельца
        ↓
подтверждённый vision
        ↓
структурированный idea note
        ↓
market + feasibility + ethics reviews
        ↓
бинарный gate
        ↓
immutable handoff в B1
```

Слой отвечает на пять вопросов:

1. Какую проблему и для кого решает продукт?
2. Где проходит граница MVP и как будет проверена его ценность?
3. Достаточно ли идея сформулирована для маркетинговой, технической и этической проверки?
4. Есть ли блокирующие противоречия или риски до детализации Concept Layer?
5. Как передать в Layer B все подтверждённые решения, гипотезы, рекомендации и открытые вопросы без потерь?

Layer A не является:

- рыночным исследованием и не доказывает наличие рынка внешними данными;
- архитектурным проектированием системы;
- юридическим заключением;
- PRD, backlog или набором user stories;
- механизмом автоматического принятия продуктовых решений вместо владельца.

Оценки A3–A5 означают качество и внутреннюю согласованность гипотез на стадии Idea Note. Они не являются доказательством product-market fit, технической готовности production-системы или нормативного соответствия.

---

## 2. Нормативные решения слоя

### Решение A-D1 — шесть агентов, внешний оркестратор

Ростер A1–A6 сохраняется. Новый продуктовый агент не требуется. Порядком запуска, checkpoint, replay и атомарной публикацией управляет внешний human-run orchestrator или runner.

### Решение A-D2 — два контура исполнения

Слой имеет два явных контура:

- `INITIAL` — первичное формирование полного пакета;
- `REVISION` — минимальный replay от самого раннего затронутого владельца данных.

Revision никогда не означает безусловный полный перезапуск слоя.

### Решение A-D3 — владелец данных определяет точку возврата

Каждый артефакт имеет единственного writer. Downstream-агент не исправляет upstream-артефакт самостоятельно, а формирует routing request.

### Решение A-D4 — review-порядок последовательный

Канонический порядок A3 → A4 → A5 сохраняется:

- A4 обязан получить `marketing_review.yaml` и оценить технический эффект marketing suggestions;
- A5 запускается после A4 и получает оба предшествующих review как контекст;
- A5 не наследует их решения, а использует только как дополнительные сигналы риска.

### Решение A-D5 — `revise` не совместим с публикацией

`recommendation: revise` означает незавершённый обязательный replay. A6 не может выдать `PROCEED`, пока любой актуальный review имеет `revise` или `block`.

Неблокирующие советы должны находиться в recommendations/open items при итоговом `recommendation: proceed`, а не маскироваться значением `revise`.

### Решение A-D6 — бинарный gate и handoff authorization разделены

`final_gate_decision.status` остаётся строго бинарным:

- `PROCEED` — автоматические условия Layer A пройдены;
- `BLOCK` — требуется revision или операторское вмешательство.

Отдельное поле `handoff_authorization.status` отражает подтверждение владельца:

- `pending_owner_confirmation`;
- `confirmed`.

Это устраняет конфликт между бинарным A6, frozen snapshot и обязательной HITL-проверкой в B1.

### Решение A-D7 — B1 принимает пару артефактов

Layer B стартует только при одновременном наличии:

- `final_gate_decision.yaml` со статусом `PROCEED`;
- `IdeaNoteLayer.snapshot.yaml`, hash которого указан в gate decision.

Один snapshot без gate decision и один gate decision без snapshot недействительны.

### Решение A-D8 — полная трассируемость важнее «последнего файла»

Runner не ищет произвольный `latest`. Каждый запуск использует явные `run_id`, `cycle_id`, версии и hashes входов. Старые версии не перезаписываются.

### Решение A-D9 — snapshot является проекцией, а не новым источником решений

A6 может переносить, классифицировать и связывать данные, но не создавать новые продуктовые факты. Каждый leaf snapshot должен иметь source path или быть явно помечен как вычисленное gate-значение.

### Решение A-D10 — внешние знания ограничены ролью агента

- A1 может приводить реальные продуктовые паттерны только как неподтверждённые варианты для владельца.
- A2 и A3 не используют внешние данные.
- A4 использует общие технические знания только для оценки реализуемости.
- A5 классифицирует риски без конкретных правовых утверждений.
- Любой предложенный A1 факт становится продуктовым решением только после явного подтверждения владельца.

---

## 3. Общий поток исполнения

### 3.1 INITIAL

```text
Owner
  ↓ интерактивное интервью, один вопрос за раз
A1 Vision Interview Agent
  → vision.yaml
  ↓ schema + completeness preflight
A2 Idea Note Generator
  → idea_note.yaml
  ↓
A3 Marketing Reviewer
  → marketing_review.yaml
  ↓ functional_impact_suggestions
A4 Architecture Feasibility Reviewer
  → architecture_review.yaml
  ↓ дополнительный risk context
A5 Ethics & Regulatory Reviewer
  → ethics_review.yaml
  ↓ barrier: все три review опубликованы и относятся к одной версии Idea Note
A6 Binary Gatekeeper
  ├─ BLOCK   → final_gate_decision.yaml + interview_brief/replay route
  └─ PROCEED → final_gate_decision.yaml + IdeaNoteLayer.snapshot.yaml
                                        ↓
                                       B1
```

### 3.2 REVISION

```text
A6 BLOCK
  ↓ canonical revision_route.restart_from
  ├─ A1: owner patch interview
  │      → vision.yaml + vision_patch.yaml + revision_advocate_summary.yaml
  │      → A2 RECOMPILE/PATCH
  │
  ├─ A2: controlled Idea Note recompile
  │      → idea_note.yaml + revision_context.yaml
  │
  ├─ A3: marketing review replay
  ├─ A4: feasibility review replay
  └─ A5: ethics review replay

После самой ранней точки возврата повторяется весь downstream closure до A6.
```

Нормативный downstream closure:

| `restart_from` | Обязательный replay |
|---|---|
| A1 | A1 → A2 → A3 → A4 → A5 → A6 |
| A2 | A2 → A3 → A4 → A5 → A6 |
| A3 | A3 → A4 → A5 → A6 |
| A4 | A4 → A5 → A6 |
| A5 | A5 → A6 |

Пропуск downstream-агента запрещён: его старый output относится к другой комбинации upstream-версий.

### 3.3 Barrier rules

A6 запускается только если:

1. Все пять входных артефактов существуют.
2. Их schema versions поддерживаются.
3. `derived_from` образует одну непрерывную lineage-цепочку.
4. A3, A4 и A5 относятся к одной текущей версии `idea_note.yaml`.
5. A4 относится к текущей версии `marketing_review.yaml`.
6. A5 содержит ссылки на фактически использованные версии Vision, Idea Note и optional reviews.
7. Ни один вход не имеет статуса partial/in_progress.

---

## 4. Ростер агентов и владение артефактами

| Агент | Роль | Обязательные входы | Выходы | HITL |
|---|---|---|---|---|
| A1 | Vision interview, owner alignment, revision advocacy | ответы owner; в revision — A6 BLOCK + текущие Vision/Idea Note | `vision.yaml`; в revision также `vision_patch.yaml`, `revision_advocate_summary.yaml` | Да |
| A2 | Детерминированная трансформация Vision → Idea Note | `vision.yaml`; в revision — previous Idea Note + patch/recompile request | `idea_note.yaml`; в revision — `revision_context.yaml` | Нет |
| A3 | Market-hypothesis quality review | текущий Idea Note; в revision — previous review + context | `marketing_review.yaml` | Нет |
| A4 | Technical feasibility and automation review | текущие Idea Note + Marketing Review; в revision — previous review + context | `architecture_review.yaml` | Нет |
| A5 | Ethics, misuse and regulatory-sensitivity review | текущие Vision + Idea Note; текущие reviews как context | `ethics_review.yaml` | Нет |
| A6 | Gate, conflict detection, routing, snapshot publication | Vision, Idea Note, три reviews | `final_gate_decision.yaml`; при PROCEED — snapshot | Нет; формирует требования к HITL |

Writer ownership:

```text
A1 owns vision*
A2 owns idea_note + revision_context
A3 owns marketing_review
A4 owns architecture_review
A5 owns ethics_review
A6 owns gate decision + layer snapshot
runner owns run state, manifests, hashes and atomic publication
```

Ни один агент не изменяет физический файл другого агента.

### 4.1 Статус существующих промптов

| Агент | Файл | Текущий статус относительно плана |
|---|---|---|
| A1 | `A1.Vision Interview Agent.md` | Базовая логика готова; нужны schema repair, patch IDs и resume contract |
| A2 | `A2.Idea Note Generator.md` | Базовая трансформация готова; нужны точные target paths и RECOMPILE mode |
| A3 | `A3.Marketing Reviewer v2.md` | Scoring готов; нужны полный artifact schema, stable IDs и impact registry |
| A4 | `A4.Architecture Feasibility Reviewer.md` | Scoring готов; нужны полный artifact schema, gap IDs и dependency-aware revision |
| A5 | `A5.Ethics & Regulatory Reviewer.md` | Risk model готов; нужны полный artifact schema, guardrail adequacy contract и dependency-aware revision |
| A6 | `A6.Binary Gatekeeper.md` | Gate skeleton готов; нужны полная fact resolution, revise policy, lossless snapshot и atomic handoff |

Ни один статус «нужны изменения» не означает, что существующий prompt непригоден для ручного запуска. Он означает, что соответствующее поведение пока не формализовано как воспроизводимый межагентный контракт.

---

## 5. Control plane и lifecycle артефактов

### 5.1 `a_layer_run.yaml`

Runner поддерживает единое состояние запуска:

```yaml
schema_version: "1.0"
run_id: A-{timestamp}-{nonce}
status: interviewing/compiling/reviewing/gating/blocked/published/escalated
current_cycle_id: AC-{seq}
mode: INITIAL/REVISION
started_at:
updated_at:

current_artifacts:
  vision_ref:
  idea_note_ref:
  marketing_review_ref:
  architecture_review_ref:
  ethics_review_ref:
  gate_decision_ref:
  snapshot_ref:

revision:
  restart_from: A1/A2/A3/A4/A5/null
  trigger_ref:
  attempt: 0
  max_attempts: 5

checkpoints:
  - stage:
    status: pending/running/completed/failed/invalidated
    input_manifest_sha256:
    output_manifest_sha256:
```

`max_attempts` ограничивает оркестрационный loop, но не снижает quality gate. После исчерпания лимита `a_layer_run.status: escalated`, а последнее решение A6 остаётся `BLOCK`.

### 5.2 Common artifact envelope

Каждый YAML-артефакт Layer A обязан иметь:

```yaml
artifact_meta:
  schema_version: "1.0"
  artifact_type:
  artifact_id:
  version:
  run_id:
  cycle_id:
  mode: INITIAL/REVISION
  created_at:
  produced_by: A1/A2/A3/A4/A5/A6
  derived_from:
    - artifact_id:
      version:
      sha256:
```

`content_sha256` хранится в stage manifest, чтобы hash не был самореферентным.

Legacy-артефакт без `artifact_meta.version` может быть прочитан A6 только в compatibility mode и получает warning. Он не может стать frozen handoff без нормализации runner'ом и записи provenance.

### 5.3 Lifecycle

```text
draft → validated → current → consumed
                    ↓ revision
                 superseded

current + A6 PROCEED → frozen in published manifest
```

Правила:

- публикация нового current-артефакта атомарно supersede предыдущий;
- downstream никогда не читает draft;
- output stage считается завершённым только после schema validation и manifest commit;
- повторный запуск с тем же input manifest обязан быть idempotent или создать явно связанную новую версию;
- ручное редактирование current-артефакта после публикации инвалидирует все downstream outputs по hash mismatch.

---

## 6. Карта артефактов

### 6.1 Основные артефакты

| Артефакт | Writer | Когда обязателен | Основные consumers |
|---|---|---|---|
| `vision.yaml` | A1 | всегда | A2, A5, A6 |
| `vision_patch.yaml` | A1 | revision с изменением Vision | A2, audit trail |
| `revision_advocate_summary.yaml` | A1 | A1 revision | A6/operator |
| `idea_note.yaml` | A2 | всегда | A3, A4, A5, A6 |
| `revision_context.yaml` | A2 | любой revision после A2 | A3, A4, A5, A6 |
| `marketing_review.yaml` | A3 | всегда | A4, A5, A6 |
| `architecture_review.yaml` | A4 | всегда | A5, A6 |
| `ethics_review.yaml` | A5 | всегда | A6 |
| `final_gate_decision.yaml` | A6 | каждый gate attempt | A1/runner/B1 |
| `IdeaNoteLayer.snapshot.yaml` | A6 | только PROCEED | B1 |

### 6.2 Control artifacts

| Артефакт | Назначение |
|---|---|
| `a_layer_run.yaml` | state machine запуска |
| `stage_input_manifest.yaml` | exact hashes входов stage |
| `stage_output_manifest.yaml` | exact hashes валидированных выходов |
| `revision_request.yaml` | нормализованный route из A6 |
| `a1_interview_state.yaml` | checkpoint интерактивного A1 |
| `publish_manifest.yaml` | атомарная пара gate + snapshot для B1 |

### 6.3 Logical names vs physical files

Промпты используют логические имена (`vision.yaml`, `idea_note.yaml`). Физическое имя не должно кодировать смысл только через `v5` или слово `latest`; конкретная версия разрешается через manifest.

---

## 7. Контракты агентов

### 7.1 A1 — Vision Interview Agent

#### INITIAL

A1 проводит нелинейное интервью с обязательными правилами:

- один атомарный вопрос за раз;
- summary и явное подтверждение в конце каждой фазовой зоны;
- возврат к зоне при противоречии;
- не менее трёх сценариев и трёх доменных сущностей;
- явные MVP exclusions, success signal и четыре категории risk map;
- финальный Vision публикуется только после owner confirmation.

#### REVISION

A1 получает нормализованный список blocker'ов A6, сортирует по severity/priority и обрабатывает не более семи owner-вопросов за один interview pass.

Каждый patch item обязан содержать:

```yaml
patch_item_id:
linked_issue_id:
operation: add/modify/delete
target_field_path:
before:
after:
user_confirmed: true
advocate_suggestion_used: true/false
```

Patch с `user_confirmed: false` не применяется.

#### Resume semantics

После каждого подтверждённого ответа runner сохраняет:

```yaml
a1_interview_state:
  run_id:
  cycle_id:
  mode:
  current_zone:
  current_question_id:
  pending_patch: null
  confirmed_patch_item_ids: []
  remaining_question_ids: []
  owner_confirmation_events: []
```

После crash A1 продолжает с первого неподтверждённого вопроса и не повторно применяет подтверждённые patch items.

#### Обязательная коррекция Vision schema

Текущая схема A1 содержит top-level `mvp_core`, но A2 ожидает `vision.mvp_concept.*` для четырёх формальных контрактов. Каноническая схема должна включать:

```yaml
mvp_concept:
  state_machine_contract: null
  event_taxonomy_contract: null
  metrics_baseline_definition: null
  schedule_state_contract: null
```

Top-level `mvp_core`, `mvp_excluded`, `mvp_success_signal` сохраняются для совместимости существующего mapping.

### 7.2 A2 — Idea Note Generator

A2 выполняет controlled transformation, а не свободный продуктовый синтез.

Инварианты:

- обязательный Vision → Idea Note mapping применяется без изменения смысла;
- новые domain entities запрещены;
- `data_created` является подмножеством `domain_entities`;
- derived fields имеют evidence/source paths;
- roadmap имеет exit criteria и не выходит за post-MVP directions;
- kill criterion связан с initial success metric;
- значимые unmapped Vision fields попадают в coverage warnings.

#### Три execution mode A2

Существующие два режима дополняются третьим, иначе routing `A6 → A2` неисполняем.

```text
INITIAL    — полная сборка из первого Vision
PATCH      — изменение полей, затронутых owner-confirmed vision_patch
RECOMPILE  — исправление только derived Idea Note fields по A6 revision_request
```

`RECOMPILE` не меняет прямые mapped fields и не требует фиктивного Vision patch. Разрешённые цели:

- `value_mechanism.optional_alternative`;
- `value_vector.*`;
- `market_hypothesis`;
- `distribution_hypothesis`;
- `monetization_hypothesis`;
- `primary_interactions`;
- `initial_roadmap_outline` в пределах Vision;
- `assumption_map` в пределах подтверждённых фактов;
- `kill_criteria`;
- coverage warnings и open questions.

Если требуемое изменение затрагивает segment, platform, entity, scenario или MVP scope, A2 обязан вернуть route в A1.

#### `revision_context.yaml`

Context является change manifest, а не пересказом:

- перечисляет все changed leaf paths с before/after;
- перечисляет frozen top-level blocks;
- различает `change_origin: vision_patch/a2_recompile`;
- содержит `affected_review_dimensions`, вычисленные по impact matrix из §8;
- ссылается на A6 blocker/revision request.

### 7.3 A3 — Marketing Reviewer

A3 оценивает четыре области:

1. Segment quality.
2. Value proposition.
3. MVP as a market object.
4. Market model.

Затем формирует gaps, ICP hypothesis, positioning draft, acquisition hypotheses, максимум пять assumption-linked experiments и functional impact suggestions.

Ограничения:

- не менять исходный segment;
- не добавлять entities или scope;
- не использовать внешние market facts;
- не выдавать hypothesis за evidence;
- experiment без `assumption_id` получает blocking output validation error до публикации review.

`overall_market_viability_score` остаётся средним пяти ключевых scores. Final recommendation рассчитывается только по anchor rules промпта.

### 7.4 A4 — Architecture Feasibility Reviewer

A4 не проектирует архитектуру. Он оценивает:

- coherence доменной модели;
- hidden entity risk;
- пригодность требований для AI-assisted implementation;
- ambiguity, state management, dependencies и testability;
- HITL intensity и конкретные triggers;
- scalability/rewrite risk;
- technical impact предложений A3.

`overall_technical_feasibility_score` вычисляется по формуле текущего промпта с penalty за gaps.

High HITL допустим только если:

- все triggers структурированы;
- у каждого trigger есть affected scenario и expected frequency;
- нет critical gaps;
- ключевые scores соответствуют proceed rules;
- A6 переносит notice в snapshot.

### 7.5 A5 — Ethics & Regulatory Reviewer

A5 обязан покрыть:

- structured hard flags;
- data sensitivity, minimization, transparency и prompt leakage;
- manipulation/addiction/delegated authority drift;
- fairness/exclusion;
- 3–5 misuse scenarios;
- geography-sensitive regulatory exposure без конкретных legal claims;
- traceable guardrails;
- safety questions для `unclear` flags;
- residual risk scan;
- полный risk coverage checklist.

Каждый medium/high misuse scenario и каждый `potential` Stage-0 flag обязан иметь guardrail. Любой `detected: true` residual risk обязан быть добавлен в основной review до публикации.

### 7.6 A6 — Binary Gatekeeper

A6 выполняет только пять функций:

1. Input/lineage validation.
2. Нормализацию gate facts.
3. Cross-review conflict detection.
4. Бинарное решение и routing.
5. Lossless snapshot projection при PROCEED.

A6 запрещено:

- менять scores;
- устранять cross-review conflict собственной интерпретацией;
- создавать новый guardrail, product fact или assumption;
- считать отсутствующее критическое поле нейтральным;
- публиковать snapshot при BLOCK.

---

## 8. Revision impact model

Текущие review-промпты требуют переносить frozen scores, но не задают детерминированную связь changed field → affected score. Runner и reviewers используют общий registry.

### 8.1 A3 impact matrix

| Changed Idea Note area | Минимально пересматриваемые области |
|---|---|
| `problem_statement` | pain intensity, urgency, value clarity |
| `target_segment_definition` | segment clarity/focus, ICP alignment, distribution realism |
| `value_mechanism`, `value_vector` | value clarity, differentiation, urgency, monetization alignment |
| `core_use_case_cluster` | pain evidence, MVP sellability, standalone value |
| `mvp_concept.*` | sellability, standalone value, complexity/value balance |
| `market_hypothesis` | market logic, ICP |
| `distribution_hypothesis` | traction plausibility, distribution realism, acquisition hypotheses |
| `monetization_hypothesis` | pay signal, market logic, monetization alignment |
| `assumption_map` | experiments backlog and linkage audit |
| `initial_roadmap_outline`, `kill_criteria` | MVP/experiment consistency only |

### 8.2 A4 impact matrix

| Changed area | Минимально пересматриваемые области |
|---|---|
| domain entities/data/scenarios | entity coherence, hidden entity risk, MVP alignment |
| `mvp_contracts.state_machine_contract` | ambiguity, state management, testability, HITL |
| event/baseline/schedule contracts | automation stability, testability, observability gaps, HITL |
| target platform/primary interactions | external dependencies, integration gaps, testability |
| MVP scope | все model integrity + automation dimensions |
| roadmap/post-MVP-related fields | scalability and rewrite risk |
| A3 functional suggestions | technical impact block; affected core score только при доказанной связи |

### 8.3 A5 impact matrix

| Changed area | Минимально пересматриваемые области |
|---|---|
| entities/data created/informational trace | privacy, minimization, prompt leakage, misuse |
| geography/users | regulatory exposure, exclusion, safety questions |
| value mechanism/interactions | transparency, manipulation, delegated authority drift |
| MVP automation/contracts | consent, authority drift, misuse, AI automation risk |
| segment/scenarios | fairness, exclusion, misuse actors |
| telemetry/metrics assumptions | minimization, temporal and organizational risks |

### 8.4 Frozen score rule

Score переносится только если:

- ни один его source path не изменился;
- ни одна его dependency dimension не изменилась;
- upstream review input, от которого он зависит, не изменился;
- previous score был рассчитан по той же schema/anchor version.

Иначе score обязан быть reassessed. Upgrade prompt/anchor version инвалидирует все scores соответствующего reviewer.

---

## 9. Routing и replay

### 9.1 Нормализованный revision request

A6 публикует:

```yaml
revision_request:
  request_id:
  source_gate_decision_id:
  revision_kind: product_content/a2_derivation/review_recompute/prompt_or_schema_defect
  restart_from: A1/A2/A3/A4/A5
  blockers:
    - blocker_id:
      source_agent:
      severity: critical/significant
      affected_fields: []
      required_resolution:
      acceptance_evidence:
  owner_interview_required: true/false
  downstream_replay: []
```

### 9.2 Routing rules

| Причина | `restart_from` | Owner interview |
|---|---|---|
| проблема, segment, scenario, entity, platform, MVP scope, owner fact | A1 | Да |
| derived Idea Note field при неизменном Vision | A2 | Нет |
| некорректный marketing analysis при валидном Idea Note | A3 | Нет |
| feasibility analysis или tech impact | A4 | Нет |
| ethics coverage/guardrail analysis при достаточных source facts | A5 | Нет |
| schema mismatch или невозможный path | соответствующий prompt owner; `revision_kind: prompt_or_schema_defect` | Нет; operator escalation |

Если review просит изменить product content, route всегда идёт к владельцу этого content, а не к самому reviewer.

### 9.3 Conflict routing

| Cross-review conflict | Канонический route |
|---|---|
| ICP противоречит segment, но segment однозначен | A3 |
| ICP выявил реальную неоднозначность segment | A1 |
| positioning противоречит value mechanism | A3 или A2 по ownership затронутого поля |
| functional suggestion снижает automation stability | A3 |
| guardrail требует изменить MVP | A1; владелец выбирает scope/guardrail direction |
| A5 требует implementation detail, отсутствующий на Idea Note stage | сохранить open item для B, если A5 может дать proceed; иначе A1/A2 только при недостающем продуктовом решении |

### 9.4 No-progress detection

Если два последовательных gate cycles возвращают одинаковый blocker fingerprint при неизменных relevant field hashes, runner не повторяет тот же replay автоматически. Run получает `status: escalated` с последним A6 `BLOCK`.

---

## 10. Gate contract A6

### 10.1 Нормализованные gate facts

A6 обязан разрешить и записать source path для:

- всех трёх `final_assessment.recommendation`;
- overall score каждого review;
- `automation_stability_score`;
- `hitl_intensity_forecast` и `primary_hitl_triggers`;
- `architecture_gaps` с severity;
- `regulatory_exposure_level`;
- Stage-0 confirmed/potential flags;
- adequacy/traceability guardrails;
- unresolved safety questions;
- self-audit pass/fail каждого review.

Критический gate fact без значения является BLOCK, а не graceful non-blocking fallback.

### 10.2 BLOCK conditions

A6 выдаёт BLOCK, если выполняется хотя бы одно условие:

1. Отсутствует обязательный вход или lineage не согласована.
2. Schema validation любого входа не пройдена.
3. Любой review дал `block` или `revise`.
4. `automation_stability_score < 6`.
5. High HITL не имеет полного списка triggers.
6. Есть хотя бы один critical architecture gap.
7. High regulatory exposure не покрыт достаточными traceable guardrails.
8. Есть confirmed Stage-0 flag.
9. Cross-review check дал conflict.
10. Критический gate fact unresolved.
11. Обязательный reviewer self-audit имеет false в поле, влияющем на полноту или scope integrity.
12. Snapshot preflight показывает невозможность lossless projection.

### 10.3 PROCEED conditions

PROCEED допустим только если:

- отсутствуют все BLOCK conditions;
- все review recommendations равны `proceed`;
- significant/minor gaps явно перенесены в open items;
- recommendations не превращены в requirements;
- A6 построил snapshot и прошёл completeness check;
- gate decision и snapshot подготовлены к одной атомарной публикации.

### 10.4 High HITL

High HITL с документированными triggers не является самостоятельным блокером, если A4 дал `proceed` по собственным правилам. A6 переносит:

- notice;
- каждый trigger;
- owner confirmation requirement;
- affected scenarios;
- intervention frequency.

### 10.5 Gate output

BLOCK output обязан содержать artifact envelope, blockers, conflicts, normalized revision route, максимум семь атомарных owner questions и no-progress fingerprint.

PROCEED output обязан содержать:

```yaml
final_gate_decision:
  layer: IdeaNote
  status: PROCEED
  snapshot_ref:
    artifact_id:
    version:
    sha256:
  handoff_authorization:
    status: pending_owner_confirmation/confirmed
    required_actions: []
  next_step:
    agent: B1
```

---

## 11. Snapshot и handoff в Layer B

### 11.1 Snapshot sections

`IdeaNoteLayer.snapshot.yaml` содержит:

1. Common artifact envelope и exact source refs.
2. `frozen_core`.
3. Полный `domain_model`.
4. `mvp_bounds` и формальные contracts.
5. `initial_roadmap_outline`.
6. Полный `assumption_map`.
7. Полный `risk_map`.
8. `reviews_digest` со статусом `RECOMMENDATION_ONLY`.
9. `cross_review_resolution_notes`.
10. `open_items_for_layer_b`.
11. `layer_readiness_certificate`.
12. `source_coverage_manifest`.

### 11.2 Frozen core

Минимальный frozen core текущего A6 расширяется, чтобы не потерять подтверждённый Vision:

```yaml
frozen_core:
  project_name:
  one_sentence_summary:
  problem_statement:
  problem_context_example:
  target_segment_definition:
  primary_user:
  paying_user:
  excluded_users:
  geography:
  target_platform:
  value_hypothesis:
  differentiation_hypothesis:
  switch_trigger:
  value_mechanism_primary:
  value_vector:
  market_hypothesis:
  distribution_hypothesis:
  monetization_hypothesis:
  mvp_core:
  measurable_signal:
  success_metrics_initial:
  kill_criteria:
```

Поле может быть `null`, если null был явным и допустимым решением. Оно не может быть молча пропущено.

### 11.3 Domain and assumptions completeness

Snapshot сохраняет все leaf fields сценариев, включая `current_alternative` и `informational_trace`. Assumption переносится вместе с `description`, `test_method`, status и `challenged_by`; перенос только ID и risk level недостаточен.

### 11.4 Recommendations vs invariants

```text
frozen_core/domain/mvp bounds = locked Layer A decisions
reviews_digest                = RECOMMENDATION_ONLY
open_items                    = unresolved work, not accepted facts
```

Guardrail остаётся recommendation до подтверждения владельцем, если A5 не классифицировал его как обязательное условие безопасного proceed. Обязательный safety constraint должен иметь отдельный `gate_constraint` и не смешиваться с обычной рекомендацией.

### 11.5 Source coverage manifest

Для каждого значимого leaf source path A6 фиксирует ровно одну disposition:

```yaml
source_coverage_manifest:
  - source_artifact_id:
    source_path:
    disposition: frozen/open_item/recommendation/metadata/explicitly_omitted
    target_path:
    omission_reason:
```

`explicitly_omitted` разрешён только для служебных метаданных или дублируемого derived presentation. Значимый продуктовый факт не может иметь эту disposition.

### 11.6 Atomic publication

Runner выполняет:

1. Запись gate и snapshot во временные immutable paths.
2. Schema validation обоих файлов.
3. Проверку snapshot completeness и cross hashes.
4. Формирование `publish_manifest.yaml`.
5. Один atomic rename/commit publish set.

Если любой шаг не завершён, B1 не видит частично опубликованный handoff.

### 11.7 B1 preflight

B1 проверяет:

- gate status = PROCEED;
- snapshot hash совпадает с gate decision;
- readiness certificate = true;
- `no_silent_omissions = true`;
- owner confirmation status и список pending actions;
- все `RECOMMENDATION_ONLY` остаются unlocked до B1 HITL.

---

## 12. Cross-review consistency model

Минимальные проверки текущего A6 сохраняются и нормализуются:

| Check | Source A | Source B | Conflict |
|---|---|---|---|
| `icp_vs_segment` | `marketing_review.icp_hypothesis.primary_icp_profile` | `idea_note.target_segment_definition` | ICP выходит за исходный segment или исключает его ядро |
| `positioning_vs_value` | positioning differentiation axis | Idea Note primary value mechanism | заявленное отличие требует другого механизма |
| `functional_change_vs_automation` | A3 functional suggestions | A4 technical impact entries | suggestion имеет high risk/worsen и одновременно подан как ready recommendation |
| `guardrails_vs_mvp` | A5 guardrails | MVP core/bounds | guardrail требует удалить или добавить core behavior |

Исправляется текущий path mismatch: Vision содержит `primary_user`, а `target_segment_definition` находится в Idea Note. A6 не должен искать `vision.target_segment_definition` как единственный source.

Дополнительные проверки:

| Check | Условие конфликта |
|---|---|
| `monetization_vs_paying_user` | monetization предполагает плательщика, противоречащего `paying_user` |
| `data_created_vs_entities` | data_created не является subset domain entities |
| `guardrail_traceability` | medium/high misuse или potential flag без guardrail |
| `roadmap_vs_mvp_bounds` | phase 1/2 включает excluded scope без entry condition |
| `kill_metric_vs_success_metrics` | kill metric не связан ни с одной success metric |
| `review_version_coherence` | review рассчитан на superseded upstream version |

A6 фиксирует конфликт и route, но не выбирает победившую трактовку.

---

## 13. Инварианты Layer A

1. Один агент — один набор owned artifacts.
2. Vision не публикуется без явного owner confirmation.
3. Любой применённый A1 patch подтверждён владельцем.
4. A2 не расширяет segment, platform, MVP scope или domain model.
5. `data_created ⊆ domain_entities`.
6. Значимое поле Vision либо mapped, либо отражено в coverage warning.
7. Review score рассчитан по versioned anchor points.
8. Frozen score переносится только при неизменных dependencies.
9. Review не выдаёт внешний market/legal факт за доказательство.
10. A4 оценивает feasibility, но не проектирует architecture.
11. Каждый significant ethics risk присутствует в теле review и имеет disposition.
12. Каждый medium/high misuse и potential Stage-0 flag имеет traceable guardrail.
13. A6 не меняет upstream product content и scores.
14. Любой `revise` или `block` запрещает PROCEED.
15. A6 не публикует snapshot при BLOCK.
16. Snapshot и gate относятся к одному run/cycle и взаимно hash-linked.
17. Snapshot не теряет значимые source fields молча.
18. RECOMMENDATION_ONLY не становится requirement без HITL.
19. Revision запускается от самого раннего владельца изменяемого поля.
20. После revision повторяется весь downstream closure.
21. B1 не запускается без валидной пары gate + snapshot.
22. Исчерпание retry budget не превращает BLOCK в PROCEED.

---

## 14. Что нужно изменить в существующих промптах

### 14.1 Общие изменения A1–A6

- Добавить common artifact envelope, `schema_version`, `run_id`, `cycle_id`, lineage refs.
- Установить полные top-level output schemas, а не только фрагменты анализа.
- Ввести canonical enums и одинаковый casing.
- Добавить stage validation status и запрет публикации partial output.
- Ссылаться на logical artifact IDs, а не на неоднозначное имя «A6.final_gate_decision».

### 14.2 A1

- Добавить недостающий `mvp_concept` с четырьмя contract fields.
- Добавить `patch_item_id` в `vision_patch.yaml` — A2 уже ожидает этот ID.
- Формализовать `a1_interview_state.yaml` и resume.
- Указать, что `vision_patch` содержит только confirmed items.
- Разделить owner facts, agent suggestions и accepted suggestions в provenance.

### 14.3 A2

- Добавить `RECOMPILE` mode для реального route A6 → A2 без фиктивного Vision patch.
- Добавить `change_origin` и affected dimensions в revision context.
- Определить полную схему BLOCK/RETURN_TO_VISION output с artifact envelope.
- Исправить mapping target paths: `mvp_success_signal` и `success_metrics_initial` должны указывать на `mvp_concept.measurable_signal` и `mvp_concept.validation_goal`, как в итоговой схеме, а не на неоднозначные top-level names.
- Исправить неоднозначную структуру `monetization_hypothesis` (сейчас она одновременно выглядит scalar и object с `derived_extension`).
- Определить mapping для значимых Vision fields, которые сегодня систематически уходят только в warnings.

### 14.4 A3

- Добавить полный `marketing_review.yaml` envelope/schema.
- Добавить stable IDs для gaps, suggestions, questions и blockers.
- Подключить versioned impact matrix.
- Уточнить: `EXPERIMENT_NOT_LINKED` блокирует публикацию самого review до исправления.
- Убрать route A2 для фактов, которые требуют owner decision; такие route должны идти в A1.
- Добавить каноническое `open_questions: []`, которое уже ожидает A6 snapshot contract.

### 14.5 A4

- Добавить полный `architecture_review.yaml` envelope/schema.
- Добавить `gap_id` — A6 snapshot уже ожидает его.
- Явно связать каждый score и HITL trigger с source paths/scenarios.
- Подключить versioned impact matrix.
- Разделить product-content revision и review recompute.
- Учитывать изменение `marketing_review.functional_impact_suggestions` даже при неизменном `revision_context.changed_fields`.
- Маршрутизировать entity/MVP owner facts в A1, а не пытаться изменить их внутри A2.
- Добавить каноническое `open_questions: []`.

### 14.6 A5

- Добавить полный `ethics_review.yaml` envelope/schema.
- Формализовать критерий `guardrails_adequate`, используемый A6.
- Добавить stable IDs для risks и связь risk → misuse → guardrail → verification.
- Подключить versioned impact matrix.
- Указать, какие unresolved safety questions допустимо передать в B при `proceed`, а какие требуют A1 revision.
- Инвалидировать зависимые frozen оценки при изменении использованных Marketing/Architecture Review, даже если Idea Note не изменился.
- Добавить каноническое `open_questions: []`.

### 14.7 A6

- Считать все три recommendations critical gate facts.
- Блокировать не только `block`, но и `revise`.
- Добавить field resolution для architecture recommendation, regulatory exposure, triggers, gaps и guardrail adequacy.
- Исправить `vision.target_segment_definition` на канонический Idea Note path с fallback к `vision.primary_user`.
- Добавить `artifact_meta` и lineage в BLOCK/PROCEED outputs.
- Публиковать `revision_request.yaml` с `revision_kind` и `restart_from`.
- Расширить snapshot до lossless projection и добавить source coverage manifest.
- Добавить cross hash gate ↔ snapshot и atomic publish contract.
- Не восстанавливать исчезнувший assumption из произвольной предыдущей версии без lineage validation; это должен делать A2 или runner через BLOCK.

### 14.8 B1 boundary

- Сделать `final_gate_decision.yaml` обязательным входом B1 наряду со snapshot.
- Добавить hash/readiness preflight.
- Различать frozen projection confirmation и handoff authorization.
- Сохранить запрет принимать recommendation без owner confirmation.

---

## 15. Директории артефактов

Рекомендуемая физическая структура runtime outputs:

```text
<a_run_root>/
  a_layer_run.yaml
  cycles/
    AC-001/
      inputs/
      A1/
        vision.yaml
        a1_interview_state.yaml
      A2/
        idea_note.yaml
      A3/
        marketing_review.yaml
      A4/
        architecture_review.yaml
      A5/
        ethics_review.yaml
      A6/
        final_gate_decision.yaml
      manifests/
    AC-002/
      A1/
        vision.yaml
        vision_patch.yaml
        revision_advocate_summary.yaml
      A2/
        idea_note.yaml
        revision_context.yaml
      ...
  published/
    final_gate_decision.yaml
    IdeaNoteLayer.snapshot.yaml
    publish_manifest.yaml
  superseded/
  events/
```

Prompt-файлы остаются в `A.Idea Note Layer/`. Runtime outputs не должны смешиваться с prompts.

---

## 16. Validation и acceptance tests

### 16.1 Schema tests

- Каждый artifact проходит YAML parse и schema validation.
- Все enum values принадлежат canonical registry.
- Все IDs уникальны в scope run.
- Все refs разрешаются и совпадают по hash.
- Все required fields review/gate/snapshot присутствуют.

### 16.2 Lineage tests

- A2 ссылается на текущий A1 Vision.
- A3 ссылается на текущий A2 Idea Note.
- A4 ссылается на текущие A2 и A3.
- A5 ссылается на текущие фактически использованные inputs.
- A6 ссылается на одну согласованную цепочку.
- После patch старый downstream output отклоняется как stale.

### 16.3 Revision tests

1. Изменение одного owner field пересматривает только affected Idea Note fields, но rerun'ит downstream closure.
2. Frozen scores сохраняются при неизменных dependencies.
3. Anchor schema change принудительно пересчитывает соответствующий review.
4. Route A2 работает без фиктивного Vision patch.
5. Route A3/A4/A5 не вызывает owner interview без product-content change.
6. Повтор того же blocker fingerprint без изменений эскалируется.

### 16.4 Gate regression matrix

| Case | Expected |
|---|---|
| missing input | BLOCK |
| review = block | BLOCK |
| review = revise | BLOCK + replay route |
| high HITL, triggers empty | BLOCK |
| high HITL, triggers complete, A4 proceed | не блокирует сам по себе |
| automation score 5 | BLOCK |
| one critical architecture gap | BLOCK |
| confirmed Stage-0 flag | BLOCK |
| high regulatory exposure, guardrails inadequate | BLOCK |
| cross-review conflict | BLOCK |
| only significant/minor documented open items, all reviews proceed | PROCEED |
| snapshot completeness false | BLOCK publication |

### 16.5 Snapshot tests

- Все assumptions, risks, guardrails, safety questions и contracts перенесены.
- Все значимые source leaves имеют disposition.
- Recommendations помечены `RECOMMENDATION_ONLY`.
- Frozen и open items не пересекаются по одному и тому же решению.
- Gate snapshot hash совпадает с фактическим файлом.
- B1 preflight принимает только полную опубликованную пару.

### 16.6 Reference-run compatibility

Существующие файлы `TEST WORKFLOW/1.A.Idea Note Layer RS` рассматриваются как legacy fixtures. Compatibility tests должны явно ловить:

- snapshot, встроенный в gate output вместо отдельного файла;
- `frozen_summary` вместо `frozen_core`;
- отсутствующие `layer_readiness_certificate` и completeness fields;
- неполные assumption records;
- версии reviews, не совпадающие с фактической lineage;
- `revision_routing.target_agent`, противоречащий итоговому `recommendation`.

Legacy fixture можно нормализовать для чтения, но нельзя публиковать в B как новый frozen handoff без повторного A6 gate.

---

## 17. Порядок внедрения

### Шаг 1 — schema registry и common envelope

Зафиксировать схемы Vision, Idea Note, трёх reviews, Gate Decision, Snapshot, Revision Request и manifests.

### Шаг 2 — A1/A2 contract repair

Добавить MVP contracts в Vision, patch IDs, resume state и A2 RECOMPILE mode. Это устраняет самые ранние разрывы lineage и revision.

### Шаг 3 — reviewer normalization

Добавить полные output schemas, stable finding IDs, impact registry и source-path evidence в A3–A5.

### Шаг 4 — A6 gate hardening

Нормализовать facts, `revise` policy, cross-review paths, routing, completeness и lossless snapshot.

### Шаг 5 — runner/control plane

Реализовать cycle state, manifests, stale invalidation, no-progress detection и atomic publication.

### Шаг 6 — B1 boundary update

Обязать B1 проверять gate + snapshot pair и handoff authorization.

### Шаг 7 — regression run

Прогнать initial, каждый restart route, high-HITL route, ethics hard flag, conflict cases, crash/resume и legacy fixture normalization.

---

## 18. Принятые решения и открытые вопросы

### Принято

- Ростер остаётся A1–A6.
- A3 → A4 → A5 выполняются последовательно.
- Все `revise` блокируют publication до replay.
- Revision начинается с владельца изменяемого поля.
- A2 получает отдельный RECOMPILE mode.
- A6 публикует snapshot только при PROCEED.
- B1 принимает hash-linked gate + snapshot pair.
- Snapshot получает lossless source coverage manifest.
- Handoff authorization хранится отдельно от бинарного gate status.

### Открытые вопросы реализации

1. Где будет жить schema registry: рядом с Layer A или в общем control-plane каталоге всех слоёв?
2. Какой runner станет нормативным: CLI, pipeline service или human-run session wrapper?
3. Требуется ли cryptographic owner approval event уже в Layer A, либо достаточно session-bound confirmation record до более позднего общего authorization layer?
4. Должен ли A1 hard-limit в семь вопросов означать новый cycle или continuation внутри того же cycle? Рекомендуемый вариант: новый interview pass внутри того же cycle, пока product inputs не опубликованы.

Эти вопросы не меняют логическую архитектуру A1–A6 и могут быть закрыты при проектировании runner.

---

## 19. Что не меняется

- A1 остаётся единственной точкой подтверждённого изменения Vision.
- Правило «один вопрос за раз» сохраняется.
- A2 остаётся ограниченной трансформацией, а не генератором нового scope.
- Anchor scoring A3–A5 сохраняется как основа калибровки.
- A4 не становится Architecture Designer.
- A5 не становится юридическим консультантом.
- A6 остаётся бинарным gatekeeper и не разрешает конфликты самостоятельно.
- High HITL с документированными triggers остаётся допустимой характеристикой реализации.
- Recommendations reviewers не становятся требованиями без HITL.
- Snapshot остаётся обязательным источником состояния Layer A для B1.

---

## 20. Definition of Done Layer A

Layer A завершён только если одновременно истинно:

```yaml
definition_of_done:
  vision_owner_confirmed: true
  idea_note_schema_valid: true
  vision_coverage_complete_or_warned: true
  marketing_review_recommendation: proceed
  architecture_review_recommendation: proceed
  ethics_review_recommendation: proceed
  cross_review_conflicts_open: 0
  critical_gate_facts_unresolved: 0
  final_gate_status: PROCEED
  snapshot_generated: true
  snapshot_completeness_passed: true
  gate_snapshot_hash_link_valid: true
  publish_manifest_committed: true
  b1_preflight_ready: true
```

До выполнения всех условий Layer A находится в `blocked`, `revision` или `escalated`, но не считается переданным в Layer B.
