# Production checkpoint: select field

Одним semantic package мигрировано поле выборки:

- обычное expression field;
- optional alias с `КАК` и без него;
- standalone `*`;
- два реальных слоя AST для `*`: `ВыражениеМоделиЗапроса` и
  `ВыражениеВсеПоля`.

`ПолеВыборки` теперь использует только constructor declarations и scalar / optional
bindings. Обычный field больше не вызывает legacy
`ПсевдонимОпционально`; optional alias разбирается canonical conditional parse.
Production `ПсевдонимОпционально` временно остаётся только для legacy table-source
island.

## Preserved language and model contract

Factories и query model не менялись. Сохранены:

- `ПолеЗапроса.Выражение`;
- `ПолеЗапроса.Псевдоним` и factory default `Неопределено` при отсутствии alias;
- `ВыражениеМоделиЗапроса.Значение`;
- semantic node с `Тип = "ВыражениеВсеПоля"` для standalone `*`.

Отдельные semantic productions `ВыражениеВсеПоляВыборки` и
`ВыражениеВсеПоля` соответствуют двум существующим model nodes. Это не
continuation/list/optional plumbing. Для обычного field число runtime calls
уменьшилось на один; два wrapper calls выполняются только для standalone `*`.

Grammar по-прежнему не допускает alias после standalone `*`. Canonical SELECT
двух alternatives `ПолеВыборки` disjoint при `k=2`; порядок generated `Если`
не используется для разрешения конфликта.

## Structural delta

| Metric | Before package | After package |
| --- | ---: | ---: |
| Source productions / alternatives | 98 / 228 | 100 / 230 |
| Lowered CFG productions / alternatives / epsilon | 135 / 298 / 68 | 138 / 302 / 69 |
| Semantic action blocks / statements | 136 / 152 | 131 / 146 |
| Constructor / collection / constant / structural statements | 27 / 16 / 14 / 92 | 23 / 16 / 14 / 90 |
| Formal parameters / actual arguments | 7 / 22 | 7 / 22 |
| Generated BSL functions / LOC | 110 / 2 617 | 112 / 2 627 |
| Production SELECT rows | 3 837 | 3 592 |
| Full legacy matcher rows | 9 530 | 9 618 |

Рост source/generated function count на два — явное представление двух
существующих semantic AST layers для `*`. При этом из production grammar
удалены четыре constructor/structural actions и normal-field path больше не
зависит от legacy matcher dispatch. Снижение production SELECT artifact на 245
rows отражает перевод `ПолеВыборки` на canonical Parser IR. Legacy matcher
остаётся отдельным compatibility artifact для ещё не мигрированных productions.

## Test coverage

Существующий headless YAxUnit `ПолеCase` защищает:

- F01 — несколько полей и их количество;
- F02/F03 — alias с `КАК` и без него;
- F04 — standalone `*` и точный semantic node type;
- F05 — `Т.*` как отдельный dereference construct;
- F06 — обычное разыменованное поле;
- F07 — порядок нескольких полей с aliases;
- F08 — keyword identifier после точки и keyword alias.

Добавлен Python generated-shape test. Он проверяет constructor counts, scalar
и optional bindings, оба semantic wrapper nodes, отсутствие
`ТекущийЭлемент`, `НомерВариантаПродукции` и вызова
`ПсевдонимОпционально` в canonical `ПолеВыборки`.

Platform execution YAxUnit остаётся общим финальным интерактивным gate по
договорённому порядку; формы этот пакет не затрагивает.

## Verification

- RED: старое `ПолеВыборки` отвергалось Parser IR из-за отсутствующих новых
  semantic productions и arbitrary structural actions.
- Focused generated-shape/config/audit tests: `3 passed`.
- Complete Python suite: `439 passed`, `1 skipped`, `4493 subtests passed`;
  skip относится к Windows symlink privilege.
- Codec/reference baseline после intentional generation обновлён на 3 592
  SELECT rows.
- `parsergen validate`: exit `0`, две существующие `VAL102` warnings.
- Canonical conflicts `0`, legacy runtime conflicts `0`, production
  lookahead сохранён `k=2`.
- Generated artifacts воспроизводимы (`artifacts.changed = []`).
- Targeted EDT revalidation сохранила прежние 7 parser markers; новых syntax
  diagnostics нет.
