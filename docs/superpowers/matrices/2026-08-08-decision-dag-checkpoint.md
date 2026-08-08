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
отдельную runtime-функцию `НеТерминалЛогическийОператор`.

## Static before/after

Источники: `2026-08-08-decision-dag-static-before.json` и
`2026-08-08-decision-dag-static-after.json`.

| Метрика | Before | After | Изменение |
| --- | ---: | ---: | ---: |
| `ТипТокенаПросмотра` в generated BSL | 1 983 | 132 | −93,3% |
| Runtime functions | 77 | 74 | −3 |
| `НеТерминал*` functions | 66 | 63 | −3 |
| Nonterminal call sites | 179 | 176 | −3 |
| Generated BSL LOC | 1 954 | 2 460 | +25,9% |
| Decision lines | 243 | 375 | +54,3% |
| Predicate atoms | 1 981 | 3 783 | +91,0% |
| Max condition characters | 6 407 | 2 551 | −60,2% |
| Max condition predicate atoms | 170 | 88 | −48,2% |
| Max lookahead calls in one condition | 170 | 1 | −99,4% |
| Max condition nesting | 8 | 2 | −75,0% |

Decision DAG содержит 33 718 symbolic source states, 415 runtime DAG states,
89 shared states, 112 decision regions и максимальную глубину lookahead 2.
Public SELECT expansions и Cartesian materializations равны нулю.

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
  conflicts empty, changed artifacts empty;
- full Python suite: 568 passed, 1 skipped, 27 735 subtests passed; skip —
  недоступное создание Windows symlink без соответствующей privilege;
- EDT revalidation: `DataProcessor.Парсер` и два изменённых YAxUnit common
  modules найдены и провалидированы; scoped ERRORS — 0;
- YAxUnit functional gate: 373 passed, 0 failed, 0 errors, 0 skipped;
- benchmark registration намеренно не запускалась.

## Следующий gate

Перед окончательным runtime benchmark отдельно возвращается прежний lifecycle:
новый parser object на каждый corpus, создание вне preflight/calibration/
warmup/samples. Состав и содержимое corpus не меняются. Непосредственно перед
измерительным запуском требуется подтверждение пользователя после остановки
тяжёлых процессов.
