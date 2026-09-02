# Разделение синтаксической грамматики и semantic profile в parsergen

## 1. Контекст и цель

Сейчас declarative constructors и bindings находятся непосредственно в source
grammar. Это удобно для одного AST, но заставляет дублировать грамматику, если
один принимаемый язык должен строить несколько семантических представлений.

Цель — разрешить одной syntax grammar иметь несколько semantic profile без
копирования RHS и без изменения существующего combined-режима. Первый внешний
потребитель — Onec Interactive Runtime: полный BSL AST остаётся для notebook
cells, а Worker reload получает компактную модель из той же BSL-грамматики.

## 2. Обязательная обратная совместимость

Существующий путь остаётся самостоятельным и неизменным:

```text
parse_grammar
  -> parse_source_grammar
  -> lower_source_grammar
  -> resolve_grammar / compute_analysis
  -> build_parser_ir
  -> generate_python_semantic_parser
```

Не меняются:

- синтаксис combined grammar: `@Node`, `Field =`, `+=`, `*=`, `~=`, `++=`,
  `=>`, `+=>`, `-=`, `:=` и inline actions;
- сигнатуры и поведение существующих функций;
- поля, equality и constructor contract существующих `SourceGrammar`,
  `LoweringResult` и `ParserIr`;
- диагностические коды и golden `module_text` legacy-пути.

Новые возможности добавляются новыми моделями и функциями. Combined grammar не
конвертируется через новый публичный API. Изменение версии и package hash
parsergen допустимо; изменение legacy generated output — нет.

## 3. Syntax grammar с именованными anchors

Syntax grammar содержит только терминалы, identifiers, nonterminal calls,
groups, EBNF quantifiers и параметры. Semantic constructors, bindings и inline
actions в separated mode запрещены.

Элемент, на который должен ссылаться semantic profile, получает anchor:

```text
#Имя ::= ID

<Присваивание> ::=
    [simple] target: #Имя '=' value: <Выражение>

<ЦепочкаДоступа> ::=
    [direct] root: #Имя arguments: <АргументыВызова>?
             postfix: <ПостфиксДоступа>*
  | [parenthesized] root: '(' <Выражение> ')'
                    postfix: <ПостфиксДоступа>*
```

Контракт authoring:

- `[name]` в начале alternative задаёт её стабильное имя;
- `name:` непосредственно перед primary задаёт anchor всей primary вместе с
  postfix quantifier;
- имена alternatives уникальны во всём production, включая alternatives
  вложенных groups;
- имена anchors уникальны внутри именованной alternative;
- единственная верхнеуровневая alternative может не иметь имени и адресуется
  через production;
- alternative внутри group, на которую ссылается профиль, обязана иметь имя;
- annotations не входят в принимаемый язык и после их удаления остаётся обычная
  syntax-only `SourceGrammar`;
- числовой путь элемента остаётся внутренней деталью модели и никогда не
  записывается в semantic-файл.

Parser annotations сохраняют исходные `SourceSpan`. Для передачи текста в
существующий source parser annotations маскируются пробелами той же длины без
изменения переводов строк. Поэтому offsets остальных grammar items не меняются.

## 4. Action-only semantic profile

Semantic profile не содержит RHS. Он адресует production/alternative и anchors:

```text
profile worker

<Присваивание>[simple] {
    @Assignment
    Target = target
    Value = value
    IsSimple := Истина
}

<ЦепочкаДоступа>[direct] {
    @AccessChain
    Root = root
    Arguments = arguments
    Postfix += postfix
}
```

В блоке поддерживается существующий declarative binding vocabulary:

- `@Node` — constructor в начале alternative;
- `Field = anchor`, `Field += anchor`, `Field *= anchor`, `Field ~= anchor`,
  `Field ++= anchor`, `Field => anchor`, `Field +=> anchor`;
- `+= anchor` и `-= anchor` для property-less collection/discard binding;
- `Field := Constant` и `:= Constant`; constants выполняются после syntax items
  в порядке строк профиля.

Anchor binding выполняется в позиции соответствующего syntax item. Constructor
вставляется перед первым syntax item, constant bindings — после последнего.
Такой порядок однозначен, не требует повторять RHS и позволяет восстановить
обычную combined `SourceGrammar` для существующего lowering.

Separated profile первой версии не поддерживает произвольные inline actions
`{ ... }`. Это не ограничивает combined mode. Если compact Worker model нельзя
выразить declarative bindings, новая операция проектируется отдельно как общая
операция parsergen, а не как callback конкретного потребителя.

## 5. Новые модели и API

Новые immutable frozen/slotted модели находятся отдельно от `source_model.py`:

```python
@dataclass(frozen=True, slots=True)
class SyntaxItemAddress:
    production: str
    alternative: str | None
    path: tuple[int, ...]

@dataclass(frozen=True, slots=True)
class SyntaxAnchor:
    name: str
    address: SyntaxItemAddress
    span: SourceSpan

@dataclass(frozen=True, slots=True)
class SyntaxGrammar:
    source_grammar: SourceGrammar
    alternatives: tuple[SyntaxAlternativeName, ...]
    anchors: tuple[SyntaxAnchor, ...]
    source_sha256: str
    path: str

@dataclass(frozen=True, slots=True)
class SemanticProfile:
    name: str
    alternatives: tuple[SemanticAlternative, ...]
    source_sha256: str
    path: str

@dataclass(frozen=True, slots=True)
class SemanticBindingResult:
    source_grammar: SourceGrammar | None
    diagnostics: tuple[Diagnostic, ...]
```

Публичные additive функции:

```python
parse_syntax_grammar(text: str, path: str = "<memory>") -> SyntaxParseResult
parse_semantic_profile(text: str, path: str = "<memory>") -> SemanticProfileParseResult
bind_semantic_profile(
    syntax: SyntaxGrammar,
    profile: SemanticProfile,
) -> SemanticBindingResult
```

Каждый `*Result` содержит nullable value и tuple diagnostics, как существующие
parse results. `SemanticBindingResult.source_grammar` — обычный
`SourceGrammar`, который передаётся без специального пути в
`lower_source_grammar`, `resolve_grammar`, `compute_analysis`,
`build_parser_ir` и существующие codegen.

Новый путь выглядит так:

```text
parse_syntax_grammar + parse_semantic_profile
  -> bind_semantic_profile
  -> обычный SourceGrammar
  -> существующие lowering / resolution / analysis / Parser IR / codegen
```

Таким образом semantic nodes входят в lowering до построения decision DAG,
`result_index`, left-fold, transparency и path specialization. Overlay поверх
готового Parser IR или codegen запрещён.

## 6. Binding и validation

Binder строит новый immutable `SourceGrammar`, структурно разделяя исходные
syntax items и добавленные semantic items. Исходная `SyntaxGrammar` не меняется.

Validation fail-closed проверяет до lowering:

- неизвестные и дублирующиеся production/alternative/anchor;
- ссылку без имени на production с несколькими alternatives;
- wrong-scope anchor;
- повторное потребление одного anchor несовместимыми bindings;
- constructor/constant/binding contract существующего declarative DSL.

Profile diagnostics используют span semantic-файла как primary location и
syntax span как `RelatedLocation`. Ошибки объявления duplicate anchors и
alternatives делают наоборот. Выделяются стабильные диапазоны кодов:

- `SGP100`–`SGP199` — syntax annotation parsing/validation;
- `SPP100`–`SPP199` — semantic profile parsing;
- `SPB200`–`SPB299` — cross-file binding/validation.

После успешного cross-file binding обычные `validate_source_grammar` и
`validate_bindings` остаются окончательным oracle declarative semantics.

## 7. Identity и детерминизм

`SyntaxGrammar.source_sha256` и `SemanticProfile.source_sha256` считаются
раздельно по точным UTF-8 bytes перед parsing. Path не входит в hash.

Parser artifact identity внешнего потребителя включает:

```text
syntax source SHA-256
+ semantic profile SHA-256
+ parsergen package identity
+ codegen options / entrypoints
```

Одинаковые bytes и options дают одинаковый bound grammar, Parser IR и generated
`module_text`. Порядок словарей, filesystem timestamps и абсолютные paths на
результат не влияют.

## 8. Проверки

Обязательные gates:

- snapshot public API, dataclass fields/equality и golden `module_text`
  combined-пути до и после изменения;
- parser tests для labels/anchors во вложенных groups, EBNF и direct LR;
- profile parser tests для всех declarative operators и malformed input;
- точные primary/related spans для missing, duplicate и wrong-scope cases;
- эквивалентная combined grammar и syntax+profile дают одинаковый semantic
  Parser IR после нормализации cross-file provenance и одинаковое выполнение
  generated Python parser;
- syntax-only и разные profiles имеют одинаковые grammar symbols,
  FIRST/FOLLOW/SELECT и canonical decision outcomes до semantic specialization;
- различия финального Parser IR между profiles объясняются только выбранными
  semantic operations и зависимой от них transparency/path optimization;
- semantic nodes каждого профиля участвуют в Parser IR optimization;
- полный `tools/parsergen/tests`, `compileall`, repository grammar validation и
  `parsergen generate --check` проходят без изменения production BSL artifacts.

## 9. Граница поставки

QueryConsole1C поставляет только универсальные syntax/profile models, parsers,
binder, diagnostics и документацию. BSL grammar, Worker semantic profile и
generated Worker parser принадлежат Onec Interactive Runtime.

Production-реализация начинается после минимального spike, который доказывает:

1. profile binding создаёт обычный `SourceGrammar`;
2. существующие lowering и Parser IR не требуют consumer-specific ветки;
3. anchors переживают groups, EBNF и direct-left-recursion lowering;
4. legacy golden output остаётся байтово неизменным.
