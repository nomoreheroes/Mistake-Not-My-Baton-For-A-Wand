# Ремонт покрытия presentation-слоя — план ре-рана I-слоя

**Дата:** 2026-08-24
**Статус:** ✅ ВЫПОЛНЕНО 2026-08-24 (I20→I21→I22→I23→I24 прогнаны; J сброшен на snapshot v2)
**Дефект:** прогон `I-run-20260618-001` дал 495 задач и **ноль** задач `code.presentation` / `execution.chain: ui_code` при полностью специфицированном Elm-фронтенде. Визуальная приёмка продукта (J13 HITL UI) структурно недостижима.

---

## 1. Что уже сделано (промпты)

Патчи внесены и проверены (28/28 якорных проверок, тесты J-слоя 69/69 зелёные). Новый прогон **физически не может** повторить дефект: он остановится на трёх независимых гейтах.

| Файл | Что изменено |
|---|---|
| `I20. Task Tree Builder.md` | Входы: `h10_elm_view_spec.yaml` + `component_mapping_*.yaml` (обязательные). Новая секция Шага 1 «Surface inventory» — самостоятельный класс coverage-целей, **не производный** от компонентов архитектуры. `target_type: presentation_surface` (`blocking: true` всегда) в `coverage_map`. Правило типовой совместимости покрытия (`implementation_task_refs`/`audit_task_refs`, запрет qa-only покрытия). Правило (c) `explicitly_not_applicable` дополнено маршрутизацией frontend-only констрейнтов в implementation-покрытие. Блок `surface_inventory` в схеме `task_tree.yaml` + `presentation_tasks`/`surfaces_total`/`surfaces_covered_by_tasks` в `topology`. Инварианты **15** (surface inventory обязателен и покрыт) и **16** (покрытие типово совместимо). |
| `I23. Task Graph QA.md` | Входы: те же два UI-источника. Секции **5k** (`surface_to_task` — независимый пересчёт инвентаря, gate failure при непокрытой поверхности), **5k-bis** (`chain_mix_sanity` — UI-рантайм есть, задач `code.presentation`/`ui_code` ноль → blocking), **5k-ter** (`coverage_type_compatibility` — qa-задача не может быть implementation-покрытием). Три новых флага `completeness_check`. `expected_count(5k)` в anti-empty gate 5j. Правило `applies_to` в Шаге 5g. Четыре строки self-audit. |
| `I21. Task Spec Agent.md` | Guard: при существующих UI-источниках и нуле presentation-задач **не пишет ни одной spec**, возвращает управление I20 (`next_prompt_signal`, `signal_type: i21_presentation_coverage_gap`). Обязательные human-visible acceptance checks с маркером `[human_ui]` для `code.presentation` + обязательный `artifact_ref` на первоисточник поверхности. `partial_test_contract_allowed` — обязательное поле каждой полной non-research spec (закрывает вторую критичную находку — livelock). Пример spec `chain: ui_code`. Инварианты **13**, **14**, **15**. |
| `I6. Architecture Synthesis.md` | Секция `h_layer_constraint_treatment` описана в промпте (раньше существовала только в артефакте). Поле `applies_to: architecture_conformance_only \| architecture_and_implementation`, дефолт — первое. Явно: «не применимо к архитектуре» ≠ «не нужно реализовывать». |
| `I17. Trade-off HITL.md` | Вариант [A] с решением `explicitly_not_applicable` требует **отдельного** вопроса человеку `[A-scope]`: исключается только из архитектурной конформности или из реализации тоже. `constraint_treatment` в ADR (`applies_to`, `implementation_owner`, `exemption_reason`). Инвариант scope + self-audit. |

---

## 2. Фактический инвентарь поверхностей (посчитан из артефактов)

Источник H10 (`h10_elm_view_spec.yaml`, `page_view_specs[]`) — 11 модулей, **70** объявленных `state_views`:

