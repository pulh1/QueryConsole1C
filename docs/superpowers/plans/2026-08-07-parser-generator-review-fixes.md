# Parser Generator Review Fixes Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Исправить шесть подтверждённых замечаний PR №70 без изменения канонической грамматики и production-парсера.

**Architecture:** CLI сохраняет существующие пределы материализации, но преобразует их превышение в контролируемый код возврата. BSL-кодогенератор различает неявную пустую альтернативу и actionful epsilon-альтернативу по наличию элементов. Остальные изменения устраняют неразрешённую аннотацию и неточности текста.

**Tech Stack:** Python 3.11+, unittest/pytest, LL(k) parser generator, BSL code generation.

## Global Constraints

- Не изменять `tools/parsergen/grammar/query-language.grammar`.
- Не изменять `QueryConsoleZUP/src/DataProcessors/Парсер`.
- Сначала наблюдать падение каждого нового функционального теста, затем вносить минимальное исправление.
- Не добавлять новый CLI-параметр лимита материализации: текущему PR достаточно контролируемой ошибки.
- Не изменять LLK201: воспроизведение подтвердило корректную нумерацию для разобранной грамматики.

---

### Task 1: Валидация нулевого lookahead без config

**Files:**
- Modify: `tools/parsergen/tests/test_cli.py`
- Modify: `tools/parsergen/src/parsergen/cli.py:187-194`

**Interfaces:**
- Consumes: CLI `parsergen validate --grammar PATH --entry NAME=PRODUCTION --lookahead VALUE`.
- Produces: код `1` и сообщение `--lookahead must be an integer at least 1` для явного нуля.

- [ ] **Step 1: Write the failing test**

```python
def test_zero_lookahead_without_config_is_rejected(self) -> None:
    grammar = self.root / "grammar.txt"
    grammar.write_text("<S> ::= a", encoding="utf-8")

    completed = self.run_cli(
        "validate",
        "--grammar",
        str(grammar),
        "--entry",
        "Разобрать=S",
        "--lookahead",
        "0",
    )

    self.assertEqual(completed.returncode, 1)
    self.assertEqual(completed.stdout, "")
    self.assertIn("--lookahead must be an integer at least 1", completed.stderr)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tools/parsergen/tests/test_cli.py::CliTests::test_zero_lookahead_without_config_is_rejected -v`

Expected: FAIL because the current expression `arguments.lookahead or 2` replaces `0` with `2` and returns code `0`.

- [ ] **Step 3: Write minimal implementation**

Replace the default expression with an explicit `None` check:

```python
lookahead=_valid_lookahead(
    arguments.lookahead if arguments.lookahead is not None else 2
),
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tools/parsergen/tests/test_cli.py::CliTests::test_zero_lookahead_without_config_is_rejected -v`

Expected: PASS.

### Task 2: Контролируемая ошибка materialization в analyze

**Files:**
- Modify: `tools/parsergen/tests/test_cli.py`
- Modify: `tools/parsergen/src/parsergen/cli.py:10-15,126-132`

**Interfaces:**
- Consumes: существующий `LookaheadMaterializationError` с полями phase/key/estimated_rows/limit_rows.
- Produces: CLI-код `2`, сообщение ошибки в stderr и отсутствие traceback.

- [ ] **Step 1: Write the failing test**

```python
def test_analyze_reports_materialization_limit_without_traceback(self) -> None:
    grammar = self.root / "grammar.txt"
    tokens = " | ".join(f"T{index:03d}" for index in range(101))
    grammar.write_text(
        f"#ID_X ::= {tokens}\n<S> ::= #ID_X #ID_X",
        encoding="utf-8",
    )

    completed = self.run_cli(
        "analyze",
        "--grammar",
        str(grammar),
        "--entry",
        "Разобрать=S",
        "--lookahead",
        "2",
        "--format",
        "json",
    )

    self.assertEqual(completed.returncode, 2)
    self.assertEqual(completed.stdout, "")
    self.assertIn("may expand to 10201 rows; limit is 10000", completed.stderr)
    self.assertNotIn("Traceback", completed.stderr)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tools/parsergen/tests/test_cli.py::CliTests::test_analyze_reports_materialization_limit_without_traceback -v`

Expected: FAIL because the uncaught `LookaheadMaterializationError` produces a traceback and process code `1`.

- [ ] **Step 3: Write minimal implementation**

Import `LookaheadMaterializationError` and handle it with the same operational-failure contract as filesystem errors:

```python
except (OSError, LookaheadMaterializationError) as error:
    print(str(error), file=sys.stderr)
    return 2
```

- [ ] **Step 4: Run both CLI fixes**

Run: `python -m pytest tools/parsergen/tests/test_cli.py -v`

Expected: all CLI tests PASS.

### Task 3: Fallback для actionful epsilon-альтернативы

**Files:**
- Modify: `tools/parsergen/tests/test_bsl_codegen.py`
- Modify: `tools/parsergen/src/parsergen/bsl_codegen.py:424-460`

**Interfaces:**
- Consumes: `Alternative.elements`, где `ПУСТО` без действий даёт пустой tuple, а actionful epsilon содержит `Action`.
- Produces: actionful epsilon участвует в dispatch и не отключает fallback-исключение; полностью пустая альтернатива сохраняет прежний неявный fallback.

- [ ] **Step 1: Write the failing test**

