# H Layer — Architecture Plan

**Дата:** 2026-06-04
**Статус:** ACTIVE

---

## 1. Назначение слоя

H-слой получает G-layer handoff (визуальный дизайн, компонентная система, трассируемость, доступность) и производит полную **спецификацию Elm-архитектуры** — не compilable код, а архитектурные решения по модулям, типам, update-логике и view-функциям. Выход H-слоя (`h_layer_handoff`) потребляется I-слоем (I1, I3, I6).

```
G14/G15 handoff → H1–H15 → h_layer_handoff → I-слой
```

---

## 2. Ростер агентов (15 агентов)

```
H1   Traceability Index Builder        [нормализует trace links из G-handoff]
H2   Traceability QA                   [аудит H1 индекса]
─────────────────────────────────────────────────────────────────────
H3   Elm Module Architect              [модули, routing, Elm package decisions ← ОБНОВЛЁН]
H4   Elm Module QA                     [аудит H3]
─────────────────────────────────────────────────────────────────────
H5   Elm State & Type Architect        [Model, Msg taxonomy, ownership]
H6   Elm State & Type QA              [аудит H5]
─────────────────────────────────────────────────────────────────────
H7   Elm Update Architect              [update ветки, effects, recovery]
H8   Elm Update QA                     [аудит H7]
─────────────────────────────────────────────────────────────────────
H9   Elm Contract Spec                 [port payload schemas + API error contracts ← НОВЫЙ]
─────────────────────────────────────────────────────────────────────
H10  Elm View Architect                [view функции, component usage]
H11  Elm View QA                       [аудит H10]
─────────────────────────────────────────────────────────────────────
H12  Elm Architecture Integrator       [кросс-слойная консистентность]
H13  Elm Architecture QA              [аудит H12]
H14  Elm Architecture HITL             [owner review, режимы A/B]
H15  Elm Architecture Gatekeeper       [exit gate → h_layer_handoff ← ОБНОВЛЁН]
```

---

## 3. Текущие проблемы и план исправлений

### 3.1 Категория 1 — Сломанное (исправить немедленно)

#### H1: `g14_qa_report.yaml` не существует

**Проблема:** H1 ожидает `g14_qa_report.yaml` от "G14" как soft input. В старом G-пайплайне G14 был отдельным агентом с QA-шагом. В новом G14 = H Layer Package Generator — отдельного QA для G14 нет. Файл никогда не создаётся.

**Симптом:** H1 всегда работает с `status: complete_with_gaps` без реальной причины.

**Действие:** Удалить строку `g14_qa_report.yaml` из таблицы входных артефактов H1.

---

### 3.2 Категория 2 — Устаревшие source-ссылки (обновить перед запуском)

В 6 промптах колонка "Источник" ссылается на старые номера G-агентов. Имена файлов правильные, но атрибуция вводит в заблуждение.

**H1** — исправить 8 строк:

| Артефакт | Написано | Правильно |
|---|---|---|
| `screen_blueprints.yaml` | G9 | G14 |
| `g21_gate_report.yaml` | G21 | G15 |
| `g13_pm_traceability_report.yaml` | G13 | G14 (gate), G15 (owner review) |
| `g12_accessibility_report.yaml` | G15 | G12 |
| `g12_composition_report.yaml` | G12 | G14 + G15 |
| `component_system.yaml` | G3 | G14 |
| `generated_assets.yaml` | G6 | G4 |
| `asset_strategy.yaml` | G5 | G3 |

**H2** — исправить 4 строки:

| Артефакт | Написано | Правильно |
|---|---|---|
| `screen_blueprints.yaml` | G9 | G14 |
| `g21_gate_report.yaml` | G21 | G15 |
| `component_system.yaml` | G3 | G14 |
| `generated_assets.yaml` | G6 | G4 |

**H3** — исправить 2 строки:

| Артефакт | Написано | Правильно |
|---|---|---|
| `screen_blueprints.yaml` | G9 | G14 |
| `g21_gate_report.yaml` | G21 | G15 |

