# Parsergen Minimal Multi-Target Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Оставить в parsergen один combined frontend, один общий IR и два renderer — canonical BSL и direct Python — удалив multiple profiles, scoped projection и legacy/hybrid BSL paths.

**Architecture:** Combined grammar компилируется в общий `ParserIr`; после обычных IR-оптимизаций общий immutable `RecursionPlan` описывает безопасные циклы и continuations. Canonical BSL и direct Python renderers потребляют одни и те же IR/recursion decisions, но генерируют синтаксис своего языка.

**Tech Stack:** Python 3.11+, pytest, dataclasses, generated BSL/Python source.

**Spec:** `docs/superpowers/specs/2026-09-05-parsergen-minimal-multi-target-design.md`

## Global Constraints

- Production authoring format — один combined `.grammar` с декларативными semantic actions.
- Multiple semantic profiles, separated frontend, `AppendNearestOwner` и scoped owner runtime удаляются полностью.
- `bsl_codegen.py`, `semantic_actions.py`, `hybrid_bsl_codegen.py` и migration selector `canonical_productions` удаляются полностью.
- Остаются ровно два renderer: canonical BSL и direct Python; runtime Python VM запрещён.
- Общий `ParserIr` не дублируется; `RecursionPlan` ссылается на IR sites и не является вторым execution IR.
- Commit `a012492` и его три regression сохраняются.
- Все три freshly generated QueryConsole BSL artifacts должны сохранить точные bytes baseline.
- Произвольные inline BSL actions становятся явно неподдерживаемым legacy syntax.
- Никаких Worker/hot-reload/BSL-production-name heuristics в parsergen.
- История опубликованного PR не переписывается; force push запрещён.
- Все команды в плане выполняются из корня repository.

---

### Task 1: Зафиксировать честные BSL byte baselines

**Files:**
- Modify: `tools/parsergen/tests/test_direct_python_bsl_artifact_fence.py`

**Interfaces:**
- Consumes: `load_config`, `compile_from_config`, `generate_from_compilation`, `render_artifacts`.
- Produces: `fresh_repository_artifacts() -> ArtifactSet`, используемый последующими задачами как raw-byte gate.

- [ ] **Step 1: Сделать тест чувствительным к output генератора**

  Заменить единственную проверку `git show HEAD` на helper, который загружает
  `parsergen.toml`, компилирует repository grammar и вызывает
  `render_artifacts(generate_from_compilation(...))`. Для доказательства
  чувствительности сначала указать для `object_module` digest из 64 нулей.

- [ ] **Step 2: Наблюдать RED**

  Run:

  ```powershell
  python -m pytest -q tools/parsergen/tests/test_direct_python_bsl_artifact_fence.py
  ```

  Expected: FAIL, actual digest начинается с `358a6123` и не равен нулевому.

- [ ] **Step 3: Зафиксировать два независимых raw baseline**

  Fresh `ArtifactSet` должен иметь SHA256:

  ```text
  object_module       358a6123f91cd9068a08c76b3849ffad69f10eb0c7b2ed90b650f87304b960e8
  select_template     acb80f86f739d5a4a54fe7d6f2c85cdc57a2d664d779a1f1e51a0aaf54a059c1
  identifier_template 13472cb0e1482b5c590a306fe6fc119d026546069e717d8eadd010b6a8661ef6
  ```

  Отдельная проверка Git blobs сохраняет:

  ```text
  ObjectModule f536869601e718ca02f026d0ecb8f733d8688ecd038f70f6b5e8cd08dbe4fbbf
  SELECT       e26a6b3b4fe08455462145de3243338d5da1c8bbb657321a2162b0abe541e208
  Identifiers  107fdbdefd57f5b6fe0658037b67806fc95f24a27d3e948eeeeaeb3335ffeff2
  ```

  Дважды вызвать fresh generation и дополнительно проверить полное равенство
  двух `ArtifactSet`, не только hashes.

- [ ] **Step 4: Наблюдать GREEN и commit**

  Run focused test и `git diff --check`. Commit:

  ```text
  test(parsergen): verify freshly generated BSL bytes
  ```

---

### Task 2: Удалить separated и scoped frontend

