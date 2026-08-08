# Wave 2 report: Parser IR и direct BSL Decision DAG

## Scope

Волна реализует Tasks 5–9: symbolic Parser IR boundary, direct BSL renderer,
production/group/value dispatch, explicit Optional/Repeat exits и общий
LeftFold loop DAG. Semantic inlining и caller/callee optimizer не входят в
scope.

## Общий RED Tasks 5–9

До production changes был добавлен весь связанный test set. Команды и
наблюдения:

- Parser IR/codegen/EBNF/LeftFold: `9 failed, 48 passed, 2 subtests passed`.
  Failures точно показывали row materialization, повторные per-alternative
  predicates, implicit Optional/Repeat exit и отдельный LeftFold guard.
- Новый renderer test отдельно завершался collection error
  `ModuleNotFoundError: parsergen.canonical_bsl_decisions`.

## Bug discovery в review-clean Tasks 1–4

### Phase 1 evidence

Первый полный parsergen pytest после Wave 2 focused GREEN дал
`34 failed, 521 passed, 1 skipped, 27006 subtests passed`. Помимо ожидаемого
artifact/reference drift были реальные production semantic failures:

- `ТипСоединения` генерировался как unconditional syntax error;
- `ОписаниеТипа` терял alternatives `БУЛЕВО` и `ДАТА`;
- `АгрегатнаяФункция` терял optional `РАЗЛИЧНЫЕ` и argument `*`;
- repository tests фиксировали отсутствующие constructors/branches.

На symbolic source boundary для `ТипСоединения` alternative `ЛЕВОЕ` при
`k = 2` получался путь:

```text
root --ЛЕВОЕ--> depth 1 --СОЕДИНЕНИЕ(FOLLOW)--> depth 2
```

У depth-2 node было `accepting=False, edges=()`. Поэтому
`_DecisionSemantics.can_accept(..., remaining=0)` корректно для полученного
source отвечал `False`, все четыре outcomes отбрасывались, а DAG становился
`ImmediateError(expected=())`.

Минимальная репродукция границы:

```text
<S> ::= <A> Z
<A> ::= X | Y
```

При `k = 2` обе languages `A` заканчивались depth-2 nodes с
`accepting=False`, и весь DAG был `ImmediateError`. Это отличается от уже
работавших случаев:

- short complete FIRST-prefix имеет настоящий terminal factor state до `k`;
- EOF проходит специальный derivative/end-outcome путь;
- source alternatives с unique first token могут early-commit до дефектного
  saturated leaf и случайно скрывают проблему.

Root cause находится в export boundary: `_export_language()` переносил только
`compressed.factor_state_terminal(state)`, хотя canonical contract считает
любой prefix длины `k` saturated и завершённым независимо от наличия более
длинного symbolic continuation.

### Hypothesis и regression RED

Единственная гипотеза: depth-`k` exported node должен быть accepting; тогда
viability и независимый validator сохранят точную `FIRST_k(α FOLLOW_k(A))`
семантику без специальных renderer fallbacks.

Regression test строит указанный `<A>` decision, проверяет leaves `X Z` и
`Y Z` и ожидает соответствующие `CommitAlternative`. До root fix он RED:
первая оценка возвращала `ImmediateError(expected=())` вместо
`CommitAlternative(AlternativeOutcome("A", 1))`.

### Root fix

Единственное production изменение сделано в `canonical_select._export_language`:
exported node имеет `accepting=True`, если `depth == compressed.k` или factor
state действительно terminal. `decision_dag` и его независимый validator не
ослаблялись; renderer не получил fallback. Публичный API не изменился.

После fix минимальный regression test GREEN. Production spot-check вернул
все четыре `ТипСоединения`, `БУЛЕВО`/`ДАТА`, `РАЗЛИЧНЫЕ` и `*`.

## Реализация Tasks 5–9

- `CanonicalDecision` хранит только symbolic source и validated DAG.
- `BranchIr`/`ValueBranchIr` связаны с полными `AlternativeOutcome`.
- Parser IR кэширует решения по `(production, exit_alternative)` и хранит
  protected entrypoint productions.
- Direct renderer выдаёт structured BSL, кэширует
  `ТокенРешения0..N`, группирует exact token-set edges с общим target и не
  создаёт runtime DAG objects/tables/helpers.
- Production, group и value dispatch используют общий leaf join.
- Optional/Repeat/WrapOptional/LeftFold различают commit, exit и error;
  Repeat/LeftFold используют `Пока Истина Цикл` и explicit `Прервать`.
- Legacy `canonical_bsl_conditions.py` и его tests удалены; legacy symbol
  search возвращает no matches.

## Commits

- `2613bf8` — `Перевести Parser IR на Decision DAG`
- `49105a4` — `Генерировать прямой BSL из Decision DAG`
- `caf5974` — `Факторизовать canonical dispatch в BSL`
- `839b277` — `Сделать EBNF exit частью canonical DAG`
- `15b936b` — `Перевести LeftFold на общий Decision DAG`
- `4b9bdfb` — `Проверить коллизии локальных переменных решений`
- `6d1331a` — `Сохранить saturated canonical SELECT в Decision DAG`

