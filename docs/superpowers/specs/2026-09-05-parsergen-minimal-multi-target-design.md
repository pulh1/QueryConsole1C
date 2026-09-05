# Минимальная многотаргетная архитектура parsergen

**Статус:** согласованное направление, ожидает проверки письменной спецификации
**Дата:** 2026-09-05
**Репозитории:** `QueryConsole1C`, `onec-interactive-runtime`

## 1. Цель

Вернуть parsergen к простой универсальной архитектуре и сохранить только две
реально используемые возможности, появившиеся в ходе исследования hot reload:

1. автоматическое устранение допустимой хвостовой и правой рекурсии;
2. генерацию нескольких целевых языков из одного общего представления.

Итоговый основной конвейер:

```text
combined .grammar с одной семантикой
  → SourceGrammar
  → LoweringResult и разрешённая grammar
  → FIRST/FOLLOW/SELECT и validation
  → общий ParserIr и semantic optimizer
  → общий RecursionPlan
  ├─ canonical BSL renderer
  └─ direct Python renderer
```

Parsergen не знает о Worker, hot reload, общих модулях 1С или конкретных
именах продукций BSL. Несколько entrypoints остаются допустимыми: это несколько
корней одной grammar, а не несколько вариантов семантики.

## 2. Причина изменения

Разделение syntax grammar и semantic profiles, а затем `AppendNearestOwner`
были добавлены ради компактной Worker projection. Production hot reload уже
переведён на полный AST и достиг целевого времени. Отдельная projection больше
не используется, а её инфраструктура:

- расширяет публичную модель parsergen;
- добавляет owner stacks и отложенные effects в generated Python parser;
- усложняет validation, lowering, IR и оба renderer;
- из-за одного `AppendNearestOwner` отключает преобразующие оптимизации всего IR.

Сохранять эту сложность без production consumer не требуется.

## 3. Проверенная база

История коммитов используется как карта происхождения изменений, а не как
обязательная последовательность механических revert.

- `0f0b17d` — Python semantic AST target поверх canonical IR до multiple
  profiles. Это архитектурная база, к которой нужно приблизиться.
- `93c0f77` — добавление separated syntax/semantic profiles. Функциональность
  удаляется.
- `224fdf6`, `e617568`, `e8724fb`, `c5aa59e`, `2e69413`, `2dc7703`,
  `5686bef`, `9cfaf05`, `dfb75e9`, `8c59967`, `7b80d56` — scoped value,
  `AppendNearestOwner`, owner runtime и связанные исправления. Эти изменения
  удаляются по смыслу.
- `7d92de9`, `fe39924`, `9bf0992`, `b74c910`…`99a20f1`, `482f35d`,
  `9433718`, `c0d1f50`, `9647a99`, `fb04ea4`, `33870c8`, `ad17dc1`,
  `3c4c94c`, `f18579e`, `cef2443` — direct target, liveness, result flow,
  continuations и общие исправления рекурсии. Они сохраняются без scoped
  coupling.
- `a012492` — исправление утечки полей continuation, discarded result и
  constant suffix после recursive call. Commit сохраняется целиком.

Если возврат файла к более ранней версии проще и надёжнее ручного удаления,
это допустимо. После возврата переносятся только доказанные общие улучшения,
каждое с отдельным regression test.

## 4. Что удаляется

### 4.1. Multiple semantics и separated frontend

Удаляются публичные понятия и API:

- `SyntaxGrammar` и связанные syntax-only модели;
- `SemanticProfile` и возможность нескольких profiles для одной grammar;
- anchors и cross-file binding;
- `parse_syntax_grammar`;
- `parse_semantic_profile`;
- `bind_semantic_profile`.

Удаляются файлы parsergen:

- `syntax_grammar_parser.py`;
- `semantic_profile_parser.py`;
- `semantic_profile_binding.py`;
- `separated_model.py`.

Основным и единственным authoring format снова становится combined `.grammar`,
где syntax и semantic actions находятся в одном файле.

### 4.2. Scoped append и Worker projection

Удаляются:

- `SemanticScopedAppend`;
- `SourceScopedValue`;
- `AppendNearestOwner`;
- `scoped_append_validation.py`;
- owner type discovery;
- owner stacks и owner state classes;
- deferred queues и enqueue sequence;
- scoped-effect propagation;
- scoped cleanup в generated parser;
- scoped branches из validation, lowering, IR, optimizer и renderers;
- глобальный optimizer barrier;
- scoped-only tests и действующая scoped документация.

