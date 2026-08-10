# Canonical Decision DAG и плоский runtime Parser IR

## Цель

Следующий этап оптимизации `tools/parsergen` должен заменить повторяющиеся
canonical SELECT predicates единым compile-time Decision DAG и сгенерировать
прямой predictive BSL control flow. Формальная CFG остаётся подробной моделью
для lowering, FIRST/FOLLOW/SELECT и диагностики, а runtime Parser IR получает
право специализировать решения и устранять доказанно структурные границы
функций.

Целевой pipeline:

```text
source grammar
        ↓
lowered canonical CFG
        ↓
factorized canonical SELECT
        ↓
validated symbolic Decision DAG
        ↓
Parser IR с упорядоченными semantic actions
        ↓
caller/callee composition + transparent wrapper elimination
        ↓
прямой BSL control flow
```

Результат не использует legacy first-match, longest-match, priority или
nullable fallback. Пересечение canonical SELECT alternatives остаётся ошибкой
grammar. Decision DAG не выбирает победителя конфликтующих alternatives.

## Подтверждённое исходное состояние

Canonical analysis уже хранит factorized SELECT внутри `analysis.py` и умеет
точно пересекать terminal и identifier matcher sets. Однако публичный
`build_canonical_decision_artifact()` перечисляет matcher rows, а
`CanonicalDecision` в `parser_ir.py` хранит строки решения. Codegen получает
отдельный набор rows для каждой alternative и поэтому повторно строит
предикаты общего prefix.

Read-only snapshot текущей production grammar при `k = 2`:

- 66 source productions и 156 lowered productions;
- 41 186 canonical matcher rows;
- 110 identifier matcher definitions;
- 105 decision occurrences в Parser IR;
- 66 generated `НеТерминал*` functions и 77 functions всего;
- 1 954 строки generated BSL;
- 1 983 текстовых вхождения `ТипТокенаПросмотра(`;
- 223 строки решений `Если`/`ИначеЕсли`/`Пока`;
- крупнейшая condition — 6 408 символов и 170 lookahead-вызовов.

Эти значения являются стартовым snapshot, а не долговечной baseline: перед
реализацией определения метрик фиксируются в audit tool и значения измеряются
повторно.

Типичный подтверждённый повтор находится в `ЛогическийМножитель`. Caller
сначала решает, присутствует ли `ЛогическийОператор`, затем вызываемый
`ЛогическийОператор` снова проверяет почти тот же lookahead для выбора одной из
своих semantic alternatives.

Parser IR уже хранит `exit_alternative` для Optional, Repeat и LeftFold, но
current codegen не использует его: неподходящий token молча оставляется caller.
Новый этап намеренно заменяет это поведение explicit canonical `Exit` либо
`ImmediateError`.

## Рассмотренные подходы

### Выбранный: symbolic DAG и action-centric Parser IR

Factorized SELECT становится публичной immutable symbolic boundary. Из него
строится validated DAG, листья связываются с semantic action regions, а
межпроцедурная оптимизация выполняется до BSL codegen. Подход решает local
factoring, caller/callee duplication, EBNF exit semantics и structural function
elimination без материализации SELECT.

### Только local DAG

Локальный DAG внутри каждого существующего Parser IR decision проще, но не
устраняет повтор `caller: present? → callee: which alternative?` и не выполняет
цель плоского runtime. Он может быть промежуточной вертикальной стадией, но не
является конечной архитектурой.

### Codegen peephole над boolean conditions

Текстовое объединение существующих условий даёт меньший diff, но сохраняет row
materialization и затрудняет доказательство EOF/FOLLOW/matcher-overlap
семантики. Такой подход не используется.

Глобальный whole-parser automaton/CPS также не выбирается: он не требуется для
устранения подтверждённых повторов и резко увеличивает сложность provenance,
LeftFold и generated code.

## Identifier matcher classes как grammar sugar

`#ID_*` не является отдельной canonical семантикой. Resolver нормализует каждое
определение в точное immutable множество terminal token types:

```text
Grammar:   #ID_ПсевдонимРасширенный
Resolver:  TokenSet{ID, БУЛЕВО, СОЕДИНЕНИЕ, ...}
Analysis:  interned TokenSetId
DAG:       edge(TokenSetId)
```

