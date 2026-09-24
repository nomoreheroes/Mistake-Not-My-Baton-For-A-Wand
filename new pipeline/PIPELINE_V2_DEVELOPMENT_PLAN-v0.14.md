# Pipeline v2 — план разработки

**Версия:** 0.14
**Дата:** 2026-09-24
**Статус:** owner-approved documentation successor; implementation и runtime authority отсутствуют  
**Архитектурный источник:** `PIPELINE_V2_ARCHITECTURE_PLAN.md` v0.16

**Изменения 0.2:** введён обязательный `Layer Architecture Gate`: каждый слой, включая S, получает собственный детальный архитектурный план и approval до разработки его contracts, prompts и layer-specific runtime. Планы создаются just-in-time перед соответствующим слоем, а не все сразу до первого запуска kernel.

**Изменения 0.3:** задача физической изоляции legacy snapshot старого Swarm перенесена из S1 в обязательные D0 relocation/product-tree gates без ignore-only fallback; Layer Architecture Gate получил phase scope budget и bounded review; V1 — заранее определённый failure route; Elm applicability — machine-readable registry authority. D0 work-item IDs перенумерованы в фактическом порядке исполнения.

**Изменения 0.4:** K0 разделён на fixture-only K0-a bootstrap proof и K0-b operational hardening/Alpha-0; добавлены `interaction_model_failure` с owner E0, SQLite architecture hypothesis register, raw telemetry с отложенными KPI, явный Q-Alpha и центральный exact-version consumer-proof gate. На этой revision decision catalog охватывал V2-D01…D35.

**Изменения 0.5:** добавлен общий `Creative Dialogue Protocol` для творческих HITL-сессий: owner-first triad moderator/critical challenger/co-creator, независимый fan-out, explicit proposal dispositions и отдельный compiler. P публикует owner-approved Idea Note; E использует тот же протокол для experience intent. Добавлены dialogue policy/events, gate F14, измеряемая architecture hypothesis и V2-D36.

**Изменения 0.6:** устранены ownership/readiness и phase-gate противоречия: A1/Q7-Alpha получили содержательное владение, H verification перенесён к фактическому A/T consumption, F10/S14 выполняются до untrusted import, Alpha events получили terminal policies, а V1 — обязательный applicable asset lane. Добавлены F15 для real-LLM dispatcher hypothesis, reproducible fixture spec, tiered complexity/invocation/human budgets, Q independence profile, pre-M F06 boundary, Core-6 fallback и V2-D37…V2-D39.

**Изменения 0.7:** добавлена per-layer readiness coverage matrix; F13 разделён на kernel/DB и product rollback scenarios; phase A1 переименована в AT1; S14 отделяет poisoned fixture от первого real legacy import; program decisions разведены между K0-b и N1. Для D0/K0-a определён manual/reference budget bootstrap, а с N1 — обязательный compiler gate. Phase/release recovery привязан к versioned backup вне Git и key gate decision projection.

**Изменения 0.8:** owner выбрал forensic reproducibility вместо external-only backup: clean full SQLite checkpoint track-ится в project Git, active DB/WAL остаются runtime-only. Foundation получил Replay Point Contract, exact agent context/worktree/tool/environment capture, deterministic forensic replay и отдельный stochastic re-execution. F13a теперь требует clone-only restore, а S17 измеряет checkpoint/Git growth до усложнения storage.

**Изменения 0.9:** Q primary snapshot получил fail-closed `.pipeline/` exclusion; replay points отделены от bounded checkpoint publications с K0-b cost projection и D0 thresholds/migration trigger. Worker/Q worktrees используют sparse exclusion checkpoint; Creative Dialogue получил topic/session caps. D0 теперь оценивает порядок полного route до V2-D01, а Bootstrap DoD прямо требует real-LLM Layer0/worker.

**Изменения 0.10:** Layer Architecture Gate получил обязательный `binary_payload_budget` для G, Q runtime evidence и любого иного binary-producing scope. План объявляет count/per-item/aggregate/publication bounds, pin-ит D0 forecast и до реализации закрывает любое расхождение через owner route §9.5.1; V1-00 и Q1-00 делают это исполняемым gate.

**Изменения 0.11:** D0-01 forecast исправлен по независимому review: design-time plan/review calls входят в package envelopes, checkpoint/publication/pack numbers выводятся из объявленных формул, hard-stop делает downstream-фазы условными. D0-02 теперь pin-ит checkpoint policy и approval-envelope schema, разделяет machine checks и reviewer judgment и запрещает автору любой версии плана выступать независимым reviewer следующей версии.

**Изменения 0.12:** повторный review устранил оставшиеся исполняемые расхождения: plan-production и runtime call scopes считаются отдельно, design invocations пишутся в Pipeline-Git ledger, budget packages получают unique IDs, checkpoint forecast разделён по project DB chains и выводит window publications из всех replay boundaries. Binary plan fields теперь включают mean, policy maximum aggregate и fail-closed runtime aggregate limit; receipts pin-ят canonical hash profile.

**Изменения 0.13:** findings третьего аудита приняты как owner-disposition inputs, а не как запрещённый третий review-return. Baseline расширен до полного hash-reachable governance graph; human budgets перенесены на package scope; binary budget ссылается на единый 12-полевой D0-02 authority; schema projections, reviewer independence и K0-a pre-publisher exemption сделаны исполняемыми.

**Изменения 0.14:** обновлённый legacy Pipeline принят только как immutable versioned prior-art overlay, а не как mutable authority или runtime dependency. Для 21 изменённого source path введены manifest и единственная applicability disposition: применимые repository/tool/hash guards входят в будущий K0b-03 scope без переноса legacy prompt/runtime, dispatcher/toolchain/oracle/attestation findings маршрутизируются в K0b-04, а I/J layer contract changes — в обязательную N1-00 migration matrix. До любого implementation scope freeze требуется отдельный review этого delta; state, gates и завершённые K0a/K0b-01/K0b-02 evidence не меняются ретроактивно.

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
5. новый Swarm получил owner-approved Idea Note через проверенный Creative Dialogue Protocol и прошёл P/R/E, ранний G/H risk slice, A-final/T, один I vertical slice и независимый Q audit;
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
| Runtime memory Swarm | active `.pipeline/runtime/pipeline.sqlite3` + tracked `.pipeline/history/pipeline-checkpoint.sqlite3` | active DB/WAL не коммитятся; clean full checkpoint версионируется только в project Git и pin-ит Pipeline commit/replay points |
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
- Human-facing project files ограничены key decision projections в обязательной YAML+MD паре; системное исключение — один tracked binary SQLite checkpoint полной process memory.
- Внешние ссылки используют `artifact_version_id`; hash-profile проверяет payload, но не заменяет identity.
- Структурированные связи хранятся реляционно; canonical JSON TEXT используется для нереляционных structured payload; binary content хранится как SQLite BLOB.
- В Alpha не вводятся CAS/external blob backend, Git LFS или серверная БД; их рассматривают только после S17 evidence.
- Active DB/WAL/temp и migration backups не track-ятся. Каждый logical replay point — короткая active-DB transaction; он не копирует SQLite. Начиная с K0-b bounded publisher группирует range points, создаёт clean consistent `.pipeline/history/pipeline-checkpoint.sqlite3` и коммитит из coordination worktree только его и готовые YAML+MD projections той же DB sequence. Checkpoint содержит accumulated full process memory; clean clone + pinned Pipeline commit восстанавливает любой опубликованный replay point без внешнего backup service.
- Publication выполняется после top-level run, перед human wait/process exit, до/после irreversible side effect, migration/replay/gate и по pinned window limits. Recommended standard window `10 replay points / 5 min / 32 MiB active-DB growth`, strict — каждый point; D0 обязан утвердить exact limits и cost thresholds §9.5.1 архитектуры.
- Agent-visible secret запрещён до persistence. Repository получает максимальный confidentiality/retention class сохранённого replay payload; incident требует quarantine, rotation, Git history rewrite и clone/mirror invalidation, а не удаления одной DB row.

