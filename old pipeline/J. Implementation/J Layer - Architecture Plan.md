# J Layer — Architecture Plan

**Дата:** 2026-06-23  
**Ревизия:** R18  
**Статус:** DRAFT

**R1 (2026-06-23):** первичный план — J0-диспетчер, j_layer_run.yaml, 5 типов задач, 20 принципов кода, git-ветки.

**R2 (2026-06-23):** task_type/execution_chain разделены на две оси (§2); J0/J-runner разделены (§4); snapshot_mode: research_only | implementation явно в алгоритме J0 (§3); J9 Dependency Auditor перемещён до J5/J6 (§6); J8 Static Analyzer перед J7 Test Runner (§6); атомарный коммит-юнит J6+J8+J7 (§7); git_checkpoint механизм (§7); pipeline.db разделён на read-only и writable namespace (§8); migration и qa как отдельные execution_chain (§6); migration_guard и rollback dry-run (§6); preflight проверка task_spec перед стартом задачи (§3); budget_escalation_response.yaml resume-протокол (§5); spike_rejection.yaml дополнен provenance_category и blast_radius (§5).

**R3 (2026-06-23):** восстановление после системного сбоя — startup reconciliation в J-runner (§4.1); динамический запрос зависимости из J6 — dependency_amendment path (§6.2 + §5.2); LOC-метрика как триггер budget_exceeded удалена, заменена тремя измеримыми условиями (§3.5); глобальный счётчик coding_unit_attempt_count уточнён + max_coding_unit_attempts в task_spec (§6.2 + §5.2); семантика rollback_strategy для миграций разделена на strategy (I-слой) + code (J6) (§6.6); параллельное выполнение независимых задач — pipelined execution mode (§3.6 + §5.1).

**R4 (2026-06-23):** исправлен порядок J4→J9 в цепочках (J4 formирует proposed_dependencies, J9 аудирует их — §6 + §5.2); добавлен `spike_rejected` в статус-enum j_layer_status (§5.1) и `spike_resolved` в j_task_status_edges (§8); batch_id: 0/N заменён на execution_phase: strict_first | implementation + batch_order (§3.1, §3.4.1, §5.2); синхронизирован trigger.type в budget_escalation_request.yaml с R3-триггерами (§5.3); уточнены имена баз данных J-runner (pipeline.db/causal_graph.db — §8); исправлен research_only spike_resolution flow: после успешного architecture_global spike J возвращает управление I-оркестратору, а не «разблокирует impl-задачи» (§6.1); pipelined mode дополнен resource_locks и revalidation-after-merge (§3.6); dependency amendment дополнен worktree-протоколом stash/audit/unstash (§6.2.1).

**R5 (2026-06-23):** после исчерпания coding_unit_max_attempts блок заменён на J21 HITL Coder Session — совместную творческую сессию агент+человек (§6.2.2 + §9); после успешного J21 — один финальный collaborative_attempt; после неуспешного J21 — budget_escalation; устранена путаница "max 2" в таблице (§6.2); j_layer_run.yaml получил hitl_coder_sessions_count и collaborative_attempt_used (§5.2); j_layer_summary.yaml получил hitl_coder_sessions_total (§5.6).

**R6 (2026-06-23):** исправлена нумерация ревизии в заголовке (R3→R6); убраны все ссылки на batch_id: 0 — заменены на execution_phase: strict_first (§1, §2, §11); §10 pipeline.db → causal_graph.db как вход J-слоя; §7.1 J9 commit_group исправлен (solo, не null); порядок J14→J9 в infra_code и J4→J9 в migration (§6.5, §6.6); integration chain: J6+J8+J7 как coding_unit при requires_glue_code: true (§6.7); config chain дополнен явным шагом validation_commands (§6.9); research_only spike success: отдельный j_spike_resolution_signal.yaml вместо budget_escalation_response.yaml (§6.1 + §5.8); закрыт OQ-J-010; spike_rejection.yaml blast_radius выравнен с I-R9 (§5.5); pipelined mode помечен как future — MVP только sequential (§3.6 + §11); добавлены инварианты #20 (J0 не изменяет task_spec) и #21 (первый production-run — sequential).

**R7 (2026-06-25):** `tasks.db` закреплён как canonical task queue, а `frozen_snapshot.yaml` — как манифест с hash/path (§1, §3.4, §10); runtime-статусы J вынесены из frozen `causal_graph.db` в отдельный `j_runtime.db` (§8); `pending_i_layer_response` разделён с `awaiting_implementation_snapshot` для successful research-only spike (§3.1, §5.1, §6.1); добавлен `acceptance_evidence.yaml` как проверяемое доказательство выполнения acceptance_checks (§3.7, §5.9); `coding_unit_attempt_count` уточнён: инкрементируется при новом полном проходе J6→J8→J7, а static fix cycles считаются отдельно (§6.2, §11); migration guard синхронизирован с `rollback_strategy` от I21 (§6.6); git safety усилен: J-runner работает в isolated worktree и не выполняет destructive reset в пользовательском checkout (§4.2, §7.2); OQ-J-006/OQ-J-007 закрыты после обновления I21 schema (§14).

**R8 (2026-06-25):** устранены остаточные несостыковки J-runner contract: §3.3 ветка `budget_exceeded` перенумерована в `f)` и checkpoint naming синхронизирован с `before_coding_unit` / `before_collaborative_attempt`; старт задачи и §7.3 переведены на `git worktree add`; startup reconciliation теперь сканирует `git worktree list` вместе с ветками `j/*`; `current_task_id` объявлен derived alias от `active_task_ids[0]`; добавлен `j_runner_signal.yaml`; OQ-J-003/OQ-J-005 закрыты, OQ-J-008/OQ-J-009 помечены future-only; `j_runtime.db` получил ссылки `archived_run_path/hash` для audit trail; верхнее описание обновлено до J1–J21 (R11 расширяет до J22).

**R9 (2026-06-25):** закрыт crash window после remote PR merge: PR create/merge объявлены идемпотентными операциями, J-runner перед create/merge делает lookup PR по head branch, startup reconciliation использует GitHub PR state как source of truth для PR/merge boundary, а `j_runtime.db` хранит `pr_number`, `remote_pr_state`, `merge_commit_hash`, `remote_checked_at`.

**R10 (2026-06-25):** закрыты blind spots budget/dependency/merge: перед destructive reset J-runner экспортирует escalation evidence в protected artifact store вне `.j-worktrees`; rejected dependency amendment передаётся J6 как явный context bundle с `dependency_audit.yaml#rejection_reason`; collaborative_attempt сохраняет внутренний J6↔J8 static-fix loop в пределах `max_static_fix_iterations`, но не даёт нового полного J7 attempt; merge gate стал chain-aware и проверяет только артефакты, предусмотренные фактической step_chain/execution_chain.

**R11 (2026-06-25):** добавлена цепочка `external_manual` для `task_type: human_action`: ручные действия во внешних системах (cloud/payment/app-store/DNS/account/secret provisioning), которые агент не может выполнить сам. Добавлен J22 External Manual Action, `human_action_result.yaml`, статус ожидания `waiting_for_external`, запрет branch/PR/code diff для external_manual и строгая политика секретов: в артефактах только `secret_ref`/`vault_path`/`env_var_name`/fingerprint, никогда secret value.

**R12 (2026-06-25):** уточнены edge flows для K-аудита: `j_layer_summary.yaml` получил minimal schema для `spike_rejected`; `idle` initialization явно создаётся J-runner при первом запуске; `human_action_result.yaml` включается в summary/audit refs; `config_validation_report.yaml` добавлен как артефакт J-runner; `spike_rejected` теперь различает `architecture_global` и локальные blast_radius; migration chain получил J9b при lockfile diff; infra_code явно блокируется без J21 после исчерпания J15+J8 попыток; dependency amendment records получили `rejection_context_ref`.

**R13 (2026-06-26):** J-runner упразднён как отдельная концепция. J0 переведён в режим Dispatcher-Orchestrator: запускает агентов J1–J22 как subagents через Agent tool, выполняет git-операции и CI через bash-инструменты в рамках одной Claude Code сессии. Пользователь запускает J0 — J0 ведёт задачу до точки остановки (HITL, external_manual, CI ожидание, budget escalation, blocked, complete). `j_runner_signal.yaml` упразднён. `j_runtime.db` переходит под управление J0. Startup reconciliation выполняет J0 при каждом запуске.

**R14 (2026-07-07):** синхронизирована граница с K R2. `j_layer_summary.yaml`, `j_runtime.db`, `acceptance_evidence.yaml` и `human_action_result.yaml` остаются J audit trail и operational evidence, но больше не являются entrypoint/source-of-truth для независимого K product audit. При `status: complete` J0 сообщает человеку, что можно вручную запустить K через `k_trigger_signal.yaml` с явным `target_ref`/A–E hashes/external evidence refs; K сам реконструирует продукт из primary sources.

**R15 (2026-07-14):** граница синхронизирована с K R5: удалено остаточное утверждение, что K читает `dependency_amendment_requests[].rejection_context_ref`; это поле и связанные dependency/spike details остаются только J audit trail для J0/человека. J0/J2/J9 prompts выровнены с тем же запретом и новым human trigger contract, включая проверяемый `authorization_context_ref` для privileged K decisions.

**R16 (2026-07-14):** human handoff синхронизирован с K R6 / `k_trigger_signal.yaml` schema 1.2. Независимость K от J не меняется; J только перечисляет человеку обязательные trigger inputs и не передаёт собственные audit artifacts.

