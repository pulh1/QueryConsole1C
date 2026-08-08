# Direct productive left recursion в parsergen

## Статус и scope

Этот документ уточняет уже утверждённый Phase 6 из общего design
`2026-08-07-grammar-query-model-optimization-design.md`. Новых language-policy
решений он не вводит: поддерживается только прямая продуктивная левая
рекурсия, runtime lowering всегда выполняет iterative left fold, а indirect
left recursion остаётся unsupported.

Phase 6 реализует механизм и проверяет его на synthetic expression grammar,
повторяющей реальную precedence-иерархию. Production grammar, query model и
generated EDT parser в этой фазе не меняются: первый production expression
slice относится к следующей фазе систематической migration и требует
downstream regression gate.

## Цель

Source grammar должна принимать естественную форму:

```text
<Expr> ::=
      @НоваяБинарная Левый = <Expr> Оператор = '+' Правый = <Term>
    | @НоваяБинарная Левый = <Expr> Оператор = '-' Правый = <Term>
    | <Term>
```

Canonical analysis получает эквивалентную CFG без left recursion, Parser IR
сохраняет `LeftFold`, а generated BSL выполняет один base parse и iterative
loop. В source grammar нет `ExprContinuation` и параметра `ЛевыйЭлемент`.

## Рассмотренные подходы

### Dedicated direct-LR descriptor и `LeftFold` — выбран

High-level validation классифицирует source alternatives. Lowering создаёт
analysis-only tail production, origin sidecar сохраняет исходные alternatives,
Parser IR публикует `LeftFold`, codegen генерирует loop.

Преимущества: существующие FIRST/FOLLOW/SELECT не меняются; canonical SELECT
остаётся единственным decision contract; semantic left binding выражается
декларативно; runtime не получает synthetic recursive function.

### Переписать direct LR в Source EBNF до Parser IR — отклонён

Механически получить `β (α)*` возможно, но такое преобразование теряет
отдельную семантику leading self-reference и затрудняет source diagnostics.
Codegen также перестаёт отличать обычный repeat от AST left fold.

### Pratt/precedence parser — отклонён

Он потребовал бы отдельную precedence table и отдельный selection algorithm,
обходящий canonical SELECT. Это расширяет DSL и нарушает выбранную архитектуру.

## Классификация source grammar

Для production `A` recursive считается alternative, у которой первый grammar
value — прямой вызов `A`. Перед ним разрешены только zero-width declarative
directives. Вызов может быть:

- непосредственным `<A>` в recognition-only grammar;
- scalar binding `Left = <A>` в semantic fold.

Group, optional, repeat или другой nonterminal перед self-call не считаются
direct LR. Такие циклы остаются в lowered CFG и диагностируются как unsupported
left recursion существующим `VAL202`.

Direct self-call с parameters обязан передавать формальные параметры production
без изменения и в том же порядке. Изменение recursive arguments не имеет
эквивалентной простой left-fold semantics и отклоняется.

Классификация публикуется как immutable source descriptor и используется
одинаково validation, lowering и Parser IR. Параллельных эвристик определения
direct LR быть не должно.

## Формальные ограничения

Для direct-LR production обязательно:

- не менее одной base alternative;
- не менее одной recursive alternative;
- self-reference является первым grammar value recursive alternative;
- suffix после удаления self-reference productive;
- `min_consumed_tokens(suffix) >= 1`;
- recursive self-call arguments равны formal parameters;
- arbitrary BSL actions отсутствуют во всей direct-LR production;
- indirect или nullable-prefix LR остаётся unsupported.

Если recursive alternatives содержат declarative AST construction, каждая из
них обязана:

- иметь ровно один top-level constructor;
- связывать leading self-reference через scalar property binding;
- создавать ровно один новый result node за итерацию.

Все recursive alternatives одной production используют semantic fold либо все
являются recognition-only. Semantic fold требует, чтобы каждая base alternative
возвращала один result: собственный constructor node или ровно один transparent
semantic child. Recognition-only form может возвращать `Неопределено`; suffix
при этом распознаётся, но AST node не создаётся.

Диагностики source-level используют отдельные коды:

- `LR200` — отсутствует base alternative;
- `LR201` — recursive suffix не гарантирует consumption;
- `LR202` — recursive arguments не сохраняют formal parameters;
- `LR203` — inconsistent/missing declarative fold binding;
- `LR204` — arbitrary action в direct-LR production.

Все diagnostics указывают исходный span self-call, suffix или action. Synthetic
tail name пользователю не показывается.

## Canonical CFG lowering

Исходная production:

```text
A ::= A α1 | A α2 | β1 | β2
```

для analysis преобразуется в:

```text
A ::= β1 TailA | β2 TailA
TailA ::= α1 TailA | α2 TailA | epsilon
```

