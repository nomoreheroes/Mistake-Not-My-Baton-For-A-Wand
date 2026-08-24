# E Layer — Architecture Plan

**Слой:** E — Design Research & Intent  
**Дата:** 2026-08-24  
**Ревизия:** R1  
**Статус:** ACTIVE BASELINE / PROMPT ALIGNMENT REQUIRED

**Основание:** существующие промпты E1–E12, `design_parameter_reference.yaml`, publish-контракт Layer D и фактические входы Layer F.

**Назначение документа:** определить путь от утверждённого PRD к подписанной паре design tokens + design grammar, сохраняя различие между исследовательским сигналом, owner intent, derived normalization, review и финальным source of truth.

---

## 1. Назначение и границы слоя

Layer E превращает продуктовый intent в проверенный design-system intent:

```text
Layer D published PRD/story corpus
        ↓
design research
        ↓
owner design vision
        ↓
parameter alignment + normalized grammar draft
        ↓
expressive/product/marketing/accessibility/frontend reviews
        ↓
mood sketches + owner direction
        ↓
intent gate + condition resolution
        ↓
per-parameter HITL sign-off
        ↓
design_tokens.json + design_grammar.yaml
```

Слой отвечает за:

- исследовательскую рамку category/user expectations;
- явное owner intent по характеру, выразительности и ограничениям;
- полноту параметров по repository-pinned reference;
- перевод intent в surface/interaction/status/role/hierarchy grammar;
- reviews с разных профессиональных перспектив;
- выбранное mood direction без преждевременного UI design;
- финальный owner sign-off каждого обязательного параметра;
- атомарную публикацию двух downstream design sources.

Layer E не:

- проектирует surface map, navigation, IA или компоненты конкретного интерфейса;
- принимает research hypothesis за факт;
- превращает mood sketch в screen specification;
- вознаграждает flat minimalism только за простоту реализации;
- позволяет F/G/H читать черновики E2–E10 как source of truth;
- создаёт третий независимый финальный design artifact.

---

## 2. Нормативные решения слоя

### Решение E-D1 — вход только из D7 publish package

E1 стартует при наличии:

- `layer_d_publish_manifest.yaml`;
- `LayerD.snapshot.yaml`;
- `d7_gate_report.yaml` с `PROCEED`;
- `prd.index.yaml` и referenced inventories/stories с совпадающими hashes.

Прямое чтение working inventories или произвольных story files запрещено.

### Решение E-D2 — parameter reference pinning

`design_parameter_reference.yaml` является schema/completeness authority, но не style authority. Его schema version и content hash фиксируются в run manifest и во всех E3/E4/E11/E12 outputs.

Изменение reference инвалидирует E3–E12 и требует migration либо replay.

### Решение E-D3 — четыре класса утверждений не смешиваются

Каждое значимое утверждение имеет `claim_class`:

- `upstream_fact` — из approved A/D package;
- `owner_intent` — реальный ответ E2/E10/E11/E12;
- `research_observation` — паттерн/сигнал с evidence scope;
- `derived_candidate` — синтез E3/E4, требующий review/sign-off.

Hypothesis не становится owner intent без decision receipt.

### Решение E-D4 — review topology фиксирована

После E4:

1. E5, E6 и E7 могут выполняться параллельно по одной версии E4.
2. E8 запускается после current E5/E6/E7 barrier.
3. E9 запускается после current E5/E6/E8 и видит E7 через нормализованный context/manifest.
4. E10 требует все пять current review reports.

Молчаливо отсутствующий reviewer недопустим.

### Решение E-D5 — reviewer возвращает к владельцу данных

Canonical return содержит `restart_from: E2 | E3 | E4`. Legacy `RETURN_TO_E2` отображается в эту модель, но не заставляет перезапускать owner interview, если ошибка только в normalization/draft.

### Решение E-D6 — E10 является mood calibration, не финальным design source

SVGs и `e10_mood_direction.yaml` нужны E11/E12 как подтверждённый calibration input. Downstream layers не используют их вместо tokens/grammar.

