# Parsergen Decision DAG Runtime Evidence Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Measure actual lookahead calls, nonterminal calls, decision-region visits, and maximum parser depth without affecting timing, then publish a three-way legacy/pre-DAG/post-DAG performance comparison.

**Architecture:** Keep the production parser uninstrumented and generate a separate test-only parser DataProcessor from the same grammar and optimized Parser IR. The existing YAxUnit benchmark continues to time the production parser, then runs one untimed instrumented pass per corpus; the final report combines this evidence with the separately captured `old_parser` baseline.

**Tech Stack:** Python parsergen, optional generated BSL instrumentation, EDT metadata in the `yaxunit` extension, YAxUnit server tests, UTF-8 JSON/Markdown evidence.

## Global Constraints

- Execute this plan only after `2026-08-08-parsergen-canonical-decision-dag.md` is complete.
- The `old_parser` and pre-DAG baseline JSON files must already exist before the final three-way report.
- Never enable counters in `QueryConsoleZUP/src/DataProcessors/Парсер`.
- Timing samples must use the uninstrumented production parser.
- Counter passes must run outside warmups and timed samples.
- The instrumented parser uses the exact production grammar, lookahead, entrypoints, generated actions, and lexer.
- Create/change metadata through EDT-MCP; validate every changed EDT object.
- Remove temporary legacy parser/lexer objects according to the separate baseline plan before MR; the generic instrumented parser may remain test-only for repeatable future measurements.

---

### Task 1: Add opt-in BSL instrumentation with zero production diff

**Files:**
- Modify: `tools/parsergen/src/parsergen/canonical_bsl_codegen.py`
- Modify: `tools/parsergen/src/parsergen/canonical_bsl_decisions.py`
- Create: `tools/parsergen/src/parsergen/templates/canonical_parser_instrumented_module.bsl`
- Create: `tools/parsergen/tests/test_canonical_bsl_instrumentation.py`

**Interfaces:**
- Produces `ParserInstrumentation(enabled: bool = False)`.
- Extends `generate_canonical_parser(..., instrumentation=ParserInstrumentation())`.
- Instrumented parser exports `СброситьСчетчикиПарсера()` and `СчетчикиПарсера()`.
- Counter fields: `lookahead_calls`, `nonterminal_calls`, `decision_region_visits`, `current_depth`, `maximum_depth`, and `constructor_actions`.

- [ ] **Step 1: Write failing default-off and enabled tests**

```python
def _build_instrumented(source: str):
    parsed = parse_grammar(source, "grammar.txt")
    assert parsed.source_grammar is not None
    assert parsed.grammar is not None
    assert parsed.lowering is not None
    resolved = resolve_grammar(parsed.grammar)
    assert resolved.grammar is not None
    analysis = compute_analysis(resolved.grammar, 2, ("S",))
    parser_ir = build_parser_ir(
        parsed.source_grammar,
        parsed.lowering,
        resolved.grammar,
        analysis,
        entrypoint_productions=("S",),
    )
    return generate_canonical_parser(
        parsed.source_grammar,
        parser_ir,
        {"Разобрать": "S"},
        instrumentation=ParserInstrumentation(enabled=True),
    )


def test_instrumentation_is_absent_by_default(self) -> None:
    module = _build("<S> ::= A | B").module_text
    self.assertNotIn("СчетчикиПарсера", module)


def test_instrumentation_counts_lookahead_functions_depth_and_regions(self) -> None:
    module = _build_instrumented("<S> ::= A | B").module_text
    self.assertIn("Процедура СброситьСчетчикиПарсера() Экспорт", module)
    self.assertIn("Счетчики.lookahead_calls = Счетчики.lookahead_calls + 1", module)
    self.assertIn("Счетчики.nonterminal_calls = Счетчики.nonterminal_calls + 1", module)
    self.assertIn("Счетчики.decision_region_visits = Счетчики.decision_region_visits + 1", module)
    self.assertIn("Счетчики.maximum_depth", module)
```

- [ ] **Step 2: Run the focused test and verify RED**

```powershell
python -m pytest tools/parsergen/tests/test_canonical_bsl_instrumentation.py -v
```

Expected: FAIL because instrumentation API/template does not exist.

- [ ] **Step 3: Implement the opt-in template and balanced depth accounting**

Add the exact option type:

```python
@dataclass(frozen=True, slots=True)
class ParserInstrumentation:
    enabled: bool = False
```

Initialize a counter structure in the instrumented template. Increment lookahead inside `ТипТокенаПросмотра`, increment decision visits immediately before each DAG root, and increment constructor actions immediately before generated constructor calls.

Wrap each generated `НеТерминал*` body so depth is decremented both on normal return and exception:

```bsl
НачатьВызовНетерминала();
Попытка
	// original generated body
	ЗавершитьВызовНетерминала();
	Возврат РезультатПродукции;
Исключение
	ЗавершитьВызовНетерминала();
	ВызватьИсключение;
КонецПопытки;
```