Нормализация раскрывает только membership одного matcher-класса. Она не
материализует Cartesian product SELECT и не перечисляет все terminal words.
Одинаковые множества интернируются; union, intersection, difference и subset
выполняются над их точным представлением. Bitset по конечному terminal universe
является предпочтительным вариантом реализации, но конкретный Python API этой
спецификацией не фиксируется.

Имена `#ID_*` сохраняются как provenance и codegen hint, но не влияют на
canonical результат. Отношения классов выводятся только из множеств, а не из
имён `Полный` или `Расширенный`. Это set-inclusion/overlap lattice, а не
номинальное наследование. Например, текущие `#ID_Псевдоним` и
`#ID_ПсевдонимРасширенный` оба входят в `#ID_Полный`, но расширенный класс не
является строгим надмножеством обычного.

Ключевые слова, допустимые как identifier, являются обычными членами
`TokenSet`. Ключевые слова продолжения не задаются глобальным ручным списком:
они получаются из residual canonical SELECT/FOLLOW конкретного DAG-state.

Literal ↔ matcher и matcher ↔ matcher пересечения вычисляются одной set
algebra. Порядок predicates никогда не является скрытым приоритетом.

## Semantic outcomes и early commit

Decision DAG различает три конечных outcome:

- `CommitAlternative(N)` — осталась единственная жизнеспособная успешная
  alternative;
- `Exit` — единственным допустимым outcome является выход из
  Optional/Repeat/LeftFold;
- `ImmediateError` — для текущего symbolic prefix не осталось canonical
  continuation.

`CommitAlternative` не означает успешное завершение parse. Это необратимый
выбор alternative. Оставшиеся terminals и nonterminals проверяются её обычными
parser actions и могут выдать отложенную syntax error. После commit запрещены
rollback, переход к другой alternative и nullable/exit fallback.

Например:

```text
S ::= A B | C D
```

После `A` parser немедленно выбирает первую alternative. `A B` успешно
разбирается, а `A X` и `A EOF` доходят до terminal action и получают конкретную
ошибку `Ожидается B`. Второй lookahead не читается только ради подтверждения
уже однозначного выбора.

Формально `Viable(state)` — множество неошибочных outcomes, для которых
существует хотя бы одно canonical continuation, совместимое с уже прочитанным
prefix:

```text
Viable = ∅                    → ImmediateError
Viable = {Alternative(N)}     → CommitAlternative(N)
Viable = {Exit}               → Exit
|Viable| > 1                  → прочитать следующий lookahead
```

Будущая возможность ошибки не блокирует early commit, если успешный outcome
уже единственный. Это отличается от модели, в которой `Error` считается
конкурирующим outcome на каждом неполном prefix.

## Failure-locality semantic actions

После early commit semantic actions выбранной alternative разрешено выполнять
немедленно. По умолчанию все grammar constructors получают доверенный
failure-local контракт:

- нет внешних наблюдаемых побочных эффектов;
- разрешено создавать UUID, структуры, массивы и другие локальные значения;
- разрешена мутация только свежих объектов, принадлежащих текущему parse
  result;
- незавершённый result при syntax error отбрасывается и не выходит из parser;
- actions не записывают глобальное состояние, не вызывают callbacks и не
  изменяют переданные извне объекты.

Таким образом, «без побочных эффектов» означает не абсолютную чистоту, а
`LocalAllocate + LocalWrite` внутри owned parse result. Создание UUID допустимо
в свежем узле, который не вышел из неуспешного parse.

Доказательство распределено по этапам генерации:

1. canonical analysis доказывает точность и непересечение SELECT;
2. DAG validation доказывает соответствие symbolic languages outcomes;
3. Parser IR optimization доказывает сохранение action order, value ownership
   и количества выполнений;
4. reachability доказывает допустимость удаления runtime function;
5. codegen только отображает validated optimized IR в BSL.

Если конкретное inlining-преобразование доказать нельзя, оно локально
пропускается. Это не ошибка grammar и не останавливает генерацию. Если в
будущем появится constructor с внешним эффектом, для него потребуется явный
opt-out из доверенного контракта; форма такого API в этой спецификации не
фиксируется.

Semantic actions сохраняют исходный порядок и выполняются ровно один раз.
Оптимизация не переносит action через token consumption или другую semantic
action.

## Построение и валидация Decision DAG

Вход одного decision — factorized symbolic отображение canonical language в
`Alternative(N)` либо `Exit`. Ошибочное пространство является дополнением к
объединению этих languages и не материализуется.

