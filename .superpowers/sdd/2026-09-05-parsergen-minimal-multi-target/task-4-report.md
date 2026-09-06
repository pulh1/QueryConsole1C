# Task 4 — общий `RecursionPlan`

Base: `f0b23a6935dff4e7605d801f2de1c84dfc0fb3dd`.

## Модель API и границы

`parsergen.recursion_plan.analyze_recursion_plan(source_grammar, parser_ir)`
строит immutable `RecursionPlan` над уже оптимизированным `ParserIr`.
Публичные facts: `IrSite`, `SequenceLiveness`, `ResultFlowFact`,
`RecursiveCallSite(kind: tail_loop | local_continuation)` и
`ContinuationLayout`/`ContinuationSlot`. Site хранит только production,
alternative и trail/indices; plan не хранит и не копирует `Operation`,
`BranchIr` или второй execution IR. Этот инвариант отдельно проверен
рекурсивным test-ом.

Generic часть в `recursion_plan.py` является единственным местом для
eligibility, result-flow, liveness и continuation layout. Доказательство
progress консервативно: fixed-point по `SourceGrammar` помечает лишь
нетерминалы/значения, которые потребляют во всех alternatives; соответствующий
prefix final IR trail обязан содержать source-linked `ParseSymbol` или
`ConsumeKnownSymbol` с proven tokens. Только syntactic position не достаточна;
если доказательство отсутствует, site не выдаётся.

`DirectRenderAnalysis` хранит `recursion_plan` плюс только Python-specific
facts shared-decision DAG. Python renderer делает lookup exact site и kind,
без второй таблицы `recursive_calls`/eligibility. Canonical BSL получает тот же
plan API, выбирает lowering только по plan site/kind и структурно прокладывает
текущий `IrSite` через sequence, region, dispatch и optional branch. Никакого
поиска/замещения строк уже отрендеренного BSL нет.

BSL frame интерпретирует layout slots `span_start`, `operation_result`,
`builder_field`, `wrap_seed`, `collection_accumulator` и `suffix_indices`;
frame имеет local LIFO stack и tag для нескольких exact nested sites.
`fold_accumulator` не имеет consumer frame по корректной причине: common
planner не выпускает site внутри `LeftFold` (negative planner test).

## Exact BSL tail excerpt and syntax gate

The structural tail plan site renders this exact branch shape (the assignment
is deliberately unreachable after `Продолжить`, but keeps the enclosing
transparent alternative syntactically assembled):

```bsl
Если ТокенРешения0 = "ITEM" Тогда
	Терминал("ITEM");
	Продолжить;
	РезультатПродукции = Неопределено;
	Прервать;
```

`test_tail_loop_plan_removes_canonical_bsl_self_call` in
`test_canonical_bsl_codegen.py` is the focused generation gate for this
branch: it asserts the loop/end-loop and absence of `НеТерминалS();`.
There is no repository BSL syntax parser/compiler harness and no installed
`oscript`, `1cv8`, or `1cv8c`; therefore no local gate proves execution-engine
syntax acceptance. No ad-hoc BSL validator was introduced.

## RED → GREEN evidence

1. Общий API: первый import test упал `ModuleNotFoundError:
   parsergen.recursion_plan`; после extraction combined tail/continuation/
   discarded-result fixture стал GREEN.
2. Progress proof: mutation заменяла consuming `ITEM` IR operation на
   `ReturnConstant`; RED оставлял `tail_loop` в plan. После source/IR proof
   `plan.sites == ()`.
3. Python consumer: migration test сначала дал `AttributeError` на удалённую
   private `recursive_calls`; после lookup `analysis.recursion_plan` весь
   Python direct file GREEN (78 tests).
4. BSL tail/local: RED соответственно не содержал iteration loop и не имел
   continuation stack; GREEN удаляет BSL self-call, использует
   `Пока Истина Цикл`/`КонецЦикла` и LIFO frame unwind.
5. Nested BSL: exact optional site RED не содержал loop и оставлял
   `НеТерминалS();`; GREEN структурно dispatches at exact `IrSite.trail`.
   Multi-site nested RED был
   `ValueError: canonical renderer cannot consume local continuation plan sites`;
   GREEN использует tagged local frames and LIFO kind dispatch.
