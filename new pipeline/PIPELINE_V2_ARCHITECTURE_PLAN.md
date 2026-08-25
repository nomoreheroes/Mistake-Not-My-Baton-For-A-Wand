# Pipeline v2 — архитектурный план

**Версия:** 0.7  
**Дата:** 2026-08-25  
**Статус:** DRAFT / обновлено по результатам архитектурного ревью  
**Область:** общая архитектура пайплайна; детальные планы слоёв и тексты промптов появятся на следующих этапах

**Изменения 0.2:** Elm закреплён как стандарт для применимых UI-контуров, а не удалён из v2; восстановлены отдельные слои G (графическое решение) и H (Elm design-to-code architecture). G построен вокруг строгого разделения творческого рисования и формальной привязки к структуре проекта.

**Изменения 0.3:** учтено архитектурное ревью: возвращены engineering standards и scale/context policy, добавлены budget escalation, registry reachability/field-consumer checks, harness-track метаслоя, DB compatibility, prompt-injection/tool/egress controls, внешний worktree root, bounded A↔H loop, platform predecision, abort/HITL/interactive recovery, incremental Q, walking-skeleton и compiled fast-path однозначной маршрутизации. Уточнено хранение: все payload остаются внутри SQLite, адресация идёт по artifact version ID, hash служит атрибутом верификации, а multi-backend storage не входит в alpha. Спорной остаётся только замена/отсрочка пилота `swarm`.

**Изменения 0.4:** routing/fan-out/ownership/replay перенесены в machine-readable dispatcher contract; `permanent_gap` разделён на static terminal и release blocker; добавлена policy для неизвестных языков; этапы планирования и реализации чередуются по Alpha-срезам; fixture и полный pilot `swarm` получили разные test gates и readiness criteria.

**Изменения 0.5:** Elm определён как стандартный профиль для stateful interactive applications; целевой event catalog отделён от минимального Alpha-профиля; `swarm` закреплён как новый greenfield-продукт без наследования старого кода; добавлены co-evolution Pipeline/Swarm, раздельные product/pipeline rollback и evidence-based готовность слоя. Roadmap перестроен так, чтобы после kernel/nonvisual fixture провести Swarm через P/R/E, ранний G/H risk slice, A(final)/T, I и Q; полный M и расширенные rosters добавляются позже.

**Изменения 0.6:** legacy snapshot старого Swarm обязан быть физически вынесен из product root до baseline и доступен только как отдельный read-only research root; D0 получил симметричный product-tree hygiene gate. Layer Architecture Gate ограничен scope текущей фазы, complexity budget и двумя review-return rounds. Для провала V1 определён явный fallback ladder без обхода G/H quality gate. Elm applicability перенесён в machine-readable registry policy.

**Изменения 0.7:** Foundation разделён на K0-a bootstrap proof и K0-b operational hardening; первый доказывает один минимальный artifact/event cycle на fixture, второй gate-ит Alpha-0 recovery/safety. Добавлены `interaction_model_failure`, canonical SQLite architecture hypothesis register, ранний сбор raw telemetry без преждевременных KPI, явный Q-Alpha profile и центральный consumer-proof invariant. V2-D24/V2-D31 уточнены без расширения decision catalog.

---

## 1. Резюме решения

Pipeline v2 предлагается строить не как жёсткую последовательность промптов, а как **событийный граф работы**, управляемый двумя уровнями диспетчеров:

- `S0` — супердиспетчер проекта. Это единственная внешняя точка входа для команд человека. Он выбирает слой, запускает его локальный диспетчер как subagent либо применяет его заранее скомпилированный однозначный route, управляет глобальной очередью событий, межслойными возвратами, разрешениями и восстановлением после сбоев.
- `{Layer}0` — локальный диспетчер каждого слоя и владелец его routing policy. Он подписан на события своего слоя, выбирает нужные рабочие промпты, проверяет их входы и результаты, формирует новые события и возвращает межслойные события только `S0`. Однозначный nominal route может исполняться harness без отдельного LLM-вызова `{Layer}0`; любое смысловое решение или отклонение снова активирует диспетчер.
- Рабочие агенты не вызывают друг друга и не передают управление напрямую. Агент семантически инициирует событие, возвращая `event_proposal`; физически событие валидирует и атомарно записывает детерминированный harness по policy соответствующего диспетчера.

Для каждого проекта создаётся одна локальная SQLite-база. Она является каноническим хранилищем:

- всех рабочих артефактов и всех их версий;
- событий и истории их доставки подписчикам;
- запусков слоёв и агентов;
- решений, gate-результатов, approvals, findings, lineage и recovery-state.

В файлы проекта выводятся только ключевые решения. Каждое такое решение имеет две синхронные проекции с одинаковым именем: YAML для машинного чтения и Markdown для человека. Обе проекции генерируются из одной версии решения в SQLite и проверяются по hash.

Предлагаемый набор предметных слоёв:

```text
P — Project Context & Change Discovery
R — Requirements & Success Criteria
E — Experience, Adoption & UX Architecture         [условный по applicability]
G — Graphic & Visual Solution                       [условный; отдельный creative контур]
A — Solution Architecture, Data & Risk
H — Elm Design-to-Code Architecture                 [обязательный, где Elm применим]
T — Task Graph & Evidence Plan
I — Implementation & Verification
Q — Independent Audit, Documentation & Release
M — Meta / Pipeline Self-Healing                    [сквозной]
```

Нормальный UI-маршрут выглядит как `P → R → E → A0(platform predecision) → G → A(draft) → H → A(final) → T → I → Q`. Ранний вызов A0 не проектирует архитектуру целиком: он фиксирует только ограничения, без которых G рисовал бы для неизвестной платформы. Для невизуального проекта E/G/H могут быть облегчены или неприменимы. Это не жёсткая линейная цепочка: события могут запускать параллельные reviews, минимальный replay, возврат к владельцу данных или отдельную M-сессию. Пропуск слоя всегда оформляется проверяемым решением applicability, а не молчаливым отсутствием артефакта.

---

## 2. Что извлекается из старого пайплайна

Анализ охватил планы и промпты слоёв A–K и M, детальные контракты J0, J13/J14, план K0, метаслой M и контрактные тесты J. Локальный прогон `python -B -m pytest "old pipeline/J. Implementation/tests" -q -p no:cacheprovider` от 2026-08-24 завершился результатом `69 passed`; тот же baseline описан в `J Layer — Deep Findings And V-Next Requirements` от 2026-08-21. Это подтверждает, что в старом пайплайне есть сильное контрактное ядро, но часть глобальных допущений слишком узка для новых типов проектов, а runtime-модель чрезмерно зависит от файлов.

Самый важный практический вывод старого G-слоя принимается как системный факт: творческая генерация и формальная привязка конкурируют за cognitive budget LLM. Когда visual agent одновременно обязан рисовать, назначать component IDs, закрывать coverage и строить traceability, он обычно производит формально полный wireframe вместо сильного графического решения. Когда он только рисует, качество выше, но связь с проектом теряется. Поэтому v2 не ищет «более сильный единый prompt», а архитектурно разводит эти задачи между независимыми контекстами и соединяет их только на отдельной mapping-фазе с HITL.

### 2.1 Сохраняем как базовые принципы

| Идея старого пайплайна | Решение для v2 |
|---|---|
| Диспетчерская модель J0/K0 | Распространить на каждый слой и добавить `S0` над локальными диспетчерами |
| Один writer на артефакт | Сохранить; downstream создаёт finding/revision event, но не правит upstream-данные |
| Immutable generation, hashes, pinned inputs | Сохранить и унифицировать общим invocation envelope и SQLite lineage |
| Gate/barrier перед публикацией | Сохранить; машинный gate бинарный, human authorization хранится отдельно |
| Возврат к самому раннему владельцу дефектных данных | Сохранить как graph-based invalidation и minimal replay |
| Разделение `task_type` и `execution_chain` | Сохранить как `work_type` и `execution_recipe` |
| Acceptance evidence обязательно для completion | Сохранить для всех реализационных задач |
| Изолированные git worktree, checkpoints, безопасный rollback | Сохранить; реализовать harness-командами, не длинными инструкциями в промптах |
| Независимый аудит K, не доверяющий самоотчёту I/J | Сохранить в Q: реконструкция as-built состояния из primary sources |
| M: prompt-defect taxonomy, red→green, Tier 0/1/2 tests | Сохранить и встроить через события и обязательный HITL |
| Claim classes из E | Расширить на весь пайплайн: факт, решение человека, наблюдение, research, derived, assumption |
| Явный `SKIP_NOT_APPLICABLE` receipt | Сохранить как универсальное applicability-событие |
| Secret hygiene для external manual | Распространить на все слои и все артефакты |

### 2.2 Переделываем

| Проблема v1 | Решение v2 |
|---|---|
| Жёсткая ориентация на commercial MVP | Project profile и адаптивные маршруты для bugfix, feature, internal software, utility и greenfield product |
| Обязательность Elm там, где UI-технология неприменима | Elm сохраняется как стандарт и отдельный H-слой для применимых UI-контуров; backend/CLI/non-Elm legacy получают явное applicability/exception decision |
| Прямая передача управления и локальные ad-hoc return-файлы | Только versioned events и подписки; межслойный return всегда получает `S0`, внутрислойный — `{Layer}0` |
| Сотни YAML-файлов как рабочее состояние | SQLite — canonical store; файловые YAML+MD только для ключевых решений |
| Монолитные mutable state-файлы J0 | Малые агрегаты состояния в БД, CAS, leases и append-only transition history |
| Разные envelope/fencing правила для разных агентов | Один uniform invocation/result envelope для каждого физического вызова |
| Approval gate перед каждым subagent | Risk-tiered autonomy: автоматические безопасные шаги, batch consent для ограниченных изменений, точечный HITL для высокорисковых действий |
| Архитектурные планы копируют схемы из промптов | План хранит границы и инварианты; схемы имеют один канонический файл в registry |
| Наличие `latest`/mtime как способ выбрать артефакт | Только artifact version ID, event causation и content hash |
| QA-задача могла ошибочно «покрыть» implementation/UI story | Типизированные coverage edges; evidence несовместимого типа не закрывает цель |
| Harness-примитивы описаны естественным языком | Atomic write, CAS, lease, hashing, Git guards и publication transaction становятся исполняемыми библиотечными операциями |

### 2.3 Не переносим

- обязательный market/marketing review для любой задачи;
- обязательную полную разработку design system для CLI или небольшой невизуальной утилиты;
- фиксированный roster из десятков агентов независимо от масштаба изменения;
- право gatekeeper или snapshot-generator создавать новые продуктовые факты;
- молчаливое продолжение при missing/stale/partial blocking input;
- глобальные destructive Git-команды в пользовательском checkout;
- хранение секретов, токенов или credential values в БД, событиях, YAML, Markdown и логах;
- прямое использование результатов реализации как независимого доказательства качества в Q-аудите.

### 2.4 Карта миграции старых слоёв

| Старый слой | Куда переходит | Что сохраняется | Что меняется |
|---|---|---|---|
| A — Idea Note | P + R | интервью, feasibility/ethics lenses, binary gate, frozen handoff | MVP и marketing перестают быть обязательными; intent описывает change/product любого типа |
| B — Concept | P + R | полнота доменных аспектов, single-writer catalog, merge lineage, accepted-risk carry-forward | aspect corpus строится только в нужной глубине; micro-задача не обязана проходить полный concept review |
| C — Requirements | R | классы требований, set identity, source binding, независимая validation | staging/publish живут в SQLite; requirement defects возвращаются событиями |
| D — Stories & PRD | R + T | scenarios, Given/When/Then, acceptance, coverage и per-item review | PRD не является обязательным жанром для bugfix/utility; decomposition отделена от product scenario |
| E — Design Research & Intent | E | claim classes, owner intent, tension mapping, accessibility и signed experience intent | слой больше не заставляет того же агента одновременно рисовать и формализовать |
| F — UX Architecture | E | surface ownership, navigation/IA/interaction chain, accessibility, immutable handoff | UX и adoption объединяются до визуального творчества; графическое решение вынесено в G |
| G — Visual System & UI | G | draw-first, assets-before-surfaces, art critic, mapping, human-visible review | разделение creative/structural lanes становится жёстким контрактом; canonical artifacts хранятся в DB |
| H — Design-to-Code Handoff | H + A | Elm modules, Model/Msg/update/view, ports, traceability, maker-checker reviews | Elm сохраняется как first-class стандарт; H получает system contracts из A draft и возвращает integration constraints в A final |
| I — Architecture & Task Graph | A + T | process→invariant→interaction derivation, spikes, multi-axis reviews, task graph, frozen snapshot | presentation coverage становится first-class; 25-agent fixed chain заменяется profile/event routing |
| J — Implementation | I + S0/harness | dispatcher, recipes, worktrees, evidence, dependency/migration/HITL flows, recovery | uniform envelope, SQLite state, executable primitives, risk-tier autonomy вместо гигантского J0 и per-agent approval |
| K — Audit & Documentation | Q | независимая reconstruction, immutable target, evidence assurance, sharding, exact docs approval | baseline выбирается из approved v2 decisions; результаты/состояние живут в project DB |
| M — Meta | M | diagnosis taxonomy, red→green, test tiers, known limitations, human merge | `M0`, event subscriptions, два approvals и pipeline-version pinning встроены в общий control plane |

Паттерн `J0/K0` не принадлежит только новым I/Q: он становится обязательной формой `P0/R0/E0/G0/A0/H0/T0/I0/Q0/M0`, а над ними появляется `S0`.

---

## 3. Цели, границы и инварианты v2

### 3.1 Цели

1. **Полнота:** каждое утверждённое намерение прослеживается до реализации и доказательства либо до явного решения `deferred/not_applicable/accepted_risk`.
2. **Точность:** ни один агент не работает с непроверенным `latest`; все входы version/hash-bound, а выводы отделены от фактов и человеческих решений.
3. **Эффективность:** запускаются только применимые агенты; независимые reviews параллелятся; replay начинается с самого раннего затронутого owner и не пересчитывает неизменившиеся ветви.
4. **Безопасность:** least privilege, изолированные worktree, deny-by-default для опасных действий, секреты только по ссылкам, hash-bound HITL и независимый аудит.
5. **Универсальность:** один control plane обслуживает новый продукт, изменение существующего продукта, внутреннее ПО, bugfix и небольшую утилиту.
6. **Восстановимость:** состояние восстанавливается из SQLite и Git, а не из памяти конкретной Claude/Codex-сессии.

### 3.2 Не-цели первой версии

- фоновый daemon или автономное выполнение без человечески запущенной VS-сессии;
- распределённая очередь между несколькими машинами;
- универсальный live-доступ к production-инфраструктуре;
- автоматическое слияние prompt-изменений M-слоя;
- полная реализация всех target events, worker rosters, сложного graph replay, cache и cost optimization до первого runtime;
- полный M-слой до появления наблюдаемого runtime; foundation включает только meta hooks/version pinning и диагностические events;
- точная реализация всех будущих prompt-схем в этом документе.

### 3.3 Неподвижные инварианты

