# Архитектура генератора парсера

## Назначение и владение

`tools/parsergen` — исходный код генератора LL(k)-парсера языка запросов. Этот каталог владеет Python-реализацией, тестами, benchmark-сценариями и канонической входной грамматикой `grammar/query-language.grammar`.

EDT-обработка `QueryConsoleZUP/src/DataProcessors/Парсер` владеет результатом генерации. В ней генератор обслуживает ровно три артефакта:

- `ObjectModule.bsl`;
- `Templates/ТаблицаПервыхСимволовВариантов/Template.txt`;
- `Templates/ОпределенияИдентификаторов/Template.txt`.

Связь входов и выходов задаёт корневой `parsergen.toml`. Изменение production-артефактов должно быть отдельным осознанным действием после проверки diff, а не побочным эффектом тестов.

## Pipeline

1. `config.py` читает TOML, разрешает пути относительно файла конфигурации и сохраняет порядок точек входа.
2. `grammar_parser.py` разбирает source grammar в immutable high-level AST из `source_model.py`.
3. `source_validation.py` до lowering доказывает productivity, nullability и минимальное потребление для EBNF-конструкций.
4. `lowering.py` детерминированно преобразует source AST в прежнюю плоскую canonical CFG и сохраняет origin sidecar.
5. `resolver.py` разрешает нетерминалы, терминалы, классы идентификаторов и типы констант только в canonical CFG.
6. `analysis.py` вычисляет nullable, FIRST(k), FOLLOW(k) и SELECT(k), затем ищет пересечения SELECT alternatives.
7. `validation.py` объединяет диагностики разбора, разрешения, анализа и проверки точек входа и отображает synthetic diagnostics обратно на source spans. Productive direct left recursion проходит отдельную source validation; indirect и nullable-prefix left recursion остаются неподдерживаемыми.
8. `canonical_select.py` экспортирует factorized SELECT как точные symbolic token-set languages, не материализуя matcher rows или Cartesian product.
9. `decision_dag.py` строит и независимо валидирует early-commit Decision DAG с outcomes alternative, exit и syntax error.
10. `parser_ir.py` связывает листья DAG с `Dispatch`, `RepeatLoop`, `OptionalBranch`, `LeftFold` и declarative AST operations; `parser_ir_optimization.py` сохраняет доказанные path facts в executable leaves, специализирует доказуемые caller/callee decisions и удаляет только semantic-transparent недостижимые wrappers. Canonical leaves при этом path facts не содержат.
11. `canonical_bsl_decisions.py` и `canonical_bsl_codegen.py` превращают DAG непосредственно в structured BSL control flow с cached lookahead, без runtime DAG objects или таблиц решений.
12. `semantic_actions.py` и `bsl_codegen.py` обслуживают только legacy BNF path и существующие встроенные BSL-действия.
13. `value_table_codec.py` сериализует таблицы в формат, читаемый 1С через `ЗначениеИзСтрокиВнутр`.
14. `artifacts.py` сравнивает или транзакционно заменяет только три разрешённых файла.

При сравнении `ObjectModule.bsl` окончания строк LF и CRLF считаются эквивалентными; остальной текст модуля должен совпадать. ValueTable сравниваются по колонкам и мультимножеству строк, поскольку штатный сериализатор 1С сохраняет внутренние идентификаторы и порядок строк, не относящиеся к семантике парсера.

## Анализ LL(k)

Вычисление реализовано как fixed-point поверх очередей работ. Новые факты передаются как delta, поэтому уже обработанные факты не прогоняются повторно через все зависимости. FIRST/FOLLOW хранятся в упакованном виде, а SELECT — в факторизованном. Production Decision DAG потребляет symbolic representation напрямую; полное декартово разворачивание не входит в этот pipeline.

Nullable/FIRST/FOLLOW/SELECT и диагностика LLK202 — канонические контракты LL(k). `find_select_conflicts` не зависит от представления и символически пересекает канонические SELECT-наборы непосредственно в сжатом представлении. Встроенная статистика фиксирует количество work items, delta-фактов, packed rows, descriptors и случаи материализации.

`k` — произвольное конечное целое не меньше единицы. Production config сейчас
использует `k = 2`, но это не architectural maximum. Верификация проверяет
disjointness SELECT для явно выбранного `k`; она не ищет минимальный подходящий
`k` автоматически. Поэтому grammar, конфликтная при `k = 2`, может пройти при
`k = 3` или `k = 10`. При пересечении SELECT validator отклоняет grammar только
для текущего configured `k`; решение увеличить `k` остаётся явным. Grammar,
для которой не существует подходящего конечного `k`, этот deterministic
backend не поддерживает. Практическая цена большого `k` — рост analysis state
и generated predicate size.

