# Итоговый отчёт миграции grammar/query model

Дата: 2026-08-08.

## Результат

Production parser переведён на canonical LL(2) path. Source grammar больше не
содержит параметров и actions, repetition генерируется BSL loops, direct
left recursion — iterative left fold. Generated production runtime не строит
legacy matcher, не вызывает `НомерВариантаПродукции` и не содержит implicit ABI
`Родитель`/`ЛевыйЭлемент`.

Query model источников теперь отражает предметное дерево JOIN, а не плоский
parser accumulator. Все найденные non-form consumers мигрированы и защищены
headless tests; интерактивные формы проверены финальным Vanessa/manual gate.

## 1. Impact analysis

Изменённое семейство модели:

| Было | Стало | Contract |
| --- | --- | --- |
| `Оператор.Источники` — container `ИсточникиЗапроса` с `.Элементы` и `.Таблицы` | `Оператор.Источники` — `Массив` корневых `Источник` | Порядок корней сохраняется |
| `СоединениеИсточника.Источник` — UUID, разрешаемый через общий registry | `СоединениеИсточника.Источник` — дочерний `Источник` | JOIN образует предметное дерево |
| Плоский registry и отдельная сортировка по иерархии | `ВсеИсточникиОператора`/`ВсеИсточники` | Стабильный depth-first обход, защита от циклов и повторных узлов |

`Источник.ИдентификаторИсточника` сохранён как domain identity. При удалении
корневого или JOIN-source observable contract сохраняется: дочерние источники
обрабатываются явно, builder не допускает цикл.

Фактическими references мигрированы:

- parser и AST factories;
- `ОбработкаМоделиЗапроса`, `МодельЗапросаУтилиты`;
- `ПостроительМоделиЗапроса`;
- `ИсполнительПредставлений`, executable-view processing;
- генераторы query/expression/BSL/feature text;
- query console и universal report;
- Query Constructor object services и три form module;
- 15 `Представление*` manager consumers;
- соответствующие YAxUnit modules.

После миграции repository search не находит обращений к
`Оператор.Источники.Элементы`; UUID JOIN больше не используется как ссылка на
source. Compatibility wrapper старой модели не создавался.

Полная карта consumers и путей:
[impact matrix](2026-08-07-query-model-consumer-impact.md). Сквозной checkpoint
модели: [source/JOIN migration](2026-08-08-source-join-model-migration-checkpoint.md).

## 2. Test coverage matrix

| Area | Post-migration evidence | Remaining gap |
| --- | --- | --- |
| Python parsergen/canonical/legacy/codegen | 508 passed, 1 skipped, 4 558 subtests | Windows symlink privilege only |
| Expression + full parser | 223/223 YAxUnit GREEN | Нет headless gap |
| Lexer/model/semantic/executor/generation/report/other consumers | 265 total / 262 passed / 3 skips | Один старый production defect; два form-only API blockers |
| Runtime benchmark | 1/1 YAxUnit GREEN | Дорогие production counters намеренно не внедрялись |
| Query Constructor/forms | Non-form logic покрыта; Vanessa прошла, изменение JOIN и удаление источников проверены вручную | Два form-data API contract остаются недоступны headless |

Свежий суммарный headless gate: **494 total / 491 passed / 0 failed /
0 errors / 3 documented skips**. Детализация всех C01–C18 и X01 находится в
[coverage matrix](2026-08-07-grammar-query-model-coverage.md).

## 3. Architecture/design

Pipeline разделён явно:

```text
Source EBNF Grammar
  -> Source Grammar AST
  -> validation + CFG lowering
  -> canonical nullable/FIRST/FOLLOW/SELECT
  -> canonical Parser IR
  -> optimized BSL codegen
```

Source AST хранит `Sequence`, `Alternative`, `Group`, `Repeat(*)`, `Plus(+)`,
`Optional(?)`, constructor и bindings. Analysis lowering создаёт synthetic CFG
только для canonical analysis; Parser IR сохраняет high-level loop/optional/
left-fold nodes, поэтому synthetic productions не становятся runtime
functions.

Declarative binding DSL production grammar использует:

- `@НовыйУзел` — constructor;
- `Свойство = X` — scalar/optional/token binding;
- `Свойство += X` — append, `Свойство *= X` — extend;
- `Свойство ~= X` — concat, `Свойство ++= X` — increment;
- `-= X` — separator/syntax-only discard;
- `Свойство := Константа` — constant/enum/boolean;
- `Свойство => X` и `Свойство +=> X` — returned-child wrapper/decorator,
  включая prepend seed для dereference после скобок.

