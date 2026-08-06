# Parser Generator Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Перенести Python-генератор LL(k)-парсера в QueryConsoleZUP и доказать его эквивалентность текущему production-парсеру без изменения BSL-артефактов.

**Architecture:** Python-пакет, тесты, benchmarks и грамматика живут в `tools/parsergen`; корневой `parsergen.toml` связывает их с EDT-обработкой `Парсер`. Production-каталог используется только для read-only parity-проверки.

**Tech Stack:** Python 3.11+, стандартная библиотека, pytest, TOML, EDT/BSL, YAxUnit для существующей регрессии.

## Global Constraints

- Не изменять `QueryConsoleZUP/src/DataProcessors/Парсер` в этой ветке.
- Не добавлять поддержку левой рекурсии и не оптимизировать грамматику.
- Сохранять алгоритмическое поведение и CLI исходного генератора.
- Не выполнять commit/push без отдельного указания пользователя.
- Текущую ветку считать подготовленной пользователем; отдельный worktree не создавать.
- Из-за недоступного shell каждый фактически не выполненный Git/Python/YAxUnit шаг явно отметить в итогах.

---

## Task 1: Перенести Python-пакет без изменения поведения

**Files:**
- Create: `tools/parsergen/pyproject.toml`
- Create: `tools/parsergen/src/parsergen/**/*.py`
- Create: `tools/parsergen/src/parsergen/templates/parser_module.bsl`
- Create: `tools/parsergen/benchmarks/*.py`

- [x] Скопировать package metadata, CLI и модули из `QueryConsoleDevelopmentTools`.
- [x] Сохранить Python >= 3.11 и optional dependency pytest.
- [x] Сохранить console entry point `parsergen = parsergen.cli:main`.
- [x] Проверить отсутствующие или внешние импорты точечным поиском.

## Task 2: Сделать грамматику и конфигурацию самодостаточными

**Files:**
- Create: `tools/parsergen/grammar/query-language.grammar`
- Create: `parsergen.toml`
- Modify: `tools/parsergen/tests/test_config.py`
- Modify: `tools/parsergen/tests/test_repository_grammar.py`
- Modify: `tools/parsergen/tests/test_reference_parser.py`

- [x] Скопировать текущую расширенную грамматику без смысловых изменений.
- [x] Настроить корневой `parsergen.toml` на локальную грамматику и `QueryConsoleZUP/src/DataProcessors/Парсер`.
- [x] Сохранить `lookahead = 2` и точки входа `Разобрать`/`РазобратьВыражение`.
- [x] Перепривязать репозиторные тесты к новой структуре каталогов.
- [x] Не записывать результаты генерации в production-каталог.

## Task 3: Перенести тестовый контур и parity-оракул

**Files:**
- Create: `tools/parsergen/tests/**/*.py`
- Create: `tools/parsergen/tests/fixtures/reference_parser/**`

- [x] Перенести unit-тесты анализа, грамматики, генерации, CLI, конфигурации и кодека ValueTable.
- [x] Перенести эталонные артефакты для детерминированного сравнения.
- [x] Проверить, что тесты не содержат ссылок на старый репозиторий.
- [x] Выполнить Python-тесты одним пакетом из `tools/parsergen`.

## Task 4: Зафиксировать архитектуру и результаты исследований

**Files:**
- Create: `docs/architecture/parser-generator.md`
- Create: `docs/research/parser-generator-research.md`
- Create: `docs/decisions/2026-08-06-parser-generator-ownership.md`

- [x] Описать pipeline: разбор грамматики, разрешение символов, nullable/FIRST/FOLLOW/SELECT, валидация, BSL-кодогенерация, сериализация ValueTable.
- [x] Зафиксировать свойства worklist/delta и ограничения текущей реализации.
- [x] Отделить подтверждённые факты от будущих направлений: левая рекурсия и семантический анализ.
- [x] Указать происхождение перенесённой реализации и дату миграции.

## Task 5: Выполнить проверку миграции

**Files:**
- Verify only: `tools/parsergen/**`
- Verify only: `QueryConsoleZUP/src/DataProcessors/Парсер/**`

- [x] Выполнить полный Python test suite.
- [x] Выполнить анализ репозиторной грамматики с `k=2`.
- [x] Сгенерировать три артефакта во временный каталог.
- [x] Выполнить `generate --check` против production-парсера.
- [x] Выполнить `git diff --check` и проверить состав изменений.
- [x] При наличии доступного раннера выполнить существующую регрессию YAxUnit; иначе оставить точную ручную проверку.

## Plan Self-Review

- План не меняет production-парсер и не смешивает миграцию с будущей поддержкой левой рекурсии.
- Все известные входы и выходы генератора имеют явные пути.
- Есть два независимых оракула: Python fixture parity и read-only `generate --check` production-артефактов.
- Невыполнимые из текущего окружения проверки нельзя засчитать как пройденные.