Обычные `AppendCollection` и `ExtendCollection` сохраняются: они заполняют
поле текущего AST-узла и не ищут внешний owner.

### 4.3. Runtime Worker parser

В `onec-interactive-runtime` удаляются:

- `bsl-worker-reload.semantic`;
- отдельная генерация Worker parser;
- committed `generated_worker_semantic_parser.py`;
- Worker parser exports;
- Worker-specific profile tests и benchmarks.

`full_ast_worker_projection.py` не удаляется только из-за имени. Функция
`project_full_ast_module` является production extractor полного AST в модель
hot reload, а не отдельным parser или semantic profile.

### 4.4. Legacy и hybrid BSL codegen

Реальный поиск production consumers показал, что единственная поставляемая
grammar языка запросов уже полностью canonical: все 66 productions входят в
canonical path. Runtime использует Python target. Произвольные inline BSL
actions встречаются только в тестах и исторической миграционной документации.

По решению пользователя обратная совместимость этого неиспользуемого legacy
API больше не является требованием. Удаляются:

- `bsl_codegen.py` и `BslGenerator`;
- `semantic_actions.py` и compiler произвольных inline BSL actions;
- `hybrid_bsl_codegen.py`;
- migration selection `canonical_productions` из config, CLI и
  `parsergen.toml`;
- legacy/hybrid tests и migration audit, не проверяющие production canonical
  parser.

`generated_parser.py` сохраняется как нейтральная модель результата генерации
для `artifacts.py`. Canonical BSL renderer должен возвращать эту модель
напрямую, без hybrid adapter.

## 5. Что сохраняется

Сохраняются:

- combined grammar и обратная совместимость её декларативных semantic actions;
- общий `SourceGrammar` и `ParserIr`;
- существующие FIRST/FOLLOW/SELECT и decision DAG;
- специализация, reachability и path-fact optimizations;
- canonical BSL target;
- direct procedural Python target без runtime VM;
- ordinary bindings, constructors, wraps, folds, repeats, constants и spans;
- несколько entrypoints одной grammar;
- общие cardinality, liveness, result-flow и continuation fixes;
- точные diagnostics и error tuples.

Public generator после cleanup не должен содержать второй Python execution
engine. Direct renderer остаётся единственным production Python target.

Canonical BSL renderer становится единственным BSL target. В parsergen после
cleanup существует ровно два renderer: один для BSL и один для Python.

## 6. Общая оптимизация рекурсии

Сейчас решение об итеративном выполнении в основном находится в
`direct_render_analysis.py`. Его нужно превратить в общий immutable
`RecursionPlan`, построенный над финальным `ParserIr` после semantic
optimization.

План содержит ссылки на существующие IR sites, но не копирует operations и не
создаёт второй execution IR:

- точные recursive call sites;
- вид преобразования: простой tail loop или local continuation;
- доказательство продвижения token cursor;
- result disposition и liveness;
- продолжение после вызова, включая допустимые zero-width constants;
- необходимые builder fields, wrap seeds и span starts;
- порядок unwind и freeze.

Оба renderer используют одно решение eligibility и порядка effects. Каждый
renderer отвечает только за синтаксис locals, loops и временного storage
целевого языка.

Не оптимизируются без отдельного доказательства:

- mutual recursion;
- non-tail recursion;
- вызовы без гарантированного продвижения input;
- suffix с неизвестными или переставляемыми side effects.

Обязательные сохранённые regressions:

- 1 500 и 5 000 элементов без зависимости от Python recursion limit;
- alternative fields не протекают между continuation frames;
- discarded self-call не возвращает результат base alternative;
- `AssignConstant` после recursive call выполняется при unwind в исходном
  порядке;
- source spans и collection order не меняются.

## 7. BSL codegen

После cleanup остаётся один BSL renderer — canonical. CLI всегда строит общий
`ParserIr` для полного достижимого production graph и передаёт его canonical
renderer. Переходный список `[migration].canonical_productions` больше не
нужен и удаляется.

Произвольные inline BSL actions намеренно становятся неподдерживаемым legacy
синтаксисом. Combined grammar продолжает поддерживать декларативные semantic
actions: constructors, scalar bindings, collections, wraps, folds, repeats и
constants. Ошибка для raw inline action должна быть ранней и однозначной, до
начала generation.

