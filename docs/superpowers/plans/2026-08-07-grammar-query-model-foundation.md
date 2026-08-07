# Grammar/Query Model Foundation Phase 0–2 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Зафиксировать воспроизводимый Phase 0–2 baseline, полную карту consumers/coverage и проверяемую canonical/legacy boundary до любых изменений production grammar, query model или generated BSL parser.

**Architecture:** Новый read-only migration audit компилирует production config через существующий parsergen pipeline, публикует раздельные `structural`, `canonical`, `legacy`, `generated` и `artifacts` секции и никогда не записывает artifacts. Durable matrices связывают model contracts с фактическими EDT/Serena references и будущими Phase 2.5 tests. Existing analysis/codegen semantics не меняются.

**Tech Stack:** Python 3.11+, dataclasses, parsergen packed/factorized LL(k) analysis, pytest/unittest, JSON, Markdown, PowerShell, EDT-MCP, Serena.

## Global Constraints

- Не изменять `tools/parsergen/grammar/query-language.grammar`.
- Не изменять `QueryConsoleZUP/src/DataProcessors/Парсер` и другие production BSL modules.
- Не изменять query model factories или properties.
- Не изменять nullable/FIRST/FOLLOW/SELECT algorithms.
- Не изменять legacy matcher normalization, shadowing, cycle prefixes или generated artifacts.
- Audit выполняется read-only и не вызывает `replace_artifacts`.
- `find_runtime_dispatch_conflicts` проверяет actual normalized rows из `build_legacy_matcher_artifact`.
- Canonical и legacy результаты публикуются в разных JSON sections.
- Две текущие `LLK202` и два `VAL102` остаются documented baseline.
- Не считать исторические YAxUnit результаты свежим прогоном.
- Не создавать или изменять EDT launch configuration в этом плане.
- Все новые Python изменения вести через TDD.
- Коммитить каждую завершённую task отдельно и push после GREEN task gate.

## File Map

- Create: `tools/parsergen/benchmarks/audit_migration.py` — deterministic read-only structural/canonical/legacy/generated report from `parsergen.toml`.
- Create: `tools/parsergen/tests/test_migration_audit.py` — schema, classification, production baseline, no-write и CLI error tests.
- Create: `docs/superpowers/matrices/2026-08-07-query-model-consumer-impact.md` — evidence-backed downstream consumer map.
- Create: `docs/superpowers/matrices/2026-08-07-grammar-query-model-coverage.md` — current automated coverage, gaps и Phase 2.5 requirements.
- Create: `docs/superpowers/matrices/2026-08-07-grammar-query-model-baseline.md` — structural/canonical/legacy/generated baseline и runtime-benchmark gap.
- Modify: `docs/architecture/parser-generator.md` — explicit temporary legacy layer, removal conditions и audit command.
- Reference only: `docs/superpowers/specs/2026-08-07-grammar-query-model-optimization-design.md` — утверждённая architecture; не изменять.

---

### Task 1: Deterministic migration audit core

**Files:**
- Create: `tools/parsergen/benchmarks/audit_migration.py`
- Create: `tools/parsergen/tests/test_migration_audit.py`

**Interfaces:**
- Consumes: `load_config(path) -> ParsergenConfig`, `compile_from_config(config) -> Compilation`, `build_legacy_matcher_artifact`, `find_canonical_select_conflicts`, `find_runtime_dispatch_conflicts`, `generate_parser`, `render_artifacts`, `compare_artifacts`.
- Produces: `classify_semantic_actions(grammar: Grammar) -> dict[str, int]` and `build_migration_audit(config_path: Path, *, max_matcher_rows: int = 100_000) -> dict[str, object]`.

- [ ] **Step 1: Add a failing semantic-action classification test**

Create `tools/parsergen/tests/test_migration_audit.py` with imports through the benchmark file:

