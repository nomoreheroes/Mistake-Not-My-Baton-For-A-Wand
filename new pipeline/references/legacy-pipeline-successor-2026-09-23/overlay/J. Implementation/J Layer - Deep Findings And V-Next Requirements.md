# J Layer — Глубокие находки ревью и требования к следующей версии пайплайна

**Дата:** 2026-08-21
**Статус:** ЧАСТЬ ТЗ V-NEXT (не runtime-контракт текущего слоя J)
**Метод:** сквозное ревью всех промптов J (J0–J22, shared-контракты `J4-J0 Core Generation And Invocation Envelope.md`, `J14-J0-J16-J17 Generation And State Schemas.md`, `J Layer - Architecture Plan.md`, регрессионная матрица J13) со сверкой против **фактических** артефактов I-слоя: `j_handoff_signal.yaml`, `frozen_snapshot.yaml` (SNAP-I-I-run-20260618-001-IMPL-20260714T131101Z), `tasks.db` (495 задач), `task_specs/` (495 файлов), формула агрегатного хеша `task_specs/` воспроизведена эмпирически. Все 69 контрактных тестов `tests/` зелёные после правок.

Локальные несостыковки исправлены на месте (список — §0 ниже). Этот документ фиксирует то, что **нельзя** чинить точечной правкой одного файла: архитектурные решения, межслойные контракты и системные свойства пайплайна, требующие версии v-next.

---

## 0. Что уже исправлено локально (для трассировки, не требует действий)

| # | Файл | Суть правки |
|---|------|-------------|
| 1 | `J10. Code Analyst.md` | Preflight требовал `j5_test_contract.yaml` schema `1.1`, канон J5 — `1.2` (дедлок любого partial contract) |
| 2 | `J3. Spike Resolver.md` | `snapshot_mode_mismatch: false \| true` в OUTCOME_ALREADY_EXISTS — `true` недостижим по собственному контракту (mismatch → `stale_or_conflicting_outcome`) |
| 3 | `J0. Dispatcher.md` | `waiting.kind` enum: добавлены реально используемые `blocked_until_j0_budget_decision` (+ routing-строка resume) и `hitl_ui_authorization_pending` в Response Format |
| 4 | `J0. Dispatcher.md` | Схема `j_runtime.db`: отсутствовала колонка `merged_at`, которую пишет Startup Reconciliation |
| 5 | `J0. Dispatcher.md` + план §10 | Список полей `j_handoff_signal.yaml` приведён к фактической схеме I24 (полей `signal_id`/`entry_point` не существует) |
| 6 | `J0. Dispatcher.md` | Snapshot Gate: имя поля `content_hash` (не `hash`); формула агрегатного хеша `task_specs/` уточнена (префикс `task_specs/` в `<path>`, только обычные файлы, исключая `.i21_staging`) — сверено вычислением против published snapshot |
| 7 | `J0. Dispatcher.md` + план §3.5.1 | Исключение задач: в tasks.db нет статуса `blocked` (CHECK: `ready\|deferred`) — заменено на `status != 'ready'` |
| 8 | `J0. Dispatcher.md` | J12-бандл: `j12_attempt_number` → `attempt_number` (как читает сам J12.md) |
| 9 | `J0. Dispatcher.md` | Operator-facing шаблон ссылался на несуществующее `task_spec.human_action.summary` |
| 10 | План | Перенумерация задвоенного §3.3 и ~15 битых перекрёстных ссылок (§3.4–§3.9) |
| 11 | План §5.2, §8 | Нормативные баннеры на устаревшие схемы `j_layer_run.yaml`/`j_runtime.db` (канон — J0.md); исправлено ложное «pipeline.db не существует» |
| 12 | План §3.5/§6.10 | Порядок старта external_manual приведён к канону J0 (launch → validate → set waiting) |
| 13 | План §5.8.1 | `status: pending` добавлен в enum `human_action_result.yaml` (template-состояние J22) |
| 14 | План §12 | Листинг директорий синхронизирован с J0 Output Artifacts (`j_task_failure_report` — task-local; bare-пути J4 → `j4_generations/`; добавлены merge intent/commit, trust anchor, ack, attestation, attempt_history, spike_attempts, root handoff-артефакты) |
| 15 | План | Инвариант 10 согласован с R18 batch policy; инвариант 3 — skip_reason рождается в J0, не в task_spec; строка J19 в merge_requirements; примечание к OQ-J-005 (j_runner_signal упразднён R13); §5.9 — источник для research_spike; §10 — предупреждение про technology_decisions вне снапшота |

### 0.1 Дополнение 2026-08-25 (найдено при исполнении J0 на задаче T-010)

