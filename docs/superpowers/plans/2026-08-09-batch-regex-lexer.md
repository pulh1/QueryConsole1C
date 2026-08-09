# Batch-regex Lexer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Заменить посимвольный production lexer языка запросов 1С на полностью materialized batch-regex lexer с совместимым token/parser contract, корректными diagnostics и воспроизводимым ускорением.

**Architecture:** Один batch regex scan создаёт непрерывный поток raw lexical units, второй batch scan индексирует CRLF/CR/LF, после чего линейный проход материализует значимые токены и deferred error. `СледующийТокен()` становится O(1), generated parser и grammar не меняются, а historical lexer в `yaxunit` остаётся неизменяемым differential oracle.

**Tech Stack:** 1С:Предприятие 8.3.24, русский BSL, 1C:EDT/EDT-MCP, YAxUnit, Python 3.11+, PowerShell, Git.

## Global Constraints

- Production EDT project: `QueryConsoleZUP`; test EDT project: `yaxunit`.
- Совместимость расширения: 1С:Предприятие 8.3.24; BSL и project files — UTF-8.
- Любая BSL-запись выполняется через EDT-MCP после `read_module_source` и с `expectedHash`.
- Форму удалять только через двухфазный EDT-MCP `delete_metadata`; `.mdo` и `Form.form` вручную не редактировать.
- Не менять `tools/parsergen/grammar/query-language.grammar`, generated parser,
  parsergen, AST/model semantics и semantic visitors.
- Не добавлять keywords, operators, block comments, C-style comments и future syntax.
- Historical `КОНС_СтарыйЛексическийАнализатор` не изменять ни функционально, ни форматированием.
- Сохранять поля токена `Класс, Тип, Лексема, НомерСтроки, НомерСимвола` и `Значение` только у literals.
- Не добавлять per-token `StartOffset`/`Length` и benchmark-only production instrumentation.
- Regex собирать из именованных fragments; keywords не включать в основной pattern.
- Поддержать ровно пять intentional fixes: позиция #ID, запрет #1, CR-only comment, CR/LF/CRLF positions и корректный EOF position.
- Выдавать все значимые токены до первой lexical error; повторный `СледующийТокен()` на error снова выбрасывает её.
- Каждый EDT-MCP `run_yaxunit_tests` выполняется с точным
  `launchConfigurationName`, обнаруженным в Task 1 Step 2; имя никогда не
  угадывается и не переносится из старого отчёта.
- Before/after timing выполнять только после свежего ручного подтверждения пользователя, что тяжёлые процессы остановлены.
- Результат timing-run не считать окончательным verdict без совпадающих corpus/runtime/methodology и проверки run-order effect.

---

## File Map

- Modify: `QueryConsoleZUP/src/DataProcessors/ЛексическийАнализатор/ObjectModule.bsl` — production batch lexer и compatibility API.
- Delete through EDT: `DataProcessor.ЛексическийАнализатор.Form.Форма` — устаревшая ручная форма reconstruction benchmark.
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ЛексическийАнализатор_МО/Module.bsl` — characterization, intentional-fix и differential tests.
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО/Module.bsl` — существующий harness, stress corpus, raw match metadata и scan-only diagnostic.
- Create: `tools/parsergen/benchmarks/compare_runtime_lexers.py` — schema/provenance validation и before/after Markdown renderer; это report tool, не новый timing harness.
- Create: `tools/parsergen/tests/test_compare_runtime_lexers.py` — unit tests report tool.
- Create from actual runs: `docs/superpowers/matrices/2026-08-09-runtime-lexer-before-batch-{1,2,3}.json`.
- Create from actual runs: `docs/superpowers/matrices/2026-08-09-runtime-parser-before-batch-{1,2,3}.json`.
- Create from actual runs: `docs/superpowers/matrices/2026-08-09-runtime-old-lexer-batch-{1,2,3}.json`.
- Create from actual runs: `docs/superpowers/matrices/2026-08-09-runtime-new-lexer-batch-{1,2,3}.json`.
- Create from actual runs: `docs/superpowers/matrices/2026-08-09-runtime-parser-after-batch-{1,2,3}.json`.
- Create from actual runs: `docs/superpowers/matrices/2026-08-09-runtime-batch-regex-scan-{1,2,3}.json`.
- Create from validated evidence: `docs/superpowers/matrices/2026-08-09-runtime-batch-regex-lexer.md`.

### Stable interfaces

Production public API remains:

```bsl
Функция Инициализировать() Экспорт
Процедура УстановитьОбрабатываемыйТекст(Текст) Экспорт
Функция СледующийТокен() Экспорт
Функция ТипыТокенов() Экспорт
```

Test-only corpus API:

```bsl
Функция КорпусыЛексераДляДифференциальнойПроверки() Экспорт
```

Python report CLI:

```text
python tools/parsergen/benchmarks/compare_runtime_lexers.py validate \
  --old-run OLD.json --new-run NEW.json --scan-run SCAN.json \
  --parser-before PARSER_BEFORE.json --parser-after PARSER_AFTER.json
python tools/parsergen/benchmarks/compare_runtime_lexers.py report \
  --old-run OLD.json --new-run NEW.json [повторяемые аргументы] \
  --parser-before PARSER_BEFORE.json --parser-after PARSER_AFTER.json --output REPORT.md
```

---

### Task 1: Capture the unmodified before baseline

**Files:**
- Create from actual run: six `docs/superpowers/matrices/2026-08-09-runtime-{lexer,parser}-before-batch-{1,2,3}.json`

**Interfaces:**
- Consumes: existing registrations `RuntimeBaselineЛексераФормируется` and `RuntimeBaselineПарсераФормируется`.
- Produces: immutable before evidence for the exact production lexer and already-optimized current parser.

- [ ] **Step 1: Verify branch, worktree and exact production hashes**

Run:

```powershell
git status --short
git log -1 --oneline
python tools/parsergen/benchmarks/legacy_runtime_baseline.py current-hashes --repo .
python tools/parsergen/benchmarks/legacy_runtime_baseline.py verify-source --repo .
```

Expected: clean worktree; current lexer normalized SHA is
`434c0230717cb61bc4a5c7e5c3a0cc2e926a20f4bbefc8a0892f5d5aa73c3c20`;
historical source verification passes. Stop if descriptor hashes and files differ.

- [ ] **Step 2: Discover live EDT runtime and establish diagnostic baseline**

Call EDT-MCP `get_applications("QueryConsoleZUP")` and `list_configurations`;
record exact application id, runtime-client configuration and platform. Call:

```json
{"projectName":"QueryConsoleZUP","objects":["DataProcessor.ЛексическийАнализатор","DataProcessor.Парсер"]}
{"projectName":"yaxunit","objects":["CommonModule.КОНС_Обр_БенчмаркПарсера_МО"]}
```

through `revalidate_objects`, then read `get_problem_summary` and filtered
`get_project_errors`. Record the existing diagnostic background.

- [ ] **Step 3: Stop at the fresh runtime gate**

Report readiness and ask the user to confirm immediately before timing that
heavy processes are stopped. Design approval and earlier confirmations do not count.

- [ ] **Step 4: Run three current-lexer measurements**

For each run call `run_yaxunit_tests`. Add the required
`launchConfigurationName` field using the exact string recorded in Step 2;
never guess it. The remaining request is:

```json
{
  "tests":["КОНС_Обр_БенчмаркПарсера_МО.RuntimeBaselineЛексераФормируется"],
  "timeout":180,
  "updateBeforeLaunch":true,
  "updateScope":"extension:QueryConsoleZUP,extension:yaxunit"
}
```

If Pending, repeat identical arguments. Require one matched test and zero
failures. Copy each emitted `runtime-lexer-benchmark-after.json` byte-for-byte
to `2026-08-09-runtime-lexer-before-batch-1..3.json`.

- [ ] **Step 5: Run three current-parser measurements**

