# Wave 3 report: semantic optimization и Decision DAG metrics

## Scope и результат

Wave 3 реализует сгруппированные Tasks 10–12 поверх base
`17dca9f5144c86ec1c6fba20c4adfbc840e75733`:

- structural proof semantic transparency и test-only action traces;
- exact symbolic caller/callee specialization для доказуемых `WrapOptional`
  sites;
- recursive reachability cleanup от фактических entrypoints и внешних legacy
  callers;
- агрегированные DAG/static metrics;
- измеряемое сравнение inline exact predicates и reusable exact named sets.

Production artifact и reference parser не регенерировались: это остаётся
Task 13. Финальный functional set GREEN; полный suite оставляет ровно три
предусмотренных Task 13 failures.

## Сгруппированный RED

Полный test set Tasks 10–12 был написан до production optimizer/metrics code и
зафиксирован отдельным коммитом `b84388c`.

Первый запуск:

```text
python -m pytest tools/parsergen/tests/test_parser_ir_optimization.py \
  tools/parsergen/tests/test_repository_grammar.py \
  tools/parsergen/tests/test_migration_audit.py \
  tools/parsergen/tests/test_canonical_bsl_decisions.py -v
```

останавливался на collection RED:

```text
ImportError: cannot import name 'specialize_outcome'
```

То есть production API symbolic specialization ещё не существовал. RED-набор
одновременно фиксировал:

- table-driven structural transparency cases;
- entrypoint, recursive SCC, LeftFold и provenance boundaries;
- successful, exit и committed-failure action traces;
- exact caller/callee language intersection и exactly-once semantic actions;
- unsupported call sites и reachability от actual entrypoints;
- три ранее deferred wrapper-text assertions Task 11;
- точный `decision_dag` audit schema и explicit baseline;
- cached-token named-set rendering без lookahead в helper call.

Во время широкого GREEN-прогона существующий repository test обнаружил ещё
один regression RED: `Поле` содержал три текстовые эмиссии
`НовыйРазыменование` вместо одной. Минимальный optimizer regression test
`test_repeated_semantic_action_without_common_prefix_proof_is_unchanged`
воспроизводил проблему и до исправления падал: specialized caller больше не
содержал `НеТерминалChoice()` и копировал общий constructor в две ветви.

## Task 10: semantic transparency и action traces

Добавлен точный public result:

```python
@dataclass(frozen=True, slots=True)
class TransparencyResult:
    transparent: bool
    reason: str
```

Classifier проверяет структуру Parser IR, а не имя/форму production. Он
запрещает удаление для:

- public entrypoints;
- recursive SCC и `LeftFold`;
- formal parameters;
- production decision и provenance/source boundaries;
- constructors, scalar/collection bindings и mutations;
- constants, `WrapOptional`, `WrapValue` и folds.

Transparent successful path обязан единообразно возвращать ровно один
неизменённый child result либо быть syntax-only. Test-only evaluator сравнивает
до/после traces `construct`, `parse`, `bind`; success, optional exit и
committed failure сохраняют порядок и exactly-once behavior. Constructor
остаётся failure-local, но никогда не классифицируется transparent wrapper.

## Task 11: symbolic specialization и cleanup

`intersect_languages(left, right)` строит exact product automaton двух
symbolic languages. `specialize_outcome(...)`:

- требует одинаковый lookahead;
- заменяет ровно один caller outcome;
- пересекает его с каждым callee outcome;
- удаляет только доказанно пустые intersections;
- сохраняет caller exit и unrelated outcomes;
- не использует priority, fallback или materialized SELECT rows.

Optimizer работает до BSL codegen. Он подставляет только direct,
parameter-free callee branch до caller-specific token consumption/actions,
композирует symbolic sources, затем заново строит и валидирует DAG. Callee
actions исполняются в отдельном выбранном action region ровно один раз, после
decision и до caller join; действия не перемещаются через token consumption.

Поддерживаемая начальная specialization ограничена `WrapOptional`, где
существует общий caller continuation. `Dispatch`, `RepeatLoop` и
`OptionalBranch` рекурсивно оптимизируют содержимое, но не получают
недоказанный action join.

Regression `Поле` разрешён консервативно и структурно: если разные callee
alternatives имеют одинаковый leading semantic action signature, composition
оставляется unchanged, потому что specialized renderer не имеет доказательства
common-prefix factoring. Проверяются сами semantic operations
(`ConstructNode`, constant assignment/return), а не production names.

После подстановок recursive reachability начинается с actual protected
entrypoints и selected productions, на которые ссылаются legacy productions.
Удаляются только действительно недостижимые canonical functions. Поэтому
standalone logical/LIKE wrappers исчезают лишь при отсутствии оставшихся
ссылок, а unsupported sites и externally referenced callees сохраняются.

## Task 12: metrics и predicate policy

Audit теперь содержит точный раздел:

```json
{
  "source_states": 33718,
  "dag_states": 415,
  "shared_states": 89,
  "max_depth": 2,
  "decision_regions": 112,
  "emitted_predicates": 316
}
```

Parser IR walker рекурсивно проходит nested operations/values. Decision
regions и DAG totals дедуплицируются по object identity; emitted predicates
считаются отдельно в соответствии с фактическим recursive BSL renderer,
включая повторную textual emission shared DAG target по разным parents.

Production generated-shape baseline:

```json
{
  "bsl_functions": 74,
  "bsl_loc": 2446,
  "constructor_names": 79,
  "select_rows": 0,
  "identifier_rows": 276,
  "lookahead_calls": 132,
  "decision_lines": 374,
  "predicate_atoms": 3783,
  "nonterminal_functions": 63,
  "nonterminal_call_sites": 176,
  "max_condition_chars": 2551,
  "max_condition_predicate_atoms": 88,
  "max_condition_lookahead_calls": 1,
  "max_condition_nesting": 2
}
```

In-memory comparison не пишет artifacts. Candidate named set должен содержать
больше восьми exact tokens, использоваться минимум три раза и иметь точное
matcher-definition label. Измерение финального implementation HEAD:

| Policy | BSL LOC | Max condition | Helper calls | Python generation |
| --- | ---: | ---: | ---: | ---: |
| inline exact sets | 2446 | 2551 | 0 | 0.01267 s |
| named exact sets | 2451 | 2551 | 3 | 0.00522 s |

Eligible named sets: `1`. Runtime BSL timing недоступен, поэтому binding rule
выбирает named policy только при строго меньшем generated LOC. Named candidate
увеличивает LOC, следовательно selected policy: `inline`.

Опциональный named renderer всё же полностью реализован и протестирован для
последующего измерения. Helper имеет прямую BSL сигнатуру
`ТокенПринадлежитКлассу(ТипТокена, ИмяКласса)`, принимает уже cached token,
делает exact table lookup и никогда не вызывает `ТипТокенаПросмотра`.

## GREEN evidence

Focused проверки:

- optimizer + `Поле` regression: `10 passed, 8 subtests passed`;
- canonical select/DAG/Parser IR/codegen/hybrid/repository set:
  `111 passed, 134 subtests passed`;
- Task 12 excluding только две deliberate stale-artifact assertions:
  `24 passed, 2 deselected`;
- optimizer после self-review cleanup: `9 passed, 8 subtests passed`;
- `python -m compileall -q tools/parsergen/src tools/parsergen/benchmarks
  tools/parsergen/tests`: exit `0`;
- `git diff --check`: exit `0`.

Полный suite:

```text
3 failed, 559 passed, 1 skipped, 27724 subtests passed in 74.55s
```

Единственный skip связан с недоступной Windows symlink privilege. Failure set
ровно Task 13:

1. `MigrationAuditUnitTests::test_build_report_has_separate_canonical_and_legacy_sections`
   — audit сообщает stale `ObjectModule.bsl`.
2. `MigrationAuditProductionTests::test_canonical_and_legacy_contracts_are_separate`
   — тот же deliberate stale artifact.
3. `ReferenceParserTests::test_full_extended_grammar_matches_reference_parser`
   — reference `ObjectModule.bsl` ещё не регенерирован.

Generated-shape audit baseline, все три Task 11 wrapper assertions и все
прочие parsergen tests GREEN.

## Validate, audit и artifact check

Project-local package должен быть первым в `PYTHONPATH`; без этого текущая
машина выбирает устаревшую global editable install, которая не знает config
section `migration`. Авторитетный запуск с local source:

```text
$env:PYTHONPATH=(Resolve-Path 'tools/parsergen/src')
python -m parsergen validate --config parsergen.toml
```

завершился exit `0`.

Read-only audit завершился exit `0`, canonical diagnostics/conflicts пусты и
сообщил единственный changed artifact:

```text
QueryConsoleZUP\src\DataProcessors\Парсер\ObjectModule.bsl
```

`python -m parsergen generate --config parsergen.toml --check` завершился
ожидаемым exit `3` и вывел только `ObjectModule.bsl`. Ни production artifact,
ни reference parser не появились в `git status`; regeneration запрещена до
Task 13.

## Commits

- `b84388c` — `Зафиксировать RED контракты Wave 3`;
- `d631024` — `Специализировать semantic caller callee decisions`;
- `f4d62f4` — `Ограничить специализацию доказуемыми action traces`;
- `990148c` — `Добавить метрики canonical Decision DAG`;
- `032a8c4` — `Упростить внутренний API оптимизатора`.

## Изменённые компоненты

- `canonical_select.py`: exact language intersection/specialization;
- `decision_dag.py`: heterogeneous composed outcomes и metrics aggregation;
- `parser_ir_optimization.py`: transparency, SCCs, specialization, traces и
  reachability;
- `parser_ir.py`: optimization после raw IR build;
- `canonical_bsl_codegen.py`, `canonical_bsl_decisions.py`:
  exactly-once specialized action regions и optional exact named predicates;
- `hybrid_bsl_codegen.py`: optimized canonical subset и safe omitted functions;
- `audit_migration.py`: recursive DAG metrics и in-memory policy benchmark;
- focused optimizer, renderer, audit и repository tests.

## Self-review и concerns

- Composition всегда начинается с symbolic sources/languages; early-committed
  DAG leaves не используются как семантический input.
- Fresh DAG проходит существующий independent validator; matcher sets остаются
  exact, без priority/fallback/materialization.
- Caller exit/error остаются в caller source; callee outcomes сохраняют
  provenance и alternative identity.
- Action trace evaluator независим от codegen text и проверяет success, exit и
  committed failure. Repository shape tests отдельно фиксируют single emitted
  semantic regions.
- Optimization намеренно консервативен: повторяющийся leading semantic prefix
  и controls без доказанного common continuation остаются unchanged. Это не
  дефект корректности, а явная граница initial specialization.
- Python generation timing шумный и не используется для выбора без runtime BSL
  evidence. Binding selection основан только на строгом LOC improvement;
  поэтому текущий результат стабильно inline.
- Единственная environmental caveat — stale globally installed `parsergen`;
  verification всегда запускается с явным local `PYTHONPATH`.