| # | Файл | Суть правки |
|---|------|-------------|
| 16 | `TEST WORKFLOW/10. J. Implementation RS/j_runtime.db` | Физический файл был создан 2026-06-29 по редакции схемы, предшествовавшей правке №4, и не имел колонки `merged_at`. Добавлена через `ALTER TABLE ... ADD COLUMN` (аддитивно, 5 строк сохранены). Порядок колонок отличается от `CREATE TABLE` в J0.md — не дефект, J0 адресует колонки по имени |
| 17 | `J0. Dispatcher.md` §0.0.1 + §0 | **Первопричина №16**: правка №4 изменила контракт схемы, но у J0 не существовало пути миграции уже существующего долгоживущего файла — расхождение проявилось бы только на первой задаче с PR, то есть потенциально через десятки закрытых `external_manual`/`research` задач. Добавлен обязательный шаг **Schema reconciliation** в Startup Reconciliation Gate: сверка `PRAGMA table_info` с контрактом, `ADD COLUMN` для недостающих (единственная разрешённая J0 DDL-операция), advisory на лишние, `Block on contradiction` на конфликт типов, запрет миграции архивных копий |
| 18 | `J22. External Manual Action.md` «Acceptance Check Mapping» | Реальные I21 `acceptance_checks` для `external_manual` содержат self-referential хвост `"...; task_results/<id>/acceptance_evidence.yaml records status: passed and check_id: <hint_id>"`. Классификация (presence/value-comparison/unmappable) выполнялась моделью по всему тексту, поэтому исход зависел от прочтения: T-009 прошёл `satisfied`, но на T-010 J22 предупредил о вероятном `unmappable`. Правило сделано детерминированным: хвост игнорируется при классификации, не является value-comparison, не делает check unmappable, и порождает ровно один advisory `spec_conflict` (`owner: i_layer`), не влияющий на `status` |
| 19 | `J22. External Manual Action.md` «Входные Артефакты» | `task_results/<task_id>/...` нормативно объявлен human-readable алиасом `{artifact_root}/{task_id}/...` (как уже сделано в J0.md «Artifact Root»); J22 обязан показывать человеку канонический путь и пояснять расхождение |
| 20 | `I21. Task Spec Agent.md` «Правила для acceptance_checks» | **Первопричина №18**: у I21 было правило про словарь `human_action_result.yaml` (вход J22), но не было запрета предписывать содержимое **выходных** артефактов J-слоя. Добавлен запрет с тремя обоснованиями (циркулярность, несуществующий `status: passed`, `check_id` всегда `AC-00N`) и образцом правильной формулировки |
| 21 | `I23. Task Graph QA.md` Шаг 3b, Проверка 4 | **Почему дефект пережил QA**: «Schema field check» проверяла только словарь `human_action_result.yaml`; `acceptance_evidence.yaml` не покрывался ничем, поэтому хвост проходил гейт незамеченным даже в прогоне HA-I23-001..008, который переписывал ровно эти же строки. Добавлен шаг 3 «Output-artifact prescription check» (применяется к части после `;` независимо от успеха шагов 1–2), новое значение `mapping_failure_reason: prescribes_j_layer_output`, строка в чеклист |
| 22 | План §5.3 | `budget_escalation_request.yaml`: в `trigger.type` отсутствовал `human_action_escalation` (4-й формальный триггер по J0.md), а `requested_action` перечислял только `technology_decision_update` (канон J21), хотя J22 подаёт в то же поле `architecture_decision_update` (канон J0.md п.4/J22.md) — enum развёрнут в union обоих источников с указанием, кто что подаёт. Обнаружено при фактическом создании BER-T-010-001 — первой эскалации типа `human_action_escalation` в этом прогоне. **Отдельная находка для v-next:** два разных имени (`technology_decision_update` у J21 vs `architecture_decision_update` у J22) для соседних по смыслу действий I-слоя — J0 обязан копировать значение как есть, но I-слою приходится понимать оба |
| 23 | `I Layer - Architecture Plan.md` §5.24 (новый) + §6 | Определён протокол budget escalation: routing-таблица scope→target_prompt, приоритет routing screen над `requested_action`, `prompt_defect` как тупик без агента, I24 — единственный производитель response, симметрия `request_id`/`request_hash`. Строка входа из J добавлена в §6 |
| 24 | `J0. Dispatcher.md` | Обязательный handoff package `j_budget_escalation_signal.yaml` (schema + правила, generic handoff без `target_prompt` запрещён — по образцу §5.18); resume-ветка дополнена сверкой `request_id`/`request_hash`, прогоном `new_snapshot_id` через Snapshot Gate и идемпотентностью повторного `resolved`; артефакт добавлен в root Output Artifacts |
| 25 | `I20. Task Tree Builder.md` | Строка входа + **Приоритет −1** в run_context-лестнице (возврат из downstream-слоя проверяется раньше внутренних I-сигналов, чтобы устаревший внутренний сигнал его не перебил); `valid_j_budget_escalation_signal` с hash-проверками; запрет применять `scope: prompt_defect`; обязанность перечислить непринятые scope в run_event |
| 26 | `I21. Task Spec Agent.md`, `I17. Trade-off HITL.md` | Строки входа для `scope: task_spec_text` (I21) и `architecture_decision`/`technology_decision` (I17) |
| 27 | `I24. Gatekeeper & Publisher.md` | Шаг 10 п.5b: I24 объявлен единственным производителем `budget_escalation_response.yaml` (обоснование: response несёт `new_snapshot_id`, публикует снапшоты только I24); схема с `applied_scope`/`unapplied_scope`; порядок записи после `j_handoff_signal.yaml` и до терминального `current_stage`; строка в таблице выходов implementation-режима и пункт чеклиста |
| 28 | `I19. Deployment Architect.md` | **Корневая причина blanket-рёбер найдена не там, где предполагалось.** `blocks_task_types` производит I19, а не I20, и в I20 это поле не упоминается ни разу. Связи «какой компонент реально потребляет produced ref» не существовало нигде: у компонентов `system_architecture.final.yaml` нет полей `external_dependencies`/`secrets`/`consumed_by`, а `payment_contract` есть только у платёжных компонентов и не обобщается. Добавлены обязательные `consumption_scope` (`component_scoped \| environment_wide`), `consumed_by_components[]` и `consumption_scope_justification`; `blocks_task_types` нормативно понижен до фильтра-подсказки с явным запретом быть источником рёбер |
| 29 | `I20. Task Tree Builder.md` | Правило «`human_action` → …» уже несло верное условие («если задача использует produced ref»), но **прозой, без механического предиката** — и условие схлопнулось в список типов (T-013 `analytics_event_service` получил `depends_on: [T-008, T-009, T-010, T-011]`, то есть зависимость сразу от GCP, Stripe, App Store и Google Play). Переписано в два проверяемых условия (тип + потребление) с явным «условие 1 само по себе ребра не создаёт» и запретом fallback'а на старое поведение при отсутствии новых полей во входном снапшоте |
| 30 | `I23. Task Graph QA.md` Шаг 3b | Новая Проверка 5 + `issue: blanket_human_action_dependency`: QA независимо проверяет каждое ребро `depends_on` на human_action-задачу против `consumption_scope`/`consumed_by_components`. Тот же принцип, что у правки 21 — не доверять тому, что производитель аккуратно применил своё правило |

