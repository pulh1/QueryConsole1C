# Codex Project Environment Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prepare layered Codex instructions, focused Serena context, a clean
documentation layout, and a project-appropriate root `.gitignore` for
QueryConsoleZUP.

**Architecture:** Root instructions define repository-wide behavior, while
`QueryConsoleZUP/AGENTS.md` and `features/AGENTS.md` add scoped EDT/BSL and
Vanessa Automation rules. Serena indexes only the EDT source tree and stores
stable project knowledge as a small graph of memories. User-facing image assets
move out of `docs/`, leaving `docs/superpowers/` for specifications and plans.

**Tech Stack:** Markdown, Git ignore rules, Serena YAML and Markdown memories,
PowerShell, 1C:EDT, BSL, Vanessa Automation.

## Global Constraints

- Default user communication is Russian.
- Use superpowers for design, planning, debugging, TDD, and verification.
- EDT-MCP is the primary source of truth for EDT metadata, forms, module
  structure, applications, and diagnostics.
- Serena is used for symbolic BSL navigation, reference analysis, and durable
  project memory.
- The extension compatibility version is 8.3.24.
- Do not invent metadata, APIs, test commands, or EDT launch configurations.
- Do not modify BSL behavior or metadata objects in this task.
- Do not normalize repository-wide formatting, line endings, encodings, or
  BOMs.
- Git index writes are blocked in the current sandbox. Commit commands below
  are handoff commands for the user; the implementing agent must not claim that
  a commit was created.

---

### Task 1: Separate project documentation from superpowers artifacts

**Files:**

- Move: `docs/img/` to `documentation/img/`
- Modify: `README.MD`
- Create: `.gitignore`

**Interfaces:**

- Consumes: the six existing image files under `docs/img/`
- Produces: valid README image links under `documentation/img/` and a root
  ignore policy that leaves project configuration trackable

- [ ] **Step 1: Verify the move preconditions**

Run:

```powershell
$oldImages = Resolve-Path -LiteralPath 'docs\img'
$newDocumentation = Join-Path (Get-Location) 'documentation'
$newImages = Join-Path $newDocumentation 'img'

$oldImages.Path
Test-Path -LiteralPath $newDocumentation
Test-Path -LiteralPath $newImages
(Select-String -LiteralPath 'README.MD' -Pattern 'docs/img/' -AllMatches).Matches.Count
```

Expected:

- `docs\img` resolves inside the repository;
- `documentation` and `documentation\img` do not exist;
- README contains exactly six `docs/img/` references.

- [ ] **Step 2: Move the binary assets safely**

Run:

```powershell
$repositoryRoot = (Resolve-Path -LiteralPath '.').Path
$sourcePath = (Resolve-Path -LiteralPath 'docs\img').Path
$targetParent = Join-Path $repositoryRoot 'documentation'
$targetPath = Join-Path $targetParent 'img'

if (-not $sourcePath.StartsWith($repositoryRoot,
        [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Source path is outside the repository: $sourcePath"
}

if (Test-Path -LiteralPath $targetPath) {
    throw "Target already exists: $targetPath"
}

New-Item -ItemType Directory -Path $targetParent | Out-Null
Move-Item -LiteralPath $sourcePath -Destination $targetPath
```

Expected: `documentation\img` contains the same six files and `docs\img` no
longer exists. `docs\superpowers` remains in place.

- [ ] **Step 3: Update README image paths**

Use `apply_patch` to replace every literal `docs/img/` occurrence in
`README.MD` with `documentation/img/`. Preserve all other README content and
its existing line-ending convention.

- [ ] **Step 4: Add the root ignore policy**

Create `.gitignore` with this content:

```gitignore
# Local agent state
/.serena/cache/
/.serena/project.local.yml
/.kilo/
/.kilocode/

# Windows and editor temporary files
Thumbs.db
Desktop.ini
*.tmp
*.bak
*.swp
*~

# Eclipse / EDT local workspace state
.metadata/
.recommenders/
*.launch

# Generated 1C artifacts and database dumps
*.cf
*.cfu
*.cfe
*.epf
*.erf
*.dt
*.1CD

# Conventional generated output
/build/
/dist/
/out/
```

