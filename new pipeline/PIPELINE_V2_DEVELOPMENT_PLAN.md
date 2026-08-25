# Pipeline v2 — план разработки

**Версия:** 0.4  
**Дата:** 2026-08-25  
**Статус:** draft для owner disposition и запуска Foundation  
**Архитектурный источник:** `PIPELINE_V2_ARCHITECTURE_PLAN.md` v0.7

**Изменения 0.2:** введён обязательный `Layer Architecture Gate`: каждый слой, включая S, получает собственный детальный архитектурный план и approval до разработки его contracts, prompts и layer-specific runtime. Планы создаются just-in-time перед соответствующим слоем, а не все сразу до первого запуска kernel.

**Изменения 0.3:** задача физической изоляции legacy snapshot старого Swarm перенесена из S1 в обязательные D0 relocation/product-tree gates без ignore-only fallback; Layer Architecture Gate получил phase scope budget и bounded review; V1 — заранее определённый failure route; Elm applicability — machine-readable registry authority. D0 work-item IDs перенумерованы в фактическом порядке исполнения.

**Изменения 0.4:** K0 разделён на fixture-only K0-a bootstrap proof и K0-b operational hardening/Alpha-0; добавлены `interaction_model_failure` с owner E0, SQLite architecture hypothesis register, raw telemetry с отложенными KPI, явный Q-Alpha и центральный exact-version consumer-proof gate. Это последний architecture refinement перед D0; decision catalog остаётся V2-D01…D35.

---

## 1. Назначение документа

Этот документ переводит архитектуру Pipeline v2 в последовательность исполнимых пакетов работ. Он отвечает на вопросы:

- что строится первым;
- какой минимальный результат обязан появиться в каждом пакете;
- на fixture или на реальном Swarm проверяется результат;
- какие evidence разрешают перейти дальше;
- что намеренно отложено, чтобы архитектура не ушла в переинженеринг.

Документ не копирует SQL, event schemas, prompt contracts и layer architectures. Их единственные нормативные источники находятся в `migrations/`, `registry/`, `*.contract.yaml` и соответствующих layer plans.

Pipeline v2 и новый Swarm рассматриваются как два связанных, но независимо версионируемых продукта:

```text
Pipeline version N (pinned)
        ↓
Swarm product slice
        ↓
Pipeline finding + evidence
        ↓
reviewed Pipeline version N+1
        ↓
новый run или явная migration/replay decision
```

Изменения Pipeline не подмешиваются в активный Swarm run через hot reload.

---

## 2. Результат разработки

Первая эксплуатационно полезная версия считается полученной, когда:

1. каждый реализованный shared plane и слой имеет отдельный детальный architecture plan, утверждённый до начала его реализации;
2. deterministic harness хранит полную process memory проекта в SQLite и безопасно управляет событиями, артефактами, проекциями и approvals;
3. S0 и локальные `{Layer}0` работают через contracts и event routing, без прямого handoff между агентами;
4. минимальный nonvisual lifecycle прошёл на committed fixture;
5. новый Swarm прошёл P/R/E, ранний G/H risk slice, A-final/T, один I vertical slice и независимый Q audit;
6. каждый задействованный слой создал реальный артефакт, передал его downstream-потребителю и доказал обработку как normal path, так и defect/revision path;
7. product rollback и Pipeline-version rollback независимо проверены;
8. ограничения и отложенные возможности явно зарегистрированы, а не маскируются как готовность.

Это не означает завершения всей целевой архитектуры. Расширенные события, rosters, сложный replay, budget/cache optimization и полный M добавляются после подтверждённой потребности.

Центральный принцип: **нет зарегистрированного потребителя — нет готовности и нет основания производить artifact как required output**. Compile-time contract называет consumer/terminal policy; runtime readiness требует независимый `consumer_receipt` exact artifact version.

---

## 3. Неподвижные границы

### 3.1 Git и рабочие каталоги

| Объект | Git authority | Что в нём меняется |
|---|---|---|
| Pipeline v2, prompts, contracts, harness, schemas, tests | корневой Git `1.Mistake Not My Baton For A Wand` | только Pipeline artifacts |
| Новый продукт Swarm | `projects/swarm/.git` | product code, tests, product projections и project evidence |
| Runtime memory Swarm | `projects/swarm/.pipeline/pipeline.sqlite3` | не коммитится; связывается с product/pipeline commits через receipts |
| Legacy research snapshot | exact ignored `research/old-swarm/`, не Git authority Pipeline/Swarm | read-only untrusted prior art; доступ только designated research importer |

Корневой Git обязан игнорировать `/projects/` и `/research/old-swarm/`. Операция не выполняется, если repository guard не доказал ожидаемые root, worktree и active commit. Product agents получают только exact `projects/swarm` root; отрицательный exclude legacy-подкаталога не считается изоляцией.

Cross-repository atomic commit не имитируется. Каждый репозиторий получает свой commit и receipt, а связь между ними хранится явно.

### 3.2 Новый и старый Swarm

`projects/swarm` — новый greenfield-продукт. Старый Swarm разрешён только как untrusted research input:

```text
old observation → verified problem/requirement → new owner decision
```

Запрещены:

- копирование старого product code;
- принятие старой архитектуры как baseline;
- перенос решения без provenance, повторной проверки и нового decision ID.

Текущее состояние учитывается явно: внутри ещё не закоммиченного `projects/swarm` находится untracked legacy snapshot `old swarm/` — 12 504 файла, 208 572 020 bytes (~199 MiB), шесть вложенных `.git`, включая `node_modules`. До любого root/product baseline он обязательно физически переносится в exact ignored `research/old-swarm/`; project-local ignore/quarantine внутри product root не является допустимой альтернативой. Перенос требует отдельного human approval и verified relocation receipt, ничего не удаляет и сохраняет snapshot только как read-only research root.