Direct productive LR вида `A -> A suffix | base` компилируется как parse base,
затем canonical-dispatched loop. На каждой итерации constructor получает
предыдущий результат как левый scalar binding, разбирает suffix и заменяет
accumulator. Это обеспечивает левую ассоциативность без роста parser stack;
precedence остаётся структурой уровней grammar.

Approved design: [grammar/query model optimization](../specs/2026-08-07-grammar-query-model-optimization-design.md).

## 4. Formal constraints

- тело `*`/`+` обязано быть productive, non-nullable и гарантированно
  потреблять минимум один token; nullable repetition отклоняется до codegen;
- тело `?` обязано быть productive и не быть уже nullable;
- arbitrary actions внутри EBNF и direct LR запрещены;
- direct LR требует хотя бы одну base alternative;
- каждый recursive suffix обязан гарантированно потреблять input;
- semantic direct LR требует ровно constructor и scalar accumulator binding;
- indirect/nullable-prefix LR в первой версии unsupported и диагностируется;
- альтернативы каждого canonical decision обязаны иметь disjoint SELECT(k).
  Порядок `Если` никогда не используется для разрешения конфликта;
- production `k=2`. Уникальный FIRST(1) может использоваться только как
  доказанно безопасная оптимизация; общие префиксы проверяются полным
  canonical SELECT(2);
- grammar, конфликтная при настроенном конечном `k`, отвергается. Сам generator
  поддерживает другой настроенный `k`; production grammar не повышалась выше 2.

## 5. Legacy compatibility report

Остаются как отдельный migration compatibility layer:

- `build_legacy_matcher_artifact`;
- final normalized-row artifact representation;
- `find_runtime_dispatch_conflicts`;
- old/hybrid backend fixtures и parity tests.

Runtime conflict checker использует те же окончательно нормализованные rows,
которые образуют artifact; отдельной approximate trie semantics нет. Current
legacy audit: 10 615 rows, 0 runtime conflicts.

Legacy matcher не является canonical LL(k) и не считается
language-preserving. Зафиксированный adversarial contract:

```text
A -> a B | a b d
B -> epsilon | b c
input: a b c
```

CFG допускает input через `a B`, а legacy longest-prefix может выбрать
competing `a b d` и отвергнуть его.

Production parser больше не зависит от legacy artifact, shadowing,
cycle-prefix injection, nullable fallback или longest-prefix dispatch. Empty
SELECT metadata artifact пока сохраняет EDT layout, но runtime его не читает.
Окончательное удаление legacy допустимо после intentional retirement старого
standalone/hybrid compatibility contract и его внешних consumers; production
migration больше не является препятствием.

## 6. Grammar/model migration

- manual continuation/list/optional productions migrated coherent families;
- arithmetic, comparison и logical expression tails заменены direct LR;
- lists, separators, optionals, UNION, JOIN, dereference и query tails используют
  EBNF/bindings;
- расширение СКД после `ИНДЕКСИРОВАТЬ ПО` декларативно добавляет отборы в
  `Операторы[0].ОтборыСКД`; characterization test закрывает потерю результата,
  возникшую при замене старого parameter-side-effect на discard binding;
- технический `ИсточникиЗапроса.Элементы` и UUID JOIN-link удалены;
- builder возвращает отсоединённое JOIN-поддерево в корни, поэтому изменение
  владельца связи и перевод источника обратно в корневые таблицы не теряют узлы;
- Query Constructor корректно обрабатывает запрос уничтожения без коллекции
  колонок, а Universal Report сохраняет преобразованные executable views внутри
  вложенного `ВТФильтр` при формировании СКД;
- production grammar содержит 66 source productions вместо 124; число 66
  включает semantic decorator `РазыменованиеПослеСкобок`, а не continuation
  plumbing;
- production runtime полностью canonical, без legacy islands.

## 7. Semantic actions

| Metric | Before | After |
| --- | ---: | ---: |
| Action blocks | 398 | 0 |
| Action statements | 431 | 0 |
| Constructor statements inside action blocks | 102 | 0 |
| Collection statements | 37 | 0 |
| Constant statements | 33 | 0 |
| Structural statements | 254 | 0 |
| Other statements | 5 | 0 |

Constructors и structural building теперь declarative directives, поэтому
они не учитываются как arbitrary semantic actions. Remaining non-constructor
actions: **0**; специальных исключений и оправданий нет.

## 8. Structural metrics

