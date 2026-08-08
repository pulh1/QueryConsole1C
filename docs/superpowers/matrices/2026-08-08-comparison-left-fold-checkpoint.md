# Checkpoint: canonical comparison left fold

Дата: 2026-08-08.

## Результат

Семейство сравнений и логического отрицания переведено на
canonical Parser IR:

- `ЛогическаяОперация` декларативно строит `ЛогическоеОтрицание`,
  считает повторы `НЕ` через EBNF `*` и привязывает всё сравнение к
  `Выражение`;
- `ЛогическаяОперацияБезОтрицания` описана естественной direct left
  recursion и lowered в один iterative BSL left-fold loop;
- все шесть операторов сравнения выбираются canonical SELECT(2);
- удалены technical productions `ОперацияСравнения` и `Отрицание`;
- generated runtime больше не вызывает recursive comparison continuation.

`k=2` не изменялся. Canonical alternatives остаются disjoint;
порядок generated `Если` не используется для разрешения конфликтов.

## Семантика

Отрицание сохраняет текущий domain contract: `НЕ 1 = 2` возвращает
`"ЛогическоеОтрицание"`, в `Выражение` которого лежит бинарное
сравнение. Default `Количество = 1` остаётся в constructor, каждый
дополнительный `НЕ` инкрементирует его один раз.

Цепочка сравнений lowered как левоассоциативная, что соответствует
формальной direct-LR semantics новой архитектуры. Прежний technical tail
строил правовложенный AST для цепочек; одиночные сравнения не
меняются.

## Coverage

Repository tests проверяют:

- `LeftFold` в Parser IR;
- один BSL loop без recursive self-call;
- один constructor и declarative bindings `ЛеваяЧасть`, `Операция`,
  `ПраваяЧасть` на итерацию;
- отсутствие runtime functions удалённых helpers;
- constructor, repeat counter и binding всего сравнения в узел отрицания;
- отсутствие legacy dispatch в обоих migrated productions.

Существующий YAxUnit expression contour покрывает все шесть операторов
сравнения, приоритет `И`/`ИЛИ`, один и три `НЕ`, а также predicates,
которые читают результат `ЛогическаяОперация`. Интерактивный platform run
остаётся финальным integration gate.

- Python: `475 passed`, `1 skipped`, `4 548 subtests`;
- skip: Windows symlink privilege (`WinError 1314`);
- generated artifacts current: да;
- targeted EDT revalidation `DataProcessor.Парсер`: успешно;
- EDT diagnostics severity `ERRORS` для `DataProcessor.Парсер`: 0.

## Metrics

| Метрика | До | После |
| --- | ---: | ---: |
| Source productions / alternatives | 73 / 169 | 72 / 168 |
| Lowered CFG productions / alternatives / epsilon | 144 / 311 / 72 | 144 / 311 / 72 |
| Semantic action blocks / statements | 51 / 61 | 42 / 51 |
| Constructor / collection / constant statements | 11 / 4 / 6 | 10 / 4 / 6 |
| Structural action statements | 40 | 31 |
| `Родитель` / `ЛевыйЭлемент` source usages | 1 / 6 | 1 / 5 |
| Generated BSL functions / LOC | 85 / 2 277 | 84 / 2 243 |
| SELECT artifact rows | 1 261 | 764 |
| Legacy analysis matcher rows | 10 025 | 10 225 |

Canonical analysis after migration:

- packed FIRST rows: 12 069;
- packed FOLLOW rows: 52 735;
- SELECT descriptors: 311;
- SELECT direct facts: 11 710;
- packed SELECT upper bound: 37 584;
- canonical conflicts: 0;
- legacy runtime conflicts: 0;
- validation diagnostics: 0.

## Remaining boundary

Пять оставшихся source usages `ЛевыйЭлемент` находятся в postfix predicate
family: `МЕЖДУ`, `ССЫЛКА`, `ЕСТЬ [НЕ] NULL`, `[НЕ] В` и `[НЕ] ПОДОБНО`.
Их нельзя механически заменить на unrestricted direct-LR repeat: такая замена
расширит язык повторными postfix predicates. Для пакета нужен
declarative max-one/returned-child lowering.

Последнее source usage `Родитель` остаётся в legacy СКД field-list. Для
его удаления требуется declarative binding к уже существующей коллекции,
поскольку observable `ГДЕ` branch заполняет `Оператор.ОтборыСКД`.
