# Baseline старых лексера и парсера для оптимизации runtime

## Статус и цель

Документ задаёт воспроизводимый baseline для последующей оптимизации runtime
лексера и парсера. Исторические реализации временно подключаются рядом с
production-реализацией в тестовом расширении `yaxunit`, измеряются тем же
harness и удаляются только перед MR.

Целевой результат:

- отдельный wall-clock baseline полной токенизации;
- отдельный wall-clock baseline полного разбора, включающего работу лексера;
- одинаковые corpus, прогрев, калибровка и статистика для старой и будущей
  оптимизированной реализации;
- долговечные JSON и Markdown-артефакты с однозначным provenance.

Процент ускорения и performance gate этой спецификацией не задаются. Baseline
нужен для честного последующего сравнения, а не для заранее выбранного вывода.

## Подтверждённое исходное состояние

- Рабочая ветка: `feature/parser-lexer-optimization` от `ad2a1e7`.
- Удалённая ветка `origin/old_parser` указывает на
  `59d538fd974c723c6b1cf336c61b0fea1aec8453` и является непосредственным
  предком текущего `HEAD`.
- `DataProcessor.Парсер` между `origin/old_parser` и текущим `HEAD` изменён.
- `DataProcessor.ЛексическийАнализатор/ObjectModule.bsl` между этими refs не
  изменён. Тем не менее временная копия фиксирует именно исторический ref,
  чтобы будущие правки production-лексера не меняли baseline.
- Старый парсер имеет те же public entrypoints `Разобрать(Текст)` и
  `РазобратьВыражение(Текст)`, зависит только от обработки лексера и собственных
  двух текстовых макетов.
- Старые макеты парсера отличаются от текущих generated-макетов и должны быть
  перенесены из исторического commit вместе с модулем.
- Существующий `КОНС_Обр_БенчмаркПарсера_МО` содержит восемь corpus, три
  прогрева, двадцать samples, batch calibration до 25 ms и расчёт median/p95.
- Отдельного runtime benchmark лексера в текущем проекте нет.
- `СледующийТокен()` обозначает конец потока токеном с
  `Тип = Неопределено`, а не значением `Неопределено` вместо токена.

## Границы

### В scope

- временные test-only обработки старых лексера и парсера;
- перенос исторических BSL-модулей и двух макетов парсера;
- параметризация существующего benchmark harness по компоненту и реализации;
- отдельный lexer benchmark на том же corpus;
- фактический запуск baseline и сохранение результатов;
- точечная EDT/YAxUnit-проверка;
- заранее определённый cleanup перед MR.

### Вне scope

- оптимизация лексера, парсера или parser generator;
- изменение production-метаданных и production entrypoints;
- изменение grammar, Parser IR, query model или downstream consumers;
- добавление instrumentation в production-модули;
- перенос UI-формы исторического лексера;
- установление performance threshold до получения результатов.

## Размещение и компоненты

### Временные обработки в `yaxunit`

Через EDT-MCP создаются два собственных объекта тестового расширения:

```text
yaxunit/src/DataProcessors/КОНС_СтарыйЛексическийАнализатор/
  КОНС_СтарыйЛексическийАнализатор.mdo
  ObjectModule.bsl

yaxunit/src/DataProcessors/КОНС_СтарыйПарсер/
  КОНС_СтарыйПарсер.mdo
  ObjectModule.bsl
  Templates/ТаблицаПервыхСимволовВариантов/Template.txt
  Templates/ОпределенияИдентификаторов/Template.txt
```

Форма лексера и manager module парсера не переносятся: runtime benchmark их не
вызывает. Метаданные получают новые UUID, созданные EDT; исторические `.mdo`
не копируются вручную.

`КОНС_СтарыйЛексическийАнализатор/ObjectModule.bsl` воспроизводит BSL из
`origin/old_parser` без функциональных изменений.

`КОНС_СтарыйПарсер/ObjectModule.bsl` воспроизводит исторический BSL с одной
разрешённой адаптацией:

```bsl
Обработки.ЛексическийАнализатор.Создать()
```

заменяется на:

```bsl
Обработки.КОНС_СтарыйЛексическийАнализатор.Создать()
```

Другие compatibility-правки не допускаются. Если старый parser не проходит
corpus без дополнительных изменений, baseline блокируется и причина
фиксируется отдельно.

Оба макета старого парсера переносятся из commit `59d538f` без изменения
содержимого. Для них создаются metadata templates типа `TextDocument`.

### Постоянный benchmark harness

Существующий модуль
`yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО/Module.bsl`
остаётся владельцем corpus и общей статистики. Он расширяется двумя явными
измерительными режимами:

- `lexer` — полный проход по токенам;
- `parser` — вызов `Разобрать` или `РазобратьВыражение` согласно corpus.

Описание реализации передаёт harness следующие данные:

- стабильный идентификатор реализации;
- компонент `lexer` или `parser`;
- созданный runtime-объект;
- source ref и полный commit;
- имена и hashes задействованных артефактов;
- имя выходного sidecar.

Harness не выбирает реализацию по наличию metadata object и не использует
исключение как обычное ветвление. Current и old реализации создаются явными
factory-функциями тестового модуля.

После cleanup общие измерительные функции и current lexer/parser tests
остаются. Удаляются только old factories, old test registrations и ссылки на
временные обработки.

## Corpus и поток данных

Оба режима используют восемь существующих corpus:

1. все 42 встроенных текста `QueryExamples`;
2. самый большой реальный пакет;
3. длинный список полей;
4. цепочка JOIN;
5. пакет с UNION ALL;
6. арифметическая цепочка;
7. логическая цепочка;
8. цепочка разыменований.

