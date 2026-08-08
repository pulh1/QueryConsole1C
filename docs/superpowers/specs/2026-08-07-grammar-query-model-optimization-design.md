# Оптимизация grammar/query model и изоляция legacy parser dispatch

## Статус и цель

Документ задаёт архитектуру крупной миграции `tools/parsergen`, production
grammar и query model. Работа выполняется поэтапно и не является механической
заменой helper-productions.

Целевой результат:

```text
Canonical Source Grammar
        ↓
Canonical Analysis
        ↓
Canonical Parser IR
        ↓
Optimized Generated BSL Parser
```

Legacy runtime dispatch сохраняется только как изолированный migration layer,
пока production parser содержит legacy islands.

## Подтверждённое исходное состояние

### Parser generator

- Production grammar содержит 124 productions и 281 alternatives при
  `lookahead = 2`.
- В grammar есть 63 epsilon-alternatives и 263 вызова nonterminals.
- `nullable`, FIRST, FOLLOW и SELECT используют packed/factorized
  representation; FOLLOW использует delta/worklist и projection
  deduplication; public materialization выполняется лениво.
- Canonical conflict scan не материализует concrete Cartesian SELECT.
- Generated module содержит 135 BSL-функций и 3394 строки.
- Legacy matcher artifact содержит 11 273 окончательно нормализованных rows.
- Production generated artifacts семантически совпадают с текущим codegen.
- В grammar обнаружены две canonical `LLK202`:
  - `ЛогическийОператор`, alternatives 2/5, witness
    `ССЫЛКА АВТОУПОРЯДОЧИВАНИЕ`;
  - `ОперандВ`, alternatives 1/2, witness `ВЫБРАТЬ *`.
- Поэтому текущие `validate` и `generate --check` ожидаемо завершаются с кодом
  1. Это зафиксированный baseline, а не новая регрессия.

FIRST/FOLLOW/SELECT не переписываются без отдельной доказанной необходимости.

### Semantic actions

Первичная механическая классификация дала:

| Метрика | Значение |
|---|---:|
| Action blocks | 398 |
| Statements внутри actions | 431 |
| Constructor assignments | 102 |
| Collection mutations | 37 |
| Structural assignments | 245 |
| Constant assignments | 32 |
| Formal production parameters | 8 |
| Nonterminal actual arguments | 26 |
| `Родитель` usages | 43 |
| `ЛевыйЭлемент` usages | 13 |
| Имена с `Продолж...` | 12 |
| Имена с `Опционально` | 19 |
| Имена с `Список` | 8 |

Классификация служит initial baseline. Phase 0–2 должен заменить эвристические
категории воспроизводимым structural report.

### Tests и consumers

- Свежий Python baseline: 226 passed, 1 skipped, 4011 subtests passed.
- В `tools/parsergen` собрано 227 tests; один platform-dependent symlink test
  пропущен из-за отсутствия Windows privilege.
- `QueryExamples` содержит 42 `.q1c`; все они используются Vanessa-наборами,
  а curated YAxUnit parser corpus содержит 12 примеров.
- Исторические YAxUnit результаты существуют для lexer, expression parser и
  full-query parser, но не считаются свежим baseline.
- EDT показывает одну связанную информационную базу в состоянии
  `INCREMENTAL_UPDATE_REQUIRED` и не показывает готовой runtime launch
  configuration. Перед новым YAxUnit baseline требуется обнаружить или создать
  корректную incremental конфигурацию запуска.
- EDT и Serena подтвердили 43 BSL-файла и 751 прямое употребление пяти
  центральных model API.
- Factory `ЭлементыМоделиЗапроса` содержит 91 export-конструктор.
- Expression dispatcher обрабатывает 29 типов, visitor template содержит 59
  callbacks. Все три concrete visitors реализуют полный template.
- Не подтверждено, что единственным manual-only consumer является Query
  Constructor. Дополнительные gaps есть у universal report, builder, отдельных
  visitors, executor adapters и executable-view transformations.

