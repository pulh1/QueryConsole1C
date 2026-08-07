# Parser Generator FOLLOW Optimization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Устранить повторное применение FOLLOW-трансформаций к delta с одинаковой значимой проекцией и ускорить production-анализ при `k = 3` без изменения результата.

**Architecture:** Исходящие FOLLOW-трансформации родительской продукции группируются по числу символов delta, влияющих на результат конкатенации. Каждая группа обрабатывает одну упакованную проекцию delta только один раз; существующие множества FOLLOW и delta-worklist продолжают отвечать за fixed-point и дедупликацию итоговых фактов.

**Tech Stack:** Python 3.11+, dataclasses, packed LL(k) analysis, unittest/pytest, PowerShell, repository benchmark CLI.

## Global Constraints

- Не изменять `tools/parsergen/grammar/query-language.grammar`.
- Не изменять `QueryConsoleZUP/src/DataProcessors/Парсер`.
- Не изменять публичные функции и структуры результата анализа.
- Сохранить точные значения `nullable`, `FIRST`, `FOLLOW`, `SELECT`, конфликтов и диагностик.
- Сначала наблюдать падение нового функционального теста, затем вносить минимальное изменение алгоритма.
- При `k = 3` сократить `follow_transform_applications` не менее чем в три раза: с 4 792 992 до значения не выше 1 597 664.
- Локальная медиана FOLLOW при `k = 3` должна быть не выше 2 000 мс.
- Локальная медиана FOLLOW при `k = 2` не должна превышать исходные 182.459 мс более чем на 10 процентов, то есть 200.705 мс.
- Wall-clock не использовать как жёсткое CI-условие; автоматический performance-gate строить по детерминированным счётчикам операций.
- Поддержку левой рекурсии, изменение грамматики и семантический анализ не включать в эту ветку.
- Для реализации кода использовать `gpt-5.6-terra` с низким reasoning; для аналитики и независимого review использовать `gpt-5.6-sol`.

## File Map

- `tools/parsergen/src/parsergen/analysis.py` — проекция packed-delta, группы трансформаций и fixed-point FOLLOW.
- `tools/parsergen/tests/test_follow_select.py` — функциональная регрессия и oracle-проверки эквивалентности анализа.
- `tools/parsergen/benchmarks/benchmark_analysis.py` — публикация детерминированных счётчиков оптимизации.
- `tools/parsergen/tests/test_benchmark_analysis.py` — контракт benchmark JSON и production work-budget.
- `docs/superpowers/specs/2026-08-07-parser-generator-follow-optimization-design.md` — утверждённые границы и критерии результата; не изменяется при реализации.

---

### Task 1: Проекционная дедупликация FOLLOW

**Files:**
- Modify: `tools/parsergen/tests/test_follow_select.py:38-194`
- Modify: `tools/parsergen/src/parsergen/analysis.py:109-113`
- Modify: `tools/parsergen/src/parsergen/analysis.py:1852-1973`

**Interfaces:**
- Consumes: `_PackedPrefix = tuple[int, int]`, `_ContinuationFirst.prefix_masks`, существующие `_FollowTransform`, `_packed_concat` и delta-worklist.
- Produces: `_FollowTransformGroup`, `_packed_project(value, max_length, solver) -> _PackedPrefix`, а также статистику `follow_projection_checks` и `duplicate_follow_projections` внутри `AnalysisResult._compressed.stats`.

- [ ] **Step 1: Зафиксировать исходное прохождение затрагиваемого тестового модуля**

Run from repository root:

```powershell
$env:PYTHONPATH=(Resolve-Path 'tools/parsergen/src').Path
python -m pytest tools/parsergen/tests/test_follow_select.py -q
```

Expected: PASS. Если исходный модуль красный, остановить реализацию и сначала зафиксировать фактическую ошибку как внешний блокер.

- [ ] **Step 2: Write the failing projection-deduplication test**

Добавить в `FollowAnalysisTests`:

```python
def test_follow_projection_deduplicates_irrelevant_delta_tails(self) -> None:
    grammar = resolved(
        "<S> ::= start\n"
        "<Owner> ::= <Parent> x u z | <Parent> x v z\n"
        "<Parent> ::= <A> p q\n"
        "<A> ::= a"
    )

    result = compute_analysis(grammar, 3, ("S",))

    self.assertEqual(
        result.follow["Parent"],
        frozenset({("x", "u", "z"), ("x", "v", "z")}),
    )
    self.assertEqual(result.follow["A"], frozenset({("p", "q", "x")}))
    stats = result._compressed.stats
    self.assertEqual(stats["follow_transform_applications"], 1)
    self.assertEqual(stats["follow_projection_checks"], 2)
    self.assertEqual(stats["duplicate_follow_projections"], 1)
```