- [ ] **Step 5: Verify documentation and ignore behavior**

Run:

```powershell
$oldReferences =
    Select-String -LiteralPath 'README.MD' -Pattern 'docs/img/' -AllMatches
$newReferences =
    Select-String -LiteralPath 'README.MD' `
        -Pattern '!\[[^\]]*\]\((documentation/img/[^)]+)\)' -AllMatches

if ($oldReferences) {
    throw 'README still references docs/img/'
}

if ($newReferences.Matches.Count -ne 6) {
    throw "Expected 6 image references, got $($newReferences.Matches.Count)"
}

$missingImages = foreach ($match in $newReferences.Matches) {
    $relativeImage = $match.Groups[1].Value
    if (-not (Test-Path -LiteralPath $relativeImage)) {
        $relativeImage
    }
}

if ($missingImages) {
    throw "Missing README images: $($missingImages -join ', ')"
}

git -c safe.directory="$((Resolve-Path '.').Path -replace '\\','/')" `
    check-ignore -v -- `
    '.serena/cache/example' `
    '.serena/project.local.yml' `
    '.kilo/example' `
    'sample.cfe'
```

Expected: all four representative local/generated paths are ignored and all
six README image references resolve.

- [ ] **Step 6: Prepare the documentation commit handoff**

The current sandbox cannot write the Git index. Provide, but do not claim to
run, these commands:

```powershell
git add -- '.gitignore' 'README.MD' 'documentation/img' 'docs/img'
git commit -m "chore: separate project docs from agent plans"
```

---

### Task 2: Create layered project instructions

**Files:**

- Create: `AGENTS.md`
- Create: `QueryConsoleZUP/AGENTS.md`
- Create: `features/AGENTS.md`

**Interfaces:**

- Consumes: confirmed project facts from
  `docs/superpowers/specs/2026-07-30-codex-environment-design.md`
- Produces: one repository-wide instruction layer and two non-overlapping
  subtree refinements

- [ ] **Step 1: Write the root instruction file**

Create `AGENTS.md` in Russian with these exact sections and requirements:

```markdown
# Инструкции для агентов

## Общение и достоверность

- По умолчанию отвечать по-русски.
- Сначала сообщать практический результат, затем необходимые детали.
- Не придумывать объекты метаданных, методы, свойства, API, команды тестов и
  конфигурации запуска.
- Перед утверждением проверять актуальное состояние проекта.

## Рабочий процесс

- Использовать подходящие skills superpowers; для изменений сначала
  проектирование и план, для ошибок — систематическая диагностика, перед
  завершением — проверка фактическими командами.
- Начинать с read-only анализа.
- EDT-MCP использовать как основной источник истины для EDT, метаданных, форм,
  модулей, приложений и диагностик.
- Serena использовать для символической навигации по BSL, поиска ссылок и
  проектной памяти.
- Для обычных файлов использовать точечный поиск и минимальные правки.

## Карта репозитория

- `QueryConsoleZUP/` — EDT-проект расширения; дополнительные правила находятся
  в `QueryConsoleZUP/AGENTS.md`.
- `features/` — сценарии Vanessa Automation и эталоны; дополнительные правила
  находятся в `features/AGENTS.md`.
- `QueryExamples/` — примеры запросов `.q1c`.
- `ReportExamples/` — примеры отчётов.
- `documentation/` — пользовательская документация и изображения README.
- `docs/superpowers/` — утверждённые спецификации и планы.

## Безопасность изменений

- Не выполнять широкие или разрушительные операции без явного разрешения.
- Не менять несвязанные пользовательские файлы и не переформатировать целые
  файлы ради точечной задачи.
- Перед перемещением или удалением проверять абсолютные пути и границы
  репозитория.
- Не использовать `git reset --hard` и аналогичные команды.
- Учитывать PowerShell и заключать пути с пробелами и кириллицей в кавычки.

## Проверка и завершение

- Проверять только то, что действительно изменено, и выбирать минимальный
  достаточный набор диагностик и тестов.
- Не считать проект чистым только потому, что изменение не добавило новых
  ошибок: у проекта есть существующий фон диагностик EDT.
- В финале перечислять изменённые файлы, выполненные проверки, оставшиеся
  ошибки и ручные проверки.
- Не утверждать, что тест или диагностика запускались, если запуск не
  выполнялся.
```