## Декомпозиция поставки

Работа разбивается на независимо утверждаемые спецификации и планы.

### 1. Foundation: Phase 0–2

- Полный impact analysis и coverage matrix.
- Structural/analysis baseline и проектирование runtime benchmark.
- Canonical/legacy boundary audit.
- Классификация productions и semantic actions.
- Design EBNF IR, bindings, lowering, Parser IR и direct LR.
- Production grammar, query model и generated artifacts не меняются.

### 2. Test hardening: Phase 2.5

- Общие headless characterization/contract tests.
- Реализация runtime benchmark harness и снятие baseline.
- Автоматизируется всё вызываемое без форм.
- Form-only поведение фиксируется Vanessa/manual scenarios.
- Production grammar/model не меняются до GREEN этого gate.

### 3. EBNF и bindings

- Source Grammar AST для `*`, `+`, `?` и grouping.
- Declarative scalar/optional/repeated/token/constant binding.
- Lowering в canonical CFG.
- Synthetic tests и representative vertical slices.

### 4. Canonical Parser IR и loop codegen

- `Repeat` преобразуется в iterative BSL loop.
- `Optional` преобразуется в conditional parse.
- Decisions используют canonical SELECT и не используют legacy matcher.

### 5. Direct left recursion

- Direct productive LR.
- Iterative left fold.
- Expression vertical slice с associativity, precedence и long-chain tests.

### 6. Systematic migration

- Небольшие coherent vertical slices.
- Дополнительные slice-specific tests перед изменением model properties.
- Совместная миграция grammar, model и всех consumers.

### 7. Production cutover и cleanup

- Differential corpus, downstream regression и benchmark.
- Переключение production generation на canonical path.
- Удаление legacy только после доказанного отсутствия consumers.

Ни один этап не начинается при незакрытых автоматизируемых gaps предыдущего
этапа.

## Source Grammar AST, analysis CFG и Parser IR

### Source Grammar AST

High-level source model хранит естественную структуру grammar:

- sequences и alternatives;
- terminals и nonterminal calls;
- grouping;
- repeat с границами `0..*` или `1..*`;
- optional;
- constructor declaration;
- binding;
- исходную структуру direct LR.

Source origin сохраняется для каждого high-level node.

### Analysis lowering

EBNF lowering создаёт synthetic CFG только для canonical analysis.

```text
X*
→ __RepeatX ::= X __RepeatX | ε
```

Direct LR lowering для анализа:

```text
A ::= A α | β
→ A ::= β __TailA
→ __TailA ::= α __TailA | ε
```

Synthetic productions имеют устойчивую связь с исходными source nodes, но не
становятся runtime BSL-функциями и не показываются пользователю в diagnostics.

### Canonical analysis

Существующие nullable/FIRST/FOLLOW/SELECT работают только с lowered CFG.
Analysis должен предоставить codegen устойчивое read-only представление
canonical decisions, не раскрывая legacy artifact и не требуя concrete
Cartesian materialization.

### Canonical Parser IR

Parser IR строится только после успешной high-level и canonical validation.
Он содержит исполнимые конструкции:

- `Dispatch`;
- `ParseSymbol`;
- `RepeatLoop`;
- `OptionalBranch`;
- `LeftFold`;
- `ConstructNode`;
- scalar assignment;
- collection append;
- constant assignment;
- return/transparent result.

Parser IR сохраняет source origin и high-level nature constructs. Codegen
поэтому отличает analysis-only synthetic recursion от требуемого runtime loop.

## EBNF и declarative binding DSL

### Синтаксис EBNF

```text
X*   zero or more
X+   one or more
X?   optional
(...) grouping
```

### Constructor

Constructor задаётся декларативно:

```text
@НовыйОператорЗапроса
```

### Bindings

```text
Свойство = <Узел>       scalar/optional assignment
Элементы += <Узел>      append to collection
+= <Узел>               append to constructed root collection
Свойство ~= &Токен       concatenate token text to scalar property
Свойство ++= Токен      consume token and increment numeric property
Свойство = &Токен       terminal/token value
Свойство := Истина      constant value
Свойство := Типы.Все    enum/symbolic constant
:= Неопределено         transparent constant production result
```