**Files:**
- Delete: `tools/parsergen/src/parsergen/syntax_grammar_parser.py`
- Delete: `tools/parsergen/src/parsergen/semantic_profile_parser.py`
- Delete: `tools/parsergen/src/parsergen/semantic_profile_binding.py`
- Delete: `tools/parsergen/src/parsergen/separated_model.py`
- Delete: `tools/parsergen/src/parsergen/scoped_append_validation.py`
- Modify: `tools/parsergen/src/parsergen/__init__.py`
- Modify: `tools/parsergen/src/parsergen/source_model.py`
- Modify: `tools/parsergen/src/parsergen/grammar_parser.py`
- Modify: `tools/parsergen/src/parsergen/lowering.py`
- Modify: `tools/parsergen/src/parsergen/left_recursion.py`
- Modify: `tools/parsergen/src/parsergen/binding_validation.py`
- Modify: `tools/parsergen/src/parsergen/source_validation.py`
- Modify: `tools/parsergen/src/parsergen/parser_ir.py`
- Modify: `tools/parsergen/src/parsergen/parser_ir_optimization.py`
- Modify: `tools/parsergen/src/parsergen/direct_render_analysis.py`
- Modify: `tools/parsergen/src/parsergen/python_direct_codegen.py`
- Modify: `tools/parsergen/src/parsergen/python_semantic_codegen.py`
- Modify: `tools/parsergen/src/parsergen/canonical_bsl_codegen.py`
- Delete: `tools/parsergen/tests/test_syntax_grammar_parser.py`
- Delete: `tools/parsergen/tests/test_semantic_profile_parser.py`
- Delete: `tools/parsergen/tests/test_semantic_profile_binding.py`
- Delete: `tools/parsergen/tests/test_separated_semantics_parser_ir.py`
- Delete: `tools/parsergen/tests/test_separated_semantics_legacy.py`
- Delete: `tools/parsergen/tests/test_scoped_append_validation.py`
- Delete: `tools/parsergen/tests/test_scoped_append_python_runtime.py`
- Delete: `tools/parsergen/tests/test_scoped_append_parser_ir.py`
- Delete: `tools/parsergen/tests/test_scoped_append_backend_fences.py`
- Create: `tools/parsergen/tests/test_minimal_public_surface.py`
- Modify: remaining direct/binding/source/IR tests that contain scoped-only cases.

**Interfaces:**
- Consumes: combined `parse_grammar()` and Task 1 byte gate.
- Produces: source/IR/direct pipeline with no separated/scoped symbols or optimizer barrier.

- [ ] **Step 1: Добавить RED-тест минимальной поверхности**

  Создать `tests/test_minimal_public_surface.py`, который импортирует
  `parsergen` и проверяет отсутствие public names:

  ```python
  REMOVED = (
      "parse_syntax_grammar",
      "parse_semantic_profile",
      "bind_semantic_profile",
      "SemanticProfile",
      "AppendNearestOwner",
  )
  assert all(not hasattr(parsergen, name) for name in REMOVED)
  ```

  До удаления тест должен упасть как минимум на первых трёх именах.

- [ ] **Step 2: Удалить frontend и scoped модели**

  Удалить пять source-файлов и их exports. В shared-файлах удалить только
  branches для `SemanticProfile`, `SourceScopedValue`, `AppendNearestOwner`,
  owner state и scoped effects. Сохранить изменения `a012492`, ordinary
  `AppendCollection`, cardinality checks и direct continuation code.

- [ ] **Step 3: Восстановить полный optimizer**

  Удалить early return из `optimize_parser_ir()` при наличии scoped effect и
  удалить сам обход scoped payload. Reachability, specialization и path facts
  должны снова выполняться без глобального feature flag.

- [ ] **Step 4: Очистить тесты и доказать отсутствие machinery**

  Run:

  ```powershell
  rg -n "SourceScopedValue|AppendNearestOwner|SemanticProfile|parse_syntax_grammar|parse_semantic_profile|bind_semantic_profile|mutable_owner_types|owner_stack|enqueue_sequence" tools/parsergen/src tools/parsergen/tests
  ```

  До GREEN допустимые совпадения отсутствуют полностью. Затем run:

  ```powershell
  python -m pytest -q tools/parsergen/tests/test_minimal_public_surface.py tools/parsergen/tests/test_binding_validation.py tools/parsergen/tests/test_source_validation.py tools/parsergen/tests/test_parser_ir.py tools/parsergen/tests/test_parser_ir_optimization.py tools/parsergen/tests/test_direct_render_analysis.py tools/parsergen/tests/test_python_direct_rendering.py
  python -m pytest -q tools/parsergen/tests/test_direct_python_bsl_artifact_fence.py
  ```

