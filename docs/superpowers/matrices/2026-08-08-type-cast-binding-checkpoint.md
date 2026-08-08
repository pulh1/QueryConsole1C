# Production checkpoint: type cast and type descriptions

Связанный пакет из пяти legacy productions мигрирован одним vertical slice:

- `ПриведениеТипа`;
- `ОписаниеТипа`;
- `ОписаниеЧисла`;
- `ТочностьЧисла`;
- `ОписаниеСтроки`.

`ПриведениеТипа` теперь использует constructor и два scalar bindings:

```text
@НовыйПриведениеТипа
ВЫРАЗИТЬ
'('
Выражение = <Выражение>
КАК
ОписаниеТипа = <ОписаниеТипа>
')'
```

`ОписаниеТипа` содержит transparent ссылочную alternative и четыре
constructor alternatives. Параметры числа и строки выражены непосредственно
через EBNF optionals; три helper-productions удалены и не создают runtime BSL
functions.

## Preserved language and model contract

Query model и factories не изменены. Сохраняются формы:

- `БУЛЕВО`, `ДАТА` и ссылочный тип `Справочник.Номенклатура`;
- `ЧИСЛО`, `ЧИСЛО(10)`, `ЧИСЛО(10,)`, `ЧИСЛО(10, 2)`;
- `СТРОКА`, `СТРОКА(20)`.

Factory defaults сохраняются структурно: absent numeric parameters оставляют
`Длина=0` и `Точность=0`; comma-only precision consumes `,`, но не выполняет
assignment; absent string length оставляет `Длина=Неопределено`.

Существующий YAxUnit test `ПриведениеТипаРазбирается` расширен default,
comma-only и reference-type cases. Он проверяет тип description, numeric
length/precision, string length и ссылочные `Группа`/`Таблица`. Исполнение на
платформе остаётся общим финальным YAxUnit/Vanessa gate.

## Structural delta

| Metric | Before slice | After slice |
| --- | ---: | ---: |
| Source productions / alternatives | 106 / 249 | 103 / 242 |
| Lowered CFG productions / alternatives / epsilon | 126 / 285 / 65 | 127 / 286 / 65 |
| Semantic action blocks / statements | 212 / 233 | 196 / 217 |
| Constructor / constant / structural statements | 43 / 15 / 149 | 38 / 14 / 139 |
| Generated BSL functions / LOC | 118 / 2 891 | 115 / 2 839 |
| Production SELECT rows | 5 446 | 5 433 |
| Full legacy matcher rows | 9 082 | 9 083 |

Рост lowered CFG на одну production/alternative относится только к synthetic
analysis representation вложенных optionals. Runtime helper functions
уменьшились на три. Formal parameters, actual arguments, collection statements,
constructor names и identifier rows не изменились.

## Verification

- RED: old family rejected canonical ownership with
  `arbitrary source actions require declarative bindings`.
- GREEN package shape-test: `1 passed`, `3 subtests passed`.
- Repository/config/audit/codec/reference contour: `66 passed`,
  `83 subtests passed`.
- Complete Python suite: `434 passed`, `1 skipped`, `4459 subtests passed`;
  skip относится к недоступному созданию symlink без Windows privilege.
- `parsergen validate`: exit `0` с двумя известными `VAL102` warnings.
- `parsergen generate --check`: artifacts current.
- Migration audit: canonical conflicts `0`, legacy runtime conflicts `0`,
  `changed_artifacts = []`, production lookahead `k=2`.
- Targeted EDT revalidation: production parser — прежние 7 markers; changed
  YAxUnit module — 33 metadata/region-style markers, syntax diagnostics absent.

Branch order не является conflict-resolution mechanism: все alternatives
приняты только после disjoint canonical SELECT validation.