**Статус применения:** правки 16–30 внесены. Frozen snapshot `SNAP-I-I-run-20260618-001-IMPL-20260824T171500Z` **не трогался** (инвариант J0 №5 «No task_spec repair» + хеши I24): дефектные формулировки в `task_specs/{T-008..T-012}.yaml` остаются как есть, но теперь обрабатываются детерминированно (правка 18) и не воспроизведутся в следующем снапшоте (правки 20–21).

---

## 1. КРИТИЧНОЕ: ветка `ui_code` мертва в реальном прогоне — визуальная приёмка не существует

**Факт.** В published `tasks.db` (495 задач) распределение цепочек: client_code 203, integration 130, server_code 87, config 29, infra_code 20, qa 14, migration 7, external_manual 5. **`ui_code`: 0.** При этом продукт — Elm on-device приложение с UI, а план §2 прямо декларирует маппинг `code.domain_logic + on_device (Elm) → ui_code`. I21 замаппил всё on-device в `client_code`. Grep по всем 495 task_specs: ни одного упоминания `human_ui`/`manual`/`hitl` в acceptance_checks.

**Последствия.**
1. Весь стек J13 HITL-UI — самый дорогой по инженерии контур слоя J (двухраундовый протокол, candidate/promotion, terminal claim, trust anchor, merge-транзакция, 40+ сценариев регрессионной матрицы, `ui_review_plan.yaml` у J4, hybrid-компоненты у J10) — **недостижимый код** в этом прогоне.
2. Хуже: видимое человеку поведение UI вообще не представлено в acceptance-контуре. Ни одна задача не потребует человеческого подтверждения того, что экран выглядит и ведёт себя как задумано в G/H-слоях. Продукт может пройти все 495 задач и быть визуально сломанным.