| surface_id | module | state_views |
|---|---|---:|
| schedule_view | page_schedule_view | 9 |
| schedule_review_screen | page_schedule_review_screen | 9 |
| chat_interface | page_chat_interface | 9 |
| onboarding_flow | page_onboarding_flow | 8 |
| balance_setup | page_balance_setup | 8 |
| planning_constraints | page_planning_constraints | 7 |
| analytics_screen | page_analytics | 7 |
| settings_screen | page_settings | 6 |
| upgrade_screen | page_upgrade | 6 |
| (layout) | layout_app_shell | 0 |
| (null) | page_not_found | 1 |

Источник G (`component_mapping_*.yaml`) — 9 файлов: analytics_screen, balance_setup, chat_interface, onboarding_flow, planning_constraints, schedule_review_screen, schedule_view, settings_screen, upgrade_screen.

**Пересечение по `surface_id` полное** для 9 поверхностей; `layout_app_shell` и `page_not_found` есть только в H10 (у них нет G component_mapping). По патчу I20 это `granularity_gap` с `required_owner: H10` — либо человек подтверждает, что shell/404 не требуют отдельной G-поверхности (тогда они всё равно получают presentation-units из H10), либо H-слой добирает mapping. **Решить это до запуска I20** — это единственный вход, требующий человеческого решения заранее.

**Ожидаемый объём:** ~11 поверхностей → presentation-units по состояниям/флоу. Верхняя граница — 70 состояний, но по правилу минимальности I20 состояния одной поверхности с общим постусловием склеиваются. Реалистичная оценка: **35–70 новых задач `code.presentation`**. Новые ID продолжат нумерацию (`T-496`…), существующие `T-001`…`T-495` **не перенумеровываются** (инвариант 13 I20 — детерминированный порядок; добавление новых units не сдвигает уже назначенные ID при partial rerun).

---

## 3. Порядок ре-рана

Каждый шаг — отдельная сессия с полным текстом соответствующего промпта. Механика partial-rerun уже обкатана (`run_context`, `i23_upstream_return_signal`).

### Шаг 1 — I20 (partial rerun)

`run_context: partial_rerun_from_i23_task_graph_qa` не подходит (сигнала от I23 нет). Использовать **новый** контекст запуска — по факту это повторный `full_implementation` прогон с уже существующим деревом. Передать в контексте:

```yaml
rerun_reason: presentation_coverage_repair
rerun_scope: additive_only
preserve:
  - существующие decomposition_units[] и tasks[] T-001..T-495 не изменяются:
    ни scope, ни acceptance hints, ни ID, ни depends_on между ними
  - существующий coverage_map сохраняется; строки дополняются полями
    implementation_task_refs/audit_task_refs по новому правилу типовой совместимости
add:
  - surface_inventory[] из h10_elm_view_spec.yaml + component_mapping_*.yaml
  - presentation_surface units и задачи code.presentation для каждой поверхности
  - depends_on новых задач на существующие (данные/контракты, от которых зависит surface)
fix:
  - строки prd_coverage с UI-стори: implementation_task_refs перепривязать
    с агрегированной QA T-495 на реальные presentation-задачи;
    T-495 остаётся только в audit_task_refs
  - frontend-only H12/H14 констрейнты (ADR-I17-007/008) отнести к поверхностям
    как h_constraint_refs (см. правило (c), applies_to: architecture_conformance_only)
```

**Предусловие:** решить вопрос `layout_app_shell`/`page_not_found` (см. §2).

**Ожидаемый результат:** `task_tree.yaml` с непустым `surface_inventory`, `topology.presentation_tasks > 0`, `completion_status: completed`.

### Шаг 2 — I6 (микро-патч, опционально, но правильно)

Дописать `applies_to: architecture_conformance_only` в 19 существующих записей `system_architecture.final.yaml#h_layer_constraint_treatment.entries[]` (ADR-I17-007/008). Формально downstream читает отсутствие поля как этот же дефолт, так что шаг можно пропустить — но явное поле убирает неоднозначность при следующем аудите. Если делать — это patch run I6, меняющий только эту секцию; хеш `system_architecture.final.yaml` изменится, что потребует пересчёта во всех downstream input_hashes (I20 уже перезапускается, I23 тоже — потерь нет).