Repeat Step 4 with exact test
`КОНС_Обр_БенчмаркПарсера_МО.RuntimeBaselineПарсераФормируется`. Copy each
`runtime-parser-decision-dag.json` to
`2026-08-09-runtime-parser-before-batch-1..3.json`.

- [ ] **Step 6: Validate all six sidecars**

Run:

```powershell
@'
import json
from pathlib import Path

paths = sorted(Path("docs/superpowers/matrices").glob(
    "2026-08-09-runtime-*-before-batch-*.json"))
assert len(paths) == 6, paths
expected = [
    "query_examples_all_42", "large_package", "long_field_list",
    "join_chain", "union_package_chain", "arithmetic_chain",
    "logical_chain", "dereference_chain", "time_accounting_large",
]
for path in paths:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    assert data["schema_version"] == 2, path
    assert [row["id"] for row in data["corpora"]] == expected, path
    assert data["warmup_count"] == 3 and data["sample_count"] == 20, path
    for row in data["corpora"]:
        assert len(row["samples_ms"]) == 20, (path, row["id"])
        assert row["wall_clock_median_ms"] > 0, (path, row["id"])
        assert row["wall_clock_p95_ms"] > 0, (path, row["id"])
print("validated", len(paths), "before sidecars")
'@ | python -
```

Expected: `validated 6 before sidecars`.

- [ ] **Step 7: Hash and commit before evidence**

```powershell
Get-FileHash 'docs/superpowers/matrices/2026-08-09-runtime-*-before-batch-*.json' -Algorithm SHA256
git add -- docs/superpowers/matrices/2026-08-09-runtime-*-before-batch-*.json
git commit -m "perf: capture lexer batch before baseline"
```

---

### Task 2: Remove obsolete reconstruction API and lexer form

**Files:**
- Modify: `QueryConsoleZUP/src/DataProcessors/ЛексическийАнализатор/ObjectModule.bsl:788-846`
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ЛексическийАнализатор_МО/Module.bsl:1-447`
- Delete through EDT: `DataProcessor.ЛексическийАнализатор.Form.Форма`

**Interfaces:**
- Consumes: approved removal of `ПолучитьТекстЗапроса()`.
- Produces: lexer without reconstruction API/UI; tokenization is unchanged in this task.

- [ ] **Step 1: Read both BSL modules and capture revision hashes**

Use EDT-MCP `read_module_source`:

```json
{"projectName":"QueryConsoleZUP","modulePath":"DataProcessors/ЛексическийАнализатор/ObjectModule.bsl"}
{"projectName":"yaxunit","modulePath":"CommonModules/КОНС_Обр_ЛексическийАнализатор_МО/Module.bsl"}
```

Continue production reads past 500 lines until EOF and save both whole-file
`contentHash` values.

- [ ] **Step 2: Remove only reconstruction registrations and tests**

Remove registration:

```bsl
.ДобавитьСерверныйТест("ВосстановлениеТекстаЗавершаетсяНаКонцеВхода")
```

and the complete parameterized registration of
`ТекстЗапросаВосстанавливаетЗначимыеКонструкции`. Remove exactly the two
corresponding exported procedures. Use guarded EDT `write_module_source`,
`mode=searchReplace`.

- [ ] **Step 3: Remove production reconstruction methods**

Remove complete functions:

```bsl
Функция ПолучитьТекстЗапроса() Экспорт
Функция ПредставлениеТокена(Токен)
Функция ПредставлениеТокенаКонстанта(Токен, ТипЗначения)
```

Use the production `expectedHash`. Do not touch platform
`СхемаЗапроса.ПолучитьТекстЗапроса()` calls elsewhere.

- [ ] **Step 4: Preview and execute the exact form deletion**

Preview:

```json
{"projectName":"QueryConsoleZUP","fqn":"DataProcessor.ЛексическийАнализатор.Form.Форма"}
```

Require only the owned form and no blockers. Then execute:

```json
{"projectName":"QueryConsoleZUP","fqn":"DataProcessor.ЛексическийАнализатор.Form.Форма","confirm":true}
```

Never pass `force`.

- [ ] **Step 5: Re-read metadata/sources and search dangling calls**

Use `get_metadata_details` for `DataProcessor.ЛексическийАнализатор` and
`read_module_source` for both modules. Run:

```powershell
rg -n 'Лексер\.ПолучитьТекстЗапроса\(' QueryConsoleZUP yaxunit
rg -n 'ПолучитьТекстЗапроса\(' QueryConsoleZUP/src/DataProcessors/ЛексическийАнализатор
```

Expected: no matches; unrelated platform calls outside this path remain.

- [ ] **Step 6: Revalidate and run lexer tests**

Revalidate `DataProcessor.ЛексическийАнализатор` and
`CommonModule.КОНС_Обр_ЛексическийАнализатор_МО`. Run YAxUnit, adding the
required `launchConfigurationName` field with the exact value recorded in
Task 1 Step 2:

```json
{
  "modules":["КОНС_Обр_ЛексическийАнализатор_МО"],
  "timeout":180,
  "updateBeforeLaunch":true,
  "updateScope":"extension:QueryConsoleZUP,extension:yaxunit"
}
```

Expected: positive test count, zero failures/errors and no new EDT errors.

- [ ] **Step 7: Commit isolated cleanup**

```powershell
git diff --check
git add -- 'QueryConsoleZUP/src/DataProcessors/ЛексическийАнализатор' 'yaxunit/src/CommonModules/КОНС_Обр_ЛексическийАнализатор_МО/Module.bsl'
git commit -m "refactor: remove obsolete lexer reconstruction"
```

Historical lexer must be absent from the diff.

---

### Task 3: Strengthen current lexical characterization

**Files:**
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ЛексическийАнализатор_МО/Module.bsl`

**Interfaces:**
- Consumes: current behavior that the new architecture must retain.
- Produces: GREEN isolation/boundary tests before the switch.

- [ ] **Step 1: Register six characterization tests**

```bsl
.ДобавитьСерверныйТест("СтроковыйЛитералИзолируетСодержимое")
.ДобавитьСерверныйТест("КомментарийПоглощаетПохожийНаЗапросТекст")
.ДобавитьСерверныйТест("НеразрывныйПробелПропускается")
.ДобавитьСерверныйТест("СоставныеЛексемыОстаютсяАтомарными")
.ДобавитьСерверныйТест("СмежныеЧислаИТочкиСохраняютГраницы")
.ДобавитьСерверныйТест("БлочныйКомментарийНеДобавляется")
```

- [ ] **Step 2: Add a reusable significant-token drain**

```bsl
Функция ПолучитьВсеЗначимыеТокены(Лексер)
	Результат = Новый Массив;
	Пока Истина Цикл
		Токен = Лексер.СледующийТокен();
		Если Токен.Тип = Неопределено Тогда
			Прервать;
		КонецЕсли;
		Результат.Добавить(Токен);
	КонецЦикла;
	Возврат Результат;
КонецФункции
```

- [ ] **Step 3: Implement exact characterization cases**

Use:

- `"abc // 123 <> test"`;
- `"abc ""quoted"" text"`;
- `"abc "" // "" 123"`;
- `// ВЫБРАТЬ X = 123 <> "abc"` producing zero significant tokens;
- `Символы.НПП + "Поле"` producing one ID at column 2;
- `<= <> >=` producing exactly three atomic tokens;
- `1..2` producing two numeric values 1 and 0.2;
- `/* ВЫБРАТЬ */` producing `/`, `*`, keyword `ВЫБРАТЬ`, `*`, `/`, proving
  that C-style comments are not introduced.

Each string case must produce one string token followed by EOF.

- [ ] **Step 4: Guard-write, run and commit GREEN characterization**

Use latest `contentHash`, revalidate the common module, run the six exact
methods and require all pass on the old scanner. Then:

```powershell
git add -- 'yaxunit/src/CommonModules/КОНС_Обр_ЛексическийАнализатор_МО/Module.bsl'
git commit -m "test: characterize lexer boundaries"
```

---

### Task 4: Implement the production batch-regex lexer

**Files:**
- Modify: `QueryConsoleZUP/src/DataProcessors/ЛексическийАнализатор/ObjectModule.bsl:1-end`
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ЛексическийАнализатор_МО/Module.bsl`

**Interfaces:**
- Consumes: preserved public API and token layout.
- Produces: materialized token array, linear source positions and deferred error.

- [ ] **Step 1: Add RED tests for five fixes and deferred errors**

Register:

```bsl
.ДобавитьСерверныйТест("ВременныйИдентификаторНачинаетсяНаРешетке")
.ДобавитьСерверныйТест("ЦифраПослеРешеткиОтклоняется")
.ДобавитьСерверныйТест("ОдиночныйCRЗавершаетКомментарий")
.ДобавитьСерверныйТест("ПереводыСтрокОпределяютКоординаты")
.ДобавитьСерверныйТест("EOFУказываетНаКонецИсходногоТекста")
.ДобавитьСерверныйТест("ОшибкаВыдаетсяПослеКорректногоПрефикса")
.ДобавитьСерверныйТест("ПовторныйВызовПослеОшибкиПовторяетИсключение")
.ДобавитьСерверныйТест("НеизвестныеСимволыНеПропускаются")
.ДобавитьСерверныйТест("НезакрытаяСтрокаДиагностируетсяНаКавычке")
```

Replace old #ID column expectations with `#ВТ -> 1` and
`"  #temp_1" -> 3`.

- [ ] **Step 2: Implement exact RED cases**

Required assertions:

```text
#1, #, #@ -> exception containing "Некорректный идентификатор с #"
"// comment" + Символы.ВК + "Поле" -> Поле at (2,1)
"Первое" + Символы.ВК + "Второе" -> Второе at (2,1)
"Первое" + Символы.ПС + "Второе" -> Второе at (2,1)
"Первое" + Символы.ВК + Символы.ПС + "Второе" -> Второе at (2,1)
"Поле" + Символы.ПС -> EOF at (2,1)
"Поле " -> EOF at (1,6)
ВЫБРАТЬ @ Поле -> ВЫБРАТЬ, then error at (1,9), repeated call repeats error
```

Parameterize `НеизвестныеСимволыНеПропускаются` with `@`, `!`, `:`, `?`, `[`
and `]`: after one valid `ВЫБРАТЬ` token, each character must produce
`Не удалось разобрать запрос` at its exact column and the following valid word
must never be returned.

For `ВЫБРАТЬ "abc`, return the keyword first, then require
`Ожидается закрывающая кавычка` at `(1, 9)`; the setter itself must complete
without throwing.

- [ ] **Step 3: Run RED tests**

Run the nine exact methods. Require actual failures for old #ID, #1,
CR-only and EOF behavior. Zero matched tests is not RED.

- [ ] **Step 4: Read the complete production module**

Use EDT `read_module_source` until `truncated` is absent. Confirm no
reconstruction API and save whole-file `contentHash`.

- [ ] **Step 5: Replace scanner state with batch state**

Module state:

```bsl
Перем ИсходныйТекст;
Перем Токены;
Перем ИндексСледующегоТокена;
Перем ОтложеннаяОшибка;
Перем ПозицияEOF;

Перем КонстантыИнициализированы;
Перем КлючевыеСлова;
Перем ПробельныеСимволыДляКлассификации;
Перем НачальныеСимволыИдентификаторов;
Перем Цифры;
Перем ШаблонТокенизации;
Перем ШаблонПереводовСтрок;

Перем КлассЛексема;
Перем КлассСлово;
Перем КлассСтроковаяКонстанта;
Перем КлассЧисловаяКонстанта;
Перем ТипИдентификатор;
Перем ТипИдентификаторСРешеткой;
```

Do not retain per-character state, character-code arrays or exported timing counters.

- [ ] **Step 6: Implement idempotent constants**

```bsl
Функция Инициализировать() Экспорт
	Если КонстантыИнициализированы Тогда
		Возврат Неопределено;
	КонецЕсли;
	КлассЛексема = "Лексема";
	КлассСлово = "Слово";
	КлассСтроковаяКонстанта = "СтроковаяКонстанта";
	КлассЧисловаяКонстанта = "ЧисловаяКонстанта";
	ТипИдентификатор = "ID";
	ТипИдентификаторСРешеткой = "ID_СРешеткой";
	Цифры = "0123456789";
	НачальныеСимволыИдентификаторов =
		"_qwertyuiopasdfghjklzxcvbnmёйцукенгшщзхъфывапролджэячсмитьбю";
	ПробельныеСимволыДляКлассификации = " " + Символы.Таб + Символы.ПС + Символы.ВК
		+ Символы.НПП + Символы.ВТаб + Символы.ПФ;
	ЗаполнитьКлючевыеСлова();
	ШаблонТокенизации = СформироватьШаблонТокенизации();
	ШаблонПереводовСтрок = "\r\n|\r|\n";
	КонстантыИнициализированы = Истина;
	Возврат Неопределено;
КонецФункции
```

Copy current `ЗаполнитьКлючевыеСлова()` entries exactly.

- [ ] **Step 7: Build the readable pattern from named fragments**

```bsl
Функция СформироватьШаблонТокенизации()
	ШаблонПробельныхСимволов = "[ \t\r\n\f\v" + Символы.НПП + "]+";
	Комментарий = "//[^\r\n]*";
	СтроковыйЛитерал = """(?:""""|[^""])*""";
	ЧисловойЛитерал = "(?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)";
	НачалоИдентификатора = "[A-Za-zА-Яа-яЁё_]";
	ПродолжениеИдентификатора = "[A-Za-zА-Яа-яЁё_0-9]*";
	ИдентификаторСРешеткой = "#" + НачалоИдентификатора + ПродолжениеИдентификатора;
	Идентификатор = НачалоИдентификатора + ПродолжениеИдентификатора;
	ДвухсимвольнаяЛексема = "(?:<=|<>|>=)";
	ОдносимвольнаяЛексема = "[./<>{}%=&()*+,\-;]";
	Возврат ШаблонПробельныхСимволов
		+ "|" + Комментарий
		+ "|" + СтроковыйЛитерал
		+ "|" + ЧисловойЛитерал
		+ "|" + ИдентификаторСРешеткой
		+ "|" + Идентификатор
		+ "|" + ДвухсимвольнаяЛексема
		+ "|" + ОдносимвольнаяЛексема;
КонецФункции
```

The EDT syntax check must validate actual BSL quote escaping.

- [ ] **Step 8: Implement linear source positions**

```bsl
Функция НовоеСостояниеПозиции()
	Возврат Новый Структура(
		"ИндексПеревода, НомерСтроки, НачальнаяПозицияСтроки", 0, 1, 1);
КонецФункции

Функция ПозицияИсточника(НачальнаяПозиция, ПереводыСтрок, Состояние)
	Пока Состояние.ИндексПеревода < ПереводыСтрок.Количество() Цикл
		Перевод = ПереводыСтрок[Состояние.ИндексПеревода];
		Если Перевод.НачальнаяПозиция >= НачальнаяПозиция Тогда
			Прервать;
		КонецЕсли;
		Состояние.НомерСтроки = Состояние.НомерСтроки + 1;
		Состояние.НачальнаяПозицияСтроки =
			Перевод.НачальнаяПозиция + Перевод.Длина;
		Состояние.ИндексПеревода = Состояние.ИндексПеревода + 1;
	КонецЦикла;
	Возврат Новый Структура("НомерСтроки, НомерСимвола",
		Состояние.НомерСтроки,
		НачальнаяПозиция - Состояние.НачальнаяПозицияСтроки + 1);
КонецФункции
```

CRLF is one match and increments line once.

