# Production checkpoint: transparent factor dispatch

Production `Множитель` переведена с двух imperative propagation actions на
transparent canonical alternatives:

```text
<Множитель> ::= <Операнд>
<Множитель> ::= <УнарнаяОперация>
```

Обе alternatives возвращают единственный parsed child. Query model,
constructors и AST properties не меняются. `Операнд` и `УнарнаяОперация` уже
принадлежат canonical parser path, поэтому multiplicative expression family
больше не возвращается в legacy dispatch на этом уровне.

## Coverage

Существующий headless YAxUnit expression contour защищает оба пути:

- обычные operands через constant, field, parameter, aggregate, function и
  `ВЫБОР` scenarios;
- unary path через `УнарнаяОперацияРазбирается` и
  `ПовторныеУнарныеЗнакиРазбираются`;
- precedence и associativity через multiplication/division expression tests.

Новый Python shape-test проверяет оба child calls и transparent returns. RED
получен на старой grammar с `arbitrary source actions require declarative
bindings`; GREEN получен после удаления только двух propagation actions.

## Structural delta

| Metric | Before slice | After slice |
| --- | ---: | ---: |
| Source productions / alternatives | 106 / 249 | 106 / 249 |
| Lowered CFG productions / alternatives / epsilon | 126 / 285 / 65 | 126 / 285 / 65 |
| Semantic action blocks / statements | 214 / 235 | 212 / 233 |
| Structural statements | 151 | 149 |
| Generated BSL functions / LOC | 118 / 2 902 | 118 / 2 891 |
| Production SELECT rows | 5 647 | 5 446 |
| Full legacy matcher rows | 9 082 | 9 082 |

Остальные structural metrics не изменились. Production lookahead остаётся
`k=2`; canonical SELECT alternatives попарно disjoint, порядок generated
`Если` конфликт не разрешает.

## Focused verification

- RED/GREEN transparent dispatch test: `1 passed`.
- Repository/config/audit/codec/reference contour: `65 passed`,
  `80 subtests passed`.
- Canonical conflicts: `0`; legacy runtime conflicts: `0`.
- Production artifacts regenerated intentionally; reference fixtures
  synchronized with the generated output.
- Complete Python suite: `433 passed`, `1 skipped`, `4456 subtests passed`;
  skip относится к недоступному созданию symlink без Windows privilege.
- `parsergen validate`: exit `0` с двумя известными `VAL102` warnings;
  `parsergen generate --check`: artifacts current.
- Targeted EDT revalidation `DataProcessor.Парсер`: прежние 7 markers —
  metadata prefix, `НСтр` language code, четыре unused `ТекущийЭлемент` и
  unused legacy method `НеТерминалКакОпционально`.

YAxUnit/Vanessa на платформе 1С остаётся финальным interactive gate по
согласованной стратегии миграции.