### Решение E-D7 — E11 является gate к sign-off, а не финальным gate слоя

E11 решает готовность к E12 и закрывает non-design conditions. Финальная публикация слоя разрешается только после E12 completeness/sign-off validation.

### Решение E-D8 — все reviewers обязательны

E5–E9 могут быть `SKIP_NOT_APPLICABLE` только через заранее определённую applicability rule и валидный receipt. Для текущего универсального E-процесса baseline — все пять применимы.

### Решение E-D9 — финальных design sources ровно два

- `design_tokens.json` — конкретные значения;
- `design_grammar.yaml` — правила применения и token refs.

`e12_signoff_receipt.yaml`, `e12_gate_report.yaml` и publish manifest — control-plane/audit, а не третий design source.

### Решение E-D10 — final pair публикуется атомарно

Ни tokens без grammar, ни grammar без tokens не являются валидным Layer E package. Hash каждого файла указан в manifest; cross-references валидируются до переключения current.

### Решение E-D11 — owner metadata не ломает token format

Подтверждения параметров хранятся в sign-off receipt. В `design_tokens.json` допускаются только поля поддерживаемого token format и, при необходимости, валидные `$extensions`; произвольные `owner_response` рядом с `$value` запрещены.

### Решение E-D12 — F читает только E12 package

F получает final pair, E layer snapshot/gate/manifest и D package refs. F не читает `design_intent_normalized.yaml`, E5–E9 reports или mood SVG для принятия архитектурных решений.

---

## 3. Общий поток исполнения

### 3.1 INITIAL

```text
D7 published package
  ↓
E1 Design Research & Category Analyst
  → e1_research_memo.yaml
  ↓
E2 Design Vision Interview [HITL]
  → design_vision.yaml
  → e2_owner_decisions.yaml
  ↓
E3 Design Parameter Alignment
  → design_parameter_alignment.yaml
  ↓
E4 Design Intent Normalizer / Tension Mapper
  → design_intent_normalized.yaml
  ↓
  ├─ E5 Expressive Adequacy Review ─┐
  ├─ E6 PM Intent Review            ├─ barrier
  └─ E7 Marketing Positioning Review┘
                    ↓
          E8 Accessibility Intent Review
                    ↓
          E9 Frontend Feasibility Review
                    ↓ all reviews current, no RETURN
E10 Mood Sketcher [SVG + HITL]
  → mood_sketch_A/B/C.svg
  → e10_mood_direction.yaml
                    ↓
E11 Research & Intent Gatekeeper
  ├─ RETURN → earliest owner E2/E3/E4 + downstream replay
  └─ READY / CONDITIONS → Mode B HITL if needed
                    ↓ ready_for_E12
E12 Design Specification Sign-Off [HITL]
  → design_tokens.json
  → design_grammar.yaml
  → e12_signoff_receipt.yaml
  → e12_gate_report.yaml
                    ↓ atomic publish
              LayerE.snapshot.yaml
              layer_e_publish_manifest.yaml
                    ↓
                   F1
```

### 3.2 Review barrier

```text
E4@hash-X
 ├─ E5@X
 ├─ E6@X
 └─ E7@X
      ↓ barrier-1
    E8@X + refs(E5,E6,E7)
      ↓
    E9@X + refs(E5,E6,E8)
      ↓ barrier-2
    E10
```

Review по другой E4 version считается stale независимо от текста recommendation.

### 3.3 Revision closure

```text
restart E2 → E2→E3→E4→E5/E6/E7→E8→E9→E10→E11→E12
restart E3 → E3→E4→E5/E6/E7→E8→E9→E10→E11→E12
restart E4 → E4→E5/E6/E7→E8→E9→E10→E11→E12
```

Если E11/E12 меняет только non-semantic confirmation metadata, ранние stages не replay. Если owner response меняет intent/value/grammar — возврат идёт к соответствующему owner.

---

## 4. Роли и ownership

