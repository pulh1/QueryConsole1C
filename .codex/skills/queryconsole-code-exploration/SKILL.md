---
name: queryconsole-code-exploration
description: Use when investigating existing QueryConsoleZUP BSL, tracing entry points, usages, call hierarchy, expression visitors, data processors, or dynamic processing contracts without changing behavior.
---

# Исследование кода QueryConsoleZUP

Главный принцип: сначала собирай доказательства из живого проекта, затем формулируй выводы. Работай только на чтение: не записывай модули, метаданные, файлы или Serena memories.

## Workflow

1. Сформулируй проверяемый вопрос и scope: поведение, входная точка, предполагаемые модули и границы исследования.
2. Через EDT-MCP обнаружь EDT project и нужные modules. EDT-MCP — источник истины о проекте и его модели.
3. Используй Serena только для symbolic navigation: поиск символов, определений, references и callers. Не создавай и не изменяй memory.
4. Проследи definitions, references и call hierarchy до наблюдаемой точки входа и обратно к вызывающим местам.
5. Для expression model составь цепочку `factory → dispatcher → template → concrete visitors → callers`. Найди полный visitor template, сверяй callbacks со всеми concrete visitors и исследуй внешние callers обхода дерева.
6. Для data processor составь цепочку `manager module → object module → creation/initialization → dynamic provider`; проверь связанные динамические контракты.
7. Верни результат отдельными разделами: «Факты» с путями/символами, «Гипотезы» и «Пробелы» с дальнейшими read-only проверками.

## Quick reference

- EDT-MCP: проект, metadata, forms, modules и diagnostics.
- Serena: символы, usages, references и иерархия вызовов BSL.
- Обычный точечный поиск: тексты, конфигурация и несимволические связи.

## Common mistakes

- Не считай первую найденную реализацию полным контрактом: найди template и все concrete visitors.
- Не подменяй факт архитектурным предположением; помечай непроверенное гипотезой.
- Не ограничивай data processor одним модулем: проверь создание, инициализацию и dynamic provider.
- Не дублируй архитектурные counts из BSL reference; получай актуальные связи из живого проекта.