### 3.3.1 Replay contract

До/после каждого LLM invocation, human answer/approval, external/nondeterministic tool interaction и side effect создаётся logical replay point. Он pin-ит exact Pipeline/prompt/contract/schema versions, product commit/tree + dirty/untracked delta, ordered harness/adapter-visible rendered context bytes, provider/model/parameters, capabilities/tool versions, exact agent-visible tool requests/responses, environment fingerprint, outputs/events и causal sequence. `capture_completeness` явно отмечает provider-hidden context/model state или другой недоступный input; такой gap нельзя скрывать за словом «полный». Git publication группирует bounded range points по policy, но не удаляет промежуточные состояния.

`forensic replay` использует recorded model/tool responses и обязан детерминированно повторить route/artifacts/events. `stochastic re-execution` повторно вызывает доступный pinned profile с тем же envelope и сравнивает semantic/safety properties; недоступная прежняя модель фиксируется gap, а не маскируется другим model name.

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
10. HITL-точки, autonomy tiers и approvals; для human dialogue — применимые modes, role profile, turn/round budgets, provenance/disposition и resume rules;
11. tools, side effects, security/egress policy и repository boundaries;
12. context/scale/sharding policy, nominal/worst-case invocation budget, human-attention budget и допустимые fallback profiles. Invocation budget содержит два отдельных scope: plan-production package (`author + fresh-context reviewer + bounded revision author/reviewer calls`) по pinned new/delta call model и runtime package (`S0/Layer0 + workers/runtime reviewers + dialogue/retry/fallback`); phase envelope суммирует packages с уникальными `package_id`;
13. для любого binary-producing scope — `binary_payload_budget`: payload classes/media types, nominal/worst-case count, assumed mean, hard cap на один объект, nominal/worst-case aggregate, policy-permitted maximum aggregate, fail-closed runtime aggregate limit, checkpoint-publication/pack amplification и binding к D0 forecast;
14. downstream consumers и критерии фактического consumption;
15. structural, contract, behavioral, fixture и real-project scenarios;
16. evidence package и критерии `fixture_verified`/`real_project_verified`;
17. migration note по старому pipeline: `source ideas`, `retained`, `rewritten`, `retired`, `new tests`;
18. риски, открытые решения и явно отложенные возможности.

Все 18 разделов обязательны как контрольные категории, но раскрываются только в пределах текущей фазы; неприменимый раздел получает короткое `N/A` с причиной. В начале плана находится `scope_envelope`: phase/package, profiles/scenarios, current workers/routes/artifact types, explicit exclusions, deferred triggers и downstream boundary. Deferred roster описывается только именем, назначением, trigger и стабильным interface — без преждевременного проектирования prompts/internal routes.

До project runtime author/reviewer calls не исчезают из evidence: каждая такая invocation получает запись в `new pipeline/ledgers/design-invocations.yaml` по `registry/design-invocation-ledger/v1.schema.yaml`. Approval receipt обязан разрешить обе ссылки и подтвердить reviewer fresh-context/conflict metadata; отсутствующие исторические поля не восстанавливаются догадкой.

`binary_payload_budget` обязателен для G assets/references, Q runtime evidence (screenshots, recordings, traces/archives) и любого другого scope, который создаёт либо впервые сохраняет binary bytes. `N/A` допустимо только с доказательством, что contract запрещает binary persistence и использует version ref на payload уже учтённого producer. Это отдельный budget, не покрываемый ограничением строк, invocation budget или общим `checkpoint_budget`; его единственный полный machine-readable список полей — `d0-02-layer-architecture-gate.yaml#binary_payload_budget.required_fields`. Prose не вправе объявлять сокращённый альтернативный список.

Human-attention tier и числа также относятся к каждому budget package, а не к агрегатной phase-строке. Каждый package объявляет `sessions`, `blocking_decisions`, `active_minutes` в nominal/worst-case вариантах, `max_single_session_minutes` и `batchable_requests`; phase profile служит только envelope-меткой суммы. Owner capacity receipt обязателен перед запуском каждого конкретного package с профилем `high_attention`; сама по себе high-attention phase envelope не создаёт девять неадресуемых phase approvals.

До approval compiler сравнивает budget с latest approved D0/phase forecast. Любое изменение assumptions или чисел блокирует Layer Architecture Gate, пока owner по §9.5.1 архитектуры не выберет `narrow/checkpoint batching | raise threshold with storage/clone evidence | migrate checkpoint storage | pause`, а updated forecast и reconciliation receipt не будут pinned в approval. Проверка выполняется до contracts/prompts/runtime, способных создать первый payload: для G — в V1-00 до V1-01, для Q — до соответствующего runtime-evidence implementation. До готовности compiler D0-02 задаёт эквивалентную manual/reference check; неизвестные значения запрещены.

Complexity budget tier выбирается до написания: `narrow` — до 500 непустых строк; `standard` — до 700; `complex` для G/A/H/I — до 900; shared-plane plan — до 800. Это full-file caps, включая таблицы: считать только routing/roster/failure sections нельзя, иначе prose-bloat станет невидимым. Внутри cap отдельно декларируются budgets для routing, roster и failure/recovery sections. Auto-generated registry index не входит в лимит. Превышение разрешает только owner receipt с причиной, почему scope нельзя сузить или разнести на versioned appendices/packages; повторяющийся overrun требует изменить tier/rubric, а не превращать receipt в рутину. Approval фиксирует фактические counts workers/routes/artifact types/scenarios.

План ссылается на canonical schemas/registries и не копирует их. Его approval фиксируется отдельным receipt с plan version/hash, reviewer, dispositions открытых вопросов, complexity budget/factual counts и разрешённым implementation scope.

Reviewer назначается W0 до начала review и не является автором ни текущей, ни любой предшествующей версии этого плана. Это отдельная fresh-context invocation/session с read-only доступом к plan, parent architecture, contracts/evidence и rubric; reviewer может создавать только findings/dispositions proposal, но не переписывать план или выдавать owner approval. Receipt фиксирует reviewer identity, model/profile/context independence и conflicts. Human owner разрешает оставшееся расхождение, но не подменяет независимый initial review. D0-02 утверждает этот reviewer contract до первого Layer Architecture Gate.

Review ограничен: initial review может вернуть план автору не более двух раз. После второго revision-return любое содержательное расхождение маршрутизируется owner/HITL, который выбирает `approve with disposition | narrow scope | revise package architecture | block`. Третий автономный author↔reviewer loop запрещён. Повторная проверка в S1/V1/AT1/I1/Q1 является delta-review изменившегося scope; неизменные sections сохраняют прежние hashes и не переписываются.

`Layer Architecture Gate` считается пройденным, если:

- план существует именно для одного слоя и прошёл review;
- ответственность слоя не пересекается с другими owners без явного contract;
- у каждого input/output/blocker/revision есть owner и достижимый route;
- определён минимальный roster текущей фазы и честно перечислен deferred roster;
- plan scope и фактический объём укладываются в approved complexity budget либо имеют owner overrun receipt;
- применимый `binary_payload_budget` полон, связан с D0 forecast, а любое расхождение имеет owner disposition и reconciliation receipt;
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

Raw telemetry K0-a является `deferred_observability_input` с activation N1/Q1 и не повышает readiness. YAML+MD — derived governance projection: human approval ссылается на exact projection version либо projection остаётся informational; сам факт генерации файла не является consumer receipt.

### 4.4 Architecture hypotheses и measurement

Architecture hypothesis register является canonical versioned artifact в SQLite. Постоянный отдельный YAML-файл для него не создаётся; YAML+MD появляется только у key owner decision, принятого по результатам гипотезы. Запись содержит falsifiable statement, mechanism, owner, заранее определённые metric/falsifier/window/evidence, independent evaluator, status и decision impact.

K0-a обязан сохранить raw telemetry, которую нельзя восстановить задним числом: времена run/invocation/tool/HITL, model/context/usage facts, tool outcomes, events/revisions, artifact sizes и approval/escalation facts. Dashboard и success KPI в K0-a запрещены. N1/Q1 формируют baseline; threshold становится gate только через заранее утверждённую hypothesis/decision с формулой и anti-gaming interpretation.

Минимальные семейства будущих метрик:

- process: active/waiting time, invocations/retries/revision cycles, context и cost facts;
- quality: downstream/Q findings, escaped defects, decision churn, gaps и rollback outcomes;
- autonomy: auto/run-authorized/HITL actions, approvals/escalations и human waiting time.

Для D0/K0-a route forecast по §16.1.2 архитектуры публикуется как versioned manual/reference worksheet и независимо сверяется: `light ≤12/20`, `standard ≤30/50` nominal/worst-case LLM invocations либо explicit `deep` budget. K0-a закрепляет machine contract/reference cases, K0-b реализует resource-budget compiler и сверяет результат с ними. Начиная с N1 до approval каждого package обязателен machine-generated forecast; ручной расчёт больше не открывает gate. Отдельно указываются blocking human sessions/decisions, active-minute estimate и batchable requests. Factual расход сравнивается с forecast; budget ledger не заменяет априорную модель. V1 получает high-attention label и не запускается без подтверждённой owner capacity.

Для Creative Dialogue заранее регистрируется отдельная гипотеза: owner-first triad должен снижать число downstream revisions/неразрешённых противоречий и повышать owner-rated clarity без неприемлемого роста cognitive load, времени и token/cost. Adoption rate предложений агента не является KPI: задача протокола — улучшать решение, а не убеждать owner соглашаться.

### 4.5 Creative Dialogue Gate

Это shared policy capability, а не новый слой. До первого creative route должны быть утверждены применимые P/E plan versions и реализованы:

1. `registry/dialogue-policy/creative-dialogue.yaml` с режимами `elicitation | creative_dialogue | hybrid | decision_approval | fact_reconstruction`, applicability и versioned role profiles;
2. owner-first FSM: первый owner input атомарно фиксируется до fan-out;
3. независимые initial challenger/co-creator invocations на одном snapshot без outputs друг друга, затем declared barrier; последующий repair получает только owner-authorized challenge через новый snapshot/event;
4. owner-approved topic manifest и исполняемые defaults `≤6 topics/session`, `≤2 sessions/artifact`, `≤2 rounds/topic`; новый topic/session требует новой manifest version и rebudget до вызова;
5. moderator как единственный controller human turn: максимум два weaknesses и три repair ideas на round;
6. provenance/disposition `owner_stated | agent_proposed | owner_adopted | owner_modified | rejected | open_hypothesis | unresolved_tension`;
7. отдельный compiler: accepted content строится только из owner statements/adopted/modified proposals; open hypotheses/tensions допускаются только в маркированном open-items разделе;
8. dialogue event schemas, persistence/resume и F14, включая остановку mid-session и fail-closed cap exhaustion;
9. exclusion tests: factual user research, approval/consent/risk acceptance и incident reconstruction не попадают в creative mode.

P2 и E2 используют один механизм, но разные domain role profiles. P6/E7 не являются четвёртыми собеседниками и не генерируют новое содержание. Formal downstream reviews не объединяются с triad. Idea Note становится key YAML+MD projection только после owner disposition и остаётся canonical versioned artifact в SQLite.

### 4.6 Правило чередования

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
| `K0-b` Operational Alpha-0 | 2.0b/3.0b | recovery/safety-ready control plane + real-LLM routing/checkpoint-cost proof | committed fixture | F01–F05/F07/F09/F10/F13a/F15 + storage thresholds проходят |
| `N1` Nonvisual / Alpha-1 | 2.1/3.1 | узкий end-to-end lifecycle | nonvisual fixture | F11 + independent Q evidence |
| `S1` Swarm discovery | 2.2/3.2 | owner-approved Idea Note и новый Swarm без legacy inheritance | fixture + реальный Swarm | S01/S14 pre-import + F14 + S02–S04 |
| `V1` Visual/Elm risk | 2.3/3.3 | visual quality и structural binding совместимы | fixture + Swarm | F12 + S05–S07; иначе declared Plan B и phase blocked |
| `AT1` Architecture/tasks | 2.4/3.4 | реализация полностью трассируема | реальный Swarm | S08 |
| `I1` Product slice | 2.5/3.5 | работающий Swarm vertical slice | fixture + реальный Swarm | F13b + S09 + rollback evidence |
| `Q1` Independent audit | 2.6/3.6 | качество проверено независимо | реальный Swarm | S10 + finding dispositions |
| `X1` Expansion | 2.7/3.7 | доказанные runtime-потребности закрыты | fixture + Swarm | применимые S11–S13/S15–S17 + F06/F08 |
| `M1` Full meta-layer | 2.8/3.8 | безопасное self-improvement | Pipeline canary | red→green + two HITL approvals |

Фазы — порядок доказательств, а не календарные сроки. Следующая фаза начинается только после disposition findings предыдущей.

---

Ниже каждая фаза раскрыта как отдельный пакет с собственным exit gate.

## 7.1 D0 — Decision baseline и repository baseline

### Цель

Устранить неоднозначности, которые могут изменить kernel, структуру данных или последовательность пилота.

### Работы