```python
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import unittest

from parsergen.grammar_parser import parse_grammar


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
AUDIT_PATH = PACKAGE_ROOT / "benchmarks/audit_migration.py"
SPEC = spec_from_file_location("audit_migration", AUDIT_PATH)
assert SPEC is not None and SPEC.loader is not None
audit_migration = module_from_spec(SPEC)
SPEC.loader.exec_module(audit_migration)


class MigrationAuditUnitTests(unittest.TestCase):
    def test_classifies_constructor_structural_collection_and_constant_actions(
        self,
    ) -> None:
        parsed = parse_grammar(
            "<S> ::= "
            "{ЭтотУзел = НовыйСписок; "
            "ЭтотУзел.Элементы.Добавить(ТекущийЭлемент); "
            "ЭтотУзел.Флаг = Истина; "
            "ЭтотУзел.Значение = ТекущийЭлемент} item",
        )
        assert parsed.grammar is not None

        self.assertEqual(
            audit_migration.classify_semantic_actions(parsed.grammar),
            {
                "action_blocks": 1,
                "statements": 4,
                "constructor_statements": 1,
                "collection_statements": 1,
                "constant_statements": 1,
                "structural_statements": 1,
                "other_assignment_statements": 0,
                "other_statements": 0,
            },
        )
```

- [ ] **Step 2: Run the test and verify RED**

```powershell
$env:PYTHONPATH=(Resolve-Path 'tools/parsergen/src').Path
python -m pytest tools/parsergen/tests/test_migration_audit.py -v
```

Expected: FAIL because `benchmarks/audit_migration.py` does not exist.

- [ ] **Step 3: Implement the classifier with mutually exclusive categories**

Create `tools/parsergen/benchmarks/audit_migration.py` with repository-local import setup and this core:

```python
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys


PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SRC = PACKAGE_ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from parsergen.model import Action, Grammar
from parsergen.semantic_actions import (
    CONSTRUCTOR,
    _normalize_newlines,
    _split_statements,
    _top_level_assignment,
)


CONSTANT = re.compile(
    r'^(?:Истина|Ложь|Неопределено|Null|-?\d+(?:\.\d+)?|"(?:[^"]|"")*")$',
    re.IGNORECASE,
)
STRUCTURAL_NAMES = (
    "ЭтотУзел",
    "ТекущийЭлемент",
    "Родитель",
    "ЛевыйЭлемент",
)


def classify_semantic_actions(grammar: Grammar) -> dict[str, int]:
    counts = {
        "action_blocks": 0,
        "statements": 0,
        "constructor_statements": 0,
        "collection_statements": 0,
        "constant_statements": 0,
        "structural_statements": 0,
        "other_assignment_statements": 0,
        "other_statements": 0,
    }
    for production in grammar.productions:
        for alternative in production.alternatives:
            for element in alternative.elements:
                if not isinstance(element, Action):
                    continue
                counts["action_blocks"] += 1
                statements = _split_statements(
                    _normalize_newlines(element.text)
                )
                counts["statements"] += len(statements)
                for statement in statements:
                    assignment = _top_level_assignment(statement)
                    if assignment is not None:
                        right = statement[assignment + 1 :].strip()
                        if CONSTRUCTOR.fullmatch(right):
                            counts["constructor_statements"] += 1
                        elif CONSTANT.fullmatch(right):
                            counts["constant_statements"] += 1
                        elif any(name in statement for name in STRUCTURAL_NAMES):
                            counts["structural_statements"] += 1
                        else:
                            counts["other_assignment_statements"] += 1
                    elif ".Добавить(" in statement:
                        counts["collection_statements"] += 1
                    else:
                        counts["other_statements"] += 1
    return counts
```

Category precedence is part of the report contract: constructor, constant,
structural assignment, other assignment, collection call, other statement.

- [ ] **Step 4: Run the focused unit test and verify GREEN**

```powershell
python -m pytest tools/parsergen/tests/test_migration_audit.py -v
```

Expected: PASS.

- [ ] **Step 5: Add a failing deterministic report-schema test**

Append a temporary repository-config test:

```python
REPOSITORY_ROOT = PACKAGE_ROOT.parents[1]


def test_build_report_has_separate_canonical_and_legacy_sections(self) -> None:
    report = audit_migration.build_migration_audit(
        REPOSITORY_ROOT / "parsergen.toml"
    )

    self.assertEqual(report["schema_version"], 1)
    self.assertEqual(
        set(report),
        {
            "schema_version",
            "config",
            "structural",
            "canonical",
            "legacy",
            "generated",
            "artifacts",
        },
    )
    self.assertEqual(report["config"]["entrypoints"], {
        "Разобрать": "ПакетЗапросов",
        "РазобратьВыражение": "Выражение",
    })
    self.assertEqual(len(report["canonical"]["conflicts"]), 2)
    self.assertEqual(report["legacy"]["runtime_conflicts"], [])
    self.assertEqual(report["artifacts"]["changed"], [])
```

- [ ] **Step 6: Run the schema test and verify RED**

```powershell
python -m pytest tools/parsergen/tests/test_migration_audit.py -k separate -v
```

Expected: FAIL because `build_migration_audit` is absent.

- [ ] **Step 7: Implement the read-only report builder**

Add imports and build the report without checking `report.has_errors`:

```python
from parsergen.analysis import (
    build_legacy_matcher_artifact,
    find_canonical_select_conflicts,
    find_runtime_dispatch_conflicts,
)
from parsergen.artifacts import compare_artifacts, render_artifacts
from parsergen.bsl_codegen import generate_parser
from parsergen.cli import compile_from_config
from parsergen.config import load_config
from parsergen.model import NonterminalCall


def _conflict_rows(conflicts) -> list[dict[str, object]]:
    return [
        {
            "production": item.production,
            "left_alternative": item.left_alternative,
            "right_alternative": item.right_alternative,
            "witness": list(item.witness),
        }
        for item in conflicts
    ]


def build_migration_audit(
    config_path: Path,
    *,
    max_matcher_rows: int = 100_000,
) -> dict[str, object]:
    config_path = Path(config_path).resolve()
    config = load_config(config_path)
    compilation = compile_from_config(config)
    if (
        compilation.grammar is None
        or compilation.resolved is None
        or compilation.analysis is None
    ):
        raise ValueError("production grammar did not produce a complete analysis")

    grammar = compilation.grammar
    resolved = compilation.resolved
    analysis = compilation.analysis
    legacy_artifact = build_legacy_matcher_artifact(
        analysis,
        max_rows=max_matcher_rows,
    )
    generated = generate_parser(
        grammar,
        resolved,
        analysis,
        config.entrypoints,
    )
    rendered = render_artifacts(generated)
    comparison = compare_artifacts(config.target, rendered)
    actions = classify_semantic_actions(grammar)
    actual_arguments = sum(
        len(element.arguments)
        for production in grammar.productions
        for alternative in production.alternatives
        for element in alternative.elements
        if isinstance(element, NonterminalCall)
    )
    compressed = analysis._compressed
    assert compressed is not None
    stats = compressed.stats
    return {
        "schema_version": 1,
        "config": {
            "grammar": str(config.grammar.relative_to(config_path.parent)),
            "target": str(config.target.relative_to(config_path.parent)),
            "lookahead": config.lookahead,
            "entrypoints": dict(config.entrypoints),
        },
        "structural": {
            "productions": len(grammar.productions),
            "alternatives": sum(
                len(item.alternatives) for item in grammar.productions
            ),
            "epsilon_alternatives": sum(
                not alternative.syntax_symbols
                for production in grammar.productions
                for alternative in production.alternatives
            ),
            "formal_parameters": sum(
                len(item.parameters) for item in grammar.productions
            ),
            "actual_arguments": actual_arguments,
            **actions,
        },
        "canonical": {
            "conflicts": _conflict_rows(
                find_canonical_select_conflicts(resolved, analysis)
            ),
            "diagnostics": [
                {
                    "code": item.code,
                    "severity": item.severity.value,
                    "message": item.message,
                }
                for item in compilation.report.diagnostics
            ],
            "stats": {
                "packed_first_rows": sum(
                    len(value) for value in compressed.first
                ),
                "packed_follow_rows": sum(
                    len(value) for value in compressed.follow
                ),
                "select_descriptors": stats["select_descriptors"],
                "conflict_work_items": stats["conflict_work_items"],
                "public_select_expansions": stats["public_select_expansions"],
                "select_cartesian_materializations": stats[
                    "select_cartesian_materializations"
                ],
            },
        },
        "legacy": {
            "matcher_rows": len(legacy_artifact.select_rows),
            "matcher_definitions": len(legacy_artifact.matcher_definitions),
            "runtime_conflicts": _conflict_rows(
                find_runtime_dispatch_conflicts(resolved, analysis)
            ),
        },
        "generated": {
            "bsl_functions": sum(
                line.strip().casefold().startswith("функция ")
                for line in generated.module_text.splitlines()
            ),
            "bsl_loc": len(generated.module_text.splitlines()),
            "constructor_names": len(generated.constructor_names),
            "select_rows": len(generated.select_table.rows),
            "identifier_rows": len(generated.identifier_table.rows),
        },
        "artifacts": {
            "changed": [
                str(path.relative_to(config_path.parent))
                for path in comparison.changed
            ],
        },
    }
```