| Агент | Ответственность | Output | HITL |
|---|---|---|---|
| E1 | Research/category/user expectation signals | `e1_research_memo.yaml` | Нет |
| E2 | Owner design vision | `design_vision.yaml` | Да |
| E3 | Parameter coverage, ranges, alignment | `design_parameter_alignment.yaml` | Нет |
| E4 | Normalization, tensions, grammar/token drafts | `design_intent_normalized.yaml` | Нет |
| E5 | Expressive adequacy/surface grammar | `e5_review_report.yaml` | Нет |
| E6 | Product/MVP/story intent | `e6_review_report.yaml` | Нет |
| E7 | Marketing/category/positioning | `e7_review_report.yaml` | Нет |
| E8 | Accessibility at intent level | `e8_review_report.yaml` | Нет |
| E9 | Frontend/design-system feasibility at intent level | `e9_review_report.yaml` | Нет |
| E10 | Mood alternatives and owner choice | SVGs + `e10_mood_direction.yaml` | Да |
| E11 | Aggregation, routing, owner conditions | `e11_gate_report.yaml` | Conditional |
| E12 | Per-parameter sign-off and final pair | tokens + grammar + receipts | Да |
| Runner | Lineage, barriers, checkpoints, publish | manifests/snapshot | Нет |

Каждый агент редактирует только свой output. E11 не переписывает E2/E4; E12 не «исправляет» owner intent без зафиксированного question/answer.

---

## 5. Common envelope, evidence и decision receipts

```yaml
artifact_meta:
  artifact_type: design_intent_normalized
  schema_version: e.design-intent.v1
  artifact_version: 2
  layer: E
  producer: E4
  run_id: run-...
  cycle_id: cycle-...
  source_layer_d_package_id: D-...
  parameter_reference:
    schema_version: e.design-parameters.v1
    sha256: "..."
  status: complete
  derived_from: []
  content_sha256: "..."
```

Evidence reference:

```yaml
evidence_ref:
  evidence_id: EV-...
  class: upstream_artifact | repository_reference | external_pattern | owner_response | derived_analysis
  locator: "..."
  observed_at: "..."
  confidence: high | medium | low
  limitation: "..."
```

Owner receipt:

```yaml
decision_receipt:
  decision_id: E2-DEC-...
  session_id: E2-SESSION-...
  question_id: Q-...
  question_text: "..."
  owner_response: "..."
  normalized_decision: "..."
  affected_parameter_ids: []
  confirmed_at: "..."
```

Синтетический owner response запрещён.

---

## 6. Источники истины и приоритеты

При конфликте используются разные authority domains:

| Domain | Authority |
|---|---|
| Product facts, MVP, stories | Layer D package с refs на A–C |
| Parameter completeness/vocabulary | pinned `design_parameter_reference.yaml` |
| Design preference/intent | E2 owner decisions |
| Research pattern | E1, только advisory/evidence |
| Normalized draft | E3/E4, derived candidate |
| Review quality signal | E5–E9 |
| Mood calibration | E10 owner choice |
| Readiness/routing | E11 |
| Final parameter values/rules | E12 final pair |

Downstream authority:

```text
design_tokens.json + design_grammar.yaml > любые E2–E10 drafts
```

---

## 7. E1 — research contract

E1 производит observations, hypotheses, tensions и constructive patterns. Он обязан:

- отделять общие category patterns от проверенных данных конкретного рынка;
- указывать evidence scope/confidence;
- не использовать нормативный язык «должно быть»;
- включать anti-patterns и риск sterile flatness;
- покрывать product expression, visual system, surface expression, interaction, brand/platform constraints и surface map hypotheses;
- явно указывать вопросы для E2.

Исправление schema mapping:

- `target_user_profile` выводится из нормативных полей A/D (`target_segment`, `primary_user`, roles), а не читается как несуществующий обязательный path;
- `product_category` является derived classification с evidence, если upstream не содержит подтверждённой category.

Research memo не является доказательством market fit и не может изменять frozen core.