- [ ] **Step 4: Prove the default artifact is byte-equivalent**

```powershell
python -m pytest tools/parsergen/tests/test_canonical_bsl_instrumentation.py tools/parsergen/tests/test_reference_parser.py -v
python -m parsergen generate --config parsergen.toml --check
```

Expected: PASS; production artifacts remain current.

- [ ] **Step 5: Commit instrumentation support**

```powershell
git add tools/parsergen/src/parsergen/canonical_bsl_codegen.py tools/parsergen/src/parsergen/canonical_bsl_decisions.py tools/parsergen/src/parsergen/templates/canonical_parser_instrumented_module.bsl tools/parsergen/tests/test_canonical_bsl_instrumentation.py
git commit -m "Добавить test-only instrumentation parsergen"
```

### Task 2: Create and generate the test-only instrumented parser DataProcessor

**Files:**
- Create through EDT-MCP: `yaxunit/src/DataProcessors/КОНС_ИнструментированныйПарсер/КОНС_ИнструментированныйПарсер.mdo`
- Generate: `yaxunit/src/DataProcessors/КОНС_ИнструментированныйПарсер/ObjectModule.bsl`
- Create through EDT-MCP and generate: `yaxunit/src/DataProcessors/КОНС_ИнструментированныйПарсер/Templates/ОпределенияИдентификаторов/Template.txt`
- Create through EDT-MCP and generate: `yaxunit/src/DataProcessors/КОНС_ИнструментированныйПарсер/Templates/ТаблицаПервыхСимволовВариантов/Template.txt`
- Modify through EDT-MCP: `yaxunit/src/Configuration/Configuration.mdo`
- Create: `tools/parsergen/benchmarks/generate_instrumented_parser.py`
- Create: `tools/parsergen/tests/test_generate_instrumented_parser.py`
- Modify: `yaxunit/src/CommonModules/КОНС_ТестовыеФабрикиСлужебный/Module.bsl`

**Interfaces:**
- Script CLI: `python tools/parsergen/benchmarks/generate_instrumented_parser.py --config parsergen.toml --target yaxunit/src/DataProcessors/КОНС_ИнструментированныйПарсер [--check]`.
- Factory export: `СоздатьИнструментированныйПарсер()`.

- [ ] **Step 1: Write a failing isolated generation/check test**

Create a temporary target with the required three artifact paths, invoke the script once to generate and once with `--check`, and assert the module contains counter exports while the identifier table equals production generation.

- [ ] **Step 2: Implement the generation script without duplicating parsergen.toml**

Load `parsergen.toml`, compile normally, call canonical generation with `ParserInstrumentation(enabled=True)`, replace only the target path using `dataclasses.replace`, and reuse `render_artifacts`/artifact comparison. Return exit code `0` when clean and `3` for `--check` drift, matching the main CLI.

- [ ] **Step 3: Create exact EDT metadata and generate its artifacts**

Through EDT-MCP create DataProcessor `КОНС_ИнструментированныйПарсер` in the `yaxunit` project with object module and the two text templates named exactly like the production parser. Add it to the YAxUnit extension configuration, then run:

```powershell
python tools/parsergen/benchmarks/generate_instrumented_parser.py --config parsergen.toml --target yaxunit/src/DataProcessors/КОНС_ИнструментированныйПарсер
python tools/parsergen/benchmarks/generate_instrumented_parser.py --config parsergen.toml --target yaxunit/src/DataProcessors/КОНС_ИнструментированныйПарсер --check
```

- [ ] **Step 4: Add the test factory and validate the object**

```bsl
Функция СоздатьИнструментированныйПарсер() Экспорт
	Возврат Обработки.КОНС_ИнструментированныйПарсер.Создать();
КонецФункции
```

Use EDT-MCP to validate the new DataProcessor and changed common module. Record existing background diagnostics separately from new diagnostics.

- [ ] **Step 5: Run tests and commit**

```powershell
python -m pytest tools/parsergen/tests/test_generate_instrumented_parser.py tools/parsergen/tests/test_canonical_bsl_instrumentation.py -v
git add tools/parsergen/benchmarks/generate_instrumented_parser.py tools/parsergen/tests/test_generate_instrumented_parser.py yaxunit/src/DataProcessors/КОНС_ИнструментированныйПарсер yaxunit/src/Configuration/Configuration.mdo yaxunit/src/CommonModules/КОНС_ТестовыеФабрикиСлужебный/Module.bsl
git commit -m "Добавить инструментированный parser в YAxUnit"
```

### Task 3: Collect counters separately from timing in the existing corpus harness

