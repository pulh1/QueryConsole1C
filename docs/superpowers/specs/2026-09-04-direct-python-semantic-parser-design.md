# Прямой Python-target семантического parsergen

## 1. Контекст и цель

Текущий `generate_python_semantic_parser()` сериализует `ParserIr` в таблицы
`PRODUCTIONS` и `DECISIONS`, а сгенерированный модуль интерпретирует их через
универсальную task VM. На двух реальных больших общих модулях ЗУП это даёт
примерно 20 млн вызовов Python для 108 542 токенов. Медиана только generated
parse составляет около 1,8 с, semantic parse вместе с построением модели —
около 2,2–2,3 с.

Основная стоимость создаётся не полезными AST-узлами, а интерпретацией
неизменного `ParserIr`: `_run_sequence`, `_run_operation`, `_decide`,
`_deliver`, `_start_call`, созданием `_Frame` и миллионами операций со стеком
задач.

Цель — генерировать из того же оптимизированного `ParserIr` обычные
Python-функции с прямыми вызовами, `if` и `while`. Production-артефакт не
содержит VM, таблиц операций или зависимости от parsergen. Это универсальный
Python-target, а не написанный вручную BSL-парсер или специальный hot-reload
индексатор.

## 2. Единственный execution IR и порядок фаз

`ParserIr` остаётся единственным исполняемым представлением. Второй набор
`PlanProduction`, `PlanOperation`, `PlanBranch` или сериализованная копия IR не
вводится.

Порядок фаз фиксируется:

```text
syntax grammar + semantic profile
  → lowering
  → FIRST/FOLLOW/SELECT
  → canonical decision DAG
  → ParserIr
  → optimize_parser_ir
  → DirectRenderAnalysis
  → Python rendering
```

`DirectRenderAnalysis` работает только после `optimize_parser_ir()` и не
изменяет `ParserIr` или decision DAG. Это immutable side tables, адресованные
стабильными путями production/alternative/operation:

- liveness результатов и временных значений;
- constructors, которым нужен mutable owner state;
- безопасные прямые хвостовые вызовы;
- минимальные layouts живого continuation для value-carrying direct right
  recursion;
- in-degree canonical DAG nodes для выбора компактной формы rendering.

Распределение имён локальных переменных остаётся внутри renderer: правила
идентификаторов Python и BSL различаются. `DirectRenderAnalysis` не хранит код,
операторы целевого языка или новое дерево управления.

## 3. Обратная совместимость Python API

Публичные имя, сигнатура и результат сохраняются:

```python
generate_python_semantic_parser(
    source: SourceGrammar,
    parser_ir: ParserIr,
    entrypoints: Mapping[str, str],
) -> GeneratedPythonSemanticParser
```

`GeneratedPythonSemanticParser` остаётся frozen/slotted dataclass ровно с
двумя полями: `module_text` и `ast_schema`.

Сохраняются:

- `GeneratedParser().parse(tokens, entrypoint)`;
- combined grammar и разделённые syntax grammar + semantic profile;
- iterable и indexable token input, включая повторное использование tuple;
- обязательное полное потребление входа;
- повторное использование parser после успеха и ошибки;
- frozen/slotted AST dataclasses, имена классов, порядок полей и `SourceSpan`;
- преобразование collection-полей в tuple;
- правила `type`, `text`, `value` для терминалов, лексем, identifiers и
  constants;
- точный `GeneratedParseError(position, actual, expected)` без token text;
- детерминированный `module_text` при одинаковых входах.

Python `module_text` намеренно меняется: прежний SHA VM-артефакта не является
совместимостью нового target и заменяется новой golden identity. Сам публичный
вызов остаётся единственным; selector backend и вторая публичная функция не
добавляются. Старый VM используется только как временный differential oracle
при разработке и удаляется до финальной поставки.

Parsergen публикует и встраивает в generated module только стабильный backend
identifier, например `python-semantic-direct-v1`. Полный artifact identity ему
не принадлежит: публичный generator уже не имеет raw bytes разделённых syntax
grammar/profile и не знает consumer-specific artifact role.

