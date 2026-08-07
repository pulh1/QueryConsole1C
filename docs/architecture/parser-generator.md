# Архитектура генератора парсера

## Назначение и владение

`tools/parsergen` — исходный код генератора LL(k)-парсера языка запросов. Этот каталог владеет Python-реализацией, тестами, benchmark-сценариями и канонической входной грамматикой `grammar/query-language.grammar`.

EDT-обработка `QueryConsoleZUP/src/DataProcessors/Парсер` владеет результатом генерации. В ней генератор обслуживает ровно три артефакта:

- `ObjectModule.bsl`;
- `Templates/ТаблицаПервыхСимволовВариантов/Template.txt`;
- `Templates/ОпределенияИдентификаторов/Template.txt`.

Связь входов и выходов задаёт корневой `parsergen.toml`. Изменение production-артефактов должно быть отдельным осознанным действием после проверки diff, а не побочным эффектом тестов.

## Pipeline

1. `config.py` читает TOML, разрешает пути относительно файла конфигурации и сохраняет порядок точек входа.
2. `grammar_parser.py` разбирает расширенный формат грамматики и формирует синтаксическую модель.
3. `resolver.py` разрешает нетерминалы, терминалы, классы идентификаторов и типы констант.
4. `analysis.py` вычисляет nullable, FIRST(k), FOLLOW(k) и SELECT(k), затем ищет пересечения SELECT альтернатив.
5. `validation.py` объединяет диагностики разбора, разрешения, анализа и проверки точек входа. Левая рекурсия в текущей версии диагностируется как неподдерживаемая.
6. `semantic_actions.py` обрабатывает встроенные в грамматику BSL-действия.
7. `bsl_codegen.py` строит модуль парсера и две логические таблицы.
8. `value_table_codec.py` сериализует таблицы в формат, читаемый 1С через `ЗначениеИзСтрокиВнутр`.
9. `artifacts.py` сравнивает или транзакционно заменяет только три разрешённых файла.

При сравнении `ObjectModule.bsl` окончания строк LF и CRLF считаются эквивалентными; остальной текст модуля должен совпадать. ValueTable сравниваются по колонкам и мультимножеству строк, поскольку штатный сериализатор 1С сохраняет внутренние идентификаторы и порядок строк, не относящиеся к семантике парсера.

## Анализ LL(k)

Вычисление реализовано как fixed-point поверх очередей работ. Новые факты передаются как delta, поэтому уже обработанные факты не прогоняются повторно через все зависимости. FIRST/FOLLOW хранятся в упакованном виде, а SELECT — в факторизованном; полное декартово разворачивание выполняется лениво и ограничивается вызывающей стороной.

Nullable/FIRST/FOLLOW/SELECT и диагностика LLK202 — канонические контракты LL(k). `find_select_conflicts` не зависит от представления и символически пересекает канонические SELECT-наборы непосредственно в сжатом представлении. Встроенная статистика фиксирует количество work items, delta-фактов, packed rows, descriptors и случаи материализации.

Сгенерированный BSL намеренно использует отдельно названный legacy-артефакт matcher: он выбирает самую длинную точную строку таблицы; nullable fallback применяется только при EOF, когда нет типизированных lookahead-токенов. Эта политика dispatch не является доказательством LL(k) и изолирована от канонической валидации.

В production-грамматике сейчас зафиксированы две канонические диагностики LLK202: для `ЛогическийОператор` между альтернативами 2 и 5 со свидетелем `ССЫЛКА/АВТОУПОРЯДОЧИВАНИЕ`, а также для `ОперандВ` между альтернативами 1 и 2 со свидетелем `ВЫБРАТЬ/*`. Исправление грамматики и сохранение языка runtime-парсера относятся к отдельной задаче.

## Граница canonical и legacy API

Canonical API:

- `compute_analysis`;
- `find_canonical_select_conflicts`;
- `find_select_conflicts` — canonical compatibility alias.

Legacy API:

- `build_legacy_matcher_artifact`;
- `find_runtime_dispatch_conflicts`.

Compatibility-only wrappers:

- `build_select_matcher_artifact`;
- `compatible_lookahead`.

Legacy API обслуживает только временный compatibility layer: его matcher и
runtime dispatch не являются canonical LL(k) analysis. В частности,
контрпример `A → a B | a b d`, `B → ε | b c` показывает, что отсутствие
коллизий в окончательно нормализованных legacy-строках не доказывает
сохранение языка. Для legacy dispatch отдельного доказательства
language-preservation нет.

Legacy можно удалить только при одновременном выполнении всех условий:

- production config uses canonical backend;
- zero legacy islands;
- zero production references to legacy APIs;
- canonical parser regression GREEN;
- differential semantic corpus complete;
- intentional generated artifact review complete;
- runtime benchmark complete.

## CLI

Из корня репозитория после установки пакета:

```powershell
python -m pip install "tools/parsergen[test]"
python -m pytest tools/parsergen/tests
parsergen validate --config parsergen.toml
parsergen analyze --config parsergen.toml --format json
parsergen generate --config parsergen.toml --check
python tools/parsergen/benchmarks/audit_migration.py --config parsergen.toml
```

`generate --check` — штатный read-only gate: код возврата `0` означает актуальные артефакты, `3` — найденные расхождения. Однако при канонических LLK202 валидация завершается кодом `1` до сравнения артефактов. `generate` без `--check` заменяет production-файлы и должен запускаться только в задаче, где такая регенерация явно предусмотрена.

`audit_migration.py` — read-only аудит: он семантически сравнивает три
артефакта, не останавливается на двух известных canonical `LLK202` и возвращает
canonical и legacy разделы раздельно. Canonical-раздел содержит конфликты и
диагностики, legacy-раздел — состояние окончательно нормализованных matcher
rows и runtime-конфликтов.

На Windows editable-установка (`pip install -e`) из пути с кириллицей может завершиться ошибкой `setuptools` при создании `.pth` в системной кодировке. Обычная wheel-установка выше не использует этот механизм и является проверенным вариантом для текущего расположения репозитория.

## Контроль изменений

Перед регенерацией нужно:

1. пройти Python unit-тесты;
2. для текущего baseline получить ровно две ожидаемые LLK202 при `lookahead = 2`; `validate` и `generate --check` завершаются кодом `1`, а сравнение артефактов не выполняется;
3. после отдельного исправления грамматики успешно выполнить `validate` и `generate --check` против production-парсера;
4. сгенерировать результат в копию структуры обработки и изучить три файла;
5. после осознанной регенерации выполнить существующую YAxUnit-регрессию лексера, выражений, полного парсера и семантической обработки.
