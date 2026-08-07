# Parsergen Hybrid Codegen Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Собрать один generated BSL module из canonical production-функций и явно оставленных legacy islands, не делая canonical Parser IR зависимым от legacy matcher artifact.

**Architecture:** `build_parser_ir` получает явную projection production names и строит IR только для migrated families, но использует полную lowered CFG и canonical SELECT для их решений. Новый hybrid assembler оставляет текущий legacy template/runtime, заменяет выбранные production-функции canonical fragments с совместимым optional ABI `(Родитель, ЛевыйЭлемент)`, исключает принадлежащие им synthetic analysis productions из runtime и ограничивает legacy matcher rows только legacy islands. Production CLI включает этот путь только при непустом явном `[migration].canonical_productions`; пустая конфигурация остаётся byte/parity-compatible с прежним generator.

**Tech Stack:** Python 3.13, `unittest`/`pytest`, parsergen source/lowering/analysis/Parser IR, generated BSL, TOML.

## Global Constraints

- SELECT alternatives выбранной canonical production и её synthetic decisions должны быть disjoint при configured finite `k`; порядок BSL `Если` не разрешает конфликт.
- Canonical Parser IR и canonical conditions не читают legacy matcher artifact, prefix shadowing, cycle-prefix injection или nullable fallback.
- Legacy matcher artifact строится из фактически нормализованных rows и содержит dispatch rows только для legacy islands.
- Legacy `generate_parser` и production artifacts не меняются, когда migration list пуст.
- EBNF/direct-LR synthetic CFG используется только для analysis; synthetic runtime functions не генерируются.
- Canonical production family не содержит arbitrary BSL actions и мигрируется целиком вместе с `Родитель`/`ЛевыйЭлемент` plumbing.
- FIRST/FOLLOW/SELECT solver не переписывается.
- Все implementation changes выполняются TDD: новый production code появляется только после наблюдаемого RED.

---

### Task 1: Projection canonical Parser IR

**Files:**
- Modify: `tools/parsergen/src/parsergen/parser_ir.py`
- Modify: `tools/parsergen/tests/test_parser_ir.py`
- Modify: `tools/parsergen/tests/test_left_fold_parser_ir.py`

**Interfaces:**
- Consumes: existing `build_parser_ir(source, lowering, resolved, analysis)`.
- Produces: `build_parser_ir(..., production_names: Collection[str] | None = None) -> ParserIr`; `None` preserves full canonical build, a collection emits only those source productions and validates only their own canonical decisions plus their owned lowering decisions.

- [ ] **Step 1: Write failing projection tests**

Add tests proving that a projected `Expr` IR:

```python
parser_ir = build_parser_ir(
    parsed.source_grammar,
    parsed.lowering,
    resolved,
    analysis,
    production_names=("Expr",),
)
assert tuple(item.name for item in parser_ir.productions) == ("Expr",)
```

accepts an untouched production containing `{Legacy = 1}`, rejects an unknown requested production, and still rejects overlapping SELECT in the selected direct-LR tail.

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```powershell
python -m pytest tests/test_parser_ir.py tests/test_left_fold_parser_ir.py -q
```

from `tools/parsergen`. Expected: projection calls fail because `production_names` is not accepted.

- [ ] **Step 3: Implement minimal projection**

Normalize requested names without reordering source productions, reject duplicates/unknown names, build only selected `SourceProduction` values, and filter canonical conflict rejection to:

```python
required_decisions = selected_source_names | owned_synthetic_decision_names
```

where owned synthetic names come from `LoweringResult.constructs` and `LoweringResult.left_recursions` whose `source_production`/`production` is selected.

- [ ] **Step 4: Run focused and full Python tests GREEN**

Run:

```powershell
python -m pytest tests/test_parser_ir.py tests/test_left_fold_parser_ir.py -q
python -m pytest -q
```

Expected: focused and full suites pass; the existing Windows symlink privilege skip may remain.

- [ ] **Step 5: Commit and push**

```powershell
git add tools/parsergen/src/parsergen/parser_ir.py tools/parsergen/tests/test_parser_ir.py tools/parsergen/tests/test_left_fold_parser_ir.py
git commit -m "Добавить projection canonical Parser IR"
git push
```

### Task 2: Canonical production fragments with explicit ABI

**Files:**
- Modify: `tools/parsergen/src/parsergen/canonical_bsl_codegen.py`
- Create: `tools/parsergen/tests/test_canonical_bsl_fragments.py`

**Interfaces:**
- Consumes: projected `ParserIr` from Task 1.
- Produces: immutable `CanonicalGeneratedFunctions(module_fragment: str, constructor_names: tuple[str, ...])` and `generate_canonical_functions(source, parser_ir, *, abi_parameters: tuple[str, ...] = ())`.