- [ ] **Step 5: Commit**

  ```text
  refactor(parsergen): remove projection semantics
  ```

---

### Task 3: Оставить один canonical BSL renderer

**Files:**
- Delete: `tools/parsergen/src/parsergen/bsl_codegen.py`
- Delete: `tools/parsergen/src/parsergen/semantic_actions.py`
- Delete: `tools/parsergen/src/parsergen/hybrid_bsl_codegen.py`
- Modify: `tools/parsergen/src/parsergen/canonical_bsl_codegen.py`
- Modify: `tools/parsergen/src/parsergen/cli.py`
- Modify: `tools/parsergen/src/parsergen/config.py`
- Modify: `parsergen.toml`
- Delete: `tools/parsergen/tests/test_bsl_codegen.py`
- Delete: `tools/parsergen/tests/test_semantic_actions.py`
- Delete: `tools/parsergen/tests/test_hybrid_bsl_codegen.py`
- Modify: `tools/parsergen/tests/test_cli.py`
- Modify: `tools/parsergen/tests/test_config.py`
- Modify: `tools/parsergen/tests/test_repository_grammar.py`
- Modify or remove legacy-only: `tools/parsergen/tests/test_migration_audit.py`

**Interfaces:**
- Consumes: combined `SourceGrammar`, full `ParserIr`, neutral `GeneratedParser` from `generated_parser.py`.
- Produces: `generate_canonical_parser(...) -> GeneratedParser`; CLI всегда использует этот path.

- [ ] **Step 1: Добавить RED-тест единственного BSL path**

  Расширить `test_minimal_public_surface.py`: modules `parsergen.bsl_codegen`,
  `parsergen.semantic_actions`, `parsergen.hybrid_bsl_codegen` не должны
  находиться через `importlib.util.find_spec`; `ParsergenConfig` не должен
  иметь `canonical_productions`; TOML с `[migration]` должен давать явный
  `ValueError` о неизвестной секции.

- [ ] **Step 2: Удалить legacy/hybrid и migration routing**

  Canonical generator возвращает neutral `GeneratedParser` напрямую. CLI
  строит IR для полного достижимого graph от config entrypoints и вызывает
  canonical generator без списка migrated productions. Удалить три modules,
  migration config и legacy-only tests.

- [ ] **Step 3: Зафиксировать отказ raw inline Action**

  Combined grammar с raw inline action должна завершать validation до
  generation с точным diagnostic `arbitrary source actions require
  declarative bindings`. Декларативная combined grammar должна успешно
  генерировать BSL и Python.

- [ ] **Step 4: Проверить production grammar и bytes**

  Run:

  ```powershell
  python -m pytest -q tools/parsergen/tests/test_minimal_public_surface.py tools/parsergen/tests/test_cli.py tools/parsergen/tests/test_config.py tools/parsergen/tests/test_canonical_bsl_codegen.py tools/parsergen/tests/test_repository_grammar.py tools/parsergen/tests/test_direct_python_bsl_artifact_fence.py
  python -m parsergen validate --config parsergen.toml
  python -m parsergen generate --config parsergen.toml --check
  ```

  Fresh byte hashes из Task 1 обязаны остаться неизменными.

- [ ] **Step 5: Commit**

  ```text
  refactor(parsergen): remove legacy BSL generator
  ```

---

### Task 4: Выделить общий RecursionPlan

**Files:**
- Create: `tools/parsergen/src/parsergen/recursion_plan.py`
- Modify: `tools/parsergen/src/parsergen/direct_render_analysis.py`
- Modify: `tools/parsergen/src/parsergen/python_direct_codegen.py`
- Modify: `tools/parsergen/src/parsergen/canonical_bsl_codegen.py`
- Create: `tools/parsergen/tests/test_recursion_plan.py`
- Modify: `tools/parsergen/tests/test_direct_render_analysis.py`
- Modify: `tools/parsergen/tests/test_python_direct_rendering.py`
- Modify: `tools/parsergen/tests/test_canonical_bsl_codegen.py`

**Interfaces:**
- Produces: `analyze_recursion_plan(source_grammar: SourceGrammar, parser_ir: ParserIr) -> RecursionPlan`.
- `RecursionPlan.sites` состоит из immutable `RecursiveCallSite`; каждый site содержит `IrSite`, kind, result-flow и optional `ContinuationLayout` со ссылками на исходные operation indices.
- `DirectRenderAnalysis` содержит `recursion_plan: RecursionPlan`, но не повторяет eligibility analysis.

