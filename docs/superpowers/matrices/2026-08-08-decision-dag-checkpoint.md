# Canonical Decision DAG production checkpoint

## Результат

Production parser сгенерирован через pipeline
`factorized canonical SELECT → validated symbolic Decision DAG → optimized
Parser IR → direct BSL`. Runtime не содержит объектов DAG, таблиц переходов
или helper-функций для отдельных decision nodes.

Canonical alternatives остаются pairwise-disjoint. `Optional`, `Repeat` и
`LeftFold` используют те же outcomes `alternative | exit | error`; branch
order, longest-match, priority и nullable fallback не разрешают конфликт.
Caller/callee specialization сохранила semantic action traces и устранила
отдельную runtime-функцию `НеТерминалЛогическийОператор`. Доказанные факты
пути живут только в optimized Parser IR после связывания canonical outcome с
action, а не в canonical leaves. Для доказанного terminal generated BSL
сдвигает token buffer без повторной проверки типа токена.

## Static before/after

Источники: `2026-08-08-decision-dag-static-before.json` и
`2026-08-08-decision-dag-static-after.json`.

| Метрика | Before | After | Изменение |
| --- | ---: | ---: | ---: |
| `ТипТокенаПросмотра` в generated BSL | 1 983 | 130 | −93,4% |
| Runtime functions | 77 | 74 | −3 |
| `НеТерминал*` functions | 66 | 63 | −3 |
| Nonterminal call sites | 179 | 180 | +1 |
| Generated BSL LOC | 1 954 | 2 463 | +26,0% |
| Decision lines | 243 | 366 | +50,6% |
| Predicate atoms | 1 981 | 3 779 | +90,8% |
| Max condition characters | 6 407 | 2 551 | −60,2% |
| Max condition predicate atoms | 170 | 88 | −48,2% |
| Max lookahead calls in one condition | 170 | 1 | −99,4% |
| Max condition nesting | 8 | 2 | −75,0% |

Decision DAG содержит 33 659 symbolic source states, 406 runtime DAG states,
89 shared states, 109 decision regions и максимальную глубину lookahead 2;
generated control flow содержит 310 emitted predicates. Относительно прошлого
checkpoint устранены три вложенных decision regions: поэтому одновременно
уменьшились `source_states` на 59, `dag_states` на 9 и
`emitted_predicates` на 6. Это результат специализации executable paths, а не
изменение canonical SELECT semantics. Public SELECT expansions и Cartesian
materializations равны нулю.

Optimized Parser IR содержит 6 специализированных executable paths и 11
known-symbol consumes; повторных validation predicates после commit нет.

Рост LOC и общего числа простых сравнений — осознанный результат прямого
structured control flow и cached lookahead. Runtime timing определит, окупает
ли уменьшение повторных lookahead-вызовов этот размер; статические метрики сами
по себе performance verdict не задают.

## Диагностика invalid EBNF exit

Первый YAxUnit gate обнаружил две несовместимости текста ошибок: explicit DAG
error возникал раньше downstream terminal и сообщал общее «Ожидается следующий
токен». Корень — codegen игнорировал уже вычисленный `ImmediateError.expected`.

Исправление не возвращает legacy fallback: для небольшого canonical expected
union generated parser сообщает точный детерминированный список допустимых
токенов. Например, незавершённый `ВЫБОР` ожидает `ИНАЧЕ`, `КОГДА` или `КОНЕЦ`,
а незакрытый список расширения СКД — `,` или `}`. Для больших token sets
остаётся компактная production-level диагностика, чтобы не раздувать BSL.

## Verification

- repository import: `tools/parsergen/src/parsergen/__init__.py`;
- `parsergen validate`: exit 0;
- `parsergen generate --check`: exit 0, artifacts current;
- migration audit: canonical conflicts/diagnostics empty, legacy runtime
  conflicts empty, changed artifacts empty, SELECT expansions/materializations
  equal zero;
- production/reference SHA-256:
  `358A6123F91CD9068A08C76B3849FFAD69F10EB0C7B2ED90B650F87304B960E8`;
- full Python suite: 578 passed, 1 skipped, 27 756 subtests passed; skip —
  недоступное создание Windows symlink без соответствующей privilege;
- EDT revalidation: `DataProcessor.Парсер` найден и провалидирован; scoped
  ERRORS — 0. Существующий фон `QueryConsoleZUP`: 36 errors, 4 blocker,
  1 critical, 168 major, 1122 minor, 1 trivial;
- YAxUnit functional gate трёх parser-модулей: 232 passed, 0 failed, 0 errors,
  0 skipped;
- runtime и lexer benchmarks намеренно не запускались.

## Следующий gate

Перед окончательным runtime benchmark отдельно возвращается прежний lifecycle:
новый parser object на каждый corpus, создание вне preflight/calibration/
warmup/samples. Состав и содержимое corpus не меняются. Непосредственно перед
измерительным запуском требуется подтверждение пользователя после остановки
тяжёлых процессов.
