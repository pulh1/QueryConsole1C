# Source/JOIN model migration checkpoint

Дата: 2026-08-08.

## Результат

Семейство `БлокИз` / source / JOIN переведено одним сквозным пакетом на
предметную древовидную модель:

```text
Оператор.Источники : Массив корневых Источник
Источник.Соединения : Массив СоединениеИсточника
СоединениеИсточника.Источник : дочерний Источник
```

Технический container `ИсточникиЗапроса.Элементы`, плоский registry всех
источников и UUID-ссылка `Соединение.Источник` удалены. UUID самого source
сохранён как domain identity (`ИдентификаторИсточника`).

Source grammar больше не передаёт accumulator `Источники` и не содержит
structural actions для регистрации source/JOIN:

```text
<БлокИз> ::= @НовыйИсточникиЗапроса
    += <ИсточникДанныхЗапроса>
    (',' += <ИсточникДанныхЗапроса>)*

<ИсточникДанныхЗапроса> ::=
    @НовыйИсточник
    Источник = <ИсточникДанных>
    Соединения = <СписокСоединений>
```

`ПраваяЧастьСоединения` и `ИсточникДанныхСоединения` также используют только
constructor/scalar/constant bindings. Все четыре source/JOIN productions
генерируются canonical path при production `k=2`.

## Model invariants

- source принадлежит ровно одному корню или одному JOIN;
- JOIN хранит дочерний source непосредственно;
- дерево не допускает циклы и повторное включение одного source;
- `ВсеИсточники` возвращает стабильный depth-first порядок;
- `СортироватьИсточникиПоИерархии` теперь является тем же depth-first обходом,
  без временных graph/container allocations;
- builder проверяет цикл до изменения дерева.

При удалении source его дочерние JOIN sources поднимаются в корневой массив,
что сохраняет прежний observable contract удаления отдельной таблицы.

## Migrated consumers

Фактическими references обновлены:

- semantic/model processing: `ОбработкаМоделиЗапроса`,
  `МодельЗапросаУтилиты`;
- executor и executable views: `ИсполнительПредставлений`;
- query/code generation: `ГенераторТекстовЗапросов`,
  `ГенераторFeatureФайлов`;
- builder: `ПостроительМоделиЗапроса`;
- universal report: `УниверсальныйОтчетРасширенный`;
- Query Constructor services и три form modules;
- parser, semantic, executable-view, builder/generator и model YAxUnit tests.

По repository search обращений `.Источники.Элементы` и UUID-интерпретаций
JOIN больше нет. Временные map-параметры `НайтиСоединение` и
`НайтиСредиВсехСоединений` удалены.

## Coverage

Добавлены/обновлены characterization contracts:

- parser сохраняет root/source/JOIN порядок и direct child source;
- model traversal возвращает root, child и nested child depth-first;
- hierarchy ordering совпадает с tree traversal;
- builder переносит присоединяемый source из roots в JOIN;
- builder отклоняет попытку создать цикл;
- factory inventory фиксирует `Оператор.Источники` и
  `НовыйИсточникиЗапроса` как массивы;
- existing semantic/executor/generator projections читают новую model.

YAxUnit tests подготовлены, но их интерактивный запуск оставлен на финальный
integration gate по согласованному порядку.

## Structural metrics

| Metric | До | После |
| --- | ---: | ---: |
| Source productions / alternatives | 70 / 162 | 70 / 162 |
| Lowered CFG productions / alternatives / epsilon | 149 / 319 / 75 | 149 / 319 / 75 |
| Semantic action blocks / statements | 21 / 25 | 7 / 8 |
| Constructor / collection / structural statements | 5 / 4 / 15 | 1 / 2 / 5 |
| Formal parameters / actual arguments | 10 / 26 | 5 / 17 |
| Generated BSL functions / LOC | 82 / 2 200 | 82 / 2 171 |
| SELECT artifact rows | 261 | 137 |
| Legacy matcher rows | 10 283 | 10 283 |

- production lookahead: `k=2`;
- canonical conflicts: `[]`;
- canonical diagnostics: `[]`;
- legacy runtime conflicts: `[]`;
- generated artifacts current: да.

## Verification

- focused repository/config/audit/reference suites: `60 passed`,
  `139 subtests`;
- full `tools/parsergen/tests`: `481 passed`, `1 skipped`,
  `4 552 subtests`;
- skip: системное ограничение Windows на создание symlink (`WinError 1314`);
- EDT targeted revalidation production objects: success, новых `ERRORS` нет;
- EDT targeted revalidation changed YAxUnit modules: success, `ERRORS` нет;
- интерактивный YAxUnit/Vanessa run: отложен до финального integration gate.
