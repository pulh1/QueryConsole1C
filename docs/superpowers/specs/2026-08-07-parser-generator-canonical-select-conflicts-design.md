# Разделение canonical SELECT и legacy runtime dispatch

## Цель

Сделать поиск конфликтов и диагностику `LLK202` математически согласованными
с canonical LL(k)-анализом, не меняя алгоритмы `nullable`, `FIRST`, `FOLLOW`,
`SELECT`, проекционную оптимизацию FOLLOW и существующие production-артефакты
BSL runtime.

После изменения результат canonical conflict scan не должен зависеть от того,
хранится `AnalysisResult.select` в compressed или materialized форме. Любая
legacy-семантика выбора альтернатив по наиболее длинной строке должна быть
вынесена в отдельно названный API и не использоваться как доказательство
LL(k)-корректности.

## Подтверждённый дефект

Для грамматики:

```text
<S> ::= <A>
<A> ::= a <B> | a b d
<B> ::= ПУСТО | b c
```

при `k = 2` canonical-анализ вычисляет:

```text
SELECT₂(A → a B)   = {("a", "$"), ("a", "b")}
SELECT₂(A → a b d) = {("a", "b")}
```

Canonical intersection содержит witness `("a", "b")`. Текущая compressed
ветка `find_select_conflicts` возвращает пустой результат, а эквивалентный
materialized `AnalysisResult` находит конфликт.

Причина: compressed scanner использует `_runtime_trie`, построенный только из
`descriptor.direct + descriptor.prefixes`, тогда как canonical SELECT для
короткого завершённого prefix должен продолжаться через `FOLLOW(owner)`.
Materialized scanner сравнивает полные canonical SELECT и поэтому имеет другую
семантику.

Generated legacy artifact для `A` содержит строки `("a",)` для первой
альтернативы и `("a", "b")` для второй. Runtime ищет наиболее длинную точную
строку, выбирает вторую альтернативу на `a b c` и затем отвергает `c`, ожидая
`d`, хотя CFG принимает `a b c` через `A → a B → a b c`. Это подтверждено
исполнением реально сгенерированной таблицы через точную транскрипцию BSL
lookup и независимым перечислением терминальных цепочек CFG. Запуск
произвольного generated BSL в информационной базе не входит в изменение,
поскольку в репозитории отсутствует такой test harness.

## Формальные контракты

### Canonical conflict detection

Для альтернативы `A → α` используется только canonical множество:

```text
SELECT_k(A → α) = FIRST_k(α FOLLOW_k(A))
```

Две альтернативы конфликтуют тогда и только тогда, когда их concrete canonical
SELECT-множества имеют непустое точное пересечение. Witness выбирается
детерминированно: сначала минимальная длина, затем лексикографический порядок.

`find_select_conflicts` получает canonical семантику. Дополнительно вводится
явное имя `find_canonical_select_conflicts`; старое имя остаётся canonical
совместимым alias. Результаты compressed и materialized путей обязаны
совпадать.

### Legacy runtime dispatch

Текущий BSL runtime использует отдельный контракт:

- exact matcher rows;
- поиск от наиболее длинной доступной строки к короткой;
- nullable fallback;
- legacy cycle prefixes;
- удаление длинных строк, shadowed коротким prefix той же альтернативы.

Эта семантика сохраняется в `find_runtime_dispatch_conflicts` и
`build_legacy_matcher_artifact`. Существующий `build_select_matcher_artifact`
остаётся compatibility-wrapper, но production codegen вызывает явное legacy
имя. Отсутствие collision в runtime rows не считается доказательством
сохранения языка или LL(k)-корректности.

## Symbolic canonical intersection

Concrete Cartesian materialization для compressed scan запрещена. Алгоритм
работает по произведению существующих factorized automata:

1. Начальные состояния альтернатив строятся через `_descriptor_state`, который
   представляет `direct ∪ truncate_k(prefix · FOLLOW(owner))`.
2. Пара состояний и остаток бюджета образуют memoized work item
   `(left_state, right_state, remaining)`.
3. При `remaining == 0` текущий prefix является witness: насыщение длины `k`
   обрезает продуктивные продолжения.
4. Если оба состояния terminal, текущий короткий prefix является witness.
5. Иначе перебираются пары matcher-переходов; продолжаются только пары с
   непустым concrete пересечением token-классов.