1. Рабочий агент не вызывает другой рабочий агент.
2. Любое управление передаётся событием.
3. Cross-layer событие маршрутизирует только `S0`; local routing policy принадлежит соответствующему `{Layer}0`, но её однозначная nominal-ветвь может исполняться как hash-pinned compiled fast-path без LLM-вызова.
4. Агент не пишет напрямую в SQLite и не изменяет runtime state; он возвращает валидируемый результат диспетчеру.
5. Артефакт имеет одного логического owner; исправление чужого артефакта выполняется через revision event.
6. Published artifact version иммутабельна. Исправление создаёт новую версию и lineage edge.
7. Gate не считается пройденным без schema, lineage, freshness и evidence checks.
8. `passed` и human approval — разные факты. Машинная готовность не подменяет разрешение человека.
9. `warning` не маскирует blocker. Неблокирующие условия имеют owner и treatment.
10. Normal run pin-ит commit/version пайплайна и baseline commit проекта.
11. Операция Git всегда знает ожидаемый repository root и роль репозитория.
12. Completion реализации невозможен без typed acceptance evidence.
13. M не меняет промпты без human approval и не исправляет проектные артефакты вручную.
14. Q реконструирует as-built состояние независимо и не принимает I-отчёты за первичное доказательство.
15. В G творческий агент не получает component IDs, traceability matrices, annotation schemas или обязанность формально покрыть структуру во время рисования.
16. Формализатор G не принимает художественных решений: он применяет только подтверждённое mapping.

---

## 4. Общая архитектура

```text
Human command in Visual Studio
              │
              ▼
     S0 Superdispatcher
       │    │      │
       │    │      └─────────────── Human approval / external action
       │    │
       │    └──── Event router + global policy + project lock
       │
       ├── P0 ── P workers
       ├── R0 ── R workers
       ├── E0 ── E workers
       ├── G0 ── G workers
       ├── A0 ── A workers
       ├── H0 ── H workers
       ├── T0 ── T workers
       ├── I0 ── I workers
       ├── Q0 ── Q workers
       └── M0 ── M workers
              │
              ▼
   deterministic pipeline harness
   - SQLite transactions and queries
   - schema validation
   - event append/delivery
   - hashes/CAS/leases
   - projection generation
   - Git/worktree/repository guards
   - safe tool execution and side-effect intents
              │
              ▼
 projects/<project>/.pipeline/pipeline.sqlite3
```

Супердиспетчер и диспетчеры слоёв являются reasoning-компонентами. Транзакции, блокировки, хеширование, Git-проверки и публикация должны быть детерминированными функциями harness. Промпты не должны «симулировать базу данных» или воспроизводить многостраничный CAS-протокол по памяти.

### 4.1 Control plane и data plane

- **Control plane:** команды, runs, events, subscriptions, gates, approvals, leases, retries, invalidations, prompt/pipeline versions.
- **Artifact plane:** content, artifact versions, decisions, evidence, findings, traceability edges.
- **Product plane:** код, тесты, миграции, конфигурация и документация в собственном Git проекта.
- **Prompt plane:** промпты, schemas, registry, harness и тесты в верхнеуровневом Git.

Control/artifact plane проекта находятся в SQLite этого проекта. Prompt plane никогда не смешивается с project Git.

---

## 5. Предлагаемый состав слоёв

Количество рабочих промптов ниже предварительное. На этапе детального проектирования слоя их можно объединять или разделять, не меняя межслойные контракты.

### 5.1 P — Project Context & Change Discovery

**Назначение:** понять, с каким проектом и типом работы мы имеем дело, зафиксировать Git baseline, существующее состояние, заинтересованных пользователей и границы изменения.

**Диспетчер:** `P0`.

**Предварительные workers:**

- `P1` Repository & Workspace Baseline — проверка двух Git-контуров, инвентаризация проекта, commit/dirty/submodule state.
- `P2` Intent & Project Profile Interview — тип проекта, цель, пользователь, urgency, interface, assurance.
- `P3` Existing System Reconnaissance — архитектура и фактическое поведение существующего ПО; для greenfield выдаёт applicability receipt.
- `P4` Stakeholder & Adoption Context — пользователи, процессы, ограничения компании, риск саботажа/непринятия внутреннего ПО.
- `P5` Scope, Risk & Unknowns Triage — change boundary, критические неизвестные, необходимость early spikes.
- `P6` Context Gate & Publisher — полнота профиля и стартовый immutable package.

**Главные outputs в БД:** project profile, repository baseline, change intent, stakeholder/adoption context, initial risk/unknown ledger.

### 5.2 R — Requirements & Success Criteria

**Назначение:** превратить intent/change request в достаточные, проверяемые и типизированные requirements и acceptance outcomes.

**Диспетчер:** `R0`.

**Предварительные workers:**

- `R1` Scope & Change Analyst — in/out of scope, compatibility, regression boundary.
- `R2` Requirement Translator — functional, system, operational и non-functional requirements.
- `R3` Scenario & Acceptance Designer — user/system scenarios, examples, acceptance checks без привязки к случайным именам будущих файлов.
- `R4` Security, Privacy, Compliance & Operational Requirements — применимые угрозы и обязательства.
- `R5` Coverage, Conflict & Testability Reviewer — полнота, конфликты, измеримость, typed coverage universe.
- `R6` HITL Scope & Success Review — подтверждение ключевого scope и критериев успеха.
- `R7` Requirements Gate & Publisher.

Market/monetization review является подключаемой линзой для коммерческого продукта, а не обязательным этапом любого проекта.

### 5.3 E — Experience, Adoption & UX Architecture

**Назначение:** определить пользовательский опыт и структуру взаимодействия до художественного проектирования: кто, зачем и в каком контексте использует продукт; какие существуют surfaces, journeys, states, navigation, content и recovery paths.

**Диспетчер:** `E0`.

**Предварительные workers:**

- `E1` Experience & Adoption Research — ожидания пользователя, контекст использования, барьеры внедрения и саботажа.
- `E2` Owner Experience Intent Interview — характер опыта, доверие, выразительность, допустимые напряжения и антицели.
- `E3` Surface, Journey & Navigation Architect.
- `E4` Information, Interaction & Content Architect.
- `E5` UX Structure & Accessibility Architecture Reviewer.
- `E6` HITL Experience Structure Review.
- `E7` Experience Gate & Publisher.

E публикует human-readable creative brief для G и отдельный formal structural contract. Он не создаёт готовое графическое решение и не заставляет будущего visual designer размечать компоненты.

Для внутреннего ПО E включается по умолчанию: adoption и usability считаются функциональными рисками, а не косметикой. Для невизуальной утилиты E0 публикует явное решение о неприменимости или облегчённом CLI/API experience review.

### 5.4 G — Graphic & Visual Solution

**Назначение:** создать сильное графическое решение, а затем независимо и проверяемо связать уже принятое решение со структурой продукта. Слой прямо учитывает установленное ограничение LLM: один и тот же creative context не должен одновременно оптимизироваться на художественное качество и формальную traceability.

**Диспетчер:** `G0`.

**Предварительный roster, сохраняющий лучшее из старого G:**

- `G1` Visual System Reference Architect.
- `G2` Visual System QA.
- `G3` Asset Strategy.
- `G4` Asset Generator, интерактивный co-author.
- `G5` Asset QA.
- `G6` Art Critic.
- `G7` Creative Surface Designer, интерактивный co-author.
- `G8` Component Manifest Builder, читающий только E/R specs.
- `G9` Visual-to-Structure Mapper.
- `G10` HITL Mapping Review.
- `G11` Annotation & Blueprint Formalizer.
- `G12` Accessibility/Perceptual Reviewer.
- `G13` Product & Traceability Reviewer.
- `G14` H-layer Package Generator.
- `G15` Owner Sign-off & Publisher.

#### 5.4.1 Жёсткое разделение контекстов

G0 формирует два непересекающихся context bundle:

- **Creative bundle для G7:** design intent, пользовательские цели surfaces, hash-bound `platform_constraint_predecision`, состояния в понятной человеку форме, design tokens, approved real assets и ранее принятые surfaces. В нём запрещены component IDs, coverage matrices, annotation schemas, traceability fields и формальный manifest.
- **Structural bundle для G8:** requirements, surface/zone/interaction contracts, invariants и component vocabulary. G8 не получает visual output G7 и не оценивает красоту.

Эта изоляция обеспечивается DB allowlist/context query, а не только текстовой просьбой в промпте. Первым агентом, которому разрешено увидеть оба результата, является G9.

G не стартует только из абстрактного interface intent. До открытия creative lane A0 публикует ограниченный `platform_constraint_predecision`: целевые platform/runtime, viewport и input modes, offline/online constraints, performance envelope, asset/media constraints и известные integration boundaries. Это не A draft и не выбор всей технологии; изменение predecision инвалидирует зависимые G-артефакты.

#### 5.4.2 Поток G

```text
G1 visual reference → G2 QA
          │
          ├─ G3 asset strategy → G4 generation/HITL → G5 QA → G6 art critic
          │                                                     ↓
          │                                    G7 creative surfaces + HITL
          │                                    (one surface at a time;
          │                                     no IDs/annotations/coverage)
          │                                                     │
          └──────────────── G8 structural manifest ─────────────┤
                         (specs only; no visual input)           ↓ barrier
                                      G9 mapping + visual overlay
                                                   ↓
                                      G10 human mapping review
                                                   ↓
                                      G11 mechanical formalization
                                                   ↓
                                      G12 + G13 independent reviews
                                                   ↓
                                      G14 H package → G15 sign-off
```

G8 может выполняться параллельно creative lane после готовности E/G1: он не передаёт свой результат G7. Mapping начинается только после того, как человек зафиксировал visual generation и G8 завершил независимый structural manifest.

#### 5.4.3 Creative protocol

- Реальные assets создаются и принимаются до рисования surfaces; placeholder graphics не используются для финального визуального решения.
- G7 работает по одной surface: предлагает 2–3 направления, человек выбирает, агент рисует и итеративно дорабатывает, затем версия surface блокируется.
- Человек является co-author, а не только финальным reviewer.
- G4 фиксирует отдельный интерактивный checkpoint после каждого принятого asset, а G7 — после каждой принятой surface. Human activity атомарно продлевает fenced lease; после crash S0 восстанавливается с последнего принятого checkpoint, не повторяя уже подтверждённую генерацию.
- До формальной G12-проверки G7 получает дешёвые advisory-сигналы о контрасте, размере targets и motion risk. Они не содержат component IDs и не подменяют G12. После G11 G13 сначала выполняет дешёвый structural precheck, затем запускает дорогие независимые reviews только при валидной структуре.
- G7 может использовать семантические HTML/class names или иной естественный visual structure, но не canonical component IDs и не downstream annotations.
- Artistic quality и formal coverage — разные gate dimensions; успех одного не компенсирует провал другого.

#### 5.4.4 Reconciliation и revision

- G9 строит overlay, сопоставляя независимый manifest и locked visual solution.
- G10 подтверждает, переназначает или отклоняет mapping; неоднозначность не решается автоматически.
- G11 только применяет подтверждённое mapping и строит blueprints/annotation/traceability. Он не имеет права менять композицию или придумывать отсутствующий компонент.
- Visual defect возвращается G0 и маршрутизируется G7; asset defect — G3/G4; structural defect — E0; mapping ambiguity — G9/G10; `interaction_model_failure` — E0 с последующей invalidation затронутых G/H/A artifacts.
- Новая visual generation инвалидирует mapping/formalization/reviews, но не G8 manifest, если E-specs не менялись.
- Изменение E structural contract инвалидирует и creative brief, и manifest, после чего G0 вычисляет минимальный replay.

Canonical visual artifacts, generations, mappings и reviews хранятся в SQLite. Для HITL harness материализует временный preview workspace; после принятия его content/hash импортируется в БД. Preview-файлы не становятся третьим источником истины.

**V1 failure policy:** провал раннего G/H risk slice не разрешает молча перейти к A-final/T/I. G0/S0 классифицируют источник как `creative_quality | structural_contract | mapping | interaction_model | A0_platform | H_elm`. `interaction_model_failure` означает, что visual и formal structure приемлемы, но пользовательский поток, состояния или обратная связь непригодны; его primary owner — E0, который возвращает исправленный journey/interaction contract и запускает dependency-based invalidation G/H/A. Затем owner выбирает один из заранее допустимых routes: (1) изменить и повторно утвердить применимые E/G/H/A layer architecture plans, сузив конкретную гипотезу и повторив V1; (2) сузить первый product surface через явное scope decision, не удаляя обязательную user-facing capability продукта; (3) использовать A8 только для доказанного Elm applicability/feasibility conflict, но не как обход visual-quality/interaction/mapping gate; (4) остановить product track и провести изолированный disposable research spike. Продолжение A-final/T/I допустимо лишь после успешного повторного V1 для оставшегося scope либо human scope decision, действительно устраняющего эту surface из продукта.

### 5.5 A — Solution Architecture, Data & Risk

**Назначение:** спроектировать целевое состояние или архитектурную дельту, вывести её из процессов/инвариантов/requirements, а не из предпочтения к модному стеку. Для UI-проектов A имеет draft/final цикл вокруг H.

**Диспетчер:** `A0`.

**Предварительные workers:**

- `A1` Technology Research & Spike Planner.
- `A2` Process, Invariant & Ownership Modeler.
- `A3` Solution/Delta Architect — draft system boundaries и frontend/backend contracts.
- `A4` Data, Contract, Migration & Compatibility Architect.
- `A5` Security & Threat Model Reviewer.
- `A6` Reliability, Performance, Cost, Observability & Deployment Reviewer.
- `A7` Architecture Conflict Resolver.
- `A8` HITL Trade-off, Technology Exception & Risk Acceptance.
- `A9` Architecture Integrator, Gate & Publisher — после H, если H применим.

Архитектура включает presentation/UI implementation surface, если он существует. Нельзя объявить UI «не относящимся к архитектуре» так, чтобы он исчез из task coverage. A draft фиксирует системные interfaces для H; H возвращает точные Elm/port/view constraints; A final проверяет целостность полной системы.

A также владеет policy для dependencies, licenses и software supply chain: допустимые registries/источники, lock/pin requirements, license compatibility, provenance/SBOM и правила исключений. I применяет опубликованную policy при реализации, а Q независимо аудирует её соблюдение; ни I, ни отдельный worker не ослабляют её локально.

### 5.6 H — Elm Design-to-Code Architecture

**Назначение:** преобразовать утверждённые UX/visual blueprints и A draft contracts в полную Elm-архитектуру, пригодную для task decomposition и реализации.

**Диспетчер:** `H0`.

**Предварительный roster, сохраняющий H3–H15:**

- `H1/H2` Traceability Index Builder / QA.
- `H3/H4` Elm Module Architect / QA.
- `H5/H6` Elm State & Type Architect / QA.
- `H7/H8` Elm Update & Effects Architect / QA.
- `H9` Elm Ports, Codec & API Contract Spec.
- `H10/H11` Elm View & Component Architect / QA.
- `H12/H13` Elm Architecture Integrator / QA.
- `H14` Elm Architecture HITL.
- `H15` Elm Architecture Gate & Publisher.

H сохраняет Model/Msg/update/view, module ownership, ports, package constraints, error contracts и traceability до visual components/surfaces. Он не является generic adapter, заменяемым произвольно в каждом новом проекте.

**Elm policy:**

