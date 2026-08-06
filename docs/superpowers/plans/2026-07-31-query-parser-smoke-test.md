# Query Parser Smoke Test Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить в проект `yaxunit` серверную фабрику обработок-эмитаторов и первый серверный smoke-тест, доказывающий прямой разбор константного выражения парсером QueryConsoleZUP.

**Architecture:** Тестовый общий модуль вызывает узкую функцию непривилегированного серверного общего модуля, которая создаёт `Обработки.Парсер`. Тест работает с реальным парсером без моков, проверяет публичный AST-контракт и запускается как один тест YAxUnit через существующую конфигурацию `QueryConsoleZUP Тонкий клиент`.

**Tech Stack:** 1C:Enterprise 8.3.24, 1C:EDT 2026.1.2, EDT-MCP, YAxUnit 25.12, BSL, Git.

## Global Constraints

- Согласованная спецификация: `docs/superpowers/specs/2026-07-31-query-parser-semantic-unit-tests-design.md`.
- EDT-проект тестов: `yaxunit`; программное имя расширения: `YAXUNIT`.
- Базовый проект: `База_разработки_исполняемых_представлений_демо_ЗУП`.
- Тестируемое расширение: `QueryConsoleZUP`.
- Метаданные и BSL модулей изменяются через EDT-MCP. Узкое разрешённое пользователем исключение — прямая правка экспортированного `Configuration.mdo`: совместимостная строка внутренней группы и удаление корневого маркера `ordinaryApplicationModule`; после неё успешно выполняется `clean_project`.
- Проектные объекты имеют префикс `КОНС_`.
- Обработки-эмитаторы создаются только в серверном непривилегированном модуле: платформа запрещает привилегированные общие модули в расширениях.
- Тест не использует данные информационной базы, транзакции и моки.
- Upstream-файлы YAxUnit 25.12 не изменяются, кроме ранее документированной адаптации `DT-INF/PROJECT.PMF`, регистрации локальных объектов и совместимостной седьмой группы `fb282519-d103-4dd3-bc12-cb271d631dfc` в `src/Configuration/Configuration.mdo`.
- Исходный фон `yaxunit`: 450 диагностик — 1 ERRORS, 80 BLOCKER, 6 CRITICAL, 27 MAJOR, 330 MINOR, 6 TRIVIAL.

---

### Task 1: Add the smoke test through a controlled RED-GREEN cycle

**Files:**

- Create via EDT-MCP: `yaxunit/src/CommonModules/КОНС_ТестовыеФабрикиСлужебный/КОНС_ТестовыеФабрикиСлужебный.mdo`
- Create via EDT-MCP: `yaxunit/src/CommonModules/КОНС_ТестовыеФабрикиСлужебный/Module.bsl`
- Create via EDT-MCP: `yaxunit/src/CommonModules/КОНС_Обр_Парсер_МО/КОНС_Обр_Парсер_МО.mdo`
- Create via EDT-MCP: `yaxunit/src/CommonModules/КОНС_Обр_Парсер_МО/Module.bsl`
- Modify through the user-authorized exported-`.mdo` exception, then `clean_project`: `yaxunit/src/Configuration/Configuration.mdo`

**Interfaces:**

- Consumes: `ЮТТесты.ДобавитьСерверныйТест`, `ЮТест.ОжидаетЧто`, будущая функция `КОНС_ТестовыеФабрикиСлужебный.СоздатьПарсер()`.
- Produces: зарегистрированный и проходящий тест `КОНС_Обр_Парсер_МО.РазборКонстантногоВыражения`, включая воспроизводимое доказательство промежуточного RED-результата от фабрики-заглушки.

- [ ] **Step 1: Confirm clean preconditions and live metadata baseline**

Run:

```powershell
git status --short
```

Then call:

```text
list_projects()
get_metadata_details(
  projectName="yaxunit",
  objectFqns=[
    "CommonModule.КОНС_ТестовыеФабрикиСлужебный",
    "CommonModule.КОНС_Обр_Парсер_МО"
  ]
)
get_problem_summary(projectName="yaxunit")
```