**Уточнение корневой причины (расследование 2026-08-24).** Первичная формулировка «I21 замаппил всё в client_code» неверна: chain-правила I21 (строки 260–264, инвариант 12 про `code.presentation`) корректны и просто **ни разу не сработали** — в `task_tree.yaml` ноль задач `code.presentation`. Фактическая цепочка отказа:
1. **ADR-I17-007/ADR-I17-008** (HITL) пометили все H12/H14 frontend-internal решения `explicitly_not_applicable` для архитектуры («no I-layer backend/on-device counterpart», см. `system_architecture.final.yaml#h_layer_constraint_treatment`). Решение легитимно для *архитектурного документа* (архитектура моделирует engines/stores/adapters — все 21 компонент), но молча стало решением о *плане реализации*: presentation исчез из вселенной покрытия.
2. **I20** строит coverage-цели из causal graph (архитектура) + PRD. UI-компонентов нет → `presentation_surface`-механика I20 (строки 763/776/789/914/959/982 — она существует и полна!) не породила ни одной единицы. UI-стори PRD (например `US-onboarding-01`) оказались «покрыты» **агрегированной QA-задачей T-495** («Verify prd … for 481 covered task(s)», `implementation_task_refs: [T-495]`, где T-495 — `task_type: qa`) — прямое нарушение собственного правила I20 (строка 792: «prd.index.yaml не должен закрываться только агрегированными QA задачами»).
3. **I23** проверил покрытие структурно (`task_refs` непусты → pass), без типовой совместимости (qa-задача засчитана как *implementation*-покрытие поведенческой стори); его Step 5g легально принял ADR-закрытие H-констрейнтов. **I22** (человек) на 495 задачах отсутствие целого класса не увидел. При этом весь frontend уже полностью специфицирован и прошёл гейт H15 (`h3/h5/h7/h10_elm_*_spec.yaml`, 11 поверхностей G-слоя `component_mapping_*.yaml`) — реализационный контракт есть, носителя-задач нет.

**СТАТУС 2026-08-24: промпты I20/I23/I21/I6/I17 пропатчены, ремонт запланирован — см. `I. Architecture & Task Graph/PRESENTATION-COVERAGE-REPAIR - Rerun Plan.md`.** Пункты ниже реализованы в промптах; здесь они остаются как формулировка требования.

**Требование v-next** (детальный план текущего исправления — см. `PRESENTATION-COVERAGE-REPAIR - Rerun Plan.md`):
- **I20 (главное)**: (а) реестр поверхностей G/H (`component_mapping_*.yaml`, `h10_elm_view_spec.yaml`) — обязательный вход и самостоятельный класс coverage-целей, независимый от компонентов архитектуры: каждая поверхность → ≥1 `presentation_surface` unit → `code.presentation` задача, либо явный `coverage_gap`/`deferred` с decision_ref; (б) типовая совместимость покрытия: `implementation_task_refs` не может состоять только из `qa`/`human_action` задач; поведенческая UI-стори покрывается только `code.presentation`-юнитом (машинно-проверяемая форма существующего правила 792).
- **I23 (backstop)**: два блокирующих чека — (а) surface inventory × task_tree (каждая поверхность имеет implementation-носителя или явное deferred-решение); (б) chain-mix sanity: продукт с Elm/web UI runtime (наличие h12/h9/bridge во входах) и 0 задач `ui_code`/`code.presentation` → blocking finding; (в) типовая проверка coverage-строк (qa-only implementation_task_refs запрещён).
- **I6/I17**: у `explicitly_not_applicable` появляется обязательный scope: `applies_to: architecture_conformance_only | architecture_and_implementation` (default — первый); I20/I23 обязаны маршрутизировать constraint с `architecture_conformance_only` в implementation-покрытие.
- **I21**: chain-правила не трогать (корректны); добавить дешёвый guard-инвариант: full_implementation при непустом surface inventory и нуле `code.presentation` в дереве → не писать спеки, вернуть управление I20 (self-healing routing к владельцу); для `code.presentation` — обязательные human-visible acceptance checks в словаре, который J4 (`ui_review_plan`) умеет классифицировать в `human_ui`/`hybrid` (без этого ui_code-задачи дадут `no_manual_ui_scope` и J13 всё равно не включится); заодно эмитить `partial_test_contract_allowed` (см. §2 — visual-checks сделают это поле практически необходимым).
- Альтернатива (если решено, что HITL-UI не нужен в MVP): убрать J13-стек из обязательной цепочки и зафиксировать это решением, а не молчаливой недостижимостью — сейчас поддержание мёртвого контура стоит дороже всего остального слоя.

## 2. КРИТИЧНОЕ: `partial_test_contract_allowed` никогда не эмитится I21 — путь `gap_allowed_partial_contract` недостижим, livelock-риск подтверждён

**Факт.** Ни один из 495 task_specs не содержит `partial_test_contract_allowed` (известная запись от 2026-07-16 подтверждена на фактических артефактах). Вся ветка J5 `partial_success` → J10 `gap_allowed_partial_contract` → Completion Gate «авторизованный J5 permanent gap» структурно недостижима: J5 обязан блокироваться на любом AC без determinable expected behavior.

**Последствия.** Любая задача с хотя бы одним принципиально нетестируемым в J-слое acceptance check идёт в цикл: J5 blocked → `j_task_failure_report`/budget escalation → I-слой должен переиздать spec → но I21-шаблон это поле не производит → повторение. Это livelock на уровне пайплайна, а не задачи.

**Требование v-next.** I21 обязан материализовать `partial_test_contract_allowed` (явное `false` по умолчанию) и правило его выставления (какие категории AC допускают permanent gap); I23 — гейт на согласованность поля с текстами AC. На стороне J достаточно текущих контрактов — они уже симметричны.