- существующий Elm UI всегда продолжает Elm-контур;
- для новой stateful interactive application Elm является стандартным UI-архитектурным профилем Pipeline: явные Model/Msg/update/view, ограниченное пространство решений и compiler-enforced correctness;
- профиль по умолчанию применим к сложным workflow, редакторам, картам/графам, образовательным и управляющим интерфейсам с существенным состоянием;
- простая статическая страница/виджет может получить `not_applicable` либо иной профиль по фактам сложности; новая существенная stateful UI-часть существующего продукта использует Elm, если её можно ввести без несоразмерной migration/interop-стоимости;
- backend, CLI, library и UI без пригодного Elm runtime получают `not_applicable`;
- локальный bugfix в существующем non-Elm UI не вызывает скрытую перепись на Elm;
- исключение для нового применимого UI требует решения A8 с причиной, альтернативами и последствиями.

Эти критерии не остаются только prose. Canonical `registry/ui-architecture-policy/elm-applicability.yaml` задаёт versioned predicates, требуемые input facts/evidence, outcomes `required | applicable_default | exception_proposed | not_applicable`, A8 exception route и staleness rules. A0 обязан ссылаться на pinned policy version/hash и сохранять machine-checkable evaluation trace; свободный вывод агента без registry evaluation не является applicability decision.

H получает G14 package и A draft. Его published handoff является обязательным входом A9/T0; обнаруженный конфликт возвращается событием H0 → S0 → A0/G0/E0, а не исправляется H напрямую. Для одного architecture generation допускается не более двух содержательных возвратов `A draft ↔ H`; третий нерешённый конфликт переводится в A8 HITL с вариантами, последствиями и точными hashes конфликтующих контрактов.

### 5.7 T — Task Graph & Evidence Plan

**Назначение:** построить минимальный, исполнимый граф работ с явными зависимостями, зонами записи, recipes, budgets и evidence contract.

**Диспетчер:** `T0`.

**Предварительные workers:**

- `T1` Change Impact & Decomposition Unit Builder.
- `T2` Task Graph Builder.
- `T3` Task Specification Agent.
- `T4` Test, Evidence & Rollback Planner.
- `T5` Coverage & Executability QA.
- `T6` HITL Task/Risk Review.
- `T7` Snapshot Gate & Publisher.

Две независимые оси сохраняются:

- `work_type` — природа работы: research, code, presentation, data migration, configuration, infrastructure, QA, documentation, human action;
- `execution_recipe` — способ исполнения: test-first code, UI implementation, migration, integration, deployment, external manual и т.д.

Coverage проверяется типизированно. Requirement, требующий изменения поведения, не закрывается одной QA-задачей; UI surface не закрывается domain-logic задачей; destructive migration требует rollback evidence и явного risk acceptance.

### 5.8 I — Implementation & Verification

**Назначение:** выполнить опубликованный task graph в изолированных worktree и собрать проверяемые evidence.

**Диспетчер:** `I0`.

**Предварительные worker families:**

- implementation methodologist;
- test writer;
- code/UI/infra/config/migration implementers;
- dependency, static, security and lockfile reviewers;
- test/integration/load/migration runners;
- UI/behavior HITL reviewer;
- external manual action facilitator;
- code quality and documentation finalizer;
- task completion gate.

Точный roster определяется recipes на этапе плана слоя. `I0` не пишет production code и не фабрикует evidence. Git, worktree, commit, diff-scope, CI и publication операции выполняет harness по side-effect intent с идемпотентной сверкой внешнего состояния.

Engineering baseline переносится из «Закона J» в канонические language profiles `registry/engineering-standards/standards.<language>.yaml`. Для каждого принципа registry задаёт applicability и enforcement: `compiler`, `linter/static`, `contract/property test`, `independent review` или явно `advisory`:

| ID | Принцип | Минимальный enforcement |
|---|---|---|
| P1 | impossible states должны быть непредставимы | compiler/type review + invariant tests |
| P2 | pattern matching исчерпывающий | compiler/linter |
| P3 | pure core отделён от impure shell | dependency/static rule + review |
| P4 | stringly-typed domain запрещён там, где нужен тип | type/static rule + review |
| P5 | parse, don’t validate | boundary contract/property tests |
| P6 | типы не ослабляются ради удобства реализации | compiler/static diff review |
| P7 | существующий пригодный код переиспользуется | repo-map similarity review |
| P8 | новая dependency разрешена только после policy-аудита | blocking lock/license/provenance audit |
| P9 | скрытая magic минимизируется и документируется | static rule + review |
| P10 | функции малы и имеют одну семантическую обязанность | complexity metric + semantic review |
| P11 | у state один источник истины | architecture contract + state tests |
| P12 | внешние границы имеют явные adapters | dependency rule + contract tests |
| P13 | contracts/invariants покрываются contract/property tests | test manifest gate |
| P14 | применимый static analysis обязателен | blocking tool-profile run |
| P15 | silent fallback запрещён | linter where possible + failure-path tests |
| P16 | ошибки типизированы | compiler/schema check + tests |
| P17 | invariants исполнимы, а не существуют только в комментариях | executable assertion/property test |
| P18 | бесструктурный `utils`-dump запрещён | module/path rule + review |
| P19 | предпочитаются стандарты и зрелые библиотеки | architecture/dependency review |
| P20 | completion требует чистого, объяснимого diff | blocking repository/diff-scope guard |

P8 и P20 являются блокирующими во всех профилях; остальные принципы могут быть `not_applicable` только с rule/evidence. `I0` строит фактический roster из versioned `execution-recipes`, а не из свободного списка ролей в промпте.

Если для обнаруженного языка нет engineering profile, I не стартует, пока не создан и не проверен профиль либо владелец не утвердил hash-bound `advisory_only` решение с перечнем неисполняемых принципов и снижением assurance. Даже в `advisory_only` language-agnostic проверки P8 и P20 остаются blocking; такой режим запрещён для high-assurance/safety-critical scope.

### 5.9 Q — Independent Audit, Documentation & Release

**Назначение:** независимо реконструировать as-built продукт из кода и первичных источников, проверить его против approved intent/requirements/experience, locked G visual solution, H Elm contracts и system architecture constraints, затем подготовить документацию и release decision.

**Диспетчер:** `Q0`.

**Предварительные workers:**

- `Q1` Immutable Source Snapshot & Repository Indexer.
- `Q2` As-built Architecture, Contract & Capability Mapper.
- `Q3` Independent Security Auditor.
- `Q4` Requirement, Scenario, Visual & Experience Coverage Auditor.
- `Q5` Quality, Efficiency, Reliability & Concurrency Auditor.
- `Q6` UI Behavior, Visual Fidelity & Accessibility Auditor, если применим.
- `Q7` Finding Reviewer & Evidence Adjudicator.
- `Q8` As-built Documentation Synthesizer.
- `Q9` HITL Acceptance, Limitation & Release Gate.
- `Q10` Documentation/Release Publisher.

Это target roster, не Alpha prerequisite. **Q-Alpha** активирует только Q0 и минимальные независимые capabilities для четырёх проверок: requirement/acceptance coverage, artifact/version lineage, code+test evidence и rollback evidence. Он публикует findings/dispositions, но не строит полный documentation portal, release governance, comprehensive security/performance audit или Q8–Q10 publication contour. Эти возможности добавляются в X1 по evidence-triggered scope; независимость Q и запрет принимать I self-report как primary proof действуют уже в Q-Alpha.

Q может читать I evidence как вторичную подсказку только если это явно разрешено профилем, но не использует его как primary proof. Primary proof — immutable source snapshot, независимые deterministic scans/tests и отдельно предоставленное runtime evidence.

Q9 обязан перед release перечислить все `deferred`, accepted risks и known limitations, проверить owner/expiry/activation condition и явно определить влияние каждого пункта на release. Deferred item не становится runnable по календарю молча: условие активирует событие `deferred.activation_triggered`, которое снова проходит routing и gate. Q использует incremental cache по immutable source shard, tool/config hash и dependency graph; любое неоднозначное изменение консервативно инвалидирует зависимый shard, а cache-hit является оптимизацией, но не evidence.

### 5.10 M — Meta / Pipeline Self-Healing

**Назначение:** диагностировать дефекты самого пайплайна, готовить проверяемое исправление промптов/контрактов и публиковать новую версию только с human-in-the-loop.

**Диспетчер:** `M0`.

**Предварительные workers:**

- `M1` Meta Analyst.
- `M2` Meta Architect, условно для cross-prompt/cross-layer изменений.
- `M3` Meta Methodologist.
- `M4` Meta Test Writer: red phase.
- `M5p` Prompt/Contract Engineer и `M5h` Harness/Registry Engineer: взаимоисключающие либо координируемые tracks, только после approval change proposal.
- `M6` Independent Meta QA & Test Runner: green phase.
- `M7` Meta Documenter, Retrospective & Known Limitations Registrar.

Подробный процесс M описан в §14.

---

## 6. Адаптивные маршруты

P-слой формирует `project_profile`, который определяет применимость и глубину работы, но не отменяет safety invariants.

### 6.1 Основные измерения профиля

- `project_kind`: existing_bugfix, existing_feature, internal_application, utility, greenfield_product;
- `interface_kind`: none, library, CLI, API, GUI, web, mobile, mixed;
- `existing_ui_stack` и `elm_applicability`: required, applicable_default, exception_proposed, not_applicable;
- `change_scope`: micro, bounded, multi_component, system_wide;
- `assurance_level`: light, standard, high;
- `deployment_impact`: none, local, shared_environment, production;
- `data_risk`: none, reversible, migration, destructive;
- `user_impact`: invisible, limited, broad, safety_critical.

### 6.2 Рекомендуемые маршруты

| Сценарий | Базовый маршрут |
|---|---|
| Малый невизуальный bugfix | P → R(light) → A(delta/light) → T → I → Q(targeted) |
| Bugfix существующего Elm UI | P → R(light) → E(delta) → A0(platform predecision) → G(targeted visual applicability) → A(draft) → H(delta) → A(final) → T → I → Q(targeted) |
| Функция существующего ПО без UI-изменений | P → R → A(delta) → T → I → Q |
| Пользовательская функция существующего ПО | P → R → E → A0(platform predecision) → G → A(draft) → H, если применим → A(final) → T → I → Q |
| Внутреннее приложение | P → R → E(adoption mandatory) → A0(platform predecision) → G → A(draft) → H(Elm default) → A(final) → T → I → Q |
| Небольшая CLI-утилита | P → R(light) → E(CLI applicability) → A(light) → T(minimal) → I → Q(targeted) |
| Новый продукт с browser UI | P → R → E → A0(platform predecision) → G → A(draft) → H(Elm default) → A(final) → T → I → Q(full) |
| Срочный security hotfix | P(expedited baseline) → R(security acceptance) → A(threat/delta) → T → I → Q(security-focused), с последующей полной ретроспективой |

`light` означает меньший набор workers и более компактный context, а не отключение lineage, evidence, Git guards, security или final gate.

Elm applicability определяет A0 по state/interaction complexity, runtime и scope. Отклонение от Elm-default для новой пригодной stateful interactive application подтверждает человек через A8. Сам факт существования non-Elm legacy не является автоматическим разрешением переписать его в рамках локального изменения.

### 6.3 Applicability protocol

Если worker или целый слой не нужен, диспетчер публикует `applicability.resolved` с:

- объектом проверки;
- правилом и evidence, по которым он неприменим;
- областью действия решения;
- сроком/условием, при котором решение станет stale;
- downstream subscribers.

Отсутствие результата без такого события является blocker.

### 6.4 Специальная pilot-policy для `swarm`

`projects/swarm` создаётся как новый greenfield-продукт Pipeline v2:

- он не продолжает старую архитектуру и не копирует старый product code;
- старый swarm и результаты старого pipeline импортируются только как provenance-bound `research_observation`/problem evidence в untrusted context;
- допустимое преобразование: `old observation → verified problem/requirement → new owner decision`; ссылка на старое решение не является обоснованием нового;
- если Swarm имеет stateful interactive UI, его real-project route обязан пройти `P → R → E → A0(platform predecision) → G → A(draft) → H → A(final) → T → I → Q`; T/I не публикуют UI scope до G/H handoff либо утверждённого applicability/exception decision.

На момент подготовки плана внутри ещё не закоммиченного Git `projects/swarm` существует untracked legacy snapshot `old swarm/`: 12 504 файла, 208 572 020 bytes (~199 MiB), шесть вложенных `.git`, включая `node_modules`; в корне snapshot находятся `audit_results.json` и `fix_prompts.md`. Project-local ignore не считается достаточной изоляцией: он не ограничивает repository-read capability, искажает inventory/scale gates и сохраняет риск случайного bulk commit.

До любого greenfield/root baseline snapshot обязан быть физически перенесён за пределы `projects/`, по умолчанию в exact ignored path `research/old-swarm/`, и зарегистрирован как отдельный read-only research root. Обычные product agents не получают этот root; его читает только явно назначенный research importer, который создаёт provenance-bound observations. `audit_results.json` и `fix_prompts.md` всегда имеют trust class `untrusted_prior_analysis`, а не decision/fact. После переноса product-tree gate доказывает отсутствие legacy path, nested `.git`, untracked bulk и неразрешённых runtime/build roots. Snapshot не удаляется автоматически.

Pipeline и Swarm являются двумя совместно развиваемыми продуктами, но не одной version line:

```text
Pipeline version N (pinned)
  → Swarm slice
  → observed pipeline finding
  → reviewed Pipeline N+1 change
  → separate publish + explicit Swarm migration/replay decision
```

Finding в Swarm не даёт права hot-reload Pipeline или править prompt-repository из product run. До полного M он обрабатывается тем же red→green/HITL процессом вручную через pipeline-development workflow; после появления M — его штатным track.

---

## 7. Диспетчерская модель

### 7.1 S0 — обязанности супердиспетчера

`S0`:

1. Разбирает команду человека и разрешает project alias только в `projects/<project>`.
2. Проверяет prompt-repository root и project-repository root.
3. Создаёт или возобновляет run в проектной БД.
4. Pin-ит pipeline commit/prompt versions и project baseline.
5. Читает необработанные cross-layer events и subscription registry.
6. Запускает нужный `{Layer}0` как subagent либо применяет допустимый compiled fast-path его pinned contract.
7. Управляет global barriers, cross-layer invalidation и project-level lease.
8. Запрашивает human approval только по policy.
9. Выполняет recovery/reconciliation при каждом `continue project Y`.
10. Показывает человеку краткий status, evidence refs, следующий runnable action и причины ожидания.

`S0` не создаёт предметные требования, архитектуру, задачи, код или findings. Он не выбирает, как исправить upstream artifact; он доставляет событие владельцу и применяет результат его локального диспетчера.

S0 ведёт budget ledger по run/layer/invocation: токены, стоимость, wall time, число attempts/subagents и тяжёлых tool calls. При достижении soft limit он предлагает уменьшение context/assurance или дополнительный budget; hard limit атомарно останавливает новые deliveries и создаёт `budget.escalation_requested`. Продолжение допустимо только после hash-bound ответа человека с новым пределом и scope. Агентское обещание «уложиться» budget не изменяет.

### 7.2 `{Layer}0` — обязанности локального диспетчера

Каждый нулевой промпт:

1. Получает одно или несколько delivered events, уже закреплённых за слоем.
2. Проверяет event schema, freshness, causation chain и prerequisites.
3. Строит минимальный context bundle из БД по allowlist.
4. Выбирает одного или несколько подписанных workers и fan-out policy.
5. Запускает workers; после каждого результата читает structured result, а не свободный summary.
6. Валидирует invocation echo, output schema, artifact ownership, evidence и event proposals.
7. Просит harness одной транзакцией сохранить artifact versions, transition и новые events.
8. Сводит fan-out через barrier и принимает routing decision в границах слоя.
9. Для cross-layer действия выпускает событие `S0`; прямой вызов другого слоя запрещён.
10. При неразрешимом состоянии останавливается с typed blocker, а не импровизирует.