6. Если terminal только одно состояние, поиск по descendants продолжается:
   factor state может одновременно представлять короткие и длинные слова.
7. Из найденных кандидатов выбирается минимум по `(len(word), word)`.

Существующие `_children`, `_terminal`, `_intersection`, factor graphs и tries
переиспользуются. Сложность ограничена числом достижимых состояний произведения
и локальными парами переходов при глубине не более `k`, а не размером concrete
Cartesian product matcher-классов.

Одноразовый прототип совпал с независимым materialized oracle на 200 случайных
грамматиках при `k = 1..3` без расхождений и без materialization SELECT.

## Validation

`LLK202` основывается только на canonical conflict scan. Существующее
подавление пары, в которой ровно одна альтернатива nullable, удаляется: nullable
fallback является legacy runtime policy и не может скрывать canonical
SELECT-intersection.

Фильтры недостижимых и уже невалидных альтернатив сохраняются. Отдельная
диагностика runtime-dispatch contract в эту задачу не добавляется, потому что
collision-free matcher rows недостаточны для доказательства language
preservation.

## Production-грамматика

Exact symbolic scan текущей repository grammar при `k = 2` и точках входа из
`parsergen.toml` находит два ранее скрытых canonical-конфликта:

```text
ЛогическийОператор, alternatives 2/5:
    ("ССЫЛКА", "АВТОУПОРЯДОЧИВАНИЕ")

ОперандВ, alternatives 1/2:
    ("ВЫБРАТЬ", "*")
```

Грамматика в этой задаче не изменяется, конфликты не подавляются. Поэтому
`parsergen validate` и `parsergen generate --check` после исправления должны
завершаться с кодом `1` и двумя `LLK202`. Это ожидаемый честный результат, а
не регрессия generated artifacts. Прямой codegen и reference-artifact tests
должны подтвердить неизменность legacy BSL и таблиц там, где они генерируются
без CLI validation gate.

## Invariant `complete`

У `_ContinuationFirst` флаг packed fact имеет точный контракт:

- при `length < budget` значение `True` означает, что вариант может завершить
  это короткое слово и внешний RHS может продолжить анализ;
- при `length == budget` значение семантически не используется и может быть
  `False`, даже если существует полная деривация с тем же насыщенным prefix.

Например, для `<X> ::= a <N>`, `<N> ::= ПУСТО`, `k = 1` допустим внутренний
fact `(1, packed("a"), False)`, при этом `FIRST(X) = {("a",)}` и SELECT
корректны. Алгоритм не меняется; контракт документируется рядом с типом fact и
закрепляется regression test.

## Проверка

Реализация выполняется через TDD и включает:

1. Заданный FOLLOW-derived контрпример с witness `("a", "b")`.
2. Равенство canonical conflicts для compressed и materialized
   `AnalysisResult`.
3. Nullable alternative против consuming alternative.
4. Strict-prefix слова: точное canonical пересечение не смешивается с legacy
   shadowing; terminal factor state с descendants продолжает обход.
5. Пересекающиеся identifier matcher classes.
6. Запрет public SELECT expansion и concrete Cartesian materialization в
   compressed scan.
7. Детерминированный witness.
8. Property/oracle test на малых случайных грамматиках при `k = 1..3`.
9. Исполнение legacy generated table на контрпримере с фиксацией известного
   расхождения CFG и runtime.
10. Regression для saturated `complete=False`.
11. Production regression: ровно два canonical conflicts и отдельно отсутствие
    изменения legacy artifact/runtime contract.
12. Полный `tools/parsergen` test suite, `validate` и `generate --check` с
    документированными ожидаемыми production diagnostics.

## Границы изменения

- Не переписывать `nullable`, FIRST, FOLLOW или SELECT.
- Не убирать и не ослаблять projection optimization FOLLOW.
- Не материализовывать concrete SELECT ради conflict scan.
- Не менять `tools/parsergen/grammar/query-language.grammar`.
- Не менять production BSL parser и templates ради устранения диагностик.
- Не объявлять legacy longest-match language-preserving без отдельного
  доказательства или проверки.
- Поддержка левой рекурсии и оптимизация production-грамматики остаются
  отдельными следующими задачами.