**H5** — исправить 1 строку:

| Артефакт | Написано | Правильно |
|---|---|---|
| `screen_blueprints.yaml` | G9 | G14 |

**H7** — исправить 1 строку:

| Артефакт | Написано | Правильно |
|---|---|---|
| `screen_blueprints.yaml` | G9 | G14 |

**H9** — исправить 2 строки:

| Артефакт | Написано | Правильно |
|---|---|---|
| `screen_blueprints.yaml` | G9 | G14 |
| `component_system.yaml` | G3 | G14 |

---

### 3.3 Категория 3 — Структурные добавления

#### A. Elm Technical Context в H3 (новый ЭТАП 0)

**Проблема:** H3–H9 проектируют Elm-архитектуру, не зафиксировав на каких библиотеках она строится. J-слой при написании кода делает ad-hoc выборы, которые могут расходиться со спецификацией.

**Почему не отдельный агент:** Elm-экосистема мала и стандартизирована. UI-компонентная библиотека уже решена (r10). Открытых вопросов три, не двадцать — полноценный researcher избыточен.

**Решение:** Добавить ЭТАП 0 в H3, новый input `interaction_spec.yaml`, расширить выходной артефакт.

##### Новый input для H3

```
| `interaction_spec.yaml` | F4 | Порты и JS-interop сигналы (LocalStorage, уведомления, внешние API) |
```

##### ЭТАП 0 — Elm Technical Context (вставить перед текущим ЭТАП 1 в H3)

H3 перед проектированием модулей фиксирует Elm-пакетные решения.

**Закрытые домены (решения приняты, не исследовать):**

| Домен | Решение |
|---|---|
| UI-компоненты | r10 (зафиксировано G14 через `DOCUMENTATION.yaml`) |
| HTTP | elm/http — стандарт, альтернатив нет |
| JSON | elm/json — стандарт |
| Тестирование | elm-test — стандарт |

**Открытые домены (H3 принимает решение):**

1. **Routing** — прочитать `h1_traceability_index.surface_index` (количество surfaces, наличие multi-step journeys) → выбрать один вариант:
   - `elm/url` + custom parser — для ≤8 поверхностей без сложной вложенности
   - `elm-spa` — для ≥9 поверхностей или сложной вложенной маршрутизации
   - Обоснование зафиксировать в `routing_decision_rationale`

2. **Ports strategy** — прочитать `interaction_spec.yaml` → для каждого JS-interop паттерна определить:
   - Нужен ли port или достаточно elm/http
   - Направление: outgoing (Elm → JS) или incoming (JS → Elm)
   - Список: LocalStorage, Push Notifications, Browser APIs, внешние виджеты

3. **Animation** — прочитать `design_system_reference.yaml` (INV-09: motion off by default) → вывод: elm-animator исключён; допустимы CSS transitions только для aha_moment_overlay. Зафиксировать как explicit exclusion.

**Формат вывода (добавить в `h3_elm_module_spec.yaml`):**

```yaml
elm_packages_assumed:
  closed_domains:
    - package: r10
      role: ui_components
      version_source: DOCUMENTATION.yaml
      decision: fixed_upstream
    - package: elm/http
      role: http_requests
      decision: standard_no_alternative
    - package: elm/json
      role: json_encoding_decoding
      decision: standard_no_alternative
    - package: elm-test
      role: testing
      decision: standard_no_alternative

  routing:
    chosen: elm/url | elm-spa
    routing_decision_rationale: <1-2 предложения>
    surface_count: <int>
    multi_step_journey_count: <int>

  ports:
    - port_id: <string>
      direction: outgoing | incoming | bidirectional
      purpose: <string>
      triggers: []        # Msg variants или JS events
      js_side_owner: <string>

  animation:
    elm_animator: excluded
    exclusion_rationale: "INV-09: motion off by default"
    css_transitions_allowed:
      - surface_id: aha_moment_overlay
        scope: hero_illustration_only

  additional_packages:
    # Любые пакеты не попавшие в выше — с обоснованием
    - package: <string>
      version_constraint: <string>
      role: <string>
      decision_rationale: <string>
```

