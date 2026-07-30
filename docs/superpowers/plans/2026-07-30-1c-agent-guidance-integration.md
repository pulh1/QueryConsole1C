# 1C Agent Guidance Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use
> superpowers:subagent-driven-development (recommended) or
> superpowers:executing-plans to implement this plan task-by-task. Steps use
> checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить в QueryConsoleZUP компактный слой 1С-инструкций и пять
project-local skills, согласованных с EDT-MCP и фактической архитектурой
проекта.

**Architecture:** Постоянные инварианты остаются в scoped `AGENTS.md`, а
пошаговые процессы загружаются только через skills. EDT-MCP остаётся основным
маршрутом чтения и изменения EDT-проекта; Serena используется только для
символической навигации. Распределённые visitor-контракты и контракты обработок
описываются в отдельном reference BSL-skill.

**Tech Stack:** Markdown, YAML, Codex project-local skills, 1C:EDT, BSL,
EDT-MCP, Serena, Git ignore rules.

## Global Constraints

- Не изменять BSL, метаданные, формы, СКД, `.feature`, `.q1c` и эталоны.
- Не создавать и не обновлять Serena memories.
- Не добавлять материалы, skills, references или настройки unit-тестирования.
- Не расширять корневой `AGENTS.md` и не изменять `features/AGENTS.md`.
- Не копировать текст или код из источников без лицензии; использовать только
  самостоятельно сформулированные идеи.
- Для MIT-источников сохранить авторство, URL, ревизии и текст лицензии.
- Не фиксировать полный каталог аргументов EDT-MCP: перед применением читать
  актуальную схему и on-demand guide.
- Не создавать конкурирующий маршрут ручного изменения EDT XML.
- Не выполнять commit: текущая sandbox-сессия не может писать в `.git`.

---

### Task 1: Scoped-инструкции, ignore policy и provenance

**Files:**

- Modify: `QueryConsoleZUP/AGENTS.md`
- Modify: `.gitignore`
- Create: `THIRD_PARTY_NOTICES.md`

**Interfaces:**

- Consumes: подтверждённые архитектурные контракты из утверждённой спецификации
- Produces: короткие постоянные инварианты, локальную ignore policy и
  лицензионный provenance

- [ ] **Step 1: Обновить scoped `AGENTS.md`**

Добавить в существующие разделы только следующие правила:

```markdown
- Перед записью BSL читать актуальный код и применять revision guard; не
  заменять целый модуль ради точечной правки.
- При изменении модели выражений сверять фабрику узла, обходчик, шаблон полного
  посетителя и все конкретные visitor-реализации.
- Не считать обработки только UI-объектами: проверять manager module, object
  module, создание, инициализацию и динамические контракты.
- Рекомендации по запросам применять после проверки семантики и диагностики
  EDT, а не как безусловные запреты.
- После изменения перечитывать результат и сравнивать новые диагностики с
  исходным фоном.
- Подробные процессы исследования, BSL-разработки, запросов, метаданных и ревью
  брать из project-local skills.
```

- [ ] **Step 2: Дополнить `.gitignore`**

Добавить отдельный раздел:

```gitignore
# Local MCP and skill runtime state
/.mcp.json
/.v8-project.json
/.codex/cache/
*.log
```

Не игнорировать `.codex/skills`, `agents/openai.yaml`, документацию и EDT
launch-конфигурации, если они будут намеренно добавлены в репозиторий.

- [ ] **Step 3: Создать `THIRD_PARTY_NOTICES.md`**

Зафиксировать:

- `Nikolay-Shirokov/cc-1c-skills`, ревизия
  `1563973636f185ee6463995c98a133571d0f7eea`, copyright
  `2025-2026 Nick Shirokov`, MIT;
- `Desko77/claude-code-skills-1c`, ревизия
  `fb70461f10459670f93889da486b9fce5d773191`, copyright `2026 Desko77`,
  MIT;
- полный общий текст MIT License;
- `Dach-Coin/claude_rules_1c` и
  `Dach-Coin/1c_dev_standarts_for_ai_agents` как research-only источники без
  переноса текста, кода, примеров или уникальной структуры;
- перечень пяти адаптированных project-local skills.

- [ ] **Step 4: Проверить границы Task 1**

Проверить, что root `AGENTS.md` и `features/AGENTS.md` байтово не изменились,
а новые правила в `QueryConsoleZUP/AGENTS.md` не дублируют длинные workflows.