If internal packed field names differ from this draft, use the already tested
public/statistical counters that yield the same metrics; do not materialize
public FIRST/FOLLOW/SELECT.

- [ ] **Step 8: Add CLI JSON output and structured errors**

Add:

```python
def _write_json(value: object) -> None:
    payload = (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode(
        "utf-8"
    )
    buffer = getattr(sys.stdout, "buffer", None)
    if buffer is None:
        sys.stdout.write(payload.decode("utf-8"))
    else:
        buffer.write(payload)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Read-only grammar/query-model migration audit",
    )
    parser.add_argument("--config", type=Path, default=Path("parsergen.toml"))
    parser.add_argument("--max-matcher-rows", type=int, default=100_000)
    arguments = parser.parse_args(argv)
    try:
        report = build_migration_audit(
            arguments.config,
            max_matcher_rows=arguments.max_matcher_rows,
        )
    except (OSError, ValueError) as error:
        _write_json({
            "schema_version": 1,
            "status": "error",
            "type": type(error).__name__,
            "message": str(error),
        })
        return 2
    _write_json(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

Add a subprocess test asserting a missing config returns code 2, valid UTF-8
JSON and no traceback.

- [ ] **Step 9: Run focused tests**

```powershell
python -m pytest tools/parsergen/tests/test_migration_audit.py -v
```

Expected: PASS.

- [ ] **Step 10: Commit and push Task 1**

```powershell
git add -- tools/parsergen/benchmarks/audit_migration.py tools/parsergen/tests/test_migration_audit.py
git commit -m "Добавить аудит миграции грамматики"
git push
```

---

### Task 2: Exact production baseline contract

**Files:**
- Modify: `tools/parsergen/tests/test_migration_audit.py`
- Create: `docs/superpowers/matrices/2026-08-07-grammar-query-model-baseline.md`

**Interfaces:**
- Consumes: `build_migration_audit` schema version 1 from Task 1.
- Produces: exact production structural/canonical/legacy/generated assertions and a durable human-readable baseline.

- [ ] **Step 1: Run the audit and capture the actual JSON**

```powershell
$env:PYTHONPATH=(Resolve-Path 'tools/parsergen/src').Path
python tools/parsergen/benchmarks/audit_migration.py --config parsergen.toml
```

Expected: exit 0; `canonical.conflicts` contains exactly two rows;
`legacy.runtime_conflicts` and `artifacts.changed` are empty.

- [ ] **Step 2: Add the exact production regression test**

Append:

```python
class MigrationAuditProductionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.report = audit_migration.build_migration_audit(
            REPOSITORY_ROOT / "parsergen.toml"
        )

    def test_structural_baseline_is_explicit(self) -> None:
        self.assertEqual(
            self.report["structural"],
            {
                "productions": 124,
                "alternatives": 281,
                "epsilon_alternatives": 63,
                "formal_parameters": 8,
                "actual_arguments": 26,
                "action_blocks": 398,
                "statements": 431,
                "constructor_statements": 102,
                "collection_statements": 37,
                "constant_statements": 32,
                "structural_statements": 245,
                "other_assignment_statements": 10,
                "other_statements": 5,
            },
        )

    def test_canonical_and_legacy_contracts_are_separate(self) -> None:
        self.assertEqual(
            self.report["canonical"]["conflicts"],
            [
                {
                    "production": "ЛогическийОператор",
                    "left_alternative": 2,
                    "right_alternative": 5,
                    "witness": ["ССЫЛКА", "АВТОУПОРЯДОЧИВАНИЕ"],
                },
                {
                    "production": "ОперандВ",
                    "left_alternative": 1,
                    "right_alternative": 2,
                    "witness": ["ВЫБРАТЬ", "*"],
                },
            ],
        )
        self.assertEqual(self.report["legacy"]["matcher_rows"], 11_273)
        self.assertEqual(self.report["legacy"]["runtime_conflicts"], [])
        self.assertEqual(self.report["artifacts"]["changed"], [])

    def test_generated_shape_baseline_is_explicit(self) -> None:
        self.assertEqual(self.report["generated"]["bsl_functions"], 135)
        self.assertEqual(self.report["generated"]["bsl_loc"], 3394)
        self.assertEqual(self.report["generated"]["constructor_names"], 79)
