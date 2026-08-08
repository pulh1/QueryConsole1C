# Checkpoint: iterative logical negation

Дата: 2026-08-08.

## Результат

Family логического отрицания переведена с recursive continuation на EBNF:

```text
<Отрицание> ::=
    @НовыйЛогическоеОтрицание
    НЕ
    (Количество ++= НЕ)*
```

Удалена production `ОтрицаниеПродолжение`. Один и несколько операторов `НЕ`
теперь разбираются одной generated function и одним BSL loop. Parser stack не
растет с длиной цепочки.

Query model не менялась:

- factory по-прежнему создает `Количество = 1`;
- каждый дополнительный `НЕ` увеличивает `Количество` на единицу;
- property `Выражение` по-прежнему заполняется вызывающей expression family;
- отдельные continuation AST nodes не создаются.

## Increment binding

Добавлен узкий declarative binding:

```text
Количество ++= НЕ
```

Semantics: consume terminal/token, не сохранять его text и увеличить numeric
scalar property на единицу. Binding требует property и active constructor,
разрешен внутри repeat, не смешивается с другими modes того же property и на
первой итерации ограничен terminal-like values. Structural nonterminal дает
`BIND209`.

Parser IR представляет операцию как `IncrementScalar`. Generated BSL не
создает временную переменную для token value:

```bsl
Терминал("НЕ");
ЭтотУзел.Количество = ЭтотУзел.Количество + 1;
```

## Characterization coverage

Headless YAxUnit test `ЛогическоеОтрицаниеРазбирается` параметризован двумя
контрактами:

- `НЕ 1 = 2` → `Количество = 1`;
- `НЕ НЕ НЕ 1 = 2` → `Количество = 3`.

Тест также сохраняет прежнюю проверку expression child и оператора сравнения.
Source зарегистрирован и успешно revalidated в EDT; фактический platform run
остается финальным integration gate миграции.

## Structural metrics

| Метрика | До | После |
| --- | ---: | ---: |
| Source productions / alternatives | 91 / 213 | 90 / 211 |
| Lowered CFG productions / alternatives / epsilon | 136 / 298 / 67 | 136 / 298 / 67 |
| Semantic action blocks / statements | 105 / 118 | 102 / 115 |
| Constructor / collection / constant / structural statements | 18 / 10 / 14 / 73 | 17 / 10 / 14 / 71 |
| Formal parameters / actual arguments | 7 / 22 | 7 / 22 |
| Generated BSL functions / LOC | 103 / 2 488 | 102 / 2 477 |
| SELECT rows | 2 090 | 2 087 |
| Legacy matcher rows | 9 572 | 9 572 |

Lowered CFG не изменился: source continuation заменен analysis-only synthetic
repeat production и не становится runtime function.

Canonical analysis остается `k=2`, SELECT alternatives disjoint:

- canonical conflicts: `0`;
- legacy runtime conflicts: `0`;
- validation diagnostics: `0`.

## Tests и diagnostics

`++=` покрыт на слоях DSL parser, validation, lowering/Parser IR и BSL codegen.
Repository shape-test проверяет constructor count, один loop, increment body,
отсутствие `ТекущийЭлемент`, `НомерВариантаПродукции` и удаленной continuation
function.

- focused infrastructure/repository suite: `130 passed`, `143 subtests`;
- полный `tools/parsergen/tests`: `462 passed`, `1 skipped`, `4509 subtests`;
- skip: недоступно создание symlink без Windows privilege;
- `parsergen validate`: exit `0`, diagnostics отсутствуют;
- targeted EDT revalidation parser и YAxUnit module: success.

У production parser остались прежние пять EDT markers. YAxUnit module имеет
существующий фон style/structure diagnostics; новых syntax errors после
characterization change не появилось.
