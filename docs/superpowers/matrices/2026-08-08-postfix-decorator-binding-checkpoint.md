# Postfix decorator binding checkpoint

## Scope

Мигрированы одним coherent package две семьи postfix-предикатов:

- `ЛогическийМножитель` + `ЛогическийОператор` (`МЕЖДУ`, `ССЫЛКА`, `ЕСТЬ NULL`, `В`);
- `ОперандСравнения` + `ОператорПодобно` (`ПОДОБНО`).

В source DSL добавлен минимальный returned-child decorator:

```text
<Base> Операнд => <Postfix>?
```

Он разбирает `Base`, при наличии ровно одного optional `Postfix` записывает
`Postfix.Операнд = Base` и возвращает `Postfix`; при отсутствии возвращает
`Base`. Это не универсальная attribute grammar и не repeat: исходный контракт
допускает максимум одну postfix-операцию.

## Formal constraints

Валидация `BIND210` требует одновременно:

- отсутствие constructor у внешней alternative;
- binding на верхнем уровне sequence;
- ровно один semantic seed перед binding;
- отсутствие semantic values после binding;
- `SourceOptional` с ровно одним semantic result в present-ветви.

Optional dispatch строится только из canonical SELECT(k=2). Альтернативы
остаются disjoint; порядок generated `Если` не используется для разрешения
конфликтов.

## Production grammar result

- удалены `ОпциональноеНЕ` и `ОпциональноеВИерархии`;
- удалены epsilon alternatives `ЛогическийОператор` и `ОператорПодобно`;
- structural actions в четырёх migrated productions заменены constructor,
  scalar/constant binding и returned-child decorator;
- `ЛевыйЭлемент` в source grammar: `5 -> 0`;
- generated ABI-параметры пока сохранены у функций для совместимости hybrid
  runtime, но migrated bodies их не используют.

## Structural metrics

| Metric | Before | After |
| --- | ---: | ---: |
| Source productions / alternatives | 72 / 168 | 70 / 162 |
| Lowered CFG productions / alternatives / epsilon | 144 / 311 / 72 | 149 / 319 / 75 |
| Semantic action blocks / statements | 42 / 51 | 21 / 25 |
| Constructor / structural statements | 10 / 31 | 5 / 15 |
| Formal parameters / actual arguments | 10 / 26 | 10 / 26 |
| Generated BSL functions / LOC | 84 / 2 243 | 82 / 2 200 |
| SELECT artifact rows | 764 | 261 |
| Legacy matcher rows | 10 225 | 10 283 |

Рост lowered CFG — только analysis representation семи новых `?`; runtime
recursive synthetic functions для них не создаются.

## Canonical and legacy evidence

- production lookahead: `k=2`;
- canonical conflicts: `[]`;
- canonical diagnostics: `[]`;
- SELECT descriptors: `319`;
- packed FIRST/FOLLOW rows: `12 125 / 54 372`;
- legacy runtime conflicts: `[]`;
- generated artifacts are current (`artifacts.changed = []`).

Legacy matcher применяется только к оставшимся legacy islands; новый wrapper IR
и его codegen не читают matcher artifact.

## Automated verification

- focused DSL/parser IR/codegen/repository/config/audit/reference/codec suites:
  `139 passed`, `186 subtests`;
- full `tools/parsergen/tests`: `481 passed`, `1 skipped`,
  `4 552 subtests`;
- skip: прежнее ограничение Windows на создание symlink (`WinError 1314`);
- `parsergen validate --config parsergen.toml`: success;
- EDT targeted revalidation: `DataProcessor.Парсер`, success;
- EDT errors for `DataProcessor.Парсер`: none.

Интерактивные YAxUnit/Vanessa проверки отложены до финального integration gate
по согласованному порядку.