- [ ] **Step 9: Implement token constructors with scalar classes**

Interfaces:

```bsl
Функция НовыйТокен(Класс, ТипТокена, Лексема, Позиция)
Функция НовыйТокенЛексема(Лексема, Позиция)
Функция НовыйТокенСлово(Лексема, Позиция)
Функция НовыйТокенСРешеткой(Лексема, Позиция)
Функция НовыйТокенСтрока(Значение, Позиция)
Функция НовыйТокенЧисло(Значение, Позиция)
Функция НовыйТокенEOF(Позиция)
```

`НовыйТокен` creates exactly:

```bsl
Токен = Новый Структура(
	"Класс, Тип, Лексема, НомерСтроки, НомерСимвола",
	Класс, ТипТокена, Лексема,
	Позиция.НомерСтроки, Позиция.НомерСимвола);
```

Only literal constructors insert `Значение`. Word constructor computes
`ВРег(Лексема)` once. No constructor calls `КлассыТокенов()`.

- [ ] **Step 10: Implement literal conversion**

String:

```bsl
ВнутреннийТекст = Сред(Лексема, 2, СтрДлина(Лексема) - 2);
Значение = СтрЗаменить(ВнутреннийТекст, """""", """");
```

Number:

```bsl
Функция ЗначениеЧисловогоЛитерала(Лексема)
	Результат = 0;
	ДробнаяЧасть = Ложь;
	Множитель = 0.1;
	Для Индекс = 1 По СтрДлина(Лексема) Цикл
		Символ = Сред(Лексема, Индекс, 1);
		Если Символ = "." Тогда
			ДробнаяЧасть = Истина;
		ИначеЕсли ДробнаяЧасть Тогда
			Результат = Результат + Число(Символ) * Множитель;
			Множитель = Множитель * 0.1;
		Иначе
			Результат = Результат * 10 + Число(Символ);
		КонецЕсли;
	КонецЦикла;
	Возврат Результат;
КонецФункции
```

This deliberately copies current numeric arithmetic for the first correctness
pass. Do not use direct `Число(Лексема)` yet; Task 5 evaluates that cheaper
path only after the manual version has passed full differential coverage.

- [ ] **Step 11: Implement materialization and coverage**

```bsl
Процедура УстановитьОбрабатываемыйТекст(Текст) Экспорт
	ИсходныйТекст = Текст;
	Токены = Новый Массив;
	ИндексСледующегоТокена = 0;
	ОтложеннаяОшибка = Неопределено;
	Совпадения = СтрНайтиВсеПоРегулярномуВыражению(
		ИсходныйТекст, ШаблонТокенизации);
	ПереводыСтрок = СтрНайтиВсеПоРегулярномуВыражению(
		ИсходныйТекст, ШаблонПереводовСтрок);
	Состояние = НовоеСостояниеПозиции();
	ОжидаемаяПозиция = 1;
	Для Каждого Совпадение Из Совпадения Цикл
		Если Совпадение.НачальнаяПозиция <> ОжидаемаяПозиция Тогда
			УстановитьОтложеннуюОшибку(
				ОжидаемаяПозиция, ПереводыСтрок, Состояние);
			Прервать;
		КонецЕсли;
		МатериализоватьСовпадение(Совпадение, ПереводыСтрок, Состояние);
		ОжидаемаяПозиция =
			Совпадение.НачальнаяПозиция + Совпадение.Длина;
	КонецЦикла;
	Если ОтложеннаяОшибка = Неопределено
		И ОжидаемаяПозиция <> СтрДлина(ИсходныйТекст) + 1 Тогда
		УстановитьОтложеннуюОшибку(
			ОжидаемаяПозиция, ПереводыСтрок, Состояние);
	КонецЕсли;
	ПозицияEOF = ПозицияИсточника(
		СтрДлина(ИсходныйТекст) + 1, ПереводыСтрок, Состояние);
КонецПроцедуры
```

`МатериализоватьСовпадение` checks first character, skips whitespace/comment
without extracting their full text, then extracts exactly one substring for a
significant string, #ID, number, word or lexeme.

Classification order is exact:

```bsl
Если СтрНайти(ПробельныеСимволыДляКлассификации, ПервыйСимвол) > 0 Тогда
	Возврат Истина;
ИначеЕсли ПервыйСимвол = "/" И Совпадение.Длина >= 2
	И Сред(ИсходныйТекст, Совпадение.НачальнаяПозиция + 1, 1) = "/" Тогда
	Возврат Истина;
ИначеЕсли ПервыйСимвол = """" Тогда
	// string
ИначеЕсли ПервыйСимвол = "#" Тогда
	// ID_СРешеткой
ИначеЕсли СтрНайти(Цифры, ПервыйСимвол) > 0
	Или ПервыйСимвол = "." И Совпадение.Длина > 1 Тогда
	// number; a one-character dot remains a lexeme
ИначеЕсли СтрНайти(НачальныеСимволыИдентификаторов, НРег(ПервыйСимвол)) > 0 Тогда
	// word
Иначе
	// supported lexeme
КонецЕсли;
```

Retain `НачальныеСимволыИдентификаторов` as one immutable module string only
for this constant-time category check; do not recreate character-code arrays.
If literal conversion throws, catch it inside materialization, store a deferred
error at that match start and stop; `УстановитьОбрабатываемыйТекст()` must not
raise a lexical-content exception.

- [ ] **Step 12: Implement deferred diagnostics and O(1) reads**

Build error text:

```bsl
Если СимволОшибки = """" Тогда
	Сообщение = "Ожидается закрывающая кавычка";
ИначеЕсли СимволОшибки = "#" Тогда
	Сообщение = "Некорректный идентификатор с #";
Иначе
	Сообщение = "Не удалось разобрать запрос";
КонецЕсли;
ПолноеСообщение = СтрШаблон(
	"{(%1, %2)}: %3",
	Позиция.НомерСтроки, Позиция.НомерСимвола, Сообщение);
ОтложеннаяОшибка = Новый Структура(
	"ИндексТокена,НачальнаяПозиция,НомерСтроки,НомерСимвола,Сообщение",
	Токены.Количество(), НачальнаяПозиция, Позиция.НомерСтроки,
	Позиция.НомерСимвола, ПолноеСообщение);
```

Read:

```bsl
Функция СледующийТокен() Экспорт
	Если ИндексСледующегоТокена < Токены.Количество() Тогда
		Токен = Токены[ИндексСледующегоТокена];
		ИндексСледующегоТокена = ИндексСледующегоТокена + 1;
		Возврат Токен;
	КонецЕсли;
	Если ОтложеннаяОшибка <> Неопределено Тогда
		ВызватьИсключение ОтложеннаяОшибка.Сообщение;
	КонецЕсли;
	Возврат НовыйТокенEOF(ПозицияEOF);
КонецФункции
```

- [ ] **Step 13: Preserve compatibility-only token type API**

Keep existing `ТипыТокенов()` and its private type builders. Remove
`КлассыТокенов()`, `КлючевыеСловаОпределяемыеСкобкой`, old scanner helpers and
timing counters. No public method returns internal mutable keyword/lexeme maps.

- [ ] **Step 14: Guard-write the complete module**

Call EDT `write_module_source` with these exact bindings:

- `projectName = "QueryConsoleZUP"`;
- `modulePath = "DataProcessors/ЛексическийАнализатор/ObjectModule.bsl"`;
- `mode = "replace"`;
- `source` is the complete concrete module composed in Steps 5-13, including
  the exact keyword/type mappings copied from the Step 4 read;
- `expectedHash` is the whole-file `contentHash` captured in Step 4;
- `skipSyntaxCheck = false`.

The source passed at execution must contain every concrete method body; never
use `overwrite=true`.

- [ ] **Step 15: Re-read, revalidate and reject old scanner remnants**

Read the complete module, revalidate `DataProcessor.ЛексическийАнализатор`,
then run:

```powershell
rg -n 'УстановитьОбрабатываемыйСимвол|КлассыТокенов\(|ВремяПолученияИдентификатора|ВремяУстановкиСимволов' 'QueryConsoleZUP/src/DataProcessors/ЛексическийАнализатор/ObjectModule.bsl'
```

Expected: no matches and no new EDT errors.

- [ ] **Step 16: Run GREEN lexer and parser tests**

Run the nine former RED methods, then full
`КОНС_Обр_ЛексическийАнализатор_МО`, then:

```json
{
  "modules":["КОНС_Обр_Парсер_МО","КОНС_Обр_ПарсерЗапросов_МО"],
  "timeout":300,
  "updateBeforeLaunch":true,
  "updateScope":"extension:QueryConsoleZUP,extension:yaxunit"
}
```

Require positive counts and zero failures/errors. Do not modify parser/grammar
to mask a lexer mismatch.

- [ ] **Step 17: Commit production batch lexer**

```powershell
git diff --check
git add -- 'QueryConsoleZUP/src/DataProcessors/ЛексическийАнализатор/ObjectModule.bsl' 'yaxunit/src/CommonModules/КОНС_Обр_ЛексическийАнализатор_МО/Module.bsl'
git commit -m "feat: materialize batch regex lexer"
```

Record this commit for benchmark provenance.

---

### Task 5: Add full differential coverage

**Files:**
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО/Module.bsl`
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ЛексическийАнализатор_МО/Module.bsl`
- Fix only on unexplained difference: `QueryConsoleZUP/src/DataProcessors/ЛексическийАнализатор/ObjectModule.bsl`

**Interfaces:**
- Consumes: historical/current lexer API.
- Produces: token-by-token comparison over synthetic and real corpus.

- [ ] **Step 1: Export the existing corpus without duplication**

```bsl
Функция КорпусыЛексераДляДифференциальнойПроверки() Экспорт
	Возврат КорпусыБенчмарка();
КонецФункции
```

- [ ] **Step 2: Register three differential tests**

```bsl
.ДобавитьСерверныйТест("ЛексерыЭквивалентныНаСинтетическомКорпусе")
.ДобавитьСерверныйТест("ЛексерыЭквивалентныНаРеальныхЗапросах")
.ДобавитьСерверныйТест("ЛексерыОдинаковоВыдаютПрефиксДоОшибки")
```

- [ ] **Step 3: Implement exact token comparison**

```bsl
Процедура ПроверитьЭквивалентностьТокенов(СтарыйТокен, НовыйТокен, Контекст)
	ЮТест.ОжидаетЧто(НовыйТокен.Класс).Равно(СтарыйТокен.Класс, Контекст + ": Класс");
	ЮТест.ОжидаетЧто(НовыйТокен.Тип).Равно(СтарыйТокен.Тип, Контекст + ": Тип");
	ЮТест.ОжидаетЧто(НовыйТокен.Лексема).Равно(СтарыйТокен.Лексема, Контекст + ": Лексема");
	ЕстьСтарое = СтарыйТокен.Свойство("Значение", СтароеЗначение);
	ЕстьНовое = НовыйТокен.Свойство("Значение", НовоеЗначение);
	ЮТест.ОжидаетЧто(ЕстьНовое).Равно(ЕстьСтарое, Контекст + ": наличие Значение");
	Если ЕстьСтарое Тогда
		ЮТест.ОжидаетЧто(НовоеЗначение).Равно(СтароеЗначение, Контекст + ": Значение");
	КонецЕсли;
	Если СтарыйТокен.Тип = Неопределено Тогда
		Возврат;
	КонецЕсли;
	ЮТест.ОжидаетЧто(НовыйТокен.НомерСтроки).Равно(
		СтарыйТокен.НомерСтроки, Контекст + ": строка");
	Если НовыйТокен.Тип = "ID_СРешеткой" Тогда
		ЮТест.ОжидаетЧто(
			НовыйТокен.НомерСимвола + СтрДлина(НовыйТокен.Лексема))
			.Равно(СтарыйТокен.НомерСимвола, Контекст + ": позиция #ID");
	Иначе
		ЮТест.ОжидаетЧто(НовыйТокен.НомерСимвола).Равно(
			СтарыйТокен.НомерСимвола, Контекст + ": колонка");
	КонецЕсли;
КонецПроцедуры
```

EOF compares empty class/type/lexeme and returns before source-position
comparison; new EOF position is independently tested, not normalized to the
historical bug.

- [ ] **Step 4: Implement full-stream comparison**

Create objects explicitly:

```bsl
СтарыйЛексер = Обработки.КОНС_СтарыйЛексическийАнализатор.Создать();
СтарыйЛексер.Инициализировать();
СтарыйЛексер.УстановитьОбрабатываемыйТекст(Текст);
НовыйЛексер = Обработки.ЛексическийАнализатор.Создать();
НовыйЛексер.Инициализировать();
НовыйЛексер.УстановитьОбрабатываемыйТекст(Текст);
```

Read both until EOF, compare ordinal and fail on different length. A test-only
maximum read count `СтрДлина(Текст) + 2` guards infinite loops.

- [ ] **Step 5: Define synthetic and real inputs**

Synthetic inputs include all string cases, all 19 lexemes, numeric sequence
`0 1 01 1. .5 12.5 1..2`, Latin/Russian/Ё/underscore identifiers, comments,
multiline string, LF and CRLF. Real test iterates every input from
`КорпусыЛексераДляДифференциальнойПроверки()`.

- [ ] **Step 6: Compare invalid prefixes explicitly**

For `ВЫБРАТЬ @ Поле` and an unterminated string after a valid keyword, compare
the complete prefix and error ordinal. Do not treat #1, CR-only and EOF bugs as
equal; their independent regressions remain.

- [ ] **Step 7: Run differential tests and resolve only production defects**

Require no unexplained field/value/position difference. On failure, correct
production lexer and add that exact input as regression; never edit historical
lexer.

- [ ] **Step 8: Evaluate direct numeric conversion behind a differential gate**

First keep the manual numeric implementation from Task 4 and obtain a GREEN
full differential run. Then replace only `ЗначениеЧисловогоЛитерала()` with
the direct candidate after normalizing `.digits` to `0.digits` and `digits.`
to `digits`. Extend the synthetic numeric matrix to:

```text
0 1 01 42 12.5 .5 1. 1..2
0.0000000000000000000000000001
9999999999999999999999999999
99999999999999.99999999999999
```

Run the synthetic and real differential tests again. Keep the direct version
only if every `Значение` and error ordinal is identical; otherwise restore the
already-GREEN manual version. In either outcome add
`ПрямоеПреобразованиеЧиселСовместимо` or
`ПрямоеПреобразованиеЧиселНесовместимо` as a regression test that fixes the
observed platform result for this exact matrix. This decision is correctness
evidence, not a timing-based language change.

- [ ] **Step 9: Revalidate and commit**

```powershell
git diff --check
git add -- 'yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО/Module.bsl' 'yaxunit/src/CommonModules/КОНС_Обр_ЛексическийАнализатор_МО/Module.bsl' 'QueryConsoleZUP/src/DataProcessors/ЛексическийАнализатор/ObjectModule.bsl'
git commit -m "test: add lexer differential coverage"
```

---

### Task 6: Extend existing benchmark with stress corpus and raw matches

**Files:**
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО/Module.bsl`

**Interfaces:**
- Consumes: existing lifecycle and user-provided batch prototype.
- Produces: 12-corpus full benchmark, raw match metadata and scan-only diagnostic.

- [ ] **Step 1: Add deterministic valid-query generators**

```bsl
Функция ПовторитьСтроку(Фрагмент, Количество)
	Части = Новый Массив;
	Для Индекс = 1 По Количество Цикл
		Части.Добавить(Фрагмент);
	КонецЦикла;
	Возврат СтрСоединить(Части, "");
КонецФункции