Canonical artifact builder Onec Interactive Runtime вычисляет полный identity
из точных hashes syntax grammar, semantic profile и parsergen package, backend
ID, ordered entrypoint mapping, lookahead `k`, выбранного production closure,
optimizer/codegen options и artifact role. Manifest сериализуется с
фиксированными именами полей и порядком, затем хешируется SHA-256. Consumer
вставляет manifest/identity в отдельную стабильную generated metadata section,
аналогичную marker seam для `SourceSpan`. Публичная сигнатура parsergen не
расширяется.

Все consumer paths используют одну функцию построения и проверки manifest.
Кэш не может принять VM-артефакт за direct-артефакт или два разных
direct-артефакта одной грамматики.

## 4. Прямая генерация Python

Сгенерированный модуль содержит:

- `SourceSpan`;
- frozen/slotted AST dataclasses;
- `AST_CLASSES` и `NODE_DEFAULTS` как reflection metadata;
- `GeneratedParseError`;
- `GeneratedParser`;
- по одной прямой функции/методу на production;
- небольшой runtime для token cursor, lookahead и формирования ошибки.

`AST_CLASSES` и `NODE_DEFAULTS` не являются mutable dispatch API. Parser
вызывает сгенерированные классы прямо; мутация reflection tables не меняет его
поведение. Fault-injection tests подменяют сам class symbol или отдельный
test-only hook, а не metadata.

Сгенерированный модуль не содержит:

- `PRODUCTIONS`, `DECISIONS` или сериализованный `ParserIr`;
- `_Frame`, task tuples и continuation task stack;
- `_run_sequence`, `_run_operation`, `_deliver`, `_start_call`;
- imports из parsergen;
- COM, notebook, BSL-runtime или hot-reload знания.

Каждая production исполняется прямым кодом. Alternative рендерится как
`if`/`elif`, optional — как `if`, `RepeatLoop` и `LeftFold` — как `while`,
nonterminal — как прямой вызов. Допускается один компактный consume-вызов на
реально потреблённый токен. Отдельного helper-вызова на semantic operation,
доставку значения или шаг последовательности нет.

Простой tree-shaped DAG разворачивается в structured `if`. Shared DAG node с
несколькими входящими рёбрами рендерится ровно один раз через локальный
decision-state block, поэтому DAG не превращается в экспоненциальное дерево.
Группировка выполняется только по одному canonical target node. Нельзя
объединять ветви только по одинаковому outcome: `BranchIr.path_facts` могут
выбирать разные специализированные operations.

Renderer использует точные `CanonicalDecision`, `BranchIr.path_facts`,
committed outcomes и `node.expected` готового `ParserIr`. Он не пересортировывает
expected set и не реконструирует решения по grammar source.

## 5. Хвостовая рекурсия без изменения DAG

Грамматика BSL и её рекурсивные `БлокКода`/`ЭлементыМодуля` в этой поставке не
переписываются. Полный AST сохраняет `CodeBlock(First, Rest)` и
`ModuleElements(Item, Rest)`; существующие consumers менять не требуется.

`DirectRenderAnalysis` отмечает прямой self-call как безопасный tail call,
только если:

- вызов находится на всех оставшихся путях в конце alternative/region;
- после него нет явного или неявного continuation;
- activation не содержит constructor, который после вызова ещё должен
  вычислить span, применить pending effects, freeze или вернуть созданный узел;
- нет незавершённого wrap, fold, collection accumulator, live receiver или
  другого состояния, которое должно пережить вызов;
- результат вызова discarded либо непосредственно является результатом
  production;
- переход не пересекает открытие/закрытие owner и не меняет scoped ordering.

Один только discarded result недостаточен: если до рекурсивного вызова был
создан обычный AST builder, его implicit freeze является continuation и
запрещает tail-loop.