- [ ] **Step 1: Write failing fragment tests**

Use a projected direct-LR `Expr` and assert observable fragment behavior:

```python
generated = generate_canonical_functions(
    source,
    parser_ir,
    abi_parameters=("Родитель", "ЛевыйЭлемент"),
)
assert "Функция НеТерминалExpr(Родитель = Неопределено, ЛевыйЭлемент = Неопределено)" in generated.module_fragment
assert generated.module_fragment.count("Пока ") == 1
assert "Функция НеТерминалTerm" not in generated.module_fragment
```

Also assert duplicate/colliding ABI names are rejected and the existing full canonical module output stays unchanged when the new API is unused.

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```powershell
python -m pytest tests/test_canonical_bsl_fragments.py tests/test_canonical_bsl_codegen.py -q
```

Expected: import/API failure for `generate_canonical_functions`.

- [ ] **Step 3: Extract the shared renderer minimally**

Reuse `_CanonicalBslGenerator` rendering and validation without loading/substituting the full template. ABI parameters are optional defaulted BSL parameters prepended only to exported production signatures; internal canonical calls continue to pass only declared grammar arguments. Validate ABI identifiers and collisions against declared parameters and generated locals.

- [ ] **Step 4: Run focused and full Python tests GREEN**

Run:

```powershell
python -m pytest tests/test_canonical_bsl_fragments.py tests/test_canonical_bsl_codegen.py tests/test_canonical_bsl_left_fold.py -q
python -m pytest -q
```

- [ ] **Step 5: Commit and push**

```powershell
git add tools/parsergen/src/parsergen/canonical_bsl_codegen.py tools/parsergen/tests/test_canonical_bsl_fragments.py
git commit -m "Генерировать canonical production fragments"
git push
```

### Task 3: Hybrid module assembler and legacy row isolation

**Files:**
- Create: `tools/parsergen/src/parsergen/hybrid_bsl_codegen.py`
- Modify: `tools/parsergen/src/parsergen/bsl_codegen.py`
- Create: `tools/parsergen/tests/test_hybrid_bsl_codegen.py`
- Modify: `tools/parsergen/tests/test_bsl_codegen.py`

**Interfaces:**
- Consumes: full lowered `Grammar`, `ResolvedGrammar`, `AnalysisResult`, `SourceGrammar`, `LoweringResult`, projected `ParserIr`, entrypoints.
- Produces: `generate_hybrid_parser(...) -> GeneratedParser` with one BSL module, canonical function replacements and a legacy-only SELECT ValueTable.
- Internal legacy hook: `BslGenerator` accepts immutable function overrides, omitted synthetic names, optional support fragment and matcher-row production filter; defaults preserve old behavior exactly.

- [ ] **Step 1: Write failing hybrid behavior tests**

Build a grammar where legacy `S` calls canonical direct-LR `Expr`, and canonical `Expr` calls legacy `Term`. Assert:

```python
module = generated.module_text
assert module.count("Функция НеТерминалExpr(") == 1
assert "Функция НеТерминалS(" in module
assert "Функция НеТерминалTerm(" in module
assert "Функция НеТерминал__parsergen_ebnf__" not in module
assert "НомерВариантаПродукции" not in expr_function
assert expr_function.count("Пока ") == 1
```

Decode the actual `generated.select_table` and assert no row has `Продукция == "Expr"` or a synthetic production, while a multi-alternative legacy island still has its rows. Add error tests for a requested canonical name missing from IR and for EBNF/LR synthetic constructs owned by a legacy island.

- [ ] **Step 2: Run focused tests and verify RED**

Run:

```powershell
python -m pytest tests/test_hybrid_bsl_codegen.py tests/test_bsl_codegen.py -q
```

Expected: import/API failure for `generate_hybrid_parser`.

- [ ] **Step 3: Add default-preserving legacy assembly hooks**

Keep `generate_parser(...)` unchanged. Add private/defaulted constructor policy to `BslGenerator` so the normal path renders all functions and all normalized artifact rows exactly as before. Filter rows only after `build_legacy_matcher_artifact`, never through a second approximate matcher model.

- [ ] **Step 4: Implement hybrid assembly**

`generate_hybrid_parser` validates ownership, renders canonical fragments with ABI `("Родитель", "ЛевыйЭлемент")`, supplies `ТипТокенаПросмотра` and canonical syntax-error helpers, replaces only selected public functions, omits only selected-owned synthetic CFG functions, and delegates all untouched functions/actions to `BslGenerator`.

- [ ] **Step 5: Prove legacy parity and hybrid GREEN**

Run:

```powershell
python -m pytest tests/test_hybrid_bsl_codegen.py tests/test_bsl_codegen.py tests/test_artifacts.py tests/test_legacy_matcher_artifact.py -q
python -m pytest -q
```