- [ ] **Step 3: Run the new test and verify the expected failure**

Run:

```powershell
python -m pytest tools/parsergen/tests/test_follow_select.py::FollowAnalysisTests::test_follow_projection_deduplicates_irrelevant_delta_tails -v
```

Expected: FAIL because the current implementation performs two transformations and does not publish the two projection counters.

- [ ] **Step 4: Add the internal transform-group type**

Immediately after `_FollowTransform`, add:

```python
@dataclass(slots=True)
class _FollowTransformGroup:
    needed: int
    transforms: list[_FollowTransform] = field(default_factory=list)
    seen_projections: set[_PackedPrefix] = field(default_factory=set)
```

The type remains private. Its `transforms` list is populated only while dependencies are built, before fixed-point propagation starts.

- [ ] **Step 5: Add packed projection**

Immediately after `_packed_concat`, add:

```python
def _packed_project(
    value: _PackedPrefix,
    max_length: int,
    solver: _ContinuationFirst,
) -> _PackedPrefix:
    length, packed = value
    taken = min(length, max_length)
    return taken, packed & solver.prefix_masks[taken]
```

This preserves the actual length for short delta and removes packed symbols that cannot affect a `k`-bounded concatenation.

- [ ] **Step 6: Group outgoing transforms while dependencies are built**

Replace the outgoing list with groups keyed by `needed`:

```python
outgoing: list[dict[int, _FollowTransformGroup]] = [
    {} for _ in solver.production_names
]
```

After a new `transform_key` is accepted, replace the append to the flat list with:

```python
transform = _FollowTransform(*transform_key)
needed = solver.k - prefix[0]
group = outgoing[occurrence.parent_id].get(needed)
if group is None:
    group = _FollowTransformGroup(needed)
    outgoing[occurrence.parent_id][needed] = group
group.transforms.append(transform)
```

`prefix[0] < solver.k` already follows from the preceding saturated-prefix branch, therefore `needed` is always in `1..k`.

- [ ] **Step 7: Deduplicate projected deltas before applying a group**

Replace the flat transform loop inside the delta-worklist with:

```python
for group in outgoing[parent_id].values():
    stats["follow_projection_checks"] += 1
    projection = _packed_project(delta, group.needed, solver)
    if projection in group.seen_projections:
        stats["duplicate_follow_projections"] += 1
        continue
    group.seen_projections.add(projection)
    for transform in group.transforms:
        stats["follow_transform_applications"] += 1
        publish(
            transform.referenced_id,
            _packed_concat(transform.prefix, projection, solver),
        )
```

Add both new counter names to the existing final `stats.setdefault(name, 0)` loop so grammars without FOLLOW dependencies still expose stable zero values.

- [ ] **Step 8: Run the focused test**

Run:

```powershell
python -m pytest tools/parsergen/tests/test_follow_select.py::FollowAnalysisTests::test_follow_projection_deduplicates_irrelevant_delta_tails -v
```

Expected: PASS with one actual transformation, two projection checks and one skipped duplicate projection.

- [ ] **Step 9: Run FOLLOW/SELECT and oracle regressions**

Run:

```powershell
python -m pytest tools/parsergen/tests/test_follow_select.py -q
```

Expected: PASS, including 600 generated cases at `k = 1..3` and 100 generated cases at `k = 4` against the full-rescan oracle.

- [ ] **Step 10: Commit the algorithm and its regression test**

```powershell
git add -- tools/parsergen/src/parsergen/analysis.py tools/parsergen/tests/test_follow_select.py
git commit -m "perf: дедуплицировать проекции FOLLOW"
```

---

### Task 2: Benchmark counters and deterministic production gate

**Files:**
- Modify: `tools/parsergen/benchmarks/benchmark_analysis.py:242-288`
- Modify: `tools/parsergen/tests/test_benchmark_analysis.py:17-192`

**Interfaces:**
- Consumes: `AnalysisResult._compressed.stats["follow_projection_checks"]`, `AnalysisResult._compressed.stats["duplicate_follow_projections"]`, production grammar at `tools/parsergen/grammar/query-language.grammar`.
- Produces: JSON fields `counts.follow_projection_checks` and `counts.duplicate_follow_projections`; deterministic limits of 105 417 applications for `k = 2` and 1 597 664 applications for `k = 3`.

