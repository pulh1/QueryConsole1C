# Production checkpoint: field dereference package

Одним vertical slice мигрированы четыре связанные части expression grammar:

- `Поле`;
- техническая parameterized production `ОперацияРазыменования`;
- `ВыражениеВсеПоляИсточника` и `ПоляВложеннойТаблицы` как предметные
  semantic child-productions;
- `ВыражениеМоделиЗапроса`.

`Поле` теперь декларативно строит `Разыменование`: первый элемент выбирается
между идентификатором, приведением типа и списком выражений в скобках;
последующие идентификаторы добавляются через EBNF `*`; завершающие `.*` и
`.(...)` представлены optional semantic child. Техническая рекурсия с
параметром `Элементы` удалена, generated parser использует один BSL-loop.

## Preserved language and model contract

Query model и factories не изменялись. Сохраняются:

- одиночное поле и цепочки `Таблица.Поле.Свойство`;
- ключевое слово как имя после точки, например `Таблица.ВЫБРАТЬ`;
- `Таблица.*` с узлом `ВыражениеВсеПоляИсточника`;
- `Таблица.(Поле1, Поле2)` с узлом `ПоляВложеннойТаблицы`;
- `(Поле1, Поле2).Свойство`;
- `ВЫРАЗИТЬ(1 КАК ЧИСЛО).Свойство`;
- обёртка `ВыражениеМоделиЗапроса.Значение`.

В YAxUnit добавлены semantic projections специальных форм и цепочка из 500
разыменований. Они не проверяют удалённую helper-production и будут выполнены
в общем финальном platform gate.

## Structural delta

| Metric | Before slice | After slice |
| --- | ---: | ---: |
| Source productions / alternatives | 103 / 242 | 104 / 238 |
| Lowered CFG productions / alternatives / epsilon | 127 / 286 / 65 | 133 / 292 / 66 |
| Semantic action blocks / statements | 196 / 217 | 184 / 200 |
| Constructor / collection / constant / structural statements | 38 / 22 / 14 / 139 | 32 / 16 / 14 / 135 |
| Formal parameters / actual arguments | 8 / 26 | 7 / 22 |
| Generated BSL functions / LOC | 115 / 2 839 | 116 / 2 821 |
| Production SELECT rows | 5 433 | 5 075 |
| Full legacy matcher rows | 9 083 | 9 207 |

Source production count вырос на одну, потому что одна техническая
`ОперацияРазыменования` заменена двумя предметными AST productions. Шесть
дополнительных lowered productions существуют только в synthetic analysis
representation для group/repeat/optional и не создают recursive runtime
functions. Рост full legacy matcher rows не переносится в production hybrid
artifact: его SELECT rows уменьшились на 358.

## Verification

- RED: intended canonical ownership отклонено из-за отсутствующих
  `ВыражениеВсеПоляИсточника` и `ПоляВложеннойТаблицы`.
- GREEN package shape-test: generated `Поле` содержит один `Пока`, не вызывает
  `ОперацияРазыменования` и не использует `ТекущийЭлемент`/legacy dispatch.
- Repository/config/audit/codec/reference contour: `67 passed`,
  `83 subtests passed`.
- Complete Python suite: `435 passed`, `1 skipped`, `4459 subtests passed`;
  skip относится к отсутствующей Windows privilege для symlink.
- `parsergen validate`: exit `0`, только две существующие `VAL102` warnings.
- `parsergen generate --check`: artifacts current.
- Migration audit: canonical conflicts `0`, legacy runtime conflicts `0`,
  `changed_artifacts = []`, production lookahead `k=2`.
- Targeted EDT revalidation: production parser сохранил прежние 7 markers;
  YAxUnit-модуль имеет 35 metadata/region-style markers и не имеет syntax
  diagnostics.

Порядок `Если` не используется для разрешения конфликтов: все alternatives и
границы repeat/optional приняты только после disjoint canonical SELECT
validation при `k=2`.