```

If Task 1's mutually exclusive classifier yields a different exact split,
inspect every difference and correct either the classifier or this expected
baseline. Do not weaken the test to `greater than zero` assertions.

- [ ] **Step 3: Run the production regression test**

```powershell
python -m pytest tools/parsergen/tests/test_migration_audit.py -v
```

Expected: PASS.

- [ ] **Step 4: Write the durable baseline matrix**

Create `docs/superpowers/matrices/2026-08-07-grammar-query-model-baseline.md`
with this checked-in baseline content, adding the exact audit command output as
an appendix only when it agrees with the assertions:

```markdown
# Baseline миграции grammar/query model

## Reproduction

`python tools/parsergen/benchmarks/audit_migration.py --config parsergen.toml`

## Structural

- productions: 124
- alternatives: 281
- epsilon alternatives: 63
- action blocks/statements: 398/431
- constructor/collection/constant/structural/other-assignment/other statements:
  102/37/32/245/10/5
- formal parameters/actual arguments: 8/26

## Canonical analysis

- packed FIRST rows: 10 758
- packed FOLLOW rows: 42 545
- direct SELECT facts: 10 438
- short complete SELECT prefixes: 320
- packed SELECT upper bound with FOLLOW projections: 32 050
- public SELECT expansions: 0
- SELECT Cartesian materializations: 0
- LLK202 `ЛогическийОператор` 2/5: `ССЫЛКА АВТОУПОРЯДОЧИВАНИЕ`
- LLK202 `ОперандВ` 1/2: `ВЫБРАТЬ *`

## Legacy compatibility

- normalized matcher rows: 11 273
- runtime conflicts: 0
- artifact comparison changes: 0

## Generated parser

- BSL functions: 135
- BSL LOC: 3394
- constructor names: 79
- SELECT ValueTable rows: 11 273
- identifier ValueTable rows: 227

## Runtime parser baseline gap