### Шаг 3 — I21 (только новые задачи)

Существующие `task_specs/T-001…T-495.yaml` **остаются байт-в-байт теми же** — критично для §4 (T-008 переживёт смену снапшота). I21 пишет спеки только для новых `T-496+`.

⚠️ Новое обязательное поле `partial_test_contract_allowed` формально требуется «в каждой полной non-research spec». Для уже существующих 495 спек это означало бы их перезапись (и смену `spec_hash` → инвалидацию `tasks.db` и текущего состояния T-008). **Решение:** в этом ре-ране применять новое правило только к новым спекам; существующие мигрировать при следующем полном прогоне I21. Зафиксировать это как явное исключение в `run_events/I21-*.yaml#migration_note`, чтобы I23 не счёл отсутствие поля у старых спек дефектом (проверка I23 на это поле пока не введена — намеренно, см. §5).

### Шаг 4 — I22 (HITL, человек)

Delta-ревью: смотреть **только** новые presentation-задачи и изменённые строки покрытия. Обязательно попросить у I22 сводку по классам (распределение задач по `task_type` × `execution_chain` × поверхности) — именно её отсутствие позволило пропустить дефект в прошлый раз на дереве из 495 узлов.

### Шаг 5 — I23 (full QA)

Полный прогон. Новые секции 5k/5k-bis/5k-ter должны пройти. Ожидаемая новая `coverage_matrix.yaml`: `prd_coverage` UI-стори перепривязаны, `surface_to_task` заполнена, три новых флага `completeness_check: true`.

### Шаг 6 — I24 (publish)

Публикует `frozen_snapshot.yaml` v2 + `tasks.db` v2 + новый `j_handoff_signal.yaml`. **Дополнительно рекомендуется** (находка §3 ревью J): включить `technology_decisions.yaml` в `included_artifacts` — он читается J4/J9, но сейчас вне контроля целостности снапшота.

---

## 4. Сброс J-слоя на snapshot v2

Текущее состояние J: `status: waiting_for_external`, активна `T-008` (`external_manual`, настройка GCP-консоли), кода нет, веток/PR нет, RES-001/RES-002 уже архивированы supersession-процедурой 2026-08-21.

Процедуры «смена implementation-снапшота посреди прогона» у J0 нет (Snapshot Supersession Recovery определён только для terminal research-состояний — отдельная находка для v-next). Ручной сброс по уже применённому в этом проекте паттерну:

1. Заархивировать текущее состояние: `_archive/T-008_snapshot_v1_<timestamp>/` ← копии `j_layer_status.yaml`, `j_runtime.db`.
2. `j_layer_status.yaml`: `status: idle`, `active_task_ids: []`, `current_task_id: null`, `waiting.kind: null`, блок `snapshot` — хеши v2.
3. Запустить J0 — Snapshot Gate провалидирует v2 штатно (включая новую формулу агрегатного хеша `task_specs/`, уточнённую в патче J0 от 2026-08-21).

**T-008 переживает смену снапшота бесплатно:** её spec не зависит от UI-задач и в v2 будет байт-идентичен → `tasks.db#spec_hash` совпадёт → Task Preflight Шаг 0 пройдёт → директория `T-008/` с шаблоном (и заполненным `human_action_result.yaml`, если человек уже выполнил действие в GCP) остаётся валидной; J22 продолжит с `validate_result`.

**Порядок исполнения задач в v2** изменится: presentation-задачи получат свои `batch_order`, и первой eligible задачей может стать не T-008. Это нормально; T-008 не блокируется.

---

## 5. Что осознанно НЕ сделано в этом патче

