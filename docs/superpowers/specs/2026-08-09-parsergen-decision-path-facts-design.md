# Decision path facts в optimized Parser IR

## Контекст и цель

Canonical Decision DAG уже строится из symbolic SELECT, выполняет early commit,
факторизует общие prefixes и компилируется в прямой BSL control flow. Parser IR
optimizer также умеет объединять caller decision с semantic callee decision.

Оставшийся повтор возникает после такой специализации. Разные DAG paths могут
вести к одной canonical alternative, после чего executable fragment снова
вычисляет часть уже доказанного prefix. В production
`ЛогическийМножитель` paths `МЕЖДУ` и `НЕ МЕЖДУ` оба выбирают alternative
`BETWEEN`, а её fragment повторно проверяет `МЕЖДУ` versus `НЕ` и затем снова
проверяет обязательный `МЕЖДУ` в terminal action.

Цель этапа — сохранить знания выполненного decision до executable leaf и
частично вычислить только тот начальный fragment alternative, для которого эти
знания достаточны. На одном runtime path нельзя повторно вычислять predicate,
который уже был необходим для достижения текущего DAG leaf.

## Архитектурная граница

Canonical SELECT и canonical Decision DAG не меняют semantic outcome model:

```text
CommitAlternative(N) | Exit | ImmediateError
```

Canonical leaf остаётся oracle и не получает semantic `knownFacts`. Это
сохраняет независимость formal analysis, раннее hash-consing одинаковых
outcomes и повторное использование canonical DAG.

Path facts появляются только после связывания canonical outcomes с actions:

```text
canonical SELECT
        ↓
validated canonical Decision DAG
        ↓
Parser IR outcome/action binding
        ↓
caller/callee specialization
        ↓
executable leaf + proven decision-path facts
        ↓
partial evaluation начального action region
        ↓
optimized Parser IR
        ↓
direct BSL
```

BSL codegen не выводит facts из текста условий и не выполняет peephole-анализ.
Он только печатает уже специализированные IR operations.

## Proven decision-path facts

Fact описывает точный token predicate, доказанный на конкретном пути decision,
и его исходное lookahead offset. Fact допустим только если он следует из всех
edge predicates, по которым executable leaf достижим.

Если один canonical leaf имеет несколько входящих paths с разными facts,
optimizer не объединяет их раньше времени. Он создаёт разные executable leaves
только тогда, когда различие facts меняет исполняемый начальный fragment.
Canonical outcome при этом остаётся одинаковым и сохраняется как provenance.

Facts не являются предположениями о будущем input. После token consumption,
nonterminal call либо иной операции, меняющей позицию lexer, offsets исходного
decision больше нельзя применять к новому текущему токену. Optimizer либо
поглощает доказанный prefix последовательно, либо прекращает specialization.

## Потребление уже проверенного токена

Устранение повторного predicate не означает удаление terminal action. Токен
нужно потребить ровно один раз, сохранить его semantic value, если он нужен,
и сдвинуть lexer в том же месте action trace.

Parser IR различает:

- обычный parse/consume с runtime validation;
- consume terminal, тип которого уже доказан decision path;
- consume identifier/constant только если path fact доказывает весь matcher,
  необходимый соответствующей operation.

Операция доказанного consume:

- не вызывает повторный token-type predicate;
- возвращает то же значение, что исходная `ParseSymbol`, если оно связано;
- вызывает то же продвижение token buffer;
- сохраняет source/provenance;
- не перемещается через constructor, binding или другую semantic action.

Конкретное имя Python-класса и форма generated BSL helper не являются
semantic contract. Codegen может вывести прямое чтение значения текущего
токена и `УстановитьТекущийТокен()` либо один общий примитив потребления. Helper
не проверяет тип токена и не является runtime DAG node.

## Partial evaluation semantic fragment

Для каждого executable leaf optimizer проходит начальный action region в
исходном порядке:

1. Выбирает вложенную Optional/Dispatch branch, если path facts доказывают
   ровно один её outcome.
2. Сохраняет все constructors, bindings, mutations и transformations.
3. Заменяет доказанные terminal operations на consume-without-recheck.
4. Удаляет только ставший ненужным decision control flow.
5. Останавливается перед первым decision, symbol parse или parser call, который
   не определяется имеющимися facts.
6. Присоединяет неизменённый остаток alternative и caller continuation.

Specialization не выполняет общий constant folding semantic actions и не
inline-ит дальнейшие независимые nonterminals. Она пересекает parser boundary
только там, где caller уже фактически принял decision callee.

Action order и exactly-once invariant обязательны как для successful parse,
так и до точки syntax error. После `CommitAlternative` нет rollback, выбора
другой alternative либо перехода в Optional/Repeat exit.

## Целевой production shape

Для logical operators executable outcomes должны различать как минимум:

```text
BETWEEN_DIRECT    = МЕЖДУ
BETWEEN_INVERTED  = НЕ МЕЖДУ
IN_DIRECT         = В
IN_INVERTED       = НЕ В
IS_NULL           = ЕСТЬ
REFERENCE_CHECK   = ССЫЛКА ID...
EXIT
```