`audit_results.json` и `fix_prompts.md` из snapshot классифицируются как `untrusted_prior_analysis`: designated importer может преобразовать конкретное утверждение только в provenance-bound observation, но ни один файл не становится готовым requirement, decision, prompt fix или фактом. После переноса D0 scanner обязан доказать, что product tree не содержит legacy path, nested `.git`, untracked bulk и неразрешённые runtime/build roots.

### 3.3 Persistence и projections

- SQLite — canonical project memory.
- В Git публикуются только key decision projections в обязательной YAML+MD паре.
- Внешние ссылки используют `artifact_version_id`; hash-profile проверяет payload, но не заменяет identity.
- Структурированные связи хранятся реляционно; canonical JSON TEXT используется для нереляционных structured payload; binary content хранится как SQLite BLOB.
- В Alpha не вводятся CAS/external blob backend или серверная БД.

### 3.4 Оркестрация и полномочия

- S0 маршрутизирует, восстанавливает состояние и организует HITL, но не проектирует продукт и не редактирует содержательные артефакты.
- `{Layer}0` владеет локальным routing/recovery слоя.
- LLM предлагает события и артефакты; deterministic harness валидирует и сохраняет их.
- Прямой agent-to-agent handoff запрещён.
- Machine-readable routing живёт только в `contract.yaml`.

---

## 4. Модель готовности

### 4.1 Статусы deliverable

| Статус | Значение |
|---|---|
| `proposed` | идея описана, но owner disposition отсутствует |
| `architecture_approved` | отдельный детальный layer architecture plan утверждён; реализацию слоя разрешено начать в пределах approved scope |
| `designed` | machine-readable contracts/schemas/tests спроектированы и согласованы с approved layer plan |
| `implemented` | prompts/harness/schema реализованы и проходят локальные checks |
| `fixture_verified` | поведение доказано на committed deterministic fixture |
| `real_project_verified` | слой доказал полный рабочий цикл на новом Swarm |
| `released` | версия опубликована, pinned и имеет release/rollback evidence |

Переходы не выполняются по self-report агента. Каждый переход ссылается на test run, artifact versions, event IDs, approvals и Git commits.

### 4.2 Layer Architecture Gate

До начала разработки каждого слоя обязателен отдельный файл:

```text
new pipeline/architecture/S-layer-plan.md
new pipeline/architecture/P-layer-plan.md
new pipeline/architecture/R-layer-plan.md
new pipeline/architecture/E-layer-plan.md
new pipeline/architecture/G-layer-plan.md
new pipeline/architecture/A-layer-plan.md
new pipeline/architecture/H-layer-plan.md
new pipeline/architecture/T-layer-plan.md
new pipeline/architecture/I-layer-plan.md
new pipeline/architecture/Q-layer-plan.md
new pipeline/architecture/M-layer-plan.md
```

Объединённый документ сразу для нескольких слоёв не заменяет индивидуальные планы. Shared control plane и shared artifact/event plane также получают собственные phase-scoped планы до реализации K0-a и delta-approval перед K0-b.

Каждый layer plan должен с большей детализацией, чем общий архитектурный план, определить:

1. назначение, границы ответственности, non-goals и applicability по project profiles;
2. обязанности локального `{Layer}0` и границу между dispatcher, deterministic harness и workers;
3. внутреннюю state machine слоя, invariants и terminal states;
4. входные события, guards, routing branches, fan-out/barriers и deterministic fast paths;
5. выходные события, subscribers/terminal policy и cross-layer handoff contracts;
6. входные и выходные artifact types, ownership, versioning, lineage и key-decision projections;
7. context/query allowlists, trust classes, provenance и правила защиты от prompt injection;
8. worker roster текущего scope: роль каждого worker, входы, результаты, capabilities и stop conditions;
9. failure taxonomy, blocker/revision ownership, invalidation, minimal replay, recovery и abort semantics;
10. HITL-точки, autonomy tiers и approvals;
11. tools, side effects, security/egress policy и repository boundaries;
12. context budgets, scale/sharding policy и допустимые fallback profiles;
13. downstream consumers и критерии фактического consumption;
14. structural, contract, behavioral, fixture и real-project scenarios;
15. evidence package и критерии `fixture_verified`/`real_project_verified`;
16. migration note по старому pipeline: `source ideas`, `retained`, `rewritten`, `retired`, `new tests`;
17. риски, открытые решения и явно отложенные возможности.

Все 17 разделов обязательны как контрольные категории, но раскрываются только в пределах текущей фазы; неприменимый раздел получает короткое `N/A` с причиной. В начале плана находится `scope_envelope`: phase/package, profiles/scenarios, current workers/routes/artifact types, explicit exclusions, deferred triggers и downstream boundary. Deferred roster описывается только именем, назначением, trigger и стабильным interface — без преждевременного проектирования prompts/internal routes.

Default complexity budget: не более 500 непустых строк, включая таблицы, для layer plan текущего slice и не более 800 для каждого shared-plane plan; auto-generated registry index в лимит не входит. Это не цель заполнения. Превышение разрешает только owner receipt с причиной, почему scope нельзя сузить или разнести на versioned appendices/packages. Approval также фиксирует фактические counts workers/routes/artifact types/scenarios, чтобы scope creep был виден как изменение, а не как рост prose.

План ссылается на canonical schemas/registries и не копирует их. Его approval фиксируется отдельным receipt с plan version/hash, reviewer, dispositions открытых вопросов, complexity budget/factual counts и разрешённым implementation scope.

Review ограничен: initial review может вернуть план автору не более двух раз. После второго revision-return любое содержательное расхождение маршрутизируется owner/HITL, который выбирает `approve with disposition | narrow scope | revise package architecture | block`. Третий автономный author↔reviewer loop запрещён. Повторная проверка в S1/V1/A1/I1/Q1 является delta-review изменившегося scope; неизменные sections сохраняют прежние hashes и не переписываются.

`Layer Architecture Gate` считается пройденным, если:

- план существует именно для одного слоя и прошёл review;
- ответственность слоя не пересекается с другими owners без явного contract;
- у каждого input/output/blocker/revision есть owner и достижимый route;
- определён минимальный roster текущей фазы и честно перечислен deferred roster;
- plan scope и фактический объём укладываются в approved complexity budget либо имеют owner overrun receipt;
- определены tests и evidence, способные опровергнуть архитектурную гипотезу;
- blocker decisions закрыты, approved scope однозначно ограничивает реализацию, а unresolved review после двух возвратов передан owner/HITL.

До этого gate запрещено создавать production prompts/contracts или layer-specific runtime behavior. Разрешены только read-only анализ старого pipeline и явно помеченные disposable spikes, которые не могут попасть в baseline без повторного review. Расширение уже реализованного слоя начинается с новой версии его architecture plan и повторного approval для расширяемого scope.

Это правило применяется just-in-time: план слоя завершается непосредственно перед разработкой этого слоя. Оно не возвращает процесс к написанию всех S/P/R/E/G/A/H/T/I/Q/M планов до Alpha-0.

### 4.3 Definition of Done слоя

Слой получает `real_project_verified`, только если зарегистрирована цепочка:

```text
architecture
  → machine contract
  → prompts + harness support
  → real Swarm artifact
  → exact-version downstream consumer receipt
  → normal-path evidence/audit
  → observed defect ИЛИ predeclared fault injection
  → owner revision/recovery
  → repeated evidence
```

Условия:

1. артефакт принадлежит слою и имеет provenance;
2. downstream действительно прочитал конкретную версию и создал `consumer_receipt`; для terminal Q consumer — независимый owner/release/scope gate;
3. normal path проверен независимо от автора артефакта;
4. defect либо наблюдался естественно, либо сценарий injection был объявлен и зафиксирован до запуска;
5. дефект не фабрикуется задним числом ради прохождения gate;
6. revision вернулась правильному owner через S0 и локальный dispatcher;
7. replay/invalidation не переписали историю;
8. unresolved gaps и downstream impact зарегистрированы.

### 4.4 Architecture hypotheses и measurement

Architecture hypothesis register является canonical versioned artifact в SQLite. Постоянный отдельный YAML-файл для него не создаётся; YAML+MD появляется только у key owner decision, принятого по результатам гипотезы. Запись содержит falsifiable statement, mechanism, owner, заранее определённые metric/falsifier/window/evidence, independent evaluator, status и decision impact.

K0-a обязан сохранить raw telemetry, которую нельзя восстановить задним числом: времена run/invocation/tool/HITL, model/context/usage facts, tool outcomes, events/revisions, artifact sizes и approval/escalation facts. Dashboard и success KPI в K0-a запрещены. N1/Q1 формируют baseline; threshold становится gate только через заранее утверждённую hypothesis/decision с формулой и anti-gaming interpretation.

Минимальные семейства будущих метрик:

- process: active/waiting time, invocations/retries/revision cycles, context и cost facts;
- quality: downstream/Q findings, escaped defects, decision churn, gaps и rollback outcomes;
- autonomy: auto/run-authorized/HITL actions, approvals/escalations и human waiting time.

### 4.5 Правило чередования

Работа идёт пакетами:

```text
design package x
  → approve detailed layer architecture x
  → implement/test package x
  → disposition findings
  → design package x+1
```

Нельзя сначала написать полные планы и prompts всех слоёв, а затем впервые запустить harness.

---

## 5. Потоки работ

| Поток | Ответственность | Основные результаты |
|---|---|---|
| `W0 Governance` | decisions, scope, release gates | owner dispositions, version pins, approvals, release/rollback receipts |
| `W1 Kernel` | deterministic control/artifact/event plane | CLI/library, SQLite migrations, registry compiler, event delivery, recovery, guards |
| `W2 Layers` | отдельный detailed architecture plan и только затем contracts/implementation каждого слоя | approved `{Layer}-layer-plan.md`, `{Layer}0`, workers, schemas, fixtures, migration notes из old pipeline |
| `W3 Verification` | independent tests и evidence | structural/contract/behavioral/E2E suites, fault injection, audit findings |
| `W4 Swarm Product` | greenfield product lifecycle | P/R/E/G/A/H/T/I/Q artifacts и работающий vertical slice |
| `W5 Pipeline Improvement` | controlled co-evolution | Pipeline findings, red→green fixes, canary, approvals, new pinned versions |

Один work item может затрагивать несколько потоков, но обязан иметь одного owner и один exit gate. Architecture-plan work item и implementation work item слоя всегда разделены, а второй зависит от approval receipt первого.

---

## 6. Карта релизных фаз

| Фаза | Пакет архитектуры | Главный результат | Среда проверки | Gate |
|---|---|---|---|---|
| `D0` Decision/repository baseline | §22.1 | архитектура разрешена; legacy research изолирован; product root clean | документы + три exact roots | blocker dispositions + relocation/hygiene receipts |
| `K0-a` Bootstrap proof | 2.0a/3.0a | один atomic artifact/event cycle через S0/Layer0 | disposable fixture | F00; product/external capabilities отсутствуют |
| `K0-b` Operational Alpha-0 | 2.0b/3.0b | recovery/safety-ready minimal control plane | committed fixture | F01–F05/F07/F09/F13 проходят |
| `N1` Nonvisual / Alpha-1 | 2.1/3.1 | узкий end-to-end lifecycle | nonvisual fixture | F11 + independent Q evidence |
| `S1` Swarm discovery | 2.2/3.2 | новый Swarm определён без legacy inheritance | реальный Swarm | S01–S04 |
| `V1` Visual/Elm risk | 2.3/3.3 | visual quality и structural binding совместимы | fixture + Swarm | F12 + S05–S07; иначе declared Plan B и phase blocked |
| `A1` Architecture/tasks | 2.4/3.4 | реализация полностью трассируема | реальный Swarm | S08 |
| `I1` Product slice | 2.5/3.5 | работающий Swarm vertical slice | реальный Swarm | S09 + rollback evidence |
| `Q1` Independent audit | 2.6/3.6 | качество проверено независимо | реальный Swarm | S10 + finding dispositions |
| `X1` Expansion | 2.7/3.7 | доказанные runtime-потребности закрыты | fixture + Swarm | применимые S11–S17 |
| `M1` Full meta-layer | 2.8/3.8 | безопасное self-improvement | Pipeline canary | red→green + two HITL approvals |