- [ ] **Step 1: Extend the small benchmark contract before changing the report**

In `test_reports_each_compressed_phase_and_work_count`, add these names to the existing `for name in (...)` assertion:

```python
"follow_projection_checks",
"duplicate_follow_projections",
```

- [ ] **Step 2: Run the contract test and verify the expected failure**

Run:

```powershell
python -m pytest tools/parsergen/tests/test_benchmark_analysis.py::AnalysisBenchmarkTests::test_reports_each_compressed_phase_and_work_count -v
```

Expected: FAIL because the two fields are present in internal stats but absent from benchmark JSON.

- [ ] **Step 3: Publish the projection counters in benchmark JSON**

In the final `counts` mapping in `_measure_worker`, add:

```python
"follow_projection_checks": stats["follow_projection_checks"],
"duplicate_follow_projections": stats["duplicate_follow_projections"],
```

Do not add a timing assertion or change the worker timeout behavior.

- [ ] **Step 4: Run the small benchmark contract**

Run:

```powershell
python -m pytest tools/parsergen/tests/test_benchmark_analysis.py::AnalysisBenchmarkTests::test_reports_each_compressed_phase_and_work_count -v
```

Expected: PASS.

- [ ] **Step 5: Add the deterministic production work-budget test**

Add to `AnalysisBenchmarkTests`:

```python
def test_production_grammar_meets_follow_work_budget(self) -> None:
    completed = self.run_cli(
        "--grammar",
        str(ROOT / "grammar" / "query-language.grammar"),
        "--k",
        "2",
        "--k",
        "3",
        "--timeout",
        "30",
    )

    self.assertEqual(completed.returncode, 0, completed.stderr)
    measurements = json.loads(completed.stdout)["measurements"]
    self.assertEqual(
        [measurement["status"] for measurement in measurements],
        ["ok", "ok"],
    )
    by_k = {measurement["k"]: measurement for measurement in measurements}
    self.assertLessEqual(
        by_k[2]["counts"]["follow_transform_applications"],
        105_417,
    )
    self.assertLessEqual(
        by_k[3]["counts"]["follow_transform_applications"],
        1_597_664,
    )
    self.assertGreater(
        by_k[3]["counts"]["duplicate_follow_projections"],
        0,
    )
```

The `k = 2` limit forbids increasing deterministic work relative to the original implementation. The `k = 3` limit is exactly one third of the measured baseline 4 792 992.

- [ ] **Step 6: Run the production work-budget test**

Run:

```powershell
python -m pytest tools/parsergen/tests/test_benchmark_analysis.py::AnalysisBenchmarkTests::test_production_grammar_meets_follow_work_budget -v
```

Expected: PASS. If the `k = 3` count exceeds 1 597 664, keep the threshold unchanged, report the actual count and return to design instead of weakening the acceptance criterion.

- [ ] **Step 7: Run all benchmark tests**

Run:

```powershell
python -m pytest tools/parsergen/tests/test_benchmark_analysis.py -q
```

Expected: PASS.

- [ ] **Step 8: Commit benchmark observability and gate**

```powershell
git add -- tools/parsergen/benchmarks/benchmark_analysis.py tools/parsergen/tests/test_benchmark_analysis.py
git commit -m "test: зафиксировать бюджет работы FOLLOW"
```

---

### Task 3: Full parity and one-process performance verification

**Files:**
- Verify only: `tools/parsergen/grammar/query-language.grammar`
- Verify only: `QueryConsoleZUP/src/DataProcessors/Парсер`
- Verify only: all files changed since `origin/master`

**Interfaces:**
- Consumes: repository test suite, `parsergen validate`, read-only `parsergen generate --check`, `_measure_worker` production benchmark.
- Produces: фактические median/p95 по 20 прогонам для `k = 2` и `k = 3`, подтверждение parity production-артефактов и чистый состав diff.

- [ ] **Step 1: Run the complete Python suite**

Run:

```powershell
$env:PYTHONPATH=(Resolve-Path 'tools/parsergen/src').Path
python -m pytest tools/parsergen/tests -q
```

Expected: PASS. Допустим только уже известный skip проверки symlink при отсутствии Windows-привилегии; новые skips или failures недопустимы.

- [ ] **Step 2: Validate the production grammar**

Run:

```powershell
python -m parsergen validate --config parsergen.toml
```

Expected: exit code `0`, без новых ошибок; две существующие диагностики VAL102 допустимы.