## GREEN evidence

- Wave 2 focused IR/codegen: `105 passed, 2 subtests passed`.
- Wave 1 canonical select/DAG/property после root fix:
  `27 passed, 22820 subtests passed`.
- Repository import подтверждён из `tools/parsergen/src/parsergen/__init__.py`.
- `parsergen validate`: PASS.
- Audit после root fix: canonical conflicts/diagnostics empty,
  `public_select_expansions = 0`, `select_cartesian_materializations = 0`.
- Audit generated shape: `lookahead_calls = 136`; changed artifact только
  production `ObjectModule.bsl`.
- `git diff --check`: PASS перед commits.

### Verification addendum на final Wave 2 HEAD

После saturated SELECT root fix по прямому review-требованию повторен полный
`python -m pytest tools/parsergen/tests -q`: `11 failed, 525 passed, 1 skipped,
27026 subtests passed` за `43.92s`. Первый post-fix запуск завершился, но его
финальный output был усечён инструментом; для доказуемой сводки та же команда
была повторена с сохранением её хвоста. Все 11 падений классифицированы:

- `MigrationAuditUnitTests::test_build_report_has_separate_canonical_and_legacy_sections`
  и
  `MigrationAuditProductionTests::test_canonical_and_legacy_contracts_are_separate`
  ожидают `artifacts.changed == []`, но намеренно не регенерированный Task 13
  `ObjectModule.bsl` отличается.
- `MigrationAuditProductionTests::test_generated_shape_baseline_is_explicit`
  сравнивает со старым pre-DAG shape baseline; его обновление входит в Task 13.
- `ReferenceParserTests::test_full_extended_grammar_matches_reference_parser`
  сравнивает in-memory direct-DAG output с намеренно stale Task 13
  reference parser.
- `RepositoryGrammarCompatibilityTests::test_alias_alternatives_return_their_identifier_value`
  проверяет старый номер temporary: direct DAG корректно вызывает
  `Идентификатор("ID_ПсевдонимРасширенный")` и возвращает его через
  `Значение2`, а assertion требует `Значение1`.
- три subtests
  `RepositoryGrammarCompatibilityTests::test_operand_alternatives_return_their_single_child`
  (`Выбор`, `Параметр`, `АгрегатнаяФункция`) аналогично проверяют
  pre-DAG temporary `Значение1`; нужные child calls и return assignments в generated
  branches присутствуют.
- два wrapper subtests и aggregate failure
  `RepositoryGrammarCompatibilityTests::test_postfix_predicates_generate_max_one_canonical_wrappers`
  требуют ровно одну текстовую копию action. Structured DAG рисует две
  копии во взаимоисключающих branches; за один runtime parse выполняется одна.
  Текстовая дедупликация относится к Wave 3 optimizer и здесь не выполнялась.

Таким образом, среди финальных failures нет доказанного runtime semantic
regression: четыре связаны с отложенными Task 13 artifacts/baselines, семь —
с изменившейся текстовой формой direct DAG. Production/reference fixtures не
регенерировались, tests под старую форму не ослаблялись.

Дополнительная verification на том же HEAD:

- `python -m parsergen validate --config parsergen.toml`: exit `0`.
- `git diff --check`: exit `0`.
- `generate --check`: ранее зафиксированный deliberate exit `3`, только stale
  `ObjectModule.bsl`; артефакт не перегенерирован.

## Изменённые файлы

- `tools/parsergen/src/parsergen/parser_ir.py`
- `tools/parsergen/src/parsergen/cli.py`
- `tools/parsergen/src/parsergen/canonical_select.py`
- `tools/parsergen/src/parsergen/canonical_bsl_decisions.py`
- `tools/parsergen/src/parsergen/canonical_bsl_codegen.py`
- удалён `tools/parsergen/src/parsergen/canonical_bsl_conditions.py`
- focused tests Parser IR, canonical decisions/codegen/bindings/EBNF/LeftFold,
  fragments и saturated Decision DAG regression.
- удалён legacy `test_canonical_bsl_conditions.py`.

## Self-review

- Outcome lookup везде использует полный `AlternativeOutcome`, а не bare
  integer; production/group/tail identities не смешиваются.
- Semantic operations остаются внутри committed leaf и сохраняют порядок;
  early commit не делает rollback и terminal actions продолжают выдавать
  точную ошибку после выбора alternative.
- `#ID_*` раскрываются только как exact token sets; reverse exact-set index
  подготовлен, named helper emission до Task 12 отключён.
- Runtime BSL не содержит DAG tables/objects или helper-per-node.
- Production lookahead остаётся 2; optimizer/inlining Wave 3 не затронут.

## Artifact drift и concerns

