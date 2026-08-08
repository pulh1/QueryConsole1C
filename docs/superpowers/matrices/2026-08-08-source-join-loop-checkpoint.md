# Checkpoint: iterative source and JOIN lists

Дата: 2026-08-08.

## Результат

Списки верхнеуровневых источников и JOIN переведены с recursive continuation
productions на canonical EBNF loops:

```text
<БлокИз> ::= @НовыйИсточникиЗапроса
    -= <ИсточникДанныхЗапроса>(ЭтотУзел)
    (',' -= <ИсточникДанныхЗапроса>(ЭтотУзел))*

<СписокСоединений>(Источники) ::= @НовыйСписокСоединений
    (+= <ПраваяЧастьСоединения>(Источники))*
```

Удалены technical helper-productions `СписокТаблиц` и `Соединение`.
Generated parser использует `Пока`, поэтому длина списков sources/JOIN больше
не увеличивает parser recursion depth и не создаёт runtime synthetic functions.

Добавлен минимальный declarative binding `-=`: он разбирает syntax element и
явно отбрасывает его semantic result. Binding нужен только на переходной
canonical/legacy boundary, где source-production изменяет переданный domain
registry. Он требует active constructor и не разрешает обычные unbound
repeated semantic values.

Плоская domain model `Источники.Элементы` и UUID-ссылки JOIN намеренно не
изменены в этом checkpoint. Фактический поиск выявил около 180 references в
semantic analyzer, executor, builders, generators и формах; tree/model
migration должна выполняться отдельным сквозным пакетом с обновлением всех
consumers.

## Compatibility boundary

`ИсточникДанныхЗапроса`, `ПраваяЧастьСоединения` и
`ИсточникДанныхСоединения` пока остаются явно ограниченными legacy islands:
они поддерживают существующий flat registry и UUID relation contract. В них
нет recursive list traversal, но остаются structural actions и параметр
`Источники`. Canonical SELECT-анализ и loop dispatch не используют legacy
matcher semantics.

Добавлена domain factory `НовыйСписокСоединений`, возвращающая `Массив`.
Factory inventory теперь проверяет 91 concrete constructor; вместе с базовой
helper-функцией модуль содержит 92 export-функции.

## Coverage

Добавлены тесты DSL и lowering:

- parsing `-=` внутри separator repeat;
- malformed `-=` без operand;
- запрет discard без constructor (`BIND201`);
- сохранение explicit `DISCARD` origin в lowering metadata;
- codegen вызова без temporary value;
- repository shape/behavior для source и JOIN loops;
- отсутствие runtime functions `СписокТаблиц` и `Соединение`;
- наличие generated `Пока` и сохранение flat-registry side effects.

Golden generated parser и обе value-table fixtures обновлены намеренно.

Focused DSL/repository/audit/reference suite: `136 passed`,
`150 subtests`.

Полный Python-контур: `473 passed`, `1 skipped`, `4 536 subtests`.
Единственный skip — системное ограничение Windows на создание symlink
(`WinError 1314`).

EDT targeted revalidation прошла для `DataProcessor.Парсер`,
`CommonModule.ЭлементыМоделиЗапроса` и YAxUnit factory inventory module:
новых diagnostics уровня `ERRORS` нет. Существующие code-style/doc-comment
markers сохранены как фоновый долг и этим checkpoint не изменялись.

## Metrics

| Метрика | До | После |
| --- | ---: | ---: |
| Source productions / alternatives | 78 / 181 | 77 / 178 |
| Lowered CFG productions / alternatives / epsilon | 142 / 309 / 72 | 143 / 310 / 72 |
| Semantic action blocks / statements | 64 / 77 | 64 / 74 |
| Collection / structural / other statements | 8 / 45 / 3 | 6 / 47 / 0 |
| Formal parameters / actual arguments | 9 / 26 | 10 / 26 |
| Generated BSL functions / LOC | 90 / 2 328 | 89 / 2 330 |
| SELECT artifact rows | 1 487 | 1 364 |
| Legacy analysis matcher rows | 10 010 | 10 023 |

Рост lowered CFG на одну synthetic production используется только canonical
analysis. Runtime BSL получил два loops вместо двух recursive functions.

- production lookahead: `k=2`;
- canonical conflicts: `0`;
- legacy runtime conflicts: `0`;
- validation diagnostics: `0`;
- production artifacts reproducibly generated: да.

## Remaining boundary

Следующий model-level этап для этой семьи требует согласованно заменить flat
registry/UUID representation и мигрировать все найденные consumers. До этого
`Источники` остаётся domain container, а три source/JOIN productions —
изолированная compatibility boundary, не dependency canonical codegen.