Фазы — порядок доказательств, а не календарные сроки. Следующая фаза начинается только после disposition findings предыдущей.

---

Ниже каждая фаза раскрыта как отдельный пакет с собственным exit gate.

## 7.1 D0 — Decision baseline и repository baseline

### Цель

Устранить неоднозначности, которые могут изменить kernel, структуру данных или последовательность пилота.

### Работы

1. Для V2-D01…V2-D35 зафиксировать `accepted | modified | explicitly_deferred`, owner и rationale.
2. Запретить defer для решений, блокирующих K0-a.
3. Утвердить обязательный состав layer architecture plan, scope/complexity budgets, два review-return rounds и формат architecture approval receipt из §4.2.
4. Получить human approval exact relocation `projects/swarm/old swarm/` → `research/old-swarm/`; до переноса добавить и проверить root-ignore rules `/projects/` и `/research/old-swarm/`.
5. Физически перенести snapshot без удаления и создать verified relocation receipt: canonical source/destination, до/после file/byte counts, nested Git inventory, source absence и destination read-only policy.
6. Выполнить product-tree hygiene scan `projects/swarm`: только root `.git`, нет nested `.git`, untracked bulk, legacy/runtime/build roots; создать project-local `.gitignore` и baseline allowlist.
7. Зафиксировать exact prompt/product/research roots, capability boundaries и worktree policy.
8. Определить identity первой Pipeline development version и правила dirty development mode.
9. Добавить в один root-Pipeline baseline commit:
   - `.gitignore`;
   - architecture plan;
   - development plan;
   - актуальный review/disposition record;
   - relocation/product-tree hygiene receipts без содержимого snapshot.
10. Создать маленький отдельный committed fixture project; не использовать Swarm как fault-injection fixture.

### Exit gate

- blocker decisions закрыты;
- Layer Architecture Gate принят как обязательная зависимость реализации каждого слоя;
- legacy snapshot физически отсутствует в `projects/swarm`, а exact ignored research root не входит в product-agent capabilities;
- product tree прошёл symmetric hygiene scan и не содержит nested Git/untracked bulk; project-local ignore существует до product baseline;
- root baseline committed и может быть pinned;
- fixture baseline воспроизводим;
- ни один product artifact/legacy payload не попал в root Git, а ни один Pipeline artifact не попал в product Git.

### Не входит

- product architecture Swarm;
- полный roster слоёв;
- публикация release Pipeline v2.

---

## 7.2 K0-a — Bootstrap proof

### Цель

Как можно раньше доказать главный тезис: basic CLI проводит один pinned route через S0/Layer0 и атомарно сохраняет artifact version вместе с событием.

### Жёсткая граница

K0-a работает только на disposable committed fixture. Разрешена запись лишь в exact fixture SQLite/runtime temp paths; fixture source tree, product/research roots, network, external mutation и произвольные tool side effects недоступны. Его результат не является Alpha-0 и не разрешает запуск Pipeline на Swarm.

### Deliverables

1. Phase-scoped approved `shared-control-plane.md`, `shared-artifact-and-event-plane.md` и `S-layer-plan.md` только для bootstrap scope.
2. Minimal forward SQLite migration и constraints для runs, invocations, artifact/version и events.
3. Atomic artifact+event transaction.
4. Minimal contract compiler/loader для одного pinned fixture route и событий `command.received`, `run.started`, `artifact.version_created`, `handoff.ready`, `run.completed`.
5. S0, один synthetic `{Layer}0` и один deterministic fixture worker.
6. Basic CLI: initialize, run и inspect.
7. Exact Pipeline/fixture root check и deny-all для остальных capabilities.
8. Raw telemetry fields: timestamps/durations, invocation/model/context/usage facts, event counts и artifact size; без dashboard/KPI.

### Обязательная проверка

`F00`: `command → S0 → Layer0/worker → atomic artifact version + event → terminal state`; CLI читает artifact/event/telemetry обратно из SQLite.

### Exit gate

- F00 проходит из clean fixture baseline;
- artifact и event ссылаются друг на друга и на pinned contract/run;
- отсутствуют product/external side effects;
- findings имеют disposition и approved K0-b delta scope.

### Не входит

- projections/YAML+MD outbox;
- crash reconciliation/resume/abort;
- полный Alpha event profile;
- production repository/tool/egress guards;
- approvals, replay, product run и release claims.

---

## 7.3 K0-b — Operational hardening и Alpha-0

### Цель

Превратить доказанный bootstrap cycle в минимальный recovery/safety-ready control plane до содержательных prompt-систем.

### Deliverables

1. Delta-approved shared-plane/S plans для operational scope.
2. Полные Alpha-0 forward migrations, schema/version binding, verified backup и integrity check.
3. Registry compiler для minimal Alpha event/subscription/routing profile.
4. Transactional projection outbox, YAML+MD pair и crash reconciliation.
5. Deterministic nominal fast path и Layer0 fallback для non-nominal state.
6. Repository/worktree, path/symlink, tool/egress/secret/process guards.
7. Graceful abort, recovery checkpoints и compatibility/rollback separation.
8. Structural, migration, contract и scenario test harness.

### Обязательные проверки