| Metric | Before | After |
| --- | ---: | ---: |
| Source productions | 124 | 66 |
| Source alternatives | 281 | 144 |
| Explicit source epsilon alternatives | 63 | 1 |
| Formal parameters / actual arguments | 8 / 26 | 0 / 0 |
| `Родитель` / `ЛевыйЭлемент` in source grammar | used as plumbing | 0 / 0 |
| Lowered CFG productions | 124 | 156 |
| Lowered CFG alternatives / epsilon | 281 / 63 | 334 / 80 |
| Generated BSL LOC | 3 394 | 1 954 |
| Generated functions / procedures / routines | 135 / 6 / 141 | 77 / 5 / 82 |
| Generated `НеТерминал*` functions | 124 | 66 |
| Generated production SELECT rows | 11 273 | 0 |
| Legacy matcher audit rows | 11 273 | 10 615 |

After canonical analysis: 12 182 packed FIRST rows, 61 150 packed FOLLOW rows,
334 SELECT descriptors, 11 810 direct SELECT facts; concrete/cartesian public
SELECT materializations remain 0. Canonical conflicts and diagnostics are
empty at `k=2`.

## 9. Runtime benchmark

Один и тот же YAxUnit harness, runtime 1C 8.3.27.2170, Windows x86-64,
3 warm-ups и 20 samples:

| Corpus | Median before -> after | p95 before -> after |
| --- | ---: | ---: |
| 42 QueryExamples | 1679.5 -> 862.5 ms (-48.6%) | 2030 -> 918 ms (-54.8%) |
| Large package | 161.5 -> 95 ms (-41.2%) | 195 -> 97 ms (-50.3%) |
| Long field list | 161.5 -> 83 ms (-48.6%) | 192 -> 92 ms (-52.1%) |
| JOIN chain | 68.5 -> 55.5 ms (-19.0%) | 80 -> 88 ms (+10.0%) |
| UNION chain | 96.5 -> 41.5 ms (-57.0%) | 125 -> 49 ms (-60.8%) |
| Arithmetic chain | 65.5 -> 48.5 ms (-26.0%) | 96 -> 64 ms (-33.3%) |
| Logical chain | 77 -> 55 ms (-28.6%) | 109 -> 64 ms (-41.3%) |
| Dereference chain | 20 -> 13 ms (-35.0%) | 32 -> 20 ms (-37.5%) |

Median уменьшилась на всех восьми corpus. p95 уменьшился на семи; JOIN p95
в одном финальном повторном прогоне вырос на 10.0% при улучшении median на
19.0%, поэтому это значение явно оставлено как наблюдаемая вариативность.

`dispatch_calls = 0`. Call/depth/constructor/allocation counters оставлены
`null` с явными причинами: дорогая production instrumentation не добавлялась.
Code-shape и long-chain tests отдельно доказывают loops/left folds без
synthetic recursive runtime functions. Полные данные:
[after benchmark](2026-08-08-runtime-parser-benchmark-after.md).

## 10. Automated evidence

- Python: 508 passed, 1 skipped, 4 558 subtests;
- `parsergen validate`: exit 0;
- `parsergen generate --check`: artifacts current;
- canonical conflict/diagnostic lists: empty at `k=2`;
- legacy normalized-row parity/runtime conflicts: green, 10 615 rows;
- parser YAxUnit (lexer, expression parser, full-query parser): 365/365 GREEN;
- combined parser/downstream/benchmark YAxUnit: 494 total / 491 passed /
  3 documented skips;
- benchmark YAxUnit: 1/1 GREEN;
- EDT exact revalidation of parser and changed test modules: no errors;
- generated parser/reference artifact parity: green;
- generated parser SHA256:
  `537939b79bc29d77d581b8148973595481f444c1415b082d032e461133736b45`.

## 11. Manual verification

Финальный интерактивный gate выполнен пользователем:

- полный Vanessa-набор прошёл;
- изменение владельца JOIN проверено в Query Constructor;
- удаление источников проверено в Query Constructor;
- формирование Universal Report после исправления вложенного executable view
  передано на повторную прикладную проверку.

## 12. Remaining limitations

- indirect и nullable-prefix left recursion не поддерживаются;
- legacy compatibility APIs и hybrid fixtures пока остаются, но production
  parser от них не зависит;
- два Query Constructor tree contracts требуют настоящих form data objects для
  headless-вызова; интерактивный Vanessa gate при этом пройден;
- один manager SKD contract заблокирован существующим именем свойства
  `.ОписаниеФильтра` вместо `.ОписаниеВТФильтр`;
- internal runtime call/depth/allocation counters не измерены, чтобы не
  оставлять expensive instrumentation в production.

## Финальный архитектурный критерий

Source grammar больше не содержит значимого объёма структуры ручной
LL-нормализации: continuation plumbing для migrated families удалён,
`Родитель`/`ЛевыйЭлемент` и arbitrary actions равны нулю. Query source model
предметная, production parser canonical, а legacy остаётся изолированным
тестируемым compatibility layer, кандидатом на отдельное удаление.