Удаление legacy/hybrid слоя не разрешает изменение production BSL artifacts.
Canonical renderer уже формирует все 66 productions QueryConsole, поэтому
fresh byte-gate обязан остаться зелёным.

## 8. Миграция runtime на combined grammar

Combined grammar восстанавливается из:

```text
56e64cb^:grammar/bsl-server-strict.grammar
```

Проверенный read-only эксперимент:

```text
parse_grammar
→ resolve_grammar
→ compute_analysis(k=1, шесть entrypoints)
→ build_parser_ir
→ generate_python_semantic_parser
```

дал 63 productions, 0 diagnostics и `module_text`, побайтово совпадающий с
текущей генерацией syntax grammar + full semantic profile:

```text
SHA256(module_text) =
2a239a4851a3fddd35722472e0e18b44b3df9752f5711acac15fdcf3ed3a1264
```

Поэтому семантика не объединяется вручную. Runtime:

- восстанавливает один `bsl-server-strict.grammar`;
- удаляет `bsl-server-strict.syntax.grammar`;
- удаляет `bsl-server-full.semantic`;
- переводит generation tools и development target на `parse_grammar`;
- сохраняет шесть entrypoints, source-span seam и production API;
- меняет manifest с пары syntax/profile hashes на hash combined grammar.

AST spans относятся к входным BSL tokens и должны остаться неизменными.
Изменение имени source-файла в generation diagnostics является ожидаемой
частью migration.

## 9. Побайтовые гейты

Гейты обязаны запускать свежую генерацию. Хеширование только committed файла
через `git show` не доказывает корректность generator.

### 9.1. Парсер языка запросов на 1С

Fresh `ArtifactSet` должен побайтово совпасть с текущим delivery baseline:

| Артефакт | SHA256 fresh bytes |
|---|---|
| `ObjectModule.bsl` | `358a6123f91cd9068a08c76b3849ffad69f10eb0c7b2ed90b650f87304b960e8` |
| `ТаблицаПервыхСимволовВариантов/Template.txt` | `acb80f86f739d5a4a54fe7d6f2c85cdc57a2d664d779a1f1e51a0aaf54a059c1` |
| `ОпределенияИдентификаторов/Template.txt` | `13472cb0e1482b5c590a306fe6fc119d026546069e717d8eadd010b6a8661ef6` |

Committed Git blobs дополнительно сохраняют собственный raw baseline:

```text
ObjectModule: f536869601e718ca02f026d0ecb8f733d8688ecd038f70f6b5e8cd08dbe4fbbf
SELECT:       e26a6b3b4fe08455462145de3243338d5da1c8bbb657321a2162b0abe541e208
Identifiers:  107fdbdefd57f5b6fe0658037b67806fc95f24a27d3e948eeeeaeb3335ffeff2
```

Fresh delivery bytes и Git blobs различаются из-за существующей EOL/serialization
policy. Каждая категория сравнивается со своим baseline без нормализации.
Ни один из трёх BSL-артефактов не получает разрешённого перехода baseline.

### 9.2. Python BSL parser

Pre-cleanup artifact:

```text
onec-interactive-runtime commit: 52b772d
artifact: src/onec_runtime/bsl/generated_semantic_parser.py
SHA256: a15c8e349d6a84215c20b87a97b7fc60d0793ae22a6af488ad01757c57331fd3
parsergen package SHA256:
797a217ad7c20230d0679175d46d7c0e7aadbf7c619eac30a90b3d8f977b71b6
```

Пользователь разрешил одноразовое изменение полного Python artifact, потому
что текущий файл содержит неиспользуемые owner cleanup instructions и hash
всего старого parsergen package. Старое значение package hash нельзя сохранять
как provenance нового package.

Переход допускается только так:

1. зафиксировать pre-cleanup bytes и inputs из Git blobs;
2. отдельно показать точный diff executable code и manifest;
3. доказать semantic AST, spans и error parity;
4. доказать отсутствие owner/profile machinery;
5. зафиксировать новый raw-byte baseline;
6. дважды выполнить независимую fresh generation и получить одинаковые bytes;
7. после перехода любое незаявленное изменение нового baseline блокирует merge.

Нельзя проходить gate копированием старого файла, postprocessing metadata,
нормализацией сравнения или ложным package hash.

## 10. Тестовая стратегия

Удаляются separated/scoped-only suites. Их production-relevant assertions
переносятся в combined grammar tests.

