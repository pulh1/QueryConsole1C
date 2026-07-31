---
name: queryconsole-1c-review
description: Use when reviewing QueryConsoleZUP BSL, metadata, forms, concrete queries, visitor or model changes, data processors, or mixed diffs.
---

# Ревью 1С-кода QueryConsoleZUP

Проводите доказательное read-only ревью: finding — только подтверждённый риск, а недостающие проверки — отдельный verification gap.

## Workflow

1. Установите точный diff, scope, ожидаемое поведение и предоставленные доказательства. Не подменяйте отсутствующий diff предположениями.
2. Найдите изменённые public interfaces, definitions, references и callers. EDT-MCP — источник истины для EDT-проекта, metadata, форм, модулей и diagnostics; Serena используйте только для символической навигации. Откройте актуальную справку живых инструментов, а не выдумывайте API.
3. Для expression model проследите `factory → dispatcher → template → concrete visitors → callers`; проверьте полноту visitor/factory/dispatcher/template и concrete visitors. Если scope добавляет callbacks в walker, а изменён только один visitor, прочитайте полный контракт и всех consumers: подтверждённый обязательный callback у неизменённого visitor оформляйте как finding, а severity определяйте по достижимости, пользовательскому эффекту и масштабу. Для data processor проверьте manager/object modules, создание, инициализацию и dynamic contract.
4. Проверьте корректность, client/server context, транзакции, привилегии, security и side effects.
5. Разберите конкретный изменённый запрос по семантике: параметры, типы metadata, `NULL`, дубликаты и результат. Производительность — finding только при доказательствах, не безусловная эвристика.
6. Через доступные сейчас live tools сравните EDT diagnostics с релевантным baseline, а не требуйте нулевых ошибок проекта.
7. Выдайте только proven findings, отсортированные по severity. Каждый содержит severity, точное место, сценарий проявления, доказательство и наименьшее практичное исправление.
8. Отдельно перечислите unknown/unavailable validation как verification gaps. Если findings нет, прямо скажите это до gaps.

## Quick reference

| Изменение | Что проследить |
| --- | --- |
| Новый expression type | factory → dispatcher → template → все visitors → callers |
| Data processor | manager/object → creation/initialization → dynamic provider |
| Metadata/form | владелец, references, client/server и diagnostic delta |
| Query | смысл, `NULL`, кратность, metadata и доказанная производительность |

## Common mistakes

- Выдавать scope-based предположение за доказанный finding.
- Считать первого найденного visitor полным списком потребителей.
- Понижать подтверждённое scope + contract несоответствие до gap вместо finding.
- Называть предполагаемые EDT-MCP методы вместо требуемой live-проверки.
- Считать query-heuristic доказательством проблемы без данных.
- Смешивать неполученный diff, runtime-проверку или diagnostics с findings вместо gaps.