```python
def test_actionful_epsilon_rejects_tokens_outside_select(self) -> None:
    entries = {"Разобрать": "S"}
    grammar, resolved, analysis = compiled(
        "<S> ::= a | {ЭтотУзел = НовыйEmpty} ПУСТО",
        1,
        entries,
    )

    generated = generate_parser(grammar, resolved, analysis, entries)
    function = generated.module_text.split(
        "Функция НеТерминалS", 1
    )[1].split("КонецФункции", 1)[0]

    self.assertIn("ИначеЕсли НомерВариантаПродукции = 2 Тогда", function)
    self.assertIn("ВызватьИсключениеНеУдалосьВыпполнитьРазбор", function)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tools/parsergen/tests/test_bsl_codegen.py::BslCodegenTests::test_actionful_epsilon_rejects_tokens_outside_select -v`

Expected: FAIL because `has_epsilon` currently uses `syntax_symbols` and suppresses the fallback exception.

- [ ] **Step 3: Write minimal implementation**

Use the same element criterion as dispatch selection:

```python
has_implicit_epsilon = any(
    not alternative.elements
    for alternative in production.alternatives
)
```

Replace both reads of `has_epsilon` with `has_implicit_epsilon`.

- [ ] **Step 4: Run code generation tests**

Run: `python -m pytest tools/parsergen/tests/test_bsl_codegen.py -v`

Expected: all BSL codegen tests PASS.

### Task 4: Разрешимость аннотаций resolver

**Files:**
- Modify: `tools/parsergen/tests/test_resolver.py`
- Modify: `tools/parsergen/src/parsergen/resolver.py:211-232`

**Interfaces:**
- Consumes: Python `typing.get_type_hints`.
- Produces: все аннотации модуля resolver разрешаются без отсутствующего `RelatedLocation`.

- [ ] **Step 1: Write the failing test**

```python
def test_private_diagnostic_annotations_are_resolvable(self) -> None:
    from typing import get_type_hints
    from parsergen import resolver

    hints = get_type_hints(resolver._diagnostic)

    self.assertIs(hints["return"], resolver.Diagnostic)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tools/parsergen/tests/test_resolver.py::ResolverTests::test_private_diagnostic_annotations_are_resolvable -v`

Expected: FAIL with `NameError: name 'RelatedLocation' is not defined`.

- [ ] **Step 3: Write minimal implementation**

Remove the unused keyword-only `related` parameter and construct the diagnostic without a fifth positional argument:

```python
def _diagnostic(code: str, span: SourceSpan, symbol: str) -> Diagnostic:
    ...
    return Diagnostic(code, Severity.ERROR, messages[code], span)
```

- [ ] **Step 4: Run resolver tests**

Run: `python -m pytest tools/parsergen/tests/test_resolver.py -v`

Expected: all resolver tests PASS.

### Task 5: Точечные текстовые исправления

**Files:**
- Modify: `docs/architecture/parser-generator.md:37`
- Modify: `tools/parsergen/tests/grammar_cases.py:1`

**Interfaces:**
- Consumes: существующая команда обычной wheel-установки.
- Produces: документация называет её установкой пакета; docstring не содержит повтор `parser parser`.

- [ ] **Step 1: Apply the text corrections**

```text
Из корня репозитория после установки пакета:
```

```python
"""Small grammar inputs shared by parser tests."""
```

- [ ] **Step 2: Check exact textual result**

Run: `rg -n "editable-пакета|parser parser" docs/architecture/parser-generator.md tools/parsergen/tests/grammar_cases.py`

Expected: no matches.

### Task 6: Полная проверка и публикация

**Files:**
- Verify: `tools/parsergen/**`
- Verify: `parsergen.toml`
- Verify unchanged: `tools/parsergen/grammar/query-language.grammar`
- Verify unchanged: `QueryConsoleZUP/src/DataProcessors/Парсер/**`

**Interfaces:**
- Consumes: все изменения Tasks 1-5.
- Produces: проверенный follow-up commit в PR №70.

- [ ] **Step 1: Run the full Python suite**

Run: `python -m pytest tools/parsergen/tests`

Expected: all tests PASS; допустим только известный Windows symlink skip.

- [ ] **Step 2: Run repository validation and drift gate**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'tools/parsergen/src').Path
python -m parsergen validate --config parsergen.toml
python -m parsergen generate --config parsergen.toml --check
```

Expected: validation exits `0` with the two existing VAL102 warnings; drift gate prints `artifacts are current`.

- [ ] **Step 3: Verify scope and whitespace**

Run:

```powershell
git diff --check HEAD~1..HEAD
git diff --name-only b2171a2..HEAD
git diff --exit-code b2171a2 -- tools/parsergen/grammar/query-language.grammar QueryConsoleZUP/src/DataProcessors/Парсер
```

Expected: no new whitespace errors; grammar and production parser have no diff.

- [ ] **Step 4: Commit and push the implementation**

```powershell
git add -- docs/architecture/parser-generator.md tools/parsergen/src/parsergen/cli.py tools/parsergen/src/parsergen/bsl_codegen.py tools/parsergen/src/parsergen/resolver.py tools/parsergen/tests/test_cli.py tools/parsergen/tests/test_bsl_codegen.py tools/parsergen/tests/test_resolver.py tools/parsergen/tests/grammar_cases.py docs/superpowers/plans/2026-08-07-parser-generator-review-fixes.md
git commit -m "Исправить замечания ревью генератора парсера"
git push
```