6. Additional BSL assertions cover isolated builder frame, constant suffix
   ordering, wrap seed, collection accumulator and operation-result slot.
   `LeftFold` negative plan proof prevents a fold frame by construction.

Focused command:

```powershell
python -m pytest -q tools/parsergen/tests/test_recursion_plan.py tools/parsergen/tests/test_direct_render_analysis.py tools/parsergen/tests/test_python_direct_rendering.py tools/parsergen/tests/test_canonical_bsl_codegen.py tools/parsergen/tests/test_direct_python_bsl_artifact_fence.py
# 122 passed in 1.64s
```

Dedicated byte fence:

```powershell
python -m pytest -q tools/parsergen/tests/test_direct_python_bsl_artifact_fence.py
# 1 passed in 1.24s
```

Full suite:

```powershell
python -m pytest -q tools/parsergen/tests
# 661 passed, 1 skipped in 40.88s
```

The skip is the existing Windows symlink-privilege case in
`test_artifacts.py`, not a parsergen failure.

Static checks:

```powershell
python -m compileall -q tools/parsergen/src
# exit 0

git diff --check
# exit 0 (only existing LF→CRLF checkout warnings)
```

Search self-review confirms `recursive_calls` and `safe_tail_loop` are gone;
classification helpers (`_direct_recursive_calls`, progress proof and layout
builders) occur only in `recursion_plan.py`. Python and BSL only consume exact
plan sites; BSL has no recursion analyzer and no rendered-text substitution.

## Production artifact fence

Rebuilding final optimized QueryConsole IR reported `plan_sites=0`.

| Artifact | SHA-256 |
| --- | --- |
| object module | `358a6123f91cd9068a08c76b3849ffad69f10eb0c7b2ed90b650f87304b960e8` |
| select template | `acb80f86f739d5a4a54fe7d6f2c85cdc57a2d664d779a1f1e51a0aaf54a059c1` |
| identifier template | `13472cb0e1482b5c590a306fe6fc119d026546069e717d8eadd010b6a8661ef6` |

## Concerns

The intentional non-emission is `LeftFold`: its accumulator semantics are not
classified as direct recursion, and this is covered by the negative shared-plan
test. QueryConsole has zero plan sites, so its byte fence cannot compile or run
the new recursive BSL path. The repository contains no local BSL compiler or
syntax parser; engine-level syntax acceptance of the excerpt above requires a
future live 1C/OneScript-capable environment.

## Fix round 1/5 — structural BSL consumption of every plan site

Reviewed commit: `33d3493`; this round is a separate fix commit. The findings
below correct the earlier report's overstatement that BSL consumed every common
plan site without applying target eligibility checks.

### Phase 1: root cause, hypothesis and WIP disposition

Read the task brief, this report, the complete `review-f0b23a6..33d3493.diff`,
repository `AGENTS.md`, TDD/good-tests and systematic-debugging instructions
before production edits. The initial worktree contained only the interrupted
Terra WIP in `canonical_bsl_codegen.py` and `test_canonical_bsl_codegen.py`.
Its canonical test file was actually run: **27 passed in 0.18s**.

The reviewed renderer chose separate simple-tail, simple-continuation and
nested-continuation production renderers. `_simple_tail_loop_calls` rejected
nested trails and `DiscardSymbol`, `_simple_local_continuation` required one
site, and `_nested_local_continuation` required `BindScalar`. Choosing the
continuation path first also left simultaneous tail sites untouched. These
were target capability filters over already valid common-plan sites.

The second defect came from different numbering domains: push enumerated
sites within each alternative, while unwind enumerated all production sites.
Thus a continuation in alternative B pushed tag 0 and restored A's fields.

Single architecture hypothesis stated before production edits: **one registry
of all production sites, consumed in one structural `IrSite.trail` rendering
traversal, plus one production-wide tag map shared by push and unwind, removes
both failure modes without changing common eligibility.**

