# Canonical BSL Codegen Design

## Goal

Сгенерировать из canonical Parser IR исполнимый BSL parser, в котором
EBNF repeat становится loop, optional — conditional branch, declarative AST
operations выполняются без structural actions, а runtime decisions не
зависят от legacy matcher artifact.

## Verified baseline

EDT показывает, что production `DataProcessors/Парсер/ObjectModule.bsl`
содержит 135 generated nonterminal functions и 3394 строк. Legacy
lists и expressions используют recursive continuation functions,
`НомерВариантаПродукции` и imperative `ЭтотУзел`/`ТекущийЭлемент`
plumbing. Phase 4 уже публикует disjoint canonical decisions, `RepeatLoop`,
`OptionalBranch`, `ConstructNode`, `BindScalar`, `AppendCollection` и
`AssignConstant`.

## Alternatives considered

### Inline canonical predicates — selected

Каждая factorized canonical matcher row превращается в статическое BSL
boolean condition. Rows одной alternative соединяются `Или`, matcher
positions — `И`. Identifier matcher остаётся factorized в список
token types. Это даёт прямой canonical path и не создаёт runtime
table allocations.

### Canonical runtime table

Отдельная, не legacy-normalized table была бы формально корректной,
но сохранила бы table lookup и allocations в каждом loop iteration. Это
противоречит performance hypothesis migration.

### Generated decision trie

Trie может сократить repeated comparisons на больших decisions, но
усложняет code shape до первого benchmark. Его можно добавить как
локальную optimization, не меняя Parser IR и formal semantics.

## Boundary

Новый `canonical_bsl_codegen.py` принимает `SourceGrammar`, `ParserIr` и
entrypoint mapping. Он не импортирует и не вызывает
`build_legacy_matcher_artifact`, `find_runtime_dispatch_conflicts`, legacy
normalization, shadowing и cycle-prefix logic.

Legacy `bsl_codegen.py` и `parser_module.bsl` не меняются, поэтому
checked-in production artifacts остаются byte/semantic-identical. Canonical
backend использует отдельный `canonical_parser_module.bsl` без
`ТаблицаПервыхСимволовВариантов` и `НомерВариантаПродукции`.

Result type хранит module text, identifier table и constructor names. Он
намеренно не содержит legacy select table. Production artifact integration
остаётся Phase 8 cutover, а не скрытой частью этого backend.

## Canonical decisions

Template helper `ТипТокенаПросмотра(Смещение)` безопасно читает
lookahead и возвращает `Неопределено` для EOF. Matcher `$` сравнивает
это значение с `Неопределено`; остальные matcher definitions
разворачиваются в equality checks с token types.

Для каждого decision codegen требует:

- rows ссылаются только на известные matcher definitions;
- каждая consuming/exit alternative имеет condition;
- alternatives с SELECT overlap не доходят до codegen;
- порядок `Если`/`ИначеЕсли` никогда не разрешает conflict;
- input вне union SELECT вызывает syntax error.

`k` ограничен только значением `ParserIr.lookahead`; production `k=2` не
является пределом generator.

## Control-flow lowering

`Dispatch` генерирует disjoint conditional chain с mandatory error branch.

`OptionalBranch` генерирует consuming branches, explicit exit condition и
`exit_operations`. Неизвестный lookahead не трактуется как absent
optional.

`RepeatLoop` герирует:

```text
Пока consume_union Цикл
    choose exactly one consuming branch
КонецЦикла;
Если Не exit_condition Тогда
    syntax error
КонецЕсли;
```

В loop нет recursive call к synthetic production. Source validation уже
доказала progress body, поэтому каждая iteration потребляет input.

## Semantic values

Each rendered operation returns either an explicit BSL temporary name or no value.
`ParseSymbol` returns the exact helper/nonterminal result. `ParseBranchValue`
executes all branch operations and selects its recorded `result_index`.
`DispatchValue` assigns one shared result temporary in every selected branch.

`AlternativeIr` and `BranchIr` gain an optional explicit `result_index` for
transparent paths. More than one transparent semantic child is rejected before
codegen; zero is allowed for syntax-only grammar. `ConstructNode` makes
`ЭтотУзел` the production result. Bind/append render their nested value first and then
assign/append it. Constant assignment consumes no input.

Nonterminal functions accept only their declared source parameters. Canonical calls do
not inject legacy `Родитель` or `ЛевыйЭлемент`.

## Diagnostics and safety

Codegen rejects mismatched source/IR, unknown entry productions, duplicate or reserved
generated BSL names, missing matcher definitions, incomplete decision alternatives and
ambiguous transparent results. Every non-exhaustive runtime decision has an explicit
syntax-error path, including EOF.

The canonical template keeps token-buffer and terminal helpers but removes all legacy
matcher initialization and lookup. Identifier parsing keeps the source identifier table;
this table is lexical classification data, not dispatch compatibility.

## Tests and gates

Headless Python tests cover:

- inline matcher conditions for token sets, `k > 2` and EOF;
- disjoint dispatch and malformed-input error branches;
- `*`, `+`, separator repeat and nested optional code shape;
- absence of synthetic functions and legacy matcher names;
- constructor, scalar, optional, append, token and constant rendering;
- explicit grouped/transparent result selection;
- long-list grammar producing one BSL loop rather than recursion;
- deterministic generation and BSL identifier validation;
- unchanged legacy reference artifacts and complete parsergen regression.

Execution of generated BSL through YAxUnit/Vanessa remains the final interactive gate,
as requested. Phase 5 nevertheless produces a complete module suitable for that later
runtime gate; it does not switch production artifacts.

## Deferred

- generated decision trie, unless benchmark demonstrates a need;
- direct productive left recursion and `LeftFold` (Phase 6);
- production grammar/model vertical slices (Phase 7);
- production artifact cutover (Phase 8);
- Vanessa/UI execution (final gate).