Состояние builder содержит текущую глубину и residual symbolic languages всех
outcomes. Алгоритм:

1. Вычислить `Viable(state)`.
2. Для пустого множества создать `ImmediateError`.
3. Для singleton создать `CommitAlternative` либо `Exit`, не читая следующий
   lookahead.
4. Для нескольких outcomes лениво разбить релевантную часть terminal universe
   на непересекающиеся классы по одинаковому вектору symbolic derivatives.
5. Для каждого класса вычислить residual successor и продолжить построение.
6. Направить complement, не имеющий viable continuation, в `ImmediateError`.
7. Hash-cons одинаковые состояния по canonical residual languages, outcome
   mapping и оставшейся глубине.
8. Сгруппировать labels с одинаковым successor в один edge predicate.

Если после глубины `k` на одном пути остаются разные outcomes, builder
обнаружил canonical conflict либо нарушение внутреннего invariant. Grammar
validation должна отбраковать конфликт до Parser IR; внутреннее расхождение
является ошибкой генератора, а не поводом применить branch priority.

Алгоритм строится непосредственно поверх существующего factor graph либо
другого эквивалентного exact symbolic representation. Публичная materialization
41 000+ matcher rows не является входом Parser IR.

### EOF и короткие prefixes

DAG реализует ровно:

```text
SELECT_k(A → α) = FIRST_k(α FOLLOW_k(A))
```

Поэтому:

- nullable alternative продолжается через FOLLOW owner;
- короткий complete FIRST-prefix продолжается через projected FOLLOW;
- prefix длины `k` считается saturated и дальше не продолжается;
- EOF является отдельным terminal element;
- после EOF successor не читает более глубокий lookahead;
- пересечение outcomes на одном полном canonical word остаётся конфликтом.

## Граница CFG и runtime Parser IR

Canonical CFG сохраняет все analysis productions, включая synthetic lowering
nodes. Runtime Parser IR строится как control-flow regions:

```text
Decision region → Action region → continuation/join
```

Лист DAG связан с упорядоченным action region, а не обязательно с отдельной
parser function. Общий continuation нескольких alternatives остаётся одним
join-блоком и не дублируется.

Action region сохраняет constructors, terminal/nonterminal parse operations,
bindings, mutations, transformations, source/provenance и return semantics.
Конкретные Python-классы или публичный API Parser IR будут выбраны в
implementation plan после проверки минимального вертикального прототипа.

## Caller/callee decision composition

Если outcome caller непосредственно означает вызов callee decision, caller
present-language пересекается с alternative languages callee. Вместо:

```text
caller: body | exit
body:   callee alternative 1 | callee alternative 2
```

Parser IR получает:

```text
callee alternative 1 | callee alternative 2 | exit
```

Composition работает символически и учитывает call-site continuation. Поэтому
глобальный FOLLOW callee может быть сужен контекстом конкретного caller без
изменения canonical CFG.

Прямое composition допустимо, если между решениями нет token consumption или
caller-specific semantic action. Semantic callee разрешено специализировать:
его selected action region переносится в соответствующий leaf, а caller
continuation присоединяется после него. Common continuation остаётся join и
выполняется один раз.

Это устраняет двойной выбор
`ЛогическийМножитель → ЛогическийОператор`, сохраняя constructors и bindings
конкретных логических операторов. Callee function остаётся, если имеет другие
неспециализированные либо внешние вызовы.

## Semantic-transparent intermediate nodes

Decision specialization semantic callee и полное удаление wrapper — разные
операции. Wrapper можно удалить только при структурном доказательстве:

- он не является public entrypoint;
- не входит в recursive SCC и не является LeftFold accumulator boundary;
- не содержит собственных constructors, bindings, mutations, constants,
  wrappers или других value transformations;
- каждая успешная path возвращает child value без преобразования либо все paths
  единообразно syntax-only;
- token consumption и child calls сохраняются в прежнем порядке;
- argument evaluation не дублируется;
- обязательная diagnostic/source boundary отсутствует либо provenance точно
  переносится на surviving action/decision;
- результат, exception behavior и observable action trace остаются
  эквивалентными.

Критерий применяется к Parser IR, а не к имени production или внешней форме
grammar. После всех substitutions отдельный reachability pass удаляет только
недостижимые runtime functions.

## Optional, Repeat и LeftFold