Сгенерированный BSL намеренно использует отдельно названный legacy-артефакт matcher: он выбирает самую длинную точную строку таблицы; nullable fallback применяется только при EOF, когда нет типизированных lookahead-токенов. Эта политика dispatch не является доказательством LL(k) и изолирована от канонической валидации.

## Source EBNF и lowering

Source grammar поддерживает grouping и postfix constructs:

```text
X*   zero or more
X+   one or more
X?   optional
(...) grouping
```

Кавычки сохраняют символы как lexemes: `'*'`, `'+'`, `'?'`, `'('`, `')'` и
`'|'` не являются EBNF-операторами. Повторный postfix вроде `X*?` запрещён.

До canonical lowering validator вычисляет для каждого source production и
construct три факта: `productive`, `nullable`, `min_consumed_tokens`.
Body `*` и `+` обязан быть productive и иметь
`min_consumed_tokens >= 1`; nullable/non-consuming body отклоняется. Body `?`
не может уже быть nullable. Arbitrary BSL action внутри group/quantifier
не переходит в canonical path: structural semantics задаётся declarative
bindings.

Lowering использует reserved prefix `__parsergen_ebnf__` и стабильные tree
coordinates. Synthetic CFG создаётся только для analysis:

```text
X* -> R ::= X R | epsilon
X? -> O ::= X | epsilon
X+ -> P ::= X R
      R ::= X R | epsilon
```

Origin sidecar связывает каждую synthetic production/alternative с исходным
construct и source span. Поэтому canonical diagnostics не показывают reserved
names. Для consume/body/exit alternatives действует тот же invariant, что и
для обычной grammar:

```text
SELECT_k(alt_i) intersection SELECT_k(alt_j) = empty, i != j
```

Порядок generated `Если` никогда не разрешает пересечение.

`build_canonical_decision_source` публикует точные symbolic languages и token
sets без matcher-row или concrete Cartesian expansion. `build_decision_dag`
строит factorized решение, hash-conses одинаковые residual states и проверяет
его независимым validator. Parser IR связывает outcomes с semantic actions и
может специализировать caller/callee decision только при доказанном сохранении
action trace. Synthetic CFG остаётся analysis model и не создаёт runtime
functions. Legacy matcher artifact не участвует в production canonical path.

Production-грамматика при `lookahead = 2` не имеет canonical SELECT conflicts.
Ранее найденные пересечения устранены уточнением предметных identifier-классов:
первый сегмент поля больше не принимает `ВЫБРАТЬ`, но `ВЫБРАТЬ` остаётся
допустимым после точки и после явного `КАК`; группа ссылочного типа принимает
только token type `ID`, поэтому keyword `АВТОУПОРЯДОЧИВАНИЕ` не может начинать
`ТипСсылочногоПоля`. Порядок ветвей и увеличение `k` для этого не использовались.

## Direct productive left recursion

Source grammar поддерживает естественную прямую форму:

```text
Expr ::= Expr '+' Term | Expr '-' Term | Term
```

Classifier выделяет leading self-reference, base alternatives и consuming
suffix каждой recursive alternative. Direct LR допустима только при следующих
условиях:

- существует хотя бы одна base alternative (`LR200`);
- каждый suffix productive и гарантированно потребляет хотя бы один token
  (`LR201`);
- recursive call передаёт formal parameters без изменения (`LR202`);
- semantic alternative задаёт accumulator через declarative scalar binding,
  а base возвращает constructor node или единственное transparent value
  (`LR203`);
- arbitrary BSL actions в direct-LR production отсутствуют (`LR204`).

Indirect recursion и recursion через nullable prefix по-прежнему получают
source-located `VAL202`. Generalized parsing и автоматический поиск минимального
`k` не выполняются.

Для canonical analysis direct LR lowering создаёт только внутреннюю CFG:

```text
Expr     ::= Base ExprTail
ExprTail ::= Suffix ExprTail | epsilon
```