Такой вызов renderer превращает в следующую итерацию `while`, не меняя
production decision DAG. Существующий gate с 5 000 шагами прямой правой
рекурсии и неизменным `sys.getrecursionlimit()` сохраняется.

Рекурсивный вызов, результат которого нужен для последующей сборки linked AST,
не является безопасным tail call. Для direct right-recursive production он
исполняется через production-local continuation stack. В stack записывается
только живое состояние, необходимое после возврата callee: значения полей,
начало span, незавершённый builder/wrap и точка продолжения этой production.
Generic IR operations, decision frames и произвольные task tuples туда не
попадают.

Разбор идёт итеративно до base alternative, после чего continuation stack
сворачивается в обратном порядке. Freeze, spans, errors и linked result
получаются в том же порядке, что у рекурсивного исполнения. Stack является
специализированным кодом одной recursive production, а не общей VM и не
per-operation dispatcher. Mutual recursion, для которой такой локальный
контракт нельзя доказать, остаётся обычными вызовами и не маскируется как tail
optimization.

В Worker profile значения рекурсивных `rest` discarded, поэтому длинные
последовательности инструкций и элементов модуля попадают в безопасный
tail-loop. Worker продолжает строить компактную модель `Module → Methods`, а не
linked full AST.

## 6. Семантическое состояние и scoped append

Обычный constructor строится из локальных переменных production-функции:
scalar начинается с `None`, collection — с list, concat — с пустой строки,
increment — с нуля. При возврате создаётся frozen dataclass, collection-поля
замораживаются в tuple.

Общий словарный `_Builder` для каждого узла не используется. Mutable builder
генерируется только для constructor, являющегося owner хотя бы одного
`AppendNearestOwner`. Для каждого реально используемого owner-типа создаётся
отдельный typed/slotted stack.

Scoped effect не выполняет немедленный append. При разборе один раз
захватываются ближайший owner и payload, после чего записывается pending entry:

```text
(source_order, enqueue_sequence, property, payload)
```

Перед freeze owner entries сортируются по `(source_order, enqueue_sequence)` и
применяются ровно один раз. Это сохраняет порядок semantic profile независимо
от вложенности grammar calls. Вложенный owner того же точного типа затеняет
внешний; отсутствующий owner означает no-op. Owner снимается до outward
delivery. Общий `finally` очищает stacks, pending queues и sequence после
syntax, append или freeze error, поэтому parser пригоден для следующего parse.

## 7. Scoped-aware оптимизация ParserIr

Текущий `optimize_parser_ir()` при любом `AppendNearestOwner` глобально
отключает почти все преобразования. Этот барьер нельзя переносить в production
direct target.

Внутри optimizer вместо глобального `any(scoped)` вычисляется отдельный
immutable `ScopedEffectSummary`. Transitive значения для recursive SCC
сходятся fixed-point до запуска преобразований. Summary содержит:

- какие owner-типы production создаёт;
- в какие owner-типы она может писать;
- содержит ли call subtree scoped effect;
- может ли преобразование пересечь owner lifetime или изменить порядок
  effects.

Recognition-only transformations и оптимизация независимых productions
продолжают выполняться. Преобразование конкретного call site/region
запрещается, если оно может переместить, клонировать, удалить или переупорядочить
`AppendNearestOwner` относительно matching `ConstructNode`/freeze boundary.
Сам `AppendNearestOwner` остаётся opaque ordered effect.

Caller/callee composition и path specialization обязаны сохранять точные
canonical target nodes и `path_facts`. Если безопасность scoped region не
доказана, optimizer оставляет только этот region непреобразованным, а не весь
`ParserIr`. До удаления глобального барьера differential tests доказывают
nearest-owner, shadowing, no-op, единственную доставку и порядок effects для
оптимизированного и неоптимизированного IR.

Tail-call rendering выполняется после этой оптимизации и потому не участвует в
построении или перестройке DAG.

## 8. Spans, diagnostics и consumer seam

