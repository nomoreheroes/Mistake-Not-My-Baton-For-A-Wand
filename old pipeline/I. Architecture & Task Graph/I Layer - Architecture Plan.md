# I Layer — Architecture Plan

**Дата:** 2026-06-04  
**Ревизия:** 2026-07-02 R11  
**Статус:** ACTIVE

**R1 (2026-06-17):** handoff source H14→H15; I0 schema migration; H14 decisions в I1/I6; spike — только технические; upstream signals I14/I15; I7 incremental; api_binding_spec + on_device_bridge_contract; frozen_snapshot manifest; task_spec schema.

**R2 (2026-06-17):** Control plane pipeline_run (§5.0); I14/I15 переупорядочены — идут до I16/I17 и подают findings в conflict resolver (§3); open_question типизирован (§5.4); Assumption Ledger (§5.5); Unified Finding Schema (§5.6); I17 scope restriction (§5.7); I7 два режима (§5.9); I6 draft→patch→final (§5.10); observability/deployability hooks в I6 (§5.11); Coverage Matrix gate (§5.14); spike blast radius (§5.16); task_spec расширен + leaf task criteria (§5.17); on_device_call условия допустимости (§2); I1 +3 домена (§9); I4 authority model (§9); 7 invariant rules (§12).

**R3 (2026-06-17):** spike_candidate получил provenance_category + impact_radius (§5.16); I6 тегирует spikes; I16 применяет axis weights из I2 для автоматического гашения конфликтов (§3); I20 строгая топологическая сортировка (§3); I24 research → execution_phase: strict_first / batch_id: 0 (§3); оптимистичный сценарий spike (§5.4); Circuit Breaker маршрутизация проваленных spikes (§5.18); Layer Rollback механизм (§5.19); max_upstream_loops: 2 + полный перезапуск reviews после I6 (§5.8); spike_rejection.yaml как вход из J-слоя (§6); layer_rollback_request.yaml (§6); §11 переименован в «Принятые решения».

**R4 (2026-06-17):** GATE-PRE-I24 разделён на GATE-PRE-I24-RESEARCH_ONLY + GATE-PRE-I24-FULL_IMPLEMENTATION (§5.0); I24 два режима publish: research_only_snapshot | implementation_snapshot (§5.21, §5.16); architecture_global spike — implementation задачи не материализуются до успеха spike (§5.16); I16 restricted auto-resolve + audit trail (§5.20); parallel write policy run_events/ (§5.0); I0 smoke tests (§5.1); process_to_invariant explicit exemption (§5.14); provenance_minimum_by_task_type (§5.17); invariant rule #3 уточнён (§12).

**R5 (2026-06-17):** orchestration_contract §13; spike_execution_context.yaml §5.23; early-spike conservative route §5.22; I16 min_weight_delta: 0.15 + max_auto_resolve_severity: minor (§5.20); run_event_merge_policy fail-fast (§5.0); frozen_snapshot snapshot_mode + accepted_risk risk_kind (§5.15); h_layer_constraint_to_arch treatment schema (§5.14); I1 без hardcoded count; §11 оркестратор закрыт.

**R6 (2026-06-17):** run_events post_merge_lifecycle: archive + stale-delete при partial_restart; I0 BEGIN EXCLUSIVE TRANSACTION; axis_weight_contract normalized 0–1 sum=1.0; code.migration data_loss_risk обязательно + I22 rule; spike_execution_context causal_context из I3.

**R7 (2026-06-17):** I7 три режима: build_review_graph | architecture_final_graph (I7b, до I20) | task_trace_graph (I7c, после I23, до I24) — диаграмма §1, §3, §5.9; frozen_snapshot union format: implementation=final_architecture, research_only=research_architecture_context (§5.15); §5.4 противоречие устранено (architecture_global spike → impl не материализуются; component → blocked_by_spike); §5.22 явный research pipeline: I20.research_task_only → I22.research_spec → I23.research_snapshot_qa → I24.research_only; spike_candidate affected_process_ids + affected_invariant_ids + affected_interaction_ids (§5.16); §5.23 causal_context scope по process/invariant/interaction IDs; GATE-PRE-I6 расширен (6 артефактов + i0_migration_report check); data_loss_risk: requires_human_review + mitigation_plan, accepted_risk только после HITL (§5.17); conflict_resolution.condition: on_delete устраняет enum mismatch (§9).

**R8 (2026-06-17):** §5.9 заголовок "три режима"; §1 диаграмма с early-spike ветвью; GATE-PRE-I24-RESEARCH_ONLY расширен (7 blocking conditions); GATE-PRE-I24-FULL_IMPLEMENTATION расширен (11 required + 7 blocking); frozen_snapshot mode-specific included_artifacts + forbidden_in_research_only; §5.22 after_spike_success full pipeline с I7b/I7c/I21; §13 resume_after_spike_success три ветки; §5.23 causal_context из I3+I4+I5; §6 api_binding + on_device_bridge_contract artifact_status draft/final; §10 step 5 два пути (main + early-spike).

**R9 (2026-06-17):** нумерация приведена к порядку исполнения: I21=Task Spec Agent, I22=HITL Tree Review + Risk Acceptance (финальный порядок I20→I21→I22→I23→I24); I7a/b/c упразднены — единый агент I7 с mode в скобках; дедлок data_loss_risk: I21 ставит risk_level/mitigation_plan/requires_human_review, I22 заполняет accepted_risk_id; §5.9 idempotency constraint для I7 (task_trace_graph); §5.14 + §5.22 I23 dual-mode YAML-only в research_snapshot_qa; §5.12 conflict_resolution → {strategy: server_wins, condition: on_delete}; §5.16/§5.21 resume → §5.22 full implementation path; §11 enrich_final_graph → architecture_final_graph.

**R10 (2026-06-25):** добавлен первоклассный `task_type: human_action` для действий, которые может выполнить только человек во внешней системе: регистрация аккаунта, настройка cloud/app-store/payment console, ручное создание ресурса, выдача ключей/токенов через secret store. Для J добавлена цепочка `execution.chain: external_manual`; I20 материализует такие узлы в графе, I21 описывает `human_action` contract и secrets policy, I22 ревьюит blocking/risky human_action, I23/I24 валидируют provenance/secret hygiene, а J публикует `human_action_result.yaml` как evidence перед downstream-задачами.

**R11 (2026-07-02):** уточнена декомпозиция I20: `component_id` больше не является листовой единицей, I20 строит `decomposition_units[]`, выполняет mandatory minimality pass с `minimality_evidence`, создаёт code.adapter per contract operation, code.domain_logic per process step/stage, code.presentation per surface state/user flow. Добавлен `granularity_gap` для upstream-too-coarse artifacts и `granularity_report` для I22; PRD/UI coverage больше нельзя закрывать только агрегированными QA-задачами без конкретных implementation task refs.

**R11 follow-up:** I3/I5/I6 должны получить `granularity_refinement_mode` / revise-mode handlers для `granularity_refinement_signal.yaml`. Без этого I20 не имеет права маршрутизировать blocking `granularity_gap` в эти prompts как завершённый механизм; маршрут считается заблокированным implementation follow-up.

---

## 1. Назначение слоя

I-слой превращает H-layer Elm-архитектуру и пользовательские, системные и глобальные истории в **исполнимый граф задач** для J-слоя. Он строит фундаментальную модель системы (процессы → инварианты → interaction semantics → архитектура) и проводит её через quality, security, legal и deployment reviews.

```
h15_gate_decision: APPROVED
+ h9_contract_spec.yaml
+ h12_integration_spec.yaml
+ h14_hitl_decision_log.yaml
+ prd.index.yaml
        ↓
I0      bootstrap + schema migration (создаёт pipeline.db если нет; добавляет колонки; обновляет CLI-скрипты)
        ↓
I1–I2   technology research + decisions
        ↓
I3–I5   фундаментальная модель системы
        ↓
I6      architecture synthesis → system_architecture.draft.yaml
        ↓
[if architecture_global spike found → early-spike conservative route (§5.22):]
  I20.research_task_only → I21.research_spec → I23.research_snapshot_qa
        → I24.research_only_snapshot → J исполняет spike research
        → after all architecture_global spikes are closed: resume from I7 (build_review_graph mode, полный пайплайн ниже)
[else:]
        ↓
I7      causal graph (build_review_graph mode)
        ↓
I8–I13  quality reviews (параллельно)
        ↓
I14–I15 security + ethics/legal reviews → findings → I16
        ↓
I16     conflict resolver (aggregates I8–I13 + I14 + I15 findings)
        ↓
I17     HITL trade-off decision → architecture_decisions.yaml
        ↓
I6      patch run → system_architecture.final.yaml
        ↓
I18–I19 observability + deployment (develop hooks; optional upstream signal)
        ↓
I7      causal graph (architecture_final_graph mode)
        ↓
I20–I23 task graph → specs → HITL → coverage matrix
        ↓
I7      causal graph (task_trace_graph mode)
        ↓
I24     gatekeeper → frozen snapshot → J-слой
```

**Ключевое:** I-слой стартует только после H15 APPROVED. Каждый артефакт проходит lifecycle: draft → reviewed → accepted → frozen. `i_layer_run.yaml` (control plane) отслеживает статус артефактов, gates и replay-события.

---

## 2. Фундаментальные принципы

### Принцип 1 — On-device backend

Система включает on-device компоненты, а не только удалённый сервер. Минимум: solver-планировщик, парсер сообщений. Возможно: local store, local state machine.

**Каждый агент I3–I6 явно аннотирует `execution_location`:**
```
on_device  — solver, parser, local store, local state machine
server     — синхронизация, push, авторизация (если есть)
hybrid     — on-device с последующей sync на сервер
```

Offline-режим (INV-08 из G-слоя) — архитектурное требование к I6, не только UI-состояние.

### Принцип 2 — Выводить, не угадывать

Компоненты выводятся из процессов и инвариантов. Контракты — из interaction semantics. Архитектурный стиль — последний шаг синтеза, не первый. Метрика качества: invariant coverage, ownership clarity, coordination cost, failure isolation.

### Принцип 3 — Три типа взаимодействия

```
sync_rpc        — адресный вызов, ждёт ответа, network (100ms+)
async_event     — публикация события, не ждёт ответа
on_device_call  — локальный вызов; допустим только при соблюдении 5 условий
```

**Пять условий допустимости on_device_call:**
1. Worst-case latency укладывается в UX budget (`latency_budget_ms`)
2. Failure mode локален и recoverable без server authority
3. Local state гарантированно доступен в данном контексте (storage, worker, WASM)
4. Операция не требует server authority (нет multi-device consistency requirement)
5. Есть deterministic fallback или graceful degradation при отказе local runtime

I5 явно проверяет все 5 условий и фиксирует: `local_failure_modes`, `latency_budget_ms`, `fallback_behavior`. Нарушение хотя бы одного — рёбро реклассифицируется в sync_rpc или async_event.

### Принцип 4 — pipeline.db как связующее звено

I3 и I4 пишут в `pipeline.db` через скрипты `pg_*` (I3) и `io_*` (I4). I0 создаёт `pipeline.db` и базовые таблицы если они отсутствуют, затем расширяет схему для I3/I4 и обновляет CLI-скрипты. I5 и I6 читают pipeline.db.

### Принцип 5 — Immutability и artifact lifecycle

Downstream-агенты не изменяют upstream-артефакты напрямую. Любое изменение идёт через replay, patch или upstream_signal с записью в control plane. Узкое lifecycle-исключение: I24 при переходе в `implementation_snapshot` сам атомарно архивирует stale `spike_execution_context.yaml`, если доказано отсутствие открытых `architecture_global` spikes; содержимое файла не редактируется, исходный SHA256 и archive path фиксируются в run event. Все финальные артефакты несут `schema_version` и `content_hash`.

```
Artifact status:  draft → reviewed → accepted → frozen
                                   ↓ (upstream signal)
                              superseded → новая draft-версия
```

---

## 3. Ростер агентов (25 агентов)

### Pre-step

```
I0   Bootstrap + Schema Migration  [однократный; создаёт pipeline.db + базовые таблицы если нет; расширяет схему; обновляет CLI-скрипты]
```

### Подслой A — Technology (I1–I2)

```
I1   Technology Researcher          [батчевый; домены из technology_domain_registry]
I2   HITL: Architect Interview      [человек фиксирует технологические выборы и оси]
```

### Подслой B — Фундаментальная модель (I3–I5)

```
I3   Process & Causality Map        [процессы, causality, execution_location]
I4   Invariants & Ownership         [сущности, authority model, инварианты, sync rules]
I5   Interaction Semantics          [sync_rpc | async_event | on_device_call с 5 условиями]
```

### Подслой C — Архитектурный синтез (I6–I7)

```
I6   Architecture Synthesis         [initial: draft + hooks; patch run: final; spike_candidates с provenance_category + impact_radius]
I7   Causal Map Builder             [modes: build_review_graph | architecture_final_graph | task_trace_graph]
```

### Подслой D — Reviews + Trade-off (I8–I15, I16, I17)

Порядок исполнения внутри подслоя:

```
(параллельно)
  I8   Architecture Reviewer: Reliability
  I9   Architecture Reviewer: Simplicity
  I10  Architecture Reviewer: Maintainability
  I11  Architecture Reviewer: Cost
  I12  Architecture Reviewer: Performance
  I13  Architecture Reviewer: Scalability
  I14  Security Review              [findings + optional upstream_signal]
  I15  Ethics & Legal Review        [findings + optional upstream_signal]
(последовательно)
  I16  Architecture Conflict Resolver  [aggregates findings; применяет axis weights из I2 для авто-гашения конфликтов; к I17 — только неразрешимые]
  I17  Trade-off HITL                  [always-on; scope restriction; может выдать layer_rollback_request.yaml]
```

### Подслой E — Специальные reviews (I18–I19)

```
I18  Observability Architect   [развивает observability_design_hooks из I6; upstream signal если нужно]
I19  Deployment Architect      [развивает deployability_design_hooks из I6; upstream signal если нужно]
```