---

## 8. E2 — Design Vision HITL

E2 задаёт один вопрос за раз и фиксирует решения по блокам:

- product expression;
- visual system;
- surface expression calibration;
- interaction principles;
- brand constraints;
- platform constraints;
- surface design map.

Каждое решение имеет:

```yaml
decision:
  parameter_area: visual_character
  value_or_direction: "..."
  strength: preference | constraint | invariant
  scope: global | surface_type | named_surface
  source: owner_response
  decision_ref: E2-DEC-...
  unresolved: false
```

Mode B reopens только affected blocks. Ранее подтверждённое решение не пересматривается без конкретной причины/конфликта.

Checkpoint пишется после каждого ответа; `design_vision.yaml` публикуется только после завершения session или как явно `INCOMPLETE` вне downstream barrier.

---

## 9. E3 — parameter alignment

E3 использует parameter reference как checklist:

- строит coverage index по всем required parameter groups;
- связывает E2 axes с параметрами;
- определяет calibration ranges;
- формирует positive/anti patterns;
- предлагает surface grammar hypotheses;
- создаёт очередь параметров для E12;
- маркирует non-importable research areas.

Каждый параметр получает:

```yaml
parameter_alignment:
  parameter_id: color.role.accent
  artifact_destination: design_tokens.json
  coverage: explicit | derivable | missing | not_applicable
  source_refs: []
  candidate_range: "..."
  owner_confirmation_required: true
```

`not_applicable` требует rationale и затем проверяется E11/E12.

---

## 10. E4 — normalized intent и drafts

E4 разделяет четыре слоя:

1. product invariant;
2. design invariant/constraint;
3. preference/calibration;
4. exploratory/open interpretation.

Он выявляет:

- internal tension;
- design↔product tension;
- design↔research tension;
- coverage gap;
- open interpretation zone без ложного конфликта.

Grammar contract покрывает:

- surface grammar;
- interaction grammar;
- status/service-state grammar;
- role grammar;
- hierarchy grammar;
- surface-type grammar;
- underexpression risks.

Draft blocks являются кандидатами E12:

```yaml
design_tokens_draft: {}
design_grammar_draft: {}
draft_coverage:
  required_parameter_count: 0
  covered: []
  missing: []
```

Lineage mismatch или отсутствующий обязательный блок даёт `BLOCK`, а не partial continuation. E4 не создаёт final pair.

---

## 11. Review contracts E5–E9

### 11.1 Общий review envelope

```yaml
review:
  reviewer: E5
  reviewed_e4_sha256: "..."
  dependency_review_refs: []
  findings:
    - finding_id: E5-F-001
      severity: critical | significant | advisory
      evidence_refs: []
      affected_parameter_ids: []
      suggested_outcome: "..."
      data_owner: E2 | E3 | E4
  recommendation: PROCEED | PROCEED_WITH_NOTES | RETURN
  revision_route:
    restart_from: E2 | E3 | E4 | null
```

### 11.2 E5 — Expressive Adequacy

Проверяет surface differentiation, hierarchy depth, role/state legibility, rhythm, actionable/informational separation и generic/sterile flatness risk. Critical underexpression core surfaces блокирует gate.

### 11.3 E6 — PM Intent

Проверяет value mechanism, success/kill metrics, target user, MVP discipline, story coverage, automation/control и trust model. E6 не использует E1 напрямую, чтобы research hypothesis не переопределял product truth.

### 11.4 E7 — Marketing Positioning

Проверяет category/segment perception, value signal, trust, tone, differentiation и over/under-conformity. Внешние паттерны маркируются как evidence, а deviation не считается failure автоматически.

### 11.5 E8 — Accessibility Intent

Проверяет color/contrast intent, typography/readability, density/load, motion, input modalities, feedback, recovery и semantic recognizability. Это intent review, не WCAG implementation audit.

### 11.6 E9 — Frontend Feasibility