1. До disposition V2-D01 составить independently recalculable reference worksheet полного Swarm route: target layer/worker/dialogue roster, package-level design/runtime invocations, human sessions/active minutes, replay-point/checkpoint-size model, publications derived from runs/waits/side effects/windows, initial/visual DB sizes и ungated no-delta Git-pack bound. Каждая phase после первого warning/hard crossing помечается conditional до owner route; expected delta/pack остаются `unknown_until_K0b`, а не маскируются пессимистическим коэффициентом. Это decision input, а не обещание точной цены; N1 уточняет его.
2. Для V2-D01…V2-D39 зафиксировать `accepted | modified | explicitly_deferred`, owner и rationale. V2-D04 дополнительно pin-ит exact checkpoint thresholds/window limits и pre-V1 migration runbook §9.5.1 архитектуры; V2-D37 блокирует K0-a и не может быть deferred.
3. Запретить defer для решений, блокирующих K0-a.
4. Утвердить обязательный состав layer architecture plan, scope/complexity budgets, два review-return rounds и формат architecture approval receipt из §4.2.
5. Получить human approval exact relocation `projects/swarm/old swarm/` → `research/old-swarm/`; до переноса добавить и проверить root-ignore rules `/projects/` и `/research/old-swarm/`.
6. Физически перенести snapshot без удаления и создать verified relocation receipt: canonical source/destination, до/после file/byte counts, nested Git inventory, source absence и destination read-only policy.
7. Выполнить product-tree hygiene scan `projects/swarm`: только root `.git`, нет nested `.git`, untracked bulk, legacy/runtime/build roots; создать project-local `.gitignore` и baseline allowlist. Ignore обязан закрывать `/.pipeline/runtime/`, `/.pipeline/backups/` и checkpoint temp files, но оставлять trackable exact `/.pipeline/history/pipeline-checkpoint.sqlite3`; broad `/.pipeline/` ignore запрещён.
8. Зафиксировать exact prompt/product/research roots, capability boundaries и worktree policy: coordination worktree единственный материализует checkpoint; task worktrees sparse-исключают `/.pipeline/history/**`, Q primary worktree — весь `/.pipeline/**`.
9. Определить identity первой Pipeline development version и правила dirty development mode.
10. Добавить в один root-Pipeline baseline commit:
   - `.gitignore`;
   - architecture plan;
   - development plan;
   - актуальный review/disposition record;
   - relocation/product-tree hygiene receipts без содержимого snapshot;
   - `new pipeline/registry/**`, `new pipeline/ledgers/**`, `new pipeline/reviews/**`;
   - все остальные records, достижимые по path/hash из dispositions, forecast и gate contract.
11. Закоммитить canonical fixture seed/spec/expected tree в root Pipeline Git и детерминированно материализовать из него маленький отдельный fixture Git; initialization record связывает Pipeline commit, fixture-spec hash и materialized fixture commit. Не использовать Swarm как fault-injection fixture.

### Exit gate

- blocker decisions закрыты;
- V2-D01 disposition ссылается на rough full-route worksheet, а V2-D04 содержит exact publication windows/thresholds, warning/hard-stop routes и last cheap migration gate до V1-01;
- Layer Architecture Gate принят как обязательная зависимость реализации каждого слоя;
- legacy snapshot физически отсутствует в `projects/swarm`, а exact ignored research root не входит в product-agent capabilities;
- product tree прошёл symmetric hygiene scan и не содержит nested Git/untracked bulk; project-local ignore существует до product baseline;
- root baseline committed и может быть pinned;
- baseline содержит каждую запись, на которую dispositions ссылаются прямо или транзитивно по hash; dangling path/hash отсутствуют;
- clean clone воспроизводит fixture seed/spec → materialized Git, а Pipeline commit + fixture-spec hash + fixture commit записаны вместе;
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

K0-a работает только на disposable committed fixture. Разрешена запись лишь в exact fixture SQLite/runtime temp paths; fixture source tree, product/research roots, arbitrary tool/network egress, external mutation и произвольные side effects недоступны. Исключение — ровно pinned model-provider channel для synthetic Layer0/worker invocations под egress policy. Его результат не является Alpha-0 и не разрешает запуск Pipeline на Swarm.

### Deliverables

1. Phase-scoped approved `shared-control-plane.md`, `shared-artifact-and-event-plane.md` и `S-layer-plan.md` только для bootstrap scope.
2. Minimal forward SQLite migration и constraints для runs, invocations, artifact/version и events.
3. Atomic artifact+event transaction.
4. Minimal contract compiler/loader для одного pinned fixture route и событий `command.received`, `run.started`, `artifact.version_created`, `handoff.ready`, `run.completed`; `handoff.ready` завершает только в fixture `bootstrap_sink` terminal policy.
5. S0, один synthetic `{Layer}0` и один fixture worker как реальные LLM invocations на безопасном synthetic domain; schema/semantic assertions детерминированы, exact wording — нет.
6. Basic CLI: initialize, run и inspect.
7. Exact Pipeline/fixture root check и deny-all для остальных capabilities.
8. Irreversible replay/telemetry fields: before/after replay-point IDs, exact rendered context bytes/hash, Pipeline/prompt/contract/model parameters, fixture commit/tree, agent-visible result bytes, timestamps/durations/usage, event counts и artifact size; telemetry зарегистрирована как `deferred_observability_input` для N1/Q1, без dashboard/KPI/readiness claim.

### Обязательная проверка

`F00`: `command → S0 → real-LLM synthetic Layer0 → real-LLM fixture worker → atomic artifact version + event → terminal state`; CLI читает artifact/event/model telemetry и exact invocation replay envelopes обратно из SQLite.

### Exit gate

- F00 проходит из clean fixture baseline;
- artifact и event ссылаются друг на друга и на pinned contract/run;
- Layer0/worker inputs и outputs доступны как exact before/after replay points, а не только usage summary;
- отсутствуют product/external side effects;
- findings имеют disposition и approved K0-b delta scope.

### Не входит

- projections/YAML+MD outbox;
- crash reconciliation/resume/abort;
- полный Alpha event profile;
- production repository/tool/egress guards;
- approvals, tracked checkpoint publisher, clean-clone replay, product run и release claims.

---

## 7.3 K0-b — Operational hardening и Alpha-0

### Цель

Превратить доказанный bootstrap cycle в минимальный recovery/safety-ready control plane до содержательных prompt-систем.

### Deliverables

1. Delta-approved shared-plane/S plans для operational scope.
2. Полные Alpha-0 forward migrations, schema/version binding и tracked clean SQLite checkpoint publisher с integrity/clean-clone restore proof.
3. Registry compiler для minimal Alpha event/subscription/routing profile и resource-budget compiler с reference-equivalence proof, включая layer-plan `binary_payload_budget` validator и D0 forecast reconciliation.
4. Transactional projection outbox, YAML+MD pair и crash reconciliation.
5. Deterministic nominal fast path и Layer0 fallback для non-nominal state.
6. Repository/worktree, path/symlink, tool/egress/secret/process guards, включая coordination-only checkpoint materialization и sparse exclusion для task/Q worktrees.
7. Graceful abort, recovery checkpoints и compatibility/rollback separation.
8. Structural, migration, contract и scenario test harness.
9. Predeclared `HYP-DISPATCH-01` matrix и F15 для real-LLM Layer0; Alpha error/meta terminal policies без dangling subscribers.
10. Replay materializer: selected replay point → product tree + dirty/untracked delta + exact context/tool/environment snapshot; forensic response injection и отдельный stochastic rerun mode.
11. Checkpoint budget compiler + synthetic page-churn/BLOB matrix: size/publication-count/delta-factor forecast, snapshot/commit p95, pack growth и clean-clone restore against D0 thresholds.

### Обязательные проверки