### Подслой F — Task Graph (I20–I24)

```
I20  Task Tree Builder               [строгая топологическая сортировка; code задачи blocked_by research при зависимости от spike; decomposition_units; human_action для внешних ручных действий]
I21  Task Spec Agent                 [task_spec расширенная схема; data_loss_risk: true → requires_human_review: true, accepted_risk_id: null; human_action contract]
I22  HITL: Tree Review + Risk Acceptance  [decomposition challenge; явное принятие риска data_loss_risk: true → заполняет accepted_risk_id; review blocking/risky human_action]
I23  Task Graph QA                   [coverage matrix; provenance; spikes; data_loss_risk gate: accepted_risk_id not null; secret hygiene для human_action]
I24  Gatekeeper & Publisher          [i24_publish_mode: research_only_snapshot | implementation_snapshot; tasks.db включает external_manual задачи; frozen_snapshot → J]
```

---

## 4. Статус промптов

| Агент | Файл | Статус |
|---|---|---|
| **I0** | `I0. Schema Migration.md` | ✅ написан |
| I1 | `I1. Technology Researcher.md` | ✅ существует; обновить: +4 домена + H14 bindings |
| I2 | `I2. HITL Architect Interview.md` | ✅ существует; проверить совместимость |
| I3 | `I3. Process Causality Map.md` | ✅ существует; обновить: execution_location, Mode A/B, ChatInlineCommit |
| I4 | `I4. Invariants Ownership.md` | ✅ существует; обновить: authority model |
| I5 | `I5. HITL Invariants Review.md` | ⚠️ УСТАРЕЛ — перезаписать как Interaction Semantics |
| I6 | `I6. Architecture Synthesis.md` | ✅ написан |
| I7 | `I7. Causal Map Builder.md` | ✅ написан |
| **I8** | `I8. Architecture Reviewer - Reliability.md` | ✅ написан |
| **I9** | `I9. Architecture Reviewer - Simplicity.md` | ✅ написан |
| **I10** | `I10. Architecture Reviewer - Maintainability.md` | ✅ написан |
| **I12** | `I12. Architecture Reviewer - Performance.md` | ✅ написан |
| **I13** | `I13. Architecture Reviewer - Scalability.md` | ✅ написан |
| **I11** | `I11. Architecture Reviewer - Cost.md` | ✅ написан |
| **I14** | `I14. Security Review.md` | ✅ написан |
| **I15** | `I15. Ethics & Legal Review.md` | ✅ написан |
| **I16** | `I16. Architecture Conflict Resolver.md` | ✅ написан |
| **I17** | `I17. Trade-off HITL.md` | ✅ написан |
| **I18** | `I18. Observability Architect.md` | ✅ написан |
| **I19** | `I19. Deployment Architect.md` | ✅ написан |
| **I20** | `I20. Task Tree Builder.md` | ✅ написан |
| **I21** | `I21. Task Spec Agent.md` | ✅ написан |
| **I22** | `I22. HITL Tree Review + Risk Acceptance.md` | ✅ написан |
| **I23** | `I23. Task Graph QA.md` | ✅ написан |
| **I24** | `I24. Gatekeeper & Publisher.md` | ✅ написан |

---

## 5. Ключевые проектные решения

### 5.0 Control Plane — pipeline_run

`i_layer_run.yaml` — служебный файл состояния I-слоя. Читается и обновляется каждым агентом.

```yaml
pipeline_run:
  run_id: I-run-20260617-001
  schema_version: "1.0"
  source_gate: h15_gate_decision
  started_at: <timestamp>
  current_stage: I6

  artifacts:
    - artifact_id: ARTIFACT-I6-DRAFT
      path: system_architecture.draft.yaml
      producer_agent: I6
      status: draft               # draft | reviewed | accepted | superseded | frozen
      input_hashes:
        - path: process_causality_map.yaml
          hash: sha256:<hash>
      content_hash: sha256:<hash>
      supersedes: null

  gates:
    - gate_id: GATE-PRE-I6
      label: "I0–I5 complete; technology decisions made; no blocking open_questions"
      required_artifacts:
        - i0_migration_report.yaml          # I0: all_passed=true
        - technology_decisions.yaml         # I2: axes + weights (normalized 0–1)
        - process_causality_map.yaml        # I3
        - invariants_ownership.yaml         # I4
        - interaction_semantics.yaml        # I5
        - assumptions.yaml                  # I3–I5: initial entries
      blocking_conditions:
        - i0_migration_report.yaml#all_passed == false
        - open_questions where blocking_level=blocks_architecture and status=open
      passed_at: null

    - gate_id: GATE-PRE-I24-RESEARCH_ONLY
      label: "Research pipeline complete; spike context ready; no impl tasks"
      required_artifacts:
        - system_architecture.draft.yaml
        - spike_candidates.yaml
        - spike_execution_context.yaml
        - task_tree.yaml                     # только research branch
        - task_specs/<research_task_id>.yaml  # task_spec для каждой research-задачи
        - i23_task_graph_qa_report.yaml       # mode: research_snapshot_qa
      blocking_conditions:
        - open_questions where blocking_level=blocks_architecture and status=open
        - task_tree.yaml#spike_task_mapping missing entry for any architecture_global spike
        - any task in task_tree where task_type != research
        - spike_execution_context.allowed_use != research_only
        - any research task_spec missing spike_id
        - any research task_spec missing open_question_id
        - i23_task_graph_qa_report.status != passed
      allows:
        - frozen_snapshot.research_only
        - tasks where task_type=research and execution_phase=strict_first
      passed_at: null

    - gate_id: GATE-PRE-I24-FULL_IMPLEMENTATION
      label: "All reviews done; full task graph ready; no blocking spikes or open risks"
      required_artifacts:
        - i17_hitl_decision_log.yaml
        - architecture_decisions.yaml
        - system_architecture.final.yaml
        - observability_spec.yaml
        - deployment_spec.yaml
        - causal_graph.db               # version: final, mode: task_trace_graph
        - task_tree.yaml
        - task_specs/                   # все листовые задачи
        - i23_task_graph_qa_report.yaml
        - coverage_matrix.yaml
        - assumptions.yaml
      blocking_conditions:
        - spike_candidate where blast_radius=architecture_global and status=open
        - coverage_matrix completeness_check any=false
        - assumption where validation_required=true and status not in [validated, accepted_risk]
        - causal_graph.version != final
        - causal_graph.mode != task_trace_graph
        - i23_task_graph_qa_report.status != passed
        - any task_spec missing required provenance per provenance_minimum_by_task_type (§5.17)
        - any code.migration task where data_loss_risk=true and accepted_risk_id=null
        - any required_artifact where content_hash is null
      allows:
        - full tasks.db with all implementation tasks executable
      passed_at: null

  replay_log:
    - replay_id: REPLAY-001
      source_agent: I14
      signal_type: security_constraint
      target_agent: I6
      reason: "..."
      affected_artifacts: [system_architecture.draft.yaml]
      affected_reviews: []
      completed_at: null
```

**Правило обновления:** агент пишет в `i_layer_run.yaml` при создании артефакта, смене статуса, прохождении gate, записи upstream signal.

**Параллельная запись (I8–I13, I14, I15):** при параллельном исполнении агенты не пишут напрямую в `i_layer_run.yaml`. Каждый агент записывает события в отдельный файл:

```yaml
parallel_agents_write_policy:
  direct_write_to_i_layer_run: false
  write_event_file: true
  event_file_path: run_events/<agent_id>-<timestamp>.yaml
  merge_by: next_sequential_agent   # I16 агрегирует run_events/* перед записью в i_layer_run.yaml
```

I16 — первый последовательный агент после параллельного блока — выполняет merge `run_events/` перед записью собственных findings.

**Политика merge run_events:** I16 не игнорирует битые или неполные файлы событий.

```yaml
run_event_merge_policy:
  invalid_event_file:
    action: fail_parallel_block       # параллельный блок считается незавершённым
  duplicate_artifact_id:
    action: fail_merge
  duplicate_finding_id:
    action: fail_merge
  missing_content_hash:
    action: fail_merge
  agent_finished_without_event_file:
    action: fail_parallel_block       # отсутствие файла = агент не завершился корректно

  post_merge_lifecycle:
    action: archive                   # файлы перемещаются, не удаляются — для audit
    archive_path: run_events/archive/<run_id>/
    trigger: after_successful_write_to_i_layer_run
    on_partial_restart:
      # human-run cleanup step удаляет старые run_events/<agent_id>-*.yaml ДО повторного запуска агента
      action: delete_stale_events_for_restarted_agents
      stale_criteria: agent_id in restarted_set AND run_id matches current run
      # предотвращает подтягивание устаревших findings от предыдущего прогона I12/I14
```

### 5.1 I0 — Bootstrap + Schema Migration

**Целевые изменения в pg_* (I3):**
- `processes`: добавить `primary_location TEXT`
- `process_steps`: добавить `execution_location TEXT`
- `pg_add_process.py`: `--primary_location` (default=None)
- `pg_add_step.py`: `--execution_location` (default=None)

**Целевые изменения в io_* (I4):**
- `io_entities`: добавить `authoritative_location TEXT`, `conflict_resolution_strategy TEXT`, `conflict_resolution_condition TEXT`, `write_authority TEXT`, `sync_requirement TEXT`, `offline_write_allowed INTEGER`, `server_confirmation_required INTEGER`
- `io_invariants`: расширить CHECK для `invariant_type` — добавить `'sync'`
- `io_add_entity.py`: все новые поля как необязательные args (default=None/False)

**Bootstrap:** если `pipeline.db` или базовые таблицы отсутствуют — вызывает `pg_create_db.py` и `io_create_tables.py` (оба идемпотентны). Fresh DB: bootstrap в temp-файл → `os.replace()`. Existing DB с missing tables: prebootstrap-backup → restore on failure.

**Миграция:** Idempotency check (`PRAGMA table_info`) выполняется **до** открытия транзакции. Все `ALTER TABLE ADD COLUMN` выполняются внутри единого `BEGIN EXCLUSIVE TRANSACTION` — при любом исключении `ROLLBACK` полностью откатывает изменения. Выход: `i0_migration_report.yaml`. `i_layer_run.yaml` инициализируется только при `all_passed: true`.

**Обязательные smoke tests:** `i0_migration_report.yaml` включает результат проверок. I0 завершается ошибкой при `all_passed: false`. I1/I3/I4 стартуют только при `all_passed: true`.

```yaml
i0_validation:
  checks:
    - old_pg_add_process_call_still_works   # вызов только со старыми аргументами
    - old_pg_add_step_call_still_works
    - old_io_add_entity_call_still_works
    - new_columns_exist_in_schema
    - new_optional_args_written_when_provided
    - migration_is_idempotent               # повторный запуск без ошибок и без дублей
  all_passed: true | false
```

### 5.2 Батчевый режим I3

**Mode A** (батч): N историй → pg_add_process, pg_add_chain, pg_add_step → progress.  
**Mode B** (синтез): все батчи → читать pipeline.db → `process_causality_map.yaml`.

В Mode A разрешены `pg_add_cross_connection.py` для межпроцессных связей из предыдущих батчей. Лимит: 20 историй или ~8000 слов.

### 5.3 Условный HITL перед I6

I5 считает `blocking_open_questions` — только вопросы с `blocking_level: blocks_architecture`.

```
blocking_open_questions == 0  → I5 → I6 напрямую
blocking_open_questions  > 0  → status: awaiting_clarification → человек отвечает →
                                 resolved_open_questions.yaml → I6 читает как optional input
```

### 5.4 open_question классификация

Каждый open_question несёт тип, resolution_mode и blocking_level.

```yaml
open_question:
  question_id: OQ-001
  question: "..."
  made_by: I3 | I4 | I5 | I6
  type: technical_unknown | architecture_choice | domain_fact | product_policy |
        legal_security_constraint
  resolution_mode: spike_allowed | architect_decision_allowed | assumption_allowed |
                   human_required
  blocking_level: blocks_architecture | blocks_task_generation |
                  blocks_specific_component | non_blocking
  affected_elements: [...]
  status: open | resolved | converted_to_spike | converted_to_assumption | accepted_risk
```

**Жёсткое правило конверсии:**

| type | resolution_mode | если unresolved → |
|---|---|---|
| `technical_unknown` | `spike_allowed` | `spike_candidate` в I6 |
| `architecture_choice` | `architect_decision_allowed` | HITL I2 или I17 |
| `domain_fact` | `assumption_allowed` | запись в `assumptions.yaml` |
| `product_policy` | `human_required` | `blocking_hitl` или явный `accepted_risk` |
| `legal_security_constraint` | `human_required` | `blocking_hitl` или явный `accepted_risk` |

**Примеры запрещённой конверсии в spike:**
- "Задача offline-создания видима на другом устройстве до sync?" — product_policy, не technical_unknown
- "Какие данные считаются sensitive?" — legal_security_constraint
- "Может ли пользователь вручную переопределять solver?" — product_policy

**Запрещено:** I6 продолжает при наличии unresolved `blocks_architecture` вопросов любого типа.

**Оптимистичный сценарий выполнения spike:**

Архитектура считается валидной до тех пор, пока spike не провален. I6 генерирует spike_candidate, I20 создаёт research-задачу в `batch_id: 0`, J исполняет. Поведение зависимых задач определяется `blast_radius` (§5.16): при `component` — зависимые impl-задачи материализуются с `blocked_by_spike`; при `architecture_global` — impl-задачи не материализуются вовсе до успешного закрытия spike.

Если J проваливает spike → `spike_rejection.yaml` → маршрутизация по §5.18 (Circuit Breaker). Маршрут зависит от `provenance_category` spike_candidate (§5.16).

### 5.5 Assumption Ledger

Агенты I3–I6 фиксируют осознанные допущения в `assumptions.yaml`. Не spike и не open_question — явный выбор в условиях неполной информации.