Проверяет platform compatibility, responsive intent, interaction/motion/data-driven complexity, tokenization, reuse, state model и expressive systematizability. Простота реализации не оправдывает потерю подтверждённой выразительности.

---

## 12. E10 — mood sketches и owner direction

### 12.1 Preconditions

E10 стартует только если:

- E4 current и complete;
- E5–E9 current;
- ни один reviewer не вернул `RETURN`;
- critical tensions имеют resolution;
- notes собраны в calibration brief.

### 12.2 Sketch contract

E10 создаёт 2–3 SVG 800×600. Каждый вариант показывает фрагменты, достаточные для оценки:

- hierarchy;
- density/rhythm;
- panel/conversation/status differentiation;
- service states;
- expressive range.

SVG не является screen, component library или pixel-perfect UI. Варианты должны быть содержательно различимы, при этом хотя бы один реализует принцип restrained-but-rich.

### 12.3 HITL output

```yaml
mood_direction:
  approved_sketch_id: B
  approved_character: "..."
  density_approach: "..."
  hierarchy_approach: "..."
  service_states: "..."
  interaction_tone: "..."
  binding_levels: {}
  rejected_variants: []
  requires_revalidation: false
  owner_decision_ref: E10-DEC-...
```

SVG manifest хранит hashes всех вариантов. Не выбранные sketches остаются audit evidence, но не downstream authority.

---

## 13. E11 — intent gate и conditions

### 13.1 Mode A

E11 агрегирует, не переревьюит:

- review verdict matrix;
- conflicts between equal reviewers;
- blind spots/systemic tensions;
- expressive gate;
- parameter/draft readiness;
- mood direction vs findings;
- unresolved items.

Verdicts:

- `APPROVED_FOR_E12`;
- `APPROVED_WITH_CONDITIONS`;
- `RETURN` с `restart_from`.

### 13.2 Mode B

Mode B разрешает только gate-critical owner conditions, которые не требуют перепроектирования E2–E4. Один вопрос за раз; все ответы входят в decision receipts.

Если ответ меняет intent, scope или draft semantics, Mode B прекращается и verdict становится `RETURN`.

### 13.3 Ready rule

`ready_for_E12: true`, когда:

- нет reviewer return;
- нет blocking handoff item;
- required parameters имеют candidate или explicit E12 confirmation path;
- expressive adequacy не critical;
- mood direction approved/current;
- Mode B conditions закрыты либо корректно переданы E12.

Фраза о разрешении условий «архитекторами F-слоя» удаляется: до E12 это owner/E12 responsibility.

---

## 14. E12 — final sign-off

### 14.1 Parameter inventory

E12 строит полный inventory из pinned reference и классифицирует каждый параметр:

```yaml
parameter_signoff:
  parameter_id: spacing.scale.200
  destination: design_tokens.json
  candidate_value_or_rule: "..."
  source_priority_used: E4_draft
  status: confirmed | adjusted | not_applicable
  owner_decision_ref: E12-DEC-...
```

Ни один required parameter не остаётся `pending`.

### 14.2 HITL protocol

- один вопрос — один ответ;
- сначала token value groups, затем grammar groups;
- похожие параметры можно показывать компактной группой, но decision status хранится per parameter;
- adjustment обновляет candidate и требует явного подтверждения;
- checkpoint после каждого ответа;
- resume не повторяет already confirmed parameter без invalidation.

### 14.3 `design_tokens.json`

Файл соответствует repository-declared supported W3C Design Tokens Format Module version. В нём находятся concrete values: color, typography, spacing, form, motion и другие tokenizable значения.

Requirements:

- валидные `$type`/`$value`/references;
- unique canonical token paths;
- no unresolved refs;
- no circular refs;
- deterministic serialization;
- sign-off metadata вынесены в receipt либо валидные `$extensions`.

### 14.4 `design_grammar.yaml`

Grammar содержит правила применения:

- surface/zone hierarchy;
- interaction states;
- role/status language;
- density and rhythm policies;
- component category rules;
- responsive/adaptive intent;
- semantic token refs.