No runtime median/p95, call-count or recursion-depth harness exists yet.
Phase 2.5 must implement and run it before the first production grammar/model
change. Python analysis timings are not a substitute for BSL runtime timings.
```

If the audit disagrees with an exact number, investigate the calculation and
live repository state before changing the documented baseline.

- [ ] **Step 5: Verify the document contains no placeholders**

```powershell
rg -n "\[copy|\[record|TBD|TODO" docs/superpowers/matrices/2026-08-07-grammar-query-model-baseline.md
```

Expected: no output, exit 1 from `rg`.

- [ ] **Step 6: Commit and push Task 2**

```powershell
git add -- tools/parsergen/tests/test_migration_audit.py docs/superpowers/matrices/2026-08-07-grammar-query-model-baseline.md
git commit -m "Зафиксировать baseline миграции грамматики"
git push
```

---

### Task 3: Durable query-model consumer impact matrix

**Files:**
- Create: `docs/superpowers/matrices/2026-08-07-query-model-consumer-impact.md`

**Interfaces:**
- Consumes: live EDT project `QueryConsoleZUP`, Serena references, the approved design and current YAxUnit/Vanessa paths.
- Produces: one evidence-backed row per consumer family with model ingress, properties, observable output, automated coverage and required Phase 2.5 test.

- [ ] **Step 1: Re-read the five central API reference sets**

Use EDT-MCP/Serena read-only operations for:

```text
ЭлементыМоделиЗапроса
ОбработкаМоделиЗапроса
МодельЗапросаУтилиты
ОбходМоделиЯзыкаВыражений
МодельЗапросаТипы
```

Expected baseline: 43 BSL files and 751 direct usages. If live counts differ,
record the new counts and list the commit/diff responsible; do not copy stale
counts.

- [ ] **Step 2: Verify expression visitor completeness**

Compare export methods of:

```text
DataProcessors/Шаблон_ПосетительМоделиВыражений/ObjectModule.bsl
DataProcessors/СемантическийАнализВыраженийПосетитель/ObjectModule.bsl
DataProcessors/ПроверкаПрименимостиОтбораПосетитель/ObjectModule.bsl
DataProcessors/ОбработчикРазыменованийДляСКДПосетитель/ObjectModule.bsl
```

Expected: template has 59 callbacks and all three concrete visitors implement
all 59. Record additional lifecycle methods separately.

- [ ] **Step 3: Write the matrix with exact required columns**

Create the document with:

```markdown
| Component | Model types/properties | Model ingress | Observable output | Existing automated test | Coverage gap | Required Phase 2.5 test |
```

Include separate rows for:

```text
AST factories
Lexer
Expression parser
Full-query parser
Semantic analyzer
Expression dispatcher/template
Semantic visitor
Filter applicability visitor
SKD dereference visitor
Model builder
Query/expression text generation
Executable-view processing
Executor/code/SKD generation
Query console underlying logic
Query Constructor underlying logic
Universal report
Feature-generation helpers
15 Представление* manager consumers
```

Every row must cite concrete module paths and public entrypoints. Mark facts,
inferences and unresolved dynamic object calls distinctly.

- [ ] **Step 4: Add the model-change protocol and UI boundary**

Append this section with real links and current evidence:

```markdown
## Change protocol

producer/reference discovery → GREEN headless characterization → new semantic
contract → factory/parser/consumer migration in one slice → zero stale
references → old property removal

## UI boundary

