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