FIRST/FOLLOW/SELECT работают с ней без специальных изменений. SELECT base
alternatives, recursive suffixes и exit проверяются при явно настроенном
произвольном конечном `k`. Конфликт при `k = 2` означает только «не LL(2)»:
после явного перехода на `k = 10` та же grammar принимается, если её
`SELECT(10)` попарно disjoint. Порядок generated `Если` конфликт не разрешает.

Parser IR восстанавливает high-level `LeftFold`, удаляет leading self-call и
заменяет его semantic value на `FoldLeftValue`. Canonical BSL backend сначала
разбирает base, затем выполняет один `Пока` по recursive SELECT. На каждой
итерации прежний accumulator присваивается left property нового constructor,
после разбора suffix новый узел становится accumulator. Это задаёт left
associativity; precedence остаётся структурой отдельных productions, например
`Expr -> Term -> Factor`. Synthetic tail не становится runtime function, а
production не вызывает саму себя.

## Declarative AST binding

Canonical source grammar поддерживает минимальный binding DSL:

```text
@Constructor
Property = value
Property += value
Property := constant
```

`=` задаёт scalar или optional property; отсутствующий optional в
Parser IR явно присваивает `Неопределено`. `+=` добавляет каждое
фактически parsed value в collection. `:=` не потребляет input и
принимает `Истина`, `Ложь`, `Неопределено`, `Null` или dotted symbolic constant.
Терминал, identifier class и constant token могут быть semantic value.

High-level validation до lowering доказывает:

- все bindings имеют preceding constructor в той же alternative;
- scalar property присваивается не более одного раза на execution path и не
  исполняется в repeat;
- одна property не смешивает scalar и collection modes;
- scalar RHS имеет cardinality `0..1` или `1..1`;
- alternative с canonical directives не содержит legacy `Action`;
- transparent alternative имеет ровно один semantic child.

Constructor, constant assignment и binding wrapper исчезают из lowered CFG:
nullable/FIRST/FOLLOW/SELECT видят только grammar value. Oracle tests сравнивают
bound и unbound grammar при `k=1..3`. Origin sidecar сохраняет source
production, alternative, tree path и span для runtime IR.

Parser IR публикует `ConstructNode`, `BindScalar`, `AppendCollection` и
`AssignConstant`. `RepeatLoop` содержит append только в consuming
branches; exit не меняет AST. `OptionalBranch` имеет явные exit
operations. Grouped value хранит index конкретной value-producing operation,
поэтому codegen не зависит от неявного «последнего temporary».

## Canonical BSL backend

Публичный backend API:

```text
SourceGrammar + ParserIr + entrypoints
    -> generate_canonical_parser(...)
    -> CanonicalGeneratedParser
```

Он использует отдельный `templates/canonical_parser_module.bsl` и не читает
legacy matcher artifact. Каждая decision строится из validated symbolic DAG:

- alternatives обязаны иметь pairwise-disjoint SELECT; порядок
  `Если`/`ИначеЕсли` не разрешает конфликт;
- общий prefix alternatives проверяется один раз, а следующий lookahead
  читается только в неоднозначной ветке;
- token-set edges становятся exact inline predicates над заранее сохранённым
  `ТокенРешенияN`;
- `$` сравнивается с `Неопределено` и означает EOF;
- literal/class и class/class пересечения разрешаются точной set algebra, а не
  порядком generated branches;
- input вне union SELECT всегда вызывает syntax error.

High-level control flow сохраняется до codegen. `X*` и хвост `X+` становятся
`Пока`; первая итерация `X+` выполняется до loop. `X?` становится явной
consume/exit/error цепочкой. После repeat дополнительно проверяется canonical
exit SELECT, поэтому посторонний token не принимается как завершение списка.
Synthetic EBNF function names в module не попадают.

Declarative operations напрямую создают узел через
`ЭлементыМоделиЗапроса.<constructor>(ТекущийТокен)`, присваивают scalar,
добавляют repeated value в collection и записывают constant. Optional scalar
на exit получает `Неопределено`. Каждый parsed semantic value имеет отдельный
generated temporary; grouped dispatch пишет явно выбранный result в общий
temporary. Canonical backend не переносит arbitrary source actions,
`Родитель`, `ЛевыйЭлемент` или неявный `ТекущийЭлемент` contract.

### Decision path facts

Canonical Decision DAG сохраняет outcomes `alternative | exit | error` и не
знает о semantic actions. Точные facts пройденных token predicates появляются
только после outcome/action binding в optimized Parser IR. Если fact полностью
доказывает terminal matcher, `ConsumeKnownSymbol` сохраняет semantic value и
ровно один сдвиг token buffer, но не выполняет повторную runtime validation.
Facts перестают действовать после первого недоказанного consume, parser call
или другого изменения текущей позиции.