---

### Task 2: Skill `queryconsole-code-exploration`

**Files:**

- Create: `.codex/skills/queryconsole-code-exploration/SKILL.md`
- Create: `.codex/skills/queryconsole-code-exploration/agents/openai.yaml`

**Interfaces:**

- Consumes: EDT-MCP project/module/symbol tools and Serena symbolic navigation
- Produces: read-only evidence map of entry points, calls, contracts and gaps

- [ ] **Step 1: RED — проверить поведение без skill**

Перед созданием файлов дать свежему агенту задачу:

```text
В QueryConsoleZUP проследи, как выражение проходит от фабрики узла до
семантического анализа. Ничего не изменяй. Покажи подтверждённые точки входа,
visitor-реализации и пробелы исследования.
```

Зафиксировать, пропустил ли агент хотя бы один слой: фабрики узлов, dispatcher,
полный visitor-контракт, конкретные visitors, callers или разграничение фактов
и гипотез.

- [ ] **Step 2: Инициализировать skill**

Запустить системный `init_skill.py` с именем
`queryconsole-code-exploration`, project-local путём `.codex/skills` и
интерфейсом:

```yaml
display_name: "Исследование кода QueryConsoleZUP"
short_description: "Навигация по архитектуре и вызовам BSL"
default_prompt: "Используй $queryconsole-code-exploration, чтобы проследить архитектуру и вызовы для выбранного поведения."
```

- [ ] **Step 3: Написать минимальный `SKILL.md`**

Frontmatter description начинается с `Use when` и перечисляет только триггеры:
разобраться в существующем BSL, найти точку входа, usages/call hierarchy,
проследить visitor или динамический processing contract.

Body задаёт read-only workflow:

1. сформулировать вопрос и границы;
2. обнаружить проект и модули через EDT-MCP;
3. использовать Serena только для символической навигации;
4. проследить определения, ссылки и call hierarchy;
5. для выражений сопоставить factory → dispatcher → template → visitors;
6. для обработок сопоставить manager/object modules → creation/init → provider;
7. вернуть факты, гипотезы и непроверенные участки раздельно.

- [ ] **Step 4: GREEN — validate и forward-test**

Запустить `quick_validate.py`, проверить frontmatter и повторить RED-сценарий с
явным использованием skill. Успех: ответ содержит все шесть архитектурных
слоёв, не изменяет файлы и не предлагает запись в Serena memories.

---

### Task 3: Skill `queryconsole-bsl-development`

**Files:**

- Create: `.codex/skills/queryconsole-bsl-development/SKILL.md`
- Create:
  `.codex/skills/queryconsole-bsl-development/references/project-architecture-contracts.md`
- Create: `.codex/skills/queryconsole-bsl-development/agents/openai.yaml`

**Interfaces:**

- Consumes: актуальный BSL, EDT-MCP revision guard, platform docs and
  `project-architecture-contracts.md`
- Produces: минимальные безопасные BSL-изменения с проверкой распределённых
  контрактов

- [ ] **Step 1: RED — проверить поведение без skill**

Дать свежему агенту read-only задачу:

```text
Составь change map для добавления нового типа выражения в QueryConsoleZUP.
Код не меняй. Укажи обязательные точки синхронизации, безопасный способ записи
BSL и проверки после изменения.
```

Зафиксировать пропуски factory/dispatcher/template/concrete visitors,
revision guard, re-read и diagnostic baseline.

- [ ] **Step 2: Инициализировать skill и reference**

Создать `queryconsole-bsl-development` с интерфейсом:

```yaml
display_name: "BSL-разработка QueryConsoleZUP"
short_description: "Безопасные изменения BSL и контрактов"
default_prompt: "Используй $queryconsole-bsl-development, чтобы безопасно реализовать изменение BSL в QueryConsoleZUP."
```

Reference должен содержать только подтверждённую карту:

- 91 factory functions в `ЭлементыМоделиЗапроса`;
- 29 dispatch types и 59 callbacks текущего expression walker;
- template visitor и три полные concrete implementations;
- 37 data processors;
- 19 `Представление*` implementations с четырьмя обязательными и двумя
  capability-dependent methods;
- динамическое разрешение через
  `Обработки[ОписаниеПредставления.ИмяОбработчика]`;
- checklist синхронизации и правило повторного обнаружения фактического состава.