- F01–F05, F07, F09 и базовая часть F13;
- undeclared event отклоняется;
- routing compiler воспроизводим на одинаковом commit;
- crash до/после DB commit не создаёт half-published YAML/MD pair;
- direct handoff не имеет исполнимого route;
- чужой Git root приводит к fail-closed;
- выбор прежней Pipeline version не меняет product Git.

### Exit gate

Alpha-0 отчёт содержит pinned Pipeline/schema versions, test evidence, finding dispositions, явно отложенные runtime families и разрешение перейти к N1.

### Не входит

- полный M;
- lease fleet/scheduler, сложный replay, budget optimizer и cache;
- все layer-specific события;
- полный G/H.

---

## 7.4 N1 — Nonvisual fixture и Alpha-1

### Цель

Доказать, что kernel переносит не только synthetic handoff, но и узкий содержательный lifecycle.

### Минимальный package

1. Отдельные детальные и утверждённые `P-layer-plan.md`, `R-layer-plan.md`, `A-layer-plan.md`, `T-layer-plan.md`, `I-layer-plan.md` и `Q-layer-plan.md` для ограниченного nonvisual scope; Q использует только Q-Alpha capabilities.
2. Только после их approval — соответствующие machine contracts, prompts, layer-specific schemas/events и fixture tests.
3. Один небольшой nonvisual bugfix fixture с известными исходными условиями.
4. Key decision YAML+MD projections и typed traceability P→R→A→T→I→Q.
5. Revision route Q→S0→owner `{Layer}0`→minimal replay.
6. Migration notes каждого слоя по использованным идеям старого пайплайна: retained/rewritten/retired/new tests.

### Обязательные проверки

- F11 проходит без ручного обхода contracts/events;
- Q-Alpha независимо проверяет requirements coverage, artifact lineage, code/test evidence и rollback evidence, не принимая I self-report;
- permanent gap терминален для reachability, но блокирует release до human risk/scope decision;
- downstream consumption каждой версии доказано exact-version `consumer_receipt`; terminal Q result потреблён fixture acceptance gate;
- один predeclared defect injection проходит корректный revision cycle.

### Exit gate

- P/R/A/T/I/Q имеют минимум `fixture_verified` для узкого профиля;
- обнаруженные проблемы kernel исправлены red→green;
- утверждён package S1, но ещё не полный roster оставшихся слоёв.

---

## 7.5 S1 — Greenfield discovery нового Swarm

### Цель

Получить проверяемое определение нового продукта, не наследуя код и архитектуру старого.

### Работы

1. Утвердить отдельный `E-layer-plan.md`; если Swarm расширяет scope уже созданных P/R/A plans — сначала выпустить и утвердить их новые версии.
2. Опубликовать и contract-test-ить `registry/ui-architecture-policy/elm-applicability.yaml`: predicates, input evidence, outcomes, A8 route и staleness rules.
3. Только после layer-plan approvals реализовать недостающие E/P/R/A contracts/prompts текущего scope.
4. Проверить D0 relocation/product-tree receipts и только после этого создать осознанный greenfield baseline в отдельном Git `projects/swarm`.
5. Сформировать observation manifest старого Swarm из явно выбранных файлов отдельного read-only research root:
   - source/provenance;
   - наблюдаемая проблема или урок;
   - trust class;
   - запрет использования как product instruction.
6. P публикует profile, intent, stakeholders, success criteria, constraints, risks и scope boundaries.
7. R превращает только проверенные observations/intent в requirements и acceptance outcomes.
8. E фиксирует user journeys, adoption/usability risks и surface contracts.
9. A0 принимает только platform predecision, необходимое для G/H; это не A-final, а Elm applicability outcome вычисляется по pinned registry policy с evaluation trace.
10. Для stateful interactive surfaces Elm назначается стандартным UI profile; исключение требует A8 decision.

### Обязательные проверки

- S01–S04;
- structural scan подтверждает отсутствие legacy snapshot/nested Git в product root и не находит tracked/imported old code/architecture;
- каждое старое observation, повлиявшее на requirement, имеет provenance chain;
- ни один product decision не обоснован только существованием старой реализации;
- A0 Elm outcome воспроизводится по policy version/hash и machine-readable input evidence;
- Pipeline run pinned и не меняется во время S1.

### Exit gate

- P/R/E/A0 artifacts приняты;
- E surface inventory достаточен для раннего visual risk slice;
- unresolved product choices не маскируются архитектурными предположениями.

---

## 7.6 V1 — Ранний G/H visual/Elm risk slice

### Цель

Проверить самую рискованную способность: создать сильное графическое решение и затем связать его с продуктовой структурой, не заставляя одного LLM одновременно решать обе задачи.

### Порядок

```text
E surface contracts + A0 platform predecision
             ├─→ G creative lane (без component IDs/coverage)
             └─→ G structural lane (без visual generations)
                          ↓
                 mapping/reconciliation
                          ↓
                    locked visual
                          ↓
                       A draft
                          ↓
                     H Elm handoff
```

Creative и structural lanes независимы до mapping. Они не выполняются как `Creative → Mapping → Structural`.

### Deliverables

1. Отдельные детальные и утверждённые `G-layer-plan.md` и `H-layer-plan.md`; применимые изменения A сначала вносятся в новую approved version `A-layer-plan.md`.
2. Только после approvals — минимальные G0/G creative/G structural/mapping/lock contracts и prompts.
3. Immutable visual generation/version и mapping lineage.
4. A draft, ограниченный решениями, нужными H.
5. H contracts для Model/Msg/update/view, state/transition coverage и compiler feedback.
6. Conflict route H→A; третий повтор ведёт A8/HITL, а не в бесконечный loop.
7. Независимый visual/structural/evidence review.

### Обязательные проверки

- сначала F12, затем S05–S07;
- creative context не содержит structural identifiers;
- structural context не содержит visual generation;
- mapping не меняет locked visual;
- visual revision инвалидирует mapping, но не structural manifest;
- E revision инвалидирует обе ветви;
- injected `interaction_model_failure` при приемлемых visual/structure возвращается E0 и пересчитывает affected G/H/A scope;
- H потребляет принятую mapping/version, а не реконструирует дизайн по описанию.

