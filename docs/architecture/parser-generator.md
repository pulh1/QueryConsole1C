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
7. `validation.py` объединяет диагностики разбора, разрешения, анализа и проверки точек входа и отображает synthetic diagnostics обратно на source spans. Левая рекурсия в текущей версии диагностируется как неподдерживаемая.
8. `parser_ir.py` после успешной canonical validation строит runtime IR с `Dispatch`, `RepeatLoop`, `OptionalBranch` и declarative AST operations, не включая synthetic productions в список runtime functions.
9. `semantic_actions.py` и `bsl_codegen.py` пока обслуживают только legacy BNF path и существующие встроенные BSL-действия.
10. `value_table_codec.py` сериализует таблицы в формат, читаемый 1С через `ЗначениеИзСтрокиВнутр`.
11. `artifacts.py` сравнивает или транзакционно заменяет только три разрешённых файла.

При сравнении `ObjectModule.bsl` окончания строк LF и CRLF считаются эквивалентными; остальной текст модуля должен совпадать. ValueTable сравниваются по колонкам и мультимножеству строк, поскольку штатный сериализатор 1С сохраняет внутренние идентификаторы и порядок строк, не относящиеся к семантике парсера.

## Анализ LL(k)

Вычисление реализовано как fixed-point поверх очередей работ. Новые факты передаются как delta, поэтому уже обработанные факты не прогоняются повторно через все зависимости. FIRST/FOLLOW хранятся в упакованном виде, а SELECT — в факторизованном; полное декартово разворачивание выполняется лениво и ограничивается вызывающей стороной.

Nullable/FIRST/FOLLOW/SELECT и диагностика LLK202 — канонические контракты LL(k). `find_select_conflicts` не зависит от представления и символически пересекает канонические SELECT-наборы непосредственно в сжатом представлении. Встроенная статистика фиксирует количество work items, delta-фактов, packed rows, descriptors и случаи материализации.

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

`build_canonical_decision_artifact` публикует factorized matcher rows и token
set definitions без concrete Cartesian expansion, legacy normalization,
shadowing, cycle-prefix injection и longest-prefix fallback. `parser_ir.py`
использует только этот API. На текущем infrastructure checkpoint optimized BSL
emission из Parser IR ещё не включён; production generation остаётся на legacy
BNF path. Legacy backend явно отклоняет grammar с synthetic EBNF productions,
чтобы они случайно не превратились в recursive BSL functions.

В production-грамматике сейчас зафиксированы две канонические диагностики LLK202: для `ЛогическийОператор` между альтернативами 2 и 5 со свидетелем `ССЫЛКА/АВТОУПОРЯДОЧИВАНИЕ`, а также для `ОперандВ` между альтернативами 1 и 2 со свидетелем `ВЫБРАТЬ/*`. Исправление грамматики и сохранение языка runtime-парсера относятся к отдельной задаче.

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
принимает `Истина`, `Ложь`, `Неопределено` или dotted symbolic constant.
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
поэтому будущий codegen не зависит от неявного «последнего temporary».

Optimized BSL emission для этих operations остаётся следующим этапом.
Production grammar, query model и legacy generated artifacts на этом checkpoint не
изменялись.

## Граница canonical и legacy API

Canonical API:

- `compute_analysis`;
- `find_canonical_select_conflicts`;
- `find_select_conflicts` — canonical compatibility alias;
- `build_canonical_decision_artifact`;
- `build_parser_ir`.

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

`audit_migration.py` — read-only аудит: он семантически сравнивает три
артефакта, не останавливается на двух известных canonical `LLK202` и возвращает
canonical и legacy разделы раздельно. Canonical-раздел содержит конфликты и
диагностики, legacy-раздел — состояние окончательно нормализованных matcher
rows и runtime-конфликтов.

На Windows editable-установка (`pip install -e`) из пути с кириллицей может завершиться ошибкой `setuptools` при создании `.pth` в системной кодировке. Обычная wheel-установка выше не использует этот механизм и является проверенным вариантом для текущего расположения репозитория.

## Контроль изменений

Перед регенерацией нужно:

1. пройти Python unit-тесты;
2. для текущего baseline получить ровно две ожидаемые LLK202 при `lookahead = 2`; `validate` и `generate --check` завершаются кодом `1`, а сравнение артефактов не выполняется;
3. после отдельного исправления грамматики успешно выполнить `validate` и `generate --check` против production-парсера;
4. сгенерировать результат в копию структуры обработки и изучить три файла;
5. после осознанной регенерации выполнить существующую YAxUnit-регрессию лексера, выражений, полного парсера и семантической обработки.
