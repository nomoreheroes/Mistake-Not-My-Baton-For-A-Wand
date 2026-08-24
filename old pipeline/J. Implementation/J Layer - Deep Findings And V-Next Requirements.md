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

## 10. Контрактная диета task_spec: мёртвые поля и дубли

**Факт (по фактическим спекам).** Поля без единого потребителя в J: `destructive`, `requires_human_review`, `risk_level`, `mitigation_plan`, `parallel_group`, `sequence_order`, `status_at_spec_time`, `batch_id` (J использует только `execution.batch_order`), `component_id` (дублируется в tasks.db). `data_loss_risk` существует **дважды** (top-level и `provenance.data_loss_risk`) — J0 preflight читает top-level, второй экземпляр — потенциальный источник расхождения. `manual_check_required/description` читает только J22 и только как прозу.

**Требование v-next.** I21: либо назначить потребителя каждому полю (например `requires_human_review: true` → обязательный HITL-шаг в chain — сейчас это молча игнорируется!), либо удалить из схемы. `data_loss_risk` — ровно одно каноническое место. Особо: `requires_human_review: true` стоит на T-008..T-012 и ни на что не влияет — это семантическая потеря сигнала I-слоя.

## 11. `deferred` в tasks.db не имеет жизненного цикла в J

**Факт.** CHECK-констрейнт допускает `ready|deferred`; J (после локальной правки) корректно исключает не-ready задачи, но нигде не определено: кто, когда и как переводит `deferred → ready` (I-слой? новый снапшот? вручную?), как J отражает наличие deferred-задач в `j_layer_summary` (сейчас Layer Finalization их не упоминает — слой может завершиться «complete», молча не выполнив deferred).

**Требование v-next.** Определить в I24: deferred-задачи меняют статус только новой публикацией снапшота; J0 Layer Finalization обязан перечислять их в summary отдельным списком и не выставлять `ready_for_human_k_trigger: true`, если deferred-задачи блокируют acceptance-scope продукта.

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