Список:

```text
<Поля> ::=
    @НовыйВыбираемыеПоля
    += <Поле>
    (',' += <Поле>)*
```

Optional properties:

```text
<Оператор> ::=
    @НовыйОператорЗапроса
    Поля = <Поля>
    Источники = <Источники>?
    Отбор = <Выражение>?
```

Direct LR:

```text
<Expr> ::=
      @НовыйБинарный
      ЛеваяЧасть = <Expr>
      Операция = ('+' | '-')
      ПраваяЧасть = <Term>
    | <Term>
```

### Binding semantics

- Unbound separators и keywords не попадают в AST.
- Alternative без constructor и с одним semantic child прозрачна.
- Alternative с constructor явно связывает все значимые children.
- `=` присваивает одно значение либо `Неопределено` для отсутствующего
  optional.
- `+=` добавляет каждое значение в collection property.
- `+=` без property добавляет значение непосредственно в constructed root
  collection; scalar root binding не поддерживается.
- `~=` добавляет text разобранного token/identifier к scalar string
  property. Binding требует property и constructor, может исполняться
  в repeat и не смешивается с `=`/`+=` для одного property. На первой
  итерации использует factory default property; для production grammar это
  проверяется generated-parser/YAxUnit contract tests.
- `++=` потребляет terminal/token и увеличивает numeric scalar property на
  единицу. Binding разрешен в repeat, требует property и constructor и не
  смешивается с другими binding modes того же property.
- `:=` принимает только ограниченные literals или dotted symbolic constants,
  но не произвольный BSL.
- `:=` без property возвращает разрешенную константу как semantic result
  alternative. Он не требует constructor и должен быть единственным
  semantic result на своем execution path; основной production use case —
  сохранение пустых slots в declarative root collections.
- Constructor recursive alternative вызывается один раз на итерацию left fold.
- Canonical production не поддерживает arbitrary BSL escape hatch.

Фактическое наличие property в создаваемой BSL-структуре проверяется
generated-parser/YAxUnit contract tests. Отдельная дублирующая Python-схема 91
factory constructor не создаётся.

## Grammar validation

### High-level validation до lowering

Validator проверяет:

- корректность postfix operators и grouping;
- binding без active constructor;
- конфликтующие `=`, `+=` и `~=` одного property;
- property-less `:=`, смешанный с constructor или другим semantic result;
- `++=` для structural nonterminal или без active constructor;
- scalar binding, способный вернуть несколько значений;
- repeated binding без collection mode;
- неоднозначный binding group;
- неоднозначную transparent alternative;
- допустимость constant expression;
- nullable/non-productive body `*` и `+`;
- nullable optional body;
- форму direct LR;
- наличие base alternative;
- гарантированное потребление recursive suffix;
- unsupported indirect LR.

Body repetition должен быть productive и иметь
`min_consumed_tokens >= 1`. Повторный postfix quantifier вроде `X*?`
запрещён.

### Canonical validation после lowering

Для каждого decision обязателен invariant:

```text
SELECT_k(alt_i) ∩ SELECT_k(alt_j) = ∅, i != j
```

Он применяется к:

- consuming alternatives;
- epsilon/exit alternative;
- base alternatives direct LR;
- recursive suffix alternatives;
- пересекающимся terminal/identifier matcher classes.

Порядок alternatives никогда не разрешает конфликт. При пересечении создаётся
canonical diagnostic с witness, Parser IR не строится и codegen не запускается.

### Diagnostics

- Все сообщения указывают source grammar spans.
- Synthetic production names скрыты.
- Related locations связывают конфликтующие alternatives/symbols.
- Любая validation error оставляет production artifacts неизменными.

## Runtime semantics и codegen

### Repeat и optional

Lowered repeat decision содержит consuming и epsilon/exit alternatives. После
compile-time доказательства их disjointness runtime выполняет единственный
canonical dispatch:

1. consuming alternative — разобрать очередной элемент;
2. exit alternative — завершить loop;
3. ни одна alternative — syntax error.

Runtime не проверяет grammar ambiguity, nullability или progress: эти свойства
уже доказаны validator. Production progress guards не генерируются.

`+` проверяет и разбирает первую обязательную итерацию, затем использует тот же
repeat decision. `?` выполняет canonical choice между body и epsilon.

### Direct LR

Поддерживается только:

```text
A ::= A α1 | A α2 | β1 | β2
```

Ограничения:

- self-reference является первым grammar symbol recursive alternative;
- есть хотя бы одна base alternative;
- каждый suffix productive и потребляет минимум один token;
- после lowering не остаётся indirect/non-consuming LR;
- base и recursive decisions имеют pairwise-disjoint canonical SELECT.

Runtime выполняет:

```text
left = ParseBase()
while canonical decision selects recursive suffix:
    left = ParseSuffixAndConstruct(left)
return left
```

Associativity всегда левая. Precedence определяется иерархией productions,
без отдельной precedence table. Continuation AST nodes не создаются, stack
depth не растёт пропорционально одноуровневой operator chain.

### Canonical decision codegen

Factorized SELECT преобразуется в deterministic decision DAG. Codegen не
строит legacy matcher artifact и не использует longest-match, shadowing или
nullable fallback.

Маленький decision может быть встроен в production/loop. Крупный decision
может быть вынесен в generated helper. Это performance policy, не parser
semantics.

## Legacy isolation и hybrid migration

### Разделение backend

```text
Canonical production ──→ Canonical Parser IR ──→ optimized function
Legacy island        ──→ Legacy Adapter      ──→ compatibility function
                                             ↓
                                  общий generated module
```

Правила:

- Migrated production полностью принадлежит canonical backend.
- Untouched production с arbitrary actions/parameters является явно
  обозначенным legacy island.
- Canonical IR не знает о matcher artifact, shadowing или fallback.
- Linking layer знает только контракт `parse nonterminal → result`.
- Legacy artifact строится только для legacy islands.
- Production family с `Родитель`, `ЛевыйЭлемент` или accumulator parameters
  мигрируется целиком.
- Canonical production не передаёт новый AST accumulator в legacy island.
- Каждый boundary покрывается migration contract tests.
- После последнего island hybrid assembly становится чистым canonical parser.

Автоматический перенос старых actions и legacy selection в Canonical Parser IR
запрещён.

### Legacy invariants до cutover

- `build_legacy_matcher_artifact` сохраняет существующий compatibility
  contract.
- `find_runtime_dispatch_conflicts` проверяет именно окончательно
  нормализованные artifact rows.
- Approximate trie не используется как параллельная runtime semantics.
- Legacy dispatch не называется canonical LL(k) и не считается
  language-preserving.
- Production artifacts остаются воспроизводимыми до первого intentional
  migrated slice.

## Phase 2.5: headless characterization gate

Для каждой строки consumer matrix допустим ровно один статус:

- покрыто существующим автоматическим тестом;
- добавлен headless characterization/contract test;
- доказан form-only contract и составлен Vanessa/manual scenario;
- зафиксирован конкретный внешний blocker.

Косвенное покрытие недостаточно для model property, которое изменяется.

### Coverage matrix baseline

