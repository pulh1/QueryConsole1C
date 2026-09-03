# Task 3 report: conditional Python runtime and backend fences

## Status

DONE. Generated Python получает scoped runtime extension только когда live IR
содержит `AppendNearestOwner`. Canonical BSL и hybrid BSL fail closed по source
и live IR до rendering/routing, а combined grammar отвергает ведущий `^` с
`GP010`. Legacy generated Python text остался byte-identical.

## Runtime contract and lifecycle proof

`AppendNearestOwner` сериализуется одним opcode с owner, property,
`source_order` и ровно одним payload source: bound value либо current field.
Runtime state создаётся на `self` при каждом `parse`, поэтому owner stacks,
pending queues и sequence instance-local.

При выполнении opcode runtime сначала снимет `stack[-1]` требуемого точного
constructor name. Этот owner instance сохраняется в receiver до завершения
payload parse; nested owner, открытый во время payload, не может перехватить
эффект. Bound payload проходит существующий `_run_bound_value` ровно один раз и
тем же значением доставляется прежнему receiver. `$CurrentField` читается один
раз непосредственно из текущего builder. Missing owner немедленно пропускает
enqueue, не создаёт queue и не увеличивает sequence.

Для существующего owner добавляется точная запись:

```text
(source_order, enqueue_sequence, property, payload)
```

`enqueue_sequence` монотонно увеличивается в пределах runtime parse. Перед
freeze именно этого builder его entries сортируются по первым двум полям и
добавляются в именованные collections. Успешный close выполняется строго:

```text
flush -> freeze -> pop exact owner instance -> outward delivery
```

Внешний `finally` у `parse` очищает stacks, pending queues и сбрасывает sequence
после syntax, freeze, append error и успешного parse. Один и тот же parser после
каждого из трёх классов ошибок успешно используется повторно.

Behavioral proof фиксирует:

- same-type child затеняет parent: leaf payload попадает только в child;
- parent tap сохраняет выбранный parent до разбора child, а parent получает уже
  frozen child;
- `$CurrentField` после child попадает в parent, доказывая pop child до
  последующей outward обработки;
- profile orders `tail=0`, `child=1`, `$Name=2` дают parent collection
  `("tail", frozen_child, "outer")`, хотя child структурно разбирается раньше;
- три repeat executions одного статического order сохраняют FIFO
  `("first", "second", "third")`;
- counting tokens читаются по одному разу, а ordinary receiver и scoped
  collection получают тот же payload ровно по одному разу;
- standalone leaf без Owner успешно возвращает свой AST, то есть missing owner
  остаётся no-op.

## Conditional generation and backend fences

`_SemanticGenerator` выставляет scoped feature flag только при фактической
сериализации opcode. Legacy path по-прежнему конкатенирует исходный
`_RUNTIME_TEMPLATE` без дополнительных байтов; scoped path добавляет отдельный
runtime subclass. Schema scan добавляет named collection target даже когда tap
вложен в ordinary receiver или другой bound value.

Canonical entrypoints проверяют `SourceScopedValue` и `AppendNearestOwner` до
создания generator/rendering. Hybrid выполняет тот же check самой первой
операцией, раньше canonical ownership и маршрутизации. Tests независимо
подкладывают source-only и IR-only effect. Пустые entrypoints/ownership намеренно
передаются одновременно: scoped-specific exception выигрывает, доказывая ранний
fence. Combined grammar поглощает недопустимый scoped prefix и публикует один
`GP010` на ведущем `^`, не поздний binding diagnostic.

## TDD evidence

### Runtime RED

До production changes:

```text
python -m pytest tools/parsergen/tests/test_scoped_append_python_runtime.py -q
6 failed in 0.29s
```

Все шесть падений доходили до реального codegen и завершались
`TypeError: AppendNearestOwner`, то есть причиной была отсутствующая feature, а
не test harness. Первый минимальный serializer run выявил nested value path;
после его добавления оставался один `KeyError: 'Items'`, который доказал
необходимость recursive scoped schema scan. После обоих root-cause fixes
runtime module прошёл полностью.

### Backend RED

До backend production changes:

```text
python -m pytest tools/parsergen/tests/test_scoped_append_backend_fences.py -q
5 failed in 0.22s
```

Canonical cases доходили до `entrypoint mapping must not be empty`, hybrid — до
`canonical production ownership must not be empty`, combined grammar выдавал
`BIND201` вместо `GP010`. Это отдельно доказало отсутствие ранних fences.

### GREEN

```text
python -m pytest \
  tools/parsergen/tests/test_scoped_append_backend_fences.py \
  tools/parsergen/tests/test_canonical_bsl_codegen.py \
  tools/parsergen/tests/test_hybrid_bsl_codegen.py -q
25 passed in 0.21s

python -m pytest <Task 3 expanded focused set> -q
96 passed in 0.83s

python -m pytest tools/parsergen/tests -q
690 passed, 1 skipped in 49.89s
```

Skip — прежнее Windows privilege restriction на создание symlink в
`test_artifacts.py`.

## Legacy byte identity and gates

Dedicated fresh regression after implementation commit:

```text
python -m pytest \
  tools/parsergen/tests/test_separated_semantics_legacy.py::\
  test_legacy_python_semantic_module_text_is_byte_identical -q
1 passed in 0.09s
```

Проверенный SHA-256 legacy module:
`5aa204ccdaddb8dba6d07da5f861bb1716be03a83d50e5ff8cacdbf44abcf01c`.

- `python -m compileall -q ...`: PASS.
- `git diff --cached --check`: PASS перед implementation commit.
- Forbidden staged scan по
  `FactSeq|SemanticResultKind|semantic_result_shape|coalescer`: PASS.
- Feature production additions: `1193` из лимита `2000`.
- Feature total additions including this report: `2644` из лимита `4000`.
- Task 3: `6 files changed, 475 insertions(+), 4 deletions(-)`;
  production additions `172`.
- `.runtime/` оставлен untracked и не изменялся/staged.

## Self-review

- Mutation `stack[0]` вместо `stack[-1]` ломает child shadowing.
- Resolution owner после payload parse ломает parent capture при nested child.
- Freeze до flush ломает immutable collection result; pop после outward
  delivery ломает последующий `$CurrentField` target.
- Sort только по structural execution либо без sequence ломает source-order/FIFO
  regressions.
- Повторный parse payload ломает token read counts и ordinary receiver result.
- Queue для missing owner ломает no-op path или sequence/state guarantees.
- Удаление любого finally clear ломает один из трёх error-and-reuse cases.
- Source-only/IR-only detector omissions ломают соответствующие backend
  parametrizations; поздний fence ломает priority assertions.
- Conditional extension removal или legacy template edit ломает exact digest.

Reviewer subagent не запускался из-за явного запрета Task 3 на субагентов;
выполнен этот локальный line-by-line и mutation-oriented self-review.

## Commit and concerns

- Implementation: `c5aa59e7d91dac56dcf0252c84e5e5d8382622fa`
  (`feat(parsergen): run scoped owner appends`).
- Base: `b5d4aa7a1ac9b57d8d62fa929344bf8925626397`.

Открытых concerns нет. Pre-existing optional-group `BIND210` limitation из Task
2 не затрагивался и к runtime/backend contract Task 3 не относится.