```yaml
assumptions:
  - assumption_id: ASM-I6-001
    made_by: I6
    statement: "Local task edits accepted immediately; sync later."
    reason: "Required for offline-first (INV-08)."
    confidence: medium    # high | medium | low
    blast_radius:
      - sync_protocol
      - conflict_resolution
      - task_state_machine
    validation_required: true
    validation_stage: I14   # кто должен проверить
    can_be_invalidated_by:
      - product decision about multi-device real-time visibility
      - security review (audit trail requirement)
      - spike result on CRDT feasibility
    status: pending_validation | validated | invalidated | accepted_risk
```

I14/I15/I18 читают `assumptions.yaml` и валидируют из своей области. Если допущение invalidated → upstream_signal в I6.

`assumptions.yaml` — обязательный input для I23 (QA) и I24 (gate: все `validation_required` должны быть `validated` или `accepted_risk`).

### 5.6 Unified Finding Schema

Все агенты I8–I13, I14, I15, I18, I19 используют единый формат finding. Это делает I16 надёжным агрегатором.

```yaml
finding:
  finding_id: FINDING-I12-003
  source_agent: I12
  axis: reliability | simplicity | maintainability | cost | performance | scalability |
        security | ethics_legal | observability | deployment
  severity: blocker | major | minor | note
  confidence: high | medium | low
  affected_elements:
    components: [solver_component]
    contracts: [HTTP-014]
    invariants: [INV-03]
    tasks: []                       # заполняется I21/I23 после task materialization / QA
  claim: "On-device solver has no latency bound on complex schedules."
  evidence: "process_causality_map.yaml#PROC_007 has no latency_budget annotation."
  recommendation: "Add latency_budget_ms to on_device_call in I5."
  tradeoff_required: false
  conflicts_with: []
  cross_ref_agents: []        # опционально: агенты, чьи findings пересекаются (например [I15]); I16 использует при агрегации
  required_architecture_change: null  # если нужно изменить I6 draft
  requires_human_decision: false
```

I16 читает все finding-файлы, группирует по `affected_elements`, выявляет конфликты между findings разных агентов, фильтрует дублирующиеся, формирует `architecture_conflicts.yaml` с реальными trade-offs для I17.

### 5.7 I17 — always-on HITL + scope restriction

I17 запускается **всегда** после I16.

```
Mode full        — I16 нашёл реальные trade-offs требующие human decision
Mode pass-through — I16 нашёл только шум; I17 фиксирует: review прошёл без предметных вопросов
```

**Scope restriction (критично):**
- **Может:** выбирать между явными options из I16 trade-off list
- **Может:** отклонить архитектуру и вернуть в I6 / I3 / I4 (через replay_log)
- **Не может:** добавить новое продуктовое или архитектурное требование без upstream routing
- Любое новое требование → upstream_message → соответствующий слой

Это предотвращает превращение I17 в неформальную точку переписывания архитектуры. Gate I18 не начинается без I17 sign-off.

### 5.8 Upstream signals — reviewers and structural failures

**Routing I14/I15:**
- **Основной путь:** I14 и I15 выдают findings (unified format §5.6) → I16 агрегирует → I17 принимает решение. Это обязательно — security и legal trade-offs должны входить в общий conflict resolution.
- **Прямой path:** если I14/I15 обнаруживают нарушение которое не укладывается в trade-off framework (например, фундаментальный compliance violation) → `upstream_signal` напрямую в I6.

**Routing I18/I19:**
- I18 и I19 развивают design hooks из I6 (§5.11). Если hook нельзя заполнить без структурного изменения → `upstream_signal` в I6.

```yaml
upstream_signal:
  source: I14 | I15 | I18 | I19
  target: I6
  target_prompt: "I6. Architecture Synthesis.md"
  signal_type: upstream_review_constraint
  nature: security_constraint | legal_constraint | architectural_constraint
  description: <что несовместимо>
  required_change: <минимальное изменение>
  source_refs: []
```

**Типы сигналов:**
- `I14` → `security_constraint`: "компонент X хранит PII без шифрования at-rest"
- `I15` → `legal_constraint`: "cloud_delete должен удалять, а не архивировать (retention policy)"
- `I18` → `architectural_constraint`: "компонент Y не поддаётся метрикам без структурного изменения"
- `I19` → `architectural_constraint`: "компонент Z не деплоится без изменения топологии"

**Механизм partial re-run:** `upstream_signal.yaml` (или `constraints_patch.yaml` при spike rejection) → человек запускает конкретный target prompt, указанный в signal file → target prompt читает сигнал как вход → I6 загружает предыдущий стейт + применяет патч → обновляет затронутые компоненты → I7 инкрементно обновляет causal_graph → запись в `replay_log`.

**Важно:** в I-layer нет фонового оркестратора. Любой replay/patch запускается человеком по конкретному prompt-specific signal. Сигнал обязан содержать `target_prompt`, `target`, `signal_type`, `required_change` и путь/ссылку на source artifact. Generic `next_owner: I-layer` недостаточен.

**Защита от бесконечных циклов: `max_upstream_loops: 2`.** Если после двух итераций upstream_signal ↔ I6 partial re-run консенсус не достигнут → конфликт принудительно эскалируется в I17 (HITL). I17 либо разрешает дополнительные итерации, либо формирует `layer_rollback_request.yaml` (§5.19).

**Полный перезапуск reviews после I6:** при любом изменении `system_architecture.draft.yaml` (результат upstream_signal или spike rejection) все агенты I8–I15 **перезапускаются с нуля**. Инкрементальное применение старых findings запрещено — это обеспечивает детерминированность итоговой review-картины.

**Routing I7 self-check failures:**

I7 не создаёт архитектурных решений и не исправляет upstream-артефакты. Если self-check провалился, I7 делает `ROLLBACK`, не публикует `causal_graph.db`, и пишет структурный failure-сигнал:

```yaml
i7_self_check_failure:
  source_agent: I7
  mode: build_review_graph | architecture_final_graph | task_trace_graph
  failure_type: self_check_failed
  blocking: true
  artifact_created: false
  failed_checks:
    - check_id: process_to_invariant
      target_agents: [I3, I4]
      affected_elements: [...]
  required_replay:
    - I3_or_I4_fix
    - I6_foundation_replay
    - I7_replay_same_mode
```

Это **не** `upstream_signal.yaml` I14–I19→I6. Это сигнал producer-агентам, которые владеют исходными данными графа.

Routing table:

| failed_check | target_agents |
|---|---|
| `story_requires_process` | I3 |
| `process_to_invariant` | I3 + I4 |
| `missing_invariant_node` | I4 |
| `missing_interaction_node` / `missing_interaction_group` | I5 |
| `missing_component_node` / `component_edges_invalid` | I6 |
| `missing_contract_or_api_binding_node` | I6, при H-layer conflict → prompt-specific signal к H-layer owner |
| `missing_spike_node` / `spike_without_affects_edges` | I6 |
| `task_traceability_gap` | I20 + I21 + I23 |

После исправления I3/I4/I5/I6 человек запускает следующий prompt по `next_prompt_signal.yaml`:

```
I6_foundation_replay_required → I6 trigger_C → I7 build_review_graph replay
```

Если target был только I6 (например, missing component), I6 применяет patch/replay напрямую и затем возвращает пайплайн в I7. Если target был I3/I4/I5, I6 всегда запускается после них, потому что `system_architecture.draft.yaml` является производным от foundational model.

### 5.9 I7 — три режима (build_review_graph / architecture_final_graph / task_trace_graph)

**Mode build_review_graph — I7 (после I6 initial):**
Строит полный граф из I3+I4+I5+I6 draft. Версия 1. Используется I8–I13, I14, I15.

```yaml
causal_graph_version: 1
mode: build_review_graph
covers: requirements → processes → invariants → interactions → components
```

**Mode architecture_final_graph — I7 (после I18/I19, перед I20):**
Добавляет к v1-графу: architecture decisions (I17), security/legal constraints (I14/I15), observability specs (I18), deployment specs (I19). Готовит граф как основу для task decomposition. Tasks и acceptance criteria ещё не добавлены.

```yaml
causal_graph_version: 2
mode: architecture_final_graph
covers: requirements → processes → invariants → interactions → components → arch_decisions → constraints → specs
```

**Mode task_trace_graph — I7 (после I23, перед I24):**
Добавляет к v2-графу: задачи из I20/I21, acceptance criteria из I23. Это финальная версия — полная трассировка для J.

```yaml
causal_graph_version: final
mode: task_trace_graph
full_trace_available: true
# J-слой может проследить: task_id → component → contract → interaction → invariant → process → story
```

J-слой получает только финальную версию `causal_graph.db`. Разделение режимов I7 устраняет противоречие: architecture_final_graph не содержит tasks (которых ещё нет), task_trace_graph не может идти до I23 (которая создаёт acceptance criteria).

**Lineage policy для `causal_graph.db`:** три режима I7 — это три разные artifact-family, даже если физический path один и тот же:

| mode | artifact_family | legacy alias |
|---|---|---|
| `build_review_graph` | `I7_BUILD_REVIEW_GRAPH` | `ARTIFACT-I7-V1` |
| `architecture_final_graph` | `I7_ARCHITECTURE_FINAL_GRAPH` | `ARTIFACT-I7-V2` |
| `task_trace_graph` | `I7_TASK_TRACE_GRAPH` | `ARTIFACT-I7-FINAL` |

`supersedes` разрешён только внутри той же `artifact_family` / того же `mode`. Cross-mode связь (`build_review_graph` → `architecture_final_graph` → `task_trace_graph`) записывается только как `derived_from`, `base_graph`, `invalidates`, `requires_rerun`, но не как `supersedes`. Если replay в `build_review_graph` выполняется после уже опубликованного `architecture_final_graph`, он обязан пометить финальный граф как invalidated/needs rerun (`requires_rerun: [I7_architecture_final_graph, I20, I21, I22, I23]` по ситуации), но не делать себя head для full-I23 gate.

Потребители обязаны выбирать head по требуемому `mode`/`artifact_family`, а не глобально по `path=causal_graph.db`. I23 full gate выбирает только `artifact_family=I7_ARCHITECTURE_FINAL_GRAPH`, `mode=architecture_final_graph`, `causal_graph_version=2`, затем сверяет `db_file_hash` выбранной записи с фактическим файлом `causal_graph.db`. Несовпадение hash означает, что физический файл заменён другим режимом и нужен новый I7 `architecture_final_graph`, а не fallback на старую запись.

**Ограничение идемпотентности I7 (task_trace_graph):** в режиме task_trace_graph I7 выполняет исключительно `INSERT task_node` и `LINK task_node TO existing_component_node / existing_contract_node`. Пересоздание, обновление или удаление уже существующих узлов (component, invariant, interaction, arch_decision) **запрещено**. Нарушение делает `content_hash` финального `causal_graph.db` недетерминированным — I24 не сможет верифицировать хеш при повторном прогоне.

**Self-check failure invariant:** любой I7 mode при failed self-check обязан создать `i7_self_check_failure.yaml`, записать replay event, оставить `causal_graph.db` непубликованным, и установить `current_stage: upstream_replay_required`.

### 5.10 I6 — Draft vs Final Architecture

```
I6 (initial run) → system_architecture.draft.yaml
I8–I15           → findings (unified format)
I16              → architecture_conflicts.yaml
I17              → architecture_decisions.yaml (с required_architecture_patch)
I6 (patch run)   → system_architecture.final.yaml
I24              → freezes final
```

`architecture_decisions.yaml` формат:

```yaml
architecture_decisions:
  - decision_id: ADR-I17-001
    conflict_id: CONFLICT-I16-003
    decision: "Use local event log as source of offline operations."
    rejected_options:
      - "Server-only task state"
      - "State snapshot sync only"
    rationale: "..."
    consequences: "..."
    required_architecture_patch:
      target: system_architecture
      patch_id: PATCH-I17-001
      affected_components: [local_event_log_component]
```

**J-слой читает одну финальную архитектуру** — `system_architecture.final.yaml`. Он не склеивает draft и decisions самостоятельно. `architecture_decisions.yaml` — только trace принятых решений.

```yaml
# system_architecture.final.yaml header:
schema_version: "1.0"
content_hash: sha256:<hash>
supersedes: system_architecture.draft.yaml
applied_decisions: [ADR-I17-001]
applied_patches: [PATCH-I17-001]
```

### 5.11 I6 — observability и deployability design hooks

I6 включает начальные hooks в `system_architecture.draft.yaml`. Это предотвращает ситуацию когда I18/I19 "вдруг обнаруживают" что архитектура непригодна — они проверяют и развивают уже заложенные hooks.

```yaml
observability_design_hooks:
  events_to_log:
    - solver_decision_result    # что solver предложил и почему
    - sync_conflict_detected
    - offline_event_created
    - local_only_mode_entered
  solver_decision_explainability:
    required: true
    mechanism: TBD_by_I18
  parser_privacy_redaction:
    applies_to: parser_input    # локальный парсер обрабатывает текст пользователя
    strategy: TBD_by_I15        # I15 заполняет с учётом legal

deployability_design_hooks:
  environments: [local_dev, staging, production]
  local_schema_upgrade_strategy: TBD_by_I19   # IndexedDB migration
  server_schema_upgrade_strategy: TBD_by_I19
  feature_flag_boundaries: TBD_by_I19
  rollback_boundaries: TBD_by_I19
  offline_event_log_backup_strategy: TBD_by_I19
```

I18 развивает `observability_design_hooks` → `observability_spec.yaml`.  
I19 развивает `deployability_design_hooks` → `deployment_spec.yaml`.

### 5.12 H14 решения как обязательный вход I-слоя

H14 зафиксировал решения в `h14_hitl_decision_log.yaml`. Архитектурные артефакты консолидированы в `h12_integration_spec.yaml` (H12). API-контракты (HTTP-011, HTTP-014, HTTP-003) — в `h9_contract_spec.yaml`. `h_layer_handoff.yaml` как единый consolidated файл не создаётся — I-слой читает эти артефакты напрямую.