Registry compiler заранее строит fast-path из pinned `{Layer}0` contract. Harness может не вызывать LLM-диспетчер и сразу создать worker invocation, только если одновременно выполнены условия:

- contract явно помечает ветвь `deterministic_fast_path: true`;
- event/profile/schema отображаются ровно в одного required worker без semantic choice, fan-out/barrier или смены owner;
- не требуются applicability/risk/autonomy/HITL/budget/replay decisions;
- inputs fresh, capabilities и context budget заранее доказаны;
- compiled rule, dispatcher contract, registry и context-query hashes входят в route decision record.

Fast-path не является direct agent-to-agent handoff: доставку, invocation и event log создаёт harness, а правило принадлежит `{Layer}0`. Любой unknown/ambiguous value, warning, blocker, revision, retry exhaustion, policy conflict или non-nominal worker result отключает fast-path и будит `{Layer}0`. Новая версия его contract обязательно перекомпилирует и инвалидирует старый route.

### 7.3 Uniform invocation envelope

Каждый физический вызов диспетчера или worker получает один и тот же тип envelope. Каноническая схема будет жить в schema registry, а не в этом плане. Минимальные смысловые поля:

- project/run/layer-run/invocation IDs;
- unique `run_id` физического вызова и attempt number;
- triggering event IDs и correlation/causation IDs;
- prompt ID, prompt version/hash и pipeline Git commit;
- input artifact version IDs и content hashes;
- project baseline/worktree identity;
- разрешённые roots, capabilities, tools и side-effect class;
- `model_profile`, `context_budget` и `expected_cost_tier`;
- hash/canonicalization profile IDs для входов и ожидаемых outputs;
- expected output schema IDs;
- deadline, retry budget и autonomy tier.

Результат обязан точно эхо-ить envelope identity, budget request hash и фактическое usage/cost до того, как диспетчер прочитает его `status`. Late/stale/orphan result не может заменить актуальный результат.

### 7.4 Возврат downstream → upstream

Пример:

```text
I-worker обнаружил дефект task spec
  → возвращает proposal task_spec.revision_requested
  → I0 валидирует и записывает событие
  → S0 видит cross-layer route и доставляет T0
  → T0 определяет реального owner: T3 или более ранний A/R
  → создаётся новая artifact version
  → T0 эмитит artifact.superseded + replay.requested
  → S0 инвалидирует только транзитивно зависимые ветви
  → I0 получает новый handoff event и решает, что переиспользовать
```

Downstream никогда не диктует upstream, какой именно prompt запустить. Он сообщает defect/evidence/affected refs. Решение принимает нулевой агент upstream-слоя.

---

## 8. Событийная модель

### 8.1 Семантика события

Агент **инициирует** событие, включив proposal в результат. Диспетчер и harness:

1. проверяют право агента инициировать этот тип;
2. валидируют payload schema и refs;
3. атомарно записывают событие вместе с artifact/result transition;
4. вычисляют подписчиков по registry и guard expressions;
5. фиксируют snapshot фактических подписчиков в delivery records.

Таким образом, event log честно показывает инициатора-агента, хотя физическая запись выполняется доверенным harness.

### 8.2 Обязательные поля event envelope

Каноническая схема будет отдельной. Архитектурно событие должно хранить:

- `event_id`, event type/version;
- UTC date/time;
- project, run, layer-run и correlation IDs;
- `caused_by_event_id`;
- инициирующий agent ID, prompt ID/version и invocation ID;
- prompt/subprompt, при обработке которого событие возникло;
- payload и его schema/hash/canonicalization profile bindings;
- artifact/evidence refs;
- severity, confidentiality и autonomy classification;
- idempotency/deduplication key;
- snapshot подписчиков, fan-out group и barrier policy.

Требуемый пользователем лог получается прямым query/view по `events + event_deliveries`: дата/время, инициатор, prompt/subprompt, параметры, все подписчики и итог каждой доставки.

### 8.3 Базовый каталог событий

Каталог ниже задаёт классы, а не окончательные payload schemas.

| Класс | Примеры |
|---|---|
| Команды | `command.received`, `run.continue_requested`, `prompt.run_requested` |
| Lifecycle | `run.started`, `layer.opened`, `agent.completed`, `run.completed`, `run.blocked` |
| Остановка | `run.abort_requested`, `run.aborting`, `run.aborted`, `side_effect.cancel_requested` |
| Артефакты | `artifact.version_created`, `artifact.published`, `artifact.superseded`, `artifact.invalidated` |
| Проекции | `projection.requested`, `projection.written`, `projection.failed`, `projection.reconciled` |
| Нормальный handoff | `handoff.ready`, `gate.passed`, `next_work.available` |
| Возврат/replay | `revision.requested`, `replay.requested`, `upstream.resolved`, `snapshot.superseded` |
| Applicability | `applicability.check_requested`, `applicability.resolved` |
| Visual/Elm | `visual.generation_locked`, `visual.mapping_requested`, `visual.mapping_confirmed`, `elm.architecture_requested`, `elm.exception_requested` |
| Ошибки | `error.input_missing`, `error.schema_mismatch`, `error.stale_input`, `error.tool_failure`, `error.timeout`, `error.security_policy` |
| Delivery/lease | `delivery.retry_scheduled`, `delivery.deadlettered`, `lease.expiring`, `lease.expired`, `late_result.rejected` |
| HITL | `approval.requested`, `approval.granted`, `approval.rejected`, `human_action.required`, `human_action.completed` |
| Quality | `finding.created`, `finding.confirmed`, `finding.refuted`, `risk.acceptance_requested` |
| Budget/scale | `budget.warning`, `budget.escalation_requested`, `budget.increased`, `context.overflow_detected`, `scale.reshard_requested` |
| DB/backup | `database.upgrade_required`, `database.upgraded`, `database.integrity_failed`, `backup.created`, `backup.verified`, `restore.requested` |
| Deferred | `deferred.recorded`, `deferred.activation_triggered`, `deferred.expired` |
| Meta | `meta.incident_detected`, `meta.change_proposed`, `meta.change_approved`, `pipeline.version_published` |

Event type всегда versioned. Несовместимое изменение создаёт новую версию, а не меняет значение старого payload задним числом.

#### 8.3.1 Минимальный Alpha event profile

Таблица §8.3 — target catalog, а не обязательный объём Foundation. Kernel начинает с событий, без которых нельзя доказать lifecycle, публикацию, handoff, revision, projection, approval и fail-closed behavior:

- `command.received`;
- `run.started`, `run.blocked`, `run.abort_requested`, `run.aborted`, `run.completed`;
- `artifact.version_created`, `artifact.published`;
- `projection.requested`, `projection.written`, `projection.failed`;
- `handoff.ready`, `revision.requested`, `gate.passed`;
- `approval.requested`, `approval.granted`, `approval.rejected`;
- `error.schema_mismatch`, `error.tool_failure`, `error.security_policy`;
- `meta.incident_detected` как hook без полного M roster.

K0-a bootstrap proof компилирует только `command.received`, `run.started`, `artifact.version_created`, `handoff.ready` и `run.completed` для одного fixture route; ошибки до K0-b могут быть typed internal terminal states. K0-b реализует остальной необходимый Alpha-0 subset и fail-closed errors; Alpha-1 добавляет gate/finding semantics для P/R/A/T/I/Q. Lease/retry events, budget/scale, cache, deferred, full replay и domain-specific namespaces добавляются только перед первым сценарием, которому они необходимы. При этом safety mechanism может существовать как внутреннее state transition до появления отдельного публичного event type. Добавление event выполняется forward-compatible migration и registry reachability test, а не расширением «на всякий случай».

### 8.4 Подписки и fan-out

- Один agent contract может подписываться на несколько event types.
- Одно событие может иметь несколько subscribers.
- Подписки имеют guard: project profile, assurance level, applicability, artifact type, severity, risk.
- При fan-out диспетчер указывает barrier policy: `all_required`, `quorum`, `first_success`, `ordered` или `advisory_collect`.
- Подписчик не считается успешно обработавшим событие только потому, что вызов завершился. Нужен валидный result transition.
- Необработанное событие после retry budget переходит в typed dead-letter state и вызывает human/M policy; оно не исчезает.

### 8.5 Ordering и exactly-once semantics

Физическое exactly-once выполнение внешнего мира недостижимо; v2 использует:

- append-once event identity;
- at-least-once delivery;
- idempotency keys;
- fenced lease для invocation;
- compare-and-swap при публикации;
- идемпотентную reconciliation перед повтором side effect.

Это даёт exactly-once **эффект** там, где внешняя операция поддерживает проверку состояния, и безопасную остановку там, где не поддерживает.

`run.abort_requested` не убивает процесс вслепую. S0 запрещает новые deliveries, переводит run в `aborting`, просит cancellable tools завершиться, отменяет только подготовленные side-effect intents и ждёт/сверяет уже начатые внешние операции. Частичные результаты сохраняются как aborted attempts, leases fence-ятся, Git worktree и БД не удаляются. После reconciliation run получает терминальный `run.aborted` либо typed blocker, если внешний эффект нельзя надёжно определить.

---

## 9. SQLite: каноническое хранилище проекта

### 9.1 Расположение и ownership

Рекомендуемый путь:

```text
projects/<project>/.pipeline/pipeline.sqlite3
```

База принадлежит только этому проекту. Она не используется другим проектом и не находится в верхнем prompt-repository.

По умолчанию runtime DB не коммитится в Git: бинарный SQLite-файл плохо сливается и создаёт шум. История версий хранится внутри самой БД; Git проекта хранит код и ключевые YAML+MD projections. Долговечность БД обеспечивается проверяемыми SQLite backups. Если владелец решит version-control DB snapshot, это должна быть отдельная явно утверждённая policy, а не случайный `git add .`.

### 9.2 Логическая схема

Точные SQL migrations являются каноническим источником и появятся в `new pipeline/harness/migrations/`. Архитектурно нужны следующие группы таблиц:

- project identity и repositories;
- pipeline/prompt/model/tool version bindings;
- runs и layer runs;
- agent invocations и invocation attempts;
- events и event deliveries;
- artifacts и immutable artifact versions;
- artifact dependencies/lineage/invalidations;
- decisions и decision versions;
- gates и gate evaluations;
- approvals/authorization receipts;
- findings, accepted risks и known limitations;
- leases, checkpoints и transition history;
- side-effect intents/results;
- projection intents/results;
- budget allocations, usage/cost records и escalation receipts;
- source shards, retrieval/cache entries и invalidation edges;
- hash/canonicalization profile bindings и внутреннее payload storage;
- schema migrations и backup registry.

### 9.3 Правила хранения артефактов

1. В БД логически доступен полный payload каждой версии рабочего артефакта, а не только path. Физическое повторение идентичных bytes внутри SQLite не требуется, но это storage optimization, а не модель идентичности.
2. Каноническая адресация в events, approvals, decisions, projections и evidence использует stable `artifact_version_id`. Hash хранится рядом как верифицируемый атрибут и никогда не заменяет version ID во внешней ссылке.
3. Hash binding состоит не из голого digest, а из `hash_profile_id + digest`; профиль pin-ит algorithm, byte canonicalization и её version. Смена алгоритма выполняется добавлением нового профиля и dual-write/backfill, без переписывания старых IDs и receipts.
4. Query-intensive данные control/trace plane — events, deliveries, decisions, approvals, gates, findings, lineage/trace/coverage/task edges и их version bindings — реляционны первично. JSON-копия не является authority для графового query или completeness gate.
5. Неоднородный структурированный payload хранится как canonical JSON `TEXT` вместе с media type, encoding, `schema_id/version/hash` и `canonicalization_version`. JSONB допустим только как воспроизводимый производный read-cache после benchmark и не участвует в identity/integrity hash.
6. Canonical schemas остаются в pinned prompt-plane registry. Project DB хранит binding на pipeline commit и schema identity/hash, но не создаёт независимый источник истины. Если для автономного аудита позже понадобится schema snapshot/cache, он импортируется только после byte/hash-сверки с registry и хранит source registry identity.
7. Бинарный payload хранится внутри SQLite как BLOB с incremental I/O для крупных значений. Оппортунистическая дедупликация возможна по уникальному `(hash_profile_id, digest)` во внутреннем payload storage, но ссылки наружу остаются version-ID-based, а provenance и reverse references сохраняются для purge.
8. External object backend, `storage_backend` polymorphism, миграция между backend и reconciliation потерянных файлов не входят в alpha. Их нельзя вводить до измерения реальных G/Q payload, backup growth и доли повторяющегося content.
9. Версия после publication не обновляется; новая редакция — новая строка с parent/supersedes edge. Current state — derived view, а не перезапись истории.
10. Project source code не дублируется как «рабочий артефакт» целиком: его primary store — project Git; БД хранит snapshot identity, diff/evidence и необходимые извлечённые представления.

### 9.4 Транзакции

Publication результата одного invocation выполняется одной транзакцией:

1. проверить lease, state revision и input freshness;
2. вставить artifact versions;
3. вставить invocation result/transition;
4. вставить events;
5. зафиксировать subscriber snapshot/deliveries;
6. обновить только derived mutable pointers через CAS;
7. commit.

Невозможно получить опубликованный артефакт без соответствующего события или событие, ссылающееся на несуществующую версию.

### 9.5 Конкурентность и backups

- SQLite работает локально, не на network share.
- `WAL`, foreign keys, busy timeout и выбранный durability profile включаются harness.
- Ни один LLM-компонент, включая S0 и `{Layer}0`, не открывает write connection. Все mutations проходят через локальную harness CLI/library, которая берёт project-scoped file lock и завершает процесс после короткой транзакции; постоянный writer-service/daemon для v2 не требуется.
- Перед schema migration и risky replay создаётся полный consistent backup через SQLite backup API. После обычной layer publication создаётся дешёвый recovery checkpoint, а новый physical backup запускается по time/change-volume/risk threshold; backup storage может применять block-level incremental/deduplicated transport, не меняя SQLite как canonical artifact store.
- Backup имеет DB schema version, project ID, last event ID и file hash.
- Restore является отдельным human-authorized действием; destructive overwrite текущей БД запрещён без проверенного backup.
- Backups находятся в `projects/<project>/.pipeline/backups/`, исключены из project Git, шифруются при наличии confidential data и удаляются по versioned retention policy. После подтверждённой утечки выполняется отдельный purge workflow для primary DB, backups, previews и logs с audit receipt; обычная ротация не считается достаточной.

### 9.6 Совместимость pipeline и DB schema

- Pipeline release объявляет диапазон поддерживаемых DB schema versions и требуемую target version.
- Более старый harness обязан отказаться открывать более новую БД на запись; read-only diagnostics разрешены только явно совместимым reader.
- Upgrade начинается событием `database.upgrade_required`, создаёт и проверяет backup, применяет только forward migrations и записывает `database.upgraded` вместе с pre/post integrity results.
- Downgrade in-place запрещён. Возврат выполняется восстановлением проверенного pre-upgrade backup в новый путь после HITL, не перезаписью текущего файла.
- Prompt/pipeline version и DB schema version pin-ятся совместно в run binding; несовместимость блокирует resume до upgrade/migration decision.