Функция ПостроитьТекстСКомментариями(КоличествоКомментариев, ДлинаХвоста)
	Строки = Новый Массив;
	Хвост = ПовторитьСтроку("x", ДлинаХвоста);
	Для Индекс = 1 По КоличествоКомментариев Цикл
		Строки.Добавить("// ВЫБРАТЬ X = 123 <> ""abc"" " + Хвост);
	КонецЦикла;
	Строки.Добавить("ВЫБРАТЬ 1 КАК Поле");
	Возврат СтрСоединить(Строки, Символы.ПС);
КонецФункции

Функция ПостроитьТекстСоСтроками(КоличествоСтрок, ДлинаХвоста)
	Поля = Новый Массив;
	Кавычка = Символ(34);
	Хвост = ПовторитьСтроку("text", ДлинаХвоста);
	Для Индекс = 1 По КоличествоСтрок Цикл
		РазделительВнутри = ?(Индекс % 10 = 0, Символы.ПС, " ");
		Литерал = Кавычка + "abc " + Кавычка + Кавычка + "quoted"
			+ Кавычка + Кавычка + РазделительВнутри
			+ "// 123 <> ВЫБРАТЬ 456 " + Хвост + Кавычка;
		Поля.Добавить(Литерал + " КАК Поле" + Строка(Индекс));
	КонецЦикла;
	Возврат "ВЫБРАТЬ " + СтрСоединить(Поля, ", ");
КонецФункции

Функция ПостроитьТекстСЧислами(КоличествоЧисел)
	Поля = Новый Массив;
	Для Индекс = 0 По КоличествоЧисел - 1 Цикл
		Поля.Добавить(Строка(Индекс % 10) + " КАК Поле" + Строка(Индекс));
	КонецЦикла;
	Возврат "ВЫБРАТЬ " + СтрСоединить(Поля, ", ");
КонецФункции

Функция MD5Строки(Текст)
	Хеш = Новый ХешированиеДанных(ХешФункция.MD5);
	Хеш.Добавить(Текст);
	Возврат СтрЗаменить(Хеш.ХешСумма, " ", "");
КонецФункции

Процедура ДобавитьStressВход(Входы, Идентификатор, Текст, Генератор, Параметры)
	Провенанс = Новый Структура(
		"type,generator,parameters,input_length,text_md5",
		"synthetic_stress", Генератор, Параметры,
		СтрДлина(Текст), MD5Строки(Текст));
	ДобавитьВход(Входы, Идентификатор, Текст, Провенанс);
КонецПроцедуры
```

Fixed inputs and parameters:

- `comment_heavy_many_short`: 500 comments, `ДлинаХвоста = 0`;
- `comment_heavy_one_long`: 1 comment, `ДлинаХвоста = 100000`;
- `string_heavy_many`: 500 literals, `ДлинаХвоста = 20`;
- `string_heavy_one_long`: 1 literal, `ДлинаХвоста = 25000` (100,000 tail
  characters because the repeated fragment is `text`);
- `numeric_dense`: 2,000 numeric fields.

If parser preflight proves a platform limit, change the documented count and
the generator provenance rather than silently skipping an input.

- [ ] **Step 2: Add three corpus descriptors**

Append after `time_accounting_large`:

```text
comment_heavy  Разобрать
string_heavy   Разобрать
numeric_dense  Разобрать
```

`comment_heavy` and `string_heavy` each contain the two inputs named above;
`numeric_dense` contains one. Store every exact generator argument in corpus
and input provenance together with `input_length` and `text_md5` from
`ДобавитьStressВход()`, so old/new alignment detects accidental drift. Do not
change provenance of the original nine corpus: immutable parser-before
evidence must still align with their after rows.

- [ ] **Step 3: Migrate the batch prototype into untimed preflight**

Add module variable `ДиагностическийRegexШаблон` and private idempotent
`ИнициализироватьДиагностическийRegex()`. That initializer assembles the
corrected eight named fragments exactly once before warmup/timing; the timed
scan must not rebuild the pattern per iteration. Add:

```bsl
Функция СтатистикаRegexСовпадений(Текст)
	Совпадения = СтрНайтиВсеПоРегулярномуВыражению(
		Текст, ДиагностическийRegexШаблон);
	ОжидаемаяПозиция = 1;
	КоличествоТокенов = 0;
	Для Каждого Совпадение Из Совпадения Цикл
		Если Совпадение.НачальнаяПозиция <> ОжидаемаяПозиция Тогда
			ВызватьИсключение СтрШаблон(
				"diagnostic regex gap: expected=%1 actual=%2",
				ОжидаемаяПозиция, Совпадение.НачальнаяПозиция);
		КонецЕсли;
		ПервыйСимвол = Сред(Текст, Совпадение.НачальнаяПозиция, 1);
		ЭтоПробел = СтрНайти(
			" " + Символы.Таб + Символы.ПС + Символы.ВК
				+ Символы.НПП + Символы.ВТаб + Символы.ПФ,
			ПервыйСимвол) > 0;
		ЭтоКомментарий = ПервыйСимвол = "/"
			И Совпадение.Длина >= 2
			И Сред(Текст, Совпадение.НачальнаяПозиция + 1, 1) = "/";
		Если Не ЭтоПробел И Не ЭтоКомментарий Тогда
			КоличествоТокенов = КоличествоТокенов + 1;
		КонецЕсли;
		ОжидаемаяПозиция =
			Совпадение.НачальнаяПозиция + Совпадение.Длина;
	КонецЦикла;
	Если ОжидаемаяПозиция <> СтрДлина(Текст) + 1 Тогда
		ВызватьИсключение "diagnostic regex did not cover source end";
	КонецЕсли;
	Возврат Новый Структура(
		"raw_match_count,significant_match_count",
		Совпадения.Количество(), КоличествоТокенов);
