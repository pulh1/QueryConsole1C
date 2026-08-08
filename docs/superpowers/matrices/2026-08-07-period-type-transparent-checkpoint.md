# Production checkpoint: transparent period type

`ТипПериода` переведён с imperative propagation на transparent canonical
production:

```text
<ТипПериода> ::= #ID_Полный
```

Identifier является единственным value-bearing symbol и автоматически
становится результатом production. Query model и consumers свойства
`ТипПериода` не изменены.

## Contract and coverage

- Generated function вызывает `Идентификатор("ID_Полный")` и возвращает его
  значение без `ТекущийЭлемент` и legacy dispatch.
- Canonical SELECT остаётся disjoint при production `k=2`; порядок branches
  не используется для разрешения конфликтов.
- Существующий headless YAxUnit test `СпециализированнаяФункцияРазбирается`
  проверяет фактические значения `МЕСЯЦ` и `ДЕНЬ` в свойствах
  `ФункцияНачалоПериода`, `ФункцияКонецПериода`, `ФункцияДобавитьКДате` и
  `ФункцияРазностьДат`.
- Новый Python codegen test фиксирует transparent result и отсутствие
  `НомерВариантаПродукции`.
- Интерактивный запуск YAxUnit/Vanessa остаётся финальным integration gate по
  договорённости.

## Structural delta

| Metric | Before slice | After slice |
| --- | ---: | ---: |
| Source productions / alternatives | 109 / 254 | 109 / 254 |
| Lowered CFG productions / alternatives / epsilon | 127 / 286 / 65 | 127 / 286 / 65 |
| Semantic action blocks / statements | 280 / 301 | 279 / 300 |
| Structural statements | 190 | 189 |
| Generated BSL functions / LOC | 121 / 3 056 | 121 / 3 051 |
| Production SELECT rows | 5 973 | 5 895 |
| Full legacy matcher rows | 9 083 | 9 083 |

Остальные action categories, parameters, constructor names и identifier rows
не изменились. Canonical FIRST/FOLLOW/SELECT stats также не изменились.

## Focused verification

- RED: canonical ownership отвергло старый action с
  `arbitrary source actions require declarative bindings`.
- GREEN: focused transparent test — `1 passed`.
- Repository/config/audit/codec/reference contour — `62 passed`,
  `71 subtests passed`.
- Full `tools/parsergen/tests` — `430 passed`, `1 skipped`,
  `4 447 subtests passed`; skip — известное ограничение Windows на symlink.
- `parsergen validate` — exit `0`, только две существующие `VAL102` warnings;
  `generate --check` — artifacts current.
- Canonical conflicts: `0`; legacy runtime conflicts: `0`; lookahead: `2`.
- Migration audit: changed artifacts `0`.
- EDT revalidation `DataProcessor.Парсер`: прежние `7` baseline diagnostics,
  новых syntax diagnostics нет.

## Next dependency

Production является входом четырёх date-period alternatives в `Функция`.
Следующий coherent slice может declaratively bind их `Дата`, `ТипПериода` и
`Сдвиг`, не возвращая structural propagation в grammar.