Для parser mode сохраняются текущие entrypoints corpus: `Разобрать` и
`РазобратьВыражение`. Lexer mode игнорирует parser entrypoint и полностью
токенизирует каждый текст.

### Preflight

До калибровки каждый вход выполняется один раз вне измерения.

Lexer preflight:

1. вызывает `УстановитьОбрабатываемыйТекст`;
2. вызывает `СледующийТокен` до `Токен.Тип = Неопределено`;
3. считает содержательные токены;
4. требует положительный token count;
5. записывает token count в описание входа и агрегат corpus.

Parser preflight вызывает соответствующий public entrypoint и требует
результат, отличный от `Неопределено`.

При ошибке сообщение включает режим, реализацию, corpus id и input id. Входы
не пропускаются, corpus не сокращается, fallback на current implementation не
выполняется.

### Измеряемая область

Для каждого режима создаётся и инициализируется один объект до первого sample.
Объект повторно используется внутри corpus.

В lexer sample входят:

- установка очередного текста;
- получение всех токенов, включая чтение конечного токена.

В parser sample входят существующие вызовы `Разобрать` или
`РазобратьВыражение`; они включают внутреннюю токенизацию. Создание parser
object в sample не входит.

Для каждого corpus выполняются:

- batch calibration до целевой длительности 25 ms;
- 3 прогрева;
- 20 фактических samples;
- median и nearest-rank p95 по отсортированным samples.

Порядок corpus, их тексты и параметры генераторов не меняются между old и
current runs.

## Результаты и provenance

Сырые YAxUnit sidecar-файлы:

```text
runtime-old-lexer-baseline.json
runtime-old-parser-baseline.json
```

После успешного запуска они копируются без ручного пересчёта в долговечные
артефакты:

```text
docs/superpowers/matrices/2026-08-08-runtime-old-lexer-baseline.json
docs/superpowers/matrices/2026-08-08-runtime-old-parser-baseline.json
docs/superpowers/matrices/2026-08-08-runtime-old-lexer-parser-baseline.md
```

Каждый JSON сохраняет существующие runtime/corpus/sample поля и дополнительно
фиксирует:

- schema version и benchmark id;
- component и measurement scope;
- implementation id;
- `source_ref = origin/old_parser`;
- полный `source_commit`;
- metadata object names;
- SHA-256 нормализованного UTF-8/LF BSL source;
- SHA-256 исходных bytes каждого макета;
- warm-up count, sample count, calibration target и clock;
- input count, input length и operation count;
- token count для lexer corpus;
- samples, median и p95.

Parser JSON записывает hashes и parser, и lexer, потому что parser measurement
включает оба компонента. Markdown-отчёт строится только по фактически
полученным JSON и содержит таблицы median/p95 без performance verdict.

## Проверка происхождения

Перед запуском baseline выполняются автоматические проверки:

- remote-tracking ref и удалённая ветка `old_parser` указывают на ожидаемый
  commit `59d538f` либо расхождение явно блокирует неявное обновление source;
- нормализованный текст временного lexer module совпадает с историческим;
- нормализованный текст временного parser module после обратной замены имени
  лексера совпадает с историческим;
- bytes двух временных templates совпадают с `git show 59d538f:<path>`;
- в old parser нет ссылки на production
  `Обработки.ЛексическийАнализатор`.

Новые metadata UUID не участвуют в сравнении исходников.

## Проверка EDT и YAxUnit

После создания объектов выполняются:

1. resync EDT с диском при необходимости;
2. точечная ревалидация `DataProcessor.КОНС_СтарыйЛексическийАнализатор`,
   `DataProcessor.КОНС_СтарыйПарсер` и
   `CommonModule.КОНС_Обр_БенчмаркПарсера_МО`;
3. сравнение diagnostics с существующим фоном, отдельно для новых errors;
4. запуск old lexer benchmark;
5. запуск old parser benchmark;
6. запуск существующих YAxUnit-модулей лексера и парсера current
   implementation;
7. проверка JSON schema и положительных median/p95 для всех восьми corpus;
8. `git diff --check` и проверка фактического diff.

Baseline не считается снятым, если benchmark не стартовал, выполнил ноль
тестов, пропустил corpus, завершился с ошибкой либо не создал оба JSON.

## Cleanup перед MR

Cleanup выполняется отдельным явным этапом после завершения оптимизаций.
Через EDT-MCP удаляются:

- `DataProcessor.КОНС_СтарыйЛексическийАнализатор`;
- `DataProcessor.КОНС_СтарыйПарсер`;
- old factories и old test registrations в benchmark-модуле.

Сохраняются:

- общий lexer/parser measurement harness;
- current lexer/parser benchmark registrations;
- оба baseline JSON;
- Markdown-отчёт и provenance.

После cleanup выполняются точечная EDT-ревалидация, current lexer/parser
benchmarks, профильные unit-тесты и поиск оставшихся ссылок на оба удалённых
metadata object. MR не создаётся, пока временные объекты или ссылки на них
остаются в проекте.

## Критерии приёмки baseline

- Исторические исходники однозначно привязаны к commit `59d538f`.
- Old lexer и old parser одновременно доступны в `yaxunit` и не изменяют
  production extension.
- Parser baseline использует исключительно old lexer.
- Все восемь corpus проходят preflight и 20 samples в обоих режимах.
- Для каждого corpus записаны положительные median и p95.
- Lexer JSON содержит token count, parser JSON содержит hashes обоих
  компонентов.
- EDT не показывает новых errors для затронутых объектов.
- Профильные current unit-тесты не получают новых failures.
- Durable JSON и Markdown-отчёт созданы только из фактического YAxUnit run.
- План cleanup однозначно отделяет временные объекты от постоянного harness и
  результатов.