КонецФункции
```

Call `ИнициализироватьДиагностическийRegex()` from the benchmark registration
before `ВыполнитьБенчмарк()` and from the non-timed stress preflight. Keep the
eight local fragment names in the initializer; do not store one opaque regex
literal.

- [ ] **Step 4: Add raw match fields to preflight and JSON**

For lexer inputs/corpus store `token_count`, `raw_match_count` and
`significant_match_count`; assert significant matches equal tokens for old and
new. Extend `ОписаниеВходов()` and `ИзмеритьКорпус()`. Emit schema version 3
for the new benchmark series.

- [ ] **Step 5: Add scan-only diagnostic inside the same harness**

Register `RuntimeBatchRegexScanФормируется`. Descriptor component:
`regex_scan`; sidecar: `runtime-batch-regex-scan.json`; measurement scope:

```text
Один batch regex scan, coverage validation и подсчёт значимых/raw matches;
без token materialization и literal conversion
```

Extend `ВыполнитьПакет()` with an explicit `regex_scan` branch. This timing is
never used as production lexer verdict.

- [ ] **Step 6: Update assertions to 12 corpus**

Append ids `comment_heavy`, `string_heavy`, `numeric_dense`; require exactly
12 rows, 20 samples, positive median/p95, positive raw matches, and positive
token counts for lexer.

- [ ] **Step 7: Add and run non-timed stress preflight**

Register `LexerStressCorpusPreflightПроходит`. It builds 12 corpus, runs old
and new lexer preflight, requires equal significant token counts, then parses
all five inputs from the three new corpus once. Run this exact test; require one pass
and no timing sidecar. Also require 843 tokens for `large_package` and 19,617
for `time_accounting_large`. Record their diagnostic raw counts beside the
prototype observations 1,297 and 29,717; any difference blocks timing until
the corrected production pattern or corpus identity explains it.

- [ ] **Step 8: Update current descriptor provenance**

```powershell
python tools/parsergen/benchmarks/legacy_runtime_baseline.py current-hashes --repo .
git log -1 --format='%H' -- 'QueryConsoleZUP/src/DataProcessors/ЛексическийАнализатор/ObjectModule.bsl'
```

Write exact lexer SHA/commit into current lexer descriptor and current parser
lexer artifact. Set current sidecars to `runtime-new-lexer-batch.json` and
`runtime-parser-after-batch.json`. Keep old descriptors untouched.

- [ ] **Step 9: Revalidate, run preflight/differential and commit**

```powershell
git add -- 'yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО/Module.bsl'
git commit -m "perf: extend lexer benchmark stress corpus"
```

---

### Task 7: Build runtime comparison and report validation

**Files:**
- Create: `tools/parsergen/benchmarks/compare_runtime_lexers.py`
- Create: `tools/parsergen/tests/test_compare_runtime_lexers.py`

**Interfaces:**
- Consumes: schema 2 before and schema 3 old/new/scan sidecars.
- Produces: strict alignment validation and Markdown renderer.

- [ ] **Step 1: Write failing tests**

Use synthetic 20-sample fixtures. Define these exact tests:

- `test_validate_rejects_misaligned_corpus_order()` expects `ValueError` when
  the second lexer sidecar swaps two ids;
- `test_validate_rejects_changed_input_identity()` expects `ValueError` after
  changing one input id, length or provenance hash;
- `test_validate_requires_raw_matches_for_schema_three_lexer()` expects
  `ValueError` after removing `raw_match_count`;
- `test_scan_alignment_accepts_distinct_component_with_same_inputs()` checks
  that `regex_scan` aligns by corpus/input identity without pretending to be
  the production lexer operation;
- `test_scan_alignment_rejects_changed_raw_counts()` expects `ValueError`
  after changing one scan raw/significant count;
- `test_parser_alignment_accepts_after_superset_with_same_original_nine()`
  validates nine before rows against the same nine plus three after rows;
- `test_parser_alignment_rejects_change_inside_original_nine()` expects
  `ValueError` after changing one of those first nine rows;
- `test_compare_reports_median_p95_speedup_and_cv()` asserts exact values for
  a fixture with old median 10 ms and new median 2 ms;
- `test_report_discloses_sequential_parser_order_caveat()` asserts the report
  contains the sequential-order caveat;
- `test_cli_writes_markdown_without_rewriting_json()` hashes every input JSON
  before and after the subprocess call and requires identical bytes.

Speedup is `old_ms / new_ms`; CV is population standard deviation / mean.

- [ ] **Step 2: Run RED**

```powershell
python -m pytest tools/parsergen/tests/test_compare_runtime_lexers.py -q
```

Expected: import/file-not-found failure.

- [ ] **Step 3: Implement loading and strict validation**

Provide these typed functions:

- `load_sidecar(path: Path) -> dict[str, object]`;
- `validate_sidecar(data: dict[str, object], *, require_raw_matches: bool) -> None`;
- `validate_alignment(left: dict[str, object], right: dict[str, object]) -> None`;
- `validate_scan_alignment(lexer: dict[str, object], scan: dict[str, object]) -> None`;
- `validate_parser_alignment(before: dict[str, object], after: dict[str, object]) -> None`;
- `corpus_rows(data: dict[str, object]) -> dict[str, dict[str, object]]`.

Require artifacts/SHA, runtime identity, warmup 3, samples 20, calibration
25 ms, positive timings and schema-3 raw counts. Old/new lexer alignment is
strict over all 12 corpus, inputs and production operation semantics. Scan
alignment is strict over the same 12 corpus/input identities and raw counts,
but requires its deliberately different `regex_scan` component and scan-only
measurement scope rather than equating it with a production lexer run.
Parser before is the immutable schema-2 nine-corpus evidence from Task 1;
parser after may append the three stress corpus, but its first nine ids,
inputs, provenance, entrypoints and parser artifacts other than the lexer must
match before exactly. Never pretend the three new after-only parser rows have
a before value.

- [ ] **Step 4: Implement statistics and Markdown**

Provide these typed functions:

- `coefficient_of_variation(samples: list[float]) -> float`;
- `summarize_runs(paths: list[Path]) -> dict[str, object]`;
- `compare_lexer_runs(old_paths: list[Path], new_paths: list[Path]) -> list[dict[str, object]]`;
- `render_report(lexer_rows: list[dict[str, object]], *, parser_before: list[Path], parser_after: list[Path], scan_runs: list[Path]) -> str`.

Report median of per-run medians, min/max, per-run p95 and CV; never pool raw
samples across calibrated runs.

- [ ] **Step 5: Implement `validate` and `report` argparse subcommands**

Both subcommands use repeatable `--old-run`, `--new-run`, `--scan-run`,
`--parser-before`, `--parser-after`. `validate` applies strict 12-corpus lexer
alignment plus nine-row parser-prefix alignment. `report` writes UTF-8/LF and
never changes input JSON.

- [ ] **Step 6: Run GREEN tests and commit**

```powershell
python -m pytest tools/parsergen/tests/test_compare_runtime_lexers.py -q
python -m pytest tools/parsergen/tests/test_legacy_runtime_baseline.py -q
git add -- 'tools/parsergen/benchmarks/compare_runtime_lexers.py' 'tools/parsergen/tests/test_compare_runtime_lexers.py'
git commit -m "tools: compare lexer runtime benchmarks"
```

---

### Task 8: Complete correctness and readability review

**Files:**
- Review all four implementation/test/tool files from File Map.

**Interfaces:**
- Consumes: functionally complete lexer.
- Produces: zero known correctness blockers before timing.

- [ ] **Step 1: Verify scope and historical integrity**

```powershell
git diff 92686b4 --name-only
git diff --exit-code 92686b4 -- 'QueryConsoleZUP/src/DataProcessors/Парсер' 'tools/parsergen/grammar/query-language.grammar' 'tools/parsergen/src'
python tools/parsergen/benchmarks/legacy_runtime_baseline.py verify-source --repo .
rg -n 'ПолучитьТекстЗапроса\(|КлассыТокенов\(' 'QueryConsoleZUP/src/DataProcessors/ЛексическийАнализатор'
```

Expected: no parser/grammar/parsergen diff; historical verification passes; no removed APIs.

- [ ] **Step 2: Review regex and allocations**

Require eight named fragments, numeric grouping, comment before slash, 2-char
lexemes before prefixes, ASCII digits and NBSP. Confirm no substring for long
comments/whitespace, one substring per significant token, one `ВРег` per word,
no class structures, no retained raw matches and no per-token span fields.

- [ ] **Step 3: Revalidate diagnostic delta**

Revalidate:

```json
{"projectName":"QueryConsoleZUP","objects":["DataProcessor.ЛексическийАнализатор","DataProcessor.Парсер"]}
{"projectName":"yaxunit","objects":["CommonModule.КОНС_Обр_ЛексическийАнализатор_МО","CommonModule.КОНС_Обр_БенчмаркПарсера_МО"]}
```

Require no new errors relative to Task 1.

- [ ] **Step 4: Run full functional frontend selection**

```json
{
  "modules":[
    "КОНС_Обр_ЛексическийАнализатор_МО",
    "КОНС_Обр_Парсер_МО",
    "КОНС_Обр_ПарсерЗапросов_МО",
    "КОНС_Обр_ИсполняемыеПредставления_МО",
    "КОНС_Обр_ПостроениеИГенерацияЗапросов_МО"
  ],
  "timeout":600,
  "updateBeforeLaunch":true,
  "updateScope":"extension:QueryConsoleZUP,extension:yaxunit"
}
```

Require positive test counts and zero failures/errors.

- [ ] **Step 5: Invoke review skills**

Use `queryconsole-1c-review` and `superpowers:requesting-code-review`. Review
semantic equivalence, five fixes, regex readability, deferred errors, source
positions, provenance and accidental parser/model changes. Apply only
evidenced fixes through EDT revision guards and add a regression for each
correctness fix.

- [ ] **Step 6: Repeat verification after fixes**

Repeat Steps 1, 3, 4 plus:

```powershell
python -m pytest tools/parsergen/tests/test_compare_runtime_lexers.py tools/parsergen/tests/test_legacy_runtime_baseline.py -q
git diff --check
```

Do not proceed with failures or unexplained differential results.

---

### Task 9: Run final timing evidence

**Files:**
- Create actual old/new/scan/parser-after JSON files from File Map.

**Interfaces:**
- Consumes: reviewed code and 12 aligned corpus.
- Produces: counterbalanced lexer and sequential parser evidence.

- [ ] **Step 1: Verify provenance immediately before timing**

```powershell
git status --short
python tools/parsergen/benchmarks/legacy_runtime_baseline.py verify-source --repo .
python tools/parsergen/benchmarks/legacy_runtime_baseline.py current-hashes --repo .
git log -1 --format='%H' -- 'QueryConsoleZUP/src/DataProcessors/ЛексическийАнализатор/ObjectModule.bsl'
```

Compare values with old/current lexer and current parser descriptors. Stale
identity blocks timing.

- [ ] **Step 2: Repeat functional preflight**

Run exact `LexerStressCorpusPreflightПроходит` and three differential tests.
Require zero failures and 12 corpus.

- [ ] **Step 3: Stop at a new manual runtime gate**

Ask for fresh confirmation that heavy processes are stopped.

- [ ] **Step 4: Run counterbalanced old/new lexer series**

Exact registrations:

```text
Old: КОНС_Обр_БенчмаркПарсера_МО.RuntimeBaselineСтарогоЛексераФормируется
New: КОНС_Обр_БенчмаркПарсера_МО.RuntimeBaselineЛексераФормируется
```

Order: `old-1, new-1, new-2, old-2, old-3, new-3`. Copy each emitted sidecar
immediately: old runs copy `runtime-old-lexer-baseline.json` to the numbered
`runtime-old-lexer-batch` path; new runs copy
`runtime-new-lexer-batch.json` to the numbered `runtime-new-lexer-batch` path.
Each call must match one test; never use module/tag filters for timing.

- [ ] **Step 5: Run three scan-only diagnostic runs**

Run exact `RuntimeBatchRegexScanФормируется` three times and copy each
`runtime-batch-regex-scan.json` to durable numbered paths.

- [ ] **Step 6: Run three parser-after runs**

Run exact `RuntimeBaselineПарсераФормируется` three times and copy
`runtime-parser-after-batch.json` to durable numbered paths. Parser artifact
other than lexer must match Task 1.

- [ ] **Step 7: Validate all alignments**

Use `compare_runtime_lexers.py validate` with all three old, new, scan,
parser-before and parser-after paths (the same path list shown in Task 10
Step 1, without `--output`). Require schema/methodology/runtime alignment,
strict 12-corpus old/new/scan order, equal old/new token and raw counts, and
20 samples. For parser, require exact alignment of the original nine rows and
allow only the three documented after-only stress rows. Require exact hashes
and unchanged parser artifacts other than the lexer. Reject and rerun
incompatible evidence.

- [ ] **Step 8: Hash raw sidecars**

```powershell
Get-FileHash 'docs/superpowers/matrices/2026-08-09-runtime-*-batch-*.json' -Algorithm SHA256
```

Never rewrite raw JSON.

---

### Task 10: Publish final report and completion evidence

**Files:**
- Create: `docs/superpowers/matrices/2026-08-09-runtime-batch-regex-lexer.md`
- Add: validated Task 9 JSON.

**Interfaces:**
- Consumes: repeated old/new/scan/parser evidence.
- Produces: final verdict, limitations and handoff.

- [ ] **Step 1: Generate Markdown**

```powershell
python tools/parsergen/benchmarks/compare_runtime_lexers.py report `
  --old-run docs/superpowers/matrices/2026-08-09-runtime-old-lexer-batch-1.json `
  --old-run docs/superpowers/matrices/2026-08-09-runtime-old-lexer-batch-2.json `
  --old-run docs/superpowers/matrices/2026-08-09-runtime-old-lexer-batch-3.json `
  --new-run docs/superpowers/matrices/2026-08-09-runtime-new-lexer-batch-1.json `
  --new-run docs/superpowers/matrices/2026-08-09-runtime-new-lexer-batch-2.json `
  --new-run docs/superpowers/matrices/2026-08-09-runtime-new-lexer-batch-3.json `
  --scan-run docs/superpowers/matrices/2026-08-09-runtime-batch-regex-scan-1.json `
  --scan-run docs/superpowers/matrices/2026-08-09-runtime-batch-regex-scan-2.json `
  --scan-run docs/superpowers/matrices/2026-08-09-runtime-batch-regex-scan-3.json `
  --parser-before docs/superpowers/matrices/2026-08-09-runtime-parser-before-batch-1.json `
  --parser-before docs/superpowers/matrices/2026-08-09-runtime-parser-before-batch-2.json `
  --parser-before docs/superpowers/matrices/2026-08-09-runtime-parser-before-batch-3.json `
  --parser-after docs/superpowers/matrices/2026-08-09-runtime-parser-after-batch-1.json `
  --parser-after docs/superpowers/matrices/2026-08-09-runtime-parser-after-batch-2.json `
  --parser-after docs/superpowers/matrices/2026-08-09-runtime-parser-after-batch-3.json `
  --output docs/superpowers/matrices/2026-08-09-runtime-batch-regex-lexer.md