- [ ] **Step 2: Write the EDT/BSL subtree instructions**

Create `QueryConsoleZUP/AGENTS.md` in Russian with these exact facts and rules:

```markdown
# Инструкции для EDT-проекта

## Инварианты

- Это расширение конфигурации в формате EDT.
- Совместимость расширения: 1С:Предприятие 8.3.24.
- Встроенный язык: русский BSL, кодировка проекта UTF-8.
- Имя расширения: `QueryConsole1C`; префикс собственных метаданных: `КОНС_`.

## Архитектура

- Запрос проходит этапы лексического анализа, синтаксического разбора,
  построения модели, семантической обработки, преобразования исполняемых
  представлений и исполнения либо генерации кода.
- Главные точки входа искать в обработках `ЛексическийАнализатор`, `Парсер`,
  `ПостроительМоделиЗапроса` и общих модулях `ОбработкаМоделиЗапроса`,
  `ОбработкаПредставлениеЗапросов`, `ИсполнительПредставлений`.
- Перед изменением интерфейса находить определения и все использования.

## Изменение проекта

- Метаданные, формы, СКД, структуру конфигурации и `.mdo` изменять через
  EDT-aware инструменты EDT-MCP.
- BSL-модули сначала читать через EDT-MCP или Serena; изменения делать
  точечно с защитой от устаревшего состояния.
- Сохранять публичные интерфейсы, области модулей, директивы исполнения,
  именование и стиль изменяемого файла.
- Не использовать исключения как обычное ветвление и не добавлять служебное
  логирование без требования задачи.
- В текстах запросов использовать параметры `&Имя`, а не конкатенацию
  пользовательских значений.

## Проверка

- После правки BSL проверять синтаксис и диагностику затронутого модуля или
  объекта.
- После изменения метаданных выполнять точечную ревалидацию объекта.
- Сравнивать результат с существующим фоном диагностик и отдельно сообщать о
  новых проблемах.
- Полную перестройку или обновление информационной базы выполнять только когда
  это действительно требуется задачей.
```

- [ ] **Step 3: Write the Vanessa Automation subtree instructions**

Create `features/AGENTS.md` in Russian with this content:

```markdown
# Инструкции для сценариев Vanessa Automation

## Структура

- `lib/` содержит экспортные переиспользуемые сценарии.
- `ВыполнениеЗапросовВКонсоли/` проверяет выполнение `.q1c` и JSON-эталоны.
- `ГенерацияКодаВКонсоли/` проверяет генерируемый BSL-код.
- `СозданиеЗапросовВКонструкторе/` проверяет построение запросов и текстовые
  эталоны.
- `long/` содержит длительные сценарии.

## Правила изменений

- Сохранять русский Gherkin, существующую табуляцию, UTF-8 и BOM файла, если он
  уже присутствует.
- Переиспользовать шаги из `lib/`, не дублировать общий сценарий.
- При изменении запроса проверять связанные `.feature`, `.q1c`, JSON и
  текстовые эталоны во всех затронутых наборах.
- Не обновлять эталон только ради прохождения теста: сначала подтвердить, что
  новое поведение корректно.
- Пути внутри сценария сохранять в стиле окружающего файла.

## Проверка

- Выбирать минимальный набор сценариев, покрывающий изменение.
- Не считать команду запуска Vanessa Automation или EDT launch-конфигурацию
  частью репозитория: перед запуском обнаруживать доступное внешнее окружение.
- Если команда или конфигурация не найдены, не придумывать их.
- Если автоматический запуск недоступен, перечислять конкретные сценарии и
  эталоны для ручного прогона.
```

- [ ] **Step 4: Check inheritance and forbidden stale references**

Run:

```powershell
$agentFiles = @(
    'AGENTS.md',
    'QueryConsoleZUP\AGENTS.md',
    'features\AGENTS.md'
)

foreach ($agentFile in $agentFiles) {
    if (-not (Test-Path -LiteralPath $agentFile)) {
        throw "Missing instruction file: $agentFile"
    }
}

$stalePattern = '(?i)(codepilot|1[сc][ -]?copilot|openspec)'
$staleMatches = Select-String -Path $agentFiles -Pattern $stalePattern
if ($staleMatches) {
    throw "Stale workflow or integration reference found: $staleMatches"
}

$wrongVersion = Select-String -Path $agentFiles -Pattern '8\.3\.27'
if ($wrongVersion) {
    throw "Incorrect platform version found: $wrongVersion"
}
```

Expected: all files exist; no stale integration/workflow reference or 8.3.27
claim is present.

- [ ] **Step 5: Prepare the instruction commit handoff**

Provide these commands:

```powershell
git add -- 'AGENTS.md' 'QueryConsoleZUP/AGENTS.md' 'features/AGENTS.md'
git commit -m "docs: add layered Codex instructions"
```

---

### Task 3: Focus Serena and persist project knowledge

**Files:**

- Modify: `.serena/project.yml`
- Track: `.serena/.gitignore`
- Track: `.serena/memories/memory_maintenance.md`
- Create through Serena: `.serena/memories/core.md`
- Create through Serena: `.serena/memories/architecture/query_pipeline.md`
- Create through Serena: `.serena/memories/tech_stack.md`
- Create through Serena: `.serena/memories/conventions.md`
- Create through Serena: `.serena/memories/suggested_commands.md`
- Create through Serena: `.serena/memories/task_completion.md`

**Interfaces:**

- Consumes: inspected EDT metadata, module structures, README, project manifest,
  feature layout, and tool availability
- Produces: focused BSL indexing and a reference-linked durable memory graph

- [ ] **Step 1: Narrow the Serena BSL workspace**

Use `apply_patch` to change:

```yaml
ls_workspace_folders:
- "."
```

to:

```yaml
ls_workspace_folders:
- "QueryConsoleZUP/src"
```

Keep `languages: [bsl]`, UTF-8, `ignore_all_files_in_gitignore: true`, and all
other generated Serena settings unchanged.

- [ ] **Step 2: Write `mem:core` through Serena**

Call `write_memory` once with name `core` and dense Markdown containing:

```markdown
# QueryConsoleZUP

- EDT extension source: `QueryConsoleZUP/src`; compatibility 8.3.24, Russian
  BSL, UTF-8, metadata prefix `КОНС_`.
- User-facing query examples: `QueryExamples`; report example:
  `ReportExamples`; Vanessa Automation coverage: `features`.
- Compiler/query pipeline and responsibility boundaries:
  `mem:architecture/query_pipeline`.
- Versions and tooling: `mem:tech_stack`.
- BSL, metadata, examples, and test conventions: `mem:conventions`.
- Available repository commands and known runner gaps:
  `mem:suggested_commands`.
- Required completion checks: `mem:task_completion`.
- EDT-MCP is authoritative for metadata/model state and diagnostics; Serena is
  authoritative for symbolic navigation and these memories.
```

- [ ] **Step 3: Write `mem:architecture/query_pipeline` through Serena**

Call `write_memory` once with name `architecture/query_pipeline` and:

```markdown
# Query processing pipeline

1. `DataProcessors/ЛексическийАнализатор` converts query text to tokens.
2. `DataProcessors/Парсер` performs table-driven parsing and builds the syntax
   representation.
3. `DataProcessors/ПостроительМоделиЗапроса` builds and edits the query model.
4. `CommonModules/ОбработкаМоделиЗапроса` performs semantic traversal and
   calculated-property processing.
5. `CommonModules/ОбработкаПредставлениеЗапросов` recognizes executable-view
   sources and prepares their model.
6. `CommonModules/ИсполнительПредставлений` executes the package or generates
   executable BSL/DCS query text; it may delegate filters/projections or
   materialize temporary tables.

- Model value constructors/utilities live in `МодельЗапроса*` and
  `ЭлементыМодели*` common modules.
- Executable-view descriptions/providers are discovered through provider and
  registry modules; inspect current definitions before extending the
  interface.
- UI entry points are `КонсольЗапросов` and `КонструкторЗапросов`.
```