Span узла начинается в позиции входа в выбранную alternative и заканчивается
`end` последнего реально потреблённого токена. Пустой узел получает zero-width
span в текущем offset.

Положительные результаты и ошибки сравниваются с VM без нормализации. Для
ошибки требуется точное равенство типа и значений `position`, `actual`,
`expected`, включая порядок tuple, `$` на EOF и отсутствие token text в
сообщении.

Generated source ограничивает объявление `SourceSpan` стабильными маркерами:

```text
# <parsergen:source-span>
...
# </parsergen:source-span>
```

Onec Interactive Runtime заменяет содержимое ровно этой секции импортом своего
`SourceSpan`. Остальной generated source не ищется и не заменяется по
случайному форматированию dataclass. Публичная сигнатура generator и
двухполевая модель результата не меняются.

Отдельная пустая секция `<parsergen:artifact-metadata>` предназначена для
consumer-owned manifest и identity. Parsergen заполняет только backend ID вне
этой секции; raw grammar/profile provenance и artifact role добавляет consumer.

Формат runtime source maps и отображение lowered BSL обратно в исходный модуль
остаются задачей consumer.

## 9. BSL-target и консоль запросов

Грамматика, semantic actions, canonical BSL-renderer и production BSL-парсер
консоли запросов не меняются. `AppendNearestOwner` остаётся запрещённым для
BSL-target и fail closed до rendering.

Новые функциональные тесты парсера консоли запросов не добавляются. Перед
изменением фиксируются raw SHA-256 трёх production artifacts:

- `ObjectModule.bsl`;
- `Templates/ТаблицаПервыхСимволовВариантов/Template.txt`;
- `Templates/ОпределенияИдентификаторов/Template.txt`.

После изменения заново сгенерированные raw bytes должны дать те же SHA-256 и
нулевой `git diff` по этим файлам. Обычного `parsergen generate --check`
недостаточно, потому что он нормализует line endings и сравнивает ValueTable
семантически, а не побайтово. Существующие repository tests продолжают
выполняться, но их набор для консоли запросов не расширяется.

## 10. Проверки parsergen

Разработка ведётся test-first. Старый VM используется как differential oracle
в отдельном рабочем состоянии и удаляется до финального commit. Большой VM
artifact или мегабайтный golden diff в репозиторий не добавляется.

Обязательные проверки:

- constructors, scalar/collection/concat/increment, constants, wraps,
  optionals, repeats, left fold, transparency и несколько entrypoints;
- точное равенство AST class/fields/values/spans старому target;
- exact error matrix для terminal, identifier, k=2, optional/repeat exit,
  committed failure, EOF, trailing token и unknown entrypoint;
- одинаковый outcome с разными `path_facts`;
- shared DAG state с несколькими входящими рёбрами без дублирования подграфа;
- 5 000 элементов EBNF repeat и 5 000 шагов безопасной правой рекурсии;
- direct self-call после открытия обычного constructor не классифицируется как
  tail call; AST, spans и freeze-error совпадают с VM;
- value-carrying direct right recursion строит 5 000 linked AST-узлов через
  production-local continuation без `RecursionError`, с точным равенством
  полей, spans и порядка freeze/error старому target;
- nearest-owner, nested shadowing, no-op, deferred ordering, единственная
  доставка и cleanup после syntax/freeze/append error;
- scoped effect из вложенной production до и после effects внешней production;
- parser reuse, iterable/indexable input и full-consumption error;
- standalone compile/import без parsergen;
- отсутствие VM symbols и operation tables;
- deterministic output при разных `PYTHONHASHSEED`;
- полный `tools/parsergen/tests`, `compileall` и repository generation check;
- raw-byte identity production BSL artifacts QueryConsole1C.

## 11. Consumer-интеграция

Onec Interactive Runtime после merge parsergen:

- обновляет parsergen identity и generated full/Worker Python artifacts;
- использует одну canonical identity без пересчёта или сокращения во всех
  путях `from_generated`, `from_files`, admission и artifact cache;