- F01–F05, F07, F09, F10, F13a и F15;
- F10 доказывает prompt-injection/secret/tool-policy boundary до выдачи designated research-import capability;
- F15 удовлетворяет pinned routing k/n и имеет ноль forbidden transitions/side effects;
- undeclared event отклоняется;
- routing compiler воспроизводим на одинаковом commit;
- resource-budget compiler совпадает с versioned reference cases и fail-closed отклоняет неполный route/fan-out/retry/dialogue graph;
- layer-plan validator fail-closed отклоняет применимый G/Q/иной binary scope без count/per-item/aggregate/publication limits, exact D0 binding или закрытого reconciliation receipt;
- crash до/после DB commit не создаёт half-published YAML/MD pair;
- direct handoff не имеет исполнимого route;
- чужой Git root приводит к fail-closed;
- task worktree физически не содержит checkpoint, Q primary worktree/index не содержит `/.pipeline/**`, а попытка обойти sparse policy блокирует invocation;
- выбор прежней Pipeline version не меняет product source files;
- checkpoint publisher коммитит только allowlisted history/projection paths одной DB sequence, не захватывает unrelated dirty product files и не допускает binary merge;
- clean clone project Git без runtime DB восстанавливает tracked checkpoint в новый path и проходит F13a forensic replay выбранного invocation;
- stochastic rerun получает exact original envelope; недоступный model/tool profile создаёт typed reproducibility gap;
- K0-b measurement не превышает hard-stop; forecast следующей phase ниже warning ratio либо owner до continuation выбрал заранее допустимый storage/batching/scope route;
- injected hard-limit crossing публикует terminal `over_limit` checkpoint текущего range и блокирует следующее product/external action.

### Exit gate

Alpha-0 отчёт содержит pinned Pipeline/schema versions, test evidence, finding dispositions, явно отложенные runtime families, tracked-checkpoint/clean-clone F13a receipt, measured checkpoint cost range и kernel→N1 feasibility forecast. Owner выбирает только `continue_to_N1 | pause_program`; Core-6 route до N1 ещё не оценивается. Warning/hard checkpoint route должен быть закрыт до продолжения. Ни один Alpha event не имеет dangling route: errors/meta заканчиваются blocked human/W5 terminal policy до M1; F00 sink остаётся fixture-only.

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
3. Один небольшой nonvisual bugfix fixture с известными исходными условиями; P использует `elicitation`, а Idea Note получает `not_applicable` receipt — creative triad не навязывается малому точному изменению.
4. Key decision YAML+MD projections и typed traceability P→R→A→T→I→Q.
5. Revision route Q→S0→owner `{Layer}0`→minimal replay.
6. Migration notes каждого слоя по использованным идеям старого пайплайна: retained/rewritten/retired/new tests.
7. Machine-generated invocation/human-attention forecast из resource-budget compiler; отсутствие или неполнота graph блокирует package до запуска.

### Обязательные проверки

- F11 проходит без ручного обхода contracts/events;
- Q-Alpha независимо проверяет requirements coverage, artifact lineage, code/test evidence и rollback evidence, не принимая I self-report;
- permanent gap терминален для reachability, но блокирует release до human risk/scope decision;
- downstream consumption каждой версии доказано exact-version `consumer_receipt`; terminal Q result потреблён fixture acceptance gate;
- один predeclared defect injection проходит корректный revision cycle.

### Exit gate

- P/R/A/T/I/Q имеют минимум `fixture_verified` для узкого профиля;
- обнаруженные проблемы kernel исправлены red→green;
- W0 опубликовал forecast remaining invocations/human attention/calendar/cost, а owner выбрал `continue_full | core6_nonvisual | pause_program`;
- при `continue_full` утверждён package S1, но ещё не полный roster оставшихся слоёв.

`core6_nonvisual` не означает успех на одном fixture: создаётся отдельный bounded package для реального nonvisual project и полного P/R/A/T/I/Q consumer/revision cycle. E/G/H/M получают explicit deferred triggers; Swarm UI и другой applicable visual scope через этот профиль не проводятся. `pause_program` сохраняет pins/evidence/findings без ложного статуса готовности.

---

## 7.5 S1 — Greenfield discovery нового Swarm

### Цель

Получить проверяемое определение нового продукта, не наследуя код и архитектуру старого.

### Работы

1. Утвердить отдельный `E-layer-plan.md`; сначала выпустить и утвердить новые P/R/A plan versions для Swarm scope. P/E plans обязаны определить dialogue modes/applicability, domain role profiles, compiler boundary и budgets по §4.5.
2. Опубликовать и contract-test-ить `registry/ui-architecture-policy/elm-applicability.yaml`: predicates, input evidence, outcomes, A8 route и staleness rules.
3. Только после layer-plan approvals реализовать недостающие E/P/R/A contracts/prompts, `registry/dialogue-policy/creative-dialogue.yaml`, dialogue events/persistence и пройти F14 до реального P2.
4. Проверить D0 relocation/product-tree receipts и только после этого создать осознанный greenfield baseline в отдельном Git `projects/swarm`.
5. До выдачи real-research capability пройти S14 на tracked `poisoned-research-fixture.md`; только затем importer впервые читает реальный `research/old-swarm/fix_prompts.md`, немедленно маркирует его `untrusted_prior_analysis` и формирует observation manifest из явно выбранных файлов read-only root:
   - source/provenance;
   - наблюдаемая проблема или урок;
   - trust class;
   - запрет использования как product instruction.
6. P2 проводит owner-first triadic creative dialogue; P6 публикует owner-approved Idea Note, profile, intent, stakeholders, success criteria, constraints, risks и scope boundaries без непринятых agent proposals.
7. R потребляет exact Idea Note/context versions, создаёт `consumer_receipt` и превращает только owner-approved intent/проверенные observations в requirements и acceptance outcomes.
8. E1 собирает factual research без brainstorming; E2 применяет Creative Dialogue Protocol к experience intent, после чего E7 фиксирует user journeys, adoption/usability risks и surface contracts только из dispositioned содержания.
9. A1 производит только platform predecision и Elm applicability evaluation, необходимые G/H; A0 валидирует binding/route. Это не A-final.
10. Для stateful interactive surfaces Elm назначается стандартным UI profile; исключение требует A8 decision.

### Обязательные проверки

- сначала K0-b F10; затем S01 и S14 до designated research import; F14 до creative P2; после этого S02–S04;
- owner input предшествует challenger/co-creator, они получают одинаковый snapshot и не видят вывод друг друга до barrier;
- raw/rejected agent proposal отсутствует в accepted content Idea Note; open hypothesis/tension остаётся только в labelled open-items, adopted/modified proposal имеет actor и exact hashes;
- mid-session resume не повторяет committed contributions/dispositions; topic/session/round cap приводит к явному owner outcome, а expansion без новой manifest version/rebudget fail-closed;
- structural scan подтверждает отсутствие legacy snapshot/nested Git в product root и не находит tracked/imported old code/architecture;
- каждое старое observation, повлиявшее на requirement, имеет provenance chain;
- ни один product decision не обоснован только существованием старой реализации;
- P содержит только Elm input facts; A1 outcome воспроизводится по policy version/hash и machine-readable evidence, A0 не является producer;
- Pipeline run pinned и не меняется во время S1.

### Exit gate

- F10 (K0-b) и S14 receipts предшествуют timestamp/correlation первого research observation/import;
- owner-approved Idea Note, P/R/E artifacts и A1 predecision через A0 приняты; R зарегистрировал exact-version consumer receipt Idea Note;
- E surface inventory достаточен для раннего visual risk slice;
- unresolved product choices не маскируются архитектурными предположениями.

---

## 7.6 V1 — Ранний G/H visual/Elm risk slice

### Цель

Проверить самую рискованную способность: создать сильное графическое решение и затем связать его с продуктовой структурой, не заставляя одного LLM одновременно решать обе задачи.