**HITL-001 (платёж):** stripe_checkout_adapter (web, code.adapter) + platform_purchase_bridge (mobile, code.adapter, platform-owned). HTTP-011 — web path. Mobile purchase — platform/I-layer owned, не Elm. I1 исследует Stripe SDK + StoreKit/Google Play Billing как домен `payment_runtime`.

**HITL-002 (удаление):** local_delete_handler (on_device, code.domain_logic) + cloud_delete_service (server, code.adapter). После cloud_delete → `local_only_mode` как архитектурное состояние. I4 фиксирует cloud data entity: `canonical_store: server`, `offline_write_allowed: false`, `conflict_resolution: {strategy: server_wins, condition: on_delete}`.

**ID-002 (HTTP-014 ChatInlineCommit):** отдельный endpoint, не alias HTTP-003. I3 добавляет process step: on_device_call confirm → sync_rpc HTTP-014. I6 включает HTTP-014 в frozen_api_surface.

### 5.13 Дополнительные выходы I6 из H12 concerns

**`api_binding_spec.yaml`:** HTTP-011 (web + mobile path), HTTP-014, HTTP-003 — path, method, request_shape, success_statuses, error_statuses, retry_policy, auth_required.

**`on_device_bridge_contract.yaml`:** bootstrap sequence, update semantics, view-mode preference (local-only vs cloud-connected), local reset semantics (что сбрасывает `local_delete` и в каком порядке).

### 5.14 Coverage Matrix как обязательный gate

I23 строит `coverage_matrix.yaml`, I24 проверяет перед публикацией.

```yaml
coverage_matrix:
  user_story_to_process:          # каждая story → хотя бы один process
  process_to_invariant:           # каждый process → хотя бы один invariant ИЛИ explicit_no_invariant_reason
  invariant_to_component:         # каждый invariant enforced компонентом/контрактом/тестом
  interaction_to_contract:        # каждый interaction semantic → contract или task
  component_to_task:              # каждый компонент → task или explicit no-op reason
  task_to_acceptance_criteria:    # каждая task_spec → непустые acceptance_checks
  h_layer_constraint_to_arch:     # каждый frozen H-layer constraint → архитектурный элемент

  completeness_check:
    no_story_without_process: true
    no_invariant_without_enforcement: true
    no_interaction_without_contract: true
    no_component_without_task: true
    no_task_without_provenance: true
    no_h_constraint_unaddressed: true
```

Любое `false` — gate failure для I24.

### 5.14a I23 deterministic upstream return routing

When I23 finishes with `status: failed`, it must not write a composite or pseudo-agent value such as
`I6_I20`, `I6_or_I20`, `UPSTREAM`, or `I-layer` into `i_layer_run.yaml#next_agent`.
I23 must write exactly one concrete prompt agent as `next_agent` and must also write
`i23_upstream_return_signal.yaml` with a full ordered remediation plan.

I23 classifies each gate failure by owner:

| I23 finding | Primary owner rule |
|---|---|
| `assumption_pending_validation` | use `assumptions.yaml#assumptions[*].validation_stage`; fallback `I6` only if the stage is absent or invalid |
| `invariant_enforcement_missing`, `component_set_mismatch`, `missing_component_node` | `I6` |
| `provenance_ref_not_found`, task-tree coverage/provenance gaps, missing task for component/PRD/interaction | `I20` |
| task_spec materialization errors, rollback_strategy/spec field errors, acceptance check format errors | `I21` |
| data_loss_risk acceptance, human_action review/evidence contract | `I22` |
| repeated `secret_value_present` with `escalation_required: true` | manual stop; `blocked_i23_manual_escalation`, `next_agent: null` |
| unknown I23 failure code | `I6` fallback with `failure_scope: unclassified_i23_gate_failure` |

If several owners are present, I23 chooses the earliest concrete owner by pipeline order as
`next_agent`, and stores the rest in
`i23_upstream_return_signal.yaml#routing_decision.ordered_agent_plan`.
This is the only legal way to represent mixed ownership. The signal is actionable input for the
first owner and an audit plan for later owners.

Required replay chains after the primary owner:

```yaml
i23_return_replay_chains:
  if_primary_in_or_before_I5:
    chain: [<primary>, I6, I7_build_review_graph, I8_I15_full_restart, I16, I17, I18_I19_parallel, I7_architecture_final_graph, I20, I21, I22, I23]
  if_primary_I6:
    chain: [I6, I18_I19_parallel, I7_architecture_final_graph, I20, I21, I22, I23]
  if_primary_I15:
    chain: [I15, I16, I17, I18_I19_parallel, I7_architecture_final_graph, I20, I21, I22, I23]
  if_primary_I20:
    chain: [I20, I21, I22, I23]
  if_primary_I21:
    chain: [I21, I22, I23]
  if_primary_I22:
    chain: [I22, I23]
```

Upstream agents that receive `i23_upstream_return_signal.yaml` process only their own
`ordered_agent_plan[]` item(s), mark or report those items as addressed, and then route to the next
agent in `ordered_agent_plan` or to the first still-needed step in
`required_chain_after_primary`. They must not fix another owner's item silently.

**Два режима I23:** при полном пайплайне I23 использует `causal_graph.db` (v2, mode: architecture_final_graph) для проверки трассировки task → component → invariant. При `research_snapshot_qa` (early-spike route §5.22) `causal_graph.db` **недоступен** — I7 (build_review_graph и architecture_final_graph) не запущен. В этом режиме I23 работает исключительно с YAML-артефактами: `spike_execution_context.yaml`, `task_specs/`, `spike_candidates.yaml`. Попытка обратиться к `causal_graph.db` в research_snapshot_qa — ошибка конфигурации.

**Исключение для `process_to_invariant`:** процесс без invariant проходит проверку при наличии поля `explicit_no_invariant_reason: <text>` (допустимые значения: `"navigation-only"`, `"orchestration-proxy"`, `"read-only aggregation"`). Пустое поле — gate failure. Это исключение предотвращает выдумывание слабых инвариантов ради прохождения gate.

Если это нарушение впервые обнаружено I7, оно маршрутизируется через `i7_self_check_failure.yaml` к I3/I4: I3 может добавить допустимое `explicit_no_invariant_reason`; I4 может добавить реальный invariant mapping. I7 не выбирает между этими вариантами самостоятельно.

**Структура записи `h_layer_constraint_to_arch`:**

```yaml
h_layer_constraint_entry:
  constraint_id: H-API-011
  source_ref: h9_contract_spec.yaml#HTTP-011
  treatment:
    - implemented_as_component      # компонент в system_architecture
    - implemented_as_contract       # запись в api_binding_spec.yaml
    - implemented_as_adapter        # code.adapter задача
    - constrained_by_platform       # внешнее ограничение (App Store, OS)
    - explicitly_not_applicable     # не применимо + reason: <text>
  arch_refs: [stripe_checkout_adapter, api_binding_spec.yaml#HTTP-011]
  task_refs: [T-042, T-043]
  verification_refs: [i23_task_graph_qa_report.yaml#H-API-011]
```

`treatment` должен содержать хотя бы один элемент. `explicitly_not_applicable` требует `reason: <text>`. Пустой `arch_refs` при treatment != `explicitly_not_applicable` — gate failure.

### 5.15 frozen_snapshot — manifest + validation

```yaml
frozen_snapshot:
  snapshot_id: SNAP-I-001
  snapshot_mode: research_only | implementation    # определяет набор validation правил
  created_at: <timestamp>
  source_run_id: I-run-20260617-001
  i_layer_version: I-R2-2026-06-17

  # --- поля для snapshot_mode: implementation ---
  final_architecture:
    path: system_architecture.final.yaml
    hash: sha256:<hash>
    applied_decisions: [ADR-I17-001]

  tasks:
    db_path: tasks.db
    db_hash: sha256:<hash>
    task_count: 142
    unresolved_architecture_blocking_spikes: 0

  causal_graph:
    path: causal_graph.db
    hash: sha256:<hash>
    version: final

  # --- поля для snapshot_mode: research_only (вместо final_architecture + tasks + causal_graph) ---
  # research_architecture_context:
  #   spike_execution_context_path: spike_execution_context.yaml
  #   spike_execution_context_hash: sha256:<hash>
  #   source_draft: system_architecture.draft.yaml
  #   source_draft_hash: sha256:<hash>
  #   spike_ids: [SPIKE-001]
  # research_tasks:
  #   db_path: tasks.db
  #   task_count: 1       # только research-задача
  #   task_types_present: [research]
  # causal_graph: absent  # I7 (build_review_graph/architecture_final_graph) не запущены; causal_graph.db не существует

  # --- included_artifacts для snapshot_mode: implementation ---
  included_artifacts:
    - path: system_architecture.final.yaml
      hash: sha256:<hash>; status: frozen
    - path: api_binding_spec.yaml
      hash: sha256:<hash>; status: frozen
    - path: on_device_bridge_contract.yaml
      hash: sha256:<hash>; status: frozen
    - path: observability_spec.yaml
      hash: sha256:<hash>; status: frozen
    - path: deployment_spec.yaml
      hash: sha256:<hash>; status: frozen
    - path: causal_graph.db
      hash: sha256:<hash>; version: final; mode: task_trace_graph
    - path: tasks.db
      hash: sha256:<hash>
    - path: task_specs/
      hash: sha256:<hash>   # aggregate hash
    - path: coverage_matrix.yaml
      hash: sha256:<hash>; status: frozen

  # --- included_artifacts для snapshot_mode: research_only ---
  # included_artifacts:
  #   - path: system_architecture.draft.yaml
  #     hash: sha256:<hash>
  #   - path: spike_candidates.yaml
  #     hash: sha256:<hash>
  #   - path: spike_execution_context.yaml
  #     hash: sha256:<hash>
  #   - path: tasks.db          # только research tasks
  #     hash: sha256:<hash>
  #   - path: task_specs/<T-000>.yaml
  #     hash: sha256:<hash>
  #   - path: i23_task_graph_qa_report.yaml    # mode: research_snapshot_qa
  #     hash: sha256:<hash>
  #
  # forbidden_in_research_only:
  #   - system_architecture.final.yaml
  #   - api_binding_spec.yaml
  #   - on_device_bridge_contract.yaml
  #   - observability_spec.yaml
  #   - deployment_spec.yaml
  #   - any task where task_type != research

  accepted_risks:
    - id: AR-001
      risk_kind: accepted_risk | architectural_debt | deferred_decision | known_limitation
      description: <текст>
      accepted_by: <role>
      expiry_condition: <условие снятия риска>
      follow_up_required: true | false
      follow_up_task_id: null   # J создаёт задачу для architectural_debt и deferred_decision

  # --- validation для snapshot_mode: implementation ---
  validation:
    all_required_artifacts_present: true
    no_unresolved_blocking_questions: true
    no_architecture_blocking_spikes: true
    coverage_matrix_complete: true
    all_assumptions_validated_or_accepted: true
    content_hashes_verified: true

  # --- validation для snapshot_mode: research_only ---
  # validation:
  #   content_hashes_verified: true
  #   no_unresolved_blocking_questions: true
  #   architecture_global_spikes_present: true        # spike существует и имеет research_task_id
  #   only_research_tasks_published: true
  #   implementation_tasks_absent_for_spike_area: true
  #   system_architecture_final_absent: true          # J не должен видеть final; только draft через spike_execution_context.yaml
```

J-слой проверяет хеши перед началом работы. При `snapshot_mode: research_only` J читает `spike_execution_context.yaml` вместо `system_architecture.final.yaml`.

### 5.16 Spike blast radius

```yaml
spike_candidate:
  spike_id: SPIKE-001
  question: "Can CRDT-based merge work for our task structure?"
  type: technical_unknown      # только technical_unknown может стать spike (§5.4)
  provenance_category: upstream_requirement | i_layer_initiative
  # upstream_requirement: spike порождён требованием из H/D-слоёв (h9_contract_spec, h14_hitl_decision_log, prd.index)
  # i_layer_initiative: spike порождён архитектурным решением, принятым внутри I-слоя
  impact_radius:               # компоненты, которые затронет провал spike (component IDs)
    - solver_component
    - local_event_log_component
  affected_process_ids:        # процессы из I3 causality map, затронутые spike
    - PROC_007
    - PROC_012
  affected_invariant_ids:      # инварианты из I4, затронутые spike
    - INV_003
  affected_interaction_ids:    # interaction semantics из I5, затронутые spike
    - IS_004
  blast_radius: architecture_global | component | optimization
  dependent_tasks: [T-034, T-035]
  publish_policy:
    architecture_global: defer_implementation  # I20 не материализует impl-задачи; только research
    component: block_dependent_tasks           # независимые задачи публикуются
    optimization: publish_with_risk_flag       # публикуем всё с accepted_risk
  research_task_id: T-000      # research-задача создаётся всегда в batch_id: 0
```

**Практическое правило для I24 (`i24_publish_mode`):**
- `architecture_global` spike → `research_only_snapshot`: I20 **не материализует** implementation-задачи для зависимой области; только research-задача в `batch_id: 0`. После успешного spike → resume per §5.22 full implementation path → GATE-PRE-I24-FULL_IMPLEMENTATION → `implementation_snapshot`
- `component` spike → `implementation_snapshot`: независимые задачи публикуются; зависимые материализованы с `blocked_by_spike` (существуют в tasks.db, но J не берёт в работу)
- `optimization` spike → `implementation_snapshot` с risk flag в `accepted_risks`

### 5.17 task_spec — расширенная схема + leaf task criteria

**Критерий "листовой задачи" (I20 применяет до создания task_spec):**