- заменяет прежний text-fragment patch `SourceSpan` на marker seam;
- сохраняет текущую BSL grammar и full AST consumers;
- проверяет равенство Worker projection и lowering результата;
- проверяет реальные `КадровыйУчет` и `КадровыйУчетРасширенный` вместе;
- проверяет MAIN и CAPTURE;
- доказывает отсутствие parsergen и COM в runtime artifact/process;
- прогоняет unit/integration suite и source-map diagnostics.

Delta admission не добавляется: hot reload полностью перезагружает изменяемый
модуль.

## 12. Производительность и методика

Эталонный корпус фиксирован:

- `КадровыйУчет`: 11 129 строк, 833 133 bytes;
- `КадровыйУчетРасширенный`: 24 607 строк, 1 981 851 bytes;
- вместе: 108 542 токена и 679 методов.

Каждый отчёт содержит privacy-safe manifest: SHA-256 обоих source bytes и
token inventory, git commits runtime/parsergen, backend identity, Python и OS,
CPU model, число logical cores, power profile и benchmark options. VM baseline
снимается и сохраняется тем же harness до удаления VM.

Warm parse benchmark выполняется в шести свежих процессах: три с порядком
VM→direct и три direct→VM. В каждом процессе после отдельного warm-up снимается
30 samples каждого backend на одном заранее построенном immutable token tuple.
Parser instance переиспользуется только внутри одной серии; tokenization,
filesystem, import и parser generation в parse-only metric не входят.

Tokenization + parse + model finalization начинается с уже прочитанных UTF-8
source bytes и пустого parser state; filesystem и parser generation не входят.
Cold import + first semantic parse запускается 30 раз на backend в отдельных
fresh child processes. До таймера generated `.py` и source bytes помещаются в
уникальный temporary directory без `__pycache__`; child запускается с
`PYTHONDONTWRITEBYTECODE=1`. Таймер включает import/compile generated module,
tokenization, parse и model finalization, но не копирование fixture и не parser
generation. Порядок backend чередуется попарно.

Samples разных процессов объединяются только внутри одинаковой метрики и
backend. p50 и p95 считаются nearest-rank по полному набору samples; отдельно
публикуются per-process p50/p95, чтобы не скрыть process-level variance.

Parsergen/direct-target gates:

- generated Worker parse p95 не более 0,75 с;
- tokenization + parse + model finalization p95 не более 1,2 с;
- cold import generated module и первый полный semantic parse от исходного
  UTF-8 текста до готовой модели, без parser generation, не более 1,5 с;
- ни одна метрика не хуже frozen VM baseline;
- `cProfile` показывает не более 60 Python calls на входной токен;
- generated module не превышает VM baseline более чем в четыре раза и не
  растёт экспоненциально на shared-DAG fixture.

Full hot reload `< 2,5 с` является gate всей hot-reload задачи, но не merge
gate отдельного parsergen PR. Текущий остаток `end_to_end - semantic_parse` уже
имеет p95 около 3,22 с в MAIN и 2,59 с в CAPTURE, поэтому после интеграции
direct parser задача продолжается профилированием и оптимизацией orchestration,
staging и transport. Hot-reload задача не закрывается, пока first load и
последующие full reload не проходят p95 `< 2,5 с` в обоих режимах.

## 13. Не входит в parsergen PR

- ручной или BSL-специфичный parser/indexer;
- изменение BSL grammar и full AST Onec Interactive Runtime;
- изменение языка запросов;
- новые функциональные тесты парсера консоли запросов;
- delta admission и method-level patches;
- оптимизация EPF/base64, runtime transactions, COM или внешнего transport.

## 14. Поставка

Изменение сначала реализуется и независимо ревьюится в QueryConsole1C как
универсальная возможность parsergen. После merge и фиксации новой версии
Onec Interactive Runtime обновляет dependency и generated artifacts, повторяет
реальные ЗУП-замеры и продолжает оптимизацию оставшегося hot-reload пути до
общего p95 `< 2,5 с`.
