# Production checkpoint: root collection lists

Добавлен минимальный declarative binding для factories, возвращающих root
collection:

```text
<Список> ::= @НовыйСписок += <Элемент> (',' += <Элемент>)*
```

Property-less `+=` означает `ЭтотУзел.Добавить(Значение)`. Он не вводит
универсальную attribute grammar и не поддерживает scalar root assignment.
Binding требует active constructor; separator не попадает в collection.

На новый binding одним package переведены:

- `СписокЭлементовУпорядочивания`;
- `КонтрольныеТочкиИтогов`.

Удалены recursive technical productions:

- `ПродолжениеСпискаЭлементовУпорядочивания`;
- `СписокКонтрольныхТочекОпциональное`.

Обе comma-list families теперь generated как BSL loops. Runtime recursion,
`Родитель`, `ТекущийЭлемент`, structural `.Добавить(...)` actions и legacy
dispatch для этих lists отсутствуют.

## Preserved model contract

Query model и factories не менялись:

- `НовыйЭлементыПорядка` по-прежнему возвращает `Массив`;
- `НовыйКонтрольныеТочкиИтогов` по-прежнему возвращает `Массив`;
- порядок элементов сохраняется;
- list остаётся one-or-more, пустой список не принимается;
- comma является separator и не сохраняется в AST.

Canonical loop decisions используют disjoint SELECT при `k=2`. Порядок
generated `Если` не разрешает конфликт.

## Structural delta

| Metric | Before package | After package |
| --- | ---: | ---: |
| Source productions / alternatives | 100 / 230 | 98 / 226 |
| Lowered CFG productions / alternatives / epsilon | 138 / 302 / 69 | 138 / 302 / 69 |
| Semantic action blocks / statements | 131 / 146 | 123 / 138 |
| Constructor / collection / constant / structural statements | 23 / 16 / 14 / 90 | 21 / 12 / 14 / 88 |
| Formal parameters / actual arguments | 7 / 22 | 7 / 22 |
| Generated BSL functions / LOC | 112 / 2 627 | 110 / 2 595 |
| Production SELECT rows | 3 592 | 3 014 |
| Full legacy matcher rows | 9 618 | 9 618 |

Lowered CFG counts не изменились: две удалённые source continuation productions
заменены analysis-only synthetic repeat/tail productions. Они не становятся
runtime functions. Legacy matcher artifact не вырос, а новый canonical path
от него не зависит.

## Tests

Root binding покрыт отдельными Python tests на каждом слое:

- DSL parser и отличие `+=` от postfix `+`;
- malformed root binding без value;
- validation active-constructor contract;
- Parser IR `AppendCollection(property=None)`;
- generated BSL `ЭтотУзел.Добавить(...)`;
- separator repeat и отсутствие double-dot codegen.

Repository shape-test проверяет для обеих production families:

- один constructor;
- один BSL `Пока` loop;
- append первого и repeated элементов;
- отсутствие обеих continuation functions;
- отсутствие `ТекущийЭлемент` и `НомерВариантаПродукции`.

Существующие headless YAxUnit contracts покрывают order lists C06-C10/C15 и
totals control-point lists T03-T05/T06-T23, включая количество, порядок,
direction, hierarchy, aliases и period options. Forms этот package не
затрагивает; platform execution остаётся финальным интерактивным gate.

## Verification

- RED: parser трактовал property-less `+=` как postfix `+`, а старые list
  productions отвергались Parser IR из-за arbitrary actions.
- Focused infrastructure/repository suite: `112 passed`, `131 subtests passed`.
- Complete Python suite: `445 passed`, `1 skipped`, `4498 subtests passed`;
  skip относится к Windows symlink privilege.
- `parsergen validate`: exit `0`, две существующие `VAL102` warnings.
- Canonical conflicts `0`, legacy runtime conflicts `0`, production
  lookahead сохранён `k=2`.
- Generated artifacts воспроизводимы (`artifacts.changed = []`).
- Targeted EDT revalidation сохранила прежние 7 parser markers; новых syntax
  diagnostics нет.