Обязательные проверки parsergen:

- combined grammar с declarative bindings;
- явный диагностический отказ для произвольных inline BSL actions;
- EBNF, multiple entrypoints, wraps, folds, repeats и constants;
- shared recursion plan и consumption обоими targets;
- 1 500/5 000 элементов;
- AST shape, field order, tuple/scalar contracts и exact spans;
- error position, actual, expected и full-consumption errors;
- deterministic direct Python generation;
- fresh exact BSL `ArtifactSet`;
- отсутствие `SemanticProfile`, `AppendNearestOwner`, owner stack и deferred
  queue в source и generated full parser.

Обязательные проверки runtime:

- fresh generation из combined grammar;
- exact semantic/error/span parity с pre-cleanup artifact;
- full AST extractor и hot-reload model parity;
- notebook lowering и module admission tests;
- wheel/import closure без parsergen, grammar sources и COM;
- real ZUP hot-reload gate и измерение p95 после итогового runtime artifact.

Основные команды финальной проверки:

```powershell
python -B -m pytest -p no:cacheprovider tools/parsergen/tests
python -B -m parsergen generate --config parsergen.toml --check
python -B tools/generate_bsl_semantic_parser.py --check-full
```

Raw-byte tests не заменяются последними двумя командами: существующий
`generate --check` использует семантическое сравнение и нормализацию EOL.

## 11. Порядок реализации

Изменения выполняются атомарными commits:

1. добавить честные baseline/fresh-generation tests;
2. сохранить уже готовый `a012492` и его regression tests;
3. вернуть runtime combined grammar и доказать pre-cleanup `module_text` parity;
4. удалить separated/scoped frontend и вернуть базовые source/lowering/IR paths;
5. удалить owner/scoped paths из direct analysis и Python renderer;
6. удалить legacy/hybrid BSL codegen и migration selection, переключить CLI на
   единственный canonical BSL renderer;
7. вынести общий `RecursionPlan` и подключить оба target;
8. обновить runtime generator, manifest и Python artifact одним разрешённым
   transition commit;
9. удалить Worker parser/profile consumers;
10. обновить документацию, версию parsergen и выполнить все gates.

История опубликованного PR не переписывается. Cleanup commits добавляются
поверх готовых direct fixes, затем текущий `master` подмешивается обычным merge.
Force push не требуется.

Каждый этап блокируется при:

- изменении любого из трёх BSL byte baselines;
- изменении AST shape, spans или error tuples;
- возврате `RecursionError` на 1 500/5 000 элементах;
- недостоверном manifest;
- появлении parsergen или COM в runtime wheel/import closure.

## 12. Версионирование и совместимость

Удаление публичного profile API является намеренным breaking change версии
`0.2.0`. Следующая версия parsergen должна быть `0.3.0`, а не повторно
публиковаться как `0.2.0`.

Сохраняется совместимость декларативных combined grammars. Совместимость
consumers, использующих экспериментальные separated profiles, raw inline BSL
actions или migration/hybrid API, намеренно прекращается.

## 13. Документация

Следующие документы помечаются superseded новой спецификацией:

- `2026-09-02-separated-parser-semantics-design.md` и plan;
- `2026-09-03-parsergen-minimal-scoped-append-design.md` и plan;
- Worker projection specs/plans в runtime;
- scoped/profile части direct Python design и plan.

Исторические benchmark и review evidence не удаляются и не переписываются.
Они получают ссылку на эту спецификацию и остаются воспроизводимым объяснением
принятого решения.

## 14. Критерии готовности

Работа готова только если одновременно выполнено следующее:

- один combined authoring frontend;
- один общий `ParserIr`;
- один общий `RecursionPlan`;
- один canonical BSL renderer и один direct Python renderer;
- direct Python и canonical BSL targets используют общий план;
- multiple profiles и scoped append отсутствуют;
- `bsl_codegen.py`, `semantic_actions.py`, `hybrid_bsl_codegen.py` и
  `canonical_productions` отсутствуют;
- QueryConsole fresh BSL artifacts побайтово неизменны;
- Python artifact прошёл явно разрешённый одноразовый transition и получил
  новый воспроизводимый byte baseline;
- parsergen и runtime suites зелёные;
- реальный ЗУП hot reload остаётся в пределах p95 `< 2,5 с`;
- финальное независимое Astra-review возвращает `READY`.
