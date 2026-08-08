# Production checkpoint: totals control point

Одним coherent package мигрировано семейство `КонтрольнаяТочкаИтогов`:

- сама semantic production контрольной точки;
- девять значений `ТипПериодаИтогов`;
- optional `ПЕРИОДАМИ`, начало/конец периода и псевдоним;
- alternative `ОБЩИЕ`.

Удалены шесть technical productions:

- `ПродолжениеКонтрольнойТочкиИтогов`;
- `ДополнениеПериодамиИтогов`;
- `ПсевдонимКонтрольнойТочкиИтогов`;
- `ПериодДополненияИтогов`;
- `ОкончаниеПериодаИтогов`;
- `ПериодИтогов`.

Все свойства одного model node теперь задаются scalar bindings непосредственно
в естественной source grammar. В generated BSL вложенные optional-группы
становятся conditional parse; отдельные runtime helper-функции не создаются.

## Preserved language and model contract

Factories и query model не менялись. Сохранены свойства `Выражение`,
`ТипКонтрольнойТочки`, `ИмяКолонки`, `ТипДополненияПериодами`,
`НачалоПериодаДополнения`, `КонецПериодаДополнения`, а также отдельный узел
`ОбщиеИтоги`.

Новая grammar сохраняет все варианты старого периода:

- без границ;
- только с началом;
- с началом и концом;
- с пропущенным началом;
- с пропущенным концом;
- с обеими пропущенными границами.

Псевдоним после `ПЕРИОДАМИ` также остаётся допустимым. У `ОБЩИЕ` псевдоним,
как и раньше, только потребляется и не сохраняется в model node; поэтому его
лексическая форма описана inline без лишнего semantic result и без
неиспользуемой generated BSL variable.

## Structural delta

| Metric | Before package | After package |
| --- | ---: | ---: |
| Source productions / alternatives | 104 / 238 | 98 / 228 |
| Lowered CFG productions / alternatives / epsilon | 134 / 294 / 67 | 135 / 298 / 68 |
| Semantic action blocks / statements | 160 / 176 | 136 / 152 |
| Constructor / collection / constant / structural statements | 29 / 16 / 14 / 114 | 27 / 16 / 14 / 92 |
| Formal parameters / actual arguments | 7 / 22 | 7 / 22 |
| Generated BSL functions / LOC | 116 / 2 726 | 110 / 2 617 |
| Production SELECT rows | 4 527 | 3 837 |
| Full legacy matcher rows | 9 293 | 9 530 |

Lowered CFG временно содержит synthetic optional productions только для
canonical analysis. Они не превращаются в BSL functions. Рост полного legacy
matcher artifact отражает EBNF lowering compatibility representation; новая
production выполняется через canonical Parser IR и от этого artifact не
зависит.

## Test coverage

До migration уже существовали T06-T20: `ОБЩИЕ`, оба вида иерархии, оба вида
псевдонима, все девять типов периода и обе заданные границы. Добавлены
headless YAxUnit characterization cases:

- T10A — псевдоним после `ПЕРИОДАМИ`;
- T21 — только начальная граница;
- T22 — пропущенное начало и заданный конец;
- T23 — обе границы пропущены.

Это тесты parser/query-model без работы с формами. Их platform execution
остаётся общим финальным интерактивным gate по договорённому порядку.

## Verification

- RED: old production rejected Parser IR с
  `arbitrary source actions require declarative bindings`.
- GREEN package shape-test: `1 passed`, `21 subtests passed`; шесть helper
  functions отсутствуют, bindings присутствуют, legacy dispatch и
  `ТекущийЭлемент` не используются.
- Focused package shape-test: `1 passed`, `21 subtests passed`.
- Complete Python suite: `438 passed`, `1 skipped`, `4493 subtests passed`;
  skip относится к Windows symlink privilege.
- `parsergen validate`: exit `0`, две существующие `VAL102` warnings.
- `parsergen generate --check`: artifacts current.
- Canonical conflicts `0`, legacy runtime conflicts `0`, production
  lookahead сохранён `k=2`.
- Targeted EDT revalidation: production parser вернулся к прежним 7 markers;
  unused semantic result отсутствует. YAxUnit-модуль имеет 37 прежних
  metadata/region-style markers; новых syntax diagnostics нет.

Порядок generated `Если` не разрешает неоднозначность: все alternatives и
optional decisions приняты только после disjoint canonical SELECT validation
при `k=2`.