### Порядок

```text
E surface contracts + A0→A1 platform/Elm predecision
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
2. `G-layer-plan.md` содержит `binary_payload_budget` по ожидаемому reference/asset/visual BLOB distribution (count, per-asset cap, aggregate, publications/amplification), pinned D0 forecast и reconciliation receipt. Любое расхождение закрыто owner route §9.5.1 до V1-01 и первого real asset, поскольку это `last_cheap_migration_gate`.
3. Только после approvals и storage gate — минимальные G0, G1/G2 reference, applicable G3–G6 asset, G7 creative, G8 structural, G9/G10 mapping, G11 lock/formalization contracts и prompts. Asset-free strategy требует evidence-bound `not_applicable`; placeholder как final запрещён.
4. Immutable visual generation/version и mapping lineage.
5. A draft, ограниченный решениями, нужными H.
6. H contracts для Model/Msg/update/view, state/transition coverage и compiler feedback.
7. Conflict route H→A; третий повтор ведёт A8/HITL, а не в бесконечный loop.
8. Независимый visual/structural/evidence review.

### Обязательные проверки

- сначала F12, затем S05–S07;
- G budget однозначно связан с approved pre-V1 checkpoint forecast; forecast ниже warning ratio либо owner до V1-01 выполнил approved batching/storage/threshold/scope route;
- reference gate и applicable asset lane завершаются до G7; generated/selected real assets проходят G5/G6 acceptance либо strategy доказывает `not_applicable`;
- creative context не содержит structural identifiers;
- structural context не содержит visual generation;
- mapping не меняет locked visual;
- visual revision инвалидирует mapping, но не structural manifest;
- E revision инвалидирует обе ветви;
- injected `interaction_model_failure` при приемлемых visual/structure возвращается E0 и пересчитывает affected G/H/A scope;
- H потребляет принятую mapping/version, а не реконструирует дизайн по описанию.

### Failure route / Plan B

Провал F12 или S05–S07 получает evidence-bound class `creative_quality | structural_contract | mapping | interaction_model_failure | platform_predecision_failure | H_elm` из pinned finding registry. Producer — G12/G13 либо owner HITL; G0 валидирует и маршрутизирует, но не пишет finding. `interaction_model_failure` означает приемлемые visual/formal artifacts при плохом user flow/state/feedback; primary owner — E0, а исправленный interaction contract инвалидирует affected G/H/A scope. Failure не превращается автоматически в generic blocker и не разрешает ослабить evidence.

Owner выбирает один из четырёх routes:

1. изменить и повторно утвердить применимые E/G/H/A layer plans для точной причины провала, затем повторить V1;
2. сузить первую Swarm surface через явное scope decision и повторить V1 для оставшегося scope — обязательную user-facing capability нельзя удалить только ради прохождения gate;
3. применить A8 исключительно при доказанном Elm applicability/feasibility conflict; A8 не является исключением из visual quality, interaction model, mapping или presentation coverage;
4. остановить product track и провести disposable research spike вне baseline, после чего вернуться к новой architecture-plan version.

Переход к A-final/T/I возможен только после успешного повторного V1 либо human scope decision, действительно удаляющего проблемную surface из принятого product scope. Если эта surface является core product capability, доступен только route 1 или 4.

### Exit gate

- G имеет `real_project_verified` для выбранной Swarm surface. H имеет approved real-project handoff artifact и минимум `fixture_verified`, но остаётся не выше этого статуса до exact-version consumption A9/T0 в phase AT1; при неуспехе сохранены classification и выбранный Plan B route, а phase остаётся незавершённой;
- A-final/T/I запрещены до успешного rerun либо допустимого human scope decision;
- качество visual solution и полнота structural mapping оценены раздельно.

### Не входит

- полный G roster для всех surface types;
- полный H для всех экранов;
- массовая генерация UI.

---

## 7.7 AT1 — Финальная архитектура и task graph

### Цель

Собрать реализуемую архитектуру Swarm после проверки product, adoption, visual и Elm constraints.

### Deliverables

1. Утверждённые версии `A-layer-plan.md` и `T-layer-plan.md`, покрывающие final architecture/task scope; если scope не изменился относительно N1/V1, сохраняются прежние plan hashes и фиксируется applicability receipt.
2. A-final: system/data/security/deployment architecture и explicit trade-offs.
3. H-final handoff либо approved A8 exception для каждой применимой surface; A9/T0 создают exact-version consumer receipts, после чего H впервые может получить `real_project_verified`.
4. T task graph с owners, dependencies, acceptance/evidence plan и presentation coverage.
5. Traceability от intent/requirements/E/G/H/A до задач.
6. Rollback и migration plan первого product slice.

### Обязательные проверки

- S08;
- A9/T0 фактически потребили H handoff и readiness H пересчитан по receipts, а не по V1 self-report;
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

- F13b и S09;
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

1. Подтвердить approved `Q-layer-plan.md` ровно для Q-Alpha scope, включая `binary_payload_budget` для captured/ingested runtime evidence либо доказанное contract-bound `not_applicable`; расширение capabilities сначала оформляется новой plan version в X1.
2. Реализовать bounded Q1/Q2 profiles для независимой проверки четырёх domain: requirements/acceptance coverage, artifact/version lineage, code+test evidence и rollback evidence; Q0 остаётся только dispatcher.
3. Q-layer plan/contract отдельно pin-ят positive `primary_source_scope` и `secondary_evidence_scope`: Q1 индексирует только product-owned code/tests/config/migrations/docs, физически исключая `/.pipeline/**`; decisions, receipts и I evidence поступают typed secondary bundles. Checkpoint bytes не попадают в Q context. Contract также pin-ит `independence_profile` и fresh context, а high-assurance model/provider fallback следует архитектуре §5.9.
4. `Q7-Alpha` является единственным agent producer/adjudicator и классифицирует finding как product defect, Pipeline defect, permanent gap или invalid finding; он может создать `risk.acceptance_requested`, но `accepted_risk` производит только hash-bound human authorization.
5. Product defect возвращается owner-слою через S0.
6. Pipeline defect создаёт отдельный W5 work item и red test; активный run не переписывается.
7. Independent owner/slice-acceptance gate потребляет exact Q finding-set version и создаёт terminal `consumer_receipt`.

### Readiness coverage matrix

`real_project_verified` присваивается по строкам, а не один раз всему slice. Injection заранее регистрируется до исполнения; один проход может закрыть несколько строк только при наличии exact artifact lineage, owner route и повторного evidence для каждой:

| Layer | Real artifact | Exact consumer | Обязательный revision/recovery proof |
|---|---|---|---|
| P | Idea Note/context package | R0 | S02 subcase: R выявляет missing owner constraint → P0 revision |
| R | requirements/acceptance set | E0/A1 | S03 subcase: untestable/conflicting requirement → R0 revision |
| E | journey/interaction/surface contract | G0/A1 | S06 `interaction_model_failure` → E0 revision + invalidation |
| G | locked visual/mapping/H package | H0/A draft | S06 visual/mapping defect → G0 revision/remap |
| H | Elm architecture handoff | A9/T0 | S08 subcase: consumer finds H contract inconsistency → H0 revision |
| A | final architecture | T0 | S08 subcase: T finds architecture ambiguity → A0→owner worker revision |
| T | executable task/evidence snapshot | I0 | S09 subcase: I finds non-executable task → T0 revision/minimal replay |
| I | product slice + primary evidence | Q0/Q workers | S10 product defect → I0 revision + repeated evidence |
| Q | finding-set/conclusion | independent slice-acceptance gate | S10 subcase: unsupported finding is rejected → Q7-Alpha correction |

### Обязательные проверки

- S10;
- Q1 primary snapshot/index не содержит ни одного `/.pipeline/**` path; попытка включения fail-closed, а secondary bundle сохраняет role/provenance/version binding;
- каждая строка readiness matrix имеет normal consumer receipt и observed либо predeclared injected revision/recovery proof; общий defect count не заменяет per-layer coverage;
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
7. BLOB optimization или иной backend — только после DB/checkpoint/Git measurements;
8. расширенные security/adversarial сценарии;
9. полные G/H rosters для новых surface types;
10. расширение Q до security/performance/documentation/release capabilities;
11. metric aggregations/dashboard и normative thresholds только после N1/Q1 baseline и approved hypotheses.

Каждый package обязан иметь triggering evidence и сначала обновить/утвердить architecture plan затронутого слоя. Только затем создаются новый/изменённый contract, forward migration при необходимости, tests, compatibility statement и rollback plan.

### Обязательные проверки

Применимые S11–S13/S15–S17, human-assisted pre-M F06, F08 и соответствующие foundation/behavioral tests. F10/F13a уже blocking в K0-b, F13b — в I1, S14 — до S1 importer; они rerun-ятся только при изменении соответствующей policy.

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

M1 повторяет F06 с реальным subscriber M0 и автоматизированной diagnosis/routing частью до обоих HITL; pre-M F06 доказывает только terminal human/W5 bridge и не засчитывается как M E2E.

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
| K0-b | остальной minimal Alpha profile, correctness/security errors с terminal human/W5 policies и F15 real-LLM routing proof |
| N1 | finding/coverage/revision semantics, нужные F11/Q-Alpha; hypothesis records используют generic artifact events |
| S1/V1 | S14 pre-import guard, dialogue events из F14 и только нужные P/R/E/G/H domain events, без общего «про запас» catalog implementation |
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
| `interaction_model_failure` | E0 получает evidence-bound finding из G12/G13/owner HITL и пересчитывает journey/interaction dependencies | принятые visual/structural versions до явной invalidation |

### 9.2 Два rollback domain

Product rollback:

- работает только с allowlisted product code/config/data/deployment paths;
- не меняет Pipeline commit и contracts;
- не checkout/revert-ит tracked `.pipeline/history/pipeline-checkpoint.sqlite3`;
- сохраняет event/evidence history операции и публикует следующий checkpoint commit.

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
3. **Foundation:** транзакции, migrations, runtime backups, tracked checkpoint publisher, projections, abort, security guards.
4. **Replay:** clean clone → checkpoint restore → selected replay point → exact context/worktree; recorded-response forensic replay отдельно от stochastic re-execution.
5. **Behavioral:** свойства LLM-результата, adversarial inputs, k/n policy.
6. **Fixture E2E:** F00 bootstrap отдельно; затем F01–F15 operational/content/dialogue scenarios; F15 применяет stochastic k/n к pinned real-LLM profile, F06 до M1 является явно human-assisted.
7. **Real-project E2E:** S01–S17 по мере фаз.
8. **Independent audit:** Q и release gate не зависят от self-report исполняющего слоя.

### 10.2 Evidence package каждого gate

Каждый gate публикует:

- phase/scenario ID;
- pinned Pipeline commit и schema/registry versions;
- product-state/checkpoint commits, tree и dirty/untracked snapshot;
- run/invocation/event/artifact/replay-point IDs;
- exact context/environment/tool snapshot refs и forensic replay receipt;
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
- projection расходится с canonical DB и reconciliation не завершён;
- обязательная checkpoint publication не завершена, unpublished window превышен либо checkpoint commit захватывает неразрешённые product paths.

---

## 11. Управление work items

Минимальная запись задачи содержит:

```yaml
work_item_id: <stable-id>
phase: <D0|K0a|K0b|N1|S1|V1|AT1|I1|Q1|X1|M1>
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
product_state_commit: <pin-or-null>
product_tree_hash: <hash-or-null>
working_state_snapshot_ref: <artifact-version-or-null>
checkpoint_id: <publisher-id-or-null>
replay_point_refs: []
context_snapshot_refs: []
environment_fingerprint_ref: <artifact-version-or-null>
tool_snapshot_refs: []
fixture_spec_hash: <hash-or-null>
fixture_commit: <commit-or-null>
invocation_budget: {profile: <light|standard|deep>, nominal: <n>, worst_case: <n>}
human_attention_budget: {sessions: <n>, blocking_decisions: <n>, active_minutes: <n>}
checkpoint_budget: {publications: <n>, size_bytes: <n>, projected_pack_growth_bytes: <n>, warning_ratio: <n>, hard_stop_ratio: <n>}
binary_payload_budget_ref: <layer-plan-section-or-null>
forecast_reconciliation_ref: <receipt-or-null>
evidence_refs: []
consumer_receipt_refs: []
hypothesis_refs: []
metric_fact_refs: []
dialogue_session_refs: []
blockers: []
```

Пока K0-a не готов, backlog может храниться в versioned YAML+MD decision projection. K0-a создаёт первый authoritative SQLite state; после K0-b active DB становится normal operational execution state, tracked SQLite checkpoint — полной forensic Git-проекцией, а YAML+MD остаются человекочитаемым срезом только ключевых решений.

---

## 12. Первый исполняемый backlog

| Порядок | ID | Работа | Зависимость | Gate |
|---:|---|---|---|---|
| 1 | `D0-01` | recalculable full-route/checkpoint worksheet + versioned checkpoint-budget policy → disposition V2-D01…D39; V2-D04 exact thresholds/migration, V2-D37 blocking | — | Decision baseline |
| 2 | `D0-02` | утвердить reviewer independence contract, plan/runtime call scopes, design-invocation ledger, tiered human/binary budgets, canonical hash profile, hash-bound receipt и approval-envelope schema | D0-01 | Layer Architecture Gate |
| 3 | `D0-03` | approve relocation target + добавить/проверить root ignore rules | D0-01 | relocation prepared |
| 4 | `D0-04` | verified physical move + product-tree hygiene + project-local ignore | D0-03 | clean product root |
| 5 | `D0-05` | commit root baseline: ignore + plans + dispositions/receipts + `registry/**` + `ledgers/**` + `reviews/**` + весь hash-reachable governance graph | D0-02/D0-04 | pinnable root without dangling hashes |
| 6 | `D0-06` | commit fixture seed/spec + deterministic materialized fixture Git + triple binding | D0-05 | reproducible fixture baseline |
| 7 | `K0a-00` | phase-scoped plans shared control/artifact-event planes и S bootstrap scope | D0 | architecture approvals |
| 8 | `K0a-01` | minimal SQLite + atomic artifact/event + exact invocation replay/telemetry schema | K0a-00 | schema/replay review |
| 9 | `K0a-02` | one pinned contract + S0/Layer0/fixture worker + basic CLI | K0a-01 | contract/root-boundary tests |
| 10 | `K0a-03` | выполнить F00 и disposition findings | K0a-02 | bootstrap proof |
| 11 | `K0b-00` | delta-approve shared/S plans для operational scope | K0a-03 | architecture approvals |
| 12 | `K0b-01` | Alpha migrations + routing/resource-budget compilers + remaining minimal events | K0b-00 | migration/contract/reference-equivalence tests |
| 13 | `K0b-02` | projection outbox + tracked checkpoint publisher + replay materializer + crash reconciliation | K0b-01 | foundation/clean-clone replay tests |
| 14 | `K0b-03` | repository/tool/egress guards + abort/compatibility + применимые raw-hash/tool-policy findings из pinned legacy delta | K0b-00/K0b-01 | security/recovery tests + reviewed applicability binding |
| 15 | `K0b-04` | F01–F05/F07/F09/F10/F13a/F15 + synthetic checkpoint cost matrix + dispatcher/toolchain/oracle/attestation delta dispositions | K0b-02/K0b-03 | Alpha-0 + dispatcher/security/storage proof |
| 16 | `K0b-05` | kernel/N1 feasibility forecast + `continue_to_N1 | pause_program` owner decision | K0b-04 | program checkpoint |
| 17 | `N1-00` | отдельные detailed P/R/A/T/I/Q-Alpha layer plans, legacy-delta migration matrix и approvals | K0b-05=`continue_to_N1` | architecture/applicability approvals |
| 18 | `N1-01` | contracts/prompts/schemas текущего P/R/A/T/I/Q-Alpha scope | N1-00 | contract review |
| 19 | `N1-02` | F11 lifecycle + Q-Alpha + revision injection | N1-01 | Alpha-1 |
| 20 | `N1-03` | remaining call/human/calendar forecast + `continue_full | core6_nonvisual | pause_program` owner decision | N1-02 | program route |
| 21 | `S1-00` | detailed E plan + P/R/A plan revisions + Elm/dialogue policies, events и F14 | N1-03=`continue_full` | architecture/policy/dialogue approvals |
| 22 | `S1-01` | validate D0/F10 receipts + S01 baseline + pre-import S14 → provenance observation manifest | S1-00/D0-04 | S01/S14 |
| 23 | `S1-02` | P2 triad → owner-approved Idea Note/P6 → R consumer → E2 triad/E7 → A0→A1 real Swarm predecision | S1-00/S1-01 | S02–S04 |
| 24 | `V1-00` | detailed G/H plans + G `binary_payload_budget` ↔ D0 reconciliation/owner route + применимые E/A revisions | S1-02 | architecture/storage approvals |
| 25 | `V1-01` | minimal reference/asset/creative/structural/mapping/H contracts + F12 | V1-00 | visual fixture |
| 26 | `V1-02` | G/A-draft/H на Swarm; interaction-model test и Plan B; H pending A/T receipt | V1-01 | S05–S07 |
| 27 | `AT1-00` | подтвердить/обновить approved A/T plan versions для final scope | V1 success/scope decision | architecture applicability |
| 28 | `AT1-01` | A-final + T + H consumer receipts + presentation coverage | AT1-00 | S08/H verified |
| 29 | `I1-00` | подтвердить/обновить approved I plan для первого slice | AT1 | architecture applicability |
| 30 | `I1-01` | F13b + первый Swarm vertical slice + rollback | I1-00 | F13b/S09 |
| 31 | `Q1-00` | подтвердить Q-Alpha plan с Q7-Alpha, independence profile и runtime-evidence `binary_payload_budget`/доказанным N/A | I1 | architecture/storage applicability |
| 32 | `Q1-01` | Q-Alpha audit + terminal consumer receipt + revision cycle | Q1-00 | S10 |
| 33 | `X1-*` | approved layer-plan revision → evidence-triggered expansion package | Q1 | S11–S13/S15–S17 + F06/F08 |
| 34 | `M1-00` | отдельный detailed M plan и approval | stable X1 subset | architecture approval |
| 35 | `M1-01` | full controlled meta-layer + F06 automated rerun | M1-00 | M gate |

Параллелить можно только работы без общей write ownership. Parallel execution не отменяет barrier и общий phase gate.

Если N1-03 выбирает `core6_nonvisual`, S1-00…M1-01 не считаются выполненными: W0 создаёт отдельные `C6-00` architecture/applicability и `C6-01` real nonvisual lifecycle work items с полным P/R/A/T/I/Q consumer/revision gate. При `pause_program` downstream backlog остаётся proposed/blocked с сохранённым rationale.

### 12.1 Legacy Pipeline successor applicability contract

Versioned base/successor/exclusion facts закреплены в `references/legacy-pipeline-successor-2026-09-23/manifest-v1.yaml`. Внешний `C:/Projects/software_workflow` остаётся read-only provenance source; он, `old pipeline/**` и 21-file overlay не являются runtime imports, authored registry truth или самостоятельным разрешением менять планы, код, state либо gates. Overlay хранит только LF-normalized bytes тех же 21 active source files и всегда проверяется одновременно с raw-source provenance pins.

Единственная path-level классификация находится в `evidence/legacy-pipeline-successor-applicability-v1.yaml`; её правила и single-source boundaries разъясняет `architecture/legacy-pipeline-successor-applicability-addendum-v1.md`. Нельзя выбирать отдельную legacy формулировку напрямую: каждое принятое требование сначала переводится в native Pipeline v2 contract/profile/schema с владельцем, phase consumer и будущим evidence route. Противоречие с canonical Pipeline v2 registry, schema, migration, state или approved architecture разрешается в пользу canonical v2 authority либо отдельным owner disposition — не импортом legacy текста.

Порядок применения:

1. K0b-03 planning successor v1.1 принимает только fail-closed repository/tool/egress/hash guard implications, не добавляя legacy dispatcher, prompts, execution chains, providers или runtime paths.
2. K0b-04 до Alpha-0/F10/F15 отдельно disposition-ит dispatcher preflight, toolchain reachability, acceptance-oracle и reduced-guarantee attestation findings; эта revision не выполняет и не засчитывает проверки.
3. N1-00 до approval layer plans создаёт 21-row migration matrix из applicability evidence: native target contract, owner, consumer, incompatibility disposition и planned verification. Ни один legacy I/J prompt не становится действующим по факту присутствия overlay.
4. Независимый review applicability package и любые реализации требуют отдельных exact-scope authorities. До них status/gates сохраняются, `G-K0B03-UNTRUSTED-SHAPES` остаётся open, runtime authority — `none`.

---

## 13. Definition of Done плана разработки

Этот план можно перевести из draft в active baseline, когда:

1. owner подтвердил или изменил V2-D01…V2-D39;
2. IDs фаз, gate mapping и greenfield policy Swarm приняты;
3. Layer Architecture Gate, обязательный состав индивидуального плана и approval receipt приняты;
4. выбран формат decision/review record;
5. D0 backlog получил owners;
6. legacy snapshot физически изолирован, product tree clean, а relocation/hygiene receipts проверены;
7. root baseline committed и pinned;
8. owner подтвердил V2-D04: active DB/WAL untracked, clean full checkpoint tracked в project Git, Replay Point Contract, exact window/cost thresholds и pre-V1 migration runbook обязательны;
9. первый architecture work item K0a-00 может быть начат без скрытого продуктового решения; K0-a implementation остаётся заблокированным до его approval.

Любое изменение порядка, которое переносит G/H после A-final/T/I для UI-enabled Swarm, разрешает hot reload Pipeline, объединяет два Git или делает полный M prerequisite первого runtime, считается архитектурным изменением и требует owner disposition.