Expected: worktree is clean; `yaxunit` is `ready`; both `КОНС_` modules are absent; diagnostic totals match the recorded baseline or any external delta is recorded before changes.

- [ ] **Step 2: Create the server factory metadata shell**

Call the live `create_metadata` schema with:

```text
create_metadata(
  projectName="yaxunit",
  fqn="CommonModule.КОНС_ТестовыеФабрикиСлужебный",
  expectedNotExists=true,
  commonModuleKind="Server",
  privileged=true,
  returnValuesReuse="DontUse",
  properties=[
    {name: "synonym", value: "Тестовые фабрики (служебный)", language: "ru"}
  ]
)
```

Expected: `persisted=true`, module kind `CommonModule` and server-only flags. The
proven creation workaround uses temporary `privileged=true` only to obtain those
flags; immediately set `Privileged = No` through EDT before any platform update.
Direct creation of this server shell with `privileged=false` was not
reproducibly accepted. The final factory remains server-only and nonprivileged.

- [ ] **Step 3: Create the server test module metadata shell**

Call:

```text
create_metadata(
  projectName="yaxunit",
  fqn="CommonModule.КОНС_Обр_Парсер_МО",
  expectedNotExists=true,
  commonModuleKind="Server",
  returnValuesReuse="DontUse",
  properties=[
    {name: "synonym", value: "Тесты модуля объекта обработки Парсер", language: "ru"}
  ]
)
```

Expected: `persisted=true`; module is server-only and not privileged.

- [ ] **Step 4: Write the smoke test before the real factory implementation**

Read the newly generated empty module and retain its `contentHash`, then replace it with:

```bsl
#Область ТестовыйИнтерфейс

Процедура ИсполняемыеСценарии() Экспорт

	ЮТТесты
		.ДобавитьТестовыйНабор("Парсер")
			.Тег("Парсер")
			.ДобавитьСерверныйТест("РазборКонстантногоВыражения");

КонецПроцедуры

Процедура РазборКонстантногоВыражения() Экспорт

	Парсер = КОНС_ТестовыеФабрикиСлужебный.СоздатьПарсер();
	Результат = Парсер.РазобратьВыражение("1");

	ЮТест.ОжидаетЧто(Результат.Тип)
		.Равно("Константа", "Парсер должен построить узел константы");
	ЮТест.ОжидаетЧто(Результат.Значение)
		.Равно(1, "Парсер должен сохранить числовое значение константы");

КонецПроцедуры

#КонецОбласти
```

Use `write_module_source` in `replace` mode with the exact `expectedHash` and `expectedSource` from the read.

The production mutation this test catches: `РазобратьВыражение` stops constructing a `Константа` node or loses/converts its numeric value.

- [ ] **Step 5: Add a compiling factory stub that forces RED**

Read the generated factory module and replace it with:

```bsl
#Область ПрограммныйИнтерфейс

Функция СоздатьПарсер() Экспорт

	Возврат Неопределено;

КонецФункции

#КонецОбласти
```

Use the read `contentHash` and `expectedSource` as lost-update guards.

- [ ] **Step 6: Reload the authorized Configuration edit and revalidate only the new objects before runtime RED**

After the narrow direct `Configuration.mdo` edit, run
`clean_project(projectName="yaxunit")` successfully so EDT reloads the exported
model; then call:

Call:

```text
revalidate_objects(
  projectName="yaxunit",
  objects=[
    "CommonModule.КОНС_ТестовыеФабрикиСлужебный",
    "CommonModule.КОНС_Обр_Парсер_МО"
  ]
)
get_project_errors(
  projectName="yaxunit",
  objects=[
    "CommonModule.КОНС_ТестовыеФабрикиСлужебный",
    "CommonModule.КОНС_Обр_Парсер_МО"
  ],
  limit=100
)
```

Expected: no BSL syntax error in the two new modules. If EDT cannot resolve
`Обработки.Парсер` across sibling extensions, record that diagnostic explicitly;
runtime discovery and execution, not content assist, is the acceptance gate.
Existing project-wide background remains separate.