`TailA` использует reserved synthetic namespace. Public production сохраняет
имя, parameters и source order base alternatives. Tail alternatives сохраняют
source order recursive alternatives, epsilon всегда последняя.

`LoweringResult` получает отдельный `LoweredLeftRecursion` sidecar:

- source production;
- synthetic tail production;
- source indices base alternatives;
- source indices recursive alternatives;
- source spans.

`production_origins` и `alternative_origins` отображают public base rows и tail
rows обратно на исходные alternatives. FIRST/FOLLOW/SELECT работают с обычной
lowered CFG без специальных веток.

## Canonical decisions

Для каждого configured конечного `k` validation требует:

```text
SELECT_k(base_i) intersection SELECT_k(base_j) = empty
SELECT_k(suffix_i) intersection SELECT_k(suffix_j) = empty
SELECT_k(suffix_i) intersection SELECT_k(exit) = empty
```

Порядок generated `Если` не разрешает conflict. Если grammar конфликтна при
текущем `k`, Parser IR не строится; пользователь может явно увеличить `k`.
Минимальный `k` автоматически не подбирается.

## Parser IR

Добавляются два semantic элемента:

```text
FoldLeftValue
LeftFold(
    base_decision,
    base_branches,
    recursive_decision,
    recursive_branches,
    exit_alternative
)
```

Leading scalar self binding преобразуется в обычный `BindScalar`, RHS которого
равен `FoldLeftValue`; recursive nonterminal call в runtime operations не
попадает. Остальные constructor/binding operations сохраняют source order.

`LeftFold` возвращает accumulator как value-producing operation. Base branch
инициализирует его constructor node, transparent child или `Неопределено` для
recognition-only grammar. Semantic recursive branch обязан вернуть созданный
`ЭтотУзел`; recognition-only branch сохраняет прежний accumulator.

## BSL codegen

Концептуальная форма:

```text
ЛевоеЗначение = ParseBase();
Пока SELECT допускает recursive suffix Цикл
    Если выбрана semantic recursive alternative Тогда
        ЭтотУзел = Constructor(ТекущийТокен);
        ЭтотУзел.Left = ЛевоеЗначение;
        parse suffix;
        ЛевоеЗначение = ЭтотУзел;
    Иначе
        parse recognition-only suffix;
    КонецЕсли;
КонецЦикла;
Если lookahead не принадлежит exit SELECT Тогда
    syntax error;
КонецЕсли;
```

Base и recursive dispatch используют только inline canonical predicates.
Generated function не вызывает себя из loop и не генерирует function для
synthetic tail. Constructor recursive alternative вызывается ровно один раз на
итерацию.

Associativity всегда левая, потому что новый node получает accumulator
предыдущей итерации и затем сам становится accumulator. Precedence задаётся
только иерархией productions (`Expr -> Term -> Factor`), без precedence table.

## Error behavior

- input вне union base SELECT вызывает syntax error до fold;
- input вне recursive/exit union после base или iteration вызывает syntax error;
- EOF обрабатывается только через canonical `$` matcher;
- compile-time ambiguity и progress errors не проверяются runtime guards;
- validation error не меняет production artifacts.

## Tests

Python tests до production migration покрывают:

- direct LR classification и source spans;
- отсутствие base;
- empty/nullable/nonproductive suffix;
- changed recursive parameters;
- unsupported indirect and nullable-prefix LR;
- one and several recursive alternatives;
- base/suffix/exit SELECT conflicts при configured `k`;
- conflict, исчезающий при достаточном конечном `k`;
- exact CFG lowering и origin sidecar;
- `LeftFold`/`FoldLeftValue` IR;
- constructor once per iteration и explicit left binding;
- generated `Пока`, post-loop exit check и syntax-error branches;
- отсутствие self-call и synthetic tail function в generated BSL;
- structural operation order for `+`/`-` left associativity and separate
  `Expr -> Term -> Factor` precedence calls;
- absence of a same-production self-call in generated loop, which statically
  prevents proportional parser recursion for an arbitrary same-level chain.

Фактическое выполнение generated BSL и построение query-model AST проверяются
после production expression slice через YAxUnit/Vanessa. Там же выполняются
cases `a+b`, `a+b+c`, `a-b-c`, `a+b*c`, `(a+b)*c` и 10,000-operator chain.
Формы для Phase 6 не нужны.

## Legacy boundary

Direct-LR source grammar доступна только canonical lowering/Parser IR/codegen.
Legacy backend её не эмулирует и не получает synthetic tail. Production legacy
artifacts должны оставаться byte/semantic-current до отдельного cutover.

## Remaining limitations

- indirect left recursion;
- nullable-prefix left recursion;
- recursive argument transformation;
- arbitrary semantic actions;
- precedence declarations вне production hierarchy;
- production runtime integration и benchmark до следующих phases.