---

## 10. Ключевые решения: YAML + Markdown

### 10.1 Что считается ключевым решением

В файловые проекции попадают только решения, которые полезны человеку вне конкретной agent-сессии:

- цель, границы и success criteria проекта/изменения;
- существенный product/internal-adoption decision;
- ADR/technology/data/contract decision;
- security/privacy/legal risk acceptance;
- существенное UX/accessibility/visual direction;
- release, migration и rollback decision;
- accepted known limitation с owner/expiry.

Review reports, промежуточные черновики, event logs, run state, retry counters и обычные findings остаются только в БД.

### 10.2 Размещение

```text
projects/<project>/.pipeline/decisions/<decision-id>.yaml
projects/<project>/.pipeline/decisions/<decision-id>.md
```

Оба файла имеют один stem и представляют одну DB decision version.

### 10.3 Синхронизация проекций

SQLite и filesystem нельзя обновить одной атомарной транзакцией, поэтому используется transactional outbox:

1. DB transaction публикует decision version и projection intent.
2. Детерминированный projector создаёт YAML и Markdown во временных файлах.
3. Оба файла проходят schema/render validation и atomic rename.
4. Projector записывает hashes и status в БД.
5. Gate/commit запрещён, пока пара отсутствует, hashes не совпадают с ожидаемыми или projection pending.
6. После crash `S0` reconciliation завершает или безопасно повторяет незавершённый intent.

YAML и Markdown не являются двумя источниками истины. Оба генерируются из одной нормализованной DB-записи. Ручное редактирование проекции не применяется молча: diff импортируется как proposal новой decision version либо отклоняется.

### 10.4 История

- Все версии решения находятся в SQLite.
- Project Git показывает историю опубликованных текущих проекций вместе с кодом.
- Markdown содержит human-readable rationale, alternatives, consequences и approval summary.
- YAML содержит stable IDs, status, machine-readable impacts, refs и hashes.
- Старые версии не размножаются отдельными `v2-final-final.yaml`; их история доступна по decision ID.

---

## 11. Git-топология и защита двух репозиториев

### 11.1 Роли репозиториев

| Репозиторий | Содержимое | Кто меняет |
|---|---|---|
| Верхний `C:\Projects\1.Mistake Not My Baton For A Wand` | `old pipeline`, `new pipeline`, harness, schemas, prompt tests | разработка v2 и M-слой |
| `projects/<project>` | код проекта, тесты, миграции, product docs, key decision projections | I/Q и человек в контексте проекта |

Один commit никогда не пытается охватить оба репозитория. Скоординированное изменение оформляется saga: отдельные commits, связанные event/correlation ID и checkpoints.

### 11.2 Обязательный repository guard

Перед каждой Git-операцией harness проверяет:

- canonical absolute root;
- expected repository ID/role;
- `git rev-parse --show-toplevel`;
- ожидаемый branch/worktree;
- baseline/full commit SHA;
- отсутствие выхода через symlink/junction;
- фактический change set против allowlist.

Git-команды выполняются через явный `git -C <exact-root>`, а не зависят от случайного текущего каталога Visual Studio.

### 11.3 Изоляция

- Нормальная реализация выполняется в task/run-owned worktree project Git, физически расположенном вне checkout проекта: `projects/.worktrees/<project>/<task-or-run>/`.
- Harness запрещает создавать worktree внутри `projects/<project>/` и проверяет, что checkout path не является потомком individual project root. Q отдельно сканирует project tree на вложенные `.git`, worktree markers и случайно импортированные runtime roots.
- Shared checkout пользователя не очищается, не reset-ится и не используется как rollback target.
- Prompt changes M выполняются в отдельном worktree/branch верхнего репозитория.
- Evidence экспортируется из disposable worktree до разрешённого rollback.
- Branch/PR/merge операции используют intent/result records и remote-state reconciliation.

### 11.4 Текущие prerequisites репозитория

На момент подготовки плана:

- корневой `.gitignore` уже содержит `/projects/`, но сам `.gitignore` пока не зафиксирован в верхнем Git;
- `new pipeline/` также пока untracked, поэтому не существует pinned committed pipeline version для normal Alpha-run;
- `projects/swarm` имеет собственный `.git` и ещё не имеет первого commit; будущий product source отсутствует, но внутри product root находится крупный untracked legacy snapshot, описанный в §6.4.

До Foundation bootstrap/Alpha-0 в normal profile необходимо:

1. после owner disposition §23 добавить в корневой `.gitignore` exact rules `/projects/` и `/research/old-swarm/`, проверить их через `git check-ignore` до перемещения данных;
2. физически перенести `projects/swarm/old swarm/` в `research/old-swarm/` без удаления содержимого и проверить source/destination, число файлов/bytes и шесть nested Git roots; операция требует отдельного human approval;
3. выполнить симметричный product-tree hygiene scan: `projects/swarm` не содержит nested `.git`, untracked bulk, legacy/runtime/build roots или файлов вне baseline allowlist; создать project-local ignore rules до первого product commit;
4. только после этих checks зафиксировать корневой `.gitignore`, принятый pipeline baseline и relocation/hygiene receipt; foundation test блокирует normal bootstrap, если правила отсутствуют в pinned commit либо snapshot всё ещё достижим из product root;
5. создать committed fixture project с project-local ignore rules для SQLite/runtime/worktrees, сохранив tracked `.pipeline/decisions/*.yaml` и `*.md`;
6. записать prompt-repository, research и fixture repository/root identities в initialization record; research root не входит в capability product agents.

До полного §20.5 pilot отдельно требуется осознанный baseline commit в уже очищенном `projects/swarm`, его project-local ignore rules и project initialization record.

`.pipeline/backups/`, preview и transient runtime paths всегда игнорируются project Git; `.pipeline/decisions/*.yaml` и `*.md` остаются разрешёнными tracked-проекциями. Имена runtime/projected файлов следуют Windows-safe grammar: lowercase ASCII, цифры, `-`, `_`, `.`, без reserved device names, trailing dots/spaces и path components, отличающихся только регистром. Harness не исполняет команды из текстовых артефактов; разрешённый command template и hash binary берутся из registry.

Эти действия не выполняются данным архитектурным планом: commit pipeline baseline относится к переходу Decision baseline → 2.0a/3.0a, fixture — к Foundation, а baseline `swarm` — к подготовке полного pilot. Обнаруженный prior-art commit `d9573c4` содержит начальные schema/bootstrap scripts, но рассматривается только как источник идей: его schema и shell/Python scripts не становятся v2 baseline без отдельного review, migration map и tests.

### 11.5 Два независимых rollback domain

- **Product rollback** возвращает code/config/data/deployment конкретного проекта к approved product checkpoint через project Git и project-owned migration/restore plan. Он не меняет pipeline commit/prompts.
- **Pipeline rollback** означает выбор ранее опубликованного pipeline commit/version для нового run либо explicit compatibility/migration decision для существующего run. Он не выполняется `git reset` общего checkout и не откатывает product code.
- Если новая pipeline version уже изменила project DB schema, выбор старой версии подчиняется §9.6: несовместимый harness не пишет БД; требуется verified pre-upgrade restore в новый path либо отдельная forward compatibility migration.
- Product и Pipeline rollback имеют разные approval receipts, events, checkpoints и Git commits. Корреляция допускается через incident/correlation ID, но атомарного cross-repository commit не существует.

---

## 12. Traceability, полнота и evidence

### 12.1 Типизированный trace graph

Минимальная сквозная цепочка:

```text
intent/change request
  → owner decision / approval receipt                 (где нужен выбор/разрешение)
  → requirement
  → scenario/acceptance outcome
  → experience surface/operation (если применимо)
  → locked visual generation                         (если применимо)
  → confirmed visual↔structural mapping              (если применимо)
  → architecture component/contract/invariant
  → Elm module/Model/Msg/update/view/port contract   (если применимо)
  → decomposition unit
  → task
  → Git change / human action
  → verification evidence
  → independent audit finding/disposition
```

Каждое ребро имеет тип, source, confidence и version bindings. Наличие любого `task_ref` само по себе не означает правильное покрытие.

### 12.2 Правила полноты

Для каждой coverage target допустим ровно один объяснимый исход:

- `implemented_and_verified`;
- `not_applicable` с applicability evidence;
- `deferred` с owner, reason, expiry/activation condition и влиянием на release;
- `accepted_risk` с hash-bound human authorization;
- `gap` — блокирует соответствующий gate.
- `permanent_gap` — терминальный outcome только для статической достижимости/учёта completeness: дальнейшего автоматического producer не существует. Для release он не терминален и остаётся blocker; до Q9 обязан быть преобразован человеком в `accepted_risk` либо в явное scope decision, иначе Q9 отклоняет release.

Правила совместимости:

- implementation outcome требует implementation task/evidence;
- QA/documentation/human-action task не может быть единственным носителем product behavior;
- UI surface требует presentation/UI implementation carrier либо явный deferred decision;
- графическое качество требует отдельного visual approval, а структурная полнота — отдельного confirmed mapping; один статус не заменяет другой;
- применимый Elm UI требует H-published architecture и Elm implementation carrier либо утверждённое A8 exception decision;
- human-visible acceptance требует human/runtime visual evidence, если это нельзя доказать детерминированно;
- NFR закрывается измерением или явно ограниченной assurance claim, а не заявлением агента;
- accepted risk никогда не исчезает из downstream context и Q-аудита.

### 12.3 Claim classes

Каждое существенное утверждение классифицируется:

- observed source fact;
- owner/stakeholder decision;
- approved requirement;
- research observation;
- derived proposal;
- assumption;
- independent audit conclusion.

Derived proposal не превращается в owner decision без approval event. Assumption имеет owner, verification plan и expiry/trigger.

### 12.4 Статическая связность registry

Registry compiler строит двунаправленный reachability graph до запуска пайплайна и блокирует публикацию версии, если:

- consumed field, enum value, artifact/event/evidence type не имеет producer, bootstrap source или явного external owner;
- emitted event не имеет ни допустимого subscriber, ни terminal policy;
- coverage target не достигает разрешённого статически terminal outcome, включая `permanent_gap`; такая достижимость не означает release readiness;
- decision/approval/evidence edge type не имеет owner и consumer;
- schema field не прочитан ни одним named consumer и не отмечен `informational: true` с rationale.

Проверка выполняется по реальным compiled contracts/registries, а не по совпадению строк в Markdown.

### 12.5 Consumer-proof invariant

Центральное правило готовности: **нет зарегистрированного потребителя — нет готовности слоя и нет основания публиковать артефакт как required output**. Producer contract заранее называет downstream consumer либо terminal policy; фактическое потребление создаёт `consumer_receipt` с consumer contract/run, exact `artifact_version_id`, прочитанными semantic fields, результатом `accepted | revision_requested | rejected` и evidence refs. Self-report producer не является receipt.

Артефакт без текущего consumer может существовать только как `experimental | deferred` с owner и activation trigger; он не повышает readiness/coverage. Для терминального Q потребителем является независимый owner/release/scope gate, который обязан сослаться на точную Q finding-set version. Registry compiler проверяет объявленную достижимость, runtime gate — фактический receipt.

### 12.6 Architecture hypothesis register

Pipeline v2 сам является проверяемой архитектурной гипотезой. Canonical evaluation register хранится versioned в SQLite каждого проекта/run, а не в отдельном постоянном YAML-файле. Pipeline-wide hypothesis использует один stable registry ID; evidence остаётся в породивших его project DB и связывается immutable refs — отдельная global/server DB в Alpha не вводится. Гипотеза содержит:

- stable ID, scope и точную falsifiable statement;
- предполагаемый causal mechanism и owner;
- заранее объявленные test/scenario, metric definitions, baseline/target либо иной falsification criterion;
- observation window, required evidence и independent evaluator;
- status `proposed | testing | supported | refuted | inconclusive | superseded`;
- evidence refs, limitations, decision impact и next review/expiry.

Примеры: достаточность SQLite по growth/restore evidence; влияние Elm-profile на качество LLM-generated stateful UI; снижение routing/revision errors событийной моделью; улучшение human visual review при разделении G creative/structural. Метрика и критерий фиксируются до наблюдения результата. Generic artifact events достаточны для K0-a/N1; отдельные hypothesis events не добавляются «про запас». Если оценка гипотезы приводит к key decision, только это решение публикуется YAML+MD pair со ссылкой на hypothesis/evidence versions.

---

## 13. Gates, HITL и автономия

### 13.1 Разделение трёх понятий

1. **Execution status:** вызов технически завершился или упал.
2. **Gate status:** проверяемые условия пройдены (`passed | blocked`).
3. **Human authorization:** человек разрешил конкретное решение/side effect.

Они не кодируются одним overloaded enum.

### 13.2 Risk-tiered autonomy

| Tier | Действия | Разрешение |
|---|---|---|
| Auto | чтение, DB-query, schema/hash checks, deterministic scans, reviews без side effects | автоматически внутри запущенного run |
| Run-authorized | ограниченные обратимые изменения в isolated worktree по approved task spec; обычные тесты | одно согласие на task/batch до следующей waiting/high-risk точки |
| Explicit HITL | key decisions, risk acceptance, секреты/внешние системы, destructive migration, deploy, merge/release, M prompt edit/publish | отдельное approval, привязанное к точным input/action hashes |

Это сохраняет контроль человека без модели J, где тысячи безопасных subagent-вызовов требуют механического подтверждения.

### 13.3 Approval receipt

Approval хранит actor identity/role, action, scope, exact input hashes, decision payload hash, timestamp, nonce/expiry и policy revision. Изменение входа делает approval stale. Самоутверждение роли текстом агента не является авторизацией.

Trust anchor первой локальной версии — интерактивный оператор в harness CLI/Visual Studio session. Approval создаётся только отдельной интерактивной командой harness, которая показывает exact action/input hashes и записывает локальную actor identity; текст, файл, event proposal или tool output от агента никогда не являются approval. Это даёт accountable audit trail на одной машине, но не заявляет криптографическую non-repudiation между независимыми людьми.

### 13.4 HITL UX

Перед запросом диспетчер показывает:

- что решается и почему сейчас;
- варианты и trade-offs;
- какие артефакты/код изменятся;
- риски и обратимость;
- что произойдёт при approve/reject/defer;
- точную команду resume.

Для внутреннего ПО отдельное внимание уделяется usability/adoption decision: «работает технически» недостаточно для принятия.

HITL requests образуют отдельную очередь с `blocking | deferrable`, priority, scope, expiry и зависимыми ветвями. Blocking request останавливает только транзитивно зависимые deliveries; независимые ветви продолжаются. Deferral требует явного resume/activation condition и не превращается в неограниченное молчаливое ожидание.

---

## 14. Встроенный метаслой M

### 14.1 Триггеры

M0 подписан, среди прочего, на:

- `error.schema_mismatch` — один подтверждённый mismatch достаточен;
- повторяющийся upstream/downstream loop выше threshold;
- `prompt_defect.suspected` от QA/dispatcher;
- unhandled event или неоднозначный routing;
- regression contract/golden test;
- завершение слоя для необязательной retrospective;
- ручной random audit;
- batch canary после смены модели.

Обычный failed QA не является автоматическим prompt defect. Сначала M1 отличает transient execution error, bad input, tool failure и реальный системный дефект промпта.