- [ ] **Step 3: Verify generated production artifacts read-only**

Run:

```powershell
python -m parsergen generate --config parsergen.toml --check
```

Expected: exit code `0` and `artifacts are current`. Не запускать `generate` без `--check`.

- [ ] **Step 4: Run 20 warm one-process measurements for each k**

Run from `tools/parsergen`:

```powershell
@'
from math import ceil
from statistics import median

from benchmarks.benchmark_analysis import DEFAULT_GRAMMAR, _measure_worker


def p95(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[ceil(len(ordered) * 0.95) - 1]


for k in (2, 3):
    warmup = _measure_worker(DEFAULT_GRAMMAR, k, False, None)
    if warmup["status"] != "ok":
        raise RuntimeError(warmup)
    runs = [
        _measure_worker(DEFAULT_GRAMMAR, k, False, None)
        for _ in range(20)
    ]
    if any(run["status"] != "ok" for run in runs):
        raise RuntimeError(runs)
    print(f"k={k}")
    for phase in runs[0]["timing_ms"]:
        values = [run["timing_ms"][phase] for run in runs]
        print(
            f"  {phase}: median={median(values):.3f} ms "
            f"p95={p95(values):.3f} ms"
        )
    print(
        "  follow_transform_applications=",
        runs[-1]["counts"]["follow_transform_applications"],
    )
    print(
        "  duplicate_follow_projections=",
        runs[-1]["counts"]["duplicate_follow_projections"],
    )
'@ | python -
```

Expected:

- `k = 3` packed FOLLOW median is at most `2 000 ms`;
- `k = 2` packed FOLLOW median is at most `200.705 ms`;
- p95 is reported for every phase without being used as a CI failure threshold;
- the operation counts match the deterministic production test.

If only the wall-clock goal fails while the deterministic count passes, preserve the correct implementation, record the measured result and design a separate factorized FOLLOW iteration. Do not change the grammar or production parser to improve the number.

- [ ] **Step 5: Check scope, whitespace and protected files**

Run from repository root:

```powershell
$baseCommit = git merge-base origin/master HEAD
git diff --check $baseCommit HEAD
git diff --exit-code $baseCommit HEAD -- tools/parsergen/grammar/query-language.grammar 'QueryConsoleZUP/src/DataProcessors/Парсер'
git status --short --branch
git diff --stat $baseCommit HEAD
```

Expected: no whitespace errors; no diff in grammar or production parser; only the approved design, plan, Python implementation, tests and benchmark changes appear.

---

### Task 4: Independent correctness, complexity and coverage review

**Files:**
- Review: `tools/parsergen/src/parsergen/analysis.py`
- Review: `tools/parsergen/tests/test_follow_select.py`
- Review: `tools/parsergen/benchmarks/benchmark_analysis.py`
- Review: `tools/parsergen/tests/test_benchmark_analysis.py`
- Review: `docs/superpowers/specs/2026-08-07-parser-generator-follow-optimization-design.md`

**Interfaces:**
- Consumes: diff from `origin/master` to `HEAD`, test and benchmark evidence from Task 3.
- Produces: независимая оценка корректности инварианта проекции, asymptotic complexity, достаточности тестового покрытия и соблюдения границ ветки.

- [ ] **Step 1: Request an independent review**

Invoke `superpowers:requesting-code-review` and assign the review to a fresh `gpt-5.6-sol` reviewer. Provide the base commit from `git merge-base origin/master HEAD`, current `HEAD`, the approved spec and the verification output.

Ask the reviewer to answer explicitly:

```text
1. Correctness: does grouping by (parent, needed) preserve every FOLLOW result,
   including short words, END, cycles and matcher classes?
2. Complexity: which loops and retained sets change asymptotically, and can the
   optimization introduce a memory blow-up?
3. Coverage: which meaningful equivalence classes or failure modes are not
   exercised by the focused test, generated oracle tests and production gate?
4. Scope: were grammar, public API or production parser changed indirectly?
```

- [ ] **Step 2: Process review findings rigorously**

If the reviewer reports an actionable issue, invoke `superpowers:receiving-code-review`, reproduce the issue, add a failing test where applicable, make the minimal fix, rerun Tasks 1–3 checks and request re-review. Do not implement speculative suggestions without evidence.

- [ ] **Step 3: Record the final review outcome**

Expected: no unresolved correctness or scope issues. Report any accepted residual performance or coverage risk explicitly in the final handoff; do not describe an unexecuted manual check as passed.