Form modules are not unit-test targets. Their callable common/object-module
dependencies remain in headless scope. A workflow is manual/Vanessa-only only
after its entrypoint analysis proves that no stable non-form contract can be
invoked.
```

- [ ] **Step 5: Review evidence and scope**

```powershell
rg -n "предполож|возможно|вероятно|TBD|TODO" docs/superpowers/matrices/2026-08-07-query-model-consumer-impact.md
git diff --check
```

Expected: every remaining uncertainty is under an explicit `Гипотезы` or
`Пробелы` section; no whitespace errors.

- [ ] **Step 6: Commit and push Task 3**

```powershell
git add -- docs/superpowers/matrices/2026-08-07-query-model-consumer-impact.md
git commit -m "Зафиксировать потребителей модели запросов"
git push
```

---

### Task 4: Test coverage matrix and Phase 2.5 gate

**Files:**
- Create: `docs/superpowers/matrices/2026-08-07-grammar-query-model-coverage.md`

**Interfaces:**
- Consumes: Task 3 impact rows, 227 collected Python tests, live YAxUnit module structures, 42 QueryExamples and 126 application Vanessa scenarios.
- Produces: a coverage decision for every affected headless consumer and an exact Phase 2.5 test backlog.

- [ ] **Step 1: Reproduce Python test inventory**

```powershell
Set-Location tools/parsergen
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest --collect-only -q -p no:cacheprovider
Set-Location ../..
```

Expected: 227 tests collected.

- [ ] **Step 2: Re-read live YAxUnit module structures**

Use EDT-MCP `get_module_structure` for:

```text
КОНС_Обр_ЛексическийАнализатор_МО
КОНС_Обр_Парсер_МО
КОНС_Обр_ПарсерЗапросов_МО
КОНС_Обр_ПарсерБудущаяГрамматика_МО
КОНС_ОМ_ОбработкаМоделиЗапроса
```

Record current procedure counts and distinguish historical execution results
from present static registration.

- [ ] **Step 3: Inventory corpus and external UI suites**

Run read-only counts:

```powershell
(rg --files QueryExamples -g '*.q1c').Count
(rg --files features/ВыполнениеЗапросовВКонсоли -g '*.feature').Count
(rg --files features/ГенерацияКодаВКонсоли -g '*.feature').Count
(rg --files features/СозданиеЗапросовВКонструкторе -g '*.feature').Count
```

Expected: 42 in each set.

- [ ] **Step 4: Write the coverage matrix**

Use columns:

```markdown
| Consumer | Affected | Current automated evidence | Gap | Phase 2.5 test | Gate type |
```

For each Task 3 row assign exactly one gate type:

```text
existing-automated
new-headless-test
form-only-vanessa/manual
external-blocker
```

The new-headless backlog must explicitly include:

```text
semantic sources/aliases/joins/fields/nested/union
factory-dispatcher-template completeness
unknown expression node error in text generation
three concrete visitor behavior contracts
headless builder mutations
model → text → model semantic round-trip
executable-view filter transformation/delegation
executor/code-generation focused integration
universal-report non-form transformations
Query Constructor non-form dependencies
runtime parser benchmark harness
```

- [ ] **Step 5: Verify every impact row has a coverage decision**

Compare Task 3 and Task 4 component headings manually and add a final checklist
mapping every impact row to one coverage row. Do not collapse universal report,
executor and Query Constructor into a generic UI row.

- [ ] **Step 6: Commit and push Task 4**

```powershell
git add -- docs/superpowers/matrices/2026-08-07-grammar-query-model-coverage.md
git commit -m "Зафиксировать покрытие миграции грамматики"
git push
```

---

### Task 5: Public canonical/legacy boundary and Foundation report

**Files:**
- Modify: `docs/architecture/parser-generator.md`
- Modify: `docs/superpowers/matrices/2026-08-07-grammar-query-model-baseline.md`

**Interfaces:**
- Consumes: audit schema and matrices from Tasks 1–4.
- Produces: public documentation of temporary legacy ownership, exact removal conditions and Phase 0–2 completion evidence.

- [ ] **Step 1: Add the audit command to architecture documentation**

Under `## CLI`, add:

```powershell
python tools/parsergen/benchmarks/audit_migration.py --config parsergen.toml
```

Document that it is read-only, does not stop on the two known canonical
conflicts, compares three artifacts semantically and returns canonical and
legacy sections separately.

- [ ] **Step 2: Expand the legacy boundary section**

State explicitly:

```text
Canonical APIs:
  compute_analysis
  find_canonical_select_conflicts
  find_select_conflicts (canonical compatibility alias)

Legacy APIs:
  build_legacy_matcher_artifact
  find_runtime_dispatch_conflicts

Compatibility-only wrappers:
  build_select_matcher_artifact
  compatible_lookahead
```

Document the known `A → a B | a b d`, `B → ε | b c` counterexample and state
that collision-free legacy rows do not prove language preservation.

- [ ] **Step 3: Document removal conditions**

Legacy removal requires all of:

```text
production config uses canonical backend
zero legacy islands
zero production references to legacy APIs
canonical parser regression GREEN
differential semantic corpus complete
intentional generated artifact review complete
runtime benchmark complete
```

- [ ] **Step 4: Add Foundation completion evidence to baseline matrix**

Append:

```markdown
## Foundation Phase 0–2 status

- impact matrix:
  [query-model consumer impact](2026-08-07-query-model-consumer-impact.md)
- coverage matrix:
  [grammar/query-model coverage](2026-08-07-grammar-query-model-coverage.md)
- approved architecture:
  [grammar/query-model optimization design](../specs/2026-08-07-grammar-query-model-optimization-design.md)
- Python baseline: 226 passed, 1 skipped, 4011 subtests passed
- current YAxUnit status: static inventory only; fresh incremental run belongs
  to Phase 2.5
- production grammar/model/artifacts changed: no
```

- [ ] **Step 5: Verify documentation consistency**

```powershell
rg -n "legacy|canonical|LLK202|audit_migration" docs/architecture/parser-generator.md docs/superpowers/matrices/2026-08-07-grammar-query-model-baseline.md
git diff --check
```

Expected: canonical and legacy terms are never used as synonyms; both known
LLK202 remain documented.

- [ ] **Step 6: Commit and push Task 5**

```powershell
git add -- docs/architecture/parser-generator.md docs/superpowers/matrices/2026-08-07-grammar-query-model-baseline.md
git commit -m "Документировать foundation миграции парсера"
git push
```

---

### Task 6: Foundation verification and handoff to Phase 2.5

**Files:**
- Verify only: all files from Tasks 1–5.

**Interfaces:**
- Consumes: completed Foundation artifacts.
- Produces: verified clean branch ready for the separate Phase 2.5 test-hardening plan.

- [ ] **Step 1: Run focused migration-audit tests**

```powershell
$env:PYTHONPATH=(Resolve-Path 'tools/parsergen/src').Path
python -m pytest tools/parsergen/tests/test_migration_audit.py -v -p no:cacheprovider
```

Expected: PASS.

- [ ] **Step 2: Run the full parsergen suite**

```powershell
Set-Location tools/parsergen
$env:PYTHONDONTWRITEBYTECODE='1'
python -m pytest -q -p no:cacheprovider
Set-Location ../..
```

Expected: all tests pass; the existing Windows symlink test may remain skipped
only for WinError 1314.

- [ ] **Step 3: Run the production audit twice**

```powershell
$env:PYTHONPATH=(Resolve-Path 'tools/parsergen/src').Path
python tools/parsergen/benchmarks/audit_migration.py --config parsergen.toml > $env:TEMP\grammar-audit-1.json
python tools/parsergen/benchmarks/audit_migration.py --config parsergen.toml > $env:TEMP\grammar-audit-2.json
Compare-Object (Get-Content -Raw $env:TEMP\grammar-audit-1.json) (Get-Content -Raw $env:TEMP\grammar-audit-2.json)
```

Expected: no output; both reports are byte-identical and report clean artifact
comparison.

- [ ] **Step 4: Verify current expected validation status**

```powershell
$env:PYTHONPATH=(Resolve-Path 'tools/parsergen/src').Path
python -m parsergen validate --config parsergen.toml
```

Expected: exit 1 with exactly two `VAL102` warnings and two `LLK202` errors.
Do not change grammar to make this command green in Foundation.

- [ ] **Step 5: Verify no forbidden production changes**

```powershell
git diff origin/master...HEAD -- tools/parsergen/grammar/query-language.grammar QueryConsoleZUP/src/DataProcessors/Парсер QueryConsoleZUP/src/CommonModules/ЭлементыМоделиЗапроса
```

Expected: no diff attributable to this plan.

- [ ] **Step 6: Verify branch state and publish any final Foundation commit**

```powershell
git status --short --branch
git log --oneline --decorate -6
git push
```

Expected: clean worktree; branch tracks
`origin/feature/grammar-optimization`; all Foundation commits are published.

- [ ] **Step 7: Start the separate Phase 2.5 plan**

Invoke `superpowers:brainstorming` only if new design choices were discovered
during Foundation; otherwise invoke `superpowers:writing-plans` for a separate
`docs/superpowers/plans/2026-08-07-grammar-query-model-test-hardening.md`.
Do not implement EBNF, bindings, Parser IR or production model changes before
that plan's headless test gate is complete.