Задача является допустимой листовой если одновременно:
1. Имеет один основной результат: файл, contract operation, schema step, surface state или surface flow; модуль и surface целиком не являются листовой единицей
2. Относится к одному `task_type`
3. Имеет явно перечисленные входные артефакты
4. Имеет проверяемые `acceptance_checks` (не абстрактные)
5. Имеет provenance к хотя бы одному process / invariant / interaction / component
6. Не требует отдельного архитектурного решения (такой вопрос → open_question или HITL)
7. Не содержит внутри независимых подзадач которые можно выполнять параллельно. Несколько process_ids, primary invariants, providers/platforms/surfaces, contracts/API bindings или независимых entity groups означают обязательный split.
8. Может быть проверена через `validation_commands` или явный критерий
9. Имеет понятные failure/rollback условия если затрагивает данные, инфраструктуру или миграции

`component_id` — ownership boundary, а не leaf boundary. I20 строит `decomposition_units[]`; листовая задача соответствует одному unit, а компонент закрывается несколькими task refs. Одна задача на весь компонент допустима только для механически тривиального компонента: один process, один primary invariant, один interface/contract, одна execution surface, без platform/UI split и без отдельных PRD/story refs.

После построения `decomposition_units[]` I20 выполняет mandatory minimality pass: для каждого unit пытается разбить его дальше и заполняет `minimality_evidence`, почему любое разбиение теряет независимое проверяемое постусловие, нарушает атомарность выполнения/отката или требует upstream архитектурного решения. Unit без `minimality_evidence` не может породить задачу.

Дополнительные правила гранулярности: `code.adapter` строится per contract operation (endpoint, bridge call, event handler, webhook), а не per contract; `code.domain_logic` строится per process step/stage, если у steps различимые постусловия; `code.presentation` строится per surface state / user flow, если acceptance criteria различаются. Если upstream process/contract/surface слишком крупный и I20 не может разделить его без нового решения, он фиксирует `granularity_gap` с owner I3/I5/I6 вместо крупного leaf task.

I20 публикует `granularity_report` для I22: tasks_per_component, components_with_less_than_3_tasks, avg/max hints per task, mechanically computed units_lower_bound и units_actual. Если units_actual меньше lower bound, каждое слияние обязано иметь `minimality_evidence`.

**Минимальные требования к provenance по типу задачи:**

```yaml
provenance_minimum_by_task_type:
  code.domain_logic:
    required: [component_id, "process_id или invariant_id", architecture_ref]
  code.adapter:
    required: [component_id, "contract_id или api_binding_ref", interaction_semantic_id]
  code.presentation:
    required: ["surface_id или surface_ref", platform_refs, "story_id или requirement_id", "component_id или interaction_semantic_id"]
  code.contract:
    required: [interaction_semantic_id, "api_binding_ref или contract_ref"]
  code.migration:
    required: [entity_id, "invariant_id или sync_requirement", rollback_strategy, data_loss_risk]
    # data_loss_risk: true|false — обязательное поле
    # если true → задача обязана иметь:
    #   mitigation_plan: <текст, не null>
    #   requires_human_review: true
    #   accepted_risk_id: null | AR-xxx    # null до явного HITL-принятия риска
    # accepted_risk НЕ создаётся I22 автоматически — только после явного принятия
  qa:
    required: [acceptance_criteria_ref, "covered_task_ids или covered_invariant_ids"]
  research:
    required: [spike_id, open_question_id]
  infrastructure:
    required: ["component_id или deployment_spec_ref"]
  config:
    required: ["component_id или contract_id"]
  code.orchestration:
    required: [process_id, component_ids]
  human_action:
    required: [external_system, action_type, actor_role, evidence_required]
    note: >
      human_action покрывает только действия вне репозитория, которые агент не может
      выполнить сам: аккаунт/проект в cloud console, app-store/payment console,
      ручная настройка webhook, выдача токена через secret store. Секретные значения
      запрещено писать в task_spec, frozen_snapshot, run_events и git; разрешены только
      secret_ref / vault_path / env_var_name / fingerprint.
```

I23 проверяет каждую task_spec по этой матрице. Несоответствие — gate failure.

**Особое правило для `code.migration` с `data_loss_risk: true`:** I21 (Task Spec Agent) обязан установить `risk_level: high`, заполнить `mitigation_plan` (не null) и `requires_human_review: true`. `accepted_risk` появляется **только после явного HITL-принятия риска** — I21 не создаёт его автоматически; поле `accepted_risk_id` остаётся `null` до принятия. I23 проверяет: если `data_loss_risk: true` и `accepted_risk_id: null` → gate failure для GATE-PRE-I24-FULL_IMPLEMENTATION. Поверхностный rollback_strategy (например, "удалить добавленную колонку") без описания поведения уже записанных данных — gate failure в I23.

**Единственный легальный HITL-узел принятия риска — I22.** I22 запускается после I21 (порядок: I20 → I21 → I22 → I23) и имеет доступ к полным task_specs. В рамках HITL I22 человек:
1. Проверяет декомпозицию (decomposition challenge — гранулярность, пропуски)
2. Явно принимает или отклоняет риск для каждой задачи с `data_loss_risk: true`
3. При принятии: задача получает `accepted_risk_id: AR-xxx`; I22 записывает accepted_risk в `i22_tree_review_log.yaml`

I17 и оркестратор **не вправе** создавать `accepted_risk_id` для `data_loss_risk` задач в обход I22 — это нарушает хронологическую целостность HITL-цепочки.

**Формат task_spec:**

```yaml
task_id: T-001
task_type: research | infrastructure | config | human_action | code.domain_logic |
           code.adapter | code.presentation | code.migration | code.contract |
           code.orchestration | qa
component_id: solver_component    # из system_architecture.final.yaml
decomposition_unit_id: DU-...      # из task_tree.yaml#decomposition_units; null только если тип задачи не порождён unit
scope: <краткое описание в 1–2 предложениях>

implementation_scope:
  - <что входит: конкретный результат 1>
out_of_scope:
  - <что явно не входит: исключение 1>
files_allowed_to_touch:           # J-агент не трогает файлы за пределами этого списка
  - src/solver/
  - tests/solver/

depends_on: [T-000]
parallel_group: PG-003       # null если строго последовательная в batch
batch_id: BATCH-03           # execution wave (см. ниже)
sequence_order: 3            # порядок внутри batch_id

acceptance_checks:
  - <проверяемый критерий 1>
validation_commands:
  - command: "elm-test tests/solver/"
    expected: "Test run passed"

provenance:
  process_ids: [PROC_001]
  invariant_ids: [INV_001]
  interaction_semantic_id: IS_001
  architecture_ref: system_architecture.final.yaml#component/solver
  architecture_decision_ids: [ADR-I17-001]

artifact_refs:
  - api_binding_spec.yaml#HTTP-014
  - on_device_bridge_contract.yaml#bootstrap_sequence

blocked_by_spikes: []       # spike_ids если результат зависит от spike
risk_level: low | medium | high
rollback_strategy: <описание или null для non-destructive>

# только для task_type: human_action
human_action:
  action_type: cloud_console_setup | account_registration | secret_provisioning |
               app_store_console | payment_console | dns_or_domain_setup |
               legal_policy_decision | other_manual_external
  external_system: stripe | aws | gcp | apple_app_store | google_play | github | other
  actor_role: owner | admin | security_owner | billing_owner | legal_owner
  instructions:
    - "<короткий шаг, который человек должен выполнить вне репозитория>"
  required_inputs:
    - "<что нужно человеку до начала действия>"
  produces:
    - kind: secret_ref | external_resource_ref | approval_ref | account_ref
      name: "<имя результата без секретного значения>"
      target_store: vault | ci_secrets | cloud_secret_manager | env_local | external_console
  evidence_required:
    - secret_store_reference
    - external_resource_id
  secrets_policy: never_write_secret_value_to_repo
```

**batch_id как execution wave:**

```yaml
batch:
  batch_id: BATCH-004
  meaning: "After local storage schema and domain contracts are ready"
  parallelizable: true
  prerequisites: [BATCH-003]
  constraints:
    - same_component_changes_must_be_serialized
    - migration_before_adapter
    - no_two_schema_migrations_in_same_batch_for_same_store
```

Топологический уровень DAG — отправная точка. Resource constraints (file conflicts, migration ordering) корректируют волны.

### 5.18 Circuit Breaker — маршрутизация проваленных Spike

Когда J-слой проваливает spike-задачу, он возвращает `spike_rejection.yaml`. J0 обязан дополнительно создать prompt-specific handoff package:

- `spike_rejection_export.yaml` — нормализованный export для I-layer;
- `i_layer_handoff.yaml` — human-readable/machine-readable инструкция запуска;
- `constraints_patch.yaml` для `target_prompt: I6. Architecture Synthesis.md` **или** `i17_spike_rejection_signal.yaml` для `target_prompt: I17. Trade-off HITL.md`.

Маршрутизация определяется `provenance_category` из spike_candidate, `recommended_action/rejection_reason` из `spike_rejection.yaml` и обязательным J0 `decision_gap_routing_screen`. Generic handoff без `target_prompt` запрещён. `decision_gap_routing_screen` имеет приоритет над `provenance_category`: missing/mismatched architecture contract field не должен уходить в I17 только потому, что исходный spike был помечен `upstream_requirement`.

```yaml
spike_rejection:
  spike_id: SPIKE-001
  rejected_by: J
  rejection_reason: "CRDT merge causes O(n²) conflicts for >100 concurrent edits"
  provenance_category: i_layer_initiative | upstream_requirement
  confirmed_at: <timestamp>
```

**Маршрут `i_layer_initiative`:**
- `spike_rejection.yaml` → J0 создаёт `constraints_patch.yaml` с `target_prompt: I6. Architecture Synthesis.md`
- Человек запускает I6 и передаёт `constraints_patch.yaml` как входной signal
- I6 выполняет локальный re-run: загружает предыдущий стейт + применяет rejection как ограничение
- Лимит: `max_retries: 2`. После 2 неудачных попыток → конфликт эскалируется в I17 (HITL) как неразрешимый

**Маршрут missing/mismatched upstream architectural contract:**
- Даже если исходный spike помечен `provenance_category: upstream_requirement`, если `spike_rejection.yaml` указывает `spike_forbidden_reason: missing_upstream_architectural_contract`, `decision_gap_routing_screen.route: I6` или эквивалентный rejection reason/blocking item, J0 создаёт `constraints_patch.yaml` для I6.
- Эквивалентные признаки включают отсутствие `contract`, `SLO`, `SLA`, `metric`, `budget`, `latency`, `timeout`, `scope`, `budget_metric`, `budget_scope`; для latency case — `documented worst-case latency`, `worst-case`, `latency_budget_ms`, `latency_budget_metric`, `latency_budget_scope`, `p95/p99 vs worst-case`, `within_budget unknown`, `on_device_call`.
- I6 обязан выполнить `decision_gap_screen` и, если gap подтверждён, создать OQ-I6 wrapper с `upstream_target_agent: I2` вместо нового spike_candidate.

**Маршрут `upstream_requirement`:**
- Применяется только если `decision_gap_routing_screen.route != I6`.
- Пайплайн принудительно останавливается
- J0 создаёт `i17_spike_rejection_signal.yaml` с `target_prompt: I17. Trade-off HITL.md`
- Человек запускает I17 с `i17_spike_rejection_signal.yaml`
- I17 (HITL) принимает решение: изменить архитектурное решение (replay I6/I3/I4) или сформировать `layer_rollback_request.yaml` (§5.19)

**Детерминированность после отказа:** если I6 меняет архитектуру в результате spike rejection, все агенты I8–I15 **перезапускаются с нуля**. Инкрементальное применение старых findings запрещено (правило из §5.8).

### 5.19 Layer Rollback — глобальный откат

I-слой не имеет права самостоятельно изменять или игнорировать бизнес-требования из H/D-слоёв.

Если I17 подтверждает что требование нереализуемо в рамках текущей архитектуры — формируется **терминальный артефакт**:

```yaml
layer_rollback_request:
  trigger_agent: I17
  triggered_at: <timestamp>
  reason: "upstream_requirement spike SPIKE-002 cannot be satisfied within current H-layer constraints."
  unresolvable_requirement_refs:
    - h9_contract_spec.yaml#HTTP-011
    - prd.index.yaml#story_042
  recommended_restart_layer: H | D
  context_for_restart: "<что именно не сходится и почему>"
  pipeline_status: aborted
```

**Последствия:**
- I-слой прерывается (`pipeline_status: aborted`) — никаких новых артефактов не публикуется
- `layer_rollback_request.yaml` записывается в `i_layer_run.yaml` как терминальное событие в `replay_log`
- Управление возвращается человеку с prompt-specific signal для перезапуска H или D слоя
- J-слой не получает задач при `aborted` статусе

**Условия формирования rollback (I17 не может выдать произвольно):**
1. `upstream_requirement` spike rejected + I6 не нашёл альтернативы за `max_retries`
2. upstream_requirement конфликтует с H-layer frozen constraint и конфликт неразрешим внутри I-слоя
3. Security или legal constraint (I14/I15) фундаментально несовместим с H-layer API surface и не имеет архитектурного обхода

### 5.20 I16 — ограничения axis-weighted auto-resolve

I16 вправе автоматически гасить конфликт только по оси из `allowed_axes` и только если severity ниже порога для `restricted_axes`.

```yaml
i16_auto_resolve_allowed:
  allowed_axes:
    - reliability
    - simplicity
    - maintainability
    - cost
    - performance
    - scalability
  restricted_axes:
    security:
      auto_resolve_allowed: false     # при severity blocker или major
      note: minor severity — авто-разрешение допустимо
    ethics_legal:
      auto_resolve_allowed: false     # при severity blocker или major
      note: minor severity — авто-разрешение допустимо
```

**Контракт шкалы весов (I2 → I16):**

I2 обязан выдавать веса в нормализованном формате; I16 обязан отклонить `technology_decisions.yaml` если контракт нарушен.