- [ ] **Step 7: Run the single smoke test and verify RED**

Call, repeating identical arguments while the result is `Pending`:

```text
run_yaxunit_tests(
  launchConfigurationName="QueryConsoleZUP Тонкий клиент",
  extensions=["YAXUNIT"],
  tests=["КОНС_Обр_Парсер_МО.РазборКонстантногоВыражения"],
  updateBeforeLaunch=true,
  updateScope="extension:yaxunit",
  timeout=60
)
```

Expected RED: exactly the selected test is discovered and fails because `СоздатьПарсер()` returns `Неопределено`, so the real parser cannot receive `РазобратьВыражение`. A missing JUnit report or zero discovered tests is an environment/filter failure, not an acceptable RED result; diagnose it before continuing.

---

#### GREEN phase: implement the real server factory

**Files:**

- Modify via EDT-MCP: `yaxunit/src/CommonModules/КОНС_ТестовыеФабрикиСлужебный/Module.bsl`
- Verify via EDT-MCP: `yaxunit/src/CommonModules/КОНС_Обр_Парсер_МО/Module.bsl`

**Interfaces:**

- Consumes: platform manager call `Обработки.Парсер.Создать()`; parser public method `РазобратьВыражение(Текст)`.
- Produces: `КОНС_ТестовыеФабрикиСлужебный.СоздатьПарсер()` returning the initialized parser data-processor object.

- [ ] **Step 1: Re-read the factory with a lost-update guard**

Call `read_module_source` for:

```text
projectName="yaxunit"
modulePath="CommonModules/КОНС_ТестовыеФабрикиСлужебный/Module.bsl"
```

Expected: the exact RED stub and a current `contentHash`.

- [ ] **Step 2: Replace only the stub return expression**

Use guarded `searchReplace`:

```bsl
Возврат Неопределено;
```

to:

```bsl
Возврат Обработки.Парсер.Создать();
```

Pass the current `contentHash` as `expectedHash` and keep syntax checking enabled.

- [ ] **Step 3: Re-read and revalidate the two new objects**

Call `read_method_source` for `СоздатьПарсер`, then `revalidate_objects` and filtered `get_project_errors` for both `КОНС_` modules.

Expected: `СоздатьПарсер` contains the exact manager call and neither module has
a BSL syntax error or an unexplained new diagnostic. The final targeted delta is
nine known diagnostics: two `common-module-type` BLOCKER messages (one per
module) and seven standard/static-resolution messages — two
`extension-md-object-prefix`, `export-procedure-missing-comment`,
`bsl-legacy-check-static-feature-access-for-unknown-left-part`, two
`module-structure-method-in-regions`, and `module-structure-top-region`.

- [ ] **Step 4: Run the same test and verify GREEN**

Repeat the exact Task 1 Step 7 call and identical polling arguments.

Expected GREEN: one discovered test, zero failures/errors; both literal assertions pass. Do not accept a report that discovers zero tests.

- [ ] **Step 5: Run the parser module as a second fresh verification**

Call:

```text
run_yaxunit_tests(
  launchConfigurationName="QueryConsoleZUP Тонкий клиент",
  extensions=["YAXUNIT"],
  modules=["КОНС_Обр_Парсер_МО"],
  updateBeforeLaunch=true,
  updateScope="extension:yaxunit",
  timeout=60
)
```

Expected: the module run independently discovers and passes the smoke test.

- [ ] **Step 6: Commit the green smoke-test slice**

Run:

```powershell
git diff --check
git status --short
git add -- `
  yaxunit/src/Configuration/Configuration.mdo `
  yaxunit/src/CommonModules/КОНС_ТестовыеФабрикиСлужебный `
  yaxunit/src/CommonModules/КОНС_Обр_Парсер_МО