## 3. Целостность снапшота неполна: `technology_decisions.yaml` (и любые policy-refs) вне `included_artifacts`

**Факт.** `frozen_snapshot.yaml#included_artifacts` published-снапшота: system_architecture.final, api_binding_spec, on_device_bridge_contract, architecture_decisions, causal_graph.db, observability_spec, deployment_spec, assumptions, coverage_matrix, task_specs/, tasks.db. `technology_decisions.yaml` — **отсутствует**, при этом J4 (Источник истины п.6, Trust Hierarchy) и J9 (Source Of Truth п.6, license policy) читают его как вход. Это unhashed-вход вне snapshot-дисциплины: Snapshot Gate его не проверяет, изменение файла между задачами невидимо.

J9 деградирует корректно (консервативный license-дефолт + cap `audit_confidence`), поэтому это не блокер прогона — но это дыра в модели целостности, ради которой Snapshot Gate вообще существует.

**Требование v-next.** I24: включить `technology_decisions.yaml` (и любой файл, который хотя бы один J-агент объявляет входом) в `included_artifacts` с `content_hash`; J-агенты — читать его только по пути из снапшота. Общее правило: **множество файлов, упомянутых во «Входных артефактах» всех J-промптов, обязано быть подмножеством `included_artifacts ∪ runtime-артефакты J`** — это проверяемо статическим тестом и должно стать contract-тестом.

## 4. Словарь acceptance_checks I21 несовместим со словарём артефактов J — держится на shim'ах

**Факт.** Реальные тексты AC из task_specs: `task_results/T-001/acceptance_evidence.yaml records status: passed`, `task_results/T-001/validation.log`, `evidence_status: acknowledged`. В J-слое: путь — `{artifact_root}/{task_id}/…`, статусы — `satisfied|failed|gap_allowed_partial_contract|not_applicable_confirmed`, поля `evidence_status` не существует, `validation.log` не создаётся. Сегодня это закрыто двумя shim'ами: J0 «Artifact Root» (маппинг `task_results/` и правило про validation.log) и J22 (примечание о prose-формате `evidence_required[]`). J10/J22 вынуждены интерпретировать тексты семантически, а не буквально — то есть машинная проверка «AC удовлетворён» частично опирается на интерпретацию модели.

**Требование v-next.** Единый словарь evidence между I21 и J: либо I21 генерирует AC-тексты в канонических терминах J (пути `{artifact_root}/{task_id}/`, статусы `satisfied|…`), либо AC-тексты становятся абстрактными (без путей и статусов вообще — «forward и rollback проверки прошли»), а привязку к артефактам делает исключительно `j_acceptance_index` + evidence map. Смешанный режим «I пишет пути в прозе, J перетолковывает» — источник тихих расхождений.

## 5. Пропускная способность: Approval Gate × 495 задач — операционно нереализуемо в текущем виде

**Факт.** Обязательное прямое согласие пользователя перед **каждым** subagent (инвариант 19/23a) при 495 задачах и 8–11 шагах цепочки — порядка **4–5 тысяч ручных подтверждений**, строго последовательно (`sequential only`), плюс CI-ожидания и PR-merge на каждую задачу. Это осознанное governance-решение текущей версии, но при данном объёме слой J не завершится за разумное время; риск — эрозия дисциплины (человек начнёт подтверждать не глядя), что хуже, чем структурированная автономия.

**Требование v-next.** Ярусная модель автономии вместо бинарной:
- **Tier A (auto)**: read-only/solo-отчётные агенты (J9b, J10, J11, J8 при чистом diff) — авто-продолжение в рамках задачи, с журналом.
- **Tier B (batch consent)**: согласие на «цепочку до следующей waiting/terminal точки» одной командой (сейчас прямо запрещено — «выполни J0 разрешает только первый subagent»).
- **Tier C (HITL, как сейчас)**: J13/J21/J22, budget escalation, merge в main.
Плюс возвращение pipelined-режима в план (§3.7) как спроектированной цели: lease-механика (`j0_task_lease`, fencing) уже готова к мульти-lane лучше, чем признаёт план.

## 6. `j_layer_run.yaml` — монолитный mutable hotspot; прецедент `j14_state.yaml` показывает целевую модель

**Факт.** Один файл несёт: счётчики попыток, step_chain/steps, durable-блок `hitl_ui` (13+ полей session.*), `fixture_acknowledgments_index`, `coding_attempt_history`, amendment-счётчики, external_manual generation. Каждый переход — atomic replace **всего файла** под lease+state_revision; конкурентная правка любой несвязанной секции конфликтует со всеми. Именно из-за этого выросли самые сложные протоколы J0 (три страницы crash-window правил для hitl_ui внутри общего файла). Для infra тот же класс проблем уже решён выделением `j14_state.yaml` (одно concern, одна CAS-точка) — и это самая чистая подсистема слоя.

