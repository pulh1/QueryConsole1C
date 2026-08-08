# Production checkpoint: logical leaf values

Одним vertical slice мигрированы три связанные leaf production логических
операторов:

- `ОперандВ`;
- `ОператорСравнения`;
- `ШаблонПодобия`.

`ОперандВ` теперь transparent canonical choice между списком выражений и
вложенным запросом. Все шесть comparison terminals возвращают своё значение
без propagation actions. Строковый шаблон `ПОДОБНО` строит `Константа` через
constructor/value binding, а параметрическая alternative остаётся transparent.

## Preserved language and model contract

Query model и factories не изменены. Сохраняются:

- операторы `=`, `<>`, `>`, `<`, `>=`, `<=`;
- `В` со списком выражений и вложенным запросом;
- строковый шаблон `ПОДОБНО` как `Константа`;
- параметрический шаблон `ПОДОБНО &Шаблон` как `ПараметрЗапроса`.

Существующие YAxUnit comparison и IN cases уже покрывают все terminal и
operand branches. `ПодобноРазбирается` расширен параметрическим шаблоном и
теперь явно проверяет тип/value/name правого узла. Platform execution остаётся
общим финальным gate.

## Structural delta

| Metric | Before slice | After slice |
| --- | ---: | ---: |
| Source productions / alternatives | 104 / 238 | 104 / 238 |
| Lowered CFG productions / alternatives / epsilon | 134 / 294 / 67 | 134 / 294 / 67 |
| Semantic action blocks / statements | 171 / 187 | 160 / 176 |
| Constructor / collection / constant / structural statements | 30 / 16 / 14 / 124 | 29 / 16 / 14 / 114 |
| Formal parameters / actual arguments | 7 / 22 | 7 / 22 |
| Generated BSL functions / LOC | 116 / 2 780 | 116 / 2 726 |
| Production SELECT rows | 4 904 | 4 527 |
| Full legacy matcher rows | 9 293 | 9 293 |

CFG и full legacy artifact не изменились: source migration удаляет только
imperative AST plumbing. Production hybrid SELECT artifact уменьшился на 377
rows, потому что три production больше не входят в legacy runtime matcher.

## Verification

- RED: old selected productions rejected Parser IR с
  `arbitrary source actions require declarative bindings`.
- GREEN package shape-test: `1 passed`, `6 subtests passed`; функции не
  используют `НомерВариантаПродукции`/`ТекущийЭлемент`.
- Repository/config/audit/codec/reference contour: `69 passed`,
  `96 subtests passed`.
- Complete Python suite: `437 passed`, `1 skipped`, `4472 subtests passed`;
  skip относится к отсутствующей Windows privilege для symlink.
- `parsergen validate`: exit `0`, только две существующие `VAL102` warnings.
- `parsergen generate --check`: artifacts current.
- Migration audit: canonical conflicts `0`, legacy runtime conflicts `0`,
  `changed_artifacts = []`, production lookahead `k=2`.
- Targeted EDT revalidation: production parser сохранил прежние 7 markers;
  YAxUnit-модуль сохранил прежние 35 metadata/region-style markers; syntax
  diagnostics не добавлены.

Порядок comparison branches не разрешает конфликт: alternatives приняты
только после disjoint canonical SELECT validation при `k=2`.