Production checkpoint содержит 6 специализированных executable paths, 11
known-symbol consumes и 0 redundant validations. После устранения трёх
вложенных decision regions итоговый DAG содержит 33 659 source states, 406 DAG
states, 89 shared states, глубину 2, 109 decision regions и 310 emitted
predicates. Generated shape: 74 functions, 2 463 LOC, 130 lookahead calls, 366
decision lines, 3 779 predicate atoms, 63 nonterminal functions и 180 call
sites. Production и reference `ObjectModule.bsl` byte-identical, SHA-256
`358A6123F91CD9068A08C76B3849FFAD69F10EB0C7B2ED90B650F87304B960E8`.

Repository-local validate, generation check и migration audit проходят без
canonical/legacy conflicts, SELECT expansions или materializations. Python
suite: 578 passed, 1 known Windows symlink privilege skip, 27 756 subtests
passed. EDT revalidation `DataProcessor.Парсер` не даёт scoped errors;
functional YAxUnit gate трёх parser-модулей: 232 passed, 0 failed, 0 errors,
0 skipped. Runtime и lexer benchmarks отложены до обновления методики и в этом
checkpoint не запускаются.

На checkpoint Phase 5 Python shape/IR/codegen tests и synthetic long-repeat
tests зелёные. Generated canonical module ещё не встроен в EDT processing и
не исполнялся платформой 1С: runtime compilation, YAxUnit/Vanessa и
differential production corpus являются gate следующих migration phases.
Production grammar, query model, BSL module, forms и legacy artifacts на этом
checkpoint не изменялись.

### Hybrid assembly для постепенной миграции

Production cutover имеет явный opt-in в конфигурации:

```toml
[migration]
canonical_productions = ["Expr", "Term"]
```

При отсутствии секции CLI вызывает прежний `generate_parser` без изменения
legacy artifacts. При непустом списке pipeline строит projection
`build_parser_ir(..., production_names=...)` и передаёт её в
`generate_hybrid_parser`.

Projection сохраняет полную lowered CFG и общий canonical analysis, но
создаёт runtime IR только для перечисленных source productions. Arbitrary BSL
actions и canonical SELECT conflicts проверяются только для выбранной family
и принадлежащих ей synthetic decisions. Полная команда `validate` при этом
остаётся строгой для всей grammar: hybrid route не подавляет `LLK202` и не
использует порядок `Если` как разрешение конфликта.

`generate_canonical_functions` отдаёт production fragments без отдельного
runtime template. Hybrid linker добавляет к их сигнатурам optional ABI
`Родитель, ЛевыйЭлемент`, чтобы существующие legacy callers могли вызвать
migrated function; сами canonical calls эти accumulator arguments не
передают. Вызов в обратную сторону использует общий контракт
`НеТерминалX(...) → semantic result`.

Synthetic productions direct-LR/EBNF остаются только в analysis. Linker
исключает их из BSL и отклоняет migration, если synthetic construct всё ещё
принадлежит legacy island. Canonical functions используют inline predicates
`ТипТокенаПросмотра`, а не `НомерВариантаПродукции`.

Legacy SELECT table строится в прежнем порядке:

```text
build_legacy_matcher_artifact
    → окончательно normalized rows
    → filter по legacy production ownership
    → ValueTable runtime artifact
```

То есть linker не вводит trie или параллельную approximation runtime
semantics. Rows migrated productions и analysis-synthetic productions в
legacy table не попадают. Canonical Parser IR по-прежнему ничего не знает об
этом artifact.

EDT read-only снимок production parser: `DataProcessors/Парсер/ObjectModule.bsl`
содержит 6 procedures, 135 functions и 3394 строки. В нём по-прежнему есть
`НомерВариантаПродукции`, параметры `Родитель`/`ЛевыйЭлемент` и recursive
`НеТерминалСписокПолейОпционально`. Cutover должен заменить этот path только
после production grammar migration и regression evidence.

## Граница canonical и legacy API

Canonical API:

- `compute_analysis`;
- `find_canonical_select_conflicts`;
- `find_select_conflicts` — canonical compatibility alias;
- `build_canonical_decision_source`;
- `build_decision_dag` и `validate_decision_dag`;
- `build_parser_ir`;
- `optimize_parser_ir`;
- `generate_canonical_parser`;
- `generate_canonical_functions`.