- [ ] **Step 3: Написать минимальный `SKILL.md`**

Workflow:

1. прочитать контракт, usages и окружающий стиль;
2. определить visitor/factory/service/plugin participation;
3. прочитать архитектурный reference, если затронута модель или обработка;
4. определить client/server и transaction boundaries;
5. получить актуальный hash/revision;
6. выполнить минимальную guarded write через EDT-MCP;
7. re-read, проверить references, syntax и diagnostic delta;
8. сообщить выполненные и недоступные проверки.

Skill не должен срабатывать на чистое исследование без изменений, конкретный
текст запроса или чистую metadata-операцию.

- [ ] **Step 4: GREEN — validate и forward-test**

Запустить `quick_validate.py` и повторить RED-сценарий со skill. Успех:
получен полный change map, отсутствуют ручной XML, whole-module replacement и
неподтверждённые API.

---

### Task 4: Skill `queryconsole-query-development`

**Files:**

- Create: `.codex/skills/queryconsole-query-development/SKILL.md`
- Create: `.codex/skills/queryconsole-query-development/agents/openai.yaml`

**Interfaces:**

- Consumes: `.q1c`/BSL query text, actual metadata and EDT-MCP query validation
- Produces: semantically preserved query change and explicit validation report

- [ ] **Step 1: RED — проверить trigger boundary**

Дать свежему агенту две задачи без skill:

```text
Опиши безопасный workflow оптимизации конкретного запроса из QueryExamples.
```

```text
Нужно изменить внутренний parser QueryConsoleZUP, но конкретный текст запроса
не меняется. Следует ли включать workflow разработки прикладных запросов?
```

Зафиксировать выдуманные metadata fields, безусловные performance rewrites или
ошибочное включение query workflow для parser-only изменения.

- [ ] **Step 2: Инициализировать и написать skill**

Интерфейс:

```yaml
display_name: "Разработка запросов QueryConsoleZUP"
short_description: "Изменение и диагностика запросов 1С"
default_prompt: "Используй $queryconsole-query-development, чтобы изменить или проверить конкретный запрос 1С."
```

Workflow:

1. определить query artifact и связанные inputs/expectations;
2. получить реальные metadata names and types;
3. сохранить параметры, dialect и семантику;
4. применять performance heuristics только с обоснованием;
5. валидировать запрос через актуальный EDT-MCP;
6. синхронизировать входы и эталоны в границах задачи;
7. сообщить фактические проверки.

Явно исключить automatic trigger для lexer/parser/AST/model/generator internals,
если не меняется конкретный query text.

- [ ] **Step 3: GREEN — validate и forward-test**

Запустить `quick_validate.py`, повторить оба сценария со skill. Успех:
прикладной query workflow применяется только в первом сценарии.

---

### Task 5: Skill `queryconsole-edt-metadata`

**Files:**

- Create: `.codex/skills/queryconsole-edt-metadata/SKILL.md`
- Create: `.codex/skills/queryconsole-edt-metadata/agents/openai.yaml`

**Interfaces:**

- Consumes: live EDT-MCP tool guides, metadata details, references and
  diagnostic baseline
- Produces: minimal EDT-aware metadata/form/DCS/role/subsystem operation

- [ ] **Step 1: RED — проверить metadata workflow без skill**

Дать свежему агенту задачу:

```text
Составь безопасный план добавления новой обработки-реализации исполняемого
представления. Ничего не изменяй. Учти EDT-MCP и существующий динамический
контракт обработок.
```

Зафиксировать предложения ручного `.mdo`/XML, пропуск object/manager modules,
provider registration, post-read или revalidation.

- [ ] **Step 2: Инициализировать и написать skill**

Интерфейс:

```yaml
display_name: "EDT-метаданные QueryConsoleZUP"
short_description: "Метаданные, формы и СКД через EDT-MCP"
default_prompt: "Используй $queryconsole-edt-metadata, чтобы безопасно изменить метаданные QueryConsoleZUP через EDT-MCP."
```

Workflow:

1. определить project/object/postcondition;
2. прочитать live tool guide;
3. прочитать объект, owner и references;
4. для data processor определить UI/service/plugin role и оба модуля;
5. выполнить минимальную EDT-aware operation;
6. re-read/revalidate и сравнить diagnostics;
7. сообщить ограничения render/runtime проверки.

- [ ] **Step 3: GREEN — validate и forward-test**