```yaml
axis_weight_contract:
  scale: normalized           # 0.0–1.0, не произвольные числа
  sum_constraint: 1.0         # сумма всех axis weights == 1.0 (±0.001 допуск на округление)
  enforced_by:
    - I2: output validation before writing technology_decisions.yaml
    - I16: pre-condition check before any auto-resolve logic
  violation_action: fail_i16_pre_condition → escalate all conflicts to I17
```

**Порог авто-разрешения:**

```yaml
axis_weight_auto_resolve:
  min_weight_delta: 0.15        # при нормализованной шкале 0–1; delta < 0.15 → I17
  max_auto_resolve_severity: minor  # major на любой оси → I17, не авторазрешение
  if_delta_below_threshold: escalate_to_I15
  if_severity_above_minor: escalate_to_I15
```

**Запрет:** I16 не авторазрешает конфликты с участием `security` или `ethics_legal` оси **ни при каком severity** — эти оси являются restricted и всегда эскалируются в I17. Аналогично: конфликт `major` на любой разрешённой оси при `weight_delta < min_weight_delta` — эскалация в I17.

**Audit trail:** все авторазрешённые конфликты записываются в `architecture_conflicts.yaml`. I17 **всегда** видит этот список как обязательный раздел.

```yaml
auto_resolved_conflict:
  conflict_id: CONFLICT-I16-007
  losing_axis: performance
  winning_axis: simplicity
  axis_weights_used:
    performance: 0.6
    simplicity: 0.8
  severity: minor
  rationale: "Simplicity weight (0.8) > performance weight (0.6); delta ниже порога значимости."
  requires_i17_visibility: true
```

### 5.21 I24 — два режима публикации

```yaml
i24_publish_mode:
  research_only_snapshot:
    trigger: spike_candidate where blast_radius=architecture_global and status=open
    gate: GATE-PRE-I24-RESEARCH_ONLY
    publishes:
      - spike_execution_context.yaml   # J читает вместо system_architecture.final.yaml
      - frozen_snapshot.research_only (без impl-задач)
      - tasks where task_type=research and execution_phase=strict_first
    does_not_publish:
      - system_architecture.final.yaml
      - implementation tasks
      - executable contracts (api_binding_spec, on_device_bridge_contract)
    defers:
      - все implementation tasks для области, зависящей от architecture_global spike
    resume_after: >
      spike resolved → resume per §5.22 full implementation path
      → GATE-PRE-I24-FULL_IMPLEMENTATION → implementation_snapshot

  implementation_snapshot:
    trigger: no open spike_candidate where blast_radius=architecture_global
    gate: GATE-PRE-I24-FULL_IMPLEMENTATION
    publishes:
      - frozen_snapshot.yaml (полный иммутабельный слепок)
      - tasks.db с всеми implementation tasks
```

При первом запуске I24: если `spike_candidates` содержит хотя бы один `architecture_global` spike — режим всегда `research_only_snapshot`. `implementation_snapshot` возможен только после закрытия всех `architecture_global` spikes и прохождения `GATE-PRE-I24-FULL_IMPLEMENTATION`.

### 5.22 Early-spike conservative route

Если I6 (initial run) обнаружил spike с `blast_radius: architecture_global`, I-слой переходит в **консервативный режим**: review-агенты пропускаются до результата spike. Это предотвращает дорогой и шумный review архитектуры, которая может быть выброшена.

```yaml
architecture_global_spike_route:
  trigger:
    condition: spike_candidate.blast_radius == architecture_global
    found_in: I6_initial_run

  before_spike_resolved:
    action: publish_research_only_snapshot via GATE-PRE-I24-RESEARCH_ONLY
    runs:
      - I20.research_task_only    # только research task, без impl-задач
      - I21.research_spec         # task_spec для research-задачи (spike_id, open_question_id, scope)
      - I23.research_snapshot_qa  # минимальный QA: provenance present, spike_id valid, causal_context included
                                  # ВАЖНО: работает исключительно с YAML-артефактами (spike_execution_context.yaml,
                                  # task_specs/). causal_graph.db в этом маршруте отсутствует — I7 (build_review_graph
                                  # и architecture_final_graph) не запущен.
      - I24.research_only_snapshot
    skip_until_spike_resolved:
      - I7 (build_review_graph)
      - I8–I15
      - I16
      - I17
      - I18–I19
      - I20 (implementation mode)
      - I7 (architecture_final_graph)
      - I7 (task_trace_graph)

  remaining_spike_guard:
    rule: before any resume_from I7, recompute remaining_open_architecture_global_spike_ids from spike_candidates.yaml
    if_remaining_open:
      action: repeat research-only route for remaining spikes
      runs:
        - I20.research_task_only
        - I21.research_spec
        - I23.research_snapshot_qa
        - I24.research_only_snapshot
        - J executes remaining spike research
      forbidden_resume:
        - I7 (build_review_graph)
        - I8-I15
        - I20 (implementation mode)
    if_none_remaining:
      action: resume from I7 (build_review_graph)

  after_spike_success_no_arch_change:
    # spike подтвердил гипотезу без изменения архитектуры
    # допустимо только если remaining_open_architecture_global_spike_ids == []
    # impl-задачи не создавались ранее → нужен полный I20 implementation mode
    resume_from: I7 (build_review_graph)
    rerun_agents:
      - I7 (build_review_graph)
      - I8–I15 (full parallel review block)
      - I16
      - I17
      - I18–I19
      - I7 (architecture_final_graph)
      - I20 (full implementation mode)
      - I21 (all leaf task specs)
      - I22 (decomposition challenge + risk acceptance)
      - I23 (full coverage check)
      - I7 (task_trace_graph)
      - I24 (implementation_snapshot)

  after_spike_success_with_arch_change:
    # spike успешен, но изменил параметры решения → I6 patch run сначала
    action: I6 patch run → затем remaining_spike_guard; I7 разрешён только если open architecture_global spikes не осталось
    rerun_agents: same as after_spike_success_no_arch_change (starting after I6 patch)
    affected_scope_source:
      - spike_candidate.impact_radius
      - spike_candidate.affected_process_ids

  # Примечание: I20_affected_scope используется только если implementation snapshot
  # уже существовал до spike (component-level или post-review spike). В early-spike
  # route impl-задач нет — нужен всегда full I20.

  after_spike_failure:
    action: circuit_breaker §5.18
```

**Если architecture_global spike обнаружен после initial reviews** (например, обнаружен в цикле upstream_signal): reviews уже выполнены → они помечаются `status: provisional`. При возврате после spike success все I8–I15 перезапускаются полностью (правило §5.8: full restart после любого I6 change).

### 5.23 spike_execution_context.yaml

Артефакт, который J получает вместо `system_architecture.final.yaml` в режиме `research_only_snapshot`. Явно ограничивает допустимое использование.

```yaml
spike_execution_context:
  spike_ids: [SPIKE-001]
  source_architecture: system_architecture.draft.yaml
  source_architecture_hash: sha256:<hash>
  allowed_use: research_only
  forbidden_use:
    - implementation
    - contract_generation
    - migration_generation
  allowed_task_ids: [T-000]   # только research-задача из batch_id: 0
  expires_after: spike_resolved   # J обязан прекратить использование после закрытия spike

  causal_context:
    # I7 не запущен в early-spike route → контекст берётся напрямую из I3/I4/I5 outputs.
    # Это позволяет J понять бизнес- и технические основания спайка без full causal graph.
    sources:
      - process_causality_map.yaml      # I3: процессы, causality chains, stories
      - invariants_ownership.yaml       # I4: содержание инвариантов (не только IDs)
      - interaction_semantics.yaml      # I5: semantics взаимодействий (не только IDs)
    scope:
      processes: spike_candidate.affected_process_ids
      invariants: spike_candidate.affected_invariant_ids
      interactions: spike_candidate.affected_interaction_ids
    includes:
      - process entries (id, name, trigger, result, stories)
      - causality_chains (cause → effect для затронутых процессов)
      - invariant entries (id, statement, enforcement_mechanism, owner)
      - interaction semantic entries (id, type, latency_budget, fallback_behavior)
      - source story_ids from prd.index.yaml
    format: inline excerpt  # вшито в spike_execution_context, не отдельный файл
```

J-слой обязан проверять `allowed_use` перед любым обращением к архитектурным артефактам из `research_only_snapshot`. `causal_context` даёт достаточный процессный фон без запуска I7 в режиме build_review_graph.

---

### 5.24 Budget Escalation — маршрутизация из J-слоя

**Проблема, которую закрывает этот раздел.** До 2026-08-25 канал `budget_escalation_request/response` был единственным I↔J каналом без приёмника: `budget_escalation_request.yaml` не значился входом ни одного I-агента, `budget_escalation_response.yaml` не имел ни одного производителя, а §6 знал ровно один вход из J — `spike_rejection.yaml`. J0 при формальном триггере обязан создать запрос, встать в `pending_i_layer_response` и остановиться, читая в этом состоянии только response (инвариант J0 №18) — то есть любая budget/human_action эскалация терминально подвешивала слой. Обнаружено первой же реальной эскалацией прогона (BER-T-010-001). Раздел строится симметрично §5.18 (Circuit Breaker), а не изобретается заново.

**Handoff package (создаёт J0, не I-слой).** Как и при spike rejection, generic handoff запрещён: J0 обязан вместе с `budget_escalation_request.yaml` создать `j_budget_escalation_signal.yaml` с явным `target_prompt`. В отличие от §5.18, где два целевых промпта требуют разных по форме payload (`constraints_patch.yaml` vs `i17_spike_rejection_signal.yaml`), здесь payload одинаков для всех целей — сам запрос плюс манифест evidence — поэтому артефакт один, а различается только `target_prompt`.

**Escalation routing screen — обязателен и имеет приоритет над `requested_action`.** Тот же принцип, что `decision_gap_routing_screen` в §5.18: грубое `requested_action` (`task_spec_update` и т. п.) не определяет цель однозначно — `task_spec_update` может означать и правку текста одной спеки (I21), и изменение рёбер графа (I20). Поэтому J0 обязан заполнить `escalation_routing_screen.scope` закрытым enum:

| `escalation_routing_screen.scope` | `target_prompt` | Владелец / почему |
|---|---|---|
| `task_graph_edges` | `I20. Task Tree Builder.md` | I20 владеет `task_tree.yaml` и `depends_on` |
| `task_status_change` | `I20. Task Tree Builder.md` | статус задачи (`ready_for_spec \| blocked_by_spike \| deferred`) рождается в task_tree; см. §11 Deep Findings J о жизненном цикле `deferred` |
| `task_decomposition` | `I20. Task Tree Builder.md` | декомпозиция — зона I20 |
| `task_spec_text` | `I21. Task Spec Agent.md` | I21 владеет текстом `task_specs/<id>.yaml` |
| `architecture_decision` | `I17. Trade-off HITL.md` | требует human trade-off |
| `technology_decision` | `I17. Trade-off HITL.md` | тот же human trade-off; при чисто синтезной правке I17 форвардит в I6 обычным механизмом |
| `prompt_defect` | `null` | **см. ниже** — ни один I-агент не может это исполнить |

`scope` — список, не одно значение: одна эскалация законно несёт несколько (BER-T-010-001 несёт `task_status_change` + `task_graph_edges` + `prompt_defect`). При нескольких scope `target_prompt` определяется первым по порядку строк таблицы выше, остальные передаются целевому агенту как контекст и форвардятся обычными внутренними механизмами I-слоя.

**`prompt_defect` — честный тупик, а не маршрут.** Если эскалация требует изменить *логику самого агента*, а не данные (пример из BER-T-010-001: «I20 не должен разворачивать `blocks_task_types` в blanket-рёбра»), ни один I-агент этого исполнить не может — правится промпт, а это работа человека/дизайна пайплайна. Такой scope не получает `target_prompt`; J0 обязан явно назвать его в signal и сообщить человеку. Запрещено молча маршрутизировать `prompt_defect` в I20 «раз он всё равно про граф» — агент выполнит запрос данных и оставит дефект логики на месте, а следующая эскалация повторит его.

**Производитель `budget_escalation_response.yaml` — I24, всегда.** Независимо от того, какой агент фактически применял изменение, цикл закрывается публикацией: response несёт `new_snapshot_id`, который J0 обязан прогнать через обычный Snapshot Gate, а единственный агент, публикующий снапшоты, — I24. Промежуточные агенты (I20/I21/I17/I6) не пишут response и не общаются с J напрямую; они отрабатывают своё изменение и передают управление дальше по обычной внутренней цепочке I-слоя вплоть до I24.

**Симметрия контракта (закрывает §9 Deep Findings J).** `budget_escalation_response.yaml` обязан эхом нести `request_id` и `request_hash` (SHA-256 байт `budget_escalation_request.yaml`, который I-слой фактически прочитал). J0 сверяет оба перед применением response; несовпадение `request_hash` означает ответ на другую ревизию запроса и не применяется. Повторный `resolved` с тем же `request_id` идемпотентен. `new_snapshot_id` применяется только после того, как новый снапшот прошёл Snapshot Gate по своему `j_handoff_signal.yaml`.

## 6. Карта входных/выходных артефактов

### Входы I-слоя

| Артефакт | Источник | Читается в |
|---|---|---|
| `h15_gate_decision: APPROVED` | **H15** | I0/I1 (gate check) |
| `h12_integration_spec.yaml` | **H12** | I1 (архитектурные constraints), I3 (frontend process model), I6 (API surface seed) |
| `h9_contract_spec.yaml` | **H9** | I6 (frozen API surface: HTTP-011, HTTP-014, HTTP-003) |
| `h14_hitl_decision_log.yaml` | **H14** | I1, I6 (H14 HITL-001 платёж, HITL-002 удаление, ID-002 ChatInlineCommit) |
| `prd.index.yaml` | D7 | I1, I3, I4, I6, I20, I22 |
| `idea_note.yaml` | A/B | I1, I3 |
| `pipeline.db` | I3 (создаёт) | I4, I5, I6, I7 |
| `spike_rejection.yaml` | **J-слой** | I6 (если `provenance_category: i_layer_initiative` или `decision_gap_routing_screen.route: I6` для missing/mismatched architecture contract), либо I17 (если `upstream_requirement` требует human trade-off/layer rollback) |
| `budget_escalation_request.yaml` + `j_budget_escalation_signal.yaml` | **J-слой (J0)** | промпт из `j_budget_escalation_signal.yaml#target_prompt` — I20 (`task_graph_edges` / `task_status_change` / `task_decomposition`), I21 (`task_spec_text`), I17 (`architecture_decision` / `technology_decision`); `scope: prompt_defect` не маршрутизируется в агента (см. §5.24). Ответ пишет **только I24** |