Hybrid migration API:

- `generate_hybrid_parser` — assembly boundary, единственный компонент,
  одновременно знающий canonical function fragments и legacy module/artifact
  plumbing.

Legacy API:

- `build_legacy_matcher_artifact`;
- `find_runtime_dispatch_conflicts`.

Compatibility-only wrappers:

- `build_select_matcher_artifact`;
- `compatible_lookahead`.

Legacy API обслуживает только временный compatibility layer: его matcher и
runtime dispatch не являются canonical LL(k) analysis. В частности,
контрпример `A → a B | a b d`, `B → ε | b c` показывает, что отсутствие
коллизий в окончательно нормализованных legacy-строках не доказывает
сохранение языка. Для legacy dispatch отдельного доказательства
language-preservation нет.

Legacy можно удалить только при одновременном выполнении всех условий:

- production config uses canonical backend;
- zero legacy islands;
- zero production references to legacy APIs;
- canonical parser regression GREEN;
- differential semantic corpus complete;
- intentional generated artifact review complete;
- runtime benchmark complete.

## Phase 5 verification checkpoint

На текущем checkout зафиксировано:

- Python: `356 passed`, `1 skipped`, `4068 subtests passed`; skip относится
  к недоступному созданию symlink без Windows privilege;
- legacy renderer/reference/artifact subset: `59 passed`, `1 skipped`,
  `42 subtests passed`;
- `validate`, `analyze` и `generate --check`: exit `1`, ровно две ожидаемые
  canonical `LLK202`;
- structural baseline: 124 productions, 281 alternatives, 63 epsilon;
- canonical SELECT: 2 conflicts, zero public SELECT expansions и zero
  Cartesian materializations during audit;
- legacy: 11273 matcher rows, `runtime_conflicts = []`;
- generated legacy baseline: 135 BSL functions, 3394 LOC;
- `artifacts.changed = []`.

Команды CLI для checkpoint должны исполнять код текущего checkout. Если ранее
установлен console script, сначала переустановить package либо запускать
`python -m parsergen` из `tools/parsergen/src`; иначе команда может загрузить
устаревшую копию из `site-packages`.

## Phase 6 verification checkpoint

Infrastructure direct productive LR проверена без изменения production
grammar/query model/generated artifacts:

- complete Python suite: `390 passed`, `1 skipped`, `4077 subtests passed`;
  skip относится к недоступному созданию symlink без Windows privilege;
- source validation: `LR200`–`LR204`, source spans, parameters, semantic
  accumulator и запрет non-consuming suffix;
- canonical lowering: stable synthetic analysis tail, origin sidecar,
  disjoint SELECT при достаточном configured finite `k`;
- Parser IR: один high-level `LeftFold`, отсутствие leading self-call и
  synthetic runtime production;
- canonical BSL shape: base dispatch, iterative recursive loop, exit/error
  check, корректный порядок constructor/left/right/accumulator;
- representative precedence module: 2 left-fold loops, 0 synthetic runtime
  functions, 0 legacy dispatch references, constructors и left bindings в
  ожидаемом порядке;
- legacy subset: `59 passed`, `1 skipped`, `42 subtests passed`;
- production audit: 124 productions, 281 alternatives, 63 epsilon, две
  ожидаемые `LLK202`, 11273 legacy matcher rows, zero runtime conflicts и
  `artifacts.changed = []`;
- EDT read-only snapshot: 6 procedures, 135 functions, 3394 lines.

Python tests доказывают lowering, IR и форму generated BSL, но не исполняют BSL
на платформе 1С. Фактические AST для `a+b`, `a+b+c`, `a-b-c`, `a+b*c`,
`(a+b)*c`, syntax errors и цепочки из 10 000 операторов остаются обязательным
YAxUnit/Vanessa gate после миграции первого production expression slice.

## Hybrid infrastructure verification checkpoint

Hybrid infrastructure проверена без opt-in production config и без изменения
production grammar/query model/generated BSL:

- complete Python suite: `404 passed`, `1 skipped`, `4082 subtests passed`;
- projected Parser IR пропускает arbitrary actions и conflicts только в
  явно оставленных legacy islands, но сохраняет strict validation выбранных
  decisions;
- canonical fragments имеют explicit optional legacy-call ABI и не содержат
  runtime template или соседние production functions;