Эти конструкции не получают отдельной decision semantics.

Optional выполняет единый DAG с outcomes `body | exit | error`.

Repeat генерирует один цикл:

```bsl
Пока Истина Цикл
    // canonical DAG: iteration | exit | error
КонецЦикла;
```

`CommitIteration` выполняет body и переходит к следующей итерации, `Exit`
выполняет `Прервать`, `ImmediateError` выдаёт syntax error. Текущее поведение
«не body — всегда выйти и оставить ошибку caller» не сохраняется.

LeftFold сначала разбирает base и создаёт accumulator. На каждой итерации тот
же DAG выбирает конкретный suffix, exit либо error. Constructor suffix,
bindings, parse правой части и замена accumulator выполняются в исходном
порядке. Actions нельзя hoist/sink через границу итерации.

Для `+` обязательная первая итерация разбирается как body, после чего остаток
использует тот же repeat DAG.

## Прямой BSL codegen

DAG является только compile-time IR. Generated BSL не содержит runtime
`DecisionNode`, transition tables, state-machine interpreter или цепочку helper
functions для каждого DAG-node.

Каждый decision region кэширует только реально необходимый lookahead:

```bsl
Токен0 = ТипТокенаПросмотра(0);

Если ... Тогда
    // early commit
ИначеЕсли ... Тогда
    Токен1 = ТипТокенаПросмотра(1);
    // deeper decision
КонецЕсли;
```

На одном выполненном decision path каждый offset читается максимум один раз.
Более глубокий token вычисляется только в неоднозначной ветви. После token
consumption или вызова parser region lookahead cache инвалидируется.

Одинаковые successors одного состояния объединяются общим predicate. Shared
DAG-state переиспользуется в compile-time IR. Если structured BSL не может
выразить cross-branch join без runtime machine, codegen может продублировать
небольшой subtree; это не должно повторять predicates на одном runtime path.
Выделение runtime helper допустимо только как редкая code-size оптимизация, а не
как функция на каждый decision node, и должно подтверждаться метриками.

### Emission TokenSet predicates

Форма BSL predicate отделена от semantic DAG:

- маленькие sets выводятся inline comparisons;
- большие или многократно используемые sets могут получать reusable predicate,
  принимающий уже прочитанный token type;
- predicate не вызывает `ТипТокенаПросмотра` самостоятельно;
- exact equality с named `#ID_*` позволяет использовать provenance hint;
- unions/differences могут выводиться компактной комбинацией named sets и
  literals;
- emitted predicate обязан быть точно эквивалентен исходному `TokenSet`.

Порог inline/reuse не является semantic contract и выбирается по BSL LOC,
condition complexity и runtime benchmark. Он не может менять outcome либо
создавать приоритет классов.

## Ошибки и диагностика

Ошибки разделяются на три места:

- `ImmediateError` — текущий decision prefix не имеет viable continuation;
- deferred terminal error после commit — ожидается конкретный terminal либо
  EOF выбранной alternative;
- nested nonterminal error — её собственный DAG или terminal action отвергли
  input.

`ImmediateError` сообщает union допустимых outgoing TokenSet текущего state в
компактной и детерминированной форме. Source/provenance исходной production и
alternative сохраняется в IR даже при удалении runtime function boundary.

Невозможность применить оптимизацию не является ошибкой. Canonical conflict,
несогласованность symbolic DAG с SELECT либо нарушение action trace являются
ошибкой validation/generation.

## Oracle и тестовая стратегия

### Canonical oracle

Для каждого canonical word DAG обязан выбрать ровно ожидаемую alternative или
exit. Для слова вне canonical SELECT допустимы два пути:

- DAG сразу возвращает `ImmediateError`;
- DAG делает early commit единственной viable alternative, после чего полный
  parser завершает её syntax error.

Запрещено выбирать другую alternative или `Exit`.

### Property tests

Для малых случайных grammar/decision sets при `k = 1..3` materialized canonical
SELECT используется только как независимый test oracle. Конечный token universe
включает EOF, literal/matcher и matcher/matcher overlaps, nullable alternatives,
короткие complete prefixes и saturated prefixes.

Для больших production equivalence проверяется symbolically без
materialization.

### Action trace

Тестовый evaluator Parser IR записывает identity и порядок semantic operations.
На успешном parse до/после оптимизации trace, результат и количество выполнений
совпадают. Отдельно проверяются constructors, scalar/collection bindings,
caller continuation и LeftFold accumulator updates. На ошибочном parse owned
result не выходит наружу, rollback к другому outcome отсутствует.