M покрывает не только prompts. Incident классифицируется как `prompt | contract/schema | registry/policy | harness/migration/tool-adapter | model-profile | project-specific`. Harness-track использует те же red→green, isolated prompt-repo worktree и два HITL approval; prompt edit запрещён, если воспроизводимый дефект находится в deterministic code, и наоборот.

### 14.2 FSM исправления

```text
incident event
  → M0 triage
  → M1 diagnosis
  → M2 architecture proposal       [если меняются несколько контрактов/слоёв]
  → M3 change specification
  → M4 regression tests, red phase
  → approval.requested(meta_change)
  → M5p prompt/contract edit ИЛИ M5h harness/registry edit in prompt-repo worktree
  → M6 compliance + tests, green phase
  → M7 docs/known limitations/similarity scan
  → approval.requested(meta_publish)
  → pipeline.version_published
```

Если причина transient/false positive, M завершается без изменения. Если red test не воспроизводит заявленный дефект, исправление не начинается.

### 14.3 Тестовые tiers

- **Tier 0:** структурные lint/tests prompt contract и обязательных секций.
- **Tier 1:** producer/consumer event/artifact schema compatibility.
- **Tier 2:** behavioral golden inputs с property assertions, без exact full-text match.
- **Tier 3:** end-to-end scenario/fault-injection на тестовом проекте.

Для недетерминированных/HITL частей честно фиксируется потолок покрытия.

### 14.4 HITL и публикация

Обязательны две человеческие точки:

1. разрешение реализовать конкретный meta change после диагноза, spec и красного теста;
2. разрешение опубликовать/слить прошедшую QA новую версию пайплайна.

Активный run не переключается на новую prompt version автоматически. Он остаётся pinned. `S0` формирует impact/replay proposal, и человек решает: продолжить старой версией, мигрировать или перезапустить затронутую ветвь.

### 14.5 Защита от самозацикливания

- max meta attempts;
- M не запускает M для текущей M-сессии рекурсивно;
- после исчерпания попыток создаётся known limitation/escalation;
- M не правит проектные артефакты, чтобы «подогнать» их под исправленный prompt;
- project replay выполняют штатные диспетчеры через события.

---

## 15. Safety и security architecture

### 15.1 Trust boundaries

- Текст в product repository считается данными, а не управляющими инструкциями пайплайна.
- Prompt/contract/schema доверены только из pinned pipeline version.
- External evidence импортируется с source, hash, confidentiality и redaction status.
- Agents получают минимальный context bundle и разрешённые roots, а не всю БД/весь workspace.

Любой fragment из project source, документации, issue, web, dependency metadata, generated file или tool output маркируется как `untrusted_content` с provenance и помещается в явно ограниченный data block. Его содержимое не может расширить capabilities, roots, tool policy, event types, approval scope или подписки; встреченная внутри него «инструкция агенту» остаётся quoted data и создаёт security finding при попытке влияния. Untrusted content никогда не является owner decision или human approval.

Network research импортируется сначала в quarantine record с URL, retrieval time, content hash, media type, publisher/provenance и injection scan. Material внешнее утверждение требует независимого второго источника либо human disposition; до этого оно не попадает в trusted context. Для source/code из сети действует отдельная license/provenance проверка.

### 15.2 Capabilities

Prompt contract объявляет capabilities, например:

- repository read;
- project worktree write;
- DB artifact read proposal;
- deterministic tool execution;
- network research;
- external system mutation;
- secret reference use;
- subagent dispatch — только для `S0` и `{Layer}0`.

Необъявленная capability запрещена. Каждая filesystem capability привязана к exact canonical positive root; отрицательный exclude подкаталога не используется как security boundary. Legacy research root выдаётся отдельно и только research importer, поэтому `repository read` product root физически не достигает snapshot. Tool adapter для Claude/Codex отображает capability на доступный инструмент, сохраняя одинаковую policy.

Machine-readable `registry/tool-policy/` для каждого executable profile задаёт exact binary path и SHA-256/version, разрешённые argument templates, cwd/root policy, network mode, environment allowlist, stdin policy, `follow_symlinks: false`, допустимые input/output media types и side-effect tier. По умолчанию запрещены product hooks, package lifecycle scripts, IDE/plugins и загруженные из проекта executables.

Каждый запуск имеет timeout, memory/CPU/output limits, process-tree kill policy, temp root, max child processes и max subagents. Publishing/external mutation получает one-time capability token, привязанный к exact intent/hash/expiry; token погашается после первой сверяемой попытки и не передаётся другому tool.

### 15.3 Секреты

- В prompt context и DB допустимы только `secret_ref`, vault path, env-var name или fingerprint.
- Значение секрета не записывается в event payload, agent result, YAML, Markdown, Git diff или test log.
- Перед persistence выполняется secret scan/redaction gate.
- Если задача требует секрет, которого нет, создаётся `human_action.required`, а не просьба вставить значение в чат/файл.

До отправки любого context внешней модели harness выполняет secret/PII/classification scan и применяет `registry/egress-policy/`: допустимые provider/model classes, data residency, retention class, redact/drop rules и `deny_source_content` для проектов, где исходный код нельзя передавать провайдеру. Логи, DB rows, previews, backups и model traces имеют versioned retention period; истечение создаёт проверяемую purge job, а не только рекомендацию удалить файлы вручную.

### 15.4 Команды и код

- Deny-by-default для destructive, privilege escalation, pipe-to-shell, отправки кода/данных наружу и выхода за project root.
- Product audit не исполняет недоверенные hooks/plugins/build scripts без отдельной sandbox policy.
- Path checks работают по canonical path и учитывают symlink/junction.
- File allowlist проверяется по фактическому status/diff, а не по небезопасному glob в shell.
- Необратимое действие требует exact target resolution, backup/rollback plan и explicit approval.

### 15.5 Независимый аудит

Q использует detached immutable source snapshot. Отсутствующий или непрочитанный in-scope source создаёт completeness gap. Уровень уверенности результата явно указывается: source-only, source+runtime evidence или release-bound evidence.

---

## 16. Эффективность, параллелизм и recovery

### 16.1 Эффективность

- risk/profile-based activation workers;
- минимальные context bundles из DB queries;
- content-addressed cache по input/prompt/model/tool/config hashes;
- parallel fan-out reviews на одном immutable input;
- barrier aggregation без передачи полных отчётов между workers;
- minimal replay по dependency graph;
- batch consent до meaningful stop point;
- complexity budget для числа tasks/prompts, чтобы маленькая утилита не превращалась в сотни work items.

#### 16.1.1 Scale/context policy

`registry/scale-policy/` задаёт уровни анализа `file → module/component → architecture/product`. Детерминированный scanner сначала строит полный inventory/dependency facts, затем компактный `repo_map`; LLM не читает весь repository монолитно и не объявляет отсутствие по непрочитанной выборке.

- `light/standard` могут использовать заранее опубликованный deterministic risk-weighted sampling plan с полным universe, assigned/excluded/unresolved counts и seed; `deep` требует всех supported eligible items. Sampling никогда не скрывается за формулировкой «репозиторий проанализирован».
- Model tier выбирается по сложности shard/claim, а не по названию слоя; дешёвый model допустим для классификации/сводки, сильный — для cross-boundary synthesis/high-risk adjudication. Понижение tier не разрешает превышать limits.
- Для каждой invocation: `effective_limit = min(configured_gate, model_context_limit - reserved_output_tokens - safety_margin_tokens)`. До вызова доказывается upper bound входа и выхода; неизвестный bound трактуется как превышение.
- Scale gates учитывают число files/symbols/edges/requirements/capabilities и token estimate. При превышении строятся lossless shards с immutable assignment manifest, expected/completed/unresolved counts, boundary stubs/cross-shard edge pass и aggregate hash.
- RAG разрешён только как retrieval backend внутри назначенного shard. Query, retrieval scope, selected refs, misses и unsupported scope сохраняются; RAG не заменяет sharding, inventory или reconciliation.
- Cache key включает content, dependency/reverse-dependency closure, prompt/model/tool/config/schema hashes. Rebase/merge, неизвестный edge или изменившаяся policy вызывают conservative invalidation; cache никогда не повышает claim confidence и не является evidence.

#### 16.1.2 Measurement policy

Raw telemetry закладывается в K0-a, поскольку задним числом её восстановить нельзя: monotonic/wall timestamps по run/invocation/tool/HITL, provider/model identity, input/output/context tokens, configured context limit, tool duration/outcome, event/delivery/revision counts, artifact sizes, approval/escalation facts и provider usage/cost receipt, если он доступен. K0-a не строит dashboard и не объявляет success thresholds.

Versioned `registry/metric-definitions/` позже вычисляет три семейства:

- process: elapsed/active/waiting time слоя, invocations/retries/revision cycles, context usage и measured cost;
- quality: downstream/Q findings по artifact version, escaped defects, decision churn после implementation, coverage gaps и rollback outcomes;
- autonomy: auto/run-authorized/HITL actions, approval/rejection/escalation counts и human waiting time.

До N1/Q1 эти данные являются diagnostic baseline, а не KPI или release gate. Числовой threshold становится нормативным только если заранее привязан к approved architecture hypothesis/decision с формулой, window и anti-gaming interpretation. Отсутствующий provider cost не пересчитывается по незафиксированной текущей цене; сохраняются исходные usage facts и versioned cost model. Telemetry подчиняется тем же secret/PII/retention rules, что event log.

### 16.2 Параллелизм

`S0` может выполнять независимые layer/worker deliveries параллельно, если:

- dependency graph разрешает;
- resource/file/DB/external locks не пересекаются;
- нет destructive migration;
- fan-out работает на одной pinned artifact version;
- project Git changes изолированы worktree.

SQLite остаётся single-writer на коротких транзакциях. Reasoning и read-only tools параллельны; commit результата сериализуется.

### 16.3 Recovery

При `continue project Y` S0:

1. проверяет DB integrity/schema и project/pipeline binding;
2. закрывает истёкшие leases;
3. находит orphaned/late invocations;
4. reconciles незавершённые projection/Git/external intents;
5. проверяет remote/local Git state;
6. пересчитывает runnable deliveries;
7. продолжает с первого безопасного действия или сообщает typed blocker.

Ни Claude, ни Codex session memory не является source of truth.

### 16.4 Side-effect intent pattern

Для Git push/PR/merge, deploy, external action и файловой projection:

```text
prepare intent in DB
  → verify authorization and preconditions
  → execute once
  → read external state back
  → record result/reconcile
```

После crash повтор начинается с чтения внешнего состояния, а не со слепого повтора команды.

---

## 17. Контракт каждого промпта

Рекомендуемый формат:

```text
new pipeline/layers/<layer>/<prompt-id>.prompt.md
new pipeline/layers/<layer>/<prompt-id>.contract.yaml
```

`contract.yaml` — единственный machine-readable контракт prompt. `prompt.md` объясняет reasoning procedure и ссылается на schema IDs, не копируя их полностью.

Contract определяет:

- prompt ID/version/role;
- dispatcher или worker;
- subscribed event types и guards;
- допустимые input artifact schema IDs;
- DB context query/allowlist;
- output artifact schema IDs;
- допустимые event proposals;
- capabilities/tools/side-effect tier;
- `model_profile`, hard/soft `context_budget`, `expected_cost_tier` и permitted fallback profiles;
- retry/timeout/stop semantics;
- owner/write scope;
- applicable project profiles;
- behavioral test fixtures.

Для dispatcher contract дополнительно обязательны machine-readable:

- `routing_table`: отображение `(event type/version × project/profile guards × state guards)` в exact worker set/terminal action;
- per-branch `deterministic_fast_path`, включая все eligibility/fallback условия;
- `fan_out` и barrier policy для каждой multi-worker ветви;
- ownership map для artifact/event/finding/revision classes;
- invalidation/replay rules и affected dependency scopes;
- recovery/reconciliation и HITL/autonomy transition rules.

Subscription и compiled-routing registries строятся из contracts детерминированно и pin-ятся на run. Ручной второй список подписок/routes, способный разойтись с contracts, не создаётся.

### 17.1 Общая структура worker prompt

1. Role и границы.
2. Trust hierarchy и claim classes.
3. Preflight и stop conditions.
4. Алгоритм работы.
5. Evidence/provenance requirements.
6. Result contract и event proposals.
7. Revision handling.
8. Absolute prohibitions.

### 17.2 Общая структура dispatcher prompt

Dispatcher `prompt.md` объясняет, как интерпретировать события, диагностировать non-nominal state, выбирать между разрешёнными branches, сводить reviews и формировать HITL explanation. Все исполняемые routing/fan-out/ownership/invalidation/recovery rules и разрешение запускать subagents находятся только в соответствующем `contract.yaml`; Markdown ссылается на их branch/rule IDs и не создаёт второй нормативный список.

---

## 18. Работа из Visual Studio

Верхняя папка `1.Mistake Not My Baton For A Wand` остаётся общей workspace root. Пользователь общается только с `S0`-контрактом естественными командами.

### 18.1 «Выполни промпт X для проекта Y»

`S0`:

1. разрешает `Y` в точный `projects/Y` и проверяет его Git;
2. разрешает `X` через pinned prompt registry;
3. проверяет prerequisites и applicability;
4. создаёт `prompt.run_requested`;
5. доставляет событие локальному dispatcher нужного слоя;
6. продолжает до terminal/waiting/high-risk точки согласно autonomy policy.

Прямой запрос prompt X не обходит event log, input validation, dispatcher policy и project DB. Отдельный LLM-вызов dispatcher может отсутствовать только при допустимом compiled fast-path §7.2.

### 18.2 «Продолжи проект Y»

`S0` выполняет recovery §16.3 и выбирает следующее runnable событие. Если вариантов несколько, безопасные независимые ветви могут выполняться параллельно. Если нужен смысловой выбор или authorization, S0 показывает один компактный HITL request.

### 18.3 Claude и Codex

Архитектура engine-neutral. Prompt contract требует capabilities, а adapter выбирает конкретный способ запуска в Claude/Codex. В каждом invocation сохраняются provider/model/version/tool profile, чтобы смена модели была видна тестам и M-canary.

---

## 19. Структура `new pipeline`

Предлагаемая целевая структура:

```text
new pipeline/
  PIPELINE_V2_ARCHITECTURE_PLAN.md
  PIPELINE_V2_ARCHITECTURE_REVIEW.md
  PIPELINE_V2_DEVELOPMENT_PLAN.md
  README.md
  architecture/
    shared-control-plane.md
    shared-artifact-and-event-plane.md
    S-layer-plan.md
    P-layer-plan.md
    R-layer-plan.md
    E-layer-plan.md
    G-layer-plan.md
    A-layer-plan.md
    H-layer-plan.md
    T-layer-plan.md
    I-layer-plan.md
    Q-layer-plan.md
    M-layer-plan.md
  superdispatcher/
    S0.prompt.md
    S0.contract.yaml
  layers/
    P/
    R/
    E/
    G/
    A/
    H/
    T/
    I/
    Q/
    M/
  registry/
    event-types/
    artifact-types/
    decision-types/
    evidence-types/
    coverage-edge-types/
    work-types/
    execution-recipes/
    claim-classes/
    hypothesis-types/
    metric-definitions/
    engineering-standards/
      standards.template.yaml
      standards.elm.yaml
      standards.python.yaml
    scale-policy/
    ui-architecture-policy/
      elm-applicability.yaml
    capability-policy/
    tool-policy/
    egress-policy/
    dependency-policy/
  schemas/
  harness/
    migrations/
    tools/
  tests/
    structural/
    contracts/
    behavioral/
    scenarios/
```

