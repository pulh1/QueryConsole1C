# Production checkpoint: declarative aggregate functions

`АгрегатнаяФункция` переведена в canonical ownership целиком. Четыре
обычные aggregate alternatives связывают имя функции с фактически разобранным
terminal value, а аргумент — с `Выражение`:

```text
@НовыйАгрегатнаяФункция
ИмяФункции = СУММА
'('
Аргумент = <Выражение>
')'
```

`КОЛИЧЕСТВО` использует отдельный существующий constructor, optional constant
binding для `РАЗЛИЧНЫЕ` и scalar choice для звёздочки или выражения:

```text
@НовыйАгрегатнаяФункцияКоличество
КОЛИЧЕСТВО
'('
(РАЗЛИЧНЫЕ Различные := Истина)?
Аргумент = ('*' | <Выражение>)
')'
```

## Semantic boundary

- Query model и обе factory functions не изменены.
- Отсутствующая optional-ветка не присваивает `Различные = Неопределено` и
  сохраняет factory-default `Ложь`.
- Technical production `АргументКоличество` удалена; choice принадлежит
  canonical Parser IR и не создаёт отдельную runtime function.
- `РазличныеОпционально` намеренно сохранена: фактический reference из legacy
  модификаторов `ВЫБРАТЬ` находится вне этого coherent slice.
- Canonical aggregate dispatch использует только disjoint SELECT при `k=2`;
  порядок generated `Если` не участвует в разрешении конфликтов.

## Generated condition factoring

Первичная генерация optional `РАЗЛИЧНЫЕ` буквально повторяла общий первый
matcher для каждой допустимой второй позиции LL(2). Формальная SELECT-модель
при этом была корректна, но generated module вырос до `2 075 689` байт.

`CanonicalConditionRenderer` теперь представляет объединение canonical rows
как префиксное булево дерево: общий matcher вычисляется один раз, а disjoint
suffixes объединяются внутри него. Это локальная оптимизация rendering после
canonical validation; она не вводит приоритет веток и не меняет Parser IR,
SELECT rows или legacy artifacts.

| Generated module shape | Bytes |
| --- | ---: |
| Before slice (`HEAD`) | 1 860 139 |
| Aggregate slice without factoring | 2 075 689 |
| Aggregate slice with factoring | 680 743 |

Truth-table test сравнивает compact condition с исходным объединением
canonical rows на полном конечном алфавите, включая multi-token matcher,
короткую строку и EOF.

## Structural delta

| Metric | Before slice | After slice |
| --- | ---: | ---: |
| Source productions / alternatives | 110 / 256 | 109 / 254 |
| Lowered CFG productions / alternatives / epsilon | 126 / 284 / 64 | 127 / 286 / 65 |
| Semantic action blocks / statements | 293 / 318 | 280 / 301 |
| Constructor statements | 70 | 65 |
| Collection / constant statements | 27 / 20 | 27 / 15 |
| Structural / other statements | 197 / 4 | 190 / 4 |
| Formal parameters / actual arguments | 8 / 26 | 8 / 26 |
| Generated BSL functions / LOC | 122 / 3 088 | 121 / 3 056 |
| Production SELECT rows | 6 223 | 5 973 |
| Full legacy matcher rows | 9 081 | 9 083 |
| Constructor names / identifier rows | 78 / 276 | 78 / 276 |

Optional/group synthetic CFG productions существуют только для canonical
analysis и не создают runtime functions. Full legacy audit по-прежнему считает
полную lowered compatibility representation отдельно от hybrid runtime
ownership.

## Coverage

- Два новых Python tests проверяют четыре terminal-name bindings, оба варианта
  аргумента `КОЛИЧЕСТВО`, optional `РАЗЛИЧНЫЕ`, factory default и отсутствие
  `АргументКоличество`/legacy dispatch в generated function.
- Существующие YAxUnit cases `АгрегатнаяФункцияРазбирается` покрывают
  `СУММА`, `МАКСИМУМ`, `МИНИМУМ`, `СРЕДНЕЕ` и их argument model.
- Существующие YAxUnit cases `КоличествоРазбирается` покрывают `*`, выражение и
  `РАЗЛИЧНЫЕ`; full-query totals cases покрывают aggregates в запросе.
- Отдельные codegen tests фиксируют форму prefix factoring и проверяют
  эквивалентность compact condition исходным canonical rows на 343 словах.
- Interactive YAxUnit/Vanessa execution остаётся финальным integration gate по
  договорённости.

## Verification

- Focused repository/config/audit/codec/reference: `61 passed`,
  `71 subtests passed`.
- Canonical BSL codegen contour: `38 passed`, `347 subtests passed`.
- Full `tools/parsergen/tests`: `429 passed`, `1 skipped`,
  `4 447 subtests passed`; skip — известное ограничение Windows на symlink.
- `parsergen validate`: exit `0`, две существующие `VAL102` warnings.
- `parsergen generate --check`: exit `0`, artifacts current.
- Canonical SELECT conflicts: `0`; legacy runtime conflicts: `0` при `k=2`.
- Migration audit: changed artifacts `0`.
- EDT revalidation `DataProcessor.Парсер`: baseline `7` diagnostics сохранён,
  новых syntax diagnostics нет.
- После gate нет Python process с working set выше 1 GB.

## Remaining

Order-list migration требует отдельного design для append непосредственно в
constructor result типа `Массив`: текущий утверждённый `Property += value`
работает с collection property. Этот infrastructure gap не маскируется
structural actions и не расширяется внутри aggregate checkpoint.