| Consumer | Текущее покрытие | Обязательный Phase 2.5 результат |
|---|---|---|
| Lexer | YAxUnit historical + transit E2E | свежий incremental baseline |
| Expression parser | 27 YAxUnit procedures, 84 historical cases | добавить затрагиваемые chains/AST observations |
| Full-query parser | 31 procedures, 97 historical cases | добавить properties будущих slices и corpus gate |
| Semantic analyzer | 12 pure-expression cases | sources, aliases, joins, fields, nested, union, parser handshake |
| Factory/dispatcher/template | factory 91 exports, dispatcher 29 types, template 59 callbacks | completeness/unknown-node contract |
| Три concrete visitors | template реализован полностью | headless behavior contracts для изменяемых nodes |
| Builder | BDD через формы | direct headless builder/mutation tests |
| Query/expression generation | BDD round-trip косвенно | headless semantic round-trip и unknown-node error |
| Executable views/filter visitor | BDD косвенно | focused transformation/delegation tests |
| Executor/code adapters | Vanessa на 42 examples | headless focused integration где возможно |
| Universal report | SKD BDD косвенно | тесты common/object-module transformations без форм |
| Query Constructor | 42 form scenarios | underlying headless contracts; формы остаются Vanessa/manual |
| Query console | UI/E2E | underlying executor/generation contracts |

### Test packages

1. Parser/model handshake: expressions, full query, reuse, recovery и
   meaningful AST observations.
2. Semantic analyzer: sources, aliases, joins, fields, dereference, grouping,
   ordering, nested query, union и parser integration.
3. Expression model: factory, dispatcher, full visitor template, concrete
   visitors и text generator dispatch.
4. Builder/generator: model mutations и semantic round-trip
   `model → text → model`.
5. Executable views/executor: filter validation, delegation, transformations,
   query/code generation и доступные integration paths.
6. Universal report/Query Constructor: все common/object-module contracts,
   вызываемые без forms.

Assertions проверяют предметные данные: число и порядок элементов, type,
alias, joins, conditions, field/source identity и generated semantics. Они не
фиксируют continuation/container topology, которую миграция удаляет.

## Query model migration

Каждая production family классифицируется как:

- предметная;
- repetition plumbing;
- optional plumbing;
- left-recursion-elimination plumbing;
- legacy compatibility.

AST node сохраняется только при собственной предметной семантике или
инварианте.

### Model property protocol

1. Найти producer и все references.
2. Получить GREEN headless characterization tests.
3. Описать новый предметный contract.
4. Изменить factory/model.
5. Перевести parser binding и всех consumers одним vertical slice.
6. Проверить visitors, builder, generators, executor и integrations.
7. Доказать отсутствие неожиданных references старого property.
8. Удалить старую structure.

Compatibility property/wrapper создаётся только при доказанном внешнем
consumer, которого нельзя мигрировать в репозитории.

## Semantic action migration

```text
ЭтотУзел = НовыйX
→ @НовыйX

ЭтотУзел.Свойство = ТекущийЭлемент
→ Свойство = <Child>

ЭтотУзел.Элементы.Добавить(...)
→ Элементы += <Child>

ЭтотУзел.Флаг = Истина
→ Флаг := Истина

ЭтотУзел = ТекущийЭлемент
→ transparent alternative

Родитель / ЛевыйЭлемент / accumulator
→ RepeatLoop или LeftFold
```

Если действие пока нельзя выразить декларативно:

- production family остаётся legacy island;
- действие попадает в semantic-action report;
- фиксируются причина и условие удаления;
- action не переносится в canonical backend.

### Предварительный порядок slices

1. Synthetic EBNF/binding fixtures.
2. List/optional families без изменения предметной model.
3. Expression lists, dereference и unary repetitions.
4. Arithmetic/logical direct LR.
5. Fields, sources и joins.
6. Query clauses, UNION и package structure.
7. Remaining legacy islands.

Фактический порядок определяется dependency graph Phase 0–2.

## Runtime performance baseline

Phase 0–2 фиксирует существующие static/analysis metrics и проектирует corpus.
Phase 2.5 реализует benchmark harness и снимает runtime baseline до первого
изменения production grammar/model.

### Corpus

- 42 `QueryExamples`;
- большой пакетный запрос;
- synthetic long field list;
- synthetic JOIN chain;
- synthetic UNION/package chain;
- long arithmetic chain;
- long logical chain;
- long dereference chain.

### Metrics

- parse wall-clock median и p95 после прогрева;
- nonterminal calls;
- dispatch calls;
- maximum recursion depth;
- constructor/action executions;
- AST node/container allocations, где это измеримо;
- generated BSL function count и LOC.