Architecture plans не содержат копии SQL/YAML/JSON schemas. Они указывают их canonical registry location и описывают только responsibility/invariants/flow.

---

## 20. Стратегия тестирования

### 20.1 Foundation tests

- SQLite forward migrations, отказ старого harness от новой schema, pre-upgrade backup/restore в новый path;
- append-only event invariants;
- artifact+event transaction atomicity;
- projection pair crash recovery;
- lease expiry, stale/late result rejection и CAS;
- repository guard для обоих Git;
- запрет worktree внутри individual project repo и поиск nested `.git`/worktree markers;
- graceful abort до, во время и после side effect;
- path/symlink/secret/unsafe-command/process-limit/tool-hash tests;
- backup retention и purge after leak;
- canonical JSON golden vectors для key order, numbers, Unicode и line endings;
- hash-profile agility: dual-write/backfill нового digest без изменения artifact version IDs/старых receipts;
- incremental BLOB I/O, shared-payload purge и backup-growth measurements;
- registry compiler принимает ровно минимальный Alpha event profile, отклоняет необъявленные события и расширяет profile только через versioned forward migration;
- product rollback и Pipeline-version rollback не меняют чужой Git root, pin, checkpoint или approval receipt;
- D0 relocation receipt сверяет source/destination, file/byte counts и nested Git inventory; product-tree scan после переноса не находит legacy path, nested `.git` или untracked bulk;
- capability test доказывает, что product repository-read не достигает `research/old-swarm/`, а designated research importer получает его отдельным read-only root.
- K0-a raw telemetry golden test фиксирует timestamps/durations, model/context/usage facts, event/revision/HITL counts без dashboard/KPI dependency.

### 20.2 Contract tests

#### 20.2.1 Общие contracts/registry

- каждый emitted event имеет schema и хотя бы один допустимый route либо terminal policy;
- producer artifact/event schema совместима с consumer contract;
- каждый consumed field/enum/type имеет producer/bootstrap/external owner, а каждый schema field — consumer либо `informational: true`;
- каждый coverage target статически достигает terminal outcome, включая честный `permanent_gap`, но release-checker не принимает `permanent_gap` без последующего human `accepted_risk`/scope decision;
- все prompt inputs входят в pinned context/snapshot policy;
- каждый blocker/revision имеет owner и handler;
- plan не дублирует canonical schema blocks;
- каждый key decision projector создаёт согласованную YAML+MD пару;
- artifact/evidence/event/approval refs адресуют `artifact_version_id` и содержат hash-profile binding для проверки, но не используют digest как внешнюю identity;
- schema binding разрешается ровно в pinned registry identity/hash; DB schema cache, если он появится, не может стать независимым authority;
- trace/coverage/task graph имеет реляционный authoritative representation, а JSON payload не подменяет graph completeness queries;
- coverage edges совместимы по типу;
- UI-enabled profile не может иметь ноль presentation tasks без approved deferral;
- language profile назначает enforcement всем применимым P1–P20, причём P8/P20 всегда blocking;
- неизвестный язык до I маршрутизируется в создание profile либо hash-bound `advisory_only` owner decision; P8/P20 не ослабляются;
- dispatcher `contract.yaml`, а не `prompt.md`, полностью задаёт routing/fan-out/ownership/invalidation/recovery fields для compiler;
- `I0` roster целиком выводится из versioned execution recipe;
- fast-path байт-в-байт соответствует pinned `{Layer}0` routing contract, допустим только для единственного nominal worker и при любом non-nominal результате активирует `{Layer}0`;
- Swarm baseline не содержит старый product code или старую architecture как normative input; допустимые observations имеют provenance и проходят новый P/R/E/A decision chain;
- UI-enabled Swarm не может перейти к A-final/T/I до принятого G mapping и H handoff либо явного A8 exception;
- `real_project_verified` вычисляется только из зарегистрированных real artifact, downstream consumption, normal-path evidence и observed/predeclared-injected defect→revision evidence, а не из статуса prompt-файла;
- product и Pipeline rollback contracts имеют разные owners, Git roots, approvals и compatibility checks.
- A0 Elm applicability outcome воспроизводится из pinned `registry/ui-architecture-policy/elm-applicability.yaml`; prose-only или policy-hash-free решение отклоняется;
- layer implementation contract не компилируется без approved plan receipt текущего scope/hash; budget overrun или третий unresolved review return маршрутизируется owner/HITL.
- required artifact route имеет declared consumer/terminal policy, а readiness требует runtime `consumer_receipt` exact version; terminal Q receipt может создать только independent owner/release/scope gate;
- architecture hypothesis schema требует predeclared falsifier/metric/evidence window до статуса `testing`; key YAML+MD projection появляется только у связанного owner decision;
- Q-Alpha contract ограничен четырьмя обязательными checks и не активирует Q8–Q10/full release governance до X1.

#### 20.2.2 G/H domain contracts

- G7 creative context не содержит G8 manifest/component IDs/traceability schemas;
- G8 structural context не содержит G7 visual generations;
- G11 не может изменить visual content и публикует только confirmed mapping;
- Elm-applicable UI не может пройти A/T gate без H handoff или A8 exception decision;
- третий A↔H conflict route всегда ведёт A8, а не начинает новый автоматический loop;
- platform predecision предшествует G и его hash входит в lineage visual generation.

### 20.3 Behavioral tests

Golden inputs проверяют свойства результата, а не точное совпадение текста. Для стохастических проверок фиксируются model version и k/n policy.

Обязательны adversarial fixtures: инструкция в README/issue/web-content запустить команду, поддельный approval, попытка расширить capability/event schema, exfiltration секретов/PII, malicious package hook и poisoned symlink/junction. Также проверяются context overflow → lossless sharding, sampling honesty, budget hard-stop/escalation и M-диагностика дефекта deterministic harness без ложного prompt edit.

### 20.4 Скелетные end-to-end сценарии на committed fixture

Fixture является маленьким отдельным project Git с детерминированными исходными состояниями. Он нужен для быстрых fault-injection/replay тестов и не выдаётся за реальный pilot:

1. `F00` — basic CLI проводит один pinned fixture route `command → S0 → Layer0/worker → atomic artifact version + event → terminal state`, после чего artifact/event и raw telemetry читаются обратно.
2. `F01` — инициализация проекта и двух Git guards.
3. `F02` — `continue project fixture` после остановки/новой agent session.
4. `F03` — normal compiled/local и cross-layer handoff.
5. `F04` — fan-out нескольким reviewers и barrier.
6. `F05` — downstream revision → S0 → upstream zero dispatcher → minimal replay.
7. `F06` — schema mismatch → meta incident → red test → HITL → prompt fix → green test.
8. `F07` — crash между DB decision и YAML+MD projection.
9. `F08` — late agent result после lease timeout.
10. `F09` — Git/worktree operation не в том repository/root.
11. `F10` — secret leakage/prompt-injection attempt.
12. `F11` — узкий невизуальный bugfix от P до independent Q-Alpha.
13. `F12` — минимальная surface проходит независимые G7/G8, G9/G10/G11, H handoff и Elm task coverage.
14. `F13` — product rollback не меняет Pipeline Git/version, а выбор предыдущей Pipeline version не меняет product Git и fail-closed при несовместимой DB.

`F00` gate-ит только K0-a bootstrap proof и не разрешает product run. `F01–F05`, `F07`, `F09` и базовая часть `F13` gate-ят K0-b/Alpha-0; `F11` gate-ит Alpha-1; `F12` gate-ит ранний visual/Elm slice; `F06/F08/F10` и compatibility-часть `F13` вместе с foundation/behavioral security tests gate-ят соответствующие расширения. Fixture success доказывает control-plane mechanics, но не готовность pipeline на реальном проекте.

### 20.5 Полный пилот на `projects/swarm`

Пилот начинается с осознанного greenfield baseline commit в `swarm` и проходит продуктовый lifecycle, а не имитирует bugfix несуществующего legacy code:

1. `S01` — legacy snapshot физически отсутствует в product root; old Swarm импортирован только как observation manifest через отдельный research root, а old code/architecture и prior-analysis answers не присутствуют в new product source/baseline.
2. `S02` — P публикует project profile, intent, success criteria, risks и границы нового Swarm.
3. `S03` — R публикует проверяемые requirements, acceptance outcomes и constraints с provenance.
4. `S04` — E публикует adoption/journey/surface contracts, A0 — platform predecision.
5. `S05` — G7 блокирует visual solution без component IDs; G8 независимо строит manifest; G9/G10 связывают их.
6. `S06` — visual revision инвалидирует mapping, но не manifest; E revision инвалидирует обе ветви; отдельно injected `interaction_model_failure` при корректных visual/structure возвращается E0 и пересчитывает affected G/H/A scope.
7. `S07` — A draft и H создают Elm architecture для stateful surface; exception без A8 approval блокируется.
8. `S08` — A final и T потребляют G/H и создают system architecture/task graph с presentation coverage.
9. `S09` — I реализует один работающий Swarm vertical slice с tests, evidence и product rollback.
10. `S10` — Q независимо реконструирует slice и находит либо уверенно исключает дефект, пропущенный I.
11. `S11` — crash в G4/G7 восстанавливает accepted checkpoint и fence-ит late result.
12. `S12` — abort при prepared/running/unknown side effect сохраняет audit trail и не повторяет действие вслепую.
13. `S13` — старый harness отказывается писать новую DB; upgrade создаёт verified backup и binding.
14. `S14` — poisoned repository/research content остаётся untrusted data и не меняет approval/tool/event policy.
15. `S15` — после появления реального cost pressure budget hard-stop сохраняется до hash-bound escalation receipt.
16. `S16` — Q9 блокирует release при `permanent_gap`; human decision преобразует его в допустимый release outcome либо оставляет release rejected.
17. `S17` — фиксируются BLOB-size distribution, backup growth и duplicate-content ratio без автоматического включения внешнего backend.

`S01–S04` gate-ят Swarm discovery, `S05–S07` — early visual/Elm slice, `S08` — architecture/task readiness, `S09` — first implementation, `S10` — first audit, `S11–S17` — integrated expansion. Полный набор `S*` является успешным Swarm pilot; full M имеет отдельный gate 3.8 и не подменяется product acceptance.

---

## 21. План дальнейшей разработки

Исполнимые deliverables, зависимости и gates вынесены в `PIPELINE_V2_DEVELOPMENT_PLAN.md`; этот раздел фиксирует архитектурный порядок и не дублирует рабочий backlog.

### Этап 1 — общий архитектурный план

Текущий документ. Для завершения этапа требуется архитектурное ревью и фиксация решений из §23.

### Этап 2 — архитектурные планы компонентов и слоёв

Этапы 2 и 3 не являются waterfall-фазами. Они чередуются по вертикальным срезам: минимально достаточный пакет планов `2.x` немедленно реализуется и проверяется соответствующим `3.x`; findings обновляют архитектуру до проектирования следующего среза. Планы всех одиннадцати слоёв и двух shared planes не являются предусловием bootstrap proof/Alpha-0.

Пакеты планирования:

1. **2.0a Bootstrap kernel:** phase-scoped shared plane/S plans для SQLite run/invocation/artifact/event minimum, atomic artifact+event, одного pinned contract route, basic CLI, exact fixture-root guard и raw telemetry fields. Никаких product/external side effects.
2. **2.0b Operational Alpha-0:** delta-plans для полного minimal Alpha event profile, projections/outbox, recovery/reconciliation, abort, repository/tool/egress guards, backup/compatibility и test harness.
3. **2.1 Nonvisual fixture:** минимальные планы `P/R/A(delta)/T/I/Q-Alpha`, их `{Layer}0` contracts и по одному worker path для bounded bugfix. Расширенные rosters ещё не проектируются.
4. **2.2 Swarm discovery:** greenfield-планы P/R/E и ограниченный A0 platform predecision для нового Swarm; old Swarm разрешён только как research evidence.
5. **2.3 Swarm visual/Elm risk:** минимальные планы G creative и G structural как независимые parallel lanes, G9/G10/G11 mapping/formalization, A draft и H handoff для одной реальной surface.
6. **2.4 Swarm architecture/tasks:** A final и T plan, которые обязаны потребить P/R/E/G/H outputs; до этого UI task publication запрещена.
7. **2.5 Swarm implementation:** минимальный I plan для одного end-to-end product slice, включая test/evidence/rollback contracts.
8. **2.6 First independent audit:** Q-Alpha plan только для requirement coverage, artifact lineage, code/test evidence и rollback evidence первого Swarm slice.
9. **2.7 Incremental expansion:** полные планы и rosters `P/R/E/G/A/H/T/I/Q`, а также lease/budget/scale/cache/full-replay events только под следующий доказанный scenario/риск.
10. **2.8 Full M:** полный prompt/harness self-healing plan после накопления реальных pipeline findings; двухapprovalная дисциплина и version pinning уже действуют с Foundation.

Каждый план слоя обязан определить:

- границы и applicability;
- `{Layer}0` routing table;
- worker roster и ownership;
- subscribed/emitted events;
- artifacts/decisions и schema owners;
- gates/HITL;
- invalidation/replay;
- security/capabilities;
- tests и Definition of Done.

План является отдельным versioned документом одного слоя и проходит `Layer Architecture Gate` до реализации contracts/prompts/runtime этого слоя. Его scope ограничен текущим package 2.x: полный target roster не проектируется заранее, deferred capabilities перечисляются только на уровне стабильных interfaces/risks. В approval receipt фиксируются `phase_scope`, plan complexity budget, фактический объём, current/deferred roster и разрешённый implementation scope. Превышение budget требует owner-approved rationale, а не расширяет scope автоматически.

Review не образует бесконечный author↔reviewer loop: после initial review допускается не более двух revision-return rounds. Оставшееся расхождение передаётся owner/HITL, который выбирает `approve with disposition | narrow scope | revise architecture package | block`. Последующая фаза обновляет план delta-review только для изменившегося scope; неизменные sections сохраняют прежний hash/approval.

### Этап 3 — последовательная разработка и тестирование промптов

Реализация следует тем же номерам пакетов:

1. **3.0a Bootstrap proof:** только committed fixture; basic CLI проводит `F00` через S0 → один synthetic Layer0/worker → atomic artifact version + event → terminal state и сохраняет raw telemetry. Это не Alpha-0 и не разрешение запускать product project.
2. **3.0b Operational hardening + Alpha-0:** реализуются outbox/projection recovery, abort, guards/policies, remaining Alpha events и назначенные `F*` §20.4. Только успешный 3.0b разрешает 2.1/3.1.
3. **3.1 Alpha-1 nonvisual:** `S0 + P0/R0/A0/T0/I0/Q0` и минимальные workers проводят `F11` на fixture до independent Q-Alpha outcome без ручных handoff.
4. **3.2 New Swarm discovery:** после отдельного baseline commit Pipeline запускает P/R/E/A0 в пустом project Git `projects/swarm`; результат — новый context/requirements/experience/platform predecision, а не перенос старой архитектуры.
5. **3.3 Early visual/Elm slice:** сначала F12 подтверждает contracts; затем одна реальная Swarm surface проходит parallel G creative/G structural → mapping/HITL → G11 → A draft → H.
6. **3.4 Architecture and task graph:** A final интегрирует H constraints, T создаёт исполнимый graph первого Swarm slice и evidence plan. Gate доказывает presentation coverage до начала I.
7. **3.5 First product implementation:** I реализует один работающий вертикальный Swarm slice с tests, product rollback и evidence; не весь продукт.
8. **3.6 First Q audit:** Q-Alpha независимо проверяет четыре обязательных evidence domain, возвращает findings владельцам и подтверждает либо отклоняет acceptance slice.
9. **3.7 Incremental expansion + integrated Alpha:** новые workers/events/mechanisms добавляются только под следующий scenario; полный обязательный набор `S*` §20.5 завершает pilot.
10. **3.8 Full M:** минимум один наблюдённый pipeline defect и один controlled harness defect проходят diagnosis → red test → HITL edit → green → отдельный publish approval. Self-hosted harness repair дополняет, но не заменяет Swarm evidence.