- mixed test graph `legacy S → canonical Expr → legacy Term` собирается в один
  module с одним iterative left-fold loop;
- synthetic runtime functions отсутствуют;
- legacy SELECT ValueTable не содержит migrated/synthetic rows и получена
  фильтрацией фактического normalized matcher artifact;
- existing legacy/reference/artifact tests остаются GREEN;
- production `validate` и `generate --check` по-прежнему дают exit `1` на тех
  же двух `LLK202`; artifacts не записывались;
- repository `parsergen.toml` не содержит `[migration]`, поэтому production
  generation остаётся на прежнем legacy backend.

До первого production slice необходимо структурно устранить конфликты
`ЛогическийОператор` alternatives 2/5 и `ОперандВ` alternatives 1/2. Они не
будут разрешаться порядком ветвей или legacy fallback. После этого arithmetic
family получает RED YAxUnit expectation левой ассоциативности и только затем
может быть добавлена в `canonical_productions`.

## Production conflict-cleanup checkpoint

После hybrid infrastructure оба production conflict устранены структурно при
неизменном `lookahead = 2`:

- `ОперандВ`: `<Поле>` начинает путь через `ID_ПолеБезРазыменования`, где
  `ВЫБРАТЬ` запрещено; после точки продолжает использоваться `ID_Полный`;
- `ЛогическийОператор`: `ТипСсылочногоПоля` использует
  `ID_ГруппаТипаСсылки '.' ID_ИмяТипа`, а не два `ID_Полный`;
- canonical SELECT conflicts: `0`;
- legacy runtime conflicts: `0`;
- legacy matcher/select rows: `9078` вместо `11273`;
- identifier rows: `276` вместо `227`;
- generated BSL shape: 135 functions и 3394 LOC, без изменения;
- complete Python suite: `404 passed`, `1 skipped`, `4082 subtests passed`;
- `validate` и `generate --check`: exit `0`, artifacts current;
- BSL characterization добавлена для списка/подзапроса после `В`, keyword
  после точки и после `КАК`, запрещённого bare keyword и недопустимых alias/type
  group; её выполнение на платформе остаётся финальным YAxUnit/Vanessa gate.

## First production direct-LR checkpoint

Production config явно перевёл `АрифметическоеВыражение` и
`Слагаемое` в canonical ownership. Две continuation-productions удалены
из source grammar, а generated functions реализуют iterative left fold
без self-recursion и `НомерВариантаПродукции`.

CLI, read-only audit и reference test выбирают backend через общий
`generate_from_compilation`; full legacy matcher остаётся отдельным audit
contract. Exact metrics, tests и remaining gates зафиксированы в
[production checkpoint](../superpowers/matrices/2026-08-07-arithmetic-direct-lr-checkpoint.md).

Следующим production slice в canonical ownership добавлены `Выражение`
и `ЛогическоеСлагаемое`; helper-productions `ЛогическоеИли`/
`ЛогическоеИ` удалены, `И` и `ИЛИ` lowered в два iterative left folds.
Exact delta зафиксирован в
[logical checkpoint](../superpowers/matrices/2026-08-07-logical-direct-lr-checkpoint.md).

Первый production EBNF-срез перевёл `СписокВыражений` на
declarative repeated binding. Helper-production
`ОпциональноеПродолжениеСпискаВыражений` удалена, generated parser
использует iterative BSL loop. Exact delta зафиксирован в
[expression-list checkpoint](../superpowers/matrices/2026-08-07-expression-list-ebnf-checkpoint.md).

Тот же EBNF-паттерн затем применён к `СписокВыраженийМодели`.
Codegen дополнительно исключает temporary variables для
discarded separator values. Exact delta зафиксирован в
[model-expression-list checkpoint](../superpowers/matrices/2026-08-07-model-expression-list-ebnf-checkpoint.md).

`УнарнаяОперация` затем переведена на declarative `+` для группы
литеральных знаков. Continuation и отдельная sign-production удалены,
а generated parser хранит знаки в исходном порядке и использует один loop.
Exact delta зафиксирован в
[unary-plus checkpoint](../superpowers/matrices/2026-08-07-unary-plus-ebnf-checkpoint.md).

CASE/`ВЫБОР` затем переведён на direct optional/repeated bindings в
предметные properties родительского узла. Четыре helper-productions и
неиспользуемый constructor промежуточного массива удалены. Exact delta
зафиксирован в
[choice checkpoint](../superpowers/matrices/2026-08-07-choice-ebnf-checkpoint.md).

