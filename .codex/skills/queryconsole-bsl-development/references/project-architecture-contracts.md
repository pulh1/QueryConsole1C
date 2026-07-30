# Подтверждённая карта архитектурных контрактов

- В `ЭлементыМоделиЗапроса` 91 factory function.
- В текущем expression walker 29 dispatch types и 59 callbacks.
- Есть template visitor и три complete concrete implementation.
- В проекте 37 data processor.
- Есть 19 реализаций `Представление*`: четыре метода обязательны, два зависят от capability.
- Dynamic resolution использует `Обработки[ОписаниеПредставления.ИмяОбработчика]`.

## Синхронизация

Перед каждой правкой заново установи текущий состав factory functions, dispatch types и callbacks, template и concrete visitors, data processors, `Представление*` и dynamic resolution. Затем синхронизируй затронутые звенья контракта и callers. Не считай приведённые counts вечными: это подтверждённая карта текущего состояния, а не замороженная спецификация.