`BETWEEN_DIRECT` и `BETWEEN_INVERTED` сохраняют один canonical alternative,
но получают разные специализированные начальные fragments. После
`НЕ МЕЖДУ` generated BSL не проверяет повторно `НЕ` или `МЕЖДУ`; оба токена
потребляются по одному разу, `Инверсия` устанавливается один раз, после чего
обычно разбираются операнды и обязательное `И`.

Для `ЕСТЬ` доказан только первый token. Вложенный выбор `НЕ? NULL` остаётся
обычным runtime decision, потому что он не участвовал в caller DAG leaf.

Caller binding `Операнд = left` выполняется после полного semantic fragment
выбранного operator. `EXIT` не выполняет ни одного operator action.

## Code size и sharing

Разные executable leaves могут дублировать небольшой специализированный
prefix. Большой общий suffix не дублируется без необходимости: optimizer
сохраняет join либо общий continuation, если это можно выразить без нового
runtime decision и без повторной проверки path facts.

Profitability guard ограничивает specialization начальным region. Если
устранение predicate потребовало бы существенного дублирования большого
semantic subtree, optimizer оставляет исходный безопасный fragment. Отказ от
оптимизации является локальным решением и не меняет canonical semantics.

Удаление отдельной parser function остаётся reachability-операцией после всех
specializations, а не самостоятельной целью.

## Identifier matcher predicates

Оптимизация больших `#ID_*` token sets не входит в этот этап. Иерархия
identifier classes остаётся grammar sugar и до canonical analysis раскрывается
в точные множества. Будущий отдельный этап сможет интернировать повторяющиеся
sets и выбирать по измерениям между inline predicate, shared predicate и
cached token classification.

Path-fact IR не должен терять symbolic token-set identity, чтобы доказанный
matcher predicate в будущем можно было потребить без материализации большого
`OR`. Literal↔matcher и matcher↔matcher пересечения остаются точной set algebra
без priority.

## Диагностика

До commit ошибки decision остаются `ImmediateError` с canonical expected set.
После commit непроверенная часть alternative выдаёт обычную terminal либо
nested-nonterminal syntax error.

Consume-without-recheck применяется только к доказанному prefix. Поэтому он не
может скрыть ошибку в следующем обязательном terminal: например после выбора
`BETWEEN` отсутствие `И` по-прежнему даёт конкретную ошибку ожидаемого `И`.

Если optimizer не может доказать факт или корректное потребление, исходная
runtime validation сохраняется.

## Тестовая стратегия

### Focused synthetic tests

Synthetic grammar с semantic constructor и prefixes `NOT? BETWEEN` и
`NOT? IN` проверяет:

- разные paths одной alternative получают разные executable fragments;
- известные terminals потребляются один раз без повторного predicate;
- constructor и bindings выполняются в прежнем порядке и ровно один раз;
- непроверенный suffix продолжает валидироваться;
- erroneous suffix не запускает fallback;
- EXIT не выполняет semantic actions.

### Oracle и action traces

Canonical DAG evaluator и property/oracle suite остаются неизменными. До/после
specialization сравниваются parser result, success action trace, failure trace
до точки ошибки и token-consumption trace.

### Production shape

Для `ЛогическийМножитель` фиксируется:

- нет вызова и недостижимой функции `НеТерминалЛогическийОператор`;
- `МЕЖДУ`, `В`, `ЕСТЬ` выбираются без `lookahead[1]`;
- `НЕ` читает `lookahead[1]`;
- после `НЕ МЕЖДУ` нет повторных predicates `НЕ`/`МЕЖДУ`;
- после `НЕ В` нет повторных predicates `НЕ`/`В`;
- каждый доказанный terminal потребляется один раз;
- caller binding выполняется после operator actions;
- `ЕСТЬ НЕ? NULL` сохраняет необходимый nested decision.

### Проверка и метрики

Помимо полного parsergen suite, generated/reference parity, EDT diagnostics и
YAxUnit parser modules, static audit добавляет либо вычисляет отдельную метрику
повторных predicates после executable commit. Сравниваются generated BSL LOC,
`ТипТокенаПросмотра(0/1)`, decision variables, predicate atoms и
nonterminal-call sites.

Runtime timing не запускается в этом этапе. Финальный benchmark выполняется на
согласованном corpus отдельным запуском после изменения методики.

## Рассмотренные альтернативы

### Выбрано: facts в optimized Parser IR

Сохраняет чистую canonical boundary, допускает structural proof, устраняет как
повторный branch, так и повторную terminal validation и оставляет codegen
механическим.

### Разделить direct/inverted alternatives в grammar

Упрощает конкретный generated shape, но переносит runtime-оптимизацию в
формальную grammar, дублирует semantic actions и не решает общий случай.
Подход не используется.

### Codegen peephole

Может удалить проверки по текстовой форме BSL, но не имеет надёжного доступа к
canonical proof, token-position invalidation и action trace. Подход не
используется.

## Критерий завершения

Этап завершён, когда canonical oracle не изменился, decision facts сохраняются
до executable leaves, доказанные prefix predicates не вычисляются повторно,
токены потребляются в прежнем порядке, semantic actions сохраняют exactly-once
trace, production shape-тесты проходят, а generated parser успешно проходит
Python, EDT и YAxUnit проверки.