Переход `2.0a → 3.0a → 2.0b → 3.0b → 2.1 → 3.1 → …` является обязательным gate. Разрешённая параллельная подготовка не может публиковать следующий полный план до disposition findings текущего среза.

### 21.1 Цикл разработки и готовность слоя

Каждый слой проходит проверяемый цикл:

```text
architecture → machine contract → prompts/harness → artifact
             → downstream consumption → evidence/audit
             → observed-or-injected defect → revision/recovery
```

Статусы различаются: `designed`, `fixture_verified`, `real_project_verified`. Написанный prompt не делает слой готовым. Consumer-proof invariant §12.5 является центральным: артефакт без фактического независимого consumer receipt не повышает readiness. Статус `real_project_verified` допускается, только если:

1. слой создал versioned артефакт на текущем реальном project scope;
2. объявленный downstream layer фактически прочитал точную version и создал `consumer_receipt`; для terminal Q это делает owner/release/scope gate;
3. normal route прошёл с typed evidence;
4. обработан минимум один defect/revision scenario — реально наблюдённый либо заранее объявленный fault injection; фабрикация «реального дефекта» запрещена;
5. возврат попал owner-диспетчеру, создал новую version/lineage и выполнил минимальный replay;
6. limitations, unresolved gaps и downstream impact зарегистрированы, а независимый gate не опирается только на self-report слоя.

Архитектура считается гипотезой до прохождения этого цикла. Красивый документ без implementation/evidence не является validated architecture.

Старые промпты используются как библиотека проверенных вопросов, gates, failure modes и test cases, но не копируются целиком. Для каждого нового prompt составляется migration note: `source ideas`, `retained`, `rewritten`, `retired`, `new tests`.

---

## 22. Definition of Done общей архитектуры

У архитектуры три последовательных readiness gate; K0-a bootstrap proof не является Alpha-0 и не разрешает product run.

### 22.1 Decision baseline — разрешение начать 2.0a/3.0a

Архитектурный candidate допускает планирование/реализацию Control-plane minimum, когда:

- принят или изменён состав слоёв и их границы;
- каждое V2-D01…V2-D35 из §23 имеет owner disposition `accepted | modified | explicitly_deferred`, причём blocker-decision не оставлен deferred;
- подтверждены S0 + `{Layer}0` и запрет direct handoff;
- утверждена SQLite canonical-store модель;
- утверждена политика YAML+MD key decision projections;
- утверждена event envelope/subscription/delivery модель;
- утверждена Git isolation policy;
- утверждена risk-tiered HITL policy;
- принята typed traceability/coverage модель;
- принято разделение G creative/structural/mapping contexts;
- принята Elm-default policy и границы H applicability;
- принят независимый Q audit boundary;
- принят M red→green + two-approval flow;
- приняты P1–P20 engineering profiles и blocking enforcement P8/P20;
- приняты scale/context/sharding, budget и registry reachability policies;
- приняты prompt-injection, tool execution, egress/retention и local approval trust-boundary controls;
- приняты physical legacy isolation/product-tree hygiene, bounded Layer Architecture Gate, V1 failure route и machine-readable Elm applicability;
- для каждого открытого архитектурного решения назначен owner и срок закрытия.

Этот gate не требует готовых планов всех одиннадцати слоёв и двух shared planes и не утверждает архитектуру окончательно: он разрешает подготовку только phase-scoped планов пакета 2.0a и затем его проверку 3.0a.

### 22.2 Bootstrap proof — разрешение начать 2.0b/3.0b

- `F00` прошёл на committed disposable fixture: один pinned contract route создал atomic artifact version+event и terminal state, прочитанные обратно basic CLI.
- Сохранены raw telemetry facts, но отсутствуют dashboard/KPI/release claims.
- Ни product root, ни external side effect не были доступны K0-a capabilities.
- Findings bootstrap proof получили disposition и delta-scope K0-b утверждён.

### 22.3 Validated baseline — разрешение перейти к 2.1

- Control-plane minimum из 2.0b реализован без ручных обходов contracts/events.
- Alpha-0 прошёл назначенные `F*` на committed fixture, включая compiled route/fallback, transaction/projection recovery, HITL и Git guards.
- Все findings Alpha-0 имеют disposition; изменения внесены в этот план/§23 и pinned contracts либо зарегистрированы как blocker следующего slice.
- Зафиксированы минимальный 2.1 nonvisual package, следующий 2.2 Swarm discovery и ранний 2.3 visual/Elm risk package; полные rosters остальных слоёв по-прежнему не являются prerequisite.

---

## 23. Решения для подтверждения владельцем

Ниже не вопросы, блокирующие написание первой версии, а предложенные defaults для перевода плана в baseline.

| ID | Предлагаемое решение | Default |
|---|---|---|
| V2-D01 | Состав слоёв | `P/R/E/G/A/H/T/I/Q + M`, `S0` как надслой |
| V2-D02 | Каноническое runtime-хранилище | одна SQLite на проект |
| V2-D03 | Файловые project artifacts | только key decisions, всегда YAML+MD pair |
| V2-D04 | Runtime DB в Git | не track; track projections, делать verified backups |
| V2-D05 | Orchestration | события; direct agent-to-agent handoff запрещён |
| V2-D06 | Persistence writer | только deterministic harness, не LLM-agent |
| V2-D07 | Harness technology | Python CLI/library, совместимая с Windows/Visual Studio |
| V2-D08 | Autonomy | risk-tiered, без approval перед каждым безопасным subagent |
| V2-D09 | Internal software | E/adoption/usability включены по умолчанию |
| V2-D10 | Independent audit | Q не доверяет I self-reports как primary evidence |
| V2-D11 | Meta changes | approval перед edit и отдельный approval перед publish |
| V2-D12 | Project folder in root Git | `/projects/` обязательно игнорируется верхним repo |
| V2-D13 | Normal pipeline runs | только pinned committed pipeline version; dirty mode — отдельный development profile с diff hash |
| V2-D14 | Architecture docs | не дублируют schemas; canonical schemas живут в registry/migrations |
| V2-D15 | Elm standard | Elm обязателен для existing Elm UI и является стандартным profile для новой пригодной stateful interactive application; applicability определяет A0, исключение утверждает A8 |
| V2-D16 | Graphic solution | G7 creative и G8 structural работают в изолированных контекстах; связь появляется только в G9/G10, formalization — только после mapping approval |
| V2-D17 | Engineering baseline | P1–P20 в language profiles; каждый принцип имеет machine/review enforcement, P8/P20 blocking |
| V2-D18 | Scale/context | honest universe/sampling, `repo_map`, effective limit, lossless sharding; RAG только внутри shard |
| V2-D19 | Tool execution | machine-readable policy, pinned binaries/arguments, resource/process limits, deny-by-default hooks/network |
| V2-D20 | Untrusted content | provenance/quarantine; content не расширяет capabilities/events и не является approval |
| V2-D21 | Egress/retention | pre-model secret/PII scan, provider classes, `deny_source_content`, auditable purge |
| V2-D22 | Artifact storage/addressing | все payload внутри SQLite; внешние refs по artifact version ID; hash-profile — проверочный атрибут; relational graph + canonical JSON TEXT + binary BLOB; external/multi-backend не входит в alpha |
| V2-D23 | Harness changes | отдельный M5h track с red→green и двумя HITL approvals |
| V2-D24 | Первый vertical rollout | K0-a bootstrap fixture → K0-b operational Alpha-0 → nonvisual fixture → new Swarm P/R/E/A0 → early G/A-draft/H → A-final/T → I slice → Q-Alpha → expansion → full M |
| V2-D25 | Deterministic route | harness исполняет однозначный nominal route из pinned `{Layer}0` contract без LLM-вызова; non-nominal state активирует `{Layer}0` |
| V2-D26 | Worktree layout | `projects/.worktrees/<project>/...`; worktree внутри individual project запрещён |
| V2-D27 | DB compatibility | joint pipeline/schema binding, forward migrations с backup, старый harness fail-closed на новой DB |
| V2-D28 | Swarm product baseline | новый greenfield product; старый Swarm только provenance-bound observations, не source architecture/code |
| V2-D29 | Rollback domains | product rollback и Pipeline version rollback раздельны по Git, approval, checkpoint и DB compatibility |
| V2-D30 | Alpha events | реализуется минимальный profile §8.3.1; target catalog расширяется just-in-time по scenario |
| V2-D31 | Layer readiness | `real_project_verified` требует exact-version independent `consumer_receipt`, evidence/audit и observed-or-injected defect/revision cycle; terminal Q consumer — owner/release/scope gate |
| V2-D32 | Legacy Swarm isolation | до root/product baseline snapshot физически переносится из `projects/swarm` в exact ignored `research/old-swarm/`; только отдельный read-only research capability, no ignore-only fallback |
| V2-D33 | Layer Architecture Gate bounds | individual just-in-time plan на текущий phase scope; declared complexity budget; максимум два reviewer return rounds, затем owner/HITL |
| V2-D34 | V1 failure route | classify, включая `interaction_model_failure`→E0; revise/reapprove E/G/H/A и повторить, честно сузить scope, ограниченный A8 Elm exception либо остановить track для disposable spike; A-final/T/I не обходят gate |
| V2-D35 | Elm applicability authority | A0 вычисляет outcome по pinned machine-readable `ui-architecture-policy/elm-applicability.yaml`; A8 утверждает исключение |

Предыдущие расхождения по V2-D22/V2-D24/V2-D25 сведены в уточнённые defaults. Таблица всё ещё является предложением, а не owner approval; Decision baseline возникает только после явного disposition каждого решения.

---

## 24. Основные риски первой версии

| Риск | Митигирование |
|---|---|
| S0 превращается в новый гигантский J0 | Вынести транзакции в harness; S0 хранит только routing/policy, а agent invocation bundles — в contracts |
| Event catalog разрастается | Versioned namespaces, минимальный core, layer-specific events только при семантической необходимости |
| SQLite становится single point of failure | backups, integrity checks, WAL, short transactions, restore drill, key projections в Git |
| BLOB-артефакты раздувают DB/backups | internal hash-profile dedup where useful, incremental BLOB I/O, backup по change/risk threshold, измерение G/Q payload и backup growth; multi-backend не реализуется до доказанной необходимости |
| Дублирование DB и YAML/MD расходится | DB canonical + transactional outbox + hash gate + crash reconciliation |
| Слишком много агентов для маленьких задач | project profile, applicability, light routes, complexity budget |
| Слишком мало проверки из-за light route | неизменяемые safety/evidence/traceability gates независимо от глубины |
| Несовместимость Claude/Codex | capability contracts и engine adapters; provider/model фиксируется в invocation |
| Creative agent снова перегружается traceability | DB-enforced context isolation; отдельные G7/G8; contract test запрещает component IDs/coverage schema в creative bundle |
| Хороший visual теряется при формализации | locked visual generation immutable; G11 не имеет права менять дизайн; любое изменение возвращается G0/G7 |
| Elm-default провоцирует скрытую перепись legacy UI | applicability rules и A8 exception/migration decision; локальный non-Elm bugfix не расширяет scope автоматически |
| Prompt self-healing повреждает активный run | pinned pipeline version; новая версия не hot-reload; human-approved migration/replay |
| Вложенные Git перепутаны | canonical repository guard, explicit roots, `/projects/` в root ignore, physical legacy move до baseline, product-tree hygiene scan и отдельные worktrees |
| Незаметно потерян UI/adoption scope | surface registry, typed presentation coverage, conditional human-visible evidence |
| Walking skeleton создаёт ложную уверенность | сразу после nonvisual slice выполняется отдельный G/H risk slice; skeleton доказывает control plane, а не полноту продукта |
| Prompt injection меняет policy через repo/web | untrusted data blocks, provenance/quarantine, capability/event/approval non-escalation и adversarial tests |
| Старый Swarm остаётся внутри product root и диктует inventory/context/архитектуру | обязательный physical move до baseline в отдельный ignored read-only research root; exact capability isolation; observation-only import с provenance; product-tree structural gate |
| G/H появляются после task graph/кода | Swarm gate запрещает A-final/T/I до G mapping и применимого H handoff/exception |
| Co-evolution превращается в hot reload Pipeline | каждый Swarm run pinned; finding создаёт отдельную reviewed Pipeline version и explicit migration/replay decision |
| Критерий дефекта стимулирует фабрикацию | readiness принимает observed или заранее объявленный fault injection; provenance сценария фиксируется до исполнения |
| Layer plans вырастают в десятки тысяч строк и задерживают runtime | phase-scoped plan envelope, declared complexity budget, deferred roster без полной детализации, delta-review и HITL после двух возвратов |
| Провал V1 останавливает продукт и вызывает импровизированную переархитектуру | заранее объявленный failure ladder; A8 не обходит visual gate; продолжение только после повторного evidence или честного scope decision |
| Elm applicability зависит от свободного текста A0 | pinned machine-readable policy, evaluation trace и contract test до H/A/T gate |
| Foundation неделями строит hardening до первого artifact/event | K0-a F00 bootstrap proof отдельно от K0-b; fixture-only и no-side-effect boundary не позволяет превратить прототип в product runtime |
| Метрики становятся KPI до появления baseline и стимулируют gaming | K0-a сохраняет только raw facts; thresholds становятся gate лишь через predeclared hypothesis/owner decision после N1/Q1 |
| Слои производят формально полные, но никому не нужные artifacts | consumer-proof invariant: declared consumer при compile time и exact-version receipt при runtime; без него нет readiness |

---

## 25. Итог

Pipeline v2 должен стать не набором длинных независимых промптов, а локальной системой управления разработкой, где:

- агенты рассуждают;
- диспетчеры принимают routing-решения;
- события передают управление;
- SQLite хранит полную историю;
- harness гарантирует транзакции и безопасность;
- Git разделяет prompt code и project code;
- G сначала создаёт и блокирует сильное visual solution, а затем отдельные агенты связывают его со структурой проекта;
- H сохраняет Elm как стандартный design-to-code контур там, где он применим;
- каждый required artifact доказывает необходимость exact-version consumer receipt, а не фактом собственного существования;
- SQLite хранит architecture hypotheses и raw telemetry, но KPI появляются только после baseline и owner decision;
- gates требуют evidence;
- HITL применяется там, где цена решения этого требует;
- M улучшает пайплайн, но не получает права менять его без человека.

Такой каркас сохраняет наиболее зрелые идеи J/K/M старого пайплайна, устраняет обнаруженные системные слабости и делает процесс применимым как к крупному продукту, так и к небольшому изменению существующего проекта.