- **I23 не проверяет `partial_test_contract_allowed`** у существующих спек — иначе ре-ран сразу упрётся в 495 legacy-файлов. Ввести проверку при следующем полном прогоне I21, когда все спеки будут переписаны.
- **Автоматическая миграция 495 существующих спек** — не делается: перезапись меняет `spec_hash` и инвалидирует текущее состояние J (T-008). Мигрировать полным прогоном I21, когда это будет безопасно.
- **Правило назначения `ui_code` в I21 не менялось** — оно корректно; дефект был выше по потоку (I20 не создал presentation-задач вовсе).
- **Остальные находки ревью J-слоя** (Approval Gate throughput, монолитный `j_layer_run.yaml`, неоднородный envelope, budget escalation contract и др.) — в `J. Implementation/J Layer - Deep Findings And V-Next Requirements.md`, не входят в этот ремонт.

---

## 6. Фактический результат прогона (2026-08-24)

| Шаг | Результат |
|---|---|
| I20 | `surface_inventory` 11 поверхностей; 60 units/задач `code.presentation` (T-496..T-555) + T-556 (bootstrap Elm-тулчейна, chain `config`); 12 `presentation_surface` coverage-целей; все 314 строк `prd_coverage` перепривязаны (qa убраны из `implementation_task_refs`); T-001..T-495 не изменены (0 diff) |
| I21 | 61 спека; каждая presentation-спека несёт ≥1 `[human_ui]` acceptance check, `manual_check_required: true`, `partial_test_contract_allowed`; `validation_commands: []` осознанно (Elm-тулчейн не подтверждён ни одним допустимым источником — отсюда T-556) |
| I22 | ITER-007, `sign_off: confirmed`; два решения человека: shell/404 без G-макета — `acknowledged`; 8 строк operator-story — `acknowledged` как audit-only. **Bulk-acknowledge не использован** |
| I23 | `status: passed`; новые секции 5k/5k-bis/5k-ter — все зелёные, 0 gate failures; 11/11 поверхностей покрыты; 0 нарушений типовой совместимости (было 314) |
| I24 | `SNAP-I-I-run-20260618-001-IMPL-20260824T130000Z`; tasks.db 556 задач; `included_artifacts` 17 (добавлены `technology_decisions.yaml` и 5 H-спек клиента) |
| J | `j_layer_status.yaml` → `idle` на v2; прежнее состояние в `_archive/snapshot_v1_supersession_20260824T131500Z/`; **T-008 spec_hash идентичен** — задача продолжается без потери |

**Распределение по chain после ремонта:** client_code 203, integration 130, server_code 87, **ui_code 60**, config 30, infra_code 20, qa 14, migration 7, external_manual 5.

## 7. Критерии приёмки ремонта

- [ ] `task_tree.yaml#surface_inventory.surfaces` — 11 записей (или явное решение по shell/404)
- [ ] `task_tree.yaml#topology.presentation_tasks` > 0; `surfaces_covered_by_tasks == surfaces_total`
- [ ] Каждая новая spec `task_type: code.presentation` имеет `execution.chain: ui_code`, ≥1 acceptance check с `[human_ui]`, `manual_check_required: true`, `artifact_ref` на h10/component_mapping
- [ ] `coverage_matrix.yaml#surface_to_task` заполнена, все `covered: true`
- [ ] `completeness_check.no_surface_without_presentation_task`, `.no_ui_runtime_without_presentation_tasks`, `.no_qa_task_as_implementation_coverage` — все `true`
- [ ] UI-стори PRD (`US-onboarding-01` и др.) имеют `implementation_task_refs` на presentation-задачи, T-495 — только в `audit_task_refs`
- [ ] `task_specs/T-001…T-495.yaml` не изменились (побайтово)
- [ ] J-слой стартует на v2, T-008 продолжается без потери состояния
- [ ] Первая presentation-задача, дойдя до J10, даёт `pending_downstream`/`downstream_owner: J13` — т.е. HITL-приёмка UI реально включилась