```

- [ ] **Step 2: Review allowed conclusions**

Report separately:

- counterbalanced final lexer verdict;
- scan-only lower bound;
- sequential parser before/after direction with order caveat;
- absence of an independent semantic-frontend timing harness in tracked repo;
- successful semantic functional modules instead of invented timing;
- unavailable allocation/memory counters.

Tables contain scenario, length, tokens/raw matches, old/new median/p95,
speedup, run range/CV and aligned parser effect.

- [ ] **Step 3: Apply the performance gate**

Accept only when:

- no correctness/count mismatch exists;
- `large_package` and `time_accounting_large` improve clearly in every
  counterbalanced run;
- comment-heavy and string-heavy do not regress;
- full production path retains a material share of scan-only gain;
- contrary parser movement is investigated and documented.

If the gate fails, do not claim completion. Use corpus-specific scan/full
distance to isolate line scan, token structures, keyword lookup or literal
conversion; add one test-only diagnostic registration, apply an evidenced fix
and repeat Tasks 8-10.

- [ ] **Step 4: Run verification-before-completion**

Use `superpowers:verification-before-completion`. Run:

```powershell
git diff --check
python -m pytest tools/parsergen/tests/test_compare_runtime_lexers.py tools/parsergen/tests/test_legacy_runtime_baseline.py -q
python tools/parsergen/benchmarks/legacy_runtime_baseline.py verify-source --repo .
```

Repeat targeted EDT validation and five YAxUnit modules from Task 8. Record
exact counts and unavailable checks.

- [ ] **Step 5: Commit durable evidence**

```powershell
git add -- docs/superpowers/matrices/2026-08-09-runtime-old-lexer-batch-*.json docs/superpowers/matrices/2026-08-09-runtime-new-lexer-batch-*.json docs/superpowers/matrices/2026-08-09-runtime-batch-regex-scan-*.json docs/superpowers/matrices/2026-08-09-runtime-parser-after-batch-*.json docs/superpowers/matrices/2026-08-09-runtime-batch-regex-lexer.md
git commit -m "perf: publish batch lexer runtime evidence"
```

- [ ] **Step 6: Final handoff**

Report changed files, five fixes, exact EDT/YAxUnit/Python checks, old/new
lexer and parser numbers, durable paths/SHA, existing diagnostic background,
semantic timing availability and remaining peak-memory observability. Keep the
historical test-only lexer as differential oracle until a separate
branch-finishing cleanup decision. Never claim success for unrun timing, zero
matched tests, incompatible sidecars or known correctness blockers.
