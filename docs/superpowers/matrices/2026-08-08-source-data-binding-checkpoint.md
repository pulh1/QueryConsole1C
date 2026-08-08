# Production checkpoint: source-data dispatch and bindings

Одним vertical slice мигрированы четыре связанные production:

- `ИсточникДанных`;
- `ПрисоединяемаяТаблица`;
- `ИсточникДанныхВременнаяТаблица`;
- `ИсточникДанныхВложенныйЗапрос`.

Две abstract productions теперь выполняют transparent canonical dispatch без
imperative propagation. Временная таблица и вложенный запрос используют
constructors и scalar/optional bindings для имени, запроса и alias.

## Preserved language and model contract

Query model и factories не изменены. Сохраняются:

- обычные таблицы, таблицы значений, временные таблицы и вложенные запросы;
- обязательный alias таблицы значений и вложенного запроса;
- optional alias временной таблицы с factory default `Псевдоним=""`;
- те же три source kinds в правой части JOIN.

`ПсевдонимОпционально` намеренно не включён в пакет. Его legacy empty branch
возвращает sentinel `ПУСТО`, который legacy callers используют для пропуска
assignment. Частичная canonical migration вернула бы `Неопределено` и могла
затереть factory defaults. Новый temporary-source production использует
guarded optional binding напрямую; общий helper будет удалён только вместе со
всеми оставшимися callers.

Существующие full-parser YAxUnit scenarios S01–S10 и J01–J07 уже покрывают
все четыре dispatch branches, aliases, temporary/nested sources и JOIN. Новые
дублирующие BSL tests для этого slice не добавлялись; platform execution
остаётся общим финальным gate.

## Structural delta

| Metric | Before slice | After slice |
| --- | ---: | ---: |
| Source productions / alternatives | 104 / 238 | 104 / 238 |
| Lowered CFG productions / alternatives / epsilon | 133 / 292 / 66 | 134 / 294 / 67 |
| Semantic action blocks / statements | 184 / 200 | 171 / 187 |
| Constructor / collection / constant / structural statements | 32 / 16 / 14 / 135 | 30 / 16 / 14 / 124 |
| Formal parameters / actual arguments | 7 / 22 | 7 / 22 |
| Generated BSL functions / LOC | 116 / 2 821 | 116 / 2 780 |
| Production SELECT rows | 5 075 | 4 904 |
| Full legacy matcher rows | 9 207 | 9 293 |

Одна дополнительная lowered production и две alternatives относятся только к
synthetic representation optional alias. Runtime helper function не создаётся.
Рост full legacy matcher rows не переносится в production hybrid artifact:
его SELECT rows уменьшились на 171.

## Verification

- RED: old selected productions rejected Parser IR с
  `arbitrary source actions require declarative bindings`.
- GREEN package shape-test: `1 passed`, `7 subtests passed`; abstract functions
  не используют `НомерВариантаПродукции`/`ТекущийЭлемент`, concrete functions
  используют bindings и не вызывают `ПсевдонимОпционально`.
- Repository/config/audit/codec/reference contour: `68 passed`,
  `90 subtests passed`.
- Complete Python suite: `436 passed`, `1 skipped`, `4466 subtests passed`;
  skip относится к отсутствующей Windows privilege для symlink.
- `parsergen validate`: exit `0`, только две существующие `VAL102` warnings.
- `parsergen generate --check`: artifacts current.
- Migration audit: canonical conflicts `0`, legacy runtime conflicts `0`,
  `changed_artifacts = []`, production lookahead `k=2`.
- Targeted EDT revalidation: production parser сохранил прежние 7 markers;
  syntax diagnostics не добавлены.

Порядок branches не разрешает неоднозначности: source alternatives приняты
только после disjoint canonical SELECT validation при `k=2`.