##### Изменения в H5, H7, H9

Добавить в таблицу входных артефактов каждого:

```
| `h3_elm_module_spec.yaml` | H3 | ... + elm_packages_assumed — frozen context |
```

Добавить в правила интерпретации: "elm_packages_assumed из H3 — frozen. Если при проектировании обнаружена несовместимость с выбранным пакетом — фиксировать как `package_conflict`, не менять решение самостоятельно."

---

#### B. Расширение `h_layer_handoff` в H14

**Проблема:** I1, I3, I6 читают `h_layer_handoff` для конкретных целей, но текущая структура — пакет ссылок на файлы + сводка HITL-решений. I-агенты вынуждены читать все H-артефакты напрямую, что нарушает принцип self-contained handoff.

**Решение:** Добавить три секции к существующей `h_layer_handoff` схеме в H14.

```yaml
h_layer_handoff:
  # ... существующие секции без изменений ...

  # НОВАЯ СЕКЦИЯ 1 — для I1 (Technology Researcher: hard constraints)
  ui_hard_constraints:
    description: >
      Решения frontend-уровня которые backend не может нарушить.
      I1 использует как hard_constraint в domain_dependencies.
    constraints:
      - constraint_id: <string>
        constraint_type: api_contract | state_ownership | routing_model | port_interface
        description: <что зафиксировано — 1 предложение>
        source_artifact: h3 | h5 | h7 | h9
        source_section: <конкретная секция>
        backend_implication: <что это означает для backend — 1 предложение>

  # НОВАЯ СЕКЦИЯ 2 — для I3 (Process & Causality Map)
  frontend_process_model:
    description: >
      Действия пользователя из UI которые инициируют серверные процессы.
      I3 использует как входной сигнал при построении causality map.
    actions:
      - action_id: <string>
        surface_id: <string>
        msg_variant: <Elm Msg — из H5>
        action_type: command | event
        # command = ждёт sync-ответа от backend
        # event = достаточно факта; async
        description: <что делает пользователь>
        expected_backend_response: sync | async | none
        latency_sensitivity: high | medium | low

  # НОВАЯ СЕКЦИЯ 3 — для I6 (Architecture Synthesis)
  frozen_api_surface:
    description: >
      API-форма которую frontend уже предполагает.
      I6 учитывает при проектировании компонентов и контрактов.
    endpoints:
      - endpoint_hint: <REST path или GraphQL operation hint>
        initiating_action: <action_id из frontend_process_model>
        data_shape_sketch:
          request_fields: []   # ключевые поля, не полная схема
          response_fields: []
        latency_expectation: low | medium | high
        auth_required: true | false

  # НОВАЯ СЕКЦИЯ 4 — Elm package decisions (агрегировано из H3)
  elm_packages_decided:
    routing: <chosen — из h3_elm_module_spec.elm_packages_assumed.routing.chosen>
    ports: []  # копия из h3_elm_module_spec.elm_packages_assumed.ports
    animation_policy: <из h3_elm_module_spec.elm_packages_assumed.animation>
    additional_packages: []
    # r10, elm/http, elm/json, elm-test не перечислены — стандарт
```

**Откуда H14 берёт данные для новых секций:**

| Секция | Источник в H14 inputs |
|---|---|
| `ui_hard_constraints` | `h11_integration_spec.yaml` → `integration_concerns` с `route_to: I_layer` + H5 state ownership decisions |
| `frontend_process_model` | `h7_elm_update_spec.yaml` → update branches с HTTP/port effects + `navigation_map.yaml` |
| `frozen_api_surface` | `h7_elm_update_spec.yaml` → HTTP commands с URL hints + `screen_blueprints.yaml` |
| `elm_packages_decided` | `h3_elm_module_spec.yaml` → `elm_packages_assumed` (прямая копия) |

H14 **агрегирует**, не изобретает. Вся информация уже есть в H-слое — нужно только структурировать её для I-агентов.

---

