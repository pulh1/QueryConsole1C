---
name: queryconsole-edt-metadata
description: Use when changing 1C metadata objects, forms, DCS/SKD, roles, subsystems, commands, attributes, tabular sections, or data-processor metadata in QueryConsoleZUP.
---

# EDT-метаданные QueryConsoleZUP

Изменяй метаданные только через EDT-MCP: он является источником истины. Никогда не редактируй `.mdo` или XML вручную.

## Workflow

1. Определи EDT-проект, объект, требуемую мутацию и наблюдаемое постусловие.
2. Открой живую справку EDT-MCP для точной нужной операции. Не выдумывай имена инструментов, параметры или их полный каталог.
3. Прочитай целевой объект, владельца, связанные объекты и references; зафиксируй текущий baseline диагностик.
4. Для обработки сначала установи её UI/service/plugin-роль, затем проверь существующие ManagerModule/ObjectModule и путь создания/инициализации. Регистрацию у поставщика и dynamic resolution проверяй только для обработки, участвующей в соответствующем plugin-контракте.
5. Выполни наименьшую доступную EDT-aware операцию. Не заменяй несвязанные части объекта.
6. Повторно прочитай объект, провалидируй его, сравни diagnostic delta и проверь затронутые references/контракты.
7. Сообщи выполненные проверки и ограничения render/runtime-проверки.

## Quick reference

| Задача | Обязательная проверка |
| --- | --- |
| Новая обработка | роль → существующие модули → создание/инициализация; для plugin — поставщик/dynamic resolution |
| Форма или СКД | владелец, связанные команды/реквизиты и пост-read |
| Любая мутация | live guide → baseline → минимальная операция → revalidation → diagnostic delta |

## Routing

- Только read-only понимание — `queryconsole-code-exploration`.
- Только реализация BSL — `queryconsole-bsl-development`.
- Конкретный текст запроса — `queryconsole-query-development`.
- Мутация metadata/form/DCS/role/subsystem — этот skill.

## Common mistakes

- Для plugin-обработки считать dynamic contract выполненным без включения в фактическую вложенную подсистему и проверки разрешения по имени.
- Изучить только один модуль, пропустив ManagerModule, ObjectModule или фактический путь инициализации.
- Выполнять запись по памяти или старому описанию EDT-MCP вместо живой справки.
- Считать проект «чистым», не сравнив диагностическую дельту с исходным фоном.