Вложенная production `КогдаТогда` после этого переведена на constructor и два
declarative scalar bindings без изменения query model. Exact delta зафиксирован
в [choice-alternative checkpoint](../superpowers/matrices/2026-08-07-choice-alternative-binding-checkpoint.md).

`Параметр` затем стал первым production-срезом с declarative identifier-token
binding: значение `#ID_Полный` напрямую записывается в `ПараметрЗапроса.Имя`.
Exact delta зафиксирован в
[query-parameter checkpoint](../superpowers/matrices/2026-08-07-query-parameter-binding-checkpoint.md).

`Константа` затем переведена целиком: string/number token values используют
scalar binding, а keyword alternatives — explicit constant binding, включая
BSL `Null`. Exact delta зафиксирован в
[constant checkpoint](../superpowers/matrices/2026-08-07-constant-binding-checkpoint.md).

`ТипСсылочногоПоля` затем переведён на два declarative identifier bindings,
сохранив точные классы `#ID_ГруппаТипаСсылки` и `#ID_ИмяТипа`, которые
обеспечивают бесконфликтную production grammar при `k=2`. Exact delta:
[reference-type checkpoint](../superpowers/matrices/2026-08-07-reference-type-binding-checkpoint.md).

Top-level `ЗапросУничтожения` затем переведён на constructor и declarative
table-name token binding. Exact delta зафиксирован в
[destroy-query checkpoint](../superpowers/matrices/2026-08-07-destroy-query-binding-checkpoint.md).

`ПакетЗапросов` затем переведён на collection repeat с optional завершающей
точкой с запятой. Recursive `ПродолжениеПакетаЗапросов` удалена, generated BSL
использует один loop, а query-model contract `ПакетЗапросов.Элементы` сохранён.
Exact delta зафиксирован в
[query-package checkpoint](../superpowers/matrices/2026-08-07-query-package-ebnf-checkpoint.md).

`ЗапросПакета` после этого стал transparent canonical choice: каждая из двух
disjoint alternatives возвращает единственный child без structural action.
Exact delta зафиксирован в
[package-query checkpoint](../superpowers/matrices/2026-08-07-package-query-transparent-checkpoint.md).

`Псевдоним` затем переведён на transparent canonical choice с сохранением
разных identifier classes для формы с `КАК` и без него. Exact delta:
[alias checkpoint](../superpowers/matrices/2026-08-07-alias-transparent-checkpoint.md).

`ТипСоединения` затем переведён на четыре constructor-only canonical
alternatives без изменения строковых enum-values модели. Exact delta:
[join-type checkpoint](../superpowers/matrices/2026-08-07-join-type-constructor-checkpoint.md).

`ТипКонтрольнойТочки` затем переведён на две constructor alternatives и
explicit empty result без изменения totals model. Exact delta:
[totals checkpoint-type checkpoint](../superpowers/matrices/2026-08-07-totals-checkpoint-type-checkpoint.md).

`ЭлементУпорядочивания` затем переведён на constructor, scalar binding и
EBNF optionals. `ИерархияОпционально` удалён, а absent direction
сохраняет factory-default `"Возр"` без legacy sentinel semantics. Exact
delta: [order-element checkpoint](../superpowers/matrices/2026-08-07-order-element-ebnf-checkpoint.md).

`АгрегатнаяФункция` затем переведена на terminal/scalar/constant bindings.
Technical `АргументКоличество` удалён, а absent `РАЗЛИЧНЫЕ` сохраняет
factory-default `Ложь`. Shared `РазличныеОпционально` остаётся legacy до
миграции его второго consumer. Canonical BSL conditions при этом lowered в
эквивалентное префиксное булево дерево: это уменьшает generated module без
изменения SELECT rows и не использует порядок веток для разрешения конфликтов.
Exact delta:
[aggregate-function checkpoint](../superpowers/matrices/2026-08-07-aggregate-function-binding-checkpoint.md).

`ТипПериода` после этого стал transparent canonical production над
`#ID_Полный`. Значение identifier возвращается без structural action и legacy
dispatch; query-model properties специализированных функций не менялись.
Exact delta:
[period-type checkpoint](../superpowers/matrices/2026-08-07-period-type-transparent-checkpoint.md).