Production parser/reference fixtures намеренно не регенерировались (Task 13).
`generate --check` завершился exit `3` и сообщает stale `ObjectModule.bsl`;
audit также перечисляет этот единственный changed artifact. Reference parser,
migration audit baseline и ряд repository textual-shape assertions остаются
stale до Task 13. EDT/YAxUnit не запускались, потому что в этой волне
production BSL artifact не изменяется.

Отдельный concern: structured DAG может текстуально повторить один action leaf,
если hash-consed leaf достижим из разных вложенных states; ветви взаимоисключающи,
поэтому runtime action выполняется ровно один раз. Устранение такого текстового
повтора относится к Wave 3 composition/optimization, который здесь намеренно
не выполнялся.

## Fix round 1

### Findings и root cause

1. Saturated regression защищал DAG outcome только на полных `("X", "Z")` и
   `("Y", "Z")`. Validator сравнивает DAG с уже exported source, поэтому
   согласованное overaccepting изменение exporter/validator осталось бы
   незамеченным. Production exporter после `6d1331a` уже exact; дефектом был
   недостаточный независимый test oracle.
2. Alias и три operand subtests привязывали semantic contract к pre-DAG
   ordinal `Значение1`. Реальный invariant: temporary, куда записан каждый
   expected child call, должен быть передан в `РезультатПродукции`.

### RED evidence

- До изменения repository assertions alias test и operand subtests `Выбор`,
  `Параметр`, `АгрегатнаяФункция` падали на ожидании
  `Значение1`; generated branches содержали child call и paired return под
  другим номером.
- Первая версия semantic helper дала адресный RED:
  `1 failed, 6 passed, 23462 subtests passed`: `НеТерминалПоле()` законно
  присутствовал в трёх взаимоисключающих leaves. Helper уточнён: он не
  требует text deduplication, но проверяет pairing для каждого emitted call.
- Для exporter tests выполнён mutation RED: temporary mutation
  `accepting = depth > 0 or terminal` дала `4 failed, 2 passed`. Exporter-level
  assertions поймали `_accepts(..., ("X",)) is True`, а independent materializer
  нашёл лишние `("X",)` и `("Y",)` относительно `analysis.select`. Mutation
  сразу удалена; production diff в round отсутствует.

### Changes и commit

- `tools/parsergen/tests/test_canonical_select.py`: incomplete saturated prefixes ложны,
  full depth-`k` paths истинны.
- `tools/parsergen/tests/test_decision_dag.py`: source exactness проверяется отдельно от
  сохранённого early-commit evaluator behavior.
- `tools/parsergen/tests/test_decision_dag_property.py`: symbolic languages материализуются
  независимым DFS и exact сравниваются с `analysis.select` в targeted и 200
  deterministic randomized cases.
- `tools/parsergen/tests/test_repository_grammar.py`: alias/operand assertions извлекают
  actual `ЗначениеN` для каждого expected child call и проверяют ровно одно
  парное result assignment.
- Commit: `c6cc1ba` — `Уточнить exact-language контракты Decision DAG`.

### GREEN и final verification

- Covering files и exact repository cases: `31 passed, 23469 subtests passed`.
- Wave 1 + Wave 2 focused: `129 passed, 23463 subtests passed`.
- Единственный full pytest этого round: `7 failed, 528 passed, 1 skipped,
  27672 subtests passed` за `48.52s`. Фактический remaining set ровно разрешённый:
  - Task 13 (3):
    `MigrationAuditUnitTests::test_build_report_has_separate_canonical_and_legacy_sections`,
    `MigrationAuditProductionTests::test_canonical_and_legacy_contracts_are_separate`,
    `ReferenceParserTests::test_full_extended_grammar_matches_reference_parser`;
  - Task 12 audit baseline (1):
    `MigrationAuditProductionTests::test_generated_shape_baseline_is_explicit`;
  - Task 11 wrapper specialization (3): two subtests (`ЛогическийМножитель`,
    `ОперандСравнения`) и aggregate failure в
    `RepositoryGrammarCompatibilityTests::test_postfix_predicates_generate_max_one_canonical_wrappers`.
- Repository import: `tools/parsergen/src/parsergen/__init__.py`.
- `python -m parsergen validate --config parsergen.toml`: exit `0`.
- `git diff --check`: exit `0`.
- Production/reference artifacts не регенерировались; wrapper production code не изменялся.

### Self-review

- Expected language берётся напрямую из public `analysis.select`; materializer не использует
  exporter/DAG evaluator logic и поэтому не является mirror assertion.
- Property comparison охватывает каждый outcome language, включая nullable/EOF,
  exact `#ID_*` predicates и `k = 1..3`.
- `_accepts(..., ("X",)) is False` проверяет только symbolic source. DAG evaluator
  по-прежнему может early-commit по единственной viable alternative; контракт не
  ослаблен.
- Temporary helper не фиксирует ordinal и не требует Wave 3 text deduplication;
  каждый фактически emitted child call остаётся связан с одним result assignment.