Запустить `quick_validate.py` и повторить RED-сценарий. Успех: отсутствует
ручной XML, а dynamic processing contract включён в change map.

---

### Task 6: Skill `queryconsole-1c-review`

**Files:**

- Create: `.codex/skills/queryconsole-1c-review/SKILL.md`
- Create: `.codex/skills/queryconsole-1c-review/agents/openai.yaml`

**Interfaces:**

- Consumes: exact diff, EDT-MCP evidence, references, diagnostics and related
  artifacts
- Produces: severity-ordered, reproducible findings and explicit verification
  gaps

- [ ] **Step 1: RED — проверить review shape без skill**

Дать свежему агенту задачу:

```text
Проведи read-only review гипотетического изменения: в expression walker
добавлен новый тип и два callbacks, но изменены только walker и один visitor.
Сформулируй findings и пробелы проверки.
```

Зафиксировать, требует ли ответ точное место, сценарий проявления,
доказательство, severity и minimal fix; проверяет ли он template и все visitor
implementations.

- [ ] **Step 2: Инициализировать и написать skill**

Интерфейс:

```yaml
display_name: "Ревью 1С-кода QueryConsoleZUP"
short_description: "Доказательное ревью BSL и метаданных"
default_prompt: "Используй $queryconsole-1c-review, чтобы провести доказательное ревью изменений QueryConsoleZUP."
```

Review workflow:

1. установить точный diff и scope;
2. найти public interfaces and usages;
3. проверить visitor/factory/dynamic processing completeness;
4. проверить correctness, client/server, transactions and security;
5. проверить queries без безусловных эвристик;
6. сравнить EDT diagnostics with baseline;
7. вывести только доказанные findings по severity;
8. отдельно вывести verification gaps.

Каждый finding имеет location, scenario, evidence и minimal fix.

- [ ] **Step 3: GREEN — validate и forward-test**

Запустить `quick_validate.py` и повторить RED-сценарий. Успех: неполный
visitor-контракт оформлен как доказанный finding, а неизвестные данные — как
verification gaps.

---

### Task 7: Интегральная проверка окружения

**Files:**

- Verify: all files from Tasks 1–6
- Modify only when a verification result proves a defect

**Interfaces:**

- Consumes: completed instructions, skills, reference, notices and ignore rules
- Produces: evidence-backed handoff with no product or memory changes

- [ ] **Step 1: Проверить skill folders**

Для каждого из пяти skills:

- запустить `quick_validate.py`;
- проверить `name == folder name`;
- проверить, что description начинается с `Use when`;
- проверить `agents/openai.yaml`, включая `$skill-name` в `default_prompt`;
- проверить отсутствие placeholders и лишних README/CHANGELOG файлов;
- проверить размер `SKILL.md` — целевой максимум 500 слов.

- [ ] **Step 2: Проверить routing**

Убедиться, что:

- exploration — read-only understanding;
- BSL development — implementation/refactoring BSL;
- query development — concrete query text;
- EDT metadata — metadata/form/DCS/role/subsystem mutations;
- review — review request.

Пересечения должны разрешаться правилом «более узкий skill имеет приоритет».

- [ ] **Step 3: Проверить границы репозитория**

Проверить `git status`, `git diff --check` и список изменённых путей. Допустимы
только:

- `.gitignore`;
- `QueryConsoleZUP/AGENTS.md`;
- `THIRD_PARTY_NOTICES.md`;
- `.codex/skills/**`;
- утверждённая specification и этот plan.

Отдельно подтвердить отсутствие изменений в:

- `QueryConsoleZUP/src/**`;
- `features/**`;
- `QueryExamples/**`;
- `ReportExamples/**`;
- `.serena/**`;
- root `AGENTS.md`.

- [ ] **Step 4: Проверить content constraints**

Проверить отсутствие:

- исключённых интеграций;
- unit-test/YAXUnit материалов вне фразы о deferred scope в spec/plan;
- ручных XML workflows;
- выдуманных команд EDT-MCP;
- копирования текста из research-only источников;
- устаревшего platform version `8.3.27`.

- [ ] **Step 5: Финальное ревью**

Провести отдельное review спецификации, плана, scoped-инструкций и всех skills
на противоречия, trigger ambiguity, чрезмерно жёсткие правила и неподтверждённые
факты. Исправить только доказанные проблемы и повторить проверки Tasks 7.1–7.4.