### Failure route / Plan B

Провал F12 или S05–S07 сначала классифицируется как `creative_quality | structural_contract | mapping | interaction_model | A0_platform | H_elm`. `interaction_model_failure` означает приемлемые visual/formal artifacts при плохом user flow/state/feedback; primary owner — E0, а исправленный interaction contract инвалидирует affected G/H/A scope. Failure не превращается автоматически в generic blocker и не разрешает ослабить evidence.

Owner выбирает один из четырёх routes:

1. изменить и повторно утвердить применимые E/G/H/A layer plans для точной причины провала, затем повторить V1;
2. сузить первую Swarm surface через явное scope decision и повторить V1 для оставшегося scope — обязательную user-facing capability нельзя удалить только ради прохождения gate;
3. применить A8 исключительно при доказанном Elm applicability/feasibility conflict; A8 не является исключением из visual quality, interaction model, mapping или presentation coverage;
4. остановить product track и провести disposable research spike вне baseline, после чего вернуться к новой architecture-plan version.

Переход к A-final/T/I возможен только после успешного повторного V1 либо human scope decision, действительно удаляющего проблемную surface из принятого product scope. Если эта surface является core product capability, доступен только route 1 или 4.

### Exit gate

- G/H имеют `real_project_verified` для выбранной Swarm surface; при неуспехе сохранены classification и выбранный Plan B route, а phase остаётся незавершённой;
- A-final/T/I запрещены до успешного rerun либо допустимого human scope decision;
- качество visual solution и полнота structural mapping оценены раздельно.

### Не входит

- полный G roster для всех surface types;
- полный H для всех экранов;
- массовая генерация UI.

---

## 7.7 A1 — Финальная архитектура и task graph

### Цель

Собрать реализуемую архитектуру Swarm после проверки product, adoption, visual и Elm constraints.

### Deliverables

1. Утверждённые версии `A-layer-plan.md` и `T-layer-plan.md`, покрывающие final architecture/task scope; если scope не изменился относительно N1/V1, сохраняются прежние plan hashes и фиксируется applicability receipt.
2. A-final: system/data/security/deployment architecture и explicit trade-offs.
3. H-final handoff либо approved A8 exception для каждой применимой surface.
4. T task graph с owners, dependencies, acceptance/evidence plan и presentation coverage.
5. Traceability от intent/requirements/E/G/H/A до задач.
6. Rollback и migration plan первого product slice.

### Обязательные проверки

- S08;
- downstream versions pinned;
- UI-enabled scope не имеет нулевого presentation coverage;
- неизвестный язык получает enforcement profile или explicit advisory-only decision до I;
- P8/P20 остаются blocking во всех profiles.

### Exit gate

Первый vertical slice можно реализовать без догадок о product behavior, UI state, evidence или rollback.

---

## 7.8 I1 — Первый работающий Swarm vertical slice

### Цель

Проверить архитектуру реальной реализацией, а не считать документ доказательством.

### Работы

1. Подтвердить применимость approved `I-layer-plan.md` к первому Swarm slice; любое расширение roster/capabilities сначала вносится в новую plan version.
2. I0 строит roster из pinned execution recipe.
3. I выполняет только задачи первого вертикального среза.
4. Код, tests и product changes коммитятся только в Git Swarm.
5. Pipeline prompt/contract fixes коммитятся отдельно в root Git и применяются лишь через новую pinned version.
6. Собираются machine evidence, human-visible evidence и lineage к task/requirement.
7. Проводится product rollback drill без изменения Pipeline version.

### Обязательные проверки

- S09;
- Elm compiler/tests и применимые security/quality gates;
- product rollback восстанавливает ожидаемый product state;
- Pipeline DB/history остаются audit-complete;
- finding в Pipeline не исправляется внутри активного run.

### Exit gate

Есть работающий, проверяемый и откатываемый slice нового Swarm. Это product increment, а не завершённый Swarm.

---

## 7.9 Q1 — Первый независимый аудит

### Цель

Проверить весь срез из исходных artifacts/evidence и выявить слепые зоны Pipeline.

### Работы

1. Подтвердить approved `Q-layer-plan.md` ровно для Q-Alpha scope; расширение capabilities сначала оформляется новой plan version в X1.
2. Независимо проверить четыре domain: requirements/acceptance coverage, artifact/version lineage, code+test evidence и rollback evidence.
3. Q получает разрешённые source snapshots/evidence, но не принимает I conclusions как primary evidence.
4. Finding классифицируется как product defect, Pipeline defect, accepted risk, permanent gap или invalid finding.
5. Product defect возвращается owner-слою через S0.
6. Pipeline defect создаёт отдельный W5 work item и red test; активный run не переписывается.
7. Independent owner/slice-acceptance gate потребляет exact Q finding-set version и создаёт terminal `consumer_receipt`.

### Обязательные проверки

- S10;
- хотя бы один observed defect либо заранее объявленный injected defect прошёл revision/recovery;
- если дефект уверенно исключён, сохранены negative evidence и audit method;
- все findings имеют owner/disposition;
- slice acceptance не принимает `permanent_gap` без human accepted-risk/scope decision.

### Exit gate

- первый реальный P/R/E/G/A/H/T/I/Q cycle замкнут;
- статусы слоёв обновлены по evidence;
- выбран только следующий минимальный expansion package.

### Не входит

- Q8/Q10 documentation publication;
- полный security/performance audit;
- release governance полного продукта.

---

## 7.10 X1 — Incremental expansion

### Цель

Добавлять target-архитектуру по доказанной потребности, а не по полноте списка.

### Возможные packages