Instrumentation существует только в test/benchmark режиме. Production runtime
не получает expensive counters или progress guards.

Заранее заданного процента ускорения нет. Обязательные ожидания:

- repeat и direct LR не увеличивают stack пропорционально chain length;
- migrated families не создают recursive continuation functions;
- ухудшение wall-clock или generated size объясняется;
- performance optimization не меняет распознаваемый язык.

## Correctness gates

### Python

- полный `tools/parsergen/tests`;
- grammar parser/model/lowering tests;
- EBNF `*`, `+`, `?` tests;
- nullable/progress/invalid-binding diagnostics;
- direct-LR/indirect-LR diagnostics;
- existing nullable/FIRST/FOLLOW/SELECT oracle tests;
- canonical conflict tests;
- legacy artifact/runtime parity tests;
- Parser IR и generated code-shape tests.

### Generated BSL parser

- expression and full-query YAxUnit;
- curated и полный доступный corpus;
- syntax error и EOF;
- parser reuse/recovery;
- long repeats и operator chains;
- left associativity и precedence.

### Downstream

- semantic analyzer;
- visitors;
- builder;
- query/expression generation;
- executable views;
- executor/code generation;
- universal-report headless transformations;
- другие consumers из impact analysis.

### Manual/UI

Только доказанные form-only gaps. Query Constructor checklist включает open,
single/multiple sources, JOIN, fields, expressions, WHERE, GROUP BY, HAVING,
ORDER BY, UNION, nested query, text regeneration и execution, если workflow
это поддерживает. Список уточняется фактическим impact analysis.

## Production cutover

Cutover разрешён, когда:

1. Все production families поддерживаются canonical backend.
2. Legacy islands отсутствуют либо имеют отдельно утверждённое исключение.
3. Canonical conflicts устранены в grammar, а не скрыты runtime policy.
4. Differential corpus сравнивает предметную semantic projection, а не старую
   AST topology.
5. Python, YAxUnit и headless downstream suites GREEN.
6. Generated parser проходит syntax-error, EOF, reuse и long-chain cases.
7. Runtime benchmark выполнен на том же corpus.
8. UI-only checklist выполнен отдельно.
9. Intentional generated artifact diff просмотрен.

После cutover отдельный cleanup может удалить:

- `build_legacy_matcher_artifact`;
- `find_runtime_dispatch_conflicts`;
- legacy cycle-prefix handling;
- legacy shadowing/fallback normalization;
- compatibility wrappers.

Удаление разрешено только при нулевых production references и сохранённом
regression evidence.

## Обязательные итоговые результаты

Финальная программа миграции предоставляет:

1. Impact analysis изменённых model types/properties и consumers.
2. Test coverage matrix с автоматизированными и manual-only областями.
3. Architecture source IR, lowering, Parser IR, codegen и legacy boundary.
4. Formal constraints и diagnostics.
5. Legacy compatibility report.
6. Grammar/model migration report.
7. Semantic action before/after report.
8. Structural metrics before/after.
9. Runtime benchmark before/after.
10. Automated test evidence.
11. Manual verification checklist.
12. Remaining limitations.

## Ограничения первой версии

- Indirect left recursion не поддерживается.
- Generalized parser, GLR и packrat не вводятся.
- Универсальная attribute grammar framework не создаётся.
- Arbitrary BSL actions не поддерживаются canonical backend.
- Actual BSL factory property existence проверяется runtime contract tests, а
  не дублирующей Python schema.
- Legacy compatibility существует до production cutover и затем становится
  кандидатом на отдельное удаление.

## Финальный критерий

Grammar и query model не содержат значительного объёма структуры, существующей
только из-за ручной LL-нормализации recursive-descent parser. Repetition,
optional и direct LR lowered generator-ом в iterative runtime constructs;
structural AST building декларативен; canonical codegen не зависит от legacy
matcher semantics; все фактические headless consumers защищены автоматическими
regression tests.
