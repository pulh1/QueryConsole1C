# Production checkpoint: declarative built-in functions

Все 22 alternatives production `Функция` переведены с imperative actions на
constructors и declarative bindings.

Обычные и специализированные functions используют scalar bindings:

```text
@НовыйФункцияНачалоПериода
НАЧАЛОПЕРИОДА
'('
Дата = <Выражение>
','
ТипПериода = <ТипПериода>
')'
```

Технические recursive helpers списков и optional path удалены:

```text
@НовыйФункцияДатаВремя
ДАТАВРЕМЯ
'('
Аргументы += &ЧисловаяКонстанта
(',' Аргументы += &ЧисловаяКонстанта)*
')'

@НовыйФункцияЗначение
ЗНАЧЕНИЕ
'('
ЧастиПути += #ID_Полный
'.'
ЧастиПути += #ID_Полный
('.' ЧастиПути += #ID_Полный)?
')'
```

`ДАТАВРЕМЯ` lowering генерирует BSL loop. Optional третья часть `ЗНАЧЕНИЕ`
генерирует conditional parse. Synthetic CFG используется только analysis и не
создаёт runtime helper functions.

## Preserved model contract

Query model и factory functions не изменены. Сохраняются:

- три аргумента `ПОДСТРОКА`;
- имя и аргумент функций частей периода;
- `Дата`, `ТипПериода`, `Сдвиг`, `Дата1`, `Дата2`;
- оба аргумента `ЕСТЬNULL`;
- arguments функций представления и `ТИП`;
- ordered numeric `Аргументы` функции `ДАТАВРЕМЯ`;
- ordered `ЧастиПути` функции `ЗНАЧЕНИЕ`.

Существующий headless YAxUnit contour `ОдноаргументнаяФункцияРазбирается` и
`СпециализированнаяФункцияРазбирается` проверяет все перечисленные observable
properties, включая значения `МЕСЯЦ`/`ДЕНЬ`, порядок arguments и path parts.
Interactive execution остаётся финальным integration gate по договорённости.

## Removed plumbing

- `СписокАргументовДатаВремя`;
- `ПродолжениеАргументовДатаВремя`;
- `ОпциональноеПродолжениеАргументаЗначение`;
- 22 constructor actions и все structural property actions внутри `Функция`;
- три generated recursive/helper BSL functions.

## Structural delta

| Metric | Before slice | After slice |
| --- | ---: | ---: |
| Source productions / alternatives | 109 / 254 | 106 / 249 |
| Lowered CFG productions / alternatives / epsilon | 127 / 286 / 65 | 126 / 285 / 65 |
| Semantic action blocks / statements | 279 / 300 | 220 / 241 |
| Constructor statements | 65 | 43 |
| Collection / structural statements | 27 / 189 | 22 / 157 |
| Generated BSL functions / LOC | 121 / 3 051 | 118 / 2 929 |
| Production SELECT rows | 5 895 | 5 791 |
| Full legacy matcher rows | 9 083 | 9 082 |

Formal parameters, actual arguments, constant/other actions, constructor names
и identifier rows не изменились.

## Focused verification

- RED: old production rejected canonical ownership with
  `arbitrary source actions require declarative bindings`.
- GREEN shape-test checks 22 constructors, scalar/collection bindings, one
  generated loop, removed helper functions and absence of legacy dispatch.
- Repository/config/audit/codec/reference contour: `63 passed`,
  `74 subtests passed`.
- Canonical conflicts: `0`; production lookahead remains `k=2`.

Branch order is not a conflict-resolution mechanism: all alternatives are
accepted only after disjoint canonical SELECT validation.

## Final automated verification

- Complete Python suite: `431 passed`, `1 skipped`, `4450 subtests passed`;
  skip относится к недоступному созданию symlink без Windows privilege.
- `parsergen validate`: exit `0`; остаются только две известные warning
  `VAL102` для legacy actions вне этого slice.
- `parsergen generate --check`: production artifacts current.
- Migration audit: `changed_artifacts = []`, canonical conflicts `0`, legacy
  runtime conflicts `0`, production SELECT rows `5791`, full legacy matcher
  rows `9082`.
- Targeted EDT revalidation `DataProcessor.Парсер`: те же 7 baseline markers —
  metadata prefix, `НСтр` language code, четыре unused `ТекущийЭлемент` и
  unused legacy method `НеТерминалКакОпционально`.

YAxUnit/Vanessa на платформе 1С намеренно остаётся финальным interactive gate,
а не выполняется после каждого production slice.