- [ ] **Step 1: Добавить RED-тест общего plan**

  Для combined grammars проверить:

  ```text
  <S> ::= ITEM <S> | STOP
  <S> ::= @Link Value = ITEM Rest = <S> Kind := Истина | @End STOP
  <S> ::= 'a' -= <S> | @End STOP
  ```

  Первый получает `tail_loop`, второй `local_continuation` с constant suffix,
  третий не получает unsafe tail transformation. Тест импортирует новый
  `parsergen.recursion_plan`, поэтому до implementation падает import error.

- [ ] **Step 2: Перенести analysis без второго IR**

  Переместить `IrSite`, recursion kinds, result-flow, continuation slots и
  exact-site/liveness classification из `direct_render_analysis.py` в новый
  module. Python-specific schema analysis остаётся в direct module. Ни одна
  operation/branch не копируется в plan.

- [ ] **Step 3: Подключить Python renderer**

  Заменить private recursion side tables на `RecursionPlan`. Все tests commit
  `a012492`, 1 500/5 000 list tests, spans и error parity остаются GREEN.

- [ ] **Step 4: Подключить canonical BSL renderer**

  Для `tail_loop` canonical BSL function не должна содержать self-call и
  должна содержать `Пока Истина Цикл`/`КонецЦикла`. Для continuation renderer
  использует локальный stack и LIFO unwind согласно общему plan. Eligibility
  заново в BSL renderer не вычисляется.

- [ ] **Step 5: Проверить оба targets и production bytes**

  Run:

  ```powershell
  python -m pytest -q tools/parsergen/tests/test_recursion_plan.py tools/parsergen/tests/test_direct_render_analysis.py tools/parsergen/tests/test_python_direct_rendering.py tools/parsergen/tests/test_canonical_bsl_codegen.py tools/parsergen/tests/test_direct_python_bsl_artifact_fence.py
  ```

  QueryConsole имеет 0 recursive plan sites после текущей IR optimization;
  его BSL bytes не меняются.

- [ ] **Step 6: Commit**

  ```text
  refactor(parsergen): share recursion plan across targets
  ```

---

### Task 5: Завершить package и интеграцию с master

**Files:**
- Modify: `tools/parsergen/pyproject.toml`
- Modify: `docs/architecture/parser-generator.md`
- Modify: `tools/parsergen/PYTHON_TARGET.md`
- Modify: superseded specs/plans status headers.

**Interfaces:**
- Consumes: Tasks 1–4.
- Produces: parsergen `0.3.0`, чистый mergeable PR head и проверенный commit для runtime migration.

- [ ] **Step 1: Обновить документацию и версию**

  Установить `version = "0.3.0"`. Документировать только combined frontend,
  общий IR/RecursionPlan и два renderers. Старые separated/scoped документы
  пометить `Superseded by 2026-09-05-parsergen-minimal-multi-target-design.md`;
  исторические evidence не удалять.

- [ ] **Step 2: Выполнить static absence gates**

  Run source search из Task 2 и дополнительный поиск:

  ```powershell
  rg -n "bsl_codegen|semantic_actions|hybrid_bsl_codegen|canonical_productions" tools/parsergen/src tools/parsergen/tests parsergen.toml
  ```

  Совпадения допускаются только в отрицательном test fixture string или
  release/migration note, но не в executable source/imports.

- [ ] **Step 3: Подмешать актуальный master без переписывания истории**

  Выполнить `git fetch origin master`, затем обычный `git merge origin/master`.
  При конфликте остановиться и разрешать каждый файл по spec, не использовать
  `ours/theirs` для всего дерева.

- [ ] **Step 4: Выполнить полную проверку**

  ```powershell
  python -B -m pytest -p no:cacheprovider tools/parsergen/tests
  python -B -m parsergen validate --config parsergen.toml
  python -B -m parsergen generate --config parsergen.toml --check
  git diff --check origin/master...HEAD
  ```

  Повторить fresh BSL byte gate отдельной командой и сохранить hashes в
  implementer report.

- [ ] **Step 5: Commit документации/версии**

  ```text
  docs(parsergen): finalize minimal multi-target architecture
  ```

  Merge commit master, если создан, остаётся отдельным commit.
