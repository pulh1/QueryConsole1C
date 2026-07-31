---
name: queryconsole-bsl-development
description: Use when implementing or refactoring existing QueryConsoleZUP BSL, expression-model contracts, visitor implementations, data-processor services, or distributed BSL behavior.
---

# BSL-разработка QueryConsoleZUP

Безопасно изменяй существующее поведение малой проверяемой правкой. EDT-MCP — источник истины о живом EDT-проекте; Serena используй только для символической навигации.

Не применяй этот skill для read-only исследования (используй `queryconsole-code-exploration`), текста прикладного запроса или чистой работы с метаданными.

## Workflow

1. Прочитай текущий контракт, usages, callers и окружающий стиль.
2. Определи участие visitor, factory, service и dynamic plugin.
3. Если затронута модель выражений или data processor, прочитай [architecture contracts](references/project-architecture-contracts.md) и заново установи живой состав участников.
4. Установи границы client/server, транзакции, привилегий и side effects.
5. Прочитай точный текущий фрагмент и получи через EDT-MCP актуальную revision/hash. Сверяйся с живой схемой инструмента, а не с запомненными именами методов или аргументов.
6. Выполни минимальную guarded-запись доступными сейчас средствами EDT-MCP. Если живая схема недоступна, не конструируй предполагаемый вызов: отдельно сообщи недоступную проверку. Для локальной правки не заменяй целый модуль; не редактируй XML вручную и не записывай Serena memories.
7. Снова прочитай результат, проверь references и syntax, затем сравни diagnostic delta с baseline затронутых объектов.
8. В отчёте раздельно укажи выполненные и недоступные проверки.

## Quick reference

| Задача | Обязательная проверка |
| --- | --- |
| Новый или изменённый тип выражения | factory → dispatcher → template → все concrete visitors → callers |
| Data processor или provider | service/создание/инициализация → dynamic contract |
| Любая запись BSL | live revision/hash → минимальная запись → re-read → diagnostics delta |

## Common mistakes

- Считать исторические counts полным и вечным составом: перед каждой правкой находи фактические участники.
- Менять только factory или только dispatcher и пропускать visitor contract и callers.
- Выполнять запись по устаревшему исходнику без revision guard.
- Называть непроверенные EDT-MCP методы или каталоги аргументов вместо описания нужной операции.
- Требовать нулевых ошибок во всём проекте вместо сравнения diagnostic delta с исходным фоном.