### Артефакты внутри I-слоя

```
I0  → i0_migration_report.yaml
I1  → technology_research.yaml
I2  → technology_decisions.yaml
I3  → pipeline.db (pg_*) + process_causality_map.yaml + open_questions.yaml
I4  → pipeline.db (io_*) + invariants_ownership.yaml + open_questions.yaml
I5  → interaction_semantics.yaml + open_questions.yaml
      resolved_open_questions.yaml (если HITL нужен)
I6  → system_architecture.draft.yaml  [initial run]
      spike_candidates.yaml
      assumptions.yaml (initial entries)
      api_binding_spec.yaml              [initial; artifact_status: draft, allowed_use: review_only]
      on_device_bridge_contract.yaml     [initial; artifact_status: draft, allowed_use: review_only]
      system_architecture.final.yaml  [patch run]
      api_binding_spec.yaml              [patch run; artifact_status: architecture_accepted, allowed_use: downstream_review_only]
      on_device_bridge_contract.yaml     [patch run; artifact_status: architecture_accepted, allowed_use: downstream_review_only]
      # Уточнено по факту реализации I6 (I6. Architecture Synthesis.md): artifact_status никогда не
      # достигает "final" — конечное значение architecture_accepted. allowed_use: implementation
      # предполагался отдельным human-run publishing/sign-off шагом после I18/I19, но такой шаг нигде
      # в пайплайне не реализован; I24 (Шаг 5) принимает architecture_accepted + downstream_review_only
      # как достаточный сигнал готовности к публикации.
I7  → causal_graph.db (версии: 1/review → final)
I8–I13 → i8_..._review.yaml .. i13_..._review.yaml  [unified finding format]
I14 → i14_security_review.yaml (+ optional upstream_signal.yaml)
I15 → i15_ethics_legal_review.yaml (+ optional upstream_signal.yaml)
I16 → architecture_conflicts.yaml
I17 → i17_hitl_decision_log.yaml + architecture_decisions.yaml
      layer_rollback_request.yaml  (терминальный; опциональный; прерывает пайплайн)
I18 → observability_spec.yaml (+ optional upstream_signal.yaml)
I19 → deployment_spec.yaml   (+ optional upstream_signal.yaml)
I20 → task_tree.yaml
I21 → task_specs/ (один yaml на листовой узел)
I22 → i22_tree_review_log.yaml
I23 → i23_task_graph_qa_report.yaml + coverage_matrix.yaml
I24 → frozen_snapshot.yaml + tasks.db
      spike_execution_context.yaml  [только в research_only_snapshot режиме]
```

### Выходы I-слоя в J-слой

| Артефакт | Производитель | Назначение в J |
|---|---|---|
| `system_architecture.final.yaml` | I6 | Единственный architecture reference |
| `api_binding_spec.yaml` | I6 | Контракты для code.contract и code.adapter |
| `on_device_bridge_contract.yaml` | I6 | Контракт для Elm ↔ on-device boundary |
| `architecture_decisions.yaml` | I17 | Append-only лог `[context, decision, trade_off_accepted]`; накладывается поверх архитектуры; I7 вшивает в causal_graph.db |
| `causal_graph.db` (final) | I7 | Полная трассировка task → component → story |
| `tasks.db` с `batch_id`, `sequence_order` | I24 | Execution-ready task graph; research в `execution_phase: strict_first` |
| `observability_spec.yaml` | I18 | Что J должен инструментировать |
| `deployment_spec.yaml` | I19 | Как J деплоит артефакты |
| `assumptions.yaml` (validated/accepted) | I6/I23 | Допущения для валидации в J |
| `frozen_snapshot.yaml` | I24 | Полный, иммутабельный, хэшированный слепок всех I-артефактов (не diff) |
| `spike_execution_context.yaml` | I24 | Только в `research_only_snapshot`; J читает вместо `system_architecture.final.yaml`; запрещает использование как implementation reference |

---

## 7. Типы задач в tasks.db

| Тип | Описание | Примечание |
|---|---|---|
| `research` | Spike: проверка технической гипотезы | Если опровергает архитектуру → partial replay I6 |
| `infrastructure` | Создание окружений, ресурсов, сервисов | |
| `config` | Конфигурационные файлы, secrets, feature flags | |
| `code.domain_logic` | Бизнес-логика: solver, parser, domain rules | |
| `code.adapter` | Интеграция с внешними сервисами / портами | Leaf unit = contract operation, не contract целиком |
| `code.presentation` | UI/client presentation behavior по surface/platform | Leaf unit = surface state / user flow; iOS/Android/web split не склеивается, если различаются runtime, bridge, navigation/state или acceptance criteria |
| `code.migration` | Миграции данных | Требует rollback_strategy |
| `code.contract` | API-контракты, типы, интерфейсы | |
| `code.orchestration` | Оркестрация процессов, flow coordination | |
| `qa` | Тесты, E2E-сценарии | |

Все code-задачи несут provenance. J использует provenance для валидации реализации против фундаментальной модели.

---

## 8. HITL-точки

| # | Агент | Когда | Что делает человек |
|---|---|---|---|
| 1 | **I2** | После I1 | Выбирает технологии по доменам, приоритеты осей |
| 2 | **I5** (условный) | Если blocking_open_questions > 0 | Отвечает на вопросы с blocking_level: blocks_architecture |
| 3 | **I17** | Всегда, после I16 | Mode full: выбирает между trade-off options. Pass-through: подтверждает. |
| 4 | **I22** | После I21 | Decomposition challenge: гранулярность и пропуски. Явное принятие риска для задач с `data_loss_risk: true` → заполняет `accepted_risk_id` (единственный легальный HITL-узел для этого). |

---

## 9. Что нужно изменить в существующих промптах

### I0 — Bootstrap + Schema Migration (написан)

Создаёт `pipeline.db` и базовые таблицы если отсутствуют (`pg_create_db.py`, `io_create_tables.py`). Затем: `PRAGMA table_info` → idempotent `ALTER TABLE ADD COLUMN` → физическая правка CLI-скриптов (backward compatible, default=None; --owner_context/--canonical_store/--conflict_resolution_condition null — I4-совместимые aliases). Выход: `i0_migration_report.yaml`. Инициализирует `i_layer_run.yaml` только при `all_passed: true`.

### I1 — расширенные технологические домены

Добавить к R1 доменам (on_device_runtime, server_runtime, local_storage, payment_runtime):

```yaml
sync_protocol:
  candidates:
    - event_log_sync          # append-only журнал операций → server replays
    - operation_based_sync    # CRDT или operation transform
    - state_snapshot_sync     # snapshot + diff
    - last_write_wins         # с conflict prompts для видимых конфликтов

local_data_model:
  candidates:
    - normalized_local_store  # relational-like в IndexedDB
    - append_only_event_log   # event sourcing on-device
    - hybrid_state_plus_log   # current state + pending events

local_security:
  candidates:
    - no_encryption
    - os_browser_storage      # platform keychain / browser credential store
    - application_level_encryption   # AES-256 перед записью в IndexedDB
```

(solver_runtime и background_execution уже в on_device_runtime; расщепить при необходимости.)

Добавить domain_dependencies: `sync_protocol` → `local_data_model`, `sync_protocol` → `server_runtime`.

### I3 — execution_location + Mode A/B + ChatInlineCommit

**Обязательный follow-up R11:** добавить `granularity_refinement_mode`, который читает `granularity_refinement_signal.yaml`, добавляет step/stage structure для coarse processes с independently testable postconditions, обновляет `process_causality_map.yaml`, пишет replay evidence и возвращает управление по signal return_contract через I4→I5→I6→I7→I20.

- `pg_add_step.py --execution_location`, `pg_add_process.py --primary_location`
- Mode A: разрешены cross-process connections
- Mode B: секции `on_device_processes` / `server_processes` в process_causality_map.yaml
- ChatInlineCommit step (H14 ID-002): on_device_call confirm → sync_rpc HTTP-014

### I4 — authority model

Расширить io_add_entity.py:

```yaml
entity_authority:
  canonical_store: on_device | server | replicated
  write_authority: device | server | both
  conflict_resolution:
    strategy: server_wins | device_wins | last_write_wins | merge_by_field |
              merge_by_operation | human_resolution | domain_specific
    condition: null | on_delete | on_conflict | on_schema_mismatch   # уточняет strategy
  sync_requirement: immediate | eventual | manual | never
  offline_write_allowed: true | false
  server_confirmation_required: true | false
```

Явно добавить cloud data entity: `canonical_store: server`, `offline_write_allowed: false`, `server_confirmation_required: true`, `conflict_resolution: {strategy: server_wins, condition: on_delete}` (из H14 HITL-002).

### I5 — Interaction Semantics (перезаписать)

**Обязательный follow-up R11:** добавить `granularity_refinement_mode`, который читает `granularity_refinement_signal.yaml`, раскладывает coarse interactions/contracts на operation-level boundaries (endpoint, bridge call, event handler, webhook) с failure/auth/error semantics, обновляет `interaction_semantics.yaml`, и возвращает управление по signal return_contract через I6→I7→I20.

Классифицирует каждое ребро. Для on_device_call явно проверяет 5 условий (§2) и записывает:

```yaml
on_device_call:
  latency_budget_ms: 16
  local_failure_modes:
    - storage_quota_exceeded
    - worker_crash
    - wasm_load_failure
  requires_local_persistence: true
  requires_worker: false
  fallback_behavior: show_offline_indicator_and_queue
```

Conditional HITL: если `blocking_open_questions > 0` (только `blocks_architecture`) → `status: awaiting_clarification`.

Типизирует каждый open_question по схеме §5.4.

### I6 — Architecture Synthesis (новый; initial + patch runs)

**Обязательный follow-up R11:** добавить `granularity_refinement_mode`, который читает `granularity_refinement_signal.yaml`, уточняет component/surface boundaries до surface state/user-flow или capability-level units без принятия новых продуктовых решений, обновляет `system_architecture.final.yaml`/binding contracts, и возвращает управление по signal return_contract через I7→I20.

**Initial run:** читает I3+I4+I5+I2+h12_integration_spec+h9_contract_spec+h14_hitl_decision_log → `system_architecture.draft.yaml` с hooks (§5.11), H14 components (§5.12), api_binding_spec.yaml, on_device_bridge_contract.yaml (§5.13). Spike candidates — только `technical_unknown`.

**Patch run** (после I17): читает `architecture_decisions.yaml` → применяет patches → `system_architecture.final.yaml`.

---

## 10. Порядок написания промптов

### Шаг 0 — Формализация схем и gate conditions

Написать форматы артефактов (не агенты):
- [ ] `i_layer_run.yaml` schema (§5.0: artifacts, gates, replay_log)
- [ ] Unified finding schema (§5.6)
- [ ] open_question schema с type/resolution_mode/blocking_level (§5.4)
- [ ] spike_candidate schema с blast_radius (§5.16)
- [ ] assumption schema (§5.5)
- [ ] coverage_matrix schema (§5.14)
- [ ] task_spec base schema (§5.17)
- [ ] frozen_snapshot manifest schema (§5.15)
- [ ] entity_authority schema для I4 (§9)

### Шаг 1 — I0 Schema Migration

- [ ] I0: pipeline.db migration + CLI updates + i_layer_run.yaml инициализация

### Шаг 2 — Исправление существующих I1/I3/I4/I5

- [ ] I1: +sync_protocol, +local_data_model, +local_security; H14 bindings
- [ ] I3: execution_location, Mode A/B, ChatInlineCommit step
- [ ] I4: authority model (write_authority, sync_requirement, offline_write_allowed)
- [ ] I5: перезаписать — Interaction Semantics с 5 условиями on_device_call + open_question typing

### Шаг 3 — I6 как draft architecture generator

- [ ] I6 initial run: draft + hooks (§5.11) + H14 components (§5.12) + H12 outputs (§5.13); **spike_candidates с provenance_category + impact_radius (§5.16); patch run после I17**

### Шаг 4 — Unified reviewer contract + I7 initial

- [ ] I7 (build_review_graph mode)
- [ ] Unified reviewer prompt template (finding schema §5.6)
- [ ] I8–I13: six quality reviewers
- [ ] I14: Security Review (findings → I16; optional upstream_signal → I6)
- [ ] I15: Ethics & Legal Review (findings → I16; optional upstream_signal → I6)
- [ ] I16: Conflict Resolver (aggregates I8–I13 + I14 + I15)
- [ ] I17: Trade-off HITL (always-on; scope restriction §5.7)
- [ ] I6 patch run capability (architecture_decisions.yaml → final)

### Шаг 5 — I18/I19 + I7 (architecture_final_graph) + Task Graph + I7 (task_trace_graph) + I24

**Основной (implementation) путь:**
- [ ] I18: Observability Architect (develops hooks → spec; optional upstream_signal)
- [ ] I19: Deployment Architect (develops hooks → spec; optional upstream_signal)
- [ ] I7: architecture_final_graph mode (добавляет decisions + constraints + specs; перед I20)
- [ ] I20: Task Tree Builder (full impl mode; строгая топосортировка; blast radius §5.16; leaf task criteria §5.17)
- [ ] I21: Task Spec Agent (расширенная схема §5.17; data_loss_risk + mitigation_plan; accepted_risk_id: null до I22)
- [ ] I22: HITL Tree Review + Risk Acceptance (decomposition challenge; принятие риска data_loss_risk: true → accepted_risk_id; единственный легальный HITL-узел §5.17)
- [ ] I23: Task Graph QA (coverage matrix §5.14; provenance_minimum_by_task_type; data_loss_risk gate: accepted_risk_id not null; dual-mode: YAML-only в research_snapshot_qa §5.14)
- [ ] I7: task_trace_graph mode (добавляет tasks + acceptance criteria; перед I24)
- [ ] I24: Gatekeeper & Publisher (два gate §5.0; два режима §5.21; frozen_snapshot §5.15; Circuit Breaker §5.18; Layer Rollback §5.19)