Все alternatives `Функция` затем получили constructors и declarative
scalar/collection bindings. `ДАТАВРЕМЯ` lowered в loop, optional path функции
`ЗНАЧЕНИЕ` — в conditional parse; три recursive/helper productions удалены.
Exact delta:
[function checkpoint](../superpowers/matrices/2026-08-07-function-binding-checkpoint.md).

`Операнд` затем стал transparent canonical choice для шести предметных child
types. Шесть structural propagation actions удалены без изменения query model;
legacy `Поле` пока вызывается через hybrid ABI. Exact delta:
[operand checkpoint](../superpowers/matrices/2026-08-07-operand-transparent-checkpoint.md).

`Множитель` после этого стал transparent canonical choice между обычным
`Операнд` и `УнарнаяОперация`. Две structural propagation actions удалены,
а multiplicative expression path больше не использует legacy dispatch на этом
уровне. Exact delta:
[factor checkpoint](../superpowers/matrices/2026-08-08-factor-transparent-checkpoint.md).

Связанный пакет `ПриведениеТипа`/`ОписаниеТипа` затем получил constructors,
scalar bindings и EBNF optionals. Три helper-productions параметров числа и
строки удалены с сохранением defaults и формы `ЧИСЛО(10,)`. Exact delta:
[type-cast checkpoint](../superpowers/matrices/2026-08-08-type-cast-binding-checkpoint.md).

Пакет разыменований затем перевёл `Поле` на collection bindings и EBNF-loop,
удалил parameterized `ОперацияРазыменования` и оформил `.*`/`.(...)` как
предметные semantic child-productions. Query model сохранена, а generated
parser больше не рекурсирует по длине цепочки. Exact delta:
[field dereference checkpoint](../superpowers/matrices/2026-08-08-field-dereference-binding-checkpoint.md).

Следующий source-data package перевёл abstract dispatch и полностью
декларативные temporary/nested sources на canonical path. Sentinel-based
`ПсевдонимОпционально` оставлен только в legacy island до одновременной
миграции всех callers. Exact delta:
[source-data checkpoint](../superpowers/matrices/2026-08-08-source-data-binding-checkpoint.md).

Logical leaf package затем удалил propagation actions из `ОперандВ`, всех
comparison terminals и строкового/параметрического `ШаблонПодобия`, сохранив
те же model node contracts. Exact delta:
[logical leaf checkpoint](../superpowers/matrices/2026-08-08-logical-leaf-binding-checkpoint.md).

Totals control-point package затем схлопнул шесть continuation/optional
productions в одну semantic production с declarative scalar bindings и
вложенными EBNF optionals. Все девять типов периода стали action-free terminal
alternatives; generated parser больше не создаёт runtime helper functions для
границ, дополнения периодами и псевдонима. Exact delta:
[totals control-point checkpoint](../superpowers/matrices/2026-08-08-totals-control-point-binding-checkpoint.md).

## CLI

Из корня репозитория после установки пакета:

```powershell
python -m pip install "tools/parsergen[test]"
python -m pytest tools/parsergen/tests
parsergen validate --config parsergen.toml
parsergen analyze --config parsergen.toml --format json
parsergen generate --config parsergen.toml --check
python tools/parsergen/benchmarks/audit_migration.py --config parsergen.toml
```

`generate --check` — штатный read-only gate: код возврата `0` означает актуальные артефакты, `3` — найденные расхождения. Однако при канонических LLK202 валидация завершается кодом `1` до сравнения артефактов. `generate` без `--check` заменяет production-файлы и должен запускаться только в задаче, где такая регенерация явно предусмотрена.

`audit_migration.py` — read-only аудит: он семантически сравнивает три артефакта
и возвращает canonical и legacy разделы раздельно. Canonical-раздел содержит
конфликты и диагностики, legacy-раздел — состояние окончательно
нормализованных matcher rows и runtime-конфликтов.

На Windows editable-установка (`pip install -e`) из пути с кириллицей может завершиться ошибкой `setuptools` при создании `.pth` в системной кодировке. Обычная wheel-установка выше не использует этот механизм и является проверенным вариантом для текущего расположения репозитория.

## Контроль изменений

Перед регенерацией нужно:

1. пройти Python unit-тесты;
2. получить zero canonical SELECT conflicts при `lookahead = 2`;
3. успешно выполнить `validate` и `generate --check` против production-парсера;
4. сгенерировать результат в копию структуры обработки и изучить три файла;
5. после осознанной регенерации выполнить существующую YAxUnit-регрессию лексера, выражений, полного парсера и семантической обработки.
