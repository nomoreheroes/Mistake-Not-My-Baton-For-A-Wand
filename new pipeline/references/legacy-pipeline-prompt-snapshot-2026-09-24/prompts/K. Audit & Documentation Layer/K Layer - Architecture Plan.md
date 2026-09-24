# K Layer — Architecture Plan (Аудит и документация)

**Дата:** 2026-07-03
**Ревизия:** R6
**Статус:** DRAFT

**R1 (2026-07-03):** первичный план. Диспетчерский паттерн по образцу J0 (единственная точка входа, оркестрация subagent'ов внутри одной интерактивной сессии). 13 агентов (K0–K12). Ключевое архитектурное решение: K-слой решает **обратную задачу** — реконструирует структуру продукта из фактического кода/данных и независимо сверяет её с E→D→C→B→A, не используя артефакты I и J слоёв (task graph, QA, causal graph, dependency/static analysis reports) как источник истины. Финал слоя — Global HITL Product Acceptance Gate (K12).

**R2 (2026-07-07):** синхронизирована граница J→K: J больше не является audit entrypoint для K, а только сообщает человеку о готовности вручную запустить K через `k_trigger_signal.yaml`. `k_repo_scan.py` переведён из открытого вопроса в обязательный preflight/contract K0–K3. `k_trigger_signal.yaml` расширен resolved commit guard, upstream A–E hash manifest, scanner profile, external evidence refs и acceptance scope. K12 уточнён: unresolved `blocking` findings не могут быть приняты как known limitations; допустимы только `rejected`, `escalated` или non-terminal dispute с возвратом в review.

**R3 (2026-07-07):** усилен version pinning A–E через `upstream_artifacts_ref` с manifest hash; добавлен центральный `observed_implementation_map.yaml` после K3 как основной вход K5/K9; K3 расширен до Contract, Data & Capability Extractor; K8 переименован в Concurrency & Distributed Behavior Auditor с более широким условием запуска; добавлен условный K-UI Frontend & Interaction Behavior Auditor для code-derived проверки пользовательского поведения без чтения F/G/H как эталонов. K4 получил независимый security toolchain и первичные K security tool outputs. Evidence refs переведены на структурированный формат с `evidence_type`, включая `absence`. K11 получил verdict states `confirmed | refuted | needs_human_review | insufficient_evidence`. K12 сохраняет `original_severity`/`reviewed_severity` и explicit human risk acceptance вместо тихой переклассификации blocking findings. K10 разделён на as-built docs и audit-derived limitations; commit документации разрешён только после K12.

**R4 (2026-07-07):** добавлены crash recovery и resumable checkpoints через `k_session_state.yaml`; K0 получил hard execution policy для scanner/security tools/subagents (timeouts, memory/output caps, offline-only network policy). Runtime evidence вынесен в optional `runtime_evidence_refs`/`runtime_evidence_manifest.yaml`: K может учитывать redacted env/orchestrator/DOM/e2e evidence, но не ходит в live infra самовольно. K9 декомпозирован на K0-orchestrated shards по requirements/components/layers с агрегатором `k9_traceability_index.yaml`, а K5 становится seed-входом для K9 вместо повторного анализа тех же связей. Cache correctness усилен dependency/reverse-dependency subgraph hash и conservative invalidation после rebase/merge. K-UI получает confidence gating: static-only UI findings не могут быть high-confidence для динамических SPA/микрофронтендов без DOM/e2e/runtime evidence. OQ-K-004 закрыт численными scale gates и обязательным sharded/RAG mode при превышении порогов.

**R5 (2026-07-14):** закрыты разрывы implementability и trust boundary. Аудит выполняется только по immutable detached snapshot полного commit SHA с `source_snapshot_manifest.yaml`; исходный checkout и docs-публикация изолированы разными worktree. `acceptance_scope` получил нормативную stage/outcome matrix: частичный аудит больше не может завершиться глобальным product verdict. K12 разделён на disposition phase и approval точного hash финального documentation candidate; merge остаётся внешним действием владельца репозитория. Уточнены blocking/risk-acceptance semantics, проверяемая авторизация HITL-ролей, audit completeness gate, полный resume state K0–K12, content-addressed A–E manifest, tagged evidence refs, scanner completeness thresholds, executable/model egress policy и shard coverage invariants.

**R6 (2026-07-14):** закрыты замечания к R5. Выбор monolithic/sharded K9 сделан двухфазным: immutable provisional profile строится по repo-gates после scanner, финальный — после K3/K5 и barrier по capability/requirement/token gates; неизвестное значение консервативно включает sharding. `dispute_and_return_to_K11` разрешён для любого confirmed finding без обхода non-waivable semantics. External evidence получило нормализованный manifest и citation variant; deep mode — проверяемые full-read counts без sampling; scanner — versioned complexity metrics/tags. K12a/K12b разделены на immutable disposition/approval artifacts, а deterministic K0 docs publisher получил intent/CAS и approval-receipt recovery. Уточнены barrier terminal states, resume-vs-reaudit semantics, common finding identifiers и K9 coverage universe.

---

## 0. Предпосылки и границы слоя (решения, а не предположения)

Прежде чем проектировать агентов, нужно зафиксировать несколько решений, вытекающих из формулировки задачи. Это — явные развилки, а не самоочевидные факты; каждая обоснована.

**Решение D1 — K не доверяет самоотчёту I/J.** Формулировка задачи: «Аудит никак не должен опираться на артефакты слоёв I и J, в том числе QA, аналитику, графы связей». Причина этого требования методологическая: I и J производят и **код**, и **отчёт о своём же коде** (test_report.yaml, static_analysis_report.yaml, dependency_audit.yaml, causal_graph.db, acceptance_evidence.yaml). Если K возьмёт эти отчёты за основу, любой систематический слепой участок реализации (агент ошибается и не замечает этого — a whole class of failure) унаследуется аудитом без шанса быть пойманным. K обязан **реконструировать структуру заново, с нуля, из первичных источников** (код, миграции БД, конфиги, инфраструктура как код) и только после этого сравнивать с продуктовым намерением E→A. Это прямая параллель тому, зачем в software engineering существуют независимые security-аудиты поверх internal QA.

**Решение D2 — источник кода для аудита указывается человеком явно, не через j_layer_summary.yaml.** Строгое прочтение D1: даже путь `artifacts_root` внутри `j_layer_summary.yaml` — это поле, которое пишет J-слой о самом себе. Чтобы не размывать инвариант «не опираться на I/J-артефакты» до степени «ну кроме одного поля», K получает целевую версию продукта (`target_ref`: git-коммит/тег/ветка реального репозитория продукта) от человека-оператора в `k_trigger_signal.yaml` (§3) — так же, как M-слой получает `meta_trigger_signal.yaml` человеко-инициированно (см. [[project_m_layer]]). K0 разрешает `target_ref` через `git`, а не через YAML пайплайна.

**Решение D3 — сравнение только с E,D,C,B,A; F,G,H не являются эталонами K.** Пользователь явно перечислил цепочку в обратном порядке: E→D→C→B→A. F (UX-архитектура), G (визуальный дизайн/UI) и H (design-to-code handoff) в неё не входят как normative baseline: K не проверяет pixel-perfect UI и не сравнивает код с дизайн-макетами. При этом K обязан проверять code-derived поведенческое покрытие пользовательских сценариев, если продукт имеет UI: UI routes, forms, state transitions, validation, offline/error states и user-visible flows реконструируются из кода и сопоставляются с E/D/C на уровне поведения. Это не нарушает D3, потому что источником остаётся фактический код, а не F/G/H-артефакты.

**Решение D4 — K читает код продукта, но не пишет в него.** K реконструирует и документирует; K не создаёт задач в J-слое и не редактирует продуктовый код. Это симметрично инварианту M-слоя «не редактирует код продукта, выход J-слоя» (см. [[project_m_layer]] §13.2) — по той же причине: решение о том, как и когда чинить найденные дефекты, стоит дороже, чем формальный запуск, и должно оставаться за человеком/владельцем слоя.

**Решение D5 — документация продукта (K10) — деливерабл продукта, а не пайплайн-артефакт.** Системную документацию синтезирует K10, а после exact K12b approval детерминированный K0 publisher записывает её Git tree в audit branch продуктового репозитория (директория `docs_target_path`, по умолчанию `docs/`). Это часть самого продукта, которую держит в руках конечная команда. Рабочие артефакты аудита (findings, coverage-матрицы, сессионные логи) живут отдельно, в `TEST WORKFLOW/11. K. Audit & Documentation RS/` — по аналогии с тем, как M-слой различает "промпт/план" (де-ливерабл процесса) и `m_layer_session_summary.yaml` (служебный лог).

**Решение D6 — Kслой не изобретает собственный парсер кода поверх LLM.** Согласно исходным «Мыслям» пользователя (RAG/AST/call-graph), первичное структурное извлечение (импорты, вызовы функций, схема БД из миграций, маршруты API) выполняется детерминированным инструментом (скрипт `tools/k_repo_scan.py` или эквивалентный executable, описанный в `scanner_profile`), а не LLM-угадыванием по тексту файла. K0 обязан остановиться на preflight, если scanner недоступен, версия scanner profile неизвестна или scanner output не проходит schema validation (§5.6). K1/K2/K3 работают над структурированным выводом scanner, а не читают тысячи файлов целиком. LLM подключается там, где нужна интерпретация (что означает этот модуль, соответствует ли он требованию), а не там, где достаточно парсинга.

**Решение D7 — runtime evidence допустим только как redacted первичный вход, не как live-инспекция K.** Статический код/IaC остаётся основным источником реконструкции, но K4–K9/K-UI могут учитывать runtime-артефакты, если человек явно приложил их в `runtime_evidence_refs`: sanitized env manifest, secret fingerprints без значений, экспорт фактических orchestrator policies, DOM snapshots, e2e traces, runtime contract captures. K сам не подключается к production/staging/облаку и не извлекает секреты; отсутствие runtime evidence фиксируется как limitation или `insufficient_evidence`, а не заменяется догадкой.

**Решение D8 — K9 масштабируется через K0-orchestrated sharding, а не через надежду на future context windows.** На больших системах K0 обязан разбить traceability-сверку на shards по layer/requirement cluster/component/capability и затем агрегировать `k9_traceability_index.yaml`. K9 не получает весь A–E baseline и всю observed map одним монолитным prompt. RAG допускается только как retrieval backend для shard'ов, но orchestration boundary остаётся в K0.

**Решение D9 — SHA является адресом snapshot, а не подписью текущего checkout.** После `git rev-parse` K0 материализует отдельный detached audit worktree/archive строго на полном `resolved_target_commit_sha`, фиксирует `git_tree_sha`, tracked-file hashes, submodule commit'ы и LFS object ids в `source_snapshot_manifest.yaml`. Scanner и K1–K11 читают только этот snapshot; dirty/untracked files исходного checkout не участвуют. Недоступный in-scope submodule/LFS/generated source не считается проверенным и для `product_acceptance` становится completeness blocker. Любая запись tool'а в snapshot инвалидирует stage. Документация создаётся в другом worktree, основанном на том же SHA.

**Решение D10 — K12 принимает конкретный source tree на заявленном уровне evidence, а не абстрактный deployed product.** K не исполняет недоверенный product code и не подключается к live infrastructure по умолчанию. Поэтому `product_acceptance` означает принятие полного `git_tree_sha` относительно pinned A–E baseline и приложенных content-addressed runtime/release evidence. Runtime-dependent acceptance criterion без достаточного evidence получает `insufficient_evidence`; такой пробел запрещает outcome `accepted` и требует явного coverage waiver для `accepted_with_known_limitations` либо `escalated`. `k_layer_summary.yaml` всегда публикует `assurance_level: source_only | source_plus_runtime_evidence | release_bound_evidence`.

**Решение D11 — запрет I/J обеспечивается input sandbox, а не только инструкцией агенту.** K0 формирует content-addressed `k_input_bundle_manifest.yaml` с allowlist: immutable product snapshot, pinned A–E entries, K schemas и локально ingested/redacted evidence. Canonical-path и symlink checks запрещают выход за разрешённые roots и ссылки на F–J/M runtime artifacts. Subagents получают только этот bundle и session scratch; обращения вне allowlist блокируются и логируются. A–E prompt-файлы не читаются как data contract: форматы задаются versioned schemas. Product source roots/files перечисляются явно; scan всего repository root по умолчанию запрещён, а workflow/control roots (`TEST WORKFLOW`, A–M prompt directories, `.agents`, `.codex`) не могут быть автоматически добавлены scanner'ом.

---

## 1. Назначение слоя

K-слой — заключительный слой пайплайна A→K. Он не производит продуктовый код и не проектирует архитектуру; он независимо аудирует то, что получилось, и формирует as-built документацию:

```
Вход в K-слой:                                    Выход из K-слоя:
- k_trigger_signal.yaml (target_ref, scope,        - k_audit_findings.yaml (сводный отчёт)
  audit_depth, docs_target_path)                    - system documentation (в репозитории продукта)
- immutable snapshot resolved commit/tree SHA       - k_layer_summary.yaml
  (git, файловая и информационная база:              - k_hitl_acceptance_session.yaml
  БД-миграции, конфиги, IaC)                         (Scoped Evidence HITL Gate для audited tree)
- pinned A–E artifacts из upstream_artifacts_ref
  (vision, concept, requirements, stories, design intent)
- optional runtime evidence refs
  (redacted env/orchestrator/DOM/e2e evidence, если передано человеком)
```

Четыре измерения аудита (буквально из ТЗ):

1. **Безопасность** (K4)
2. **Полнота покрытия requirements и user stories** (K5, синтез в K9)
3. **Эффективность** (K6)
4. **Качество реализации** (K7)

Плюс — условно, для конкурентных/асинхронных/распределённых систем — **K8** (race conditions, транзакции, retry/lost updates, контракты сообщений, эмерджентное поведение) и для продуктов с UI — **K-UI** (поведенческое покрытие пользовательских сценариев из кода).

Результаты сходятся в K12 — scoped HITL gate по конкретному source tree и declared assurance level. Это не утверждение о deployed release без свежего release-bound runtime evidence (D10).

---

## 2. Границы: что K читает и что не читает

| Источник | K читает? | Как используется |
|---|---|---|
| Immutable snapshot полного resolved commit/tree SHA | Да | Первичный источник реконструкции (K1–K3); исходный checkout не читается |
| Миграции БД, IaC, конфиги в репозитории | Да | Реконструкция данных/инфраструктуры (K3, K6) |
| A/B/C/D/E артефакты (vision…design intent) | Да, только pinned manifest из `upstream_artifacts_ref` | Эталон для сравнения (K9), источник requirements/stories (K5) |
| F/G/H артефакты (UX/визуал/handoff) | Нет как эталон | Вне normative traceability chain; UI-поведение проверяется только code-derived агентом K-UI — решение D3, §0 |
| Redacted runtime evidence | Да, только из `runtime_evidence_refs` | Дополнительное первичное свидетельство для env/orchestrator/DOM/e2e/runtime claims; K не ходит в live infra сам |
| External supplied evidence | Да, только из `external_evidence_manifest.yaml` | Hash-pinned standards/advisories/research/operator documents с provenance, citation locator и subject/freshness binding; relevant slices для K4–K9/K-UI |
| I-слой артефакты (system_architecture.final.yaml, causal_graph.db, tasks.db) | Нет | Запрещено решением D1 |
| J-слой артефакты (j_layer_summary.yaml, test_report.yaml, static_analysis_report.yaml, dependency_audit.yaml, acceptance_evidence.yaml) | Нет | Запрещено решением D1 |
| `pipeline.db` / `causal_graph.db` / `j_runtime.db` / `tasks.db` | Нет | Запрещено — это самоотчёт I/J |
| M-слой артефакты | Нет | Не относится к продукту; M чинит промпты, не продукт |

K не читает prompt-файлы слоёв как data contract. Форматы A–E и K задаются versioned schema registry; если schema для pinned artifact неизвестна, K0 останавливает соответствующую ветку как `schema_unsupported`, а не извлекает контракт из инструкций агенту. K0 передаёт каждому specialist только relevant hash-addressed external/runtime slices; свободный URL lookup или ссылка без manifest entry не являются evidence.

---

## 3. Триггер и версионирование сессии

K-слой запускается на **версию продукта**, а не непрерывно. Аналогично M-слою (см. [[project_m_layer]] Факт 2), это человеко-инициированная Claude Code-сессия — нет фонового демона.

```yaml
# k_trigger_signal.yaml
schema_version: "1.2"
signal_id: KTS-{seq}
target_ref: "abc1234"                 # git commit/tag/branch продуктового репозитория — единственный источник "что аудируем"
expected_target_commit_sha: "0123456789abcdef0123456789abcdef01234567"
                                       # обязателен для product_acceptance; иначе optional guard
product_repo_path: "C:/Projects/<product_repo>"
product_repo_id: "product-stable-id"  # identity для cache/reaudit
source_policy:
  tracked_files_only: true
  include_roots: ["src/", "migrations/", "infra/", "config/"]
  include_files: ["package.json", "package-lock.json"]
  allow_repository_root: false
  exclude_roots: [".git/", ".k-worktrees/", "TEST WORKFLOW/"]
  follow_symlinks: false
  submodules: require_pinned           # require_pinned | exclude
  lfs_objects: require_present         # require_present | record_unavailable
scope: full_system                     # full_system | module_subset
scope_modules: []                     # заполняется только при module_subset
acceptance_scope: product_acceptance   # product_acceptance | audit_only | documentation_only
audit_depth: standard                 # standard | deep
scanner_profile: default              # имя профиля k_repo_scan.py: языки, ignores, extractors, schema version
upstream_artifacts_ref:                # pinned A–E baseline, задаётся человеком/оркестратором, не I/J
  artifacts_root: "TEST WORKFLOW/..."
  snapshot_id: "..."
  manifest_path: "a_e_baseline_manifest.yaml"
  manifest_sha256: "sha256:{hash}"
  required_layer_gate_status: accepted  # accepted | frozen
  target_binding:
    expected_target_commit_sha: "0123456789abcdef0123456789abcdef01234567"
    asserted_by: "..."
    assertion_reason: "approved baseline for this source revision"
    authorization_event_id: "..."
    approval_binding_sha256: "sha256:{manifest+target+action+nonce+expiry}"
external_evidence_refs: []            # только local path + sha256 + provenance; URL сам по себе не evidence
runtime_evidence_refs: []             # local redacted payload + sha256 + subject revision/environment binding
tool_execution_policy_ref: null       # optional override; иначе K0 пишет default tool_execution_policy.yaml (§5.8)
authorization_context_ref:            # обязателен для product verdict, risk waiver и docs commit
  path: "authorization_context.yaml"
  sha256: "sha256:{hash}"
  authority: "repository-governance-provider"
  policy_revision: "..."
resume_session_id: null               # если задан, K0 пытается продолжить checkpointed K-сессию (§6.3)
is_reaudit: false
previous_k_layer_summary_ref: null    # при reaudit: {path, sha256, session_id, resolved_target_commit_sha}
docs_target_path: "docs/"             # относительно product_repo_path
requested_by:
  actor_id: "..."
  role: audit_operator
  identity_provider: "..."
  subject: "..."
requested_at: "2026-07-03T10:00:00Z"
```

`is_reaudit: true` включает дифф-режим (§5.4): K1 сравнивает snapshot с полным `previous_k_layer_summary_ref.resolved_target_commit_sha`, предварительно проверив hash самого summary, repository identity и manifest его артефактов; mutable `target_ref` базой diff не является.

`resume_session_id != null` не создаёт новую reaudit-сессию и имеет приоритет как resume operation: K0 загружает сохранённый normalized trigger исходной сессии, а все повторно переданные semantic fields (`target_ref`, scope/depth, `is_reaudit`, previous summary, policies/manifests) обязаны byte/canonical-value совпасть с ним. Значение `is_reaudit` сохраняется таким, каким было при создании сессии, и не может быть переключено через resume. Несовпадение — `resume_context_mismatch`, а не новый запуск или неявный reaudit.

K0 нормализует trigger в `normalized_k_trigger_signal.yaml`, добавляя полный `resolved_target_commit_sha`, `git_tree_sha`, `repository_fingerprint`, `scanner_profile_resolved` и hashes policy/schema bundle. Если guard не совпадает, K0 останавливается до snapshot. `a_e_baseline_manifest.yaml` содержит точный список `{layer, artifact_id, path, schema_id, schema_version, content_sha256}`; `manifest_sha256` — SHA-256 canonical manifest bytes. K0 materializes read-only copy каждого entry, проверяет containment/symlinks/hash, и K9 никогда не ищет "latest". External/runtime refs сначала ingested в session bundle как immutable redacted payload; URL/resource id без локального payload hash остаётся metadata, а не подтверждающим evidence.

Для `product_acceptance` `target_binding.expected_target_commit_sha` обязан совпасть с resolved SHA, а assertion actor/role входит в HITL trail. Отсутствующий или несовпадающий baseline binding запрещает `accepted` и останавливает preflight вместо сравнения с произвольным намерением. Manifest также перечисляет gate artifact/status каждого слоя A–E; product acceptance требует hash-verified `accepted | frozen` baseline по всем пяти слоям. Отсутствующий B8/C2/D7/E11+E12-equivalent gate/sign-off не заменяется догадкой о последнем patch/report.

`requested_by.role` и роли внутри HITL-файла являются claims, а не доказательством полномочий. K0 hash-проверяет `authorization_context_ref` и через configured authorization adapter подтверждает actor subject, разрешённые роли/репозиторий/действия и policy revision. Baseline assertion, `risk_accepted`, `coverage_waiver` и docs approval требуют непереиспользуемого signed/provider approval event, привязанного к `session_id`, action, exact input hashes, nonce и expiry. Если adapter/authorization evidence недоступны, K может завершить технический audit и записать рекомендацию, но не может выдать product acceptance, принять риск/coverage waiver или commit'ить документацию: outcome становится `escalated`, docs — `skipped`.

### 3.1 Scope, depth и outcome matrix

| `acceptance_scope` | Допустимый `scope` | Обязательные стадии | Product outcome | Запись docs |
|---|---|---|---|---|
| `product_acceptance` | только `full_system` | полный применимый K1–K12 + completeness gate | `accepted | accepted_with_known_limitations | rejected | escalated` | по отдельному hash-approval K12 |
| `audit_only` | `full_system` или `module_subset` | K1–K9, K11, K12 disposition | `not_applicable` | запрещена |
| `documentation_only` | `full_system` или `module_subset` | K1–K3, K10, K12 documentation approval | `not_applicable` | только as-built docs; audit-derived limitations запрещены без accepted K-session ref |

`module_subset + product_acceptance` — schema/preflight error. Для subset K2 вычисляет dependency и reverse-dependency closure; summary перечисляет `requested_scope`, `evaluated_scope` и `boundary_dependencies`, но не делает утверждений о продукте целиком. При `documentation_only + module_subset` manifest и каждый документ обязаны явно маркировать partial scope, а `docs_target_path` должен быть scope-specific и не может перезаписывать canonical full-system docs; публикация в canonical path разрешена только для `full_system`. `standard` использует declared risk-weighted sampling (§5.3). `deep` отключает sampling для K4/K6/K7 и любого specialist check, который в standard-mode допускает sample: все supported eligible in-scope source items читаются полностью (chunked/streamed при необходимости), запускаются все применимые offline tools, а counts-инвариант проверяется в completeness report. Ни один режим не превращает unsupported/failed parsing или отсутствие runtime evidence в pass. `upstream_artifacts_ref` обязателен для `product_acceptance` и `audit_only`; в `documentation_only` он optional и не используется как источник as-built текста.

---

## 4. Общий поток сессии

```
Человек стартует K0, передаёт k_trigger_signal.yaml
        ↓
K0 Preflight: schema/policy → resolve full SHA → immutable audit snapshot/input bundle
              → deterministic scanner + source completeness gate
        ↓
K1 Repo Indexer  →  repo_map.yaml (+ file_level_findings.yaml, дешёвый tier)
        ↓
K2 Structure & Dependency Mapper  →  reconstructed_architecture.yaml
        ↓
K3 Contract, Data & Capability Extractor
  → interface_contract_map.yaml, data_schema_map.yaml, observed_implementation_map.yaml
        ↓
   ┌───────────┬───────────┬───────────┬──────────────┬──────────────┬─────────────┐
   ↓           ↓           ↓           ↓              ↓              ↓
  K4          K5          K6          K7          K8 (условно)   K-UI (условно)
 Security   Coverage   Efficiency   Quality     Concurrency     UI behaviour
   │           │           │           │              │              │
   └─────┬─────┴─────┬─────┴─────┬─────┴──────┬───────┴──────────────┘
         ↓            ↓
   K9 Sharded Upstream Traceability Synthesizer
   (K0 запускает shards по layer/requirement/component; K9 читает только shard slice)
         ↓
   K11 Findings Reviewer & Aggregator + audit_completeness_report.yaml
   (дедуп, refuted/insufficient evidence routing, severity history, unresolved checks)
        ↓
   K10a Documentation Draft (no product_repo writes)
        ↓
   K12a HITL finding disposition / product decision
        ↓
   K10b Final Candidate + documentation_candidate_manifest.yaml
         ↓
   K12b exact candidate-manifest hash approval
         ↓
   deterministic K0 publisher: intent → exact Git tree/commit → CAS audit ref; merge вне K
        ↓
        k_layer_summary.yaml: execution_status + scope-specific outcome + assurance_level
```

Диаграмма показывает `product_acceptance`; для других режимов стадии сокращаются строго по §3.1. K4–K8 и K-UI выполняются как независимые subagent-запуски K0. Единственный writer session state — K0: stage сначала публикует все outputs под уникальными temp names, затем schema/hash-validated `stage_output_manifest.yaml`, completion marker и только после этого checkpoint. Частично опубликованный multi-file stage не считается completed. K9 стартует после barrier. K12b подтверждает exact hash финального candidate, уже учитывающего K12a decisions; любое изменение bytes/hash инвалидирует approval. Branch commit и merge — разные действия: K может создать только audit-branch commit, но никогда не merge.

---

## 5. Управление контекстом и стоимостью

Это прямой ответ на «Мысли» из постановки задачи: нельзя скармливать весь код целиком. Стратегия — конвейер с сжатием на каждом уровне.

### 5.1 Уровни абстракции (Divide & Conquer)

```
Уровень A — файл       : K1, дешёвый/быстрый tier, индексирует scanner output
                          и читает только bounded content одного файла за раз.
                          Scanner остаётся источником структурных фактов;
                          LLM-summary/code smells имеют confidence/provenance.
Уровень B — модуль      : K2/K3, средний tier. Основной вход — summary файлов уровня A
                          + структурный вывод детерминированного инструмента
                          (§0 D6), а не сырой репозиторий целиком; разрешены только
                          точечные bounded-чтения source slices по §5.2.
Уровень C — архитектура : K4–K9/K-UI, верхний tier, но НЕ по всему репозиторию —
                          по reconstructed_architecture.yaml + точечным чтениям
                          конкретных файлов там, где риск/неопределённость
                          высоки (см. §5.3 risk-weighted sampling).
```

### 5.2 Repo Map как сжатое представление

`repo_map.yaml` (K1) — не список файлов с summary целиком в одном документе для каждого запроса, а индекс: путь → {role, exports, one_line_summary, risk_tags}. K2–K9 запрашивают из него только релевантные срезы (по домену/риск-тегу), не весь файл целиком, пока не понадобится конкретное подтверждение — тогда точечный `Read` конкретного файла.

### 5.3 Risk-weighted sampling (для K4/K6/K7)

В `standard` не каждый файл получает одинаковую глубину внимания. K2 помечает модули риск-тегами при реконструкции (`risk_tags: [auth, payment, pii_data, public_entrypoint, migration]`), scanner/K1 добавляют versioned `complexity_tags`. K4 (Security), K6 (Efficiency) и K7 (Quality) обязаны выполнить **полное** чтение файлов с соответствующими risk/complexity tags; для остальных модулей допустима выборочная проверка (representative sample) с явной пометкой `coverage: sampled` в отчёте — честная деградация точности, аналогично `manual_diff_level` в M-плане (см. [[project_m_layer]] §0/P2), а не притворство, что проверено всё.

В `deep` эта оптимизация запрещена: K4/K6/K7 читают все supported eligible items полностью, дробя крупные файлы на непересекающиеся chunks с byte/line coverage manifest. Для каждого specialist report обязательны `eligible_items`, `full_read_items`, `sampled_items`, `unsupported_items`; deep проходит только при `sampled_items == 0` и `full_read_items == supported_eligible_items`. K11 сверяет counts с scanner inventory, а нарушение создаёт completeness finding и запрещает `overall: complete`.

До запуска workers K0 публикует `specialist_sampling_plan.yaml`: hash scanner inventory/K2/K3 inputs, mode, per-dimension eligibility universe, assigned files/modules/chunks, explicit exclusions/unresolved items и deterministic sampling seed для `standard`. В `deep` каждый supported eligible item обязан быть назначен соответствующему specialist shard; unassigned item делает plan invalid. Worker report ссылается на plan hash и не может самовольно сузить universe.

### 5.4 Graph-aware кэширование (реаудит)

`k_file_audit_cache.db` (в `TEST WORKFLOW/11. K. Audit & Documentation RS/`): ключ `(product_repo_id, repository_fingerprint, file_path, content_sha256, dependency_subgraph_hash, reverse_dependency_subgraph_hash, graph_hash_algorithm_version, scanner_binary_hash, scanner_profile_hash, source_policy_hash, k_prompt_hash, analysis_mode, exact_model_revision, model_config_hash)` → `{k1_summary, k1_findings, cached_at}`. Graph hashes строятся canonical algorithm из scanner output и включают imports/calls/exports/routes/db_entities/config_keys для dependency и reverse-dependency slices. Cache writes выполняет только K0 в SQLite transaction; concurrent sessions используют DB lock, а cache никогда не является evidence сам по себе.

При `is_reaudit: true` K1 переиспользует file-level cache только после проверки previous summary/artifact hashes, той же repository identity и совпадения полного key context. K2/K3 инкрементально обновляют affected subgraph, включая reverse dependents. Если K0 видит non-linear ancestry, rebase, сложный merge или невозможность доказать стабильность graph slice, он обязан перейти в conservative mode: пересчитать K2/K3 для всего компонента, а не только для изменившихся файлов. Экономия допустима только там, где сохранена точность реконструкции.

### 5.5 Tiered models

```
K1 (file-level)                    → дешёвая/быстрая модель (Haiku-класс)
K2/K3 (module/contract level)      → средняя модель (Sonnet-класс)
K4/K5/K6/K7/K8/K9/K-UI (интерпретация, → топ-модель (Opus-класс) —
  сопоставление с намерением,        только на срезах из §5.1 Уровень C,
  security reasoning)                не на всём репозитории
K10 (section-level synthesis)       → средняя модель + deterministic manifest assembly
K11 (фильтрация false positive)    → средняя/топ модель, требует суждения
```

Конкретный маппинг на модели — деталь исполнения (задаётся в конфиге K0), не фиксируется в плане жёстко.

### 5.6 k_repo_scan.py contract (обязательный preflight)

K0 запускает scanner до K1/K2/K3 и валидирует его output как отдельный машинный контракт:

```yaml
scanner_profile:
  name: default
  schema_version: "1.0"
  supported_languages: [...]
  ignore_paths: [...]
  extractors:
    imports: true
    exports: true
    call_edges: best_effort
    api_routes: true
    db_migrations: true
    config_keys: true
    complexity_metrics: best_effort
  complexity_metric_version: "..."
  complexity_thresholds:
    high_source_lines: 500
    high_cyclomatic_complexity: 20

scan_output:
  scanner_version: "..."
  scanner_binary_sha256: "sha256:{hash}"
  target_ref: "..."
  target_commit_sha: <resolved_target_commit_sha>
  git_tree_sha: "..."
  repository_fingerprint: "sha256:{hash}"
  source_snapshot_manifest_hash: "sha256:{hash}"
  languages_detected: [...]
  metrics:
    tracked_in_scope_file_count: 0
    tracked_in_scope_bytes: 0
    scanned_source_bytes: 0
    file_count: 0
    symbol_count: 0
    call_edge_count: 0
    parsed_file_count: 0
    partial_file_count: 0
    failed_file_count: 0
    deliberately_excluded_file_count: 0
  files:
    - path: "..."
      language: "..."
      symbols: [...]
      imports: [...]
      exports: [...]
      calls: [...]
      routes: [...]
      db_entities: [...]
      config_keys: [...]
      test_files: [...]
      code_metrics:
        physical_lines: 0
        source_lines: 0
        function_count: 0
        max_cyclomatic_complexity: null
        complexity_measurement: measured  # measured | unsupported
      complexity_tags: []                 # напр. large_file | high_complexity; thresholds/profile hash-pinned
      parse_status: parsed  # parsed | partial | failed
      parse_reason: null
  unsupported_files: []
  deliberately_excluded_files: []      # path + policy rule + reason; не скрываются из denominator
```

Scanner запускается только внутри audit snapshot после policy/sandbox preflight. Если binary/profile/schema неизвестны, tree/manifest/repository hashes не совпадают или output невалиден, K0 пишет terminal preflight summary и не запускает K1–K12. K0 сверяет scanner inventory с `source_snapshot_manifest.yaml`: каждый in-scope tracked file обязан быть `parsed | partial | failed | deliberately_excluded`, без silent drop. `partial`, `failed` и `unsupported` всегда порождают completeness entries и попадают в K7; неизвестный executable/critical security, contract, migration, UI или concurrency surface блокирует `product_acceptance`, а не разрешает skip K8/K-UI. Complexity tags вычисляются только из hash-pinned metric version/thresholds; `unsupported` не подменяется низкой сложностью. Порог допустимого incomplete coverage задаётся scanner profile, но для `deep` равен нулю по supported source.

### 5.7 Scale Gates, Sharding & RAG Fallback

Scale decision двухфазный и monotonic: однажды выбранный `sharded` нельзя понизить обратно до `monolithic` в той же сессии.

1. После scanner/baseline preflight K0 пишет immutable `scale_profile.provisional.yaml` (phase A) и оценивает все уже вычислимые gates: source bytes, files, symbols, call edges и exact pinned baseline requirement/story count. Он нужен K2/K3/K5 для раннего component/coverage sharding.
2. После terminal K3 и K5, внутри barrier перед release K9, K0 пишет финальный `scale_profile.yaml` (phase B). Он включает hash phase-A artifact, фактические capability и normalized coverage-universe counts и canonical monolithic-K9 token estimate по observed map, K5 matrix, pinned A–E slices и применимым worker reports. Token estimator/version/config hash фиксируются в profile. Неизвестное значение gate, failed K5 или невозможность доказать upper bound консервативно выбирают `sharded` и создают completeness entry.

Если в соответствующей фазе выполняется хотя бы одно условие ниже, монолитный K9 запрещён:

```yaml
scale_gates:
  max_scanned_source_bytes_for_monolithic_k9: 5_000_000
  max_scanner_files_for_monolithic_k9: 1_500
  max_symbols_for_monolithic_k9: 12_000
  max_call_edges_for_monolithic_k9: 30_000
  max_capabilities_for_monolithic_k9: 350
  max_requirements_or_stories_for_monolithic_k9: 250
  max_estimated_k9_context_tokens: 120_000
```

Финальный артефакт сохраняет обе фазы и причину решения:

```yaml
schema_id: k/scale-profile
schema_version: "1.1"
status: finalized
phase_a:
  provisional_profile_sha256: "sha256:{hash}"
  evaluated_at: "2026-07-14T09:05:00Z"
  input_hashes: {scanner_output: "sha256:{hash}", baseline_manifest: "sha256:{hash}", scale_policy: "sha256:{hash}"}
  measured: {scanned_source_bytes: 4200000, scanner_files: 1100, symbols: 9000, call_edges: 21000, baseline_requirements_or_stories: 240}
  triggered_gates: []
  decision: monolithic_candidate
phase_b:
  evaluated_at: "2026-07-14T09:40:00Z"
  input_hashes: {observed_map: "sha256:{hash}", k5_matrix: "sha256:{hash}", worker_manifest_set: "sha256:{hash}", baseline_manifest: "sha256:{hash}"}
  measured: {capabilities: 410, requirements_or_stories: 300, estimated_k9_context_tokens: 180000}
  token_estimator: {id: "...", version: "...", config_sha256: "sha256:{hash}"}
  triggered_gates: [max_capabilities_for_monolithic_k9, max_requirements_or_stories_for_monolithic_k9, max_estimated_k9_context_tokens]
final_traceability_mode: sharded
decision_reason: phase_b_gate_exceeded
```

При превышении порога K0 включает `traceability_mode: sharded` и строит `k9_shard_manifest.yaml`: shards по `(layer, requirement_cluster, component_id, capability_cluster)`. Каждый shard получает только релевантный slice из pinned A–E, `observed_implementation_map.yaml`, K5 matrix и K4–K8/K-UI findings. K9 shard outputs агрегируются в `k9_traceability_index.yaml`, затем в `traceability_gap_report.yaml`. RAG разрешён как retrieval backend для shard'ов, но не заменяет sharding: retrieval scope, query, selected evidence and misses должны быть зафиксированы как structured evidence. K9 не стартует по provisional decision: его единственный допустимый scale input — hash profile с `status: finalized` и завершённой phase B.

Если даже shard превышает `max_estimated_k9_context_tokens`, K0 дробит его дальше по requirement/story или переводит shard в `needs_human_review` с reason `oversized_traceability_slice`; запускать oversized shard целиком запрещено.

Scale profile применяется не только к K9, но gates stage-specific. K2/K3 выбирают initial component sharding только по доступным phase-A repository gates и собственному pre-prompt effective-context guard; K5 — по phase-A baseline item count и тому же local guard. Если K2/K3/K5 во время построения universe обнаруживают превышение своего output/context bound, они дробят текущий stage до публикации canonical output, а не завершают monolith и не требуют retroactive rerun. Phase-B capability/coverage/token gates управляют K9 и не переопределяют уже валидные stage-specific decisions. K11 review'ит findings batches с global dedup/index pass, а K10 собирает docs по section/component manifests. Ни один consumer не обязан загружать целиком central map или все reports. Для каждого sharded stage обязательны coverage universe, expected/completed/unresolved counts, cross-boundary edge pass и aggregate manifest hash.

`max_estimated_k9_context_tokens` дополнительно ограничивается effective context выбранной model revision: `effective_limit = min(configured_gate, model_context_limit - reserved_output_tokens - safety_margin_tokens)`. Model mapping из §5.5 не может сделать разрешённым prompt, превышающий этот limit.

### 5.8 Tool Execution Policy

K0 создаёт или валидирует `tool_execution_policy.yaml` до запуска scanner/K4 tools:

```yaml
schema_version: "1.0"
network_mode: disabled          # disabled | allowlist; default для child processes
allow_external_saas_tools: false
telemetry_disabled_required: true
repository_code_execution: forbidden
git_hooks_enabled: false
repository_plugins_and_lifecycle_scripts: forbidden
follow_symlinks: false
read_roots: ["<audit_snapshot>", "<k_input_bundle>"]
write_roots: ["<session_scratch>", "<session_artifacts>"]
environment_allowlist: ["PATH", "TEMP", "TMP"]
process_limits:
  default_timeout_seconds: 600
  max_timeout_seconds: 1800
  max_memory_mb: 4096
  max_output_bytes: 50_000_000
  kill_process_tree_on_timeout: true
agent_limits:
  max_stage_retries: 2
  max_parallel_subagents: 6
allowed_executables:
  - executable_id: git
    absolute_path: "<resolved path>"
    binary_sha256: "sha256:{hash}"
    version: "..."
    args_policy: read_only_and_worktree_ops
  - executable_id: k_repo_scan
    absolute_path: "<resolved path>"
    binary_sha256: "sha256:{hash}"
    version: "..."
    args_policy: scan_snapshot_only
allowed_network_hosts: []
model_egress_policy:
  mode: approved_zero_retention_provider  # self_hosted | approved_zero_retention_provider | deny_source_content
  allowed_data_classes: [source_code]
  pre_llm_secret_scan: required
  retention_profile_ref: "..."
```

Пустой `allowed_executables` означает deny-all; поэтому default policy обязан содержать pinned `git`, scanner и выбранные K4 tools. Репозиторий рассматривается как hostile input: scanner/tools не исполняют product code, hooks, build scripts, package lifecycle scripts или repo-local plugins/config без отдельного future execution profile. Pre-LLM deterministic secret/PII scan и явная model egress policy обязательны независимо от child-process network policy. Любой network/SaaS override содержит actor, role, timestamp, reason и разрешённые data classes. Если платформа не умеет обеспечить заявленные filesystem/process limits, preflight останавливается; timeout/memory/output breach — stage failure, не partial pass. Write-capability для docs не активна во время аудита: после K12b K0 создаёт одноразовый `docs_publish_policy`, привязанный к intent/candidate/disposition/approval hashes, expected result tree/ref и idempotency key. Он разрешает только pinned Git no-filter blob/tree/commit operations и CAS update конкретного audit ref (плюс optional materialization worktree), затем capability отзывается.

---

## 6. K0 — Audit Dispatcher-Orchestrator

Единственная точка входа, аналогично J0/M1: один агент-оркестратор-исполнитель в интерактивной сессии, вызывает K1–K12 как subagents через Agent tool.

### 6.1 Алгоритм

```
1. Принять и schema-validate k_trigger_signal.yaml; создать session dir и durable
   k_session_state.yaml со status=initializing.
2. До запуска executable/модели: validate schema registry, tool/model policy,
   cross-field constraints §3.1 и authorization context/actor claims. Resolve target_ref в полный SHA;
   для product_acceptance expected_target_commit_sha обязателен и должен совпасть.
3. Создать detached audit snapshot на resolved SHA; проверить tree/submodules/LFS,
   canonical include/exclude roots и записать source_snapshot_manifest.yaml.
   Materialize hash-checked A–E/evidence в allowlisted k_input_bundle_manifest.yaml.
4. Запустить pinned scanner только по snapshot; сверить inventory/tree/manifest hashes
   и completeness thresholds. Любой preflight stop всё равно выпускает terminal
   k_layer_summary.yaml с execution_status=preflight_failed.
5. K0 пишет normalized trigger/policies/manifests, scanner_output.yaml и immutable
   scale_profile.provisional.yaml (phase A по repository + pinned baseline gates).
6. K1 → repo_map.yaml + file_level_findings.yaml (с учётом кэша §5.4 при reaudit).
7. K2 → reconstructed_architecture.yaml (использует scanner_output.yaml
  перед LLM-интерпретацией, см. §0 D6 и §5.6)
8. K3 → interface_contract_map.yaml, data_schema_map.yaml,
  observed_implementation_map.yaml
9. Если documentation_only — перейти к шагу 13. Иначе K0 сначала публикует
   specialist_sampling_plan.yaml (§5.3), затем запускает параллельно:
   K4, K5, K6, K7, K8 (если deterministic inventory + K2/K3 обнаружили
  concurrency/asynchrony/distributed/local-first/transactional surfaces —
  иначе K8 пропускается, skip_reason: no_concurrency_surface),
   K-UI (если deterministic inventory + K3 обнаружили UI surfaces —
  иначе K-UI пропускается, skip_reason: no_ui_surface)
10. Barrier — дождаться terminal status всех применимых веток шага 9. Состояния
    completed | failed | skipped проходят barrier как terminal: failed/skipped создают
    completeness entries/placeholders и не изображаются как отсутствие findings.
    После terminal K3/K5 K0 финализирует phase B в scale_profile.yaml; неизвестный
    capability/requirement/token gate включает sharded. Только затем release K9.
11. K9 → k9_shard_manifest.yaml, k9_traceability_shards/*,
  k9_traceability_index.yaml, traceability_gap_report.yaml (§8.1)
12. K11 → k_audit_findings.yaml + audit_completeness_report.yaml; file-level
    findings K1 входят через K7 и сохраняют source refs.
13. K10a → documentation draft без product_repo writes; в audit_only stage skipped.
    Его failure закрывает docs branch как failed, но не блокирует независимый K12a
    product/audit decision.
14. K12a → immutable k_hitl_disposition.yaml с finding dispositions и
    scope-specific product/audit decision;
    в documentation_only stage skipped. При audit_only перейти к шагу 18.
15. K10b → final candidate из as-built maps и K12a decisions;
    в documentation_only — только as-built. Записать exact candidate manifest.
16. K12b проверяет exact candidate + K12a disposition hash, когда phase A применима;
    в documentation_only вместо него bind'ит normalized trigger/scope/target tree. При approve/skip
    пишет immutable k_documentation_approval.yaml с соответствующим decision;
    revision_required пишет review event и повторяет 15–16 без canonical approval.
17. Deterministic K0 docs publisher пишет pre-side-effect intent, создаёт exact
    Git blobs/tree/commit и CAS-обновляет audit branch либо skip. K10 здесь не запускается.
18. K0 пишет immutable k_hitl_acceptance_session.yaml index, если K12 был достигнут,
    затем terminal k_layer_summary.yaml и hash-chained session log entry.
```

K1/K2/K3 — core reconstruction prerequisites, а не parallel barrier branches. Их failed/invalid output механически запрещает dependent workers и K9: K0 создаёт core completeness finding, переводит K11 в `completeness_only` aggregation и затем маршрутизирует `product_acceptance` только в `rejected | escalated`, `audit_only` — в `inconclusive | escalated`. Для `documentation_only` сессия завершается failed без K12b, поскольку as-built candidate недоказуем. Core reconstruction failure не coverage-waivable внутри K. Failed K4–K8/K-UI, напротив, проходит terminal barrier по шагу 10 и влияет на outcome через completeness semantics §11.1.

K0 после каждого шага обновляет `k_session_state.yaml`: session/stage status, exact input and output-manifest hashes, retry counters, skip/failure reason, HITL approval hashes и idempotency keys. При crash K0 переводит оставшийся `running` stage в `interrupted`; resume разрешён только при том же context fingerprint. Изменение findings, completeness report, final candidate или target tree автоматически инвалидирует K12 approval.

### 6.2 Изоляция

K использует два разных изолированных workspace и никогда не переключает branch/index исходного checkout пользователя:

1. `audit_snapshot` — detached/read-only worktree или archive полного `resolved_target_commit_sha`; scanner и K1–K11 читают только его. Tool outputs/caches пишутся только в session scratch. Hash tracked tree проверяется до и после каждого executable stage.
2. `docs_worktree` — optional review/materialization workspace, создаваемый только после K12b exact-hash approval от того же resolved SHA на ветке `k-audit/{session_id}`. Источником commit является не LLM/worktree staging, а deterministic K0 publisher с isolated Git index/plumbing и `--no-filters`: он создаёт exact approved blobs/tree, поэтому `.gitattributes`, clean/smudge filters и hooks не меняют candidate bytes. Canonical `docs_target_path` обязан оставаться внутри repo, не быть symlink/junction и не содержать `..`; итоговый tree diff может затрагивать только allowlisted documentation paths. Git hooks отключены.

Перед Git side effect K0 атомарно пишет `docs_publish_intent.yaml`: repository/base/ref identity, expected old ref, candidate/disposition/approval hashes, полный expected result tree, deterministic commit metadata/trailers и idempotency key. Publisher создаёт blobs/tree/commit, затем выполняет compare-and-swap update audit ref. Commit идемпотентен по `(session_id, candidate_manifest_sha256, approval_sha256)`: при resume K0 находит ref/commit по intent и trailer даже если crash произошёл после ref update, но до state checkpoint, и adopt'ит его только при точном совпадении parent/tree/allowed diff/approval. Иное состояние — conflict/failure без второго commit. K никогда не merge и не push; repo owner рассматривает audit branch обычным governance/PR-процессом вне K. Поэтому product outcome и `documentation_publish_status` независимы.

```
audit_snapshot (detached resolved SHA, read-only)  ← scanner, K1–K11
docs_worktree: k-audit/{session_id}               ← optional view exact K0-published commit
TEST WORKFLOW/11. K. Audit & Documentation RS/    ← session artifacts/scratch
```

### 6.3 Crash Recovery & Resume Semantics

Каждая K-сессия имеет durable state:

```yaml
schema_id: k/session-state
schema_version: "1.2"
session_id: "K-run-..."
session_status: running  # initializing | running | awaiting_human | finalizing | completed | failed | cancelled
target_ref: "abc1234"
resolved_target_commit_sha: "0123456789abcdef0123456789abcdef01234567"
git_tree_sha: "..."
core_context_fingerprint: "sha256:{hash}"
stages:
  preflight: {status: completed, attempt: 1}
  scanner: {status: completed, attempt: 1}
  scale_phase_a: {status: completed, attempt: 1}
  K1: {status: completed, attempt: 1}
  K2: {status: pending, attempt: 0}
  K3: {status: pending, attempt: 0}
  sampling_plan: {status: pending, attempt: 0}
  K4: {status: pending, attempt: 0}
  K5: {status: pending, attempt: 0}
  K6: {status: pending, attempt: 0}
  K7: {status: pending, attempt: 0}
  K8: {status: pending, attempt: 0}
  K-UI: {status: pending, attempt: 0}
  scale_phase_b: {status: pending, attempt: 0}
  K9: {status: pending, attempt: 0}
  K11: {status: pending, attempt: 0}
  K10a: {status: pending, attempt: 0}
  K12a: {status: pending, attempt: 0}
  K10b: {status: pending, attempt: 0}
  K12b: {status: pending, attempt: 0}
  docs_commit: {status: pending, attempt: 0}
  summary: {status: pending, attempt: 0}
artifacts:
  repo_map.yaml:
    sha256: "sha256:{hash}"
    produced_by_stage: K1
    stage_output_manifest_sha256: "sha256:{hash}"
last_failure: null
resume_cursor: null
approvals: {}
side_effects: {}
```

Для каждого stage объект дополнительно содержит `input_hashes`, `stage_input_fingerprint`, `output_manifest_sha256`, `skip_reason`, `failure`, timestamps, idempotency key и append-only `attempt_history`; допустимые status: `pending | running | interrupted | awaiting_human | completed | failed | skipped`. Старый attempt/output никогда не перезаписывается: canonical stage ref переключается только после atomic validated completion marker.

Нормативные переходы:

| Текущее состояние / событие | Следующее состояние | Обязательный эффект |
|---|---|---|
| `pending` | `running | skipped` | записать attempt id/input fingerprint; skip требует reason |
| `running` | `completed | failed | awaiting_human` | completed только после manifest+marker; failed сохраняет failure artifact |
| core K1/K2/K3 `failed` | dependent stages `skipped`; K11 `pending(completeness_only)` либо terminal docs failure | cascade-skip с `upstream_core_failure`; product core gap non-waivable |
| crash при `running` | `interrupted` | никаких предположений о completion/side effect |
| `interrupted`, валидный marker того же attempt/input | `completed` | adopt существующий output без повторного запуска |
| `interrupted`, marker отсутствует/невалиден | `running | failed` | quarantine partial temp outputs; новый append-only attempt |
| K12a `dispute_and_return_to_K11` | `K11: pending` | записать immutable review event; инвалидировать canonical K11 result и K10a→K12b/docs attempts/approvals, сохранив history |
| K12a terminal signed disposition | `K12a: completed` | сначала atomic approval receipt, затем immutable `k_hitl_disposition.yaml` |
| K12b `revision_required` | `K10b: pending` | записать immutable review event; инвалидировать candidate/K12b/docs attempts |
| K12b signed `approved | skipped` decision | `K12b: completed` | сначала atomic approval receipt, затем immutable `k_documentation_approval.yaml`; publish запускается только для approved |
| crash/retry `docs_commit` | `completed | failed` | reconcile prewritten intent/ref/commit; adopt только exact parent/tree/diff/trailer, иначе conflict |

Resume допустим только при полном совпадении immutable `core_context_fingerprint` (normalized original trigger, target tree, source/input manifests, schemas и tool/model/scanner/prompt/authorization policies). Его несовпадение всегда `resume_context_mismatch` и hard stop; K0 не продолжает сессию через частичную инвалидацию. Каскадная инвалидация разрешена лишь при том же core fingerprint для нового предусмотренного attempt (dispute/revision) либо когда recovery обнаружил отсутствующий/невалидный stage output marker с тем же expected stage input.

Approval provider вызывается с stable `decision_request_id`/nonce. До изменения stage state K0 атомарно сохраняет immutable `approval_receipts/{event_id}.yaml` и добавляет hash-chained ledger entry. Повтор ровно того же `(event_id, decision_request_id, binding_sha256)` после crash — idempotent reconciliation, а не replay; тот же event/request с иным binding немедленно отклоняется. Если crash произошёл после provider decision, но до checkpoint, K0 сначала ищет локальный receipt и/или запрашивает provider по stable request id, а не просит человека подписать повторно.

`scale_phase_a` и `scale_phase_b` — отдельные immutable checkpoints: phase B ссылается на hash phase A, а K9 никогда не возобновляется по одному provisional profile.

---

## 7. Ростер ролей K0–K12 и K-UI

| Агент | Роль | Вход | Выход | Модель-tier |
|---|---|---|---|---|
| K0 | Audit Dispatcher-Orchestrator | k_trigger_signal.yaml | оркестрация, k_layer_summary.yaml | — |
| K1 | Repo Indexer / Summarizer | scanner output + bounded reads immutable snapshot (+ кэш) | repo_map.yaml, file_level_findings.yaml | низкий |
| K2 | Structure & Dependency Mapper | repo_map.yaml + scanner output + scale_profile.provisional.yaml | reconstructed_architecture.yaml | средний |
| K3 | Contract, Data & Capability Extractor | reconstructed_architecture.yaml, scanner_output.yaml, scale_profile.provisional.yaml, bounded source slices (миграции/routes/schemas/UI/jobs/config) | interface_contract_map.yaml, data_schema_map.yaml, observed_implementation_map.yaml | средний |
| K4 | Security Auditor | reconstructed_architecture.yaml + observed_implementation_map.yaml + lockfiles/IaC/config/risk-tagged files + relevant runtime/external evidence slices + tool_execution_policy.yaml | security_audit_report.yaml, security_tool_outputs/* | высокий |
| K5 | Requirements & Story Coverage Auditor | scale_profile.provisional.yaml + observed_implementation_map.yaml + interface_contract_map.yaml + D (stories), C (requirements) | requirements_coverage_shards/* + requirements_coverage_matrix.yaml index | высокий |
| K6 | Efficiency & Resource Auditor | reconstructed_architecture.yaml, data_schema_map.yaml, IaC/config | efficiency_audit_report.yaml | высокий |
| K7 | Implementation Quality Auditor | repo_map.yaml, file_level_findings.yaml, risk/complexity-tagged файлы | implementation_quality_report.yaml | высокий |
| K8 | Concurrency & Distributed Behavior Auditor (условный) | reconstructed_architecture.yaml, observed_implementation_map.yaml, interface_contract_map.yaml | concurrency_distributed_behavior_audit.yaml | высокий |
| K-UI | Frontend & Interaction Behavior Auditor (условный) | observed_implementation_map.yaml + UI code surfaces + relevant runtime/external evidence slices | ui_behavior_audit.yaml | высокий |
| K9 | Sharded Upstream Traceability Synthesizer | finalized scale_profile.yaml + K2/K3/K5 + observed_implementation_map.yaml + все K4–K8/K-UI terminal reports/placeholders + pinned E/D/C/B/A slices | k9_traceability_shards/*, k9_traceability_index.yaml, traceability_gap_report.yaml | высокий |
| K10 | Documentation Synthesizer / Finalizer | as-built maps + K11/K12a decisions | draft, final candidate bytes + manifest; Git publication не выполняет | средний |
| K11 | Findings Reviewer & Aggregator | K1 через K7 + все отчёты K4–K9/K-UI | k_audit_findings.yaml, audit_completeness_report.yaml | средний/высокий |
| K12 | Scoped Evidence & Documentation HITL Gate | findings + completeness (phase a); final candidate + disposition hash либо documentation-only scope binding (phase b) | k_hitl_disposition.yaml, k_documentation_approval.yaml | HITL (risk owner / docs approver) |

Это формализация ролей из «Мыслей» пользователя: deterministic Scanner выполняется K0 как tool preflight, K1 индексирует/суммаризирует его результат, Mapper — K2+K3, Workers — K4–K8/K-UI, Reviewer — K11. K9 выполняет обратное сопоставление с E–A, K10 — документацию, K12 — scoped HITL gate. Итого 13 numbered roles K0–K12 плюс одна условная роль K-UI.

### 7.1 Observed Implementation Map

`observed_implementation_map.yaml` — центральная as-built карта возможностей, которую K3 строит после K2. Она связывает наблюдаемое поведение с concrete implementation surfaces: API, UI routes, CLI, background jobs, workers, DB constraints, config, permission rules, feature flags, retry/offline-sync/data-retention policies. K5 и K9 используют её как основной вход для проверки requirements/stories; `interface_contract_map.yaml` и `data_schema_map.yaml` остаются важными, но не исчерпывают реализацию requirements.

### 7.2 K4 Independent Security Toolchain

K4 не читает J security/static/dependency reports. Вместо этого он запускает или фиксирует собственные первичные K tool outputs:

- dependency vulnerability scan по lockfiles;
- secret scan;
- config/IaC security scan;
- auth/authz review;
- input validation and injection surface review;
- PII/data handling review;
- crypto/session/token review;
- dangerous API usage scan.

Secret/dependency/IaC inventory tools проходят по всему in-scope snapshot независимо от risk tags; tags регулируют глубину reasoning review, но не полноту deterministic inventory. Каждый tool run фиксирует binary/config/ruleset hash, version, command policy, exit status, input tree hash и output hash. Для offline vulnerability DB обязательны database hash, `updated_at`, maximum allowed staleness и freshness verdict.

Если конкретный tool недоступен, output incomplete или vulnerability DB просрочена, K4 записывает structured completeness entry и компенсирующий manual/static review scope; отсутствие tool output не должно тихо превращаться в "проверено". Critical-domain gap блокирует plain `accepted` согласно §11.

Все K4 tools запускаются под `tool_execution_policy.yaml` (§5.8). Default: `network_mode: disabled`, telemetry disabled, SaaS upload запрещён. Dependency scanners могут использовать только локальные vulnerability databases или заранее синхронизированные/self-hosted mirrors; secret scanners никогда не отправляют matches за пределы локальной среды. Нарушение offline-only policy — preflight failure, а не advisory finding.

### 7.3 K-UI Scope

K-UI запускается только если K3 обнаружил UI surfaces. Агент не читает F/G/H как эталон и не проверяет pixel-perfect соответствие. Он реконструирует из кода UI routes, screens, forms, user actions, validation behavior, state transitions, offline/error states и user-visible completion paths, затем сопоставляет это с D/C/E на уровне пользовательского поведения. Это защищает от false positive покрытия, когда backend endpoint существует, но пользовательская story невыполнима в интерфейсе.

K-UI обязан разделять `static_inference` и `runtime_supported` evidence. Для SPA/микрофронтендов/условного rendering выводы о user-visible flow без DOM snapshots/e2e traces/API response fixtures не могут иметь `confidence: high`; максимум `medium`, а при сложных state transitions — `low` или `insufficient_evidence`. Runtime evidence не берётся из F/G/H и не является дизайн-эталоном: это redacted факт исполнения, переданный через `runtime_evidence_refs` (§0 D7).

### 7.4 Runtime Evidence Manifest

`runtime_evidence_manifest.yaml` нормализуется K0 только после local ingestion и повторной secret/redaction проверки payload. Каждый entry содержит immutable payload hash, collector/collection method, capture time, environment/deployment revision, freshness policy и binding к audited commit, release artifact или image digest. Mutable URL остаётся provenance metadata и не fetch'ится неявно. K4 использует manifest для runtime/config security gaps, K8 — для фактических retry/queue/concurrency policies, K-UI — для dynamic UI behavior. Unbound/stale evidence снижает confidence; отсутствие достаточного evidence превращает любой runtime-dependent claim K4–K9/K-UI в `insufficient_evidence`, а не "pass".

---

## 8. K9 — Sharded Upstream Traceability Synthesizer (детально)

Это агент, реализующий «обратную задачу» из постановки: `observed_implementation_map.yaml` и реконструированную структуру нужно последовательно сверить с pinned слоями E, D, C, B, A — **в этом порядке**, от ближайшего к коду до самого раннего/абстрактного.

### 8.1 K9 sharding strategy

K9 никогда не обязан читать весь A–E baseline и всю implementation map одним prompt. K0 строит `k9_shard_manifest.yaml`:

```yaml
schema_version: "1.0"
traceability_mode: sharded  # monolithic | sharded
partition_keys: [layer, requirement_cluster, component_id, capability_cluster]
coverage_universe_sha256: "sha256:{hash}"
expected_item_counts: {upstream: 0, requirements: 0, stories: 0, capabilities: 0, components: 0, cross_boundary_edges: 0}
shards:
  - shard_id: K9-D-orders-create
    layer: D
    requirement_ids: [...]
    story_ids: [...]
    component_ids: [...]
    capability_ids: [...]
    input_refs:
      upstream_slice: "pinned/D/..."
      observed_slice: "observed_implementation_map.yaml#..."
      k5_seed_entries: [...]
    input_hashes: {upstream_slice: "sha256:{hash}", observed_slice: "sha256:{hash}"}
    estimated_context_tokens: 42000
```

Каждый shard выпускает `k9_traceability_shards/{shard_id}.yaml` с local findings, evidence refs, unresolved links, confidence и exact input hashes. Manifest validation доказывает, что каждый in-scope upstream item, requirement/story, observed capability/component и cross-boundary edge назначен хотя бы одному shard либо имеет explicit out-of-scope reason; cross-shard edges получают overlap/edge shard. Затем K0/K9 aggregator строит `k9_traceability_index.yaml`: дедуплицирует gaps, связывает cross-layer chains E→D→C→B→A и формирует финальный `traceability_gap_report.yaml`. K5 не дублируется: matrix используется как seed для D/C shards.

Oversized shard запрещён. Если shard превышает scale gate (§5.7), K0 дробит его по story/requirement/capability или маркирует unresolved с `reason: oversized_traceability_slice`. Каждый missing/failed/unresolved shard порождает synthetic completeness finding; `traceability_complete: false` блокирует plain `accepted` и требует coverage waiver либо `escalated`.

```
Проверка против E (Design Research & Intent):
  Вход: exact E entries из manifest: design_vision.yaml,
  design_intent_normalized.yaml, e11_gate_report.yaml и финальные E12
  design_grammar.yaml + design_tokens.json/sign-off provenance.
  Вопрос: отражает ли реализация зафиксированные design-параметры и
  interaction-принципы на уровне, доступном без анализа UI/визуала —
  т.е. не "похож ли пиксель", а "соблюдены ли behavioural constraints
  дизайн-намерения, которые обязаны материализоваться в коде" (напр.
  local-first behaviour, offline-merge semantics, если такие constraints
  зафиксированы в design_intent_normalized.yaml как функциональные, не
  визуальные).

Проверка против D (Stories & PRD):
  Вход: prd.index.yaml, global_stories_inventory.yaml,
  system_stories_inventory.yaml, user_stories_inventory.yaml,
  detailed_stories/{story_id}.yaml
  Вопрос: для каждой story — есть ли соответствующая наблюдаемая
  реализация в observed_implementation_map.yaml (endpoint/handler/UI-flow/
  CLI/background job/permission/config/data rule)? Использует
  requirements_coverage_matrix.yaml из K5 как основной вход, K9 добавляет
  сюда story-уровневую семантику (acceptance criteria из detailed_stories).

Проверка против C (Requirements):
  Вход: requirements_index.yaml, requirements_nfr.yaml,
  requirements_ssr.yaml, requirements_usr.yaml
  Вопрос: функциональные и нефункциональные требования (NFR/SSR/USR)
  покрыты кодом — NFR перекрывается с K6 (эффективность) и K4
  (безопасность, если NFR включает security-требования).

Проверка против B (Concept):
  Вход: только exact B entries из A–E manifest — coverage map, B2–B7
  patches и B8 gatekeeper report. B8 не является patch; report обязателен для
  product_acceptance, а его отсутствие в audit_only становится baseline limitation.
  Вопрос: не произошёл ли scope drift — реализованы ли фичи, которых
  не было в концепции (scope creep), или, наоборот, выпали ли из кода
  целые аспекты покрытия, заявленные на уровне концепции.

Проверка против A (Idea Note / Vision):
  Вход: exact versioned entries "2. Idea Note...", "5.Ethic & Regulatory
  Review...", "6.Gate Decision..." из pinned manifest; поиск latest запрещён.
  Вопрос: продукт всё ещё служит исходному vision и не нарушает
  ethics/regulatory ограничения, зафиксированные на входе (напр., если
  A5 наложил constraint на обработку персональных данных — соблюдён ли
  он фактическим кодом, а не только тем, что было заявлено в
  architecture review на уровне I).
```

Для каждого уровня и shard K9 производит отдельный под-отчёт с находками типа `traceability_gap`: `{layer: E|D|C|B|A, shard_id, gap_type: missing_implementation | scope_drift | contract_mismatch | constraint_violation, severity, evidence_refs}`. Находки уровня A и C с `gap_type: constraint_violation` (напр. нарушение ethics-ограничения) — всегда минимум `major`, эскалируются в K12 отдельным блоком независимо от общего severity routing (§9).

---

## 9. Таксономия находок и routing

Единая severity-шкала для K1 и K4–K9/K-UI findings, проходящих через K11 (согласована с уже принятой в M-плане градацией advisory/blocking, см. [[project_m_layer]] §10):

```
blocking  — критический риск или hard/non-waivable constraint violation.
            Всегда блокирует plain accepted; non-waivable допускает только
            rejected/escalated, waivable — privileged risk acceptance, после
            которого возможен только accepted_with_known_limitations.
major     — существенный дефект (частичная реализация, серьёзная
            неэффективность, значимый gap); требует individual disposition.
minor     — подтверждённый некритичный дефект; допускает signed batch
            disposition, привязанный к exact findings hash.
advisory  — рекомендация по улучшению, не дефект.
```

K11 — единственный агент, который меняет raw severity; любое изменение требует `severity_change_reason` и новых evidence refs. Raw findings не удаляются: сохраняются `source_finding_refs`/artifact hashes и dedup lineage. `refuted` получает `actionable: false`, `reviewed_severity: null` и не входит в actionable severity totals. `confirmed` требует disposition; reclassification представляется тем же verdict `confirmed` с изменённым `reviewed_severity`, а не отдельным enum state. `needs_human_review` и `insufficient_evidence` остаются unresolved. Действие человека `disputed` не является финальным verdict: оно возвращает finding в K11; до `refuted | confirmed` product decision не завершается.

Confirmed ethics/regulatory/legal violation или иной constraint, помеченный pinned A/C artifact как hard/non-waivable, всегда `blocking` и не risk-acceptable внутри K. Остальные A/C constraint violations имеют минимум `major`; downgrade ниже `major` возможен только после refutation исходного constraint mapping с сохранённым audit trail.

---

## 10. K10 — Documentation Synthesizer

Пишет консистентную структурированную документацию системы. Документация делится на as-built и audit-derived:

```
docs/architecture.md        — as-built: reconstructed_architecture.yaml в читаемом виде
docs/api_reference.md       — as-built: из interface_contract_map.yaml
docs/data_model.md          — as-built: из data_schema_map.yaml
docs/known_limitations.md   — audit-derived: только limitations, принятые/маршрутизированные K12
docs/audit_traceability.md  — optional audit-derived: человекочитаемый trace K9/K11 для команды
docs/glossary.md            — optional as-built: термины, извлечённые в ходе K1–K3
```

Документация формируется из independently reconstructed observations, а не переписывается из A–E. Поскольку reconstruction может быть sampled/unsupported/low-confidence, K10 не превращает гипотезу в факт: section manifest фиксирует source artifact/evidence hashes, coverage и confidence, а непроверенные места маркируются как unknown/limitation. Publication policy запрещает перенос secret matches, exploit details, credentials, sensitive topology и raw security evidence в product docs; вместо них используются redacted finding ids.

K10a готовит draft. После K12a dispositions K10b строит final candidate, включая `known_limitations.md` только из explicit accepted risks/coverage waivers/fix-required backlog. В `documentation_only` audit-derived files не создаются без hash-pinned accepted K-session ref.

`documentation_candidate_manifest.yaml` содержит base `resolved_target_commit_sha`/tree, canonical `docs_target_path`, а для каждого path — operation `create | replace | delete`, before/after content hashes, before/after Git blob ids/modes, source kind и provenance/confidence. Он также фиксирует полный expected result tree SHA и candidate payload manifest hash. K12b подписывает этот manifest вместе с K12a disposition hash, когда phase A применима; в `documentation_only` вместо disposition используется normalized trigger/requested+evaluated scope/target-tree binding. После approval K10 больше не запускается: K0 publisher проверяет candidate hashes, создаёт exact blobs с filters disabled, сверяет result tree и только затем CAS-обновляет audit branch. Любое regeneration/formatting изменение требует нового manifest и K12b review. Commit SHA/tree hash записываются отдельно, merge выполняется вне K.

---

## 11. K12 — Scoped Evidence & Documentation HITL Gate

K12 имеет две hash-bound фазы. Phase A рассматривает findings и полноту evidence; phase B, если docs разрешены, подтверждает exact final candidate после применения phase-A decisions. Product verdict существует только для `product_acceptance` и относится к `resolved_target_commit_sha`/`git_tree_sha` на declared `assurance_level`.

### 11.1 Нормативная таблица решений

| Состояние после K11 | Допустимое действие K12a | Ограничение outcome |
|---|---|---|
| `refuted` | сохранить audit trail, действий нет | не влияет |
| `confirmed blocking`, `non_waivable: true` | `reject | escalate | dispute_and_return_to_K11` | после повторного confirmation только `rejected | escalated`; dispute временно запрещает terminal decision |
| `confirmed blocking`, waivable | `reject | escalate | risk_accepted | dispute_and_return_to_K11` designated risk owner'ом | risk acceptance допускает только `accepted_with_known_limitations`; dispute временно запрещает terminal decision |
| `confirmed major` | `reject | fix_required | risk_accepted | dispute_and_return_to_K11` | при `fix_required/risk_accepted` только `accepted_with_known_limitations`; dispute временно запрещает terminal decision |
| `confirmed minor` | individual или hash-bound batch `accepted_limitation | fix_required`; `dispute_and_return_to_K11` только individual | при наличии только `accepted_with_known_limitations`; dispute временно запрещает terminal decision |
| `confirmed advisory` | `accept` без risk disposition или individual `dispute_and_return_to_K11` | advisory не ухудшает outcome; dispute временно запрещает terminal decision |
| `needs_human_review | insufficient_evidence` | `dispute_and_return_to_K11 | coverage_waiver | escalate` | waiver допускает только `accepted_with_known_limitations`; без него terminal acceptance запрещён |
| failed/invalid core reconstruction K1–K3 | `reject | escalate` (`audit_only`: `mark_inconclusive | escalate`) | не coverage-waivable; dependent workers/K9 не запускаются |
| failed/unresolved required stage, critical parse/tool gap или `traceability_complete: false` | исправить/возобновить, privileged coverage waiver или escalate | plain `accepted` запрещён |
| только confirmed advisory/refuted, completeness full | `accept` | `accepted` |

`disputed` никогда не закрывает finding и допустим для любого confirmed verdict, включая non-waivable blocking: это не risk acceptance и не downgrade, а запрос повторной проверки. Переход всегда `confirmed → disputed/reopened → K11 → refuted | confirmed` (последний может иметь новый `reviewed_severity`). Он инвалидирует незавершённые/прежние phase-A decisions, K10a и все downstream approvals; K11 и K10a выполняются заново на новых hashes. До нового K11 verdict product decision не финализируется. Plain `accepted` возможен только при `audit_completeness_report.overall: complete`, отсутствии actionable confirmed defect и отсутствии waiver. `fix_required` означает дефект в текущем tree, поэтому не совместим с plain accepted; backlog entry обязан иметь owner, due/expiry, external tracking ref (может быть null только с reason), verification criteria и `required_reaudit: true`.

Для `audit_only` `product_outcome: not_applicable`, а K12a фиксирует `audit_disposition_status: completed | inconclusive | escalated`. Для `documentation_only` phase A отсутствует и K12 выполняет только docs phase B. Product decision и docs publish decision независимы.

### 11.2 Контракт HITL

`authorization_context` задаёт action→role policy; YAML role без provider verification не даёт прав. Минимальная матрица (repository policy может быть строже):

| Действие | Минимальная проверенная роль |
|---|---|
| overall `accept | accept_with_limitations | reject | escalate` | `product_acceptance_owner` |
| audit-only `complete_audit | mark_inconclusive | escalate` | `audit_governance_owner` |
| `risk_accepted` | `product_risk_owner` |
| `coverage_waiver` | `audit_governance_owner` или явно делегированный `product_risk_owner` |
| `accepted_limitation | fix_required` | `product_acceptance_owner` |
| `dispute_and_return_to_K11` | `audit_reviewer` (non-terminal review event) |
| `approved_for_branch_commit | skipped | revision_required` | `repository_docs_approver` |

K12a и K12b никогда не дописывают один файл. K12a выпускает immutable disposition только после разрешения всех dispute loops:

```yaml
schema_id: k/hitl-disposition
schema_version: "1.0"
session_id: "K-run-..."
decision_request_id: "K-run-.../K12a/attempt-2"
authorization_context_sha256: "sha256:{hash}"
authorization_policy_revision: "..."
binding:
  normalized_trigger: "sha256:{hash}"
  source_snapshot: "sha256:{hash}"
  target_tree: "sha256:{hash}"
  baseline_manifest: "sha256:{hash}"
  findings: "sha256:{hash}"
  completeness_report: "sha256:{hash}"
  traceability_report: "sha256:{hash}"
  scope: full_system
  audit_depth: deep
  assurance_level: source_plus_runtime_evidence
binding_sha256: "sha256:{canonical binding}"
overall_decision:
  action: accept_with_limitations
  product_outcome: accepted_with_known_limitations
  audit_disposition_status: completed
  authorized_subject: "..."
  authorized_role: product_acceptance_owner
  authorization_receipt_ref: "approval_receipts/EVT-overall.yaml"
  decided_at: "2026-07-14T10:00:00Z"
  expires_at: "2026-08-14T10:00:00Z"
finding_decisions:
  - finding_id: KF-001
    original_severity: blocking
    reviewed_severity: blocking
    acceptance_decision: risk_accepted
    reason: "..."
    compensating_controls: ["..."]
    authorized_subject: "..."
    authorized_role: product_risk_owner
    authorization_receipt_ref: "approval_receipts/EVT-risk-KF-001.yaml"
    decided_at: "2026-07-14T10:00:00Z"
    expires_at: "2026-08-14T10:00:00Z"
coverage_waivers:
  - completeness_ref: KCOMP-001
    reason: "..."
    authorized_subject: "..."
    authorized_role: audit_governance_owner
    authorization_receipt_ref: "approval_receipts/EVT-waiver-KCOMP-001.yaml"
remediation_backlog:
  - finding_id: KF-002
    owner: "..."
    due_at: "2026-08-01T00:00:00Z"
    external_tracking_ref: null
    external_tracking_missing_reason: "to be registered by product owner"
    verification_criteria: ["..."]
    required_reaudit: true
decision_payload_sha256: "sha256:{canonical record excluding receipt payloads}"
```

Даже при нулевом числе findings `overall_decision` требует отдельного signed/provider receipt. `dispute_and_return_to_K11` не попадает в финальный disposition: каждый такой ответ хранится в `hitl_review_events/` и запускает переход §6.3.

K12b выпускает отдельный immutable artifact:

```yaml
schema_id: k/documentation-approval
schema_version: "1.0"
session_id: "K-run-..."
decision_request_id: "K-run-.../K12b/attempt-1"
authorization_context_sha256: "sha256:{hash}"
authorization_policy_revision: "..."
binding:
  normalized_trigger: "sha256:{hash}"
  target_tree: "sha256:{hash}"
  disposition_sha256: "sha256:{hash}"  # null только для documentation_only
  candidate_manifest_sha256: "sha256:{hash}"
binding_sha256: "sha256:{canonical binding}"
decision: approved_for_branch_commit
authorized_subject: "..."
authorized_role: repository_docs_approver
authorization_receipt_ref: "approval_receipts/EVT-docs.yaml"
nonce: "..."
approved_at: "2026-07-14T10:30:00Z"
expires_at: "2026-07-15T10:30:00Z"
merge_status: not_performed_by_k
decision_payload_sha256: "sha256:{canonical record excluding receipt payload}"
```

Для `documentation_only` null disposition заменяется binding на normalized trigger, requested/evaluated scope и target tree; для остальных docs modes disposition hash обязателен. `revision_required` создаёт review event, но не canonical approval artifact.

В terminal step K0 создаёт только index, не изменяя phase artifacts:

```yaml
schema_id: k/hitl-acceptance-session-index
schema_version: "1.0"
session_id: "K-run-..."
disposition_ref: {path: "k_hitl_disposition.yaml", sha256: "sha256:{hash}"}  # nullable by mode/status
documentation_approval_ref: {path: "k_documentation_approval.yaml", sha256: "sha256:{hash}"}  # nullable by mode/status
review_event_chain_head_sha256: "sha256:{hash}"  # null если review events не было
approval_ledger_head_sha256: "sha256:{hash}"     # null если K12 не достигнут
```

Cross-field rules: `product_acceptance` требует disposition; `audit_only` требует disposition и запрещает documentation approval; `documentation_only` требует documentation decision и `disposition_ref: null`. Если сессия завершилась до K12, index не создаётся. `skipped` docs decision всё равно имеет approval artifact, но не запускает publisher.

Risk/coverage/docs decisions привязаны к verified provider subject/role, authorization policy revision, UTC timestamp, nonce/expiry и exact input hashes; изменение любого input делает их stale. K не порождает J-задачи из backlog автоматически: дальнейшая маршрутизация остаётся решением владельца продукта.

Чтобы избежать hash-cycle, `decision_payload_sha256` вычисляется по canonical decision record без `authorization_receipt_ref` и без provider receipt bytes. Provider receipt подписывает canonical tuple `(session_id, decision_request_id, action, input_binding_sha256, decision_payload_sha256, nonce, expires_at, policy_revision)`; final artifact затем добавляет immutable receipt refs. Поэтому изменение как inputs, так и самого решения обнаруживается независимо.

---

## 12. Схемы ключевых артефактов

### 12.0 Schema registry, common envelope и evidence refs

Нормативные схемы хранятся в versioned registry `schemas/k/` (JSON Schema 2020-12 или эквивалент с теми же guarantees). Примеры ниже иллюстративны; K0 валидирует required fields, enums/formats, `additionalProperties`, cross-field constraints, duplicate YAML keys и запрещает custom tags до checkpoint. Hash имеет вид `sha256:<64 lowercase hex>`, timestamp — quoted RFC 3339 UTC.

Каждый produced artifact содержит common envelope:

```yaml
schema_id: k/repo-map
schema_version: "1.2"
artifact_id: "KART-..."
session_id: "K-run-..."
producer:
  stage: K1
  prompt_sha256: "sha256:{hash}"
  model_revision: "exact-model-revision"
resolved_target_commit_sha: "0123456789abcdef0123456789abcdef01234567"
git_tree_sha: "..."
generated_at: "2026-07-14T10:00:00Z"
input_artifact_hashes:
  scanner_output.yaml: "sha256:{hash}"
```

Ниже для краткости показаны только domain payload fields; common envelope из этого раздела всё равно обязателен и не повторяется в каждом excerpt.

`evidence_refs` — tagged union по `source_kind`; поля одного variant не подменяются полями другого:

```yaml
evidence_refs:
  - source_kind: product_file
    repository_fingerprint: "sha256:{hash}"
    resolved_target_commit_sha: "0123456789abcdef0123456789abcdef01234567"
    file_path: "src/api/routes/orders.py"
    content_sha256: "sha256:{hash}"
    locator: {line_start: 40, line_end: 88, symbol: create_order}
    evidence_type: implementation
  - source_kind: upstream_artifact
    baseline_manifest_sha256: "sha256:{hash}"
    artifact_path: "pinned/C/requirements_usr.yaml"
    artifact_sha256: "sha256:{hash}"
    pointer: "/requirements/13"
  - source_kind: runtime_artifact
    runtime_evidence_id: RTE-001
    payload_sha256: "sha256:{hash}"
  - source_kind: external_artifact
    external_evidence_id: EXT-001
    external_manifest_sha256: "sha256:{hash}"
    payload_sha256: "sha256:{hash}"
    locator: {page: 12, section: "4.2"}
  - source_kind: tool_output
    tool_run_id: K4-TOOL-001
    output_sha256: "sha256:{hash}"
  - source_kind: absence_search
    query: "route POST /orders or equivalent create-order handler"
    method: scanner_query_plus_symbol_search
    scanner_output_sha256: "sha256:{hash}"
    included_scopes: ["src/api", "src/domain"]
    excluded_scopes: []
    failed_or_unsupported_scopes: []
    coverage: complete
    absence_reason: "no matching route/handler found"
```

Missing-implementation claim обязан использовать `absence_search`. При `coverage: partial` он не может быть high-confidence и одновременно создаёт completeness entry.

### 12.0a Common specialist report

K4/K6/K7/K8/K-UI и K9 shards реализуют общий `k/specialist-report` envelope с dimension-specific extensions:

```yaml
schema_id: k/specialist-report
schema_version: "1.1"
stage: K4
dimension: security
stage_status: completed
sampling_plan_sha256: "sha256:{hash}"
coverage: {mode: full, eligible_items: 1200, supported_eligible_items: 1200, full_read_items: 1200, sampled_items: 0, unsupported_items: 0}
checks:
  - {check_id: dependency_vulnerability_scan, status: completed, tool_run_ref: K4-TOOL-001}
tool_runs: [...]
findings: [...]
limitations: []
confidence: high
```

Каждый item в `findings` валидируется общей registry-схемой `k/finding`. `component_ids`, `capability_ids` и `requirement_ids` обязательны как массивы; если все три пусты, `unmapped_scope_reason` обязан быть non-null. Это позволяет K9 строить slices, а K11 — deterministic dedup/lineage:

```yaml
findings:
  - finding_id: K4-F-007
    dimension: security
    severity: major
    summary: "..."
    component_ids: [orders-service]
    capability_ids: [CAP-orders-create]
    requirement_ids: [REQ-SSR-009]
    source_file_paths: ["src/api/routes/orders.py"]
    unmapped_scope_reason: null
    evidence_refs: [...]
```

`stage_status: skipped | unavailable | partial | failed` требует reason и попадает в `audit_completeness_report.yaml`; report с partial tool output не может объявить соответствующий check passed. Перед K11 deterministic evidence verifier повторно сверяет product-file hashes/locators и referenced artifact hashes с immutable bundle.

### 12.1 repo_map.yaml (K1)

```yaml
schema_version: "1.2"
target_ref: abc1234
resolved_target_commit_sha: "0123456789abcdef0123456789abcdef01234567"
git_tree_sha: "..."
repository_fingerprint: "sha256:{hash}"
scanner_profile: default
scanner_output_hash: "sha256:{hash}"
generated_at: "2026-07-14T10:00:00Z"
files:
  - path: "src/api/routes/orders.py"
    role: api_entrypoint
    exports: [create_order, cancel_order]
    one_line_summary: "..."
    risk_tags: [public_entrypoint, payment]
    complexity_tags: [high_complexity]
    code_metrics_ref: "scanner_output.yaml#/files/0/code_metrics"
    content_sha256: "..."
cache_hit_count: 812      # заполняется при is_reaudit: true
cache_miss_count: 14
```

### 12.2 reconstructed_architecture.yaml (K2)

```yaml
schema_version: "1.0"
components:
  - component_id: orders-service
    kind: service  # enum: service | module | library
    entrypoints: [...]
    depends_on: [payments-service, inventory-db]
    risk_tags: [payment, pii_data]
communication_edges:
  - from: orders-service
    to: payments-service
    kind: sync_http  # enum: sync_http | async_queue | direct_import
concurrency_or_distributed_system: true  # определяет, запускается ли K8
```

### 12.3 observed_implementation_map.yaml (K3)

```yaml
schema_version: "1.0"
capabilities:
  - capability_id: CAP-orders-create
    capability_summary: "User or system can create an order"
    implementation_surfaces:
      - type: api_endpoint  # enum также включает ui_route, cli_command, background_job, db_constraint, config, worker, integration, permission_rule, feature_flag, retry_policy, offline_sync, data_retention_rule
        evidence_refs: [...]
    related_components: [orders-service]
    related_contracts: [...]
    confidence: high  # high | medium | low
    confidence_reason: "..."
```

### 12.4 requirements_coverage_matrix.yaml (K5)

```yaml
schema_version: "1.0"
entries:
  - requirement_id: REQ-USR-014          # из requirements_usr.yaml
    story_ids: [GS-entities-02]           # из detailed_stories/
    coverage_status: implemented  # implemented | partial | missing | unable_to_verify
    verification_level: static_semantics  # static_presence | static_semantics | supplied_runtime_evidence | release_bound_evidence
    confidence: medium
    capability_ids: [CAP-orders-create]
    evidence_refs: [...]
    notes: "..."
summary:
  total: 214
  implemented: 189
  partial: 14
  missing: 9
  unable_to_verify: 2
```

### 12.5 k_audit_findings.yaml (K11, сводный)

```yaml
schema_id: k/audit-findings
schema_version: "1.2"
session_id: "K-run-..."
findings:
  - finding_id: KF-001
    source_finding_refs:
      - {artifact_sha256: "sha256:{hash}", source_finding_id: K4-F-007}
    source_agent: K4  # K1 | K4 | K5 | K6 | K7 | K8 | K-UI | K9
    dimension: security  # coverage | efficiency | quality | concurrency | frontend_behavior | traceability | completeness
    original_severity: blocking
    reviewed_severity: blocking  # null only when refuted
    non_waivable: false
    actionable: true
    summary: "..."
    component_ids: [orders-service]
    capability_ids: [CAP-orders-create]
    requirement_ids: [REQ-SSR-009]
    unmapped_scope_reason: null
    evidence_refs: [...]
    reviewer_verdict: confirmed  # confirmed | refuted | needs_human_review | insufficient_evidence
    severity_change_reason: null
summary:
  actionable_by_severity: {blocking: 1, major: 3, minor: 11, advisory: 22}
  by_verdict: {confirmed: 37, refuted: 4, needs_human_review: 2, insufficient_evidence: 1}
  unresolved_count: 3
  refuted_count: 4
```

K11 canonical finding сохраняет те же три scope-id массива из `k/finding`; при merge/dedup он объединяет ids с provenance, но не может удалить последний mapping без `unmapped_scope_reason` и evidence. Это требование действует и для synthetic completeness findings.

### 12.5a audit_completeness_report.yaml

```yaml
schema_id: k/audit-completeness-report
schema_version: "1.1"
session_id: "K-run-..."
overall: incomplete  # complete | incomplete
assurance_level: source_only
required_checks: {total: 42, completed: 39, skipped: 1, failed: 1, unresolved: 1}
scanner_coverage: {in_scope_files: 1200, parsed: 1198, partial: 1, failed: 1, deliberately_excluded: 0}
traceability: {expected_items: 420, covered_items: 418, unresolved_items: 2, complete: false}
tool_coverage: {required: 6, completed: 5, unavailable_or_stale: 1}
sampling: {mode: standard, universe_items: 1200, assigned_items: 1200, full_read_items: 380, sampled_items: 820, excluded_items: 0, unresolved_items: 0, invariant_passed: true}
critical_unresolved_refs: [KCOMP-001]
```

### 12.6 k_layer_summary.yaml (финальный)

```yaml
schema_id: k/layer-summary
schema_version: "1.2"
layer: K
execution_status: completed  # completed | completed_with_failures | preflight_failed | failed | cancelled
session_id: "K-run-..."
target_ref: "abc1234"
resolved_target_commit_sha: "0123456789abcdef0123456789abcdef01234567"
git_tree_sha: "..."
repository_fingerprint: "sha256:{hash}"
source_snapshot_manifest_sha256: "sha256:{hash}"
acceptance_scope: product_acceptance
requested_scope: {kind: full_system, modules: []}
evaluated_scope: {kind: full_system, modules: [], boundary_dependencies: []}
assurance_level: source_plus_runtime_evidence
product_outcome: accepted_with_known_limitations  # not_applicable для audit/documentation only
audit_disposition_status: completed
scanner_profile: default
scanner_output_sha256: "sha256:{hash}"
scale_profile_sha256: "sha256:{hash}"
traceability_mode: sharded
traceability_complete: true
upstream_manifest_sha256: "sha256:{hash}"
k_hitl_disposition_sha256: "sha256:{hash}"
k_documentation_approval_sha256: "sha256:{hash}"
documentation_commit_manifest_sha256: "sha256:{hash}"
started_at: "2026-07-14T09:00:00Z"
completed_at: "2026-07-14T11:00:00Z"
findings_summary:
  actionable_by_severity: {blocking: 0, major: 3, minor: 11, advisory: 22}
  by_verdict: {confirmed: 36, refuted: 4, needs_human_review: 0, insufficient_evidence: 0}
documentation_publish_status: committed  # not_applicable | skipped | approved | committed | failed
documentation_candidate_manifest_sha256: "sha256:{hash}"
documentation_branch: "k-audit/K-run-..."
documentation_commit_sha: "0123456789abcdef0123456789abcdef01234567"
documentation_merge_status: not_performed_by_k
remediation_backlog_count: 3
artifacts_root: "TEST WORKFLOW/11. K. Audit & Documentation RS/sessions/K-run-.../"
```

`execution_status` описывает завершение механики и не подменяет product outcome. Failure до terminal signed K12a disposition даёт `product_outcome: null`. Failure K10a/K10b/K12b/docs_commit после или независимо от валидного K12a не стирает уже hash-bound product outcome: summary сохраняет его, ставит `documentation_publish_status: failed | skipped` и обычно `execution_status: completed_with_failures`. Terminal summary и session-log entry обязательны всегда. Enum/cross-field constraints задаются schema registry; строки с комментариями выше показывают один валидный экземпляр, а не YAML-enum через `|`.

`k_hitl_disposition_sha256` nullable только если K12a не применим (`documentation_only`) или не достиг terminal disposition; `k_documentation_approval_sha256` nullable при отсутствии docs decision, а `documentation_commit_manifest_sha256` — пока publish не завершён/reconciled. Эти null не должны обнулять независимый валидный product outcome.

### 12.7 k_session_state.yaml (K0)

Полный stage roster и state transition contract приведены в §6.3. Registry schema дополнительно требует per-stage input/output hashes, `skip_reason` для skipped, failure object для failed/interrupted, approval bindings и side-effect reconciliation:

```yaml
schema_id: k/session-state
schema_version: "1.2"
session_id: "K-run-..."
session_status: awaiting_human
core_context_fingerprint: "sha256:{hash}"
stages:
  K12a:
    status: awaiting_human
    attempt: 1
    input_hashes:
      k_audit_findings.yaml: "sha256:{hash}"
      audit_completeness_report.yaml: "sha256:{hash}"
    output_manifest_sha256: null
    skip_reason: null
last_failure: null
resume_cursor: K12a
approvals:
  pending_decision_request: {decision_request_id: "K-run-.../K12a/attempt-1", binding_sha256: "sha256:{hash}"}
  receipt_refs: []
  ledger_head_sha256: "sha256:{hash}"
side_effects:
  docs_publish_intent_ref: null
```

### 12.8 runtime_evidence_manifest.yaml (K0, optional)

```yaml
schema_id: k/runtime-evidence-manifest
schema_version: "1.1"
runtime_evidence_refs:
  - evidence_id: RTE-001
    evidence_type: e2e_trace  # env_manifest | secret_fingerprint | orchestrator_policy | deployed_config | dom_snapshot | e2e_trace | api_capture
    ingested_payload_path: "evidence/runtime/RTE-001.redacted.json"
    payload_sha256: "sha256:{hash}"
    source_ref: "redacted://provenance-only"
    collector: {id: "...", method: manual_export, version: "..."}
    redaction: {status: verified, verified_by: "...", contains_secret_values: false}
    target_environment: staging
    subject_binding:
      commit_sha: "0123456789abcdef0123456789abcdef01234567"
      release_artifact_digest: null
      deployment_revision: "..."
    captured_at: "2026-07-14T08:00:00Z"
    freshness: {max_age_seconds: 86400, verdict: fresh}
```

### 12.8a external_evidence_manifest.yaml (K0, optional)

Каждый `external_evidence_ref` сначала копируется в immutable session bundle и получает нормализованную citation/provenance запись. URL без локального hash-verified payload остаётся discovery metadata и не может использоваться в finding evidence.

```yaml
schema_id: k/external-evidence-manifest
schema_version: "1.0"
external_evidence_refs:
  - evidence_id: EXT-001
    evidence_type: standard  # standard | regulation | advisory | research | vendor_documentation | operator_supplied
    ingested_payload_path: "evidence/external/EXT-001.redacted.pdf"
    payload_sha256: "sha256:{hash}"
    provenance:
      supplied_by: "..."
      source_uri: "https://example.invalid/document"
      publisher: "..."
      title: "..."
      version_or_date: "..."
      retrieved_at: "2026-07-14T08:00:00Z"
    citation:
      locator_scheme: pdf_page_section
      stable_locator: {page: 12, section: "4.2"}
    ingestion: {method: local_copy, scanner_status: passed}
    redaction: {status: verified, verified_by: "...", contains_secret_values: false}
    subject_binding:
      product_repo_id: "product-stable-id"
      commit_sha: "0123456789abcdef0123456789abcdef01234567"
      baseline_manifest_sha256: "sha256:{hash}"
    freshness: {max_age_seconds: 2592000, verdict: fresh}
```

`source_kind: external_artifact` обязан ссылаться на `evidence_id`, manifest hash, payload hash и stable locator из этой записи. Изменение payload/citation invalidates dependent findings и K12 decisions.

### 12.9 K9 shard artifacts

`k9_shard_manifest.yaml`:

```yaml
schema_id: k/k9-shard-manifest
schema_version: "1.1"
traceability_mode: sharded
scale_profile_sha256: "sha256:{hash}"
coverage_universe_sha256: "sha256:{hash}"
expected_item_counts: {upstream: 47, requirements: 214, stories: 86, capabilities: 240, components: 17, cross_boundary_edges: 31}
shards: [...]
```

`k9_traceability_index.yaml`:

```yaml
schema_id: k/k9-traceability-index
schema_version: "1.1"
shard_count: 24
completed_shards: 23
unresolved_shards: [K9-D-orders-create]
expected_items: 588
covered_items: 586
unresolved_items: 2
traceability_complete: false
deduped_gap_ids: [...]
cross_layer_chains:
  - chain_id: "..."
    layers: [E, D, C, B, A]
    finding_ids: [...]
synthetic_completeness_finding_refs: [KF-099]
```

### 12.10 Documentation candidate and publish transaction

`documentation_candidate_manifest.yaml`:

```yaml
schema_id: k/documentation-candidate-manifest
schema_version: "1.1"
session_id: "K-run-..."
base_commit_sha: "0123456789abcdef0123456789abcdef01234567"
base_tree_sha: "..."
docs_target_path: "docs/"
files:
  - path: "docs/architecture.md"
    operation: replace  # create | replace | delete
    before: {content_sha256: "sha256:{hash}", git_blob_oid: "...", mode: "100644"}
    after: {content_sha256: "sha256:{hash}", git_blob_oid: "...", mode: "100644"}
    source_kind: as_built
    provenance_refs: ["reconstructed_architecture.yaml#..."]
    confidence: high
candidate_payload_manifest_sha256: "sha256:{hash}"
expected_result_tree_sha: "..."
```

Для `create` поле `before` равно null, для `delete` — `after: null`; остальные комбинации запрещены schema. Candidate payload содержит только after bytes для create/replace. K0 до approval проверяет blob ids/expected tree через pinned Git object format без записи branch ref.

Перед side effect K0 публикует `docs_publish_intent.yaml`, после него — `documentation_commit_manifest.yaml`:

```yaml
schema_id: k/docs-publish-intent
schema_version: "1.0"
session_id: "K-run-..."
repository_fingerprint: "sha256:{hash}"
base_commit_sha: "0123456789abcdef0123456789abcdef01234567"
branch_ref: "refs/heads/k-audit/K-run-..."
expected_old_ref: null
candidate_manifest_sha256: "sha256:{hash}"
disposition_sha256: "sha256:{hash}"  # null только для documentation_only; тогда intent также bind'ит scope/trigger
documentation_approval_sha256: "sha256:{hash}"
authorization_expires_at: "2026-07-15T10:30:00Z"
expected_result_tree_sha: "..."
commit_metadata:
  parent: "0123456789abcdef0123456789abcdef01234567"
  author: "K Documentation Publisher <k-publisher@local.invalid>"
  authored_at: "2026-07-14T10:31:00Z"
  message_sha256: "sha256:{hash}"
  trailers: {K-Session: "K-run-...", K-Candidate: "sha256:{hash}", K-Approval: "sha256:{hash}"}
idempotency_key: "sha256:{session+candidate+approval}"
```

Commit manifest фиксирует intent hash, old/new ref, parent/tree/commit OIDs, actual allowed-path diff hash, CAS result и `reconciliation: newly_published | adopted_existing`. Он считается valid только при exact match intent; обнаруженный commit с иным parent/tree/diff/trailer не усыновляется.

### 12.11 Approval receipt

```yaml
schema_id: k/approval-receipt
schema_version: "1.0"
event_id: "EVT-docs"
decision_request_id: "K-run-.../K12b/attempt-1"
session_id: "K-run-..."
action: approved_for_branch_commit
binding_sha256: "sha256:{hash}"
provider: "repository-governance-provider"
policy_revision: "..."
subject: "..."
verified_role: repository_docs_approver
nonce: "..."
issued_at: "2026-07-14T10:30:00Z"
expires_at: "2026-07-15T10:30:00Z"
provider_signature_digest: "sha256:{hash}"
authorization_constraints: {allow_post_expiry_adoption: true}
received_at: "2026-07-14T10:30:01Z"
```

Receipt immutable. Ledger uniqueness key — `(provider, event_id, decision_request_id)`; тот же key допустим повторно только с идентичным binding/action/subject/role/signature digest.

Новая privileged transaction и CAS ref update допустимы только пока receipt не истёк; один лишь ранее записанный intent срок не продлевает. Непосредственно перед CAS K0 сверяет trusted clock/receipt и durable записывает `pre_cas_authorization_check` в hash-chained log. Если при resume ref ещё не обновлён, а receipt уже истёк, K0 не выполняет CAS и требует новый K12b decision. Если exact ref/commit уже существует и log доказывает pre-CAS check при действующем receipt, поздний resume может только adopt его при `allow_post_expiry_adoption`; никакой новый commit/ref mutation после expiry не выполняется. Risk/coverage expiry также не продлевается recovery-механикой и отражается в re-audit/backlog policy.

---

## 13. Директории артефактов

```
schemas/k/                                 # versioned normative schemas + conformance fixtures
TEST WORKFLOW/11. K. Audit & Documentation RS/
  sessions/{session_id}/
    k_trigger_signal.yaml
    normalized_k_trigger_signal.yaml
    tool_execution_policy.yaml
    authorization_context.normalized.yaml
    source_snapshot_manifest.yaml
    a_e_baseline_manifest.normalized.yaml
    k_input_bundle_manifest.yaml
    input_access_log.jsonl
    evidence/runtime/                      # ingested immutable redacted payloads
    evidence/external/
    runtime_evidence_manifest.yaml
    external_evidence_manifest.yaml
    k_session_state.yaml
    session_artifact_manifest.yaml
    stage_manifests/                       # one validated manifest/completion marker per stage
    scale_profile.provisional.yaml
    scale_profile.yaml
    scanner_output.yaml
    repo_map.yaml
    file_level_findings.yaml
    reconstructed_architecture.yaml
    reconstructed_architecture_shards/
    interface_contract_map.yaml
    data_schema_map.yaml
    observed_implementation_map.yaml
    observed_implementation_map_shards/
    specialist_sampling_plan.yaml
    security_tool_outputs/
    security_audit_report.yaml
    requirements_coverage_shards/
    requirements_coverage_matrix.yaml
    efficiency_audit_report.yaml
    implementation_quality_report.yaml
    concurrency_distributed_behavior_audit.yaml
    ui_behavior_audit.yaml
    k9_shard_manifest.yaml
    k9_traceability_shards/
    k9_traceability_index.yaml
    traceability_gap_report.yaml
    k_audit_findings.yaml
    audit_completeness_report.yaml
    documentation/draft/
    documentation/final_candidate/
    documentation_candidate_manifest.yaml
    hitl_review_events/
    approval_receipts/
    approval_event_ledger.jsonl
    k_hitl_disposition.yaml
    k_documentation_approval.yaml
    docs_publish_intent.yaml
    documentation_commit_manifest.yaml
    k_hitl_acceptance_session.yaml
    k_layer_summary.yaml
  k_file_audit_cache.db                    # transactional + locked, §5.4
  k_audit_session_log.jsonl                # hash-chained; single writer K0
```

---

## 14. Инварианты K-слоя

1. **Enforced no-I/J trust.** K-agents receive only `k_input_bundle_manifest.yaml` allowlist; canonical-path/symlink sandbox blocks F–J/M runtime roots, `pipeline.db`, `causal_graph.db`, `tasks.db`, `j_runtime.db` and J reports. No I/J artifact has legitimate K use in R6.
2. **Content-addressed A–E baseline.** K reads only exact hash-verified entries in the pinned manifest; heuristic latest lookup is forbidden.
3. **No F/G/H normative baseline.** K9 compares only E→D→C→B→A; K-UI is code-derived behavior audit, not design comparison.
4. **Immutable target identity.** Scanner/evidence use a detached snapshot of full resolved commit/tree SHA, including pinned submodule/LFS identities; dirty source checkout never participates.
5. **Inventory completeness before interpretation.** Every in-scope tracked file is parsed, partial/failed/unsupported or deliberately excluded with reason. Critical unknown surface blocks product acceptance.
6. **Independent observed map before comparison.** K2/K3 reconstruct observed capabilities before K4–K9/K-UI may compare them with product claims.
7. **Scope-safe outcomes.** `product_acceptance` requires `full_system`; subset/audit/docs modes cannot emit a global product outcome (§3.1).
8. **No product-code mutation.** Audit snapshot is read-only. After K12b, deterministic K0 publisher may create only exact approved docs blobs/tree under canonical allowlist using prewritten intent and CAS; K never switches the user's checkout, pushes or merges.
9. **No autonomous remediation routing.** K records owned/expiring backlog entries but never creates J tasks or chooses a repair route.
10. **Schema-valid atomic stages.** All outputs validate against the versioned registry. A multi-file stage becomes completed only after its output manifest and completion marker; K0 is the sole state/log/cache writer.
11. **Deterministic severity/disposition.** Raw severity and lineage are immutable; K11 changes reviewed severity only with reason/evidence. For terminal disposition, non-waivable blocking permits only reject/escalate; non-terminal dispute may reopen review but cannot accept/downgrade the risk. Any waiver/fix-required rules out plain accepted.
12. **Hard constraints stay hard.** Pinned non-waivable legal/ethics/regulatory violations are blocking; other A/C constraint violations are at least major until their mapping is refuted.
13. **Sampling is planned and provable.** Standard samples use a deterministic plan/seed and record unknowns. Deep requires every supported eligible item assigned and fully read with `sampled_items: 0`; K11 reconciles counts to scanner inventory. Neither mode is represented as stronger evidence than it is.
14. **Cache correctness and isolation.** Reuse requires repository identity plus all content/graph/tool/prompt/model/config hashes; uncertain ancestry or graph semantics triggers conservative invalidation.
15. **Tagged, verifiable evidence only.** Evidence uses §12.0 variants and resolved hashes; external citations resolve through the normalized manifest/payload/locator, and missing implementation requires `absence_search` with inventory/query/exclusions/failed scopes.
16. **Human-initiated sessions.** No daemon/scheduler starts K; each run begins with an actor-identified human trigger.
17. **Hostile-input execution boundary.** Product code/hooks/plugins/lifecycle scripts are not executed. Tools are pinned and sandboxed offline by default; model egress is governed separately and pre-LLM secret scan is mandatory.
18. **Enforced resource limits.** Missing enforcement capability or any timeout/memory/output breach fails the stage, never yields partial pass.
19. **Complete resumability.** State covers preflight through K12/docs/summary with core/stage fingerprints, append-only attempts, immutable approval receipts, transition-driven invalidation and intent/CAS side-effect reconciliation.
20. **Two-phase scale and partition completeness.** K2/K3/K5 use immutable phase-A repository/baseline gates; K9 requires finalized phase B with capability/coverage-universe/token gates. K2/K3/K5/K9/K11/K10 shard/stream above gates; every expected item/cross-boundary edge is covered or unresolved, and unresolved shards create completeness findings.
21. **Evidence assurance gating.** Runtime-dependent claims in K4–K9/K-UI without fresh commit/release-bound evidence are `insufficient_evidence`; summary declares `assurance_level`.
22. **Verified, hash-bound HITL authority.** Self-asserted roles are insufficient. Authorization provider/policy, actor subject, nonce/expiry and approval event bind to exact action, findings, completeness, target tree and final candidate hashes; changed input or replay invalidates approval.
23. **Terminal audit trail.** Even preflight failure/cancellation emits `k_layer_summary.yaml` plus hash-chained session-log entry; execution status is separate from product outcome.
24. **Documentation does not overclaim.** K10 preserves provenance/confidence/coverage and applies redaction policy; only deterministic K0 publisher may commit the exact approved candidate/result tree.

---

## 15. Ростер (сводно) и связь со смежными слоями

| Вход | Источник | Использование в K |
|---|---|---|
| Immutable product snapshot | full resolved commit/tree SHA + source manifest | Первичный источник реконструкции |
| A/B/C/D/E артефакты | content-addressed `a_e_baseline_manifest.yaml` | Pinned эталон сравнения (K9), источник требований/историй (K5) |
| Runtime/external evidence | locally ingested redacted payloads + hashes | Optional evidence с subject/freshness binding |
| k_trigger_signal.yaml | человек | Границы и версия сессии |

| Выход | Получатель | Условие |
|---|---|---|
| k_layer_summary.yaml | человек / архив пайплайна | Любой terminal исход, включая preflight failure |
| system documentation candidate / audit-branch commit | владелец продукта | Exact K12b hash approval; merge вне K |
| k_audit_findings.yaml | человек, потенциально — вход для ручного создания новых J-задач | Всегда |
| audit_completeness_report.yaml | K12 / человек | Для audit/product modes |
| k_hitl_acceptance_session.yaml | человек, архив | Если K12 достигнут: terminal mode-valid index immutable phase artifacts, review-event chain и approval ledger |

K-слой не имеет "выхода" в I/J в смысле автоматического хендоффа — пайплайн A→K заканчивается на K12; повторный проход через J (если remediation потребует нового кода) — отдельный, вручную инициированный проход J-слоя с новым task_spec, вне механики K.

---

## 16. Открытые вопросы

```
OQ-K-001: CLOSED in R3. F/G/H не добавляются как normative baseline,
          но добавлен условный K-UI для code-derived проверки UI behaviour
          against E/D/C without pixel-perfect design comparison.
OQ-K-002: CLOSED as architecture decision. `k_repo_scan.py`/scanner profile —
          обязательная preflight dependency (§5.6). IMPLEMENTATION BLOCKER:
          в workspace пока нет scanner executable, schema registry,
          supported-language matrix и conformance fixtures; без них K не стартует.
OQ-K-003: маппинг tiered models (§5.5) на конкретные модели — вынесен
          в config K0; exact revision/context/egress profile всё равно hash-pinned.
OQ-K-004: CLOSED in R6. Scale decision двухфазный и monotonic; финальный
          capability/requirement/token pass обязателен перед K9. Sharding/streaming
          применяется к K2/K3/K9/K11/K10; oversized prompt запрещён.
OQ-K-005: CLOSED in R5. repository_docs_approver подтверждает exact candidate
          hash только для audit-branch commit. K никогда не merge/push;
          repo_merge_approver действует вне K через repository governance/PR.
OQ-K-006: CLOSED in R5. Допустим только human-initiated trigger; scheduler/cron
          не входит в текущий K-контракт.
OQ-K-007: CLOSED for R5 scope. K не исполняет hostile product code и не является
          runtime test runner. Future hermetic build/dynamic verifier потребует
          отдельного execution profile/роли, sandbox и artifact-digest binding;
          до этого действует evidence-limited acceptance из D10.
OQ-K-008: CURRENT BASELINE BLOCKER. В `TEST WORKFLOW/2.B. Concept Layer RS/`
          присутствуют coverage map и B2–B7 patches, но нет опубликованного
          B8 gatekeeper report. На текущем snapshot product_acceptance обязан
          остановиться; audit_only может продолжиться только с baseline limitation.
OQ-K-009: IMPLEMENTATION BLOCKER. Нужны authorization adapter, policy schema и
          verifier одноразовых approval events. Пока их нет, K может выполнять
          технический audit, но privileged product/risk/docs decisions обязан
          завершать как escalated/skipped, а не доверять role из YAML.
OQ-K-010: IMPLEMENTATION BLOCKER для docs publication. Нужен deterministic K0
          Git publisher с candidate/result-tree verifier, pre-side-effect intent,
          approval receipt ledger, no-filter blob creation и CAS/recovery fixtures.
          До его реализации product/audit decision допустим, но docs publish — skipped.
```