**Early-spike branch (если I6 initial создаёт architecture_global spike):**
- [ ] I20.research_task_only (без impl-задач)
- [ ] I21.research_spec (task_spec с spike_id + open_question_id)
- [ ] I23.research_snapshot_qa (минимальный QA: provenance + spike_id valid)
- [ ] I24.research_only_snapshot (через GATE-PRE-I24-RESEARCH_ONLY)
- [ ] → после spike success: полный основной путь от I7 (build_review_graph) (§5.22)

---

## 11. Принятые решения по открытым вопросам

**Что содержит `architecture_decisions.yaml` от I17?**  
Append-only лог с записями `[context, decision, trade_off_accepted]`. Накладывается поверх system_architecture.draft.yaml через required_architecture_patch. I7 вшивает принятые решения в causal_graph.db в режиме architecture_final_graph. J-слой использует как trace, не как исполняемый артефакт. Поля `confidence` и `expiry_condition` — опциональны в MVP.

**Как upstream signal механически возвращается в I6?**  
Как prompt-specific `constraints_patch.yaml` с `target_prompt: I6. Architecture Synthesis.md`. Человек запускает I6 и передаёт этот файл как входной signal. I6 загружает предыдущий стейт + применяет патч → выдаёт новую версию draft. Лимит: `max_upstream_loops: 2` (§5.8). После превышения I6 пишет prompt-specific signal для I17.

**Как I20 определяет гранулярность задач?**  
Жёсткая эвристика: 1 задача = 1 `decomposition_unit`, а не 1 компонент. Компонент — только ownership boundary; I20 раскладывает его на domain capabilities, adapter endpoints, contract shapes, migration steps, orchestration flows и UI presentation surfaces. Для `human_action` листовой результат — один подтверждаемый внешний state change или один набор связанных secret refs в одном external system.

**Как I24 обрабатывает незакрытые research-задачи?**  
Research-задачи принудительно выносятся в `execution_phase: strict_first` (batch_id: 0). Зависимые code-задачи блокируются (`blocked_by_spike`). Frozen snapshot публикуется оптимистично — J получает архитектуру и research-задачи, но не берёт implementation tasks до закрытия фазы 0. Провал spike → маршрутизация по §5.18.

**`frozen_snapshot.yaml` — копия или diff?**  
Полный, иммутабельный, хэшированный слепок всех I-артефактов. Не diff. J проверяет хеши перед стартом.

**Нужен ли агент-оркестратор для retry-цикла I6 ↔ J (spike rejection)?**  
Нет. Retry-логика не должна жить в скрытом агенте или внешнем daemon. Нужен human-run signal contract: каждый prompt пишет конкретный signal artifact (`target_prompt`, `signal_type`, `required_change`, source refs), а человек явно запускает следующий prompt. `i_layer_run.yaml`, `run_events/`, `max_upstream_loops`, partial re-run I6, full restart I8–I15, два режима I24, circuit breaker и layer rollback остаются control-plane данными, но переход между ними выполняется через prompt-specific signals, а не через неявный оркестратор.

---

## 12. Что НЕ меняется

- Механизм `pipeline.db` + скрипты (`pg_*`, `io_*`) — ядро накопления; I0 создаёт БД/таблицы если нет, затем добавляет колонки
- Шесть осей quality review (I8–I13) — полный набор; не сокращается
- Архитектурный стиль как **вывод** (не вход) I6 — принцип сохраняется
- H-layer Elm-архитектура — frozen invariant; I-агенты не пересматривают H-решения
- HITL-точки: I2, условный I5, I17, I22 — сохраняются; `human_action` не заменяет эти решения, а моделирует внешние ручные операции в J-графе.

**Invariant rules (R2):**

1. **No downstream write.** Downstream-агент не изменяет upstream-артефакт напрямую. Любое изменение — через replay/patch/upstream_signal с записью в `replay_log`. Исключение только для lifecycle-cleanup I24: stale `spike_execution_context.yaml` атомарно переносится в audit-архив при переходе в implementation после проверки, что открытых `architecture_global` spikes нет.

2. **Content-addressed finals.** Любой final-артефакт несёт `schema_version` и `content_hash`. Без них I24 не включает артефакт в frozen_snapshot.

3. **No task without typed provenance.** Любая задача в tasks.db имеет provenance согласно матрице `provenance_minimum_by_task_type` (§5.17). Базовый минимум: хотя бы один `process_id` или `invariant_id`; для code-задач — тип-специфичный набор полей. Несоответствие — gate failure в I23.
4. **No secret values in artifacts.** `task_type: human_action` и любые config/infra задачи могут ссылаться только на `secret_ref`, `vault_path`, `env_var_name`, `external_resource_id`, fingerprint/last4/hash. Полные API keys, refresh tokens, webhook secrets, private keys и пароли в YAML/Markdown/git запрещены; обнаружение значения → gate failure в I23/I24.

5. **No blocking question → no snapshot.** Если любой open_question с `blocking_level: blocks_architecture` имеет `status: open` → I24 не публикует snapshot.

6. **No architecture-blocking spike → no implementation snapshot.** Если любой spike с `blast_radius: architecture_global` не закрыт → I24 публикует только research-задачи.

7. **H-layer constraints are frozen.** H-layer frozen API surface (`h9_contract_spec.yaml` + `h12_integration_spec.yaml`) — только constrained или adapted в I-слое, не redefined. Переопределение требует возврата в H-слой.

8. **I17 scope is bounded.** I17 выбирает между явными options или возвращает архитектуру. Новые требования — только через upstream_message в соответствующий слой.

---

## 13. Контракт human-run orchestration

В I-layer нет фонового оркестратора, daemon, pipeline runner или скрытого автоматического продолжения. Единственный оркестратор — человек, который явно запускает следующий prompt. Агенты I0–I24 не должны рассчитывать, что внешний компонент сам выберет следующий шаг. Поэтому каждый переход между prompt'ами должен быть представлен конкретным machine-readable signal artifact с `target_prompt`, `target`, `signal_type`, `required_change` и source refs.

Агенты I0–I24 пишут состояние в `i_layer_run.yaml` и `run_events/`, но не запускают следующий numbered agent сами. Человек читает prompt-specific signal file и запускает указанный prompt вручную.

```yaml
orchestration_contract:
  owner: human_operator
  reads:
    - i_layer_run.yaml
    - next_prompt_signal.yaml
    - prompt-specific signal files

  signal_requirements:
    required_fields:
      - target_prompt
      - target
      - signal_type
      - required_change
      - source_refs
    invalid_if:
      - target_prompt is null
      - target is generic owner text such as "I-layer" without a concrete prompt
      - required_change is absent or not actionable

  responsibilities:
    select_next_agent:
      basis: target_prompt from prompt-specific signal; fallback current_stage + gate_status in i_layer_run.yaml
      action: human explicitly launches target prompt
    enforce_gates:
      action: do not launch target prompt if gate.blocking_conditions are not cleared
    merge_run_events:
      trigger: after parallel block I8–I15 completes
      signal_file: next_prompt_signal.yaml
      target_prompt: I16. Architecture Conflict Resolver.md
    detect_retry_limit_exceeded:
      source: i_layer_run.yaml#replay_log + max_upstream_loops
      signal_file: i17_replay_limit_signal.yaml
      target_prompt: I17. Trade-off HITL.md
    trigger_full_review_restart_after_i6_change:
      trigger: system_architecture.draft.yaml content_hash changed
      action: write next_prompt_signal.yaml for I7 build_review_graph; human launches each prompted step explicitly
    route_spike_rejection:
      source: spike_rejection.yaml from J
      action: read J0 i_layer_handoff.yaml; launch exact target_prompt from target_signal_ref (§5.18)
    route_i23_gate_failure:
      source: i23_upstream_return_signal.yaml from I23
      condition: i_layer_run.yaml#current_stage == blocked_i23_gate_failure
      action: launch exactly source.target_prompt; do not infer a different owner from gate_failures when the signal exists
    prevent_j_start_when_aborted:
      condition: pipeline_status == aborted in i_layer_run.yaml
      action: block J-layer launch; write upstream layer_rollback signal for H/D owner if applicable
    manage_i24_publish_mode:
      basis: open architecture_global spikes in spike_candidates.yaml
      action: orchestrator (human/tooling, e.g. tools/run_i20_task_tree_builder.py, tools/run_i23_task_graph_qa.py)
        sets i_layer_run.yaml#pipeline_run.i24_publish_mode to research_only_snapshot | implementation_snapshot
        (§5.21) before launching I24; I24 itself only consumes this field as input, validates it against
        spike_candidates.yaml/current_stage (conflict-check, see I24 prompt §«Определение режима»), and either
        publishes the corresponding snapshot or blocks (mode_conflict/cannot_determine_mode) — I24 does not
        select its own mode. Real producers currently write `full_implementation_pending` as an alias for
        `implementation_snapshot` (I24 accepts it explicitly).
    resume_after_spike_success:
      source: spike_execution_context.yaml#expires_after
      action:
        guard:
          recompute: remaining_open_architecture_global_spike_ids from spike_candidates.yaml
          if_remaining_open: write next_prompt_signal.yaml for I20.research_task_only and repeat I20→I21→I23→I24→J
          if_none_remaining: allow resume_from I7 (build_review_graph)
        if_success_no_arch_change:
          resume_from: I7 (build_review_graph)
          run: write concrete next_prompt_signal for each step; human launches each prompt explicitly
        if_success_with_arch_change:
          trigger: write constraints_patch.yaml for I6 patch run, then apply guard before writing any I7 build_review_graph signal
        if_pre_existing_implementation_snapshot:
          trigger: write affected-scope next_prompt_signal per spike_candidate.impact_radius

  not_responsible_for:
    - making architecture decisions
    - resolving trade-offs
    - editing artifacts directly
    - choosing between conflicting findings
```

**Минимальная реализация (MVP):** человек читает `i_layer_run.yaml` и prompt-specific signal files, затем явно запускает нужный prompt. Скрипт-оркестратор не предполагается и не требуется. Сложные ветки (spike rejection, layer rollback) должны быть представлены concrete signal artifacts, а не неявными if-условиями.

---

*Написан 2026-06-04. R1: 2026-06-17 — handoff H14→H15, I0, H14 bindings, api_binding_spec, on_device_bridge_contract, frozen_snapshot manifest, task_spec. R2: 2026-06-17 — control plane (i_layer_run.yaml), open_question typing, assumption ledger, unified finding schema, I14/I15 before I16, I7 two modes, I6 draft→final, observability/deployability hooks, coverage matrix gate, spike blast radius, extended task_spec + leaf criteria, on_device_call 5 conditions, I1 +3 domains, I4 authority model, 7 invariant rules. R3: 2026-06-17 — provenance_category + impact_radius в spike_candidate; I16 axis-weighted auto-resolve; I20 строгая топосортировка; I24 execution_phase strict_first; оптимистичный spike; Circuit Breaker §5.18; Layer Rollback §5.19; max_upstream_loops + полный перезапуск reviews; spike_rejection.yaml ← J; layer_rollback_request.yaml; §11 переименован. R4: 2026-06-17 — два gate I24; два режима publish; architecture_global spike не материализует impl-задачи; I16 restricted auto-resolve + audit trail; parallel write policy run_events/; I0 smoke tests; process_to_invariant explicit exemption; provenance_minimum_by_task_type; invariant rule #3 уточнён. R5: 2026-06-17 — orchestration_contract §13; spike_execution_context.yaml §5.23; early-spike conservative route §5.22; I16 min_weight_delta + axis_weight_contract; run_event_merge_policy fail-fast; frozen_snapshot snapshot_mode + risk_kind; h_layer_constraint_to_arch treatment; I1 без hardcoded count. R6: 2026-06-17 — run_events archive + stale-delete; I0 EXCLUSIVE TRANSACTION; axis_weight_contract 0–1 sum=1.0; data_loss_risk + I22 rule; causal_context из I3. R7: 2026-06-17 — I7 три режима; frozen_snapshot union format; §5.4 противоречие; early-spike research pipeline; spike_candidate affected_process/invariant/interaction_ids; GATE-PRE-I6 расширен; data_loss_risk→HITL-only; conflict_resolution.condition on_delete. R8: 2026-06-17 — §5.9 заголовок "три режима"; §1 диаграмма с early-spike ветвью; GATE-PRE-I24-RESEARCH_ONLY расширен (7 blocking conditions); GATE-PRE-I24-FULL_IMPLEMENTATION расширен (11 required + 7 blocking); frozen_snapshot mode-specific included_artifacts + forbidden_in_research_only; §5.22 after_spike_success full pipeline с I7b/I7c/I21; §13 resume_after_spike_success три ветки; §5.23 causal_context из I3+I4+I5; §6 api_binding + on_device_bridge_contract artifact_status draft/final; §10 step 5 два пути (main + early-spike). R9: 2026-06-17 — нумерация I20→I21→I22→I23 (I21=Task Spec, I22=HITL); I7a/b/c → I7 (mode); §5.17 I21 ставит risk/mitigation, I22 заполняет accepted_risk_id; §5.12 server_wins_on_delete → {strategy: server_wins, condition: on_delete}; §5.16/§5.21 partial re-run → resume per §5.22; §11 enrich_final_graph → architecture_final_graph; I7 task_trace_graph idempotency; I23 dual-mode YAML-only в research_snapshot_qa.*