The WIP's fixtures and unified-loop direction were useful, but its new entry
point bypassed rather than removed the old renderers and filters. It also
resolved operations in a second `_operation_at_site` traversal. Replaced that
architecture with the single registry/traversal described below. No committed
change was reset or reverted; no unrelated file, grammar, runtime, version or
production artifact was changed.

Two initial WIP fixtures did not isolate their intended original bugs:
multiple top-level **bound** continuations were already renderable at
`33d3493`, and a top-level frame-tag test did not independently demonstrate
nested cross-alternative collisions. Extended the former to include both
unbound and bound calls, and changed the latter to two nested alternatives
with distinct `Value/Rest` versus `Other/Tail` fields. Assertions now associate
each tag with its own saved fields and unwind binding.

### RED evidence

The original renderer was loaded from Git into a separate Python process;
the working file was never overwritten. The final regression set was run
against that original module:

```powershell
@'
import subprocess, sys
sys.path.insert(0, 'tools/parsergen/src')
import parsergen.canonical_bsl_codegen as module
source = subprocess.check_output(['git', 'show', '33d3493:tools/parsergen/src/parsergen/canonical_bsl_codegen.py']).decode('utf-8')
exec(compile(source, module.__file__, 'exec'), module.__dict__)
import pytest
raise SystemExit(pytest.main(['-q', 'tools/parsergen/tests/test_canonical_bsl_codegen.py', '-k', 'consumes_nested or resolved_region_site or mixed_tail or multiple_direct or global_plan_tags', '--tb=no']))
'@ | python -
# 5 failed, 23 deselected in 0.06s; exit 1
```

Separately running the same fixtures with `unittest` subtests against the
original module observed these exact failure types:

| Fixture | Original result |
| --- | --- |
| `<S> ::= (ITEM <S>) \| STOP` | `AssertionError: 'Пока Истина Цикл'` absent; self-call retained |
| `<S> ::= ITEM -= <S> \| STOP` | `AssertionError: 'Пока Истина Цикл'` absent; self-call retained |
| `<S> ::= ITEM -= (<S>) \| STOP` | `AssertionError: 'Пока Истина Цикл'` absent |
| `<S> ::= ITEM <S> \| @Node Value = MARK <S> \| @End STOP` | `AssertionError: 'НеТерминалS();'` unexpectedly present |
| Same mixed grammar with `Rest = <S>` | The tail self-call was still present |
| `<S> ::= @A Value = A <S> \| @B Value = B <S> \| @End STOP` | `ValueError: canonical renderer cannot consume local continuation plan sites` |
| Nested A/B alternatives with distinct fields | Second push contained `Вид = 0` instead of `Вид = 1` |

Added a separate resolved-region regression by replacing a one-branch
`Dispatch` with its equivalent `ResolvedRegion`; common plan still names
`(("operation", 0), ("region", 0), ("operation", 1))`. Its original-renderer
RED is included in the five failures above. The tail matrix also covers
two nested dispatch sites and a constructorless optional tail site.

The enhanced original-finding fixtures were already GREEN on the inherited
WIP, before this round's production edits. They are not claimed as WIP RED.
A separate inherited-WIP defect was observed after strengthening the suffix
assertion: it emitted the constant suffix both after `Продолжить` and during
unwind. The focused command was:

```powershell
python -m pytest -q tools/parsergen/tests/test_canonical_bsl_codegen.py -k unwinds_constant_suffix --tb=short
# AssertionError: 2 != 1
# 1 failed, 26 deselected in 0.15s
```

One exploratory mixed dispatch fixture had inconsistent branch semantic
results (`ParseSymbol` versus discarded result); it was corrected to two
propagating branches before the final regression run. Its validation error
was not treated as a recursion fix or hidden by a planner restriction.

### Final implementation

`_RecursionRendering` is production-local emission state. It indexes **all**
`RecursiveCallSite` objects for that production; only the planner's `kind`
selects loop transfer versus continuation push. It allocates stable tags once
for the production, and records `(AlternativeIr, Operation)` references when
the actual structural rendering traversal encounters a continuation. These
are renderer references into the original IR, not a new execution IR or a
second analysis. The common immutable `RecursionPlan` and the Python consumer
are unchanged.