### Generated shape

Golden/shape tests закрепляют:

- общий prefix проверяется один раз;
- `lookahead[1]` вложен только в неоднозначную ветвь;
- `ЛогическийМножитель → ЛогическийОператор` имеет одно runtime decision;
- Optional/Repeat/LeftFold содержат explicit exit и error paths;
- semantic-transparent wrapper исчезает, semantic boundary без доказательства
  сохраняется;
- generated BSL не содержит runtime DAG interpreter;
- TokenSet predicate не читает lookahead самостоятельно.

## Метрики и performance baseline

Сравнение выполняется в трёх точках:

```text
remote old_parser
current canonical parser before Decision DAG
optimized canonical Decision DAG parser
```

Это отделяет эффект текущего этапа от общей разницы legacy и migrated parser.
Получение `old_parser` baseline описано отдельно в
[baseline design](2026-08-08-legacy-parser-lexer-benchmark-baseline-design.md).

Статический audit фиксирует:

- число occurrences `ТипТокенаПросмотра`;
- decision sites и predicate atoms;
- `НеТерминал*` и общее число generated functions;
- parser-function call sites;
- generated BSL LOC;
- максимальную длину, число atoms и nesting depth condition;
- число DAG states до/после hash-consing и число emitted decision regions.

Instrumented runtime отдельно фиксирует:

- фактические lookahead calls;
- parser-function calls;
- максимальную parser stack depth;
- число посещённых decision states/regions.

Timing выполняется на неинструментированном artifact: median/p95 на
существующем corpus, включая expression-heavy, длинные списки полей, JOIN,
UNION, arithmetic, logical и dereference scenarios. Instrumentation overhead не
смешивается с timing. Наблюдаемая регрессия порядка 5% и выше подтверждается
повторными сериями перед выводом.

Hard gates:

- canonical semantics и action-trace equivalence;
- отсутствие legacy conflict resolution в canonical path;
- один decision в целевом logical caller/callee pattern;
- отсутствие повторного lookahead одного offset на runtime decision path;
- отсутствие runtime DAG interpreter;
- успешные validation, generation checks и test suite.

Performance и structural metrics публикуются before/after. Если оптимизация
увеличивает code size без runtime выигрыша, её profitability policy
корректируется без изменения semantic contracts.

## Поэтапное внедрение

Работа выполняется вертикальными стадиями, после каждой из которых generator и
parser остаются проверяемыми:

1. TokenSet normalization и независимый pure-Python DAG evaluator с oracle
   tests.
2. Local DAG Parser IR/codegen без caller/callee composition.
3. Explicit canonical exit/error для Optional, Repeat и LeftFold.
4. Caller/callee decision composition и logical-operator target case.
5. Structural transparency proof, wrapper elimination и reachability cleanup.
6. Полный static audit, instrumented runtime metrics и uninstrumented timing.

Конкретное разбиение Python-модулей, имена классов и публичные API выбираются в
implementation plan после минимального vertical prototype. Semantic contracts
этой спецификации от этого выбора не зависят.

## Границы этапа

- Не менять configured production lookahead `k = 2`.
- Не материализовывать SELECT ради DAG.
- Не менять canonical conflict semantics.
- Не переносить legacy priority/longest-match/nullable fallback в DAG.
- Не вводить контекстно-зависимые lexer tokens для `#ID_*`.
- Не строить runtime DAG interpreter или global whole-parser automaton.
- Не удалять semantic functions по имени либо форме grammar production.
- Не переносить semantic actions через token consumption.
- Не совмещать instrumented runtime с timing benchmark.
- Не удалять временные `old_parser` baseline objects до получения и фиксации
  baseline; их удаление перед MR остаётся отдельным шагом baseline-плана.

## Критерий завершения

Этап завершён, когда optimized generated parser сохраняет canonical language и
semantic results, читает минимально необходимый lookahead для выбора outcome,
не повторяет общий prefix либо caller/callee decision на одном runtime path,
использует explicit canonical loop exits, удаляет только доказанно transparent
runtime nodes и генерирует обычный прямой BSL control flow. Все изменения
подтверждены oracle/property/action-trace tests и опубликованными трёхточечными
structural/runtime performance metrics.