Expected: hybrid tests pass and existing reference parser artifact tests remain unchanged.

- [ ] **Step 6: Commit and push**

```powershell
git add tools/parsergen/src/parsergen/hybrid_bsl_codegen.py tools/parsergen/src/parsergen/bsl_codegen.py tools/parsergen/tests/test_hybrid_bsl_codegen.py tools/parsergen/tests/test_bsl_codegen.py
git commit -m "Собрать hybrid canonical и legacy parser"
git push
```

### Task 4: Explicit migration config and CLI route

**Files:**
- Modify: `tools/parsergen/src/parsergen/config.py`
- Modify: `tools/parsergen/src/parsergen/cli.py`
- Modify: `tools/parsergen/tests/test_config.py`
- Modify: `tools/parsergen/tests/test_cli.py`
- Modify: `tools/parsergen/tests/test_repository_grammar.py`

**Interfaces:**
- Consumes: optional TOML table `[migration] canonical_productions = ["Expr"]`.
- Produces: `ParsergenConfig.canonical_productions: tuple[str, ...]`; `generate` uses legacy backend when empty and hybrid backend when non-empty.

- [ ] **Step 1: Write failing config tests**

Assert empty/default configuration gives `canonical_productions == ()`, a valid string array preserves order, and non-array/empty/duplicate names fail with explicit `ValueError`.

- [ ] **Step 2: Write failing CLI route tests**

Use a temporary conflict-free mixed grammar and real artifact layout. Assert `generate --check` selects hybrid output only with the migration table, and a selected production with arbitrary action fails before writing artifacts. Assert the existing repository config without migration still compares through the legacy path.

- [ ] **Step 3: Run focused tests and verify RED**

Run:

```powershell
python -m pytest tests/test_config.py tests/test_cli.py tests/test_repository_grammar.py -q
```

- [ ] **Step 4: Implement config parsing and CLI routing**

Build projected Parser IR only for configured names, then call `generate_hybrid_parser`; do not weaken `validate_grammar` or suppress `LLK202`. A grammar with any canonical validation error remains rejected, so production opt-in occurs only after its two known conflicts are resolved explicitly.

- [ ] **Step 5: Run all gates GREEN**

Run:

```powershell
python -m pytest -q
python -m parsergen validate --config ..\..\..\parsergen.toml
python -m parsergen generate --config ..\..\..\parsergen.toml --check
```

from `tools/parsergen/src`. Expected for the unchanged production config: Python suite GREEN; repository commands retain the two known `LLK202` failures and do not change artifacts.

- [ ] **Step 6: Commit and push**

```powershell
git add tools/parsergen/src/parsergen/config.py tools/parsergen/src/parsergen/cli.py tools/parsergen/tests/test_config.py tools/parsergen/tests/test_cli.py tools/parsergen/tests/test_repository_grammar.py
git commit -m "Подключить явный hybrid migration route"
git push
```

### Task 5: Architecture evidence and next-slice gate

**Files:**
- Modify: `docs/architecture/parser-generator.md`
- Modify: `docs/superpowers/plans/2026-08-07-parsergen-hybrid-codegen.md`

**Interfaces:**
- Consumes: verified implementation and command outputs from Tasks 1–4.
- Produces: documented hybrid ownership/ABI/artifact invariants and explicit blocker list for the first production arithmetic slice.

- [ ] **Step 1: Document verified boundary**

Record that full validation remains canonical and strict, hybrid generation never uses `if` order to resolve overlaps, canonical functions contain no matcher-table calls, and legacy rows are filtered from the already normalized real artifact representation.

- [ ] **Step 2: Record verification evidence**

Update this plan checkboxes and append exact test counts, known repository diagnostics, artifact parity result and generated hybrid shape assertions.

- [ ] **Step 3: Run final diff and status checks**

Run:

```powershell
git diff --check
git status --short
```

- [ ] **Step 4: Commit and push**

```powershell
git add docs/architecture/parser-generator.md docs/superpowers/plans/2026-08-07-parsergen-hybrid-codegen.md
git commit -m "Документировать hybrid parser migration"
git push
```

## Self-review

- Spec coverage: projection, canonical/legacy isolation, exact normalized legacy rows, common generated module, ABI boundary, synthetic CFG omission, strict canonical conflicts, CLI opt-in, legacy parity and production cutover gate each have an owning task.
- Intentional non-scope: production grammar and query model remain unchanged in this infrastructure plan; their first arithmetic slice follows only after both repository `LLK202` conflicts are structurally resolved and its YAxUnit characterization is updated from known right associativity to required left associativity.
- Placeholder scan: plan contains no deferred implementation placeholders.
- Type consistency: Tasks 2–4 consistently consume projected `ParserIr`; only the hybrid assembler knows both canonical fragments and legacy `GeneratedParser` artifacts.