The normal `_render_production` path handles zero, direct, nested and mixed
sites. `_render_operations` carries the exact operation/region/branch/exit
trail and resolves direct or `value` sites from the registry. There is no
second operation-at-site walker. Every issued site must be consumed; the
post-render invariant rejects an internally missed site instead of quietly
falling back to recursive output. All former simple/nested selectors,
per-alternative numbering and separate recursion rendering paths were removed.

Each push creates a fresh structure, records the node and layout slots, then
transfers to the production loop. The common `suffix_indices` are rendered
only on unwind. `span_start` maps to the already-created BSL node, whose
constructor received the original start token; `builder_field` and
`collection_accumulator` map to the frame's own node/collection receiver;
`operation_result` restores the prior result after applying the recursive
operand; `wrap_seed` preserves the pre-descent seed and is applied to the
returned wrapper. LIFO uses `Получить(Количество() - 1)` and deletes that same
last element before restoring it. `LeftFold` remains the common-plan negative;
the unused BSL `fold_accumulator` pseudo-support was removed.

### GREEN and artifact gates

All commands below were run in the assigned worktree:

```powershell
python -m pytest -q tools/parsergen/tests/test_canonical_bsl_codegen.py -k 'consumes_nested or resolved_region_site or mixed_tail or multiple_direct or global_plan_tags'
# 5 passed, 23 deselected in 0.12s

python -m pytest -q tools/parsergen/tests/test_canonical_bsl_codegen.py
# 28 passed in 0.16s

python -m pytest -q tools/parsergen/tests/test_recursion_plan.py tools/parsergen/tests/test_direct_render_analysis.py tools/parsergen/tests/test_python_direct_rendering.py tools/parsergen/tests/test_canonical_bsl_codegen.py tools/parsergen/tests/test_direct_python_bsl_artifact_fence.py
# 127 passed in 1.64s

python -m pytest -q tools/parsergen/tests/test_direct_python_bsl_artifact_fence.py
# 1 passed in 1.22s

python -m pytest -q tools/parsergen/tests
# 666 passed, 1 skipped in 40.90s
```

The sole skip is `test_artifacts.py:146`, Windows symlink creation denied by
`WinError 1314`. Python direct behavior, including existing 1,500/5,000 item
tests, result flow and spans, remained GREEN.

Fresh production hashes and site count were independently printed:

```powershell
@'
import sys
from pathlib import Path
from hashlib import sha256
sys.path.insert(0, 'tools/parsergen/src')
from parsergen.cli import compile_from_config, generate_from_compilation
from parsergen.config import load_config
from parsergen.parser_ir import build_parser_ir
from parsergen.recursion_plan import analyze_recursion_plan
from parsergen.artifacts import render_artifacts
config = load_config(Path('parsergen.toml'))
compilation = compile_from_config(config)
ir = build_parser_ir(compilation.source_grammar, compilation.lowering, compilation.resolved, compilation.analysis, entrypoint_productions=config.entrypoints.values())
print('plan_sites=' + str(len(analyze_recursion_plan(compilation.source_grammar, ir).sites)))
artifacts = render_artifacts(generate_from_compilation(config, compilation))
for name in ('object_module', 'select_template', 'identifier_template'):
    print(name + '=' + sha256(getattr(artifacts, name)).hexdigest())
'@ | python -
# plan_sites=0
# object_module=358a6123f91cd9068a08c76b3849ffad69f10eb0c7b2ed90b650f87304b960e8
# select_template=acb80f86f739d5a4a54fe7d6f2c85cdc57a2d664d779a1f1e51a0aaf54a059c1
# identifier_template=13472cb0e1482b5c590a306fe6fc119d026546069e717d8eadd010b6a8661ef6
```

Static checks:

```powershell
python -m compileall -q tools/parsergen/src
# exit 0
git diff --check
# exit 0; only checkout LF-to-CRLF warnings
rg -n '_simple_tail_loop_calls|_simple_local_continuation|_nested_local_continuation|_operation_at_site|_active_nested|_active_tail|_active_recursion' tools/parsergen/src/parsergen/canonical_bsl_codegen.py
# no matches
rg -n 'def _direct_recursive_calls|def _has_proven_progress|def _continuation_layout|def _nested_continuation_layout|def _has_live_enclosing_result|def _unchanged_result_flow' tools/parsergen/src/parsergen
# only recursion_plan.py:175,284,397,415,624,645
rg -n 'replace\(|endswith\(|НеТерминал.* in |call_text' tools/parsergen/src/parsergen/canonical_bsl_codegen.py
# sole match: existing module-template marker substitution in _substitute_template
```

That unchanged template substitution inserts complete generated sections at
fixed template markers. No recursive call text matching, rendered BSL
replacement, `endswith` or textual surgery exists in recursion lowering.

### Exact generated BSL excerpts and remaining live gate

The following excerpts were printed from the current generator; line endings
are normalized for this Markdown report. Mixed tail/continuation grammar
`<S> ::= ITEM <S> | @Node Value = MARK <S> | @End STOP`:

```bsl
		Если ТокенРешения0 = "ITEM" Тогда
			Терминал("ITEM");
			Продолжить;
			РезультатПродукции = Неопределено;
			Прервать;
		ИначеЕсли ТокенРешения0 = "MARK" Тогда
			ЭтотУзел = ЭлементыМоделиЗапроса.Node(ТекущийТокен);
			Значение1 = Терминал("MARK");
			ЭтотУзел.Value = Значение1;
			Продолжение = Новый Структура;
			Продолжение.Вставить("Вид", 0);
			Продолжение.Вставить("Узел", ЭтотУзел);
			Продолжение.Вставить("Слот0", ЭтотУзел);
			Продолжение.Вставить("Слот1", ЭтотУзел.Value);
			СтекПродолжений.Добавить(Продолжение);
			Продолжить;
```

For `<S> ::= @A A (Value = ITEM Rest = <S>)? | @B B (Other = ITEM Tail = <S>)? | @End STOP`,
the B alternative pushes its own tag and field:

```bsl
				Продолжение = Новый Структура;
				Продолжение.Вставить("Вид", 1);
				Продолжение.Вставить("Узел", ЭтотУзел);
				Продолжение.Вставить("Слот0", ЭтотУзел);
				Продолжение.Вставить("Слот1", ЭтотУзел.Other);
				СтекПродолжений.Добавить(Продолжение);
				Продолжить;
```

Its exact production-wide unwind:

```bsl
	Пока СтекПродолжений.Количество() > 0 Цикл
		Продолжение = СтекПродолжений.Получить(СтекПродолжений.Количество() - 1);
		СтекПродолжений.Удалить(СтекПродолжений.Количество() - 1);
		Если Продолжение.Вид = 0 Тогда
			ЭтотУзел = Продолжение.Узел;
			ЭтотУзел = Продолжение.Слот0;
			ЭтотУзел.Value = Продолжение.Слот1;
			ЭтотУзел.Rest = РезультатПродукции;
			РезультатПродукции = ЭтотУзел;
		ИначеЕсли Продолжение.Вид = 1 Тогда
			ЭтотУзел = Продолжение.Узел;
			ЭтотУзел = Продолжение.Слот0;
			ЭтотУзел.Other = Продолжение.Слот1;
			ЭтотУзел.Tail = РезультатПродукции;
			РезультатПродукции = ЭтотУзел;
		Иначе
			ВызватьИсключение "Неизвестное продолжение";
		КонецЕсли;
	КонецЦикла;
```

`Get-Command oscript,1cv8,1cv8c -ErrorAction SilentlyContinue` returned no
commands. No live BSL compilation/execution was performed and no improvised
syntax validator was added. The emission tests and unchanged QueryConsole
bytes do not establish engine acceptance of this recursive path. In
particular, the enclosing result assignments/breaks following `Продолжить`
remain unreachable emitted statements, as shown explicitly above. The
remaining gate is compilation and execution in a live 1C/OneScript-capable
environment, including mixed-depth stack frames and cross-alternative fields.