**Требование v-next.** Разнести по concern-файлам: `j_run_state.yaml` (cursor/counters), `j_hitl_ui_state.yaml`, `j_amendment_state.yaml`, `j_attempt_history/` (уже append-only каталог). Правило: один mutable файл = один агрегат = один CAS. Это сократит и текст J0 (большая часть «Per-task lock», «Atomic replace», transition-таблиц станет общей библиотекой harness'а, см. §8).

## 7. Неоднородный envelope/fencing: три поколения дисциплины в одном слое

**Факт.** Сейчас сосуществуют:
- полный invocation envelope (J4/J5/J10/J12 — shared doc);
- generation+report envelope (J14/J16/J17 — shared doc) + ad-hoc эквиваленты J15 (`invocation_id`), J8/J9/J9b (`run_id`+`task_spec_hash`);
- **без per-dispatch fencing**: J7 (только `coding_unit_attempt_count` — два физических вызова J7 в одной попытке неразличимы, тот самый аргумент, которым J8 обосновал введение `run_id`), J11 (attempt-key без run_id), J18, J19 (сознательно без хешей вовсе), J20 (свой pair/run-id gate), J1/J2/J3 (hash-bundle от J0, без echo-fencing).

**Требование v-next.** Один документ «Uniform Agent Report Envelope» (по образцу J14-J0-J16-J17): `run_id` + `attempt_key` + `input_hash_bindings` обязательны для **каждого** агента, echo-проверка до чтения `status` — универсальное правило Step Result Contract, а не 6 вариантов по строкам. Отдельно закрыть J7 (run_id) — сейчас это самое слабое звено coding_unit.

## 8. Harness-примитивы описаны прозой в промптах — вынести в исполняемую библиотеку

**Факт.** Atomic-replace, CAS по revision, fenced lease, temp+rename, candidate/promotion, claim/reclaim, двухфазные merge-транзакции — описаны на десятках страниц естественного языка внутри J0 и повторяются (с вариациями) в J13/J14-схемах. Модель обязана «исполнять» файловые транзакции по прозе — это главный источник сложности и риска дрейфа. Дисперсия хеш-профилей — того же корня: canonical-object/raw-bytes определены в J13.md; J19 заявляет «канонической формулы task_spec_hash для J-агентов не существует» и сверяет по plain-text равенству; J1/J13/J14 не имеют права хешировать и зависят от wrapper.

**Требование v-next.**
1. Выделить `J Harness Primitives.md` + референс-скрипты (`tools/`): atomic_replace, cas_update, lease_acquire, promote_candidate, merge_txn, hash_canonical, hash_raw. Промпты ссылаются на именованные примитивы, не переописывают их.
2. Единый «Hash Profiles Registry» (два профиля, их области, кто вычисляет — агент/J0/wrapper) — сейчас это фрагмент внутри J13.md, на который опираются все.
3. Контрактные тесты уже показали правильный путь (69 тестов) — расширить их на инварианты «план↔промпты» и «Входные артефакты ⊆ снапшот» (§3).

## 9. Слабейший межслойный контракт — budget escalation

**Факт.** `budget_escalation_request/response` — единственный I↔J канал без hash-binding и freshness-дисциплины: response не эхо-ит hash запроса, нет schema_version-гейта на стороне J при resume, нет защиты от stale response после нескольких эскалаций (сравните с `j_handoff_signal` + Snapshot Gate, где это решено образцово). При этом канал критичный: по нему пересобирается снапшот.

**Требование v-next.** Симметричный контракт: `request_id` + `request_hash` эхо в response; `superseded_task_ids/new_task_ids` привязаны к `new_snapshot_id`, который обязан пройти обычный Snapshot Gate (j_handoff_signal нового снапшота), прежде чем J0 применит response; повторный resolve того же request_id — идемпотентен.

**ХУЖЕ, ЧЕМ ЗАФИКСИРОВАНО ВЫШЕ — подтверждено эмпирически 2026-08-25 (BER-T-010-001).** Абзац выше описывает *качество* канала (нет hash-binding, нет freshness-дисциплины), молча предполагая, что приёмник существует. Приёмника нет. Проверено по всему репозиторию промптов:

- `budget_escalation_request.yaml` вне `J. Implementation/` упоминается **один раз** — в `I24. Gatekeeper & Publisher.md:2119`, и то в отрицательном смысле («записать `j_spike_resolution_signal.yaml` … не `budget_escalation_request.yaml`»). Ни один I-агент не объявляет его своим входом.
- `budget_escalation_response.yaml` не встречается **ни в одном** файле вне J-слоя. У артефакта, которого J0 ждёт в состоянии `pending_i_layer_response`, нет ни одного производителя.
- Карта входов I-слоя (`I Layer - Architecture Plan.md` §6) перечисляет ровно **один** вход из J: `spike_rejection.yaml` → I6/I17. Для budget escalation аналога нет.

Сравните с research-spike-веткой, где канал закрыт образцово (§5.18 Circuit Breaker): J0 обязан собрать prompt-specific handoff package (`spike_rejection_export.yaml` + `i_layer_handoff.yaml` + `constraints_patch.yaml`/`i17_spike_rejection_signal.yaml`), routing определяется явными правилами, а generic handoff без `target_prompt` прямо запрещён. У budget escalation нет ни handoff package, ни routing-правил, ни целевого промпта.

**Следствие — не теоретическое.** J0 контрактно обязан при формальном триггере создать `budget_escalation_request.yaml`, перевести слой в `pending_i_layer_response` и остановиться; в этом состоянии он по инварианту №18 не читает ничего, кроме response. Значит любая budget/human_action эскалация **терминально подвешивает слой**: J0 не имеет права ни продолжить, ни изобрести маршрут («не угадывай», «J0 не фабрикует содержимое агентских отчётов»), а I-слой не имеет входа, чтобы ответить. Первая же реальная эскалация в прогоне (BER-T-010-001, T-010, `human_action_escalation`) в это и упёрлась.

**Требование v-next — дополнительно к симметричному контракту выше.** Закрыть канал по образцу §5.18: (а) назначить I-агента-приёмника для каждого `requested_action` (минимум: `task_spec_update` → I20/I21, `task_decomposition` → I20, `architecture_decision_update`/`technology_decision_update` → I17/I6); (б) определить, кто именно пишет `budget_escalation_response.yaml` (кандидат — I24 как gatekeeper, тот же агент, что публикует снапшот, на который response ссылается через `new_snapshot_id`); (в) обязать J0 собирать prompt-specific handoff package с явным `target_prompt`, как он уже делает для spike rejection; (г) добавить `budget_escalation_request.yaml` в §6 карты входов I-слоя.

**Взаимодействие с §11.** BER-T-010-001 просит перевести T-010 в `deferred` — то есть первая же реальная эскалация упирается сразу в два незакрытых контракта: канал без приёмника (§9) и `deferred` без жизненного цикла (§11).

**СТАТУС 2026-08-25: канал закрыт (правки 23–27).** Протокол определён и разведён по владельцам: `I Layer - Architecture Plan.md` §5.24 (routing-таблица `escalation_routing_screen.scope` → `target_prompt`, приоритет screen над грубым `requested_action`, `prompt_defect` как честный тупик без агента-исполнителя, I24 как единственный производитель response, симметрия `request_id`/`request_hash`); §6 карты входов; `J0. Dispatcher.md` (обязательный handoff package `j_budget_escalation_signal.yaml` + сверка `request_id`/`request_hash` перед применением response + Snapshot Gate на `new_snapshot_id` + идемпотентность повторного `resolved`); входные строки у I20/I21/I17 и Приоритет −1 в run_context-лестнице I20; `I24. Gatekeeper & Publisher.md` Шаг 10 п.5b (схема response, порядок записи после `j_handoff_signal.yaml`, `applied_scope`/`unapplied_scope`). Требование симметричного контракта из абзаца выше выполнено этими же правками. **Остаётся открытым для v-next:** §11 (`deferred` без жизненного цикла в J) — BER-T-010-001 просит именно `deferred`, и Layer Finalization по-прежнему не перечисляет такие задачи в summary.

## 10. Контрактная диета task_spec: мёртвые поля и дубли

**Факт (по фактическим спекам).** Поля без единого потребителя в J: `destructive`, `requires_human_review`, `risk_level`, `mitigation_plan`, `parallel_group`, `sequence_order`, `status_at_spec_time`, `batch_id` (J использует только `execution.batch_order`), `component_id` (дублируется в tasks.db). `data_loss_risk` существует **дважды** (top-level и `provenance.data_loss_risk`) — J0 preflight читает top-level, второй экземпляр — потенциальный источник расхождения. `manual_check_required/description` читает только J22 и только как прозу.

**Требование v-next.** I21: либо назначить потребителя каждому полю (например `requires_human_review: true` → обязательный HITL-шаг в chain — сейчас это молча игнорируется!), либо удалить из схемы. `data_loss_risk` — ровно одно каноническое место. Особо: `requires_human_review: true` стоит на T-008..T-012 и ни на что не влияет — это семантическая потеря сигнала I-слоя.

## 11. `deferred` в tasks.db не имеет жизненного цикла в J

**Факт.** CHECK-констрейнт допускает `ready|deferred`; J (после локальной правки) корректно исключает не-ready задачи, но нигде не определено: кто, когда и как переводит `deferred → ready` (I-слой? новый снапшот? вручную?), как J отражает наличие deferred-задач в `j_layer_summary` (сейчас Layer Finalization их не упоминает — слой может завершиться «complete», молча не выполнив deferred).

**Требование v-next.** Определить в I24: deferred-задачи меняют статус только новой публикацией снапшота; J0 Layer Finalization обязан перечислять их в summary отдельным списком и не выставлять `ready_for_human_k_trigger: true`, если deferred-задачи блокируют acceptance-scope продукта.

**СТАТУС 2026-08-26: I-половина закрыта, J-половина открыта.** `I24. Gatekeeper & Publisher.md` Шаг 6b-2 определяет жизненный цикл: переход `deferred → ready` только новой публикацией снапшота (правка status внутри опубликованного `tasks.db` = порча снапшота), обязательные `reentry_condition`/`owner` с gate failure `deferred_task_without_reentry_condition`, секция `deferred_scope[]` в `frozen_snapshot.yaml` с механически вычисляемым `blocks_acceptance_scope`, и передача `deferred_scope_present: true` через `j_handoff_signal.yaml`. **СТАТУС 2026-08-26 (позже в тот же день): ЗАКРЫТО С ОБЕИХ СТОРОН.** Приёмная сторона реализована в
`J0. Dispatcher.md`: (а) Snapshot Gate, раздел `snapshot_mode: implementation` — обязательный приём
`deferred_scope` с четырьмя блокирующими проверками (`deferred_scope_declared_but_missing`,
`deferred_task_not_declared_in_scope`, `deferred_scope_task_mismatch`, `deferred_scope_entry_incomplete`),
запись списка в `j_layer_status.yaml#deferred_scope` и явный запрет переводить `deferred → ready` на стороне J;
(б) Layer Finalization — `deferred_scope` обязателен в `j_layer_summary` отдельным поимённым списком
(при отсутствии отложенных писать `deferred_scope: []` явно), а `ready_for_human_k_trigger` гейтится:
при `blocks_acceptance_scope: true` хотя бы у одной записи → `false` с
`k_trigger_blocked_reason: deferred_tasks_block_acceptance_scope`. Понижать `blocks_acceptance_scope` на
стороне J запрещено — поле вычисляется I24 механически. Предупреждение
`j_side_deferred_lifecycle_not_implemented` снято из `j_handoff_signal.yaml` и трактуется J0 как
исторический маркер, а не gate failure. Новые правила проверены симуляцией на опубликованном снапшоте
`SNAP-I-I-run-20260618-001-IMPL-20260826T131500Z`: 7/7 пройдено; у единственной отложенной задачи T-010
`blocks_acceptance_scope: false`, поэтому k_trigger не гейтится.

## 12. Architecture Plan как жанр — источник дрейфа

**Факт.** R17 уже признал системное отставание плана; это ревью снова нашло ~15 расхождений (см. §0), включая противоречащие канону схемы и битую нумерацию. Причина структурная: план дублирует схемы и алгоритмы, которые живут в промптах.

**Требование v-next.** План v-next — только: (а) карта слоёв/цепочек, (б) реестр канонических разделов («схема X живёт в файле Y»), (в) инварианты. Ни одной копии схемы. Плюс contract-тест, падающий при появлении в плане yaml-блока с `schema_version`, дублирующего файл-канон. Поле `quality_summary.test_coverage_avg` в §5.6 — пример «осиротевшей» метрики без производителя (ни один агент её не вычисляет) — удалить или назначить владельца (J10 aggregate).

## 13. Разное (зафиксировать решением, не срочно)

- **Filename-грамматика** (`[A-Za-z0-9][A-Za-z0-9._-]{0,127}`, запрет `:` для Windows, reserved names) описана в J13/J0 — вынести в общий раздел harness-доков; применить ко всем генерируемым именам (spike_attempts, attempt_history и т.д.).
- **J0-бандл запуска агентов** (гигантская иллюстративная строка с overlay-поправками) — v-next: канонический invocation-бандл каждого агента живёт в его файле; J0 хранит только ссылку. Случай `j12_attempt_number` (ложь в бандле + «ignore»-overlay сверху) показал, что «иллюстративный, но неверный» текст в J0 всё равно опасен.
- **Research-шаблон I21** (`allowed_use`, `expires_after`, `provenance.spike_id/open_question_id`, `budget.max_spike_retry_attempts`) — в текущем снапшоте research-задач нет, поля непроверяемы; I23-гейт на соответствие J0 Task Preflight обязателен до первого research_only прогона v-next.
- **`j_acceptance_index.yaml#validation_commands`** (command_hash/expected_hash) сейчас «infra_code only» — распространить на config/migration (J20/config_validation получили бы тот же durable staleness-якорь, что J14).
- **`observability_spec.yaml`/`coverage_matrix.yaml`/`assumptions.yaml`** входят в снапшот, но не имеют объявленного потребителя в J-промптах (observability используется только косвенно через J4 deployment plan `source_ref`) — v-next: либо явный вход (J12/J16 observability checks), либо перевести в `gate_evidence_artifacts`.
- **K-handoff**: инструкция k_trigger дублируется в двух местах J0 + план §5.6 — оставить одно каноническое место (J0 Layer Finalization), план — ссылкой.