- [ ] **Step 4: Write `mem:tech_stack` through Serena**

Call `write_memory` once with name `tech_stack` and:

```markdown
# Tech stack

- 1C:EDT configuration-extension project (`V8ExtensionNature`).
- 1C:Enterprise extension compatibility and EDT runtime manifest: 8.3.24.
- Configuration/extension name: `QueryConsole1C`; EDT project:
  `QueryConsoleZUP`; base project:
  `База_разработки_исполняемых_представлений_демо_ЗУП`.
- Russian BSL; project encoding UTF-8.
- Metadata sources are EDT `.mdo` plus BSL/form files under
  `QueryConsoleZUP/src`.
- Acceptance tests: Vanessa Automation/Gherkin in `features`; query fixtures
  use `.q1c`, JSON, and text expectations.
- No repository-local build tool, package manager, Vanessa runner command, or
  versioned EDT launch configuration is defined; discover external/user EDT
  launch state when needed.
```

- [ ] **Step 5: Write `mem:conventions` through Serena**

Call `write_memory` once with name `conventions` and:

```markdown
# Conventions

- Preserve the edited BSL module's regions, execution directives, formatting,
  and public interfaces; avoid whole-file formatting for focused changes.
- Verify metadata/module/API existence and signatures through EDT-MCP or
  Serena before use.
- Metadata, forms, DCS, configuration structure, and `.mdo` changes are
  EDT-aware operations; revalidate touched objects.
- Query text uses `&Параметр`; never concatenate user values into query text.
- Query examples are UTF-8 `.q1c` XML documents containing query text and
  parameter values; preserve XML escaping and existing BOM.
- Vanessa features use Russian Gherkin and tab indentation. Changes may require
  synchronized `.feature`, `.q1c`, JSON, generated-code, and text expectations.
- Existing EDT diagnostics are not a clean baseline; distinguish pre-existing
  problems from regressions.
```

- [ ] **Step 6: Write `mem:suggested_commands` through Serena**

Call `write_memory` once with name `suggested_commands` and:

```markdown
# Suggested commands (PowerShell)

Repository inspection:

`git -c safe.directory="$((Resolve-Path '.').Path -replace '\\','/')" status --short --branch`

Fast file listing/search:

`rg --files`

`$pattern = 'literal-or-regex'; rg -n --glob '!**/.git/**' $pattern`

README documentation-link check:

`Select-String -LiteralPath 'README.MD' -Pattern 'documentation/img/' -AllMatches`

The repository defines no command for running Vanessa Automation and no EDT
launch configuration. Discover the user's external Vanessa setup instead of
inventing a command. Use EDT-MCP for project/module diagnostics.
```

- [ ] **Step 7: Write `mem:task_completion` through Serena**

Call `write_memory` once with name `task_completion` and:

```markdown
# Task completion

- Review `git diff`/`git status`; exclude unrelated user changes.
- BSL edit: syntax-check and inspect EDT diagnostics for each touched module or
  object.
- Metadata edit: use EDT-aware mutation, re-read/revalidate the touched object,
  then compare diagnostics with the pre-existing baseline.
- Public interface edit: find and update all references.
- Query/feature edit: check paired `.feature`, `.q1c`, JSON and text/code
  expectations; run the smallest available Vanessa scenario set.
- If Vanessa execution is unavailable, name the exact scenarios requiring
  manual execution.
- Final response: changed files, checks actually run, remaining errors, and
  unperformed manual checks.
```

- [ ] **Step 8: Validate the memory graph**

Use Serena to:

1. list memories and confirm the seven entries:
   `memory_maintenance`, `core`, `architecture/query_pipeline`, `tech_stack`,
   `conventions`, `suggested_commands`, and `task_completion`;
2. read `mem:core` and confirm all five focused `mem:` references resolve;
3. read each focused memory and confirm it contains no current diagnostic
   counts, task-local branch notes, or placeholders.

Also tell the user that `serena memories check` can be run from the repository
root for an additional reference audit.

- [ ] **Step 9: Prepare the Serena commit handoff**

Provide:

```powershell
git add -- '.serena/.gitignore' '.serena/project.yml' '.serena/memories'
git commit -m "chore: add focused Serena project context"
```

---

### Task 4: Verify the complete Codex environment

**Files:**

- Verify all files created or modified in Tasks 1–3
- Modify only if a verification failure identifies a defect

**Interfaces:**

- Consumes: the completed documentation, instruction hierarchy, ignore policy,
  Serena configuration, and memories
- Produces: an evidence-backed handoff with no source-code or metadata changes

- [ ] **Step 1: Run static repository checks**

Run:

```powershell
$required = @(
    '.gitignore',
    'AGENTS.md',
    'QueryConsoleZUP\AGENTS.md',
    'features\AGENTS.md',
    '.serena\.gitignore',
    '.serena\project.yml',
    '.serena\memories\core.md',
    '.serena\memories\architecture\query_pipeline.md',
    '.serena\memories\tech_stack.md',
    '.serena\memories\conventions.md',
    '.serena\memories\suggested_commands.md',
    '.serena\memories\task_completion.md',
    'documentation\img\architecture_diagram.png'
)

$missing = $required | Where-Object {
    -not (Test-Path -LiteralPath $_)
}
if ($missing) {
    throw "Missing required files: $($missing -join ', ')"
}

$oldDocReferences =
    Select-String -LiteralPath 'README.MD' -Pattern 'docs/img/' -AllMatches
if ($oldDocReferences) {
    throw 'Old documentation image references remain'
}

$environmentFiles = @(
    'AGENTS.md',
    'QueryConsoleZUP\AGENTS.md',
    'features\AGENTS.md',
    '.serena\memories\*.md',
    '.serena\memories\architecture\*.md'
)
$stalePattern = '(?i)(codepilot|1[сc][ -]?copilot|openspec|8\.3\.27)'
$staleMatches = Select-String -Path $environmentFiles -Pattern $stalePattern
if ($staleMatches) {
    throw "Stale environment reference found: $staleMatches"
}
```

- [ ] **Step 2: Confirm no EDT source or feature content changed**

Run:

```powershell
$safeDirectory = (Resolve-Path '.').Path -replace '\\','/'
$sourceDiff = git -c safe.directory="$safeDirectory" diff --name-only -- `
    'QueryConsoleZUP/src' `
    'features/*.feature' `
    'features/**/*.feature' `
    'QueryExamples' `
    'ReportExamples'

if ($sourceDiff) {
    throw "Unexpected source/test change: $($sourceDiff -join ', ')"
}
```

Expected: no BSL, metadata, feature, query-example, or report-example changes.
Because source is untouched, do not run a destructive rebuild, database update,
or Vanessa suite.

- [ ] **Step 3: Review the final Git diff and status**

Run:

```powershell
$safeDirectory = (Resolve-Path '.').Path -replace '\\','/'
git -c safe.directory="$safeDirectory" status --short
git -c safe.directory="$safeDirectory" diff --stat
git -c safe.directory="$safeDirectory" diff --check
```

For untracked text files, read them directly because plain `git diff` does not
show their content. Confirm the final change set is limited to:

- documentation image relocation and README links;
- `.gitignore`;
- three `AGENTS.md` files;
- `.serena` tracked configuration and memories;
- the approved specification and this plan.

- [ ] **Step 4: Prepare the final combined commit handoff**

If the user prefers one commit, provide:

```powershell
git add -- `
    '.gitignore' `
    'AGENTS.md' `
    'README.MD' `
    'documentation' `
    'docs/superpowers' `
    'QueryConsoleZUP/AGENTS.md' `
    'features/AGENTS.md' `
    '.serena/.gitignore' `
    '.serena/project.yml' `
    '.serena/memories'

git commit -m "chore: prepare Codex project environment"
```

- [ ] **Step 5: Report completion accurately**

The final response must state:

- the environment files and documentation paths created or changed;
- that no BSL or metadata behavior was changed;
- exact checks that passed;
- that Vanessa scenarios were not run because no repository-local runner or
  launch configuration exists;
- that commits were not created because the sandbox cannot write `.git`;
- the ready-to-run commit command and `serena memories check` command.