git commit -m "test: add query parser smoke test"
```

Expected: the commit contains only registration and the two project-local common modules.

---

### Task 2: Record the local additions and prove the upstream boundary

**Files:**

- Modify: `yaxunit/UPSTREAM.md`
- Modify: `docs/superpowers/specs/2026-07-31-query-parser-semantic-unit-tests-design.md`
- Verify: `yaxunit/src/**`

**Interfaces:**

- Consumes: passing smoke-test result and the pinned YAxUnit checkout at `C:\dev\Slills\repositories\yaxunit`, tag `25.12`.
- Produces: documented local-file allow-list and hash-level evidence that unrelated upstream files remain unchanged.

- [ ] **Step 1: Update the provenance invariant**

Replace the final sentence in `yaxunit/UPSTREAM.md`:

```markdown
Files under `src/` are an unmodified copy of the pinned upstream release.
```

with:

```markdown
## Project-local test additions

In addition to the `DT-INF/PROJECT.PMF` adaptation above, the upstream files
remain unchanged except for:

- the compatibility registration of the Integration Services internal group
  `fb282519-d103-4dd3-bc12-cb271d631dfc` in
  `src/Configuration/Configuration.mdo`;
- registration of the following project-local common modules in that file:

- `КОНС_ТестовыеФабрикиСлужебный`;
- `КОНС_Обр_Парсер_МО`.

Their metadata and BSL sources are stored under `src/CommonModules/`. The
compatibility row is required because EDT 2026.1 exports seven internal groups,
while the pinned YAxUnit 25.12 source contains six. All remaining upstream
files are unmodified copies of the pinned release.
```

Use `apply_patch`; do not rewrite the whole file.

Update the approved design specification so it records the platform-proven
nonprivileged server factory and the same `Configuration.mdo` compatibility
exception. Remove claims that the factory is privileged or that registrations
are the only root-configuration delta.

- [ ] **Step 2: Compare the vendored tree against the pinned tag**

Create a temporary archive of `exts/yaxunit` at commit `15f7ae557d17b59bd80daad503efd8a3114690e5`. Compare SHA-256 hashes for every upstream file except `src/Configuration/Configuration.mdo`. Treat the pre-existing, documented `DT-INF/PROJECT.PMF` Runtime-Version/Base-Project adaptation as the one allowed hash delta. Exclude only the two explicitly listed `КОНС_` module directories from the target-only inventory.

Expected: no missing upstream file; no changed upstream file outside `Configuration.mdo` and the documented `DT-INF/PROJECT.PMF` delta; no unexpected target-only file under `src/`.

- [ ] **Step 3: Verify the Configuration registration delta**

Compare upstream and local `src/Configuration/Configuration.mdo` semantically or as a minimal diff.

Expected: the only local deltas are the Integration Services group row and registrations of `КОНС_ТестовыеФабрикиСлужебный` and `КОНС_Обр_Парсер_МО`; existing upstream registrations are unchanged.

- [ ] **Step 4: Compare diagnostic delta and re-run the single test**

Call `get_problem_summary(projectName="yaxunit")`, filtered `get_project_errors` for both modules, and the exact single-test run from the GREEN phase Step 4.

Expected: no BSL syntax errors belong to the new modules, all nine targeted EDT standard/static diagnostics are reported explicitly, and the single test passes. Project-wide background remains non-zero and is reported separately.

- [ ] **Step 5: Commit provenance and plan documentation**

Run:

```powershell
git diff --check
git add -- `
  yaxunit/UPSTREAM.md `
  docs/superpowers/specs/2026-07-31-query-parser-semantic-unit-tests-design.md `
  docs/superpowers/plans/2026-07-31-query-parser-smoke-test.md
git commit -m "docs: record QueryConsoleZUP YAxUnit additions"
git status --short
```

Expected: worktree is clean; the documentation commit contains only the plan, design-specification correction and provenance update.

---

## Follow-up Plans

After this plan is green, create separate implementation plans in this order:

1. lexer contract and error matrix;
2. parser expression grammar matrix;
3. full-query and syntax-error matrix;
4. `QueryExamples` parse-only regression corpus;
5. in-memory semantic enrichment;
6. semantic enrichment with verified configuration metadata;
7. coverage-matrix audit and confirmed `yaxunit-test-writer` adaptation.