Raw tokenizable hex/px/typographic values запрещены: используется `token_ref`. Нечисловые policy scalars и semantic ranges допустимы, если они являются правилом, а не скрытым токеном.

### 14.5 Final completeness gate

E12 проверяет:

1. Все required parameters resolved.
2. E11 ready и current.
3. Все owner receipts real/complete.
4. Tokens schema valid.
5. Grammar schema valid.
6. Все grammar token refs разрешаются.
7. Нет circular refs.
8. Draft→final coverage complete.
9. D scope/attention constraints отражены.
10. Self-audit critical checks true.

---

## 15. Финальный package

```text
published/layer-e/<package_id>/
├── design_tokens.json
├── design_grammar.yaml
├── e11_gate_report.yaml
├── e12_gate_report.yaml
├── e12_signoff_receipt.yaml
├── LayerE.snapshot.yaml
└── layer_e_publish_manifest.yaml
```

`LayerE.snapshot.yaml`:

```yaml
layer_e_snapshot:
  package_id: E-...
  source_layer_d_package_id: D-...
  parameter_reference:
    schema_version: e.design-parameters.v1
    sha256: "..."
  final_sources:
    design_tokens:
      path: design_tokens.json
      sha256: "..."
    design_grammar:
      path: design_grammar.yaml
      sha256: "..."
  gates:
    e11: {verdict: APPROVED_FOR_E12, sha256: "..."}
    e12: {verdict: PROCEED, sha256: "..."}
  carry_forward_conditions: []
  handoff:
    target: F1
    authorized: true
```

Control files объясняют публикацию, но downstream design lookup всегда идёт только в final pair.

---

## 16. Revision routing и invalidation

| Finding owner | Restart | Downstream closure |
|---|---|---|
| Product/PRD conflict | D1/D3 через Layer D | D7→E1→…→E12 |
| Owner design intent | E2 | E2→E3→E4→reviews→E10→E11→E12 |
| Parameter alignment/reference mapping | E3 | E3→E4→reviews→E10→E11→E12 |
| Normalization/draft grammar | E4 | E4→reviews→E10→E11→E12 |
| Reviewer-only stale/error | affected reviewer + dependent reviews | dependent barrier→E10→E11→E12 |
| Mood direction | E10 | E10→E11→E12 |
| Non-semantic owner condition | E11 Mode B | E11→E12 |
| Final value/rule adjustment | E12 | affected final validation→publish |

Изменение E5/E6/E7 может инвалидировать E8/E9 по dependency refs. Изменение E8 инвалидирует E9. Любое current review change инвалидирует E10/E11/E12.

---

## 17. State, concurrency и recovery

- E2/E10/E11 Mode B/E12 используют resumable session checkpoints.
- Owner answer log append-only.
- E5/E6/E7 могут работать параллельно только по immutable E4 hash.
- Runner фиксирует review barrier manifest.
- E12 final pair собирается в staging.
- Publication использует compare-and-swap и не оставляет half-published pair.
- Изменение parameter reference после начала run даёт `REFERENCE_STALE`.
- Idempotency key защищает повторную генерацию sketches/receipts.
- SVG generation failure не создаёт fake owner choice.

---

## 18. Инварианты слоя

1. Research observation не является owner decision.
2. Parameter reference задаёт полноту, не стиль.
3. Каждый owner intent имеет decision receipt.
4. Каждый review связан с current E4 hash.
5. Все пять review perspectives закрыты до E10.
6. Critical underexpression не проходит E11.
7. E10 choice не подменяет tokens/grammar.
8. Каждый required parameter подписан или justified not-applicable.
9. Grammar token refs разрешаются в final tokens.
10. Final pair публикуется атомарно.
11. Downstream не читает drafts как authority.
12. E11/E12 gate refs и final hashes совпадают с manifest.

---

## 19. Обязательные изменения промптов

### E1

- требовать D7 package/gate;
- исправить отсутствующие A field paths;
- добавить evidence class/confidence/limitations;
- читать stories по PRD manifest.