1. lease/timeout/late-result fencing — когда появляется concurrent/long-running execution;
2. advanced replay/invalidation — когда минимального replay недостаточно;
3. budget events и hard-stop — после измеримого cost pressure;
4. cache semantics — после повторяемой expensive deterministic work;
5. additional layer events/agents — при появлении нового domain route;
6. scale/sharding — при фактическом context overflow;
7. BLOB optimization или иной backend — только после DB/backup measurements;
8. расширенные security/adversarial сценарии;
9. полные G/H rosters для новых surface types;
10. расширение Q до security/performance/documentation/release capabilities;
11. metric aggregations/dashboard и normative thresholds только после N1/Q1 baseline и approved hypotheses.

Каждый package обязан иметь triggering evidence и сначала обновить/утвердить architecture plan затронутого слоя. Только затем создаются новый/изменённый contract, forward migration при необходимости, tests, compatibility statement и rollback plan.

### Обязательные проверки

Применимые S11–S17, F06/F08/F10/F13 compatibility и соответствующие foundation/behavioral tests.

### Exit gate

Функция входит в released profile только после fixture evidence и, если она влияет на product semantics, реального Swarm usage.

---

## 7.11 M1 — Полный meta-layer

### Цель

Автоматизировать обнаружение дефектов Pipeline, сохранив человеческий контроль над изменением и публикацией.

### Предварительные условия

- kernel и хотя бы один реальный lifecycle стабильны;
- есть реальные Pipeline findings и regression corpus;
- version pinning, rollback и compatibility доказаны;
- отдельный детальный `M-layer-plan.md` прошёл Layer Architecture Gate;
- M не является способом обойти owner/change-control.

### Цикл

```text
incident/finding
  → diagnosis
  → failing regression test
  → HITL approval to edit
  → isolated Pipeline change
  → green tests + canary
  → separate HITL approval to publish
  → new pinned Pipeline version
```

До M1 тот же цикл выполняется вручную через W5. Meta hooks присутствуют в kernel, но не дают M права автоматически редактировать или публиковать Pipeline.

### Exit gate

- ни один self-change не применён к active run;
- два approvals различимы и проверяемы;
- canary и rollback evidence сохранены;
- false-positive/false-negative behavior измеряется.

---

## 8. Расширение событий по фазам

| Момент | Event scope |
|---|---|
| K0-a | только пять bootstrap route events; остальные ошибки — internal typed terminal state |
| K0-b | остальной minimal Alpha profile и correctness/security errors |
| N1 | finding/coverage/revision semantics, нужные F11/Q-Alpha; hypothesis records используют generic artifact events |
| S1/V1 | только P/R/E/G/H domain events, без общего «про запас» catalog implementation |
| I1/Q1 | task/execution/evidence/audit events первого slice |
| X1 | lease, retry, budget, cache, deferred, scale и replay families по triggering scenario |
| M1 | полный meta diagnosis/change/canary/publish lifecycle |

Новый event type принимается, только если указаны producer, subscribers/terminal policy, schema version, owner, replay semantics и tests. Registry расширяется forward-only; неизвестное событие отклоняется fail-closed.

---

## 9. Co-evolution и обработка дефектов

### 9.1 Классификация finding

| Класс | Где исправляется | Что остаётся pinned |
|---|---|---|
| Product defect | Git Swarm, через owner layer | Pipeline version текущего run |
| Prompt/contract defect | root Pipeline Git, новый red→green change | product commit и текущий run history |
| Harness/schema defect | root Pipeline Git + compatibility/migration plan | product Git; старая DB до approved migration |
| Invalid finding | нигде; сохраняется rationale/evidence | обе версии |
| Accepted risk/scope decision | human decision projection | обе версии и исходный gap |

### 9.2 Два rollback domain

Product rollback:

- работает с product Git/config/data/deployment;
- не меняет Pipeline commit и contracts;
- сохраняет event/evidence history операции.

Pipeline-version rollback:

- выбирает ранее опубликованный Pipeline commit для нового run либо выполняет explicit approved migration;
- не выполняет `git reset` общего checkout как runtime-механику;
- не меняет product Git;
- fail-closed при несовместимой SQLite schema.

---

## 10. Test strategy и evidence package

### 10.1 Уровни проверки

1. **Structural:** наличие/уникальность IDs, отсутствие schema duplication, Git/path boundaries.
2. **Contract:** producer/consumer compatibility, routing reachability, ownership, profiles, invalidation/recovery.
3. **Foundation:** транзакции, migrations, backups, projections, abort, security guards.
4. **Behavioral:** свойства LLM-результата, adversarial inputs, k/n policy.
5. **Fixture E2E:** F00 bootstrap отдельно; затем детерминированные F01–F13 operational/content scenarios.
6. **Real-project E2E:** S01–S17 по мере фаз.
7. **Independent audit:** Q и release gate не зависят от self-report исполняющего слоя.

### 10.2 Evidence package каждого gate

Каждый gate публикует:

- phase/scenario ID;
- pinned Pipeline commit и schema/registry versions;
- project commit/snapshot;
- run/invocation/event/artifact IDs;
- test commands и результаты;
- approvals и policy decisions;
- findings/dispositions;
- rollback/restore evidence, если применимо;
- consumer receipts, raw telemetry refs и затронутые architecture hypotheses;
- известные gaps и следующий разрешённый package.

### 10.3 Stop conditions

Фаза останавливается и не маскируется ручным обходом, если:

- repository identity не доказана;
- contract/schema несовместимы;
- событие или side effect не разрешены policy;
- отсутствует owner/handler blocker или revision;
- требуемый HITL receipt отсутствует/невалиден;
- provenance обязательного input потерян;
- active run пытается загрузить другую Pipeline version;
- projection расходится с canonical DB и reconciliation не завершён.

---

## 11. Управление work items

Минимальная запись задачи содержит:

