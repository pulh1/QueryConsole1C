# Production checkpoint: transparent operand dispatch

Production `Операнд` переведена с шести imperative propagation actions на
transparent canonical alternatives:

```text
<Операнд> ::= <Выбор>
<Операнд> ::= <Поле>
<Операнд> ::= <Константа>
<Операнд> ::= <Параметр>
<Операнд> ::= <АгрегатнаяФункция>
<Операнд> ::= <Функция>
```

Каждая alternative возвращает единственный parsed child. Query model,
constructors и свойства AST не меняются. `Поле` пока остаётся legacy child;
hybrid ABI допускает canonical `Операнд` → legacy `Поле`, не включая legacy
matcher semantics в decision самой `Операнд`.

## Coverage

Существующий headless YAxUnit expression contour семантически защищает все
шесть alternatives:

- `ВыборРазбирается`;
- `РазыменованиеРазбирается`;
- `КонстантаРазбирается`;
- `ПараметрЗапросаРазбирается`;
- `АгрегатнаяФункцияРазбирается` и `КоличествоРазбирается`;
- `ОдноаргументнаяФункцияРазбирается` и
  `СпециализированнаяФункцияРазбирается`.

Новый Python shape-test проверяет шесть child calls и шесть transparent return
paths. Он прошёл обязательный RED/GREEN cycle: старая grammar была отвергнута
с `arbitrary source actions require declarative bindings`, после удаления
actions generated function стала canonical и не содержит `ТекущийЭлемент` или
`НомерВариантаПродукции`.

## Structural delta

| Metric | Before slice | After slice |
| --- | ---: | ---: |
| Source productions / alternatives | 106 / 249 | 106 / 249 |
| Lowered CFG productions / alternatives / epsilon | 126 / 285 / 65 | 126 / 285 / 65 |
| Semantic action blocks / statements | 220 / 241 | 214 / 235 |
| Structural statements | 157 | 151 |
| Generated BSL functions / LOC | 118 / 2 929 | 118 / 2 902 |
| Production SELECT rows | 5 791 | 5 647 |
| Full legacy matcher rows | 9 082 | 9 082 |

Остальные structural metrics не изменились. Production lookahead остаётся
`k=2`; canonical SELECT alternatives попарно disjoint, порядок generated
`Если` конфликт не разрешает.

## Focused verification

- RED/GREEN transparent dispatch test: `1 passed`, `6 subtests passed`.
- Repository/config/audit/codec/reference contour: `64 passed`,
  `80 subtests passed`.
- Canonical conflicts: `0`; legacy runtime conflicts: `0`.
- Production artifacts regenerated intentionally; reference fixtures
  synchronized with the reviewed generated output.
- Complete Python suite: `432 passed`, `1 skipped`, `4456 subtests passed`;
  skip относится к недоступному созданию symlink без Windows privilege.
- `parsergen validate`: exit `0` с двумя известными `VAL102` warnings;
  `parsergen generate --check`: artifacts current.
- Targeted EDT revalidation `DataProcessor.Парсер`: прежние 7 markers —
  metadata prefix, `НСтр` language code, четыре unused `ТекущийЭлемент` и
  unused legacy method `НеТерминалКакОпционально`.

YAxUnit/Vanessa на платформе 1С остаётся финальным interactive gate по
согласованной стратегии миграции.