### 3.4 Новый агент H9 — Elm Contract Spec

**Место в пайплайне:** после H8 (Update QA), до H10 (View Architect).

**Тип агента:** синтезатор, не архитектор. Собственного QA-агента не требует — синтезирует уже верифицированные H7/H8 данные. Ошибки синтеза выявляет H13 (Architecture QA).

**Зачем:** H10–H15 проектируют view и интеграцию не зная точной формы payload портов и стратегии обработки ошибок API. I-слой не может спроектировать JS-обёртку и backend error model без этих контрактов.

**Входные артефакты:**

| Артефакт | Источник | Назначение |
|---|---|---|
| `h3_elm_module_spec.yaml` | H3 | Список портов (port_id, direction) |
| `h5_elm_state_type_spec.yaml` | H5 | Типы данных для payload inference |
| `h7_elm_update_spec.yaml` | H7 | Effects, error patterns per branch |
| `h8_elm_update_qa_report.yaml` | H8 | Proceed flag — H9 не запускается если H8 failed |
| `prd.index.yaml` | D7 | Бизнес-ошибки из acceptance criteria |

**Выходной артефакт:** `h9_contract_spec.yaml`

Две секции:
- `port_contracts` — payload schema для каждого порта (fields, types, typescript_hint)
- `error_handling_contracts` — per-endpoint: стратегия (`granular_codes | generic_fallback | mixed`), список parseable error codes (если известны из PRD), generic fallback behavior

**Потребители:**
- H10 (View Architect) — context для error display zones
- H12 (Integration) — cross-layer context
- H15 (Gatekeeper) — включает в `h_layer_handoff` для I-слоя

---

## 4. Карта артефактов

### Входные артефакты H-слоя (от G и F)

| Артефакт | Производитель | Потребители H |
|---|---|---|
| `screen_blueprints.yaml` | **G14** | H1, H2, H3, H5, H7, H10, H15 |
| `component_system.yaml` | **G14** | H1, H2, H10 |
| `g21_gate_report.yaml` | **G15** | H1, H2, H3 |
| `g13_pm_traceability_report.yaml` | **G13** | G14 (gate), G15 (owner review) |
| `g12_accessibility_report.yaml` | **G12** | H1 |
| `g12_composition_report.yaml` | **G14** + G15 patch | H1 |
| `generated_assets.yaml` | **G4** | H1, H2 |
| `asset_strategy.yaml` | **G3** | H1 |
| `surface_map.yaml` | F1 | H1, H2, H3, H10 |
| `navigation_map.yaml` | F2 | H1, H2, H3, H7, H10, H15 |
| `interaction_spec.yaml` | F4 | **H3** (новый) |
| `prd.index.yaml` | D7 | H1, H5, H7, **H9**, H12, H14 |

### Внутренние артефакты H-слоя

```
H1  → h1_traceability_index.yaml
H2  → h2_traceability_qa_report.yaml
H3  → h3_elm_module_spec.yaml          ← теперь содержит elm_packages_assumed
H4  → h4_elm_module_qa_report.yaml
H5  → h5_elm_state_type_spec.yaml
H6  → h6_elm_state_type_qa_report.yaml
H7  → h7_elm_update_spec.yaml
H8  → h8_elm_update_qa_report.yaml
H9  → h9_contract_spec.yaml            ← НОВЫЙ: port payload schemas + error contracts
H10 → h10_elm_view_spec.yaml
H11 → h11_elm_view_qa_report.yaml
H12 → h12_integration_spec.yaml
H13 → h13_elm_architecture_qa_report.yaml
H14 → h14_hitl_decision_log.yaml
H15 → h15_gate_decision.yaml
     h_layer_handoff.yaml              ← расширен 4 новыми секциями + contract_spec
```

### Поток `elm_packages_assumed`

```
H3 (производит) → h3_elm_module_spec.elm_packages_assumed
                → H5 (frozen context)
                → H7 (frozen context)
                → H9 (port schema context)
                → H10 (frozen context)
                → H12 (через H3/H5/H7/H10 inputs)
                → H15 (агрегирует → elm_packages_decided в handoff)
```