### E2

- добавить common envelope, owner receipts и resumable checkpoint;
- формализовать Mode B affected-block scope;
- запретить synthetic responses.

### E3/E4

- pin parameter reference hash/version;
- блокировать lineage mismatch;
- добавить per-parameter coverage IDs;
- отделить draft от final source;
- нормализовать D attention routes.

### E5–E9

- унифицировать recommendation и revision route;
- связать reviews с exact E4 hash;
- сделать dependency reports обязательными по topology;
- формализовать applicability/skip receipt;
- не смешивать evidence и authority.

### E10

- требовать полный current review barrier;
- добавить SVG manifest/hashes и HITL checkpoint;
- запретить продолжение при missing reviewer;
- оформить owner decision receipt.

### E11

- сделать all-review coverage обязательным;
- заменить всегда `RETURN_TO_E2` на owner-aware route;
- исправить ответственность conditions до E12;
- связать Mode B answers с receipts;
- не считать себя финальным publish gate.

### E12

- добавить resumable per-parameter ledger;
- хранить sign-off metadata вне token core;
- валидировать поддерживаемую token schema и cross-refs;
- публиковать pair + control receipt atomically;
- не создавать третий design source.

### F boundary

- удалить чтение E4 drafts, E5–E9 reports и E10 mood artifact как authority;
- требовать Layer E manifest/snapshot/E12 gate + final pair.

---

## 20. Валидация и тесты

### Reference/schema tests

- изменённый reference hash инвалидирует E3+;
- missing required parameter блокирует E12;
- invalid DTFM token record блокирует publish;
- grammar raw tokenizable value обнаруживается;
- unresolved/circular token ref блокирует publish.

### Evidence/decision tests

- hypothesis не может получить strength `invariant` без owner ref;
- пустой owner response не принимается;
- E2 resume не повторяет confirmed answers;
- external pattern с низкой confidence остаётся advisory.

### Review topology tests

- E8 не стартует без E5/E6/E7 current refs;
- E9 не стартует без E5/E6/E8;
- E10 блокируется при missing E7;
- изменённый E4 hash делает все reviews stale;
- E5 critical underexpression запрещает approval.

### Gate/sign-off tests

- E11 RETURN блокирует E12;
- E11 condition, меняющий intent, маршрутизируется E2/E3/E4;
- E12 подтверждает каждый required parameter;
- crash между записью tokens и grammar не меняет current package;
- F1 отвергает final pair без E12 gate/manifest.

### Handoff tests

- F не использует mood SVG или E4 draft;
- F grammar refs разрешаются по exact tokens hash;
- D package mismatch блокирует E1;
- carry-forward conditions присутствуют в E snapshot.

---

## 21. Порядок реализации

1. Утвердить common envelopes, claim classes и decision receipts.
2. Pin `design_parameter_reference.yaml` schema/hash.
3. Перевести E1 на D publish package.
4. Добавить checkpoints E2 и parameter coverage E3/E4.
5. Реализовать review dependency barrier E5–E9.
6. Сделать E10 full-barrier HITL с SVG manifest.
7. Обновить E11 owner-aware routing/Mode B.
8. Реализовать E12 sign-off ledger и validators.
9. Добавить atomic Layer E package и исправить F boundary.
10. Покрыть revision, stale-input и failure-injection tests.

---

## 22. Definition of Done

Layer E готов, когда:

- E1 принимает только D7-published package;
- research, owner intent и derived candidates различимы по provenance;
- parameter reference pinned и полностью покрыт;
- E5–E9 дают полный current review barrier;
- E10 фиксирует реальный owner mood choice;
- E11 маршрутизирует проблему к реальному data owner;
- E12 получает sign-off каждого required parameter;
- tokens и grammar валидны, согласованы и опубликованы атомарно;
- downstream design authority ограничена ровно двумя final files;
- F не читает internal E drafts/reviews как source of truth;
- prompts, schemas, runner и тесты соответствуют плану.