**R17 (2026-08-17):** синхронизация с фактическим текущим состоянием `J0. Dispatcher.md`/`J13. HITL UI.md`/`J14-J0-J16-J17 Generation And State Schemas.md`, которые с R16 прошли собственные раунды hardening без параллельного обновления этого документа. Заменена устаревшая схема J13 `hitl_ui_approval.yaml` на реальный двухраундовый протокол `hitl_ui_request_<session_id>.yaml`/`hitl_ui_result_<session_id>.yaml` (§5.1, §5.9, §6.4, §7.3, §11, §12); добавлена обязательная Approval Gate между каждым subagent-вызовом J0 (§1, §3.1, §3.3), новые значения `waiting.kind` (`next_subagent_approval`, `hitl_ui_authorization_pending` — §5.1); добавлен терминальный acceptance-статус `not_applicable_confirmed` (§5.9, §7.3, §11); добавлено упоминание `j_acceptance_index.yaml`, `j0_task_lease.yaml`, `j14_generations/`/`j14_state.yaml`, `j_handoff_signal.yaml` (§10, §12) как реально используемых, но ранее не задокументированных здесь механизмов; §5.5 `spike_rejection.yaml` помечена явной ссылкой на `J3. Spike Resolver.md` как единственный источник истины для полной схемы (тем же способом, что уже применён в §5.7 для J21); в §3.3 добавлено обязательное поле `budget.max_spike_retry_attempts` (только `research_spike`). Это правки только этого документа под факты, зафиксированные в промптах — сами промпты (J0/J13/J3/J-регрессионная матрица) в рамках этой же правки дополнительно синхронизированы отдельно (см. J0.md "Обязательная re-pin проверка перед round 2" и `J13 HITL UI Protocol - Regression Matrix.md` #N26b).

**R18 (2026-08-20):** усилен сквозной контракт research spike между J0/J1/J2/J3: канонические ID берутся из `task_spec.provenance`, добавлены hash/attempt bindings и acceptance-index identity, закрытый каталог J1 gates, единое хранение assumptions, evidence-bound impacts, безопасный archive-before-retry и batch-local routing для `research_only`. Схемы `spike_findings.yaml` и J3 outcome artifacts подняты до 1.1. До синхронизации upstream I21 отсутствие `budget.max_spike_retry_attempts` совместимо и означает default `2`, а не preflight failure.

---

## 1. Назначение слоя

J-слой выполняет граф задач, произведённый I24. Точка входа — `frozen_snapshot.yaml`. Режим выполнения определяется полем `snapshot_mode`.

```
frozen_snapshot.yaml (от I24)
  snapshot_mode: research_only | implementation
        ↓
J0  manual orchestrator-executor (VS Code / Claude Code сессия, запускается человеком)
    — читает runtime state
    — выбирает задачу и шаг
    — запускает агентов J1–J22 как subagents через Agent tool
    — выполняет bash/git/gh/validation-команды
    — ведёт runtime-артефакты и j_runtime.db
    — создаёт PR, ждёт CI, выполняет merge
    — останавливается в terminal/waiting states, а также после КАЖДОГО запуска subagent —
      до прямого согласия пользователя на конкретный следующий subagent (Approval Gate, §3.1, §3.4)
        ↓
[если snapshot_mode: research_only]
  только research_spike chain — через spike_execution_context.yaml
  запрещено: system_architecture.final.yaml, impl-задачи
        ↓
[если snapshot_mode: implementation]
  фаза strict_first: задачи с execution_phase: strict_first (research_spike chain)
  фаза implementation: impl-задачи с execution_phase: implementation по execution_chain из task_spec
        ↓
J0 сообщает человеку: J-слой complete; K можно запускать только вручную через k_trigger_signal.yaml
```

Пользователь запускает J0 как Claude Code / VS Code-сессию. Системные операции выполняет J0 в рамках текущей интерактивной сессии. Отдельного runner, daemon, background process или автоматического оркестратора в J-слое нет. J0 ведёт задачу от начала до конца, но не проходит несколько шагов подряд автономно: после **каждого** завершённого subagent J0 обязан остановиться и получить прямое согласие пользователя на конкретный следующий subagent (Approval Gate между subagents, §3.1, §3.4) — это дополнительная точка остановки сверх terminal/waiting states, во всех случаях с записью явных инструкций по resume.

`tasks.db`, опубликованный I24, является единственным canonical task queue для J. `frozen_snapshot.yaml` не дублирует список задач: он указывает `tasks.db` path/hash и фиксирует `snapshot_mode`. `causal_graph.db` в J-слое read-only и используется только для трассировки task → architecture/story.

---

## 2. Два словаря: task_type и execution_chain

В J-слое намеренно разделены две разные оси:

```
task_type      = природа работы (что делаем)
execution_chain = способ исполнения (как исполняем)
```

**task_type** — канонический словарь I-слоя, иммутабелен:

```
research          — spike/исследование
infrastructure    — инфраструктурный код
config            — конфигурация и параметры
code.domain_logic — бизнес-логика
code.adapter      — адаптер к внешней системе
code.migration    — миграция данных или схемы
code.contract     — тип/интерфейс/контракт
code.orchestration — координационная логика
qa                — тестирование, проверка качества
human_action      — внешнее ручное действие: console setup, account setup, secret provisioning
```

**execution_chain** — словарь J-слоя, как именно выполнять задачу:

```
research_spike   — исследование; execution_phase: strict_first
server_code      — серверная реализация
client_code      — клиентская реализация без UI
ui_code          — реализация UI + HITL-сессия
infra_code       — инфраструктурный код (IaC)
migration        — миграция данных с rollback-проверкой
integration      — интеграция компонентов + нагрузочные тесты
qa               — автономная QA-задача
config           — конфигурационные изменения
external_manual  — ожидание и проверка ручного действия человека во внешней системе
```

**Откуда берётся execution_chain:** только из `task_spec.execution.chain`, установленного I21. J0 не выводит цепочку самостоятельно ни при каких обстоятельствах. Если поле отсутствует — task_spec invalid, возврат в I21/I23.

**Пример соответствия:**

| task_type | execution_location | execution_chain |
|---|---|---|
| code.domain_logic | server | server_code |
| code.adapter | server | server_code |
| code.domain_logic | on_device (Elm) | ui_code |
| code.migration | server | migration |
| code.contract | server | server_code |
| code.orchestration | server | server_code |
| infrastructure | — | infra_code |
| config | — | config |
| qa | — | qa |
| research | — | research_spike |
| human_action | — | external_manual |

---

## 3. J0 — Dispatcher-Orchestrator

J0 — единственная точка входа в J-слой, запускается пользователем как Claude Code сессия. J0 совмещает логическое диспетчирование и исполнение: запускает агентов J1–J22 как subagents через Agent tool и выполняет системные операции (git, CI, PR, merge, запись в j_runtime.db) через bash-инструменты.

### 3.1 Алгоритм J0

```
0. Если `j_layer_status.yaml` отсутствует:
   • J0 создаёт initial idle документ (§5.1):
     status: idle, active_task_ids: [], current_task_id: null
   • J0 продолжает с шага 2

1. Читаем j_layer_status.yaml
   • status: idle → переходим к шагу 2
   • status: complete → «J-слой завершён, переходим к K-аудиту»; СТОП
   • status: aborted  → «J-слой прерван: {reason}»; СТОП
   • status: pending_i_layer_response → ждём budget_escalation_response.yaml (§3.6)
   • status: awaiting_implementation_snapshot → ждём новый frozen_snapshot.yaml с snapshot_mode: implementation (§6.1)
   • status: waiting_for_external → маршрутизация по `waiting.kind`: `hitl_ui`/`hitl_coder`/`external_manual` (§6.10) ждут артефакт от человека/HITL-сессии; `next_subagent_approval` ждёт прямое согласие пользователя на конкретный следующий subagent (Approval Gate, §3.4) — без него J0 не запускает следующий шаг; `hitl_ui_authorization_pending` ждёт валидный participant authorization grant для J13 round 2, отдельно от обычного ожидания ответа человека на checklist; `blocked_until_j0_budget_decision` ждёт разрешения конкретного deferred decision (JIT readiness flag J4/J14/J18, operator attestation, provide_secret_ref — см. J0.md); `ci_checks`/`remote_unavailable` ждут внешнюю систему
   • status: blocked  → «Задача {task_id} завершилась ошибкой. Требуется вмешательство»; СТОП

2. Определяем snapshot_mode из frozen_snapshot.yaml
   • research_only → только research_spike задачи; читаем spike_execution_context.yaml; переходим к шагу 4
   • implementation → полный pipeline; читаем system_architecture.final.yaml + tasks.db + task_specs/

3. Phase gate (только для implementation):
   Если существуют незакрытые задачи с execution_phase: strict_first → ТОЛЬКО их рассматриваем
   (execution_phase берётся из task_spec.execution.execution_phase; значения: strict_first | implementation)
   Примечание: I-слой использует строковые batch_id (BATCH-001, BATCH-02, …); J читает
   task_spec.execution.execution_phase, а для относительного порядка внутри фазы —
   task_spec.execution.batch_order (число). Числовые batch_id: 0/1 не используются в J.

4. Определяем текущее действие:
   a) j_layer_run.yaml существует, current_step_index < len(step_chain):
      → RESUME: продолжаем текущую задачу с current_step (§3.4), но только при наличии
        прямого согласия пользователя на этот конкретный следующий subagent (Approval Gate, §3.4);
        без него → status: waiting_for_external, waiting.kind: next_subagent_approval; СТОП
   b) j_layer_run.yaml отсутствует или current_step_index == len(step_chain):
      → NEXT TASK: берём следующую задачу (§3.5)
   c) Все задачи завершены:
      → FINALIZE: создаём j_layer_summary.yaml (схема — §5.6)
```

### 3.2 Worktree isolation rule

J0 не работает в основном рабочем дереве пользователя и в ветке `main`. Для каждой non-external_manual задачи J0 создаёт или переиспользует изолированный worktree:

```
.j-worktrees/{task_id}    ← все кодовые изменения только здесь
branch: j/{task_id}/{slug}
```

Запрещено:
- `git checkout -b <branch>` в основном checkout
- `git commit` в основном checkout
- `git reset --hard`, `git checkout -- .`, `git clean` в основном checkout

### 3.3 Preflight-проверка task_spec

Перед созданием j_layer_run.yaml для новой задачи J0 проверяет наличие обязательных полей:

```yaml
# обязательные поля
task_id:            required
task_type:          required, in canonical I-layer set
execution:
  chain:            required, in J-layer set
  reason:           required
  execution_phase:  required, strict_first | implementation
  batch_order:      required, number
files_allowed_to_touch: required (список; может быть wildcard для новых файлов)
acceptance_checks:  required
validation_commands: required
provenance:         required
artifact_refs:      required
resource_locks:     required (список; может быть пустым)
triggers_module_complete: required, boolean
budget:
  max_unspecified_decisions: required, number (I21 default 3)
  max_coding_unit_attempts: required, number (I21 default 3)
  max_static_fix_iterations: required, number (I21 default 3)
  max_spike_retry_attempts: optional только для execution.chain: research_spike, non-negative integer —
    если I21 не материализовал J-specific поле, J0 фиксирует default 2 в j_layer_run.yaml;
    ограничивает цикл J3 spike_retry → J1 и используется J3 при spike_rejection (retry_limit_warning)

# блокирующие условия
blocked_by_spikes:  если not empty → задача ждёт, СТОП
data_loss_risk: true + accepted_risk_id: missing → СТОП
task_type: human_action + execution.chain != external_manual → СТОП
execution.chain: external_manual + human_action missing → СТОП
```

Если любое из блокирующих условий истинно — J0 не создаёт ветку и не запускает шаги. Отчёт пользователю с указанием причины.

Для `execution.chain: external_manual` поле `files_allowed_to_touch` должно быть `[]`: задача не имеет code diff. J0 проверяет `human_action.secrets_policy: never_write_secret_value_to_repo`; если task_spec содержит явное значение секрета вместо ссылки, задача немедленно `blocked`.

### 3.4 Выполнение шага (RESUME)

**Approval Gate между subagents (обязателен перед каждым шагом 3 ниже).** J0 не запускает следующего subagent автоматически после предыдущего — согласие пользователя не переносится между агентами. Перед каждым вызовом Agent tool J0 обязан иметь прямое согласие пользователя на конкретный запуск в текущей сессии (например: «запусти J6 для T-042»), полученное после того, как J0 показал результат предыдущего subagent. Общая команда вида «выполни J0» разрешает только первый выбираемый subagent, не всю цепочку. Без такого согласия J0 не выполняет шаг 3: вместо этого он выставляет `j_layer_status.status: waiting_for_external`, `waiting.kind: next_subagent_approval`, `waiting.resume_instruction` с именем следующего subagent и task_id, и останавливается. Полный контракт (operator-facing сообщения до/после subagent) — см. `J0. Dispatcher.md`, «Approval Gate между subagents».

```
0. Approval Gate: без прямого согласия пользователя на этот конкретный шаг — СТОП (см. выше)
1. step = step_chain[current_step_index]
2. Перед запуском:
   • для coding_unit: J0 фиксирует git_checkpoint.before_coding_unit (§7.2) через bash
   • для collaborative_attempt: J0 фиксирует git_checkpoint.before_collaborative_attempt (§7.2) через bash
   • для solo-шагов: отдельный checkpoint не нужен; при failure до commit J0 сбрасывает task-owned worktree
3. J0 запускает агента как subagent через Agent tool (читает промпт из J. Implementation/<agent>.md)
4. Агент производит YAML-артефакты в TEST WORKFLOW/10. J. Implementation RS/{task_id}/
5. По результату:
   a) success:
      • J0 обновляет j_layer_run.yaml: step.status: complete, artifacts
      • J0 выполняет коммит через bash (если шаг входит в commit-группу — см. §7.1)
      • current_step_index++
   b) step_failed (retry допустим):
      • J0 сбрасывает к git_checkpoint.before_coding_unit для coding_unit через bash
      • для solo-шагов без commit: J0 очищает task-owned worktree через bash
      • retry_count++; возвращаемся к шагу 3
   c) step_failed (coding_unit, coding_unit_max_attempts исчерпан, collaborative_attempt_used: false):
      • J21 HITL Coder Session (§6.2.2)
   d) step_failed (coding_unit, collaborative_attempt также провалился или J21 → needs_i_layer):
      • needs_i_layer / task_scoped_down → §3.6 (budget_escalation)
      • collaborative_attempt failed → §3.9 (эскалация провала)
   e) step_failed (retry исчерпан, не coding_unit):
      • J0 пишет j_layer_run.yaml: step.status: failed
      • Эскалация провала (§3.9)
   f) budget_exceeded:
      • J0 сбрасывает к git_checkpoint.before_coding_unit или git_checkpoint.before_collaborative_attempt через bash
      • Эскалация в I-слой (§3.6)
6. Отчёт: «Шаг {step} завершён. Следующий: {next_step}» или «Задача завершена»
```

### 3.5 Старт новой задачи

```
1. Берём первую незаблокированную задачу из tasks.db (§3.5.1)
2. Выполняем preflight (§3.3)
3. J0 создаёт j_layer_run.yaml с execution_chain из task_spec
4. Если `execution_chain: external_manual` (порядок важен — launch → validate → set waiting, см. J0.md «Special Flow: External Manual»; выставлять waiting до запуска subagent противоречило бы предусловию Step Dispatch «J0 не ожидает manual intervention»):
   • J0 НЕ создаёт git worktree и НЕ создаёт branch/PR
   • J0 запускает J22 как subagent; J22 показывает человеку structured checklist и создаёт template `human_action_result.yaml` со `status: pending` (§6.10)
   • J0 читает созданный template и подтверждает успех шага
   • Только теперь J0 обновляет j_layer_status.yaml: status=waiting_for_external, waiting.kind=external_manual, active_task_ids=[task_id]; останавливается; ждёт заполненный `human_action_result.yaml` при следующем запуске
5. Иначе: J0 через bash: git worktree add .j-worktrees/{task_id} -b j/{task_id}/{slug} origin/main
6. current_step_index: 0
7. J0 обновляет j_layer_status.yaml: active_task_ids; current_task_id пересчитывается как derived alias
8. Переходим к §3.4
```

**3.5.1 Выбор задачи:**
- Из `tasks.db` (порядок материализован I24 из I20/I21)
- Исключаем: completed (в j_layer_status.yaml), задачи со `status != 'ready'` в tasks.db (CHECK-констрейнт I24 допускает только `ready | deferred`; статуса `blocked` в tasks.db не существует), задачи с незавершёнными `depends_on`, задачи с `execution_phase: implementation` пока открыты задачи с `execution_phase: strict_first`
- Среди незаблокированных: сортируем по `execution.batch_order` (возрастание), затем по `task_id`

### 3.6 Бюджет и эскалация в I-слой

**Формальные триггеры budget_exceeded (любой из):**

1. **Decision overflow** — J6 сталкивается с более чем N дизайн-решениями, не покрытыми task_spec или methodology_review. N берётся из `task_spec.budget.max_unspecified_decisions` (дефолт: 3). Каждое такое решение J6 обязан явно зафиксировать в артефакте перед эскалацией.

2. **Scope expansion** — J6 обнаруживает, что задача требует изменений в файлах за пределами `task_spec.files_allowed_to_touch`. Это сигнал о недооценённой области, а не просто нарушение правила (нарушение правила → step_failed; требование расширения → budget_exceeded).

3. **Technology fundamental gap** — одобренных библиотек фундаментально недостаточно для требуемой функциональности, и проблема не решается через dependency amendment (§6.2.1). Это означает, что task_spec построен на неверных технологических допущениях.

**Удалено (R3):** `estimated_loc × 1.5` как триггер. LLM-агенты генерируют более многословный код по сравнению с эталоном, и жёсткая привязка к количеству строк неизбежно производит ложные эскалации. Объём кода — следствие дизайн-решений, а не самостоятельная метрика.

**Действия при budget_exceeded:**

```
1. J0: экспортирует protected escalation evidence из task-owned worktree
   в `TEST WORKFLOW/10. J. Implementation RS/{task_id}/escalation_evidence/`
   (вне `.j-worktrees/{task_id}` и вне зоны `git reset --hard`)
2. J0: записывает `escalation_evidence_manifest.yaml` с path/hash каждого evidence-файла
3. J0 через bash: сброс task-owned worktree к git_checkpoint.before_coding_unit или
   git_checkpoint.before_collaborative_attempt (никаких частичных изменений в ветке)
4. J0: обновляет j_layer_run.yaml: step.status: budget_exceeded
5. J0: пишет budget_escalation_request.yaml (§5.3), включая ссылки на `escalation_evidence_manifest.yaml`
6. J0: обновляет j_layer_status.yaml: status: pending_i_layer_response
7. J0 останавливается; отчёт пользователю с деталями
```

**Protected evidence rule:** любые артефакты, которые объясняют `decision_overflow`, `scope_expansion` или `technology_fundamental_gap`, должны быть скопированы из worktree в protected artifact store до reset. I-слой читает только protected копии и их hashes; partial code в ветке после reset не сохраняется.

**Resume после ответа I-слоя:**

J0 при status: pending_i_layer_response ищет `budget_escalation_response.yaml`:
- Не найден → «Ожидаем ответа I-слоя»; СТОП
- Найден с status: resolved:
  1. J0 загружает новый frozen_snapshot (по `new_snapshot_id`)
  2. J0 через bash удаляет текущую ветку (или архивирует worktree)
  3. Задачи из `superseded_task_ids` помечаются superseded в j_layer_status.yaml
  4. Новые задачи из `new_task_ids` добавляются в очередь
  5. J0 обновляет j_layer_status.yaml: status: running
  6. Продолжаем с шага 3.1

### 3.7 Режим параллельного выполнения (Pipelined) [Not designed — requires runner]

> **Не проектировать сейчас.** В ручной модели (J0 = manual session) pipelined режим неприменим: нет отдельного runner-компонента, который мог бы управлять несколькими execution lanes между запусками J0. Будущая поддержка потребует либо явного multi-worktree manual lane protocol, либо реинтродукции отдельного runner. До этого moment `execution_mode` всегда `sequential`.
>
> Описание ниже сохранено как reference для возможной будущей реализации, но не является actionable частью текущего плана.

По умолчанию J-runner выполняет задачи последовательно (`execution_mode: sequential`). Для проектов с независимыми задачами поддерживается режим `pipelined`.

**Условия запуска задачи в параллель:**
1. `active_task_ids` содержит менее `max_concurrent_tasks` элементов (дефолт: 3)
2. Новая задача прошла resource conflict check (см. ниже)
3. У новой задачи нет транзитивной зависимости `blocked_by` ни от одной из активных задач
4. Обе задачи не входят в одну migration chain (параллельные миграции запрещены)

**Resource conflict check (R4):** простой сравнение списков `files_allowed_to_touch` недостаточен. J-runner выполняет:

```
shared_resources: [
  "package-lock.json", "yarn.lock", "pnpm-lock.yaml",  # lockfile — любая установка пакета меняет его
  "tsconfig.json", ".eslintrc*", "jest.config.*",       # shared config
  "prisma/schema.prisma", "migrations/",                # schema/migration path
  # + все explicit resource_locks из task_spec
]

conflict_check(new_task, active_tasks):
  for each active in active_tasks:
    # 1. Wildcard expansion: src/**/*.ts vs src/auth/index.ts — пересечение
    if glob_intersect(new_task.files_allowed_to_touch, active.files_allowed_to_touch):
      return CONFLICT
    # 2. Directory overlap: src/auth/ vs src/auth/utils/ — пересечение
    if directory_overlap(new_task.files_allowed_to_touch, active.files_allowed_to_touch):
      return CONFLICT
    # 3. Shared resources
    if intersects(new_task.files_allowed_to_touch, shared_resources):
      if intersects(active.files_allowed_to_touch, shared_resources):
        return CONFLICT  # обе пишут в lockfile или shared config
    # 4. Explicit resource_locks
    if intersects(new_task.resource_locks, active.resource_locks):
      return CONFLICT
  return OK
```

**task_spec требование (R7):** I21 должен добавлять поле `resource_locks: []` всегда. Пустой список допустим; непустой список задаёт явные блокировки, которые не выводятся из files_allowed_to_touch (например, `"docker-registry:latest-tag"` или `"k8s-test-namespace"`).

**Revalidation after merge (R4):** когда соседняя ветка мержится в main, активные ветки могут устареть. J-runner обязан:
```
после каждого merge в main:
  для каждой активной задачи в active_task_ids:
    git fetch origin main
    git merge-base --is-ancestor HEAD origin/main → если нет:
      1. git rebase origin/main (или merge) на ветке задачи
      2. повторно запустить J8 (static analysis) + J7 (tests) на rebased ветке
      3. если rebase конфликт → задача переходит в status: rebase_conflict
         → J0 получает уведомление → escalate как step_failed
```

**Поведение J-runner в pipelined режиме:**
- J-runner ведёт N независимых execution lanes, каждый со своей git-веткой
- Если активная задача перешла в состояние ожидания (HITL, CI checks, budget_escalation) — J-runner немедленно стартует следующую подходящую задачу из очереди
- J0 по-прежнему вызывается последовательно: J-runner передаёт J0 один активный lane за раз, по round-robin
- `j_layer_status.yaml` хранит `active_task_ids: []`; `current_task_id` остаётся derived alias и не используется для планирования pipelined lanes
- J_layer_run.yaml каждой задачи находится в своей папке `{task_id}/j_layer_run.yaml` — изоляция обеспечена структурой директорий

**Не поддерживается в pipelined режиме:** задачи типа `migration` (data integrity требует строгой последовательности).

### 3.8 Завершение задачи

```
1. J0 через bash: запускает validation_commands из task_spec (для config chain)
2. J10 пишет quality_report.yaml с acceptance_evidence_map (каждый acceptance_check -> evidence_ref); J10 сам acceptance_evidence.yaml не создаёт. J0 собирает acceptance_evidence.yaml (§5.9) из quality_report.yaml#acceptance_evidence_map (+ `hitl_ui_result_<session_id>.yaml` для ui_code — итог двухраундовой J13-сессии `hitl_ui_request_<session_id>.yaml`/`hitl_ui_result_<session_id>.yaml`, см. §6.4) — для config/infra_code из соответствующих validation/deployment отчётов, для external_manual его создаёт J22 сам
3. J0 проверяет acceptance_evidence.yaml: каждый acceptance_check — `status: satisfied`, `status: gap_allowed_partial_contract` (авторизованный J5 permanent gap) либо `status: not_applicable_confirmed` (J13-confirmed inapplicability для human_ui checks — отдельный провенанс, не смешивать с предыдущим); `pending_downstream`/`deferred_to_downstream` не считается достаточным до разрешения downstream-агентом
4. J0 через bash: ищет PR по head branch `j/{task_id}/{slug}` (§7.3)
   • если PR отсутствует → создаёт PR
   • если PR уже OPEN → переиспользует существующий PR, не создаёт дубль
   • если PR уже MERGED → переходит к шагу 8 (local finalize)
5. J0: записывает `pr_number`, `pr_url`, `remote_pr_state`, `remote_checked_at` в j_runtime.db
6. J0 через bash: ждёт CI/automated checks (`gh pr checks --watch`)
7. Перед merge J0 повторно читает remote PR state:
   • MERGED → merge уже выполнен; перейти к шагу 8
   • OPEN + checks passed → `gh pr merge`
   • CLOSED без merge → task_failed / manual intervention; J0 останавливается
8. J0 через bash: повторно читает PR state после merge; записывает `merged_at`, `merge_commit_hash`, `remote_pr_state: MERGED`
9. J0: обновляет j_runtime.db — j_task_status_edges: task → complete (§8)
10. J0: обновляет j_layer_status.yaml: task → complete
11. J0: архивирует j_layer_run.yaml → archive/j_layer_run.{task_id}.archived.yaml
12. Отчёт
```

**Idempotency rule:** `gh pr create` и `gh pr merge` никогда не выполняются вслепую. Перед `create` J0 ищет PR по head branch. Перед `merge` J0 проверяет remote PR state. Если remote state уже `MERGED`, локальное состояние догоняет GitHub и повторный merge не выполняется.

### 3.9 Эскалация провала задачи

```
1. J0: НЕ удаляет ветку (сохраняется для диагностики)
2. J0: пишет j_task_failure_report.yaml
3. J0: обновляет j_layer_status.yaml: status: blocked, blocked_task_id
4. J0 останавливается. Отчёт: «Задача {task_id} не выполнена. Требуется вмешательство.»
```

---

## 4. Системные операции J0

J0 выполняет системные операции через bash-инструменты в рамках той же Claude Code сессии, что и логические решения.

### 4.1 Startup reconciliation

При каждом запуске J0 сверяет фактическое состояние git-дерева с YAML-файлами. Это защита от рассинхронизации после аварийного завершения сессии.

**Источники истины (по приоритету):**
1. GitHub PR state — для PR/merge boundary (`OPEN`, `MERGED`, `CLOSED`).
2. Local git/worktree/log — для step-level recovery до PR.
3. `j_runtime.db` + `j_layer_status.yaml` — локальная проекция, которую J0 догоняет до фактов из 1–2.

```
STARTUP RECONCILIATION (выполняется до любых других операций):

1. Сканируем task-owned worktrees и ветки:
   • git worktree list
   • git branch -a | grep "j/"

2. Для каждой task-owned worktree `.j-worktrees/{task_id}`:
   a) сверяем путь worktree, branch `j/{task_id}/{slug}` и task_id
   b) проверяем наличие `{task_id}/j_layer_run.yaml`
   c) если worktree есть, но branch не `j/{task_id}/{slug}` → discrepancy

3. Для каждой ветки `j/{task_id}/{slug}` без worktree:
   a) восстановить worktree: `git worktree add .j-worktrees/{task_id} j/{task_id}/{slug}`
   b) если невозможно → пометить discrepancy, остановиться до manual intervention

4. Для каждой задачи с branch `j/{task_id}/{slug}` и status: in_progress:
   a) Проверяем remote PR state:
      `gh pr list --head j/{task_id}/{slug} --state all --json number,url,state,mergedAt,mergeCommit --limit 1`
   b) PR state = MERGED:
      - записать в j_runtime.db: status=complete, pr_number, pr_url, merged_at, merge_commit_hash
      - обновить j_layer_status.yaml: task → complete
      - архивировать j_layer_run.yaml
   c) PR state = OPEN → записать pr_number, remote_pr_state=OPEN; не создавать новый PR
   d) PR state = CLOSED без merge → task_failed; остановиться
   e) PR не найден → продолжить local step-level recovery

5. Для прерванных задач без MERGED PR:
   a) git log j/{task_id}/{slug} — парсим completed steps по pattern "[{task_id}] {step_name}:"
   b) Сверяем с j_layer_run.yaml; корректируем расхождения

6. Сверяем j_task_status_edges (j_runtime.db) с j_layer_status.yaml

7. Если discrepancies > 0 → выводим предупреждение перед продолжением
```

### 4.2 Git и CI операции J0

```
git_operations (через bash):
  - git worktree add .j-worktrees/{task_id} -b j/{task_id}/{slug}
  - git add <files_allowed_to_touch> && git commit -m "[{task_id}] {step_name}: ..."
  - git reset --hard {checkpoint}  — только внутри .j-worktrees/{task_id}
  - git checkout -- .              — только внутри .j-worktrees/{task_id}
  - git diff --name-only           — проверка files_allowed_to_touch после J6/J15

ci_and_pr (через bash/gh):
  - gh pr list --head j/{task_id}/{slug} --state all   (перед create/merge)
  - gh pr create                   — только если PR по head branch отсутствует
  - gh pr checks --watch           — ожидание CI
  - gh pr merge --squash           — только если remote PR state = OPEN и checks passed

j_runtime_db:
  - пишет только в j_task_status_edges (§8)
  - не открывает causal_graph.db на запись

artifact_enforcement:
  - проверяет наличие обязательных артефактов после каждого шага
  - отклоняет переход к следующему шагу при нарушении files_allowed_to_touch
```

**J0 не имеет права:**
- Делать git merge/reset в shared workspace пользователя (только в `.j-worktrees/{task_id}`)
- Изменять task_spec, tasks.db, causal_graph.db или frozen_snapshot.yaml

---

## 5. Схемы артефактов

### 5.1 j_layer_status.yaml

```yaml
schema_version: "1.0"
layer: J
snapshot_mode: research_only | implementation
snapshot_hash: sha256:{hash}         # hash frozen_snapshot.yaml
execution_mode: sequential           # MVP; pipelined только future
future_supported_modes: [pipelined]
max_concurrent_tasks: 3              # только для future pipelined
status: idle | running | waiting_for_external | pending_i_layer_response | awaiting_implementation_snapshot | spike_rejected | blocked | complete | aborted
current_phase: strict_first | implementation
active_task_ids: [T-042]             # для pipelined: может содержать несколько; для sequential: не более одного
current_task_id: T-042               # derived alias: active_task_ids[0] в sequential mode или null
pending_i_layer_response:            # заполняется при status: pending_i_layer_response
  request_id: BER-001
  created_at: 2026-06-23T11:00:00Z
  status: waiting_for_i | resolved
awaiting_implementation_snapshot:     # заполняется при status: awaiting_implementation_snapshot
  signal_id: SRS-T-003
  spike_id: SPIKE-003
  current_snapshot_mode: research_only
  expected_snapshot_mode: implementation
waiting_for_external:                 # заполняется при status: waiting_for_external
  task_id: T-020
  kind: hitl_ui | hitl_ui_authorization_pending | hitl_coder | external_manual | next_subagent_approval | blocked_until_j0_budget_decision | ci_checks | remote_unavailable
  # hitl_ui_authorization_pending: J13 round 2 ждёт валидный participant authorization grant —
  #   отдельно от hitl_ui (ожидание ответа человека на checklist); J13 не вызывается в этом состоянии
  # next_subagent_approval: J0 ждёт прямое согласие пользователя на конкретный следующий subagent
  #   (Approval Gate между subagents — см. §3.4 «Выполнение шага (RESUME)»)
  action_type: payment_console         # для external_manual
  external_system: stripe              # для external_manual
  expected_artifact: "TEST WORKFLOW/10. J. Implementation RS/T-020/human_action_result.yaml"
  expected_command: null               # для ci_checks: "gh pr checks <pr_number>"
  resume_instruction: "Заполни human_action_result.yaml и перезапусти J0"
  status: waiting | result_received | rejected
completed_tasks:
  - task_id: T-001
    task_type: code.adapter
    execution_chain: server_code
    completed_at: 2026-06-23T10:00:00Z
    branch_merged: j/T-001/stripe-adapter
    pr_url: https://github.com/.../pull/12
    commit_hash: abc123
failed_tasks: []
spike_rejected_tasks: []
superseded_tasks: []
total_tasks: 47
completed_count: 1
last_updated: 2026-06-23T10:00:00Z
```

**Правило согласованности active/current:**
- В `execution_mode: sequential` поле `active_task_ids` содержит 0 или 1 элемент.
- `current_task_id` должен быть равен `active_task_ids[0]`; если активных задач нет — `null`.
- В pipelined future-mode `current_task_id` не используется для принятия решений и остаётся только backward-readable alias.

### 5.2 j_layer_run.yaml

**Нормативная схема живёт в `J0. Dispatcher.md` (раздел «j_layer_run.yaml — Canonical Schema») — этот параграф даёт только структурную сводку для ориентации, не отдельный источник истины.** Реальная схема заметно шире и устроена иначе: плоский `step_chain` + параллельный массив `steps` (runtime-состояние), `available_toolchain`, durable-блок `hitl_ui` (state_revision/session.*/trust anchor refs), `hitl_review_attempt_count`, `amendment_sequence_in_attempt`, `round2_bounce_count`, `fixture_acknowledgments_index`, `coding_attempt_history`, `external_manual_template_generation`, `git_checkpoint.coding_unit_committed` и др. Если этот параграф и `J0. Dispatcher.md` расходятся, `J0. Dispatcher.md` побеждает; расхождение — баг документации, а не два легитимных варианта одного `schema_version` (тот же принцип, что §5.5/§5.7).

```yaml
schema_version: "1.0"
task_id: T-042
task_type: code.adapter              # из task_spec (I-layer canonical)
execution_chain: server_code         # из task_spec.execution.chain
execution_phase: strict_first | implementation   # из task_spec.execution.execution_phase
batch_order: 2                       # из task_spec.execution.batch_order (порядок внутри фазы)
task_title: "Stripe Checkout Adapter"
branch_name: j/T-042/stripe-checkout-adapter
started_at: 2026-06-23T10:00:00Z
resumed_count: 0
budget_escalation_count: 0
current_step_index: 3
step_chain:
  - step: j_methodologist
    agent: J4
    status: complete
    started_at: 2026-06-23T10:01:00Z
    completed_at: 2026-06-23T10:05:00Z
    retry_count: 0
    retry_allowed: false
    commit_group: solo               # коммитит самостоятельно
    artifacts:
      - methodology_review.yaml      # содержит proposed_dependencies
  - step: j_dependency_auditor
    agent: J9
    status: complete
    started_at: 2026-06-23T10:06:00Z
    completed_at: 2026-06-23T10:09:00Z
    retry_count: 0
    retry_allowed: false
    commit_group: solo
    artifacts:
      - dependency_audit.yaml        # approved/rejected по proposed_dependencies из J4
  - step: j_test_writer
    agent: J5
    status: complete
    commit_group: solo
    artifacts:
      - tests/adapters/stripe_checkout_test.ts
  - step: j_coder
    agent: J6
    status: in_progress
    retry_count: 0
    retry_allowed: true
    retry_max: 2
    commit_group: coding_unit        # коммитит вместе с J8+J7
    artifacts: []
coding_unit_attempt_count: 0         # ГЛОБАЛЬНЫЙ счётчик для всего блока J6→J8→J7
coding_unit_max_attempts: 3          # из task_spec.budget.max_coding_unit_attempts (дефолт: 3)
static_fix_iteration_count: 0        # локальный счётчик J6↔J8 внутри текущей попытки
hitl_coder_sessions_count: 0         # число запущенных J21 HITL Coder Session для этой задачи
collaborative_attempt_used: false    # true после J21 → финальный pass J6+J8+J7
dependency_amendment_requests:       # запросы J6 на новую зависимость в процессе кодирования
  - request_id: DAR-001
    package: "stripe-node"
    version: "^14.0"
    reason: "..."
    status: pending | approved | rejected
    rejection_context_ref: null       # заполняется при status: rejected
task_status: in_progress
git_checkpoint:
  before_coding_unit: abc123        # J0 записывает перед J6
  before_collaborative_attempt: null # J0 записывает перед collaborative_attempt (§6.2.2)
  coding_unit_commit: null          # заполняется когда J6+J8+J7 пройдены
external_manual:
  expected_result_path: null        # для execution_chain=external_manual: human_action_result.yaml
  result_hash: null
  no_branch_created: false          # true только для execution_chain=external_manual
```

### 5.3 budget_escalation_request.yaml

```yaml
schema_version: "1.0"
request_id: BER-{task_id}-{seq}
task_id: T-042
step: j_coder
trigger:
  type: decision_overflow | scope_expansion | technology_fundamental_gap
  # decision_overflow    — >N дизайн-решений вне task_spec (N = task_spec.budget.max_unspecified_decisions)
  # scope_expansion      — нужны файлы вне task_spec.files_allowed_to_touch
  # technology_fundamental_gap — approved libs фундаментально недостаточны (не решается dep-amendment)
  detail: "..."
  evidence_summary: "..."
  evidence_manifest_ref: "TEST WORKFLOW/10. J. Implementation RS/T-042/escalation_evidence_manifest.yaml"
  evidence_manifest_hash: sha256:{hash}
created_at: 2026-06-23T11:00:00Z
requested_action: task_decomposition | task_spec_update | technology_decision_update
context:
  task_spec_hash: sha256:{hash}
  frozen_snapshot_hash: sha256:{hash}
```

### 5.4 budget_escalation_response.yaml

```yaml
schema_version: "1.0"
request_id: BER-T-042-001
original_task_id: T-042
status: resolved | rejected | superseded
new_snapshot_id: frozen_snapshot_v2.yaml
superseded_task_ids: [T-042]
new_task_ids: [T-042a, T-042b]
action_for_j:
  - reload_snapshot
  - discard_current_run
  - resume_from_new_tasks
```

### 5.5 spike_rejection.yaml

**Нормативная схема живёт в `J3. Spike Resolver.md` (раздел «Выход: spike_rejection.yaml») — этот параграф даёт только структурную сводку для ориентации, не отдельный источник истины.** Реальная схема заметно шире: она дополнительно включает `task_id`, `open_question_id`, `outcome`, `snapshot_mode`, `spike_retry_count`/`retry_limit_warning`, `primary_rejection_category`/`rejection_categories`, `spike_forbidden_reason`, `recommended_owner`, `source_artifacts`, `decision_basis`, `blocking_items[]`, `not_accepted_assumptions[]`, `affected_ref_conclusions[]`, `downstream_impacts[]`, `acceptance_check_coverage[]`, `routing{...}`, `evidence_refs[]`, `traceability{...}`, `self_audit{...}` и `affected_component_ids_resolution`. Если этот параграф и `J3. Spike Resolver.md` расходятся, `J3. Spike Resolver.md` побеждает; расхождение — баг документации, а не два легитимных варианта одного `schema_version` (тот же принцип, что уже применён в §5.7 для `j_hitl_coder_session.yaml`/J21).

```yaml
schema_version: "1.1"
spike_id: SPIKE-003
spike_task_id: T-003
provenance_category: i_layer_initiative | upstream_requirement
blast_radius: architecture_global | component | optimization
  # architecture_global — затрагивает всю архитектуру; implementation flow останавливается,
  #                        а research_only batch следует §6.1 и останавливается только при explicit batch invalidation либо после finalization
  # component           — затрагивает один или несколько компонентов
  # optimization        — только производительность / качество; архитектура стабильна
affected_process_ids: [P-01, P-02]
affected_invariant_ids: [INV-03]
affected_interaction_ids: [INT-05]
affected_component_ids: [C-07, C-08]
rejection_reason: "..."
findings_summary: "..."
impact_on_architecture: "..."
recommended_action: layer_rollback | architecture_revision | spike_retry
created_at: 2026-06-23T09:00:00Z
```

### 5.6 j_layer_summary.yaml (финальный артефакт J-layer)

```yaml
schema_version: "1.0"
layer: J
status: complete
snapshot_mode: implementation
started_at: ...
completed_at: ...
total_tasks: 47
completed_tasks: 47
failed_tasks: 0
spike_tasks_resolved: 3
migrations_completed: 2
hitl_sessions: 1
hitl_coder_sessions_total: 0
human_actions_completed: 0
human_action_tasks:
  - task_id: T-020
    external_system: stripe_dashboard
    action_type: webhook_setup
    status: completed
    result_ref: "T-020/human_action_result.yaml"
    acceptance_evidence_ref: "T-020/acceptance_evidence.yaml"
modules_deployed: 2
merged_branches: [...]
quality_summary:
  test_coverage_avg: 0.87
  static_analysis_violations_total: 0
  dependency_audits_passed: 47
  migration_dry_runs_passed: 2
artifacts_root: "TEST WORKFLOW/10. J. Implementation RS/"
j_runtime_db_hash: sha256:{hash}
ready_for_human_k_trigger: true
k_trigger_instruction: "Запусти K0 вручную с K R6 k_trigger_signal.yaml schema 1.2: product_repo_path/product_repo_id, target_ref + expected_target_commit_sha, explicit source_policy, scope/acceptance_scope/audit_depth, content-addressed upstream_artifacts_ref с target binding, scanner_profile, authorization_context_ref, external_evidence_refs, optional runtime_evidence_refs и optional tool_execution_policy_ref. Не используй J artifacts как K inputs."
```

**Minimal schema при `status: spike_rejected`:**

```yaml
schema_version: "1.0"
layer: J
status: spike_rejected
snapshot_mode: research_only | implementation
started_at: ...
completed_at: ...
total_tasks_seen: 1
completed_tasks: 0
partial_tasks: []
rejected_spike:
  task_id: T-003
  spike_id: SPIKE-003
  blast_radius: architecture_global | component | optimization
  spike_rejection_ref: spike_rejection.yaml
  spike_rejection_hash: sha256:{hash}
artifacts_root: "TEST WORKFLOW/10. J. Implementation RS/"
j_runtime_db_hash: sha256:{hash}
ready_for_human_k_trigger: false
next_owner: I-layer Circuit Breaker
```

`j_layer_summary.yaml` создаётся и при `spike_rejected`, но это больше не K entrypoint. При `spike_rejected` K не запускается; I-слой продолжает читать `spike_rejection.yaml` как routing artifact.

### 5.7 j_hitl_coder_session.yaml

**Нормативная схема живёт в `J21. HITL Coder Session.md` (раздел Output Artifact) — этот параграф даёт только структурную сводку для ориентации, не отдельный источник истины. Если этот параграф и `J21. HITL Coder Session.md` расходятся, `J21. HITL Coder Session.md` побеждает; расхождение — баг документации, а не два легитимных варианта одного `schema_version`.**

Round 1 создаёт файл (`session_status: awaiting_human`, `session_outcome: null`); round 2 финализирует тот же файл в place (`session_status: resolved`), не создаёт новый. Ключевые поля верхнего уровня:

```yaml
schema_version: "1.0"
session_id: "HITL-CS-{task_id}-1"      # суффикс всегда литеральный "1" — одна логическая сессия на задачу, {seq} никогда не растёт
task_id: T-042
execution_chain: server_code | client_code | ui_code | migration
session_status: awaiting_human | resolved
interaction_round: 1 | 2
created_at: ...                         # round-1 open time, неизменно
resolved_at: ...                        # null пока awaiting_human

context: {...}                          # round-1 snapshot, дословно переиспользуется в round 2
trigger: {...}                          # включая структурированную worktree_reset attestation + checkpoint_ref
preflight: {...}                        # round-1 snapshot, включая ownership_attribution_passed
round2_preflight: {...}                 # null в round 1; свой снапшот для round 2, не перезаписывает preflight

failure_dossier:
  attempt_timeline: [...]               # failed_at: J6|J8|J7|J0|environment|unknown
  established_facts: [...]
  root_cause_hypotheses: [...]
  rejected_options: [...]

human_session:
  questions_presented: [...]            # question_id + option_ids_presented
  decisions_made:                       # answer_kind: option | escalate | moot | unanswered
    - question_id: "Q-001"
      answer_kind: option
      selected_option_id: "OPT-001"

options_considered: [...]               # option_id + recommendation: recommended|acceptable|rejected

session_outcome: session_resolved | needs_i_layer | task_scoped_down | null
outcome_notes: "..."

implementation_handoff: {...}           # authoritative structured plan for J6 (required for session_resolved)
agreed_approach: "..."                  # derived prose digest of implementation_handoff, never an independent source

escalation_trigger: decision_overflow | scope_expansion | technology_fundamental_gap | null
requested_action: task_decomposition | task_spec_update | technology_decision_update | null
escalation_context: {...}

self_audit: {...}
```

Non-consuming abort (Ownership Attribution Gate, preflight failure, malformed `human_decision_bundle`) пишет отдельный файл `j21_launch_blocked.yaml` вместо этого — не расходует `hitl_coder_sessions_count`.

**session_outcome:**
- `session_resolved` — согласован конкретный `implementation_handoff`; следует один `collaborative_attempt` (J6+J8+J7 с новым контекстом)
- `needs_i_layer` — blocker требует вмешательства I-слоя; J0 переходит к §3.6 (budget_escalation)
- `task_scoped_down` — согласовано уменьшение объёма задачи; также ведёт к §3.6 с `requested_action: task_spec_update`

### 5.8 j_spike_resolution_signal.yaml

Создаётся J0 после успешного завершения `research_only` spike (§6.1). Отдельный артефакт — не путать с `budget_escalation_request.yaml` (разные сценарии).

```yaml
schema_version: "1.0"
signal_id: SRS-{spike_task_id}
spike_id: SPIKE-003
spike_task_id: T-003
snapshot_mode: research_only
spike_outcome: resolved                  # resolved | rejected (rejected → spike_rejection.yaml)
spike_resolution_path: "TEST WORKFLOW/10. J. Implementation RS/T-003/spike_resolution.yaml"
requested_action: produce_implementation_snapshot
  # I-оркестратор должен: запустить I7→I8–I15→I16/I17→I6 patch→I18–I24
  # и опубликовать новый frozen_snapshot с snapshot_mode: implementation
created_at: 2026-06-23T09:30:00Z
```

J0 кладёт этот файл по пути, ожидаемому I-оркестратором §13. I-оркестратор отвечает публикацией нового `frozen_snapshot.yaml` (не `budget_escalation_response.yaml`).

### 5.8.1 human_action_result.yaml

Создаётся J22 или человеком по structured template для задачи `execution_chain: external_manual`. Этот файл является evidence, что внешнее ручное действие выполнено или отклонено. Он не содержит secret values.

```yaml
schema_version: "1.0"
task_id: T-020
task_spec_hash: sha256:{hash}
created_at: 2026-06-25T10:15:00Z
status: pending | completed | rejected | blocked   # pending — состояние template, который J22 создаёт в режиме initial_checklist до заполнения человеком; J0 не трактует pending как результат
performed_by: "<role-or-person-ref>"
external_system: stripe
action_type: payment_console

evidence:
  - type: external_resource_id
    name: stripe_staging_webhook_endpoint_id
    value: "we_123..."          # external id допустим; не секрет
  - type: secret_ref
    name: STRIPE_WEBHOOK_SECRET
    location: "staging/cloud-secret-manager/STRIPE_WEBHOOK_SECRET"
    value_present: false        # всегда false: значение секрета не пишется
  - type: console_export_ref
    path: "TEST WORKFLOW/10. J. Implementation RS/T-020/evidence/stripe_webhook_console_export.txt"
    hash: sha256:{hash}

secret_material_policy:
  secret_values_written_to_repo: false
  allowed_material: [secret_ref, env_var_name, vault_path, external_resource_id, fingerprint]
  forbidden_material_detected: false

rejection:
  reason: null
  requested_i_layer_action: null       # task_spec_update | task_decomposition | architecture_decision_update
```

Если `status: completed`, J22 создаёт `acceptance_evidence.yaml`, где каждый acceptance_check ссылается на конкретный evidence item из `human_action_result.yaml`. Если `status: rejected` или `blocked`, J0 пишет `j_task_failure_report.yaml` или `budget_escalation_request.yaml` в зависимости от `requested_i_layer_action`.

### 5.9 acceptance_evidence.yaml

Для server_code/client_code/ui_code/migration/integration/qa **J0 собирает** `acceptance_evidence.yaml` на этапе завершения задачи (§3.8), после всех шагов `step_chain` и до PR — источник этой сборки: `quality_report.yaml#acceptance_evidence_map` (J10), плюс, для `ui_code`, итог двухраундовой J13-сессии: `hitl_ui_request_<session_id>.yaml` (round 1) и `hitl_ui_result_<session_id>.yaml` (round 2) — два immutable файла на сессию, не один `hitl_ui_approval.yaml` (устаревшее имя; см. §6.4). J10 сам `acceptance_evidence.yaml` не создаёт — см. J10. Code Analyst.md. Для `config` J0 собирает его из `config_validation_report.yaml` + список изменённых config-файлов + `documentation_report.yaml`; для `infra_code` — из `deployment_report.yaml` + `infra_test_report.yaml` + `documentation_report.yaml`. Только для `external_manual` `acceptance_evidence.yaml` создаёт сам J22, сразу после проверки `human_action_result.yaml`, и evidence берётся из structured evidence items этого файла. Для `research_spike` J0 собирает его только при `spike_resolution.yaml` + `snapshot_mode: implementation` (из `spike_findings.yaml` + `spike_report.md` + `spike_resolution.yaml`); при `spike_rejection.yaml` Task Completion Gate не применяется — задача закрывается через Special Flow (см. J0.md, таблица источников Task Completion Gate). Это машинно-проверяемая связка между natural-language `acceptance_checks` из task_spec и фактическими доказательствами из отчётов J7/J8/J9b/J10/J13/J19/J20/J22.

```yaml
schema_version: "1.0"
task_id: T-042
task_spec_hash: sha256:{hash}
generated_at: 2026-06-23T13:00:00Z
status: satisfied | failed
checks:
  - check_id: AC-001
    source_text: "[INV_003] solve([]) -> SolvedPlan { tasks: [] }"
    status: satisfied | failed | gap_allowed_partial_contract | not_applicable_confirmed
    evidence_refs:
      - test_report.yaml#tests/solver/empty_input
    verified_by: J7
  - check_id: AC-002
    source_text: "[IS_004] solve выполняется за <16ms на 1000 задач"
    status: satisfied
    evidence_refs:
      - quality_report.yaml#performance_review.observations[0]
    verified_by: J10
manual_evidence:
  - check_id: AC-UI-001
    required: true
    evidence_ref: hitl_ui_result_<session_id>.yaml#resolved_acceptance_evidence
```

Задача не считается complete, пока каждый `acceptance_check` не получит `status: satisfied` с непустым `evidence_refs`, `status: gap_allowed_partial_contract` (авторизованный J5 permanent gap — см. J10. Code Analyst.md, `task_spec.partial_test_contract_allowed: true`), либо `status: not_applicable_confirmed` (J13-confirmed inapplicability для human_ui checks; отдельный провенанс от `gap_allowed_partial_contract`, не смешивать). `pending_downstream`/`deferred_to_downstream` — временный статус, не финальный: J0 не считает задачу завершённой, пока downstream-агент (например J13 через `hitl_ui_result_<session_id>.yaml`) не разрешит его в `satisfied`/`failed`/`not_applicable_confirmed`. Для manual checks evidence должен ссылаться на HITL-артефакт, а не на свободный текст в отчёте.

---

## 6. Цепочки промптов по execution_chain

Порядок шагов единый для code/config/infra/qa цепочек. `research_spike` и `external_manual` являются отдельными специализированными цепочками:

```
J4 Methodologist → J9 Dependency Auditor → J5 Test Writer
→ [J6+J8+J7 атомарная единица] → J9b Lockfile Verifier → J10 Code Analyst → J11 Documenter
→ [опционально: J12, J13, J20, и т.д.]
```

Логика порядка: J4 формирует `proposed_dependencies` — без этого J9 не знает, что аудировать. J9 одобряет или отклоняет список — без этого J5/J6 не знают, какие пакеты доступны.

### 6.1 research_spike

| Шаг | Агент | Артефакт | Commit |
|-----|-------|----------|--------|
| 1 | J1 — Spike Executor | spike_findings.yaml | solo |
| 2 | J2 — Spike Documenter | `spike_report.md` (success) **или** `spike_report_gate_failure.yaml` (gate/self-audit failure) | solo |
| 3 | J3 — Spike Resolver | spike_resolution.yaml **или** spike_rejection.yaml | solo |

**Если spike_rejection.yaml:** поведение зависит от `blast_radius`:
- `architecture_global` → в `snapshot_mode: implementation` J0 останавливает обычный implementation flow и формирует I-layer handoff. В `snapshot_mode: research_only` outcome сначала становится terminal для текущей task; J0 продолжает остальные независимые research spikes текущего snapshot и формирует aggregate I-layer handoff только при batch-finalization либо при явном structured evidence, что rejection инвалидирует remaining spikes. Один `architecture_global` label сам по себе batch не останавливает (нормативная процедура — `J0. Dispatcher.md`, «Research-only Spike Batch Policy»).
- `component` → J0 помечает affected component tasks как `blocked` в `j_runtime.db`; unaffected tasks могут продолжать выполняться, если их dependencies не затронуты.
- `optimization` → J0 помечает текущую optimization/spike task как `blocked` или `known_limitation` в `j_runtime.db`; implementation tasks продолжаются, если acceptance_checks не зависят от отклонённой оптимизации.

**Если spike_resolution.yaml и snapshot_mode: implementation:**
J0 обновляет `j_runtime.db#j_task_status_edges`: spike task → `spike_resolved`. Impl-задачи с `blocked_by_spikes: [this_spike]` становятся доступными только если tasks.db уже содержит их как component-level blocked tasks. Продолжаем в рамках существующего implementation_snapshot.

**Если spike_resolution.yaml и snapshot_mode: research_only:**
Impl-задачи ещё не материализованы — их нет в текущем frozen_snapshot. J **не разблокирует** задачи, которых нет. Сначала J0 завершает research batch:
```
1. J0 помечает текущую research task как spike_resolved и вычисляет remaining eligible research tasks
2. Если remaining tasks есть и batch не invalidated → продолжает batch через Approval Gate; signal пока не создаётся
3. При batch-finalization J0 создаёт j_spike_resolution_signal.yaml (§5.8) или aggregate handoff, если batch содержит rejections
4. Для all-resolved batch J0: j_layer_status.yaml: status: awaiting_implementation_snapshot
          awaiting_implementation_snapshot.reason: spike_resolved
5. J0 останавливается; ждёт нового frozen_snapshot с snapshot_mode: implementation
   от I-оркестратора (который запустил полный impl path: I7→I8–I15→I16/I17→I6 patch→I18–I24)
   Примечание: это НЕ budget_escalation_response.yaml — разные сценарии
6. После получения implementation_snapshot → обычный flow §3.1 с snapshot_mode: implementation
```
J не переходит к реализации до получения implementation_snapshot от I-оркестратора.

### 6.2 server_code

| Шаг | Агент | Описание | Commit |
|-----|-------|----------|--------|
| 1 | J4 | Methodologist (формирует proposed_dependencies; если `triggers_module_complete: true` — также `deployment_execution_plan.yaml` для J12, см. J4.md "Deployment Execution Plan") | solo |
| 2 | J9 | Dependency Auditor (аудирует proposed_dependencies из J4) | solo |
| 3 | J5 | Test Writer (TDD — тесты до реализации) | solo |
| 4–6 | J6+J8+J7 | coding_unit (см. ниже) | coding_unit |
| → | J21* | HITL Coder Session — если coding_unit_max_attempts исчерпан | solo |
| → | J6+J8+J7* | collaborative_attempt — один финальный проход после J21 | coding_unit |
| 7 | J9b | Dependency Lockfile Check | solo |
| 8 | J10 | Code Analyst | solo |
| 9 | J11 | Documenter | solo |
| 10† | J12 | Container & Deploy | solo |

\* J21 и collaborative_attempt вставляются в цепочку только если `coding_unit_attempt_count >= coding_unit_max_attempts`. Не являются плановыми шагами.  
† Шаг 10 только если `task_spec.triggers_module_complete: true`

**coding_unit — логика повторов:**
Одна «попытка» coding_unit = один полный проход J6 → J8 → J7. `coding_unit_attempt_count` инкрементируется при входе в J6 для нового полного прохода. Возврат J6↔J8 из-за static violations остаётся внутри текущей попытки и ограничен `static_fix_iteration_count` / `task_spec.budget.max_static_fix_iterations` (дефолт: 3). Провал J7 начинает новую попытку.

**collaborative_attempt after J21:** после `session_outcome: session_resolved` допускается ровно один финальный полный проход J6 → J8 → J7. Внутри этого прохода static-fix loop J6↔J8 **не отключается**: мелкие type/lint/static violations можно исправлять до `max_static_fix_iterations`. Если после этого J8 всё ещё не clean или J7 fails — задача переходит в §3.9 (`blocked`); новый J21 или новый полный coding attempt не запускается.

```
coding_unit_attempt_count < coding_unit_max_attempts:
  J6 → J8:
    если static violations → J6 (исправляет) → J8 снова [тот же attempt, static_fix_iteration_count++]
    если static_fix_iteration_count > max_static_fix_iterations → новая attempt или J21 при лимите
  → J7:
    если tests failed → J6 (исправляет) → J8 → J7 [новый attempt: coding_unit_attempt_count++]
    если passed → J0 через bash commit coding_unit; продолжаем

coding_unit_attempt_count >= coding_unit_max_attempts:
  J0 через bash сбрасывает к git_checkpoint.before_coding_unit
  → J0 запускает J21 HITL Coder Session как subagent (§6.2.2)
```

`coding_unit_max_attempts` берётся из `task_spec.budget.max_coding_unit_attempts` (дефолт: 3). `max_static_fix_iterations` берётся из `task_spec.budget.max_static_fix_iterations` (дефолт: 3).

**J4 обязанность:** явно заполнить `proposed_dependencies` в methodology_review.yaml. J6 не имеет права добавлять пакет, отсутствующий в `dependency_audit.yaml: approved: true`.

**files_allowed_to_touch:** J6 может трогать только файлы из `task_spec.files_allowed_to_touch`. J0 проверяет `git status --porcelain` перед коммитом — нарушение → остановиться; revert шага.

#### 6.2.1 Dependency amendment (динамический запрос зависимости)

Если в процессе кодирования J6 обнаруживает необходимость в библиотеке, не указанной в `methodology_review.yaml`, он **не добавляет её самостоятельно**, а сигнализирует через артефакт:

```yaml
# dependency_amendment_request.yaml (в {task_id}/)
request_id: DAR-{task_id}-{seq}
package: "stripe-node"
version: "^14.0"
reason: "Payment processing requires Stripe SDK; standard fetch insufficient."
status: pending
```

J0 обнаруживает файл и выполняет **worktree-протокол**:

```
Dependency Amendment Protocol:
1. J0 через bash: git stash push --include-untracked
                  (прячем изменения J6, чтобы J9 работал в чистом worktree)
2. J0 запускает J9 как subagent в amendment mode (читает только dependency_amendment_request.yaml
   и dependency_audit.yaml — read-only; не видит partial code J6)
3. J9 пишет НЕ dependency_audit.yaml, а single-decision delta: dependency_amendment_decision.yaml
   (schema: dependency_decision + amendment_record + previous_dependency_audit_snapshot).
   Это осознанный отказ от full-file regeneration на каждый amendment: растущая история
   dependencies[]/amendments в dependency_audit.yaml делала полную перезапись файла моделью
   ненадёжной (risk of truncation/дрейфа прозы на "неизменных" старых записях).
4. J0 выполняет Dependency Audit Splice — детерминированный merge, не LLM-регенерация:
   - staleness-check: previous_dependency_audit_snapshot.dependencies_count/last_decision_id
     должны совпасть с фактическим dependency_audit.yaml на диске; при расхождении —
     НЕ сплайсить, перезапустить J9 (свежее чтение), без пометки шага как failed
   - append dependency_decision в dependencies[] (с финальным decision_id),
     append/update amendments.<request_id> из amendment_record
   - пересчитать summary (approved/rejected/already_available/no_op counts,
     active_rejections[].blocks_current_implementation_path, active_rejections_block_coding)
     и top-level status детерминированно — это чистая функция от dependencies[].decision,
     не требует LLM-суждения
   - никогда не удалять/переписывать прошлые записи, только append/point-update
5. После сплайса J0 оценивает merged dependency_audit.yaml:
   - dependency_decision.decision approved/already_available → J0 через bash: git stash pop;
     J6 продолжает с одобренным пакетом (не считается новой попыткой coding_unit)
   - dependency_decision.decision rejected/duplicate_rejected_request → J0 через bash: git stash pop;
     J0 создаёт dependency_amendment_rejection_context.yaml из merged dependency_audit.yaml;
     J6 обязан прочитать context и найти альтернативу
6. Если git stash pop даёт конфликт → J0 записывает step.status: stash_conflict
   → эскалация как step_failed (retry)
7. Если J6 не находит альтернативу после rejected amendment → budget_exceeded
   (trigger 3: technology_fundamental_gap)
```

```yaml
# dependency_amendment_rejection_context.yaml (в {task_id}/)
schema_version: "1.0"
request_id: DAR-{task_id}-{seq}
package: "stripe-node"
status: rejected
rejection_reason_ref: dependency_audit.yaml#amendments/DAR-{task_id}-{seq}/rejection_reason
forbidden_imports:
  - stripe-node
required_j6_action:
  - remove_or_avoid_rejected_package
  - choose_alternative_from_approved_dependencies
  - escalate_budget_exceeded_technology_fundamental_gap  # if no alternative
```

J6 resume context after rejection always includes `dependency_audit.yaml` and `dependency_amendment_rejection_context.yaml`. Re-requesting the same package/version in the same coding_unit attempt is a blocking violation, not a new amendment request.
J0 также обновляет `j_layer_run.yaml#dependency_amendment_requests[].rejection_context_ref`, чтобы J0 и человек могли связать rejected request с конкретным context artifact. Это поле остаётся J audit trail и не является входом независимого K-аудита (K R6/D1).

**Ограничения:** не более 2 amendment request за одну coding_unit попытку. При третьем запросе — автоматически budget_exceeded (decision_overflow). J6 не может вызвать amendment внутри другого amendment.

#### 6.2.2 J21 HITL Coder Session

J0 запускает J21 когда `coding_unit_attempt_count >= coding_unit_max_attempts` и `collaborative_attempt_used: false`. Блок J21 вставляется в цепочку один раз — не является плановым шагом. Полный нормативный контракт живёт в `J21. HITL Coder Session.md` и в `J0. Dispatcher.md` §"J21 HITL Coder Session"; здесь — только актуальный обзор, не дублирующая копия схемы (см. предупреждение в конце этого раздела).

**J21 — не живой диалог.** Subagent работает по turn-based модели одного вызова и не может внутри него дождаться ответа человека. Поэтому одна логическая HITL-сессия состоит из **двух ролей вызова** одного и того же subagent, оба пишут/дополняют один и тот же `j_hitl_coder_session.yaml`:

- **Round 1 (new session)** — J21 читает историю попыток (только через `j_layer_run.yaml#coding_attempt_history`, никогда напрямую живые `static_analysis_report.yaml`/`test_report.yaml`, которые J0 перезаписывает на каждой попытке), проходит **Ownership Attribution Gate** (если хоть одна ещё-не-reconciled попытка провалилась не по вине J6 — J5/J7/J8/environment/J0-routing дефект — J21 не тратит сессию: пишет `j21_launch_blocked.yaml#reason: j_layer_reconciliation_required`, J0 маршрутизирует проблему реальному владельцу и повторяет round 1 позже), строит dossier + до 5 вопросов с явными вариантами (`options_considered`), и останавливается: `session_status: awaiting_human`, `session_outcome: null`. Не решает ничего единолично.
- **Round 2 (resume)** — вызывается только после того, как J0 собрал структурированный `human_decision_bundle` от реального человека в текущей Claude Code/Codex-сессии (никогда сам J21). Если бандл покрывает не все вопросы и ни один ответ не `escalate` — J21 **не финализирует и не трогает файл**, а сообщает J0, каких ответов не хватает; J0 донабирает их у человека и вызывает round 2 снова (сколько угодно раз, сессия не расходуется). Как только бандл достаточен, J21 финализирует: `session_status: resolved`, один из трёх исходов ниже. Human decision на unsafe/rejected-опцию никогда не переинтерпретируется J21 — это всегда эскалация, не подстановка "что человек на самом деле имел в виду".

**Преусловия round 1:**
- `hitl_coder_sessions_count == 0` (одна логическая сессия на задачу — считает сессии, не вызовы subagent; инкрементируется J0 один раз, сразу после того как round 1 вернул `awaiting_human`, не раньше)
- `collaborative_attempt_used == false`
- J0 строит структурированную `worktree_reset_attestation` (не полагается на голое совпадение commit-хэшей — `git reset --hard` не удаляет untracked-файлы) и сбрасывает worktree к `git_checkpoint.before_coding_unit` перед запуском round 1

**По итогу финализированной (round 2, `resolved`) сессии J0 маршрутизирует по `session_outcome`:**

```
session_outcome: session_resolved
  → J0: collaborative_attempt_used: true
  → J0 через bash: git_checkpoint.before_collaborative_attempt = current HEAD
  → J0 запускает один финальный collaborative_attempt (J6 → J8 → J7), используя
    j_hitl_coder_session.yaml#implementation_handoff как авторитетный структурированный план
    (agreed_approach — производный prose-дайджест для беглого чтения, не отдельный источник инструкций):
      если passed → J0 через bash commit coding_unit; продолжаем (J9b, J10, J11 ...)
      если failed → §3.9 (задача завершена с ошибкой; дальнейшие J21 запрещены)

session_outcome: needs_i_layer
  → J0: budget_escalation_request.yaml (trigger = escalation_trigger из j_hitl_coder_session.yaml)
  → j_layer_status.yaml: status: pending_i_layer_response
  → J0 останавливается; ждёт budget_escalation_response.yaml от I-оркестратора (§3.6)

session_outcome: task_scoped_down
  → Аналогично needs_i_layer; requested_action: task_spec_update
```

**Что J21 НЕ делает:**
- Не принимает архитектурные решения единолично и не подставляет собственную интерпретацию вместо явного ответа человека
- Не меняет `files_allowed_to_touch`, `task_type`, `execution_chain` — только I-слой
- Не открывает вторую логическую HITL-сессию для той же задачи (round 1 + сколько угодно round-2-попыток той же сессии — это не "вторая сессия")
- Не запускает git/тесты/статический анализ сам — worktree-состояние приходит только от J0 (`worktree_reset_attestation`)

**Счётчик:** `hitl_coder_sessions_count` в `j_layer_run.yaml` — логические сессии, не вызовы subagent; максимум 1 на задачу. `hitl_coder_sessions_total` в `j_layer_summary.yaml` инкрементируется, если задача в итоге завершилась успешно после HITL-сессии.

**⚠️ Эта секция — обзор, не источник истины для схемы.** Полная схема `j_hitl_coder_session.yaml` (session_status/interaction_round/answer_kind/round2_preflight/и т.д.) — только в §5.7, которая обязана оставаться синхронной с реальным `schema_version` в `J21. HITL Coder Session.md`; не копировать сюда отдельную версию схемы повторно.

### 6.3 client_code

Идентична server_code (6.2), шаг 10 (J12) отсутствует.

### 6.4 ui_code

Идентична server_code (6.2), шаг 10 заменяется:

| Шаг | Агент | Описание |
|-----|-------|----------|
| 10 | J13 | HITL UI — человек проверяет функцию/поверхность в реальном приложении |

J13 — условный шаг (только если у `quality_report.yaml#acceptance_evidence_map` есть хотя бы один check с `downstream_owner: J13`; иначе шаг помечается `skipped: no_manual_ui_scope` и J13 не вызывается вовсе). Одна логическая HITL-UI-сессия состоит из до двух вызовов одного subagent, оба immutable-артефакта, никогда один эволюционирующий файл: **round 1** пишет `{task_id}/hitl_ui_request_<session_id>.yaml` (checklist, ничего не решает) и останавливается; **round 2** запускается только после того, как J0 собрал структурированный `human_decision_bundle` от человека, и пишет `{task_id}/hitl_ui_result_<session_id>.yaml` с `session_outcome: approved | rejected | blocked`. J0 останавливается (`waiting.kind: hitl_ui`) до получения `session_outcome: approved` при следующем запуске. При `session_outcome: rejected` — J0 возвращает задачу к J6 с rejection notes из результата (retry_count++). При `session_outcome: blocked` — маршрутизация зависит от причины (environment fix, эскалация и т.п.). Полный протокол (Preflight Gate, Launch Conditions, participant authorization, terminal-artifact family `abandoned`/`invalidated`/`orphaned`/`launch_blocked`) — см. `J13. HITL UI.md` и `J0. Dispatcher.md`, «J13 HITL UI Session»; этот параграф — только обзор, не источник истины для схемы.

### 6.5 infra_code

| Шаг | Агент | Описание | Commit |
|-----|-------|----------|--------|
| 1 | J14 | Infra Methodologist (IaC-принципы, proposed_dependencies) | solo |
| 2 | J9 | Dependency Auditor (аудирует proposed_dependencies из J14) | solo |
| 3–4 | J15+J8 | coding_unit: J15 Infra Coder → J8 Static Analyzer; нарушения J8 → J15 (тот же attempt) | coding_unit |
| — | | коммит coding_unit (J15+J8) | |
| 5* | J9b | Lockfile Verifier — если coding_unit изменил manifest/lockfile/provider-lock или добавил approved dependency | solo |
| 6 | J16 | Infra Deployer (deploy + smoke tests в тестовом кластере) | solo |
| 7 | J17 | Infra Tester (infra tests) | solo |
| 8** | J16 | conditional cleanup-only pass после появления `infra_test_report.yaml`, если lifecycle policy назначает cleanup J16 | solo |
| 9 | J11 | Documenter | solo |

\* Если manifest/lockfile/provider-lock не изменён и новых approved dependencies нет, J9b пропускается с `skip_reason: no_manifest_or_lockfile_delta` (тот же паттерн, что в §6.6 migration). J9b обязан идти раньше J16/J17, а не после: J16 применяет IaC, J17 тестирует применённое, и оба не должны выполняться против ещё не верифицированного manifest/lockfile/provider-lock diff (см. `J0. Dispatcher.md`, "J9b Lockfile Verifier — failure routing").

\** Cleanup-only — отдельный второй вызов J16 с `invocation_reason: cleanup_only` и `deployment_cleanup_report.yaml`; он не перезаписывает `deployment_report.yaml`. Если cleanup был запланирован, этот проход выполняется и после `failed`/`blocked` J17, чтобы тестовая инфраструктура не осталась бесхозной; корневую причину J17 он не заменяет.

**Примечание:** infra_code не включает J7 Test Runner (инфраструктурные тесты — J17). coding_unit = J15+J8 (без J7).  
**files_allowed_to_touch:** J15 проверяется аналогично J6.

**HITL Coder Session:** J21 в MVP не поддерживает `infra_code`. Если J15+J8 исчерпали `coding_unit_max_attempts`, задача переходит в §3.9 (`blocked`) с `j_task_failure_report.yaml`; ручное восстановление выполняется вне J21.

### 6.6 migration

**migration_guard:** до начала шагов J0 проверяет:
```yaml
requires_in_task_spec:
  - rollback_strategy: not_empty      # текстовое описание стратегии (от I21, не код)
  - data_loss_risk: присутствует (true или false)
  - accepted_risk_id: обязательно если data_loss_risk: true
```

**Семантика rollback (R3):** `task_spec.rollback_strategy` — архитектурная инструкция (текст), написанная I21. Это описание того, ЧТО должен делать откат: какие таблицы затронуты, как восстановить состояние, есть ли риск необратимой потери данных. **Код отката (SQL-скрипт, миграционный файл) пишет J6** как часть своей реализации — вместе с прямой миграцией. J20 получает оба файла (forward + rollback) и тестирует оба на тестовых данных.

**Migration Execution Plan (R8):** J4 (шаг 1) обязан создать `migration_execution_plan.yaml` — второй, отдельный artifact (не секция `methodology_review.yaml`), см. J4.md "Migration Execution Plan (`migration`)". Это единственный источник target identity, dataset/fixture, credential refs, команд (provision/fixture_load/baseline_check/forward_apply/post_check/idempotency_probe/rollback_apply/restore_check/teardown/teardown_verify), partial-forward recovery и retention policy для J20. J20 (шаг 8) исполняет этот план — он больше не выводит команды или target из "project conventions" самостоятельно.

| Шаг | Агент | Описание | Commit |
|-----|-------|----------|--------|
| 1 | J4 | Methodologist (migration mode, proposed_dependencies) + `migration_execution_plan.yaml` | solo |
| 2 | J9 | Dependency Auditor (аудирует proposed_dependencies из J4) | solo |
| 3 | J5 | Migration Test Writer | solo |
| 4–6 | J6+J8+J7 | coding_unit: J6 Migration Coder → J8 Static Analyzer → J7 Migration Test Runner; правила повторов как в §6.2 | coding_unit |
| — | | коммит coding_unit | |
| 7* | J9b | Dependency Lockfile Check — если migration изменила lockfile или добавила approved dependency | solo |
| 8 | J20 | Migration Dry Run / Rollback Tester — исполняет `migration_execution_plan.yaml` от J4 | solo |
| 9 | J10 | Code Analyst | solo |
| 10 | J11 | Documenter | solo |

\* Если lockfile не изменён и новых approved dependencies нет, J9b пропускается с `skip_reason: no_manifest_or_lockfile_delta`.

**J20** запускает dry-run миграции и dry-run rollback по командам из `migration_execution_plan.yaml`. Производит `migration_dry_run_report.yaml` и `rollback_test_report.yaml`. Если любой из них содержит `passed: false` — задача считается failed, не достигает J10/J11. Если `migration_execution_plan.yaml` отсутствует или неполон, J20 блокируется (`status: blocked`), а не угадывает недостающие поля.

### 6.7 integration

J5 (Test Writer) теперь всегда идёт первым шагом в `integration` — до J18, без `methodology_review.yaml` (его для `integration` не существует), напрямую из `task_spec.acceptance_checks` + architecture/contract refs, тем же способом, что и для `qa`. J18 после этого читает `j5_test_contract.yaml` как готовый test-контракт и планирует `requires_glue_code`/verification вокруг него — это устраняет прежнюю дыру, где J6 (glue-only) и J18 (artifact-only) не имели полномочий создавать новые integration test assets.

**Если `integration_plan.yaml: requires_glue_code: true`:**

| Шаг | Агент | Описание | Commit |
|-----|-------|----------|--------|
| 1 | J5 | Test Writer → j5_test_contract.yaml (integration test suite против контрактной границы, вне методологии J4) | worktree-mutating solo |
| 2 | J18 | Integration Planner → integration_plan.yaml (читает `j5_test_contract.yaml`) | solo |
| 3–5 | J6+J8+J7 | coding_unit: J6 Coder (glue code) → J8 Static Analyzer → J7 Test Runner (integration mode); правила повторов как в §6.2 | coding_unit |
| 6 | J9b | Lockfile Verifier (только если coding_unit затронул manifest/lockfile) | solo |
| 7 | J19 | Load Tester | solo |
| 8 | J10 | Code Analyst | solo |
| 9 | J11 | Documenter | solo |

**Если `integration_plan.yaml: requires_glue_code: false`:**

| Шаг | Агент | Описание | Commit |
|-----|-------|----------|--------|
| 1 | J5 | Test Writer → j5_test_contract.yaml | worktree-mutating solo |
| 2 | J18 | Integration Planner → integration_plan.yaml (читает `j5_test_contract.yaml`) | solo |
| 3 | J7 | Test Runner (integration mode, verification) | solo |
| 4 | J19 | Load Tester | solo |
| 5 | J10 | Code Analyst | solo |
| 6 | J11 | Documenter | solo |

### 6.8 qa

| Шаг | Агент | Описание | Commit |
|-----|-------|----------|--------|
| 1 | J5 | QA Test Planner / Test Writer | solo |
| 2 | J7 | Test Runner | solo |
| 3 | J10 | Quality Analyst | solo |
| 4 | J11 | Documenter | solo |

### 6.9 config

| Шаг | Агент | Описание | Commit |
|-----|-------|----------|--------|
| 1 | J4 | Methodologist (config mode — проверяет принципы §13 П7, П9, П11) | solo |
| 2–3 | J6+J8 | coding_unit: J6 Coder (конфигурационные изменения) → J8 Static Analyzer / schema validator; нарушения J8 → J6 (тот же attempt) | coding_unit |
| — | | коммит coding_unit | |
| 4 | — | **J0 через bash: выполняет `task_spec.validation_commands`** и пишет `config_validation_report.yaml` (runtime/schema validation; config применяется и проверяется) | — |
| ↑ | | если validation_commands упали → J0 через bash откатывает к `git_checkpoint.before_coding_unit`; задача → step_failed | |
| 5 | J11 | Documenter | solo |

### 6.10 external_manual

Цепочка для `task_type: human_action`. Используется для действий, которые должен выполнить человек во внешней системе: account registration, cloud/payment/app-store/DNS console setup, secret provisioning, manual approval. J-слой не пытается автоматизировать эти действия и не просит вставлять secret value в чат или файл.

| Шаг | Агент | Описание | Commit |
|-----|-------|----------|--------|
| 1 | J22 | External Manual Action — показывает человеку чеклист из `task_spec.human_action`, ждёт `human_action_result.yaml`, проверяет evidence и secret hygiene | none |

**Старт external_manual (порядок: launch → validate → set waiting — см. J0.md «Special Flow: External Manual»):**
1. J0 создаёт `j_layer_run.yaml` без git worktree и без branch.
2. J0 запускает J22 как subagent (режим `initial_checklist`); J22 создаёт template `human_action_result.yaml` со `status: pending` и показывает человеку:
   - external_system, action_type, actor_role
   - required_inputs
   - instructions
   - produces
   - evidence_required
   - secrets_policy
3. J0 читает созданный template (`status: pending`), подтверждает успех шага, и только теперь обновляет `j_layer_status.yaml: status=waiting_for_external, waiting.kind=external_manual`.
4. J0 останавливается; ждёт заполненный `human_action_result.yaml` при следующем запуске.

**Проверки J22 (запускается J0 как subagent при следующем запуске):**
- `human_action_result.yaml#status == completed`
- каждый `task_spec.human_action.evidence_required[]` покрыт structured evidence item
- `secret_material_policy.secret_values_written_to_repo == false`
- evidence не содержит full API key/webhook secret/private key/password/recovery code
- для `secret_ref` указаны name + location, но нет value

**Завершение:**
- Если проверки пройдены: J22 пишет/обновляет `acceptance_evidence.yaml`, J0 помечает задачу complete в `j_runtime.db`, downstream `depends_on` разблокируются.
- Если человек отклонил действие или evidence неполный: задача `blocked`; J0 сообщает, что нужно исправить `human_action_result.yaml` или эскалировать в I-слой.
- Если task_spec оказался неверным (не тот actor_role, external system, missing instructions): J0 пишет `budget_escalation_request.yaml` с `requested_action: task_spec_update`.

**Запрещено:**
- создавать branch/PR/code diff для external_manual
- писать секретные значения в `human_action_result.yaml`, run logs, markdown или git
- заменять evidence свободным текстом "сделано"
- выполнять downstream задачи до complete external_manual task

---

## 7. Git-процесс

### 7.1 Атомарные коммит-группы

Не каждый шаг делает отдельный коммит. Шаги разбиты на три вида:

**solo:** шаг коммитит свои артефакты самостоятельно по завершении (J0 выполняет `git add` + `git commit` через bash).

**coding_unit:** J6 + J8 + J7 (или J15 + J8) образуют атомарную группу:
- J0 **не коммитит** после J6 или J8 по отдельности
- Коммит происходит только когда **оба** J8 (static analysis: clean) и J7 (tests: all passed) завершились успешно
- При неудаче любого из них: J6 исправляет → повторяем J8 → повторяем J7
- При исчерпании retry: J0 через bash `git reset --hard {git_checkpoint.before_coding_unit}` только внутри `.j-worktrees/{task_id}`

**null:** шаг не производит самостоятельного коммита; его артефакт является частью следующего solo-шага. J9 Dependency Auditor **не null** — он solo: `dependency_audit.yaml` коммитится самостоятельно до J5/J6.

Формат коммит-сообщения:
```
[{task_id}] {step_name}: {description}

Task: {task_title}
Step: {step_index}/{total_steps}
Agent: {agent_id}
```

### 7.2 git_checkpoint

J0 записывает checkpoint через bash перед началом каждой coding_unit и перед финальной collaborative_attempt после J21. Solo-шаги не получают отдельный checkpoint: если solo-шаг падает до commit, J0 очищает только task-owned worktree через bash.

```yaml
git_checkpoint:
  before_coding_unit: {commit_hash}    # записывается до запуска J6
  before_collaborative_attempt: null    # заполняется перед финальным pass после J21
  coding_unit_commit: null             # заполняется после успешного прохождения J6+J8+J7
rollback_policy:
  applies_only_inside: .j-worktrees/{task_id}
  on_budget_exceeded:       export_escalation_evidence, then git reset --hard before_coding_unit
  on_retry_exhausted:       git reset --hard before_coding_unit
  on_collaborative_failed:   git reset --hard before_collaborative_attempt
  on_step_failed_pre_commit: git checkout -- . (сброс task-owned worktree)
```

### 7.3 Именование ветки и PR

Для `execution_chain: external_manual` этот раздел не применяется: branch, worktree, commit и PR не создаются. Задача закрывается через `human_action_result.yaml` + `acceptance_evidence.yaml`.

```bash
# task-owned worktree + ветка
git worktree add .j-worktrees/{task_id} -b j/{task_id}/{slug}
# slug = первые 40 символов task_title в kebab-case

# PR
gh pr create \
  --title "[{task_id}] {task_title}" \
  --body "Task: {task_id}\nType: {task_type}\nChain: {execution_chain}\n..."
```

**Условия merge:** J0 проверяет `merge_requirements` из фактической `j_layer_run.yaml#step_chain`, `execution_chain` и `task_spec`. Нельзя требовать отчёт от агента, который не входит в эту цепочку.

```yaml
merge_requirements:
  always:
    - ci_checks: passed
    - all_steps_in_step_chain: complete
    - acceptance_evidence.yaml: all_checks_satisfied  # "satisfied" here means status: satisfied OR gap_allowed_partial_contract OR not_applicable_confirmed; never deferred_to_downstream/pending_downstream
    - diff_scope: files_allowed_to_touch_only
  if_step_present:
    J7:
      - test_report.yaml: all_passed
    J8:
      - static_analysis_report.yaml: blocking_violations == 0
    J9:
      - dependency_audit.yaml: status in {approved, partially_approved, no_new_dependencies} && preflight.passed == true && summary.active_rejections_block_coding == false
    J13:
      - hitl_ui_result_<session_id>.yaml: session_outcome == approved  # двухраундовый артефакт — см. §6.4; не hitl_ui_approval.yaml
    J19:
      - load_test_report.yaml: status == passed
    J20:
      - migration_dry_run_report.yaml: passed == true
      - rollback_test_report.yaml: passed == true
    J21:
      - j_hitl_coder_session.yaml: session_outcome == session_resolved
  execution_chain_specific:
    config:
      - validation_commands: passed
      - config_validation_report.yaml: passed == true
    infra_code:
      - infra_test_report.yaml: passed == true
    qa:
      - test_report.yaml: all_passed
    external_manual:
      - human_action_result.yaml: status == completed
      - acceptance_evidence.yaml: all_checks_satisfied  # same rule: satisfied OR gap_allowed_partial_contract OR not_applicable_confirmed, never a pending/deferred status
```

Для `config` chain отсутствие `J7/test_report.yaml` не является ошибкой, если `J7` отсутствует в `step_chain`. В этом случае evidence для acceptance checks должен ссылаться на `validation_commands` / `config_validation_report.yaml`. Аналогично для любой цепочки: обязательны не конкретные имена отчётов “вообще”, а отчёты, соответствующие фактически выполненным шагам и acceptance evidence.

---

## 8. Базы данных J-слоя — разделение namespace

**Файлы БД (уточнение R7):**

| Файл | Владелец | Назначение |
|------|----------|-----------|
| `pipeline.db` | I0/I-слой | Bootstrap, schema migration, lifecycle артефактов I-слоя |
| `tasks.db` | I24 | Canonical task queue для J: порядок, depends_on, status, task_spec refs |
| `causal_graph.db` | I7/I24 | Замороженный архитектурный и task-trace graph; только read-only в J |
| `j_runtime.db` | J0 | Runtime-статусы J, PR/commit refs, acceptance evidence refs |

J0 **не меняет** БД и таблицы, принадлежащие I-слою. Запись в `causal_graph.db` запрещена, потому что I24 включает его hash в frozen snapshot.

| Таблица | БД | Owner | J-слой |
|---------|-----|-------|--------|
| architecture_nodes | causal_graph.db | I-слой (frozen) | read-only |
| architecture_edges | causal_graph.db | I-слой (frozen) | read-only |
| task_nodes | causal_graph.db | I-слой (frozen) | read-only |
| task_edges | causal_graph.db | I-слой (frozen, dependencies) | read-only |
| published_tasks | tasks.db | I24 (frozen) | read-only |
| j_task_status_edges | j_runtime.db | **J0** | write |

**Как J0 получает зависимости:** из `tasks.db`:
- `depends_on` — читать из таблицы `task_dependencies` (JOIN по `task_id`); это source of truth для dependency graph; отдельной колонки `depends_on` в таблице `tasks` нет
- `blocked_by_spikes`, `execution_phase`, `batch_order` — колонки таблицы `tasks`

`causal_graph.db` используется как trace/reference для аудита и проверки provenance, но не как mutable state. `pipeline.db` существует, но принадлежит I-слою (bootstrap/lifecycle I-артефактов — см. таблицу выше) и не входит в frozen snapshot; J0 не читает и не открывает его вовсе.

**j_runtime.db schema:**

**Нормативная схема живёт в `J0. Dispatcher.md` §0.0.1 — таблица ниже осталась как историческая сводка и расходится с ней** (в канонической версии: `pr_number INTEGER`, есть `block_reason`/`status_detail`, статус-enum `pending|in_progress|waiting|complete|blocked|superseded|spike_resolved|spike_rejected`, нет `execution_chain`/`execution_phase`/`commit_hash`/`artifact_hashes`/`acceptance_evidence_hash`). При расхождении побеждает J0.md.

```sql
CREATE TABLE j_task_status_edges (
  task_id TEXT PRIMARY KEY,
  status TEXT NOT NULL,
    -- pending | in_progress | waiting_for_external | complete | failed | superseded | spike_resolved
    -- spike_resolved: spike-задача завершена успешно (resolution записана)
  execution_chain TEXT,
  execution_phase TEXT,            -- strict_first | implementation
  branch_name TEXT,
  commit_hash TEXT,
  pr_number TEXT,
  pr_url TEXT,
  remote_pr_state TEXT,           -- OPEN | MERGED | CLOSED | UNKNOWN
  remote_checked_at TEXT,
  merge_commit_hash TEXT,
  merged_at TEXT,
  artifact_hashes TEXT,           -- JSON
  acceptance_evidence_hash TEXT,
  archived_run_path TEXT,
  archived_run_hash TEXT,
  updated_at TEXT NOT NULL
);
```

Для MVP step-level audit trail хранится в `archive/j_layer_run.{task_id}.archived.yaml`. `j_runtime.db` хранит `archived_run_path` и `archived_run_hash`, чтобы J0 и человек могли проверить порядок J4/J9/J5/J6/J8/J7 без эвристического поиска файлов.

K R2 не читает `j_runtime.db` или `j_layer_summary.yaml` как источник истины для product audit; K запускается отдельным human trigger и реконструирует продукт из primary sources. Архитектурные таблицы остаются content-addressed и иммутабельными для J/I audit trail.

`j_runtime.db` не читается J-runner (его нет); он пишется J0 напрямую через bash-инструменты.

---

## 9. Агенты J-слоя

| ID | Имя | Назначение | execution_chain |
|----|-----|-----------|----------------|
| J0 | Dispatcher-Orchestrator | Читает статус, принимает решения, запускает агентов J1–J22 как subagents через Agent tool, выполняет git/CI через bash | все |
| J1 | Spike Executor | Исполняет spike-исследование | research_spike |
| J2 | Spike Documenter | Документирует findings | research_spike |
| J3 | Spike Resolver | spike_resolution.yaml или spike_rejection.yaml | research_spike |
| J4 | Methodologist | CS-принципы, алгоритмы, proposed_dependencies, запрет антипаттернов; для `server_code` с `triggers_module_complete: true` — также `deployment_execution_plan.yaml` для J12 | server, client, ui, migration, config |
| J5 | Test Writer | TDD: тесты до реализации; QA test planning; integration test suite против контрактной границы | server, client, ui, migration, qa, integration |
| J6 | Coder | Реализация по methodology_review + 20 принципов | server, client, ui, migration, integration*, config |
| J7 | Test Runner | Запуск тестов: unit / integration / migration режимы | server, client, ui, migration, integration, qa |
| J8 | Static Analyzer | Typecheck, lint, security scan | server, client, ui, migration, infra, integration*, config |
| J9 | Dependency Auditor | Проверка новых зависимостей по allowlist (до кодирования) | server, client, ui, migration, infra |
| J9b | Lockfile Verifier | Сверка lockfile после кодирования | server, client, ui, migration*, infra* |
| J10 | Code Analyst | Скорость, надёжность, поддерживаемость | server, client, ui, migration, integration, qa |
| J11 | Documenter | API-docs, архитектурные заметки | все |
| J12 | Container & Deploy | Dockerfile + deploy в тестовый кластер | server (module-complete) |
| J13 | HITL UI | Человек проверяет UI в реальном приложении | ui |
| J14 | Infra Methodologist | IaC-принципы, infra антипаттерны | infra |
| J15 | Infra Coder | Реализация IaC | infra |
| J16 | Infra Deployer | Deploy + smoke tests в тестовом кластере | infra |
| J17 | Infra Tester | Инфраструктурные тесты | infra |
| J18 | Integration Planner | integration_plan.yaml | integration |
| J19 | Load Tester | Нагрузочные и стресс-тесты | integration |
| J20 | Migration Dry Run | Dry-run + rollback тест для миграций | migration |
| J21 | HITL Coder Session | Совместная сессия агент+человек после исчерпания coding_unit_max_attempts; outcome: session_resolved / needs_i_layer / task_scoped_down | server, client, ui, migration |
| J22 | External Manual Action | Ожидание и проверка ручного действия во внешней системе; создаёт/валидирует human_action_result.yaml | external_manual |

*Для integration: только при `requires_glue_code: true`. Для migration: только если lockfile изменён или добавлена approved dependency.

---

## 10. Взаимодействие со смежными слоями

### Вход из I-слоя

| Артефакт | Агент-источник | Использование в J |
|----------|---------------|------------------|
| j_handoff_signal.yaml | I24 | Триггер публикации. Фактические поля I24: schema_version/source_agent/target_prompt/run_id/snapshot_id/snapshot_mode/frozen_snapshot_hash/tasks_db_hash/created_at (полей `signal_id`/`entry_point` в схеме I24 нет — уникальность даёт snapshot_id, точку входа — target_prompt). J0 читает его ДО `frozen_snapshot.yaml` при первом обращении к новому/сменившемуся snapshot и сверяет хеши — доказательство того, что публикация I24 завершена атомарно, а не в процессе перезаписи |
| frozen_snapshot.yaml | I24 | Точка входа; snapshot_mode, paths/hashes included artifacts |
| tasks.db | I24 | Canonical task queue: task order, depends_on, blocked status, task_spec refs |
| task_specs/{task_id}.yaml | I21 | task_type, execution_chain, files_allowed_to_touch, validation_commands, human_action contract |
| causal_graph.db (read-only) | I7/I24 | task_nodes, task_edges, architecture_nodes, architecture_edges для trace/provenance; J0 не пишет |
| system_architecture.final.yaml | I6 | Контекст для J4/J6/J14/J15 (только при implementation) |
| spike_execution_context.yaml | I24 | Контекст для J1 (только при research_only) |
| technology_decisions.yaml | I2 | Технологический контекст для J4/J9. ⚠️ Не входит в `frozen_snapshot.yaml#included_artifacts` текущего I24-снапшота (unhashed вход вне snapshot-целостности) — поэтому J4/J9 читают его строго «if available/if referenced», а J9 при его отсутствии применяет задокументированный консервативный license/policy-дефолт (см. J9.md, Approval Rules); включение в snapshot — задача I24 v-next |
| budget_escalation_response.yaml | I-слой оркестратор | Resume после decomposition |

### Выход из J-слоя

| Артефакт | Получатель | Условие |
|----------|-----------|---------|
| j_layer_summary.yaml | Человек / J archive | После `complete` или `spike_rejected`; сообщает operational итог J и инструкцию для ручного K trigger при complete |
| spike_rejection.yaml | I-слой Circuit Breaker | При провале спайка |
| j_spike_resolution_signal.yaml | I-слой оркестратор | При успешном research_only spike (§5.8) |
| human_action_result.yaml | J22 / J0 / человек | J22 создаёт template; J0 проверяет при resume; для K R4 это не source-of-truth, человек при необходимости переносит redacted первичные внешние refs в `k_trigger_signal.yaml#external_evidence_refs` или runtime refs в `runtime_evidence_refs` |
| budget_escalation_request.yaml | I-слой оркестратор | При budget_exceeded |
| j_task_failure_report.yaml | Ручное разрешение | При невосстановимом провале |
| acceptance_evidence.yaml | J0 / reviewer / человек | Evidence map acceptance_checks → reports; не вход K R2 |

---

## 11. Инварианты J-слоя

1. **No phase skip.** J0 не начинает задачи с `execution_phase: implementation` пока существуют незавершённые задачи с `execution_phase: strict_first`.
2. **No chain derivation.** J0 читает `execution_chain` из task_spec. Самостоятельный вывод цепочки запрещён.
3. **No step skip.** Каждый шаг цепочки обязателен. Пропуск — только с явным закрытым `skip_reason`, предусмотренным правилами J0 для конкретного шага (`no_manifest_or_lockfile_delta` для J9b, `triggers_module_complete_false` для J12, `no_manual_ui_scope` для J13, `no_new_dependencies` для J9 в config), а не по усмотрению агента; task_spec сам skip_reason не задаёт.
4. **No partial commit.** При `budget_exceeded` или `retry_exhausted` — J0 сбрасывает к `git_checkpoint.before_coding_unit`. Нет частичного кода в ветке.
5. **No main commit.** Весь код идёт через ветку и PR. Прямой push в main запрещён.
6. **No merge with failures.** Все условия merge (§7.3) — обязательны одновременно.
7. **No new dependency without audit.** J9 — до J5/J6. J6 не добавляет пакет без `dependency_audit.yaml: approved: true`.
8. **No implementation without methodology.** J4/J14 — всегда до J6/J15. Нет methodology_review.yaml → J6 не запускается.
9. **No files outside scope.** J6/J15 трогают только файлы из `task_spec.files_allowed_to_touch`. J0 проверяет `git status --porcelain` перед коммитом.
10. **spike_rejection routes by blast_radius.** В `snapshot_mode: implementation` `architecture_global` останавливает весь J-слой и создаёт `j_layer_summary.yaml: status=spike_rejected`. В `snapshot_mode: research_only` `architecture_global` терминален только для текущей task: batch продолжается до batch-finalization либо до явной batch invalidation (см. §6.1 и `J0. Dispatcher.md`, «Research-only Spike Batch Policy» — R18). `component` и `optimization` блокируют только затронутые задачи, если dependencies позволяют продолжить остальные.
11. **HITL blocks.** J13 блокирует merge до явного `hitl_ui_result_<session_id>.yaml: session_outcome: approved` (двухраундовый протокол `hitl_ui_request_<session_id>.yaml`/`hitl_ui_result_<session_id>.yaml` — см. §6.4).
12. **migration_guard is mandatory.** Цепочка migration не стартует без `rollback_strategy` (текст) + `accepted_risk_id` (если `data_loss_risk: true`). J6 пишет rollback-код, J20 тестирует оба направления.
13. **Budget escalation returns to I.** J0 не упрощает задачу сам. Решение — только I-слой через budget_escalation_response.yaml. LOC-объём не является триггером.
14. **Frozen graph is immutable.** J0 не открывает `causal_graph.db` на запись. Runtime-статусы пишутся только в `j_runtime.db#j_task_status_edges`.
15. **research_only isolation.** При `snapshot_mode: research_only`: system_architecture.final.yaml недоступен, impl-задачи не запускаются.
16. **coding_unit_attempt_count counts full passes.** Счётчик инкрементируется при входе в J6 для нового полного прохода J6→J8→J7. J6↔J8 static-fix loops считаются через `static_fix_iteration_count`. При достижении `coding_unit_max_attempts` — J21 или эскалация провала, не budget_exceeded.
17. **Reconciliation before action.** J0 проверяет согласованность git worktrees / branches / YAML / j_runtime.db при каждом запуске (§4.1). Операции начинаются только после успешной сверки.
18. **Parallel isolation by resource conflict check.** В pipelined режиме: resource_conflict_check (§3.7) пройден — включает wildcard expansion, directory overlap, shared resources, explicit resource_locks. Migration tasks — только sequential. Revalidation (git rebase + J8+J7) обязательна после каждого merge соседней ветки в main.
19. **J21 is once per task.** HITL Coder Session (J21) запускается не более одного раза на задачу (`hitl_coder_sessions_count: max 1`). После J21 допускается ровно один `collaborative_attempt`. Если collaborative_attempt не проходит J8+J7 — задача переходит в §3.9 (blocked); повторный J21 запрещён. J21 не может изменять task_spec, files_allowed_to_touch или execution_chain — только I-слой.
20. **J0 does not modify task_spec.** J0 не вправе изменять, дополнять или интерпретативно расширять `task_spec`. Если task_spec неполный, противоречивый или неисполняемый — J0 пишет `budget_escalation_request.yaml` или `j_task_failure_report.yaml`. Самостоятельная «починка» missing fields (execution_chain, files_allowed_to_touch, validation_commands) разрушает traceability из I-слоя.
21. **Sequential first.** Первый production-run J-слоя выполняется только в `execution_mode: sequential`. Pipelined mode (`execution_mode: pipelined`) не активируется до полной обкатки sequential flow.
22. **No destructive operations in shared checkout.** J0 выполняет `git reset --hard`, `git checkout -- .`, stash/pop только внутри task-owned isolated worktree `.j-worktrees/{task_id}`. Shared workspace пользователя не очищается автоматически.
23. **Acceptance evidence required.** Задача не считается complete без `acceptance_evidence.yaml`, где каждый `task_spec.acceptance_checks[]` имеет `status: satisfied` (с evidence refs), `status: gap_allowed_partial_contract` (авторизованный J5 permanent gap) либо `status: not_applicable_confirmed` (J13-confirmed inapplicability для human_ui checks) и ссылку на report/HITL evidence.
23a. **Approval Gate is mandatory between subagents.** J0 не запускает следующий subagent автоматически после завершения предыдущего. Каждый launch требует нового прямого согласия пользователя на конкретный следующий шаг; отсутствие такого согласия переводит слой в `waiting_for_external` / `waiting.kind: next_subagent_approval` (см. §3.4 «Выполнение шага (RESUME)»).
24. **Single active task in sequential mode.** При `execution_mode: sequential` `active_task_ids` содержит 0 или 1 элемент; `current_task_id` является derived alias и обязан совпадать с `active_task_ids[0]` или быть `null`.
25. **Archived run is audit anchor.** После завершения задачи `archive/j_layer_run.{task_id}.archived.yaml` создаётся обязательно, а `j_runtime.db.archived_run_path/hash` указывают на него.
26. **PR operations are idempotent.** J0 не вызывает `gh pr create` без предварительного lookup по head branch и не вызывает `gh pr merge` без повторной проверки remote PR state. `MERGED` на GitHub всегда сильнее локального `in_progress`.
27. **Escalation evidence survives reset.** Перед `git reset --hard` при `budget_exceeded` J0 копирует все evidence-артефакты в protected artifact store вне `.j-worktrees/{task_id}` и записывает hashes.
28. **Rejected dependency context is mandatory.** После rejected dependency amendment J6 resume context обязан включать `dependency_audit.yaml` и `dependency_amendment_rejection_context.yaml`; повторный запрос того же package/version в той же попытке запрещён.
29. **Merge requirements are chain-aware.** J0 проверяет merge gate по фактической `step_chain`; отсутствие `test_report.yaml` или `static_analysis_report.yaml` допустимо только если соответствующий агент не входит в цепочку и acceptance evidence покрыто другим предусмотренным отчётом.
30. **External manual has no code diff.** `execution_chain: external_manual` не создаёт worktree, branch, commit или PR. Единственные task artifacts: `j_layer_run.yaml`, `human_action_result.yaml`, `acceptance_evidence.yaml` и audit logs.
31. **No secret values in J artifacts.** J22 и J0 запрещают полные API keys, webhook secrets, refresh tokens, private keys, пароли и recovery codes в `human_action_result.yaml`, logs, markdown и git. Разрешены только `secret_ref`, `env_var_name`, `vault_path`, `external_resource_id`, fingerprint/last4/hash.

---

## 12. Директории артефактов

```
TEST WORKFLOW/10. J. Implementation RS/
  j_layer_status.yaml
  j_layer_summary.yaml                    → J archive / human K trigger instruction
  spike_rejection.yaml                    → I-слой Circuit Breaker
  j_spike_resolution_signal.yaml          → I-слой оркестратор (только при research_only spike success)
  budget_escalation_request.yaml          → I-слой оркестратор
  budget_escalation_response.yaml         ← I-слой оркестратор (ответ)
  spike_rejection_export.yaml             → root-level, только при research-only batch-finalization с architecture_global rejection(s)
  i_layer_handoff.yaml                    → тот же случай; human-launched I-prompt handoff
  constraints_patch.yaml                  → если handoff target_prompt == I6
  i17_spike_rejection_signal.yaml         → если handoff target_prompt == I17
  _archive/                               → Snapshot Supersession Recovery: архив старых terminal research artifacts
  j_runtime.db
  {task_id}/
    j_layer_run.yaml
    j_layer_run.archived.yaml             # создаётся при complete ИЛИ blocked/failure (J0)
    j_task_failure_report.yaml            # canonical path — ВСЕГДА task-local (см. J0.md Output Artifacts); в root не пишется
    j_acceptance_index.yaml               # J0, один раз за задачу: канонический источник check_id для всех J-агентов
    j0_task_lease.yaml                    # J0: fenced lease (owner_token/fencing_token) для CAS-записи runtime-state
    dependency_audit.yaml
    dependency_amendment_request.yaml     ← J6 (при обнаружении новой зависимости в процессе)
    dependency_amendment_decision.yaml    ← J9, mode: amendment (single-decision delta; J0 сплайсит в dependency_audit.yaml)
    dependency_amendment_rejection_context.yaml
    escalation_evidence_manifest.yaml
    escalation_evidence/
    j4_state.yaml                         # non-infra J4 chains: J0-owned mutable CAS pointer; единственный источник текущей J4 generation
    j4_generations/{run_id}/              # non-infra J4 chains: immutable generation dirs (methodology_review.yaml,
                                           # deployment_execution_plan.yaml*, ui_review_plan.yaml*, migration_execution_plan.yaml*,
                                           # manifest.yaml — J0-sealed) — bare-path J4 outputs под {task_id}/ больше не существуют,
                                           # см. J4-J0 Core Generation And Invocation Envelope.md
    j5_test_contract.yaml                 # J5 control/handoff artifact (success | partial_success | no_change_required | blocked)
    coding_blocker.yaml                   # J6/J15 blocker protocol; синхронно j15_no_change_confirmation.yaml для corrective-replay no-op
    tests/...
    static_analysis_report.yaml
    test_report.yaml
    lockfile_check.yaml
    config_validation_report.yaml
    quality_report.yaml
    acceptance_evidence.yaml
    human_action_result.yaml              # J22 / external_manual
    deployment_report.yaml
    deployment_cleanup_report.yaml            # J16 cleanup-only; never overwrites deployment_report.yaml
    deployment_diagnostic_report.yaml         # J16 diagnostic, out-of-band
    hitl_ui_request_<session_id>.yaml     # J13 round 1 — immutable, ui_code только; не hitl_ui_approval.yaml
    hitl_ui_result_<session_id>.yaml      # J13 round 2 — immutable, ссылается на request; см. §6.4
                                           # (+ hitl_ui_abandoned/invalidated/orphaned/launch_blocked_*.yaml —
                                           #  edge-case terminal/transient markers, см. J13.md и regression matrix)
    j_hitl_coder_session.yaml        # J21 (если coding_unit_max_attempts исчерпан); j21_launch_blocked.yaml — non-consuming abort
    j13_merge_intent_<session_id>.yaml    # J0, immutable — двухфазная merge-транзакция J10+J13 (Phase 1)
    j13_merge_commit_<session_id>.yaml    # J0, immutable — commit-маркер той же транзакции (Phase 3a)
    hitl_ui_trust_anchor_<session_id>.yaml # J0, immutable — durable baseline для второго прогона Completion Gate
    fixture_irreversible_ack_<ack_id>.yaml # J0, write-once — acknowledgment необратимой fixture (ui_code)
    manual_check_attestation_<decision_id>.yaml # оператор, вне автоматического цикла — resolution_kind: operator_attestation (infra_code)
    documentation_report.yaml             # J11
    attempt_history/attempt-<NN>/         # J0 — Coding Attempt Archival (архив J7/J8 отчётов per attempt)
    spike_attempts/attempt-<N>/           # J0 — Research Spike Retry Archive (research_spike only)
    j14_generations/{generation_id}/      # infra_code только: immutable generation dirs (methodology_review.yaml,
                                           # deployment_execution_plan.yaml, manifest.yaml) — см. J14-J0-J16-J17
                                           # Generation And State Schemas.md
    j14_state.yaml                        # infra_code только: единственный mutable pointer/retry-state файл
    infra_test_report.yaml
    infra_test_outputs/<run_id>/...            # sanitized bounded J17 evidence
    integration_plan.yaml
    load_test_report.yaml
    # migration_execution_plan.yaml живёт ВНУТРИ j4_generations/{run_id}/ (см. выше), не на bare path
    migration_dry_run_report.yaml
    rollback_test_report.yaml             # J20 тестирует и forward, и rollback скрипты
    spike_findings.yaml
    spike_report.md
    spike_report_gate_failure.yaml      # J2 diagnostic — только если J2 preflight/self-audit gate failed
    spike_resolution.yaml
  archive/
    j_layer_run.{task_id}.archived.yaml      # hash хранится в j_runtime.db.archived_run_hash
```

---

## 13. Принципы написания кода (Закон J-слоя)

Обязательны для J4, J5, J6, J14, J15. Нарушение — блокирующий дефект: шаг не считается завершённым, J8/J7 возвращают управление к J6/J15. J0 не принимает "пояснения" нарушений — только исправление.

**П1 — Невозможные состояния непредставимы.**  
`Status = Draft | Approved | Published | Archived`, не `status: string`. `Money | Quantity | Percent`, не `amount: number`. Набор boolean-флагов → discriminated union.

**П2 — Exhaustive pattern matching.**  
Новый вариант состояния → компилятор принуждает обработать его везде. TypeScript: exhaustiveness через `never`. Elm: компилятор требует покрытия всех веток.

**П3 — Pure core, impure shell.**  
Бизнес-логика — чистые функции: вход → выход, без БД/HTTP/времени/random/env. Эффекты (repositories, API clients, queues, clock) — только на границах системы.

**П4 — Никакой stringly typed архитектуры.**  
Имена событий, статусы, типы операций, route names, feature flags внутри домена — enum/union/newtype. Строки допустимы только на внешней границе (HTTP, JSON, БД, UI). Парсинг строки → доменный тип: один раз на входе.

**П5 — Parse, don't validate.**  
Внешние данные → доменный тип или отклонение. `ValidEmail`, `NonEmptyText`, `PositiveAmount`, `AuthorizedCommand`. После парсинга внутри системы — только типизированные значения.

**П6 — Запрет ослабления типов для компиляции.**  
`any`, `unknown as X`, `as any`, `// @ts-ignore`, `unsafe`, отключение strict mode — запрещены. Код не компилируется → исправить реальную проблему, не обойти типизацию.

**П7 — Использовать существующий код, не генерировать заново.**  
Перед созданием функции/класса/хелпера — проверить проект и approved dependency list. Реализация с нуля: только если аналог отсутствует, не подходит или явно запрещён.

**П8 — Запрет новых зависимостей без проверки.**  
Новый пакет — только через J9 (до кодирования): проверка существования, лицензии, maintenance status, security advisories, lockfile diff. Без `dependency_audit.yaml: approved: true` — блокирующий дефект.

**П9 — Минимум магии.**  
Запрещены: reflection, auto-discovery, implicit DI, monkey patching, decorators с side effects, runtime registration, global mutable singletons, naming conventions вместо явных imports. Только явная композиция, явные imports, явные constructors.

**П10 — Маленькие функции с доменной семантикой.**  
Функция делает один бизнес-шаг с типом, выражающим смысл. Не 300 строк процедурного кода. Не 40 технических микрохелперов без доменного смысла.

**П11 — Один источник истины для состояния.**  
Не дублировать состояние в БД + cache + UI model + derived flags без строгих правил синхронизации. Canonical state → производные значения вычисляются.

**П12 — Обязательные boundary adapters.**  
`BrokerApiResponse` → `PortfolioSnapshot`, `OrderExecution`. Внешняя система не проникает в доменную модель напрямую.

**П13 — Контракты на границах, property tests в ядре.**  
Для критичной логики: property-based tests, golden tests, contract tests. Unit-тесты LLM пишет под свои допущения; расширенные тесты выявляют скрытые ошибки.

**П14 — Static analysis обязательна.**  
J8 — обязательный шаг, идёт до J7. Нарушения → возврат к J6. «Быть аккуратнее» не работает — только конкретные нарушения и конкретные исправления.

**П15 — Никаких silent fallback'ов.**  
«API не сработал → пустой список», «БД недоступна → in-memory mock» — запрещено. Это маскировка незавершённой реализации.

**П16 — Типизированные ошибки.**  
`Result<Success, DomainError>`, где `DomainError = ValidationError | AuthorizationError | ExternalServiceUnavailable | Conflict | InvariantViolation`. Не `throw new Error("failed")`.

**П17 — Инварианты не в комментариях.**  
Инвариант → тип, тест, assert, schema constraint, DB constraint, static rule. Комментарий — только пояснение WHY. Комментарий не является гарантией исполнения.

**П18 — Запрет generic utils dump.**  
Нет `utils.ts`, `helpers.py`, `common.py`. Доменные модули: `Money`, `DateRange`, `TaskSchedule`. Общий helper — только если имеет несколько реально независимых использований.

**П19 — Стандартные протоколы и mature libraries.**  
Даты → date/time library. Decimal/money → decimal/money type. Crypto → approved library. Retry/circuit breaker → готовая lib или centralized module. Auth — не генерировать руками.

**П20 — Чистый diff.**  
Никакого «заодно» форматирования всего файла, массовых переименований, переносов модулей вместе с feature change в одном PR. Чистый diff → возможность поймать галлюцинацию при review.

---

## 14. Открытые вопросы (OQ)

| ID | Вопрос | Статус | Ответственный |
|----|--------|--------|--------------|
| OQ-J-001 | `max_unspecified_decisions` (дефолт: 3) — нужно валидировать на реальных задачах; значение может потребовать калибровки | Открыт | I21 / калибровка |
| OQ-J-002 | Конкретный инструментарий тестового кластера для J12/J16 (K8s namespace? Docker Compose? Minikube?) — определяет I19 Deployment Architect | Открыт | I19 |
| OQ-J-003 | Стратегия загрузки Elm/package decisions из H/I frozen artifacts: явная ссылка в `task_spec.artifact_refs` или глобальный контекст frozen_snapshot? | **Закрыт (R8):** источником для J4/J6 является `task_spec.artifact_refs`. Если пакетные решения нужны многим задачам, I24 может добавить `global_context_refs` в frozen_snapshot, но каждая J-задача всё равно должна ссылаться на нужные артефакты явно через `artifact_refs` | I21/I24 |
| OQ-J-004 | Нужен ли именованный K-слой агент-приёмник для j_layer_summary.yaml или достаточно файла? | **Закрыт (R14/K R2):** не нужен; K не принимает `j_layer_summary.yaml` как audit entrypoint. J0 только сообщает человеку, что можно вручную создать `k_trigger_signal.yaml`. | K-слой план |
| OQ-J-005 | Как J-runner сигнализирует готовность для следующего J0-запуска (flag-файл, exit code, webhook)? | **Закрыт (R8), устарел (R13):** `j_runner_signal.yaml` был добавлен в R8, но упразднён в R13 вместе с самим J-runner — вопрос снят: J0 единственный manual orchestrator, сигнальный файл не нужен (§5.8.1 теперь описывает `human_action_result.yaml`) | J-runner design |
| OQ-J-006 | `execution.chain` в I21 task_spec schema — требует немедленного обновления I21 | **Закрыт (R7):** I21 добавляет `execution.chain`, `execution.reason`, `execution.execution_phase`, `execution.batch_order`; I24 валидирует и материализует эти поля в `tasks.db` | I21/I24 |
| OQ-J-007 | `coding_unit_max_attempts: 3` — это дефолт в J-плане, но значение должно быть переопределяемым в task_spec; нужно явное поле в I21 schema | **Закрыт (R7):** I21 добавляет `budget.max_coding_unit_attempts` и `budget.max_static_fix_iterations`; J0 материализует их в `j_layer_run.yaml` при старте задачи (R13) | I21 |
| OQ-J-008 | Pipelined mode: как выбирается следующая задача при нескольких кандидатах? (FIFO? по приоритету? по estimated_complexity?) | Future, not blocking MVP — pipelined требует отдельного runner-компонента (§3.7) | J-layer design |
| OQ-J-009 | shared_resources список в §3.7 — нужна ли его конфигурация в frozen_snapshot (project-specific lockfiles)? | Future, not blocking MVP — актуально только при pipelined mode | J-layer design / I24 |
| OQ-J-010 | research_only → spike_resolution → I-оркестратор: нужен ли явный артефакт-сигнал (j_spike_resolution_signal.yaml) или J-runner просто кладёт spike_resolution.yaml в известную папку? | **Закрыт (R6):** добавлен j_spike_resolution_signal.yaml (§5.8); spike_resolution.yaml — внутренний R/O артефакт J; сигнал для I-оркестратора — отдельный файл | I-оркестратор §13 |

---

## 15. Что требует обновления в I-слое

| Агент I-слоя | Что добавить |
|---|---|
| I21 Task Spec Agent | **Синхронизировано в R7:** обязательный блок `execution.chain` + `execution.reason` + `execution.execution_phase` (strict_first/implementation) + `execution.batch_order` (число); `budget.max_*`; `files_allowed_to_touch`; `resource_locks: []`; `triggers_module_complete`; `rollback_strategy` для migration tasks |
| I24 Gatekeeper | **Синхронизировано в R7:** `tasks.db` — canonical task queue; `snapshot_mode` явно присутствует в frozen_snapshot.yaml; не использовать числовые batch_id: 0/N для J-порядка — только `execution_phase` + `batch_order` из task_spec |
| I-слой оркестратор (§13) | Добавить: обработка `budget_escalation_request.yaml` → написание `budget_escalation_response.yaml`; обработка `spike_rejection.yaml` из J; обработка `j_spike_resolution_signal.yaml` от J при research_only mode (≠ budget_escalation_request!) → запуск полного impl path (I7→I8–I15→I16/I17→I6 patch→I18–I24) → публикация нового `frozen_snapshot.yaml` с `snapshot_mode: implementation` |

---

## 16. Порядок написания промптов J-слоя

1. J0 — Dispatcher (ядро логики; читает task_type + execution_chain, не выводит)
2. J1/J2/J3 — Research/Spike chain (разблокирует impl-фазу)
3. J4/J9 — Methodologist + Dependency Auditor (gate перед кодированием)
4. J5/J6/J8/J7 — Coding atomic unit
5. J9b/J10/J11 — Lockfile check, analyst, documenter
6. J12/J13/J20/J21 — Module deploy, HITL UI, Migration dry-run, HITL Coder Session
7. J14/J15/J16/J17 — Infrastructure chain
8. J18/J19 — Integration chain