```yaml
work_item_id: <stable-id>
phase: <D0|K0a|K0b|N1|S1|V1|A1|I1|Q1|X1|M1>
owner: <single-owner>
dependencies: []
architecture_plan_ref: <path-or-null>
architecture_plan_hash: <hash-or-null>
architecture_approval_ref: <receipt-or-null>
inputs: []
deliverables: []
tests: []
exit_gate: <gate-id>
status: <proposed|architecture_approved|designed|implemented|fixture_verified|real_project_verified|released>
pipeline_commit: <pin-or-null>
project_commit: <pin-or-null>
evidence_refs: []
consumer_receipt_refs: []
hypothesis_refs: []
metric_fact_refs: []
blockers: []
```

Пока K0-a не готов, backlog может храниться в versioned YAML+MD decision projection. K0-a создаёт первый authoritative SQLite state; после K0-b он становится normal operational execution state, а Git-проекция остаётся человекочитаемым срезом ключевых решений.

---

## 12. Первый исполняемый backlog

| Порядок | ID | Работа | Зависимость | Gate |
|---:|---|---|---|---|
| 1 | `D0-01` | disposition V2-D01…D35 | — | Decision baseline |
| 2 | `D0-02` | утвердить bounded layer-plan rubric и architecture approval receipt | D0-01 | Layer Architecture Gate |
| 3 | `D0-03` | approve relocation target + добавить/проверить root ignore rules | D0-01 | relocation prepared |
| 4 | `D0-04` | verified physical move + product-tree hygiene + project-local ignore | D0-03 | clean product root |
| 5 | `D0-05` | commit root baseline: ignore + plans + review/relocation receipts | D0-02/D0-04 | pinnable root |
| 6 | `D0-06` | создать committed fixture Git и expected-root manifest | D0-05 | fixture baseline |
| 7 | `K0a-00` | phase-scoped plans shared control/artifact-event planes и S bootstrap scope | D0 | architecture approvals |
| 8 | `K0a-01` | minimal SQLite + atomic artifact/event + raw telemetry schema | K0a-00 | schema review |
| 9 | `K0a-02` | one pinned contract + S0/Layer0/fixture worker + basic CLI | K0a-01 | contract/root-boundary tests |
| 10 | `K0a-03` | выполнить F00 и disposition findings | K0a-02 | bootstrap proof |
| 11 | `K0b-00` | delta-approve shared/S plans для operational scope | K0a-03 | architecture approvals |
| 12 | `K0b-01` | Alpha migrations + registry compiler + remaining minimal events | K0b-00 | migration/contract tests |
| 13 | `K0b-02` | projection outbox + crash recovery/reconciliation | K0b-01 | foundation tests |
| 14 | `K0b-03` | repository/tool/egress guards + abort/compatibility | K0b-00/K0b-01 | security/recovery tests |
| 15 | `K0b-04` | F01–F05/F07/F09/F13 + Alpha-0 dispositions | K0b-02/K0b-03 | Alpha-0 |
| 16 | `N1-00` | отдельные detailed P/R/A/T/I/Q-Alpha layer plans и approvals | K0-b | architecture approvals |
| 17 | `N1-01` | contracts/prompts/schemas текущего P/R/A/T/I/Q-Alpha scope | N1-00 | contract review |
| 18 | `N1-02` | F11 lifecycle + Q-Alpha + revision injection | N1-01 | Alpha-1 |
| 19 | `S1-00` | detailed E plan + P/R/A plan revisions + Elm applicability registry | N1 | architecture/policy approvals |
| 20 | `S1-01` | validate D0 receipts + greenfield baseline + provenance observation manifest | S1-00/D0-04 | S01 |
| 21 | `S1-02` | P/R/E/A0 реального Swarm | S1-00/S1-01 | S02–S04 |
| 22 | `V1-00` | отдельные detailed G/H plans + применимые E/A-plan revisions | S1-02 | architecture approvals |
| 23 | `V1-01` | минимальные G/H contracts/prompts + F12 | V1-00 | visual fixture |
| 24 | `V1-02` | G/A-draft/H на Swarm; включая interaction-model test и Plan B | V1-01 | S05–S07 |
| 25 | `A1-00` | подтвердить/обновить approved A/T plan versions для final scope | V1 success/scope decision | architecture applicability |
| 26 | `A1-01` | A-final + T + presentation coverage | A1-00 | S08 |
| 27 | `I1-00` | подтвердить/обновить approved I plan для первого slice | A1 | architecture applicability |
| 28 | `I1-01` | первый Swarm vertical slice + rollback | I1-00 | S09 |
| 29 | `Q1-00` | подтвердить Q-Alpha plan для четырёх independent checks | I1 | architecture applicability |
| 30 | `Q1-01` | Q-Alpha audit + terminal consumer receipt + revision cycle | Q1-00 | S10 |
| 31 | `X1-*` | approved layer-plan revision → evidence-triggered expansion package | Q1 | S11–S17 |
| 32 | `M1-00` | отдельный detailed M plan и approval | stable X1 subset | architecture approval |
| 33 | `M1-01` | full controlled meta-layer | M1-00 | M gate |

Параллелить можно только работы без общей write ownership. Parallel execution не отменяет barrier и общий phase gate.

---

## 13. Definition of Done плана разработки

Этот план можно перевести из draft в active baseline, когда:

1. owner подтвердил или изменил V2-D01…V2-D35;
2. IDs фаз, gate mapping и greenfield policy Swarm приняты;
3. Layer Architecture Gate, обязательный состав индивидуального плана и approval receipt приняты;
4. выбран формат decision/review record;
5. D0 backlog получил owners;
6. legacy snapshot физически изолирован, product tree clean, а relocation/hygiene receipts проверены;
7. root baseline committed и pinned;
8. первый architecture work item K0a-00 может быть начат без скрытого продуктового решения; K0-a implementation остаётся заблокированным до его approval.

Любое изменение порядка, которое переносит G/H после A-final/T/I для UI-enabled Swarm, разрешает hot reload Pipeline, объединяет два Git или делает полный M prerequisite первого runtime, считается архитектурным изменением и требует owner disposition.