### Поток `h9_contract_spec`

```
H9 (производит) → h9_contract_spec.yaml
                → H10 (View Architect — context для error display)
                → H12 (Integration — context для cross-layer decisions)
                → H15 (Gatekeeper — включает в h_layer_handoff)
```

---

## 5. HITL-точки

| # | Агент | Что делает владелец | Режим |
|---|---|---|---|
| 1 | **H14** | Финальный review Elm-архитектуры; решает отложенные вопросы; может отклонить в H12 | Mode A (присутствует) / Mode B (авто для non-blocking) |

H-слой имеет только одну HITL-точку — это сознательное решение. Технические архитектурные вопросы (module boundaries, type ownership, update semantics) разрешаются агентами H3–H12 без прерывания. Владелец включается только в H14, получая понятный briefing без Elm-специфики.

---

## 6. Порядок работ (приоритизированный)

### Шаг 1 — Исправления (механические, сделать сразу)

- [x] H1: удалить `g14_qa_report.yaml` из inputs
- [x] H1: исправить 8 source-ссылок
- [ ] H2: исправить 4 source-ссылки
- [ ] H3: исправить 2 source-ссылки
- [x] H5: исправить 1 source-ссылку
- [x] H6: исправить 1 source-ссылку (screen_blueprints.yaml G9→G14)
- [x] H7: исправить 1 source-ссылку
- [x] H9: исправить 2 source-ссылки

### Шаг 2 — Расширение H3 (новый контент)

- [ ] Добавить `interaction_spec.yaml` в inputs H3
- [ ] Написать ЭТАП 0 (Elm Technical Context) в H3
- [ ] Добавить `elm_packages_assumed` в схему выходного артефакта H3

### Шаг 3 — Прокидывание elm_packages_assumed (минорные изменения)

- [x] H5: добавить строку в inputs + правило интерпретации
- [x] H6: обновить H3 input description + добавить ЭТАП 7D (elm_packages_assumed compliance) + precondition check
- [x] H7: добавить строку в inputs + правило интерпретации
- [x] H9: добавить строку в inputs + правило интерпретации

### Шаг 4 — Расширение H15 handoff (новый контент) ✓ ВЫПОЛНЕНО (под старым именем H14)

- [x] Написать логику сборки `ui_hard_constraints` из H12 + H5
- [x] Написать логику сборки `frontend_process_model` из H7 + navigation_map
- [x] Написать логику сборки `frozen_api_surface` из H7 + screen_blueprints
- [x] Добавить `elm_packages_decided` (копия из H3)
- [x] Обновить validation checks H15 (проверять наличие новых секций)

### Шаг 5 — Новый агент H9 Contract Spec + перенумерация

- [x] Обновить Architecture Plan (ростер, карта артефактов, HITL-секция)
- [ ] Создать H9. ELM Contract Spec.md
- [ ] Переименовать файлы H9→H10 … H14→H15
- [ ] Обновить внутренние ссылки H8 (flags_for_h9→h10, flags_for_h11→h12)
- [ ] Обновить внутренние ссылки H10 (был H9)
- [ ] Обновить внутренние ссылки H11 (был H10)
- [ ] Обновить внутренние ссылки H12 (был H11) + добавить h9_contract_spec в inputs
- [ ] Обновить внутренние ссылки H13 (был H12)
- [ ] Обновить внутренние ссылки H14 (был H13)
- [ ] Обновить внутренние ссылки H15 (был H14) + добавить h9_contract_spec в inputs/handoff

---

## 7. Что НЕ меняется

- Функциональная логика H1–H8, H10–H15 (роли, алгоритмы, правила интерпретации) — без изменений
- Gate conditions H15 — без изменений (новые секции — дополнение, не замена)
- Количество HITL-точек: одна (H14, ex-H13)

---

*Написан 2026-06-04. Обновлён 2026-06-09: добавлен H9 Contract Spec, перенумерация H9→H10 … H14→H15.*