**Files:**
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО/Module.bsl`
- Create: `docs/superpowers/matrices/2026-08-08-runtime-parser-decision-dag.json`

**Interfaces:**
- Each corpus result adds `instrumented_counters` with totals and normalized per-input values.
- Existing `samples_ms`, `wall_clock_median_ms`, and `wall_clock_p95_ms` still come only from production parser calls.

- [ ] **Step 1: Add RED assertions for available counters**

In `RuntimeBaselineПарсераФормируется`, assert every corpus has non-null positive `lookahead_calls`, `nonterminal_calls`, and `maximum_depth`, and a nonnegative `decision_region_visits` value. Keep the existing 20-sample timing assertions.

- [ ] **Step 2: Implement one untimed instrumented pass per corpus**

After all timing samples are complete, create the instrumented parser, reset counters, parse every corpus input exactly once with the same entrypoint selection, then read counters. Never include parser creation, reset, or counter reads in `ИзмеритьПакет`.

- [ ] **Step 3: Version and describe the output**

Set `schema_version` to `2`, identify both production and instrumented artifact hashes/LOC, and state in `measurement_scope` that timing and counters are separate passes over identical inputs.

- [ ] **Step 4: Run the YAxUnit benchmark through EDT-MCP**

Run module `КОНС_Обр_БенчмаркПарсера_МО` with the existing server launch configuration and sufficient timeout for three warmups plus 20 samples on eight corpora. Copy the emitted UTF-8 JSON sidecar exactly to `docs/superpowers/matrices/2026-08-08-runtime-parser-decision-dag.json`.

- [ ] **Step 5: Validate JSON invariants and commit**

Check eight corpora, 20 samples each, positive median/p95, positive call counts, and `current_depth == 0` after every corpus. Then commit:

```powershell
git add yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО/Module.bsl docs/superpowers/matrices/2026-08-08-runtime-parser-decision-dag.json
git commit -m "Измерить runtime Decision DAG parser"
```

### Task 4: Publish the three-way legacy/current/DAG comparison

**Files:**
- Create: `tools/parsergen/benchmarks/compare_runtime_parsers.py`
- Create: `tools/parsergen/tests/test_compare_runtime_parsers.py`
- Create: `docs/superpowers/matrices/2026-08-08-runtime-parser-three-way.md`
- Modify: `docs/superpowers/matrices/2026-08-08-decision-dag-checkpoint.md`

**Interfaces:**
- CLI consumes `--legacy`, `--pre-dag`, and `--dag` JSON paths and writes deterministic Markdown to stdout.
- Rows include median/p95 absolute values and percentage changes for the same eight corpus IDs; DAG rows additionally include calls/depth counters.

- [ ] **Step 1: Write failing comparison tests for corpus alignment and percentages**

Use three minimal JSON fixtures with two corpus IDs. Assert mismatched IDs raise `ValueError`, zero timing is rejected, and percentage change uses `(new - old) / old * 100` rounded to one decimal place.

- [ ] **Step 2: Implement deterministic comparison and provenance checks**

Require equal corpus order, input count, input length, and provenance identifiers across all three files. Include artifact hashes and runtime/platform versions in the report header. Never compare counter values from uninstrumented files.

- [ ] **Step 3: Generate the durable report from actual evidence**

```powershell
python tools/parsergen/benchmarks/compare_runtime_parsers.py --legacy docs/superpowers/matrices/2026-08-08-runtime-old-parser-baseline.json --pre-dag docs/superpowers/matrices/2026-08-08-runtime-parser-benchmark-after.json --dag docs/superpowers/matrices/2026-08-08-runtime-parser-decision-dag.json > docs/superpowers/matrices/2026-08-08-runtime-parser-three-way.md
```

- [ ] **Step 4: Investigate repeatable regressions of approximately 5% or more**

For any median or p95 regression at or above 5%, repeat the complete uninstrumented benchmark series and report both runs. Change only predicate profitability thresholds or other non-semantic codegen policy; never weaken canonical contracts.

- [ ] **Step 5: Run final verification and commit**

```powershell
python -m pytest tools/parsergen/tests/test_compare_runtime_parsers.py tools/parsergen/tests/test_canonical_bsl_instrumentation.py tools/parsergen/tests/test_generate_instrumented_parser.py -v
python tools/parsergen/benchmarks/generate_instrumented_parser.py --config parsergen.toml --target yaxunit/src/DataProcessors/КОНС_ИнструментированныйПарсер --check
python -m parsergen generate --config parsergen.toml --check
git diff --check
git add tools/parsergen/benchmarks/compare_runtime_parsers.py tools/parsergen/tests/test_compare_runtime_parsers.py docs/superpowers/matrices/2026-08-08-runtime-parser-three-way.md docs/superpowers/matrices/2026-08-08-decision-dag-checkpoint.md
git commit -m "Опубликовать сравнение runtime parser"
```

## Final Verification

Run Python checks, EDT validation for the instrumented DataProcessor and benchmark module, the YAxUnit benchmark, and confirm the production parser module contains no counter names:

```powershell
rg -n "СчетчикиПарсера|НачатьВызовНетерминала" QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl
```

Expected: no matches. The final handoff lists exact JSON/Markdown evidence, EDT diagnostics, YAxUnit results, and any repeated performance series.
