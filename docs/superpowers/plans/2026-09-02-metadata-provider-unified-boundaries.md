# Metadata Provider Unified Boundaries Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Доставить семантическую и UI-части поставщиков метаданных одним ready PR, устранив утечки конкретных поставщиков и сохранив ленивый точечный поиск.

**Architecture:** Семантика остаётся диспетчером по доменным типам источников и обращается к именованным таблицам только через точечные операции реестра. Реестр становится единственной composition boundary для UI: агрегирует provider-owned каталог, маршрутизирует раскрытие групп и отдаёт нейтральные параметры, а форма не знает конкретные provider objects и legacy-поставщик. Временные таблицы, таблицы значений и вложенные запросы остаются локальными источниками модели и не получают отдельного поставщика.

**Tech Stack:** 1C:Enterprise 8.3.24, BSL, EDT-проекты `QueryConsoleZUP` и `yaxunit`, YAxUnit, EDT-MCP, 1C Interactive Runtime MCP, Vanessa Automation MCP, Git/GitHub CLI.

**Spec:** `docs/superpowers/specs/2026-09-02-metadata-provider-unified-boundaries-design.md`

## Global Constraints

- Вся работа выполняется в `feature/metadata-provider`, которая содержит обе прежние ветки.
- Платформа проекта: 1C:Enterprise 8.3.24; не использовать API более новых версий.
- Не изменять lexer, parser, AST или модель источников.
- Не создавать отдельный поставщик временных таблиц или вложенных запросов.
- Не создавать новый корневой узел по имени поставщика.
- Не добавлять новый редактор параметров стандартных виртуальных таблиц.
- Не вводить глобальный, session-level или межоперационный кэш provider object.
- Не изменять публичный API legacy-модуля `ПоставщикИсполняемыхПредставлений`.
- `ДанныеПоставщика` разрешены только в server-side описаниях и server-side adapter исполняемых представлений; UI и semantic visitor их не читают.
- UI не создаёт и не разбирает маршрут каталога; формат `<сегмент>|<идентификатор>` закрыт внутри реестра.
- Не менять `Form.form`: маршрут группы хранится в существующей скрытой строковой колонке `Имя`.
- Изменения BSL выполнять минимально через EDT-MCP с revision/hash guard; если живая схема записи недоступна, отдельно зафиксировать этот пробел и не придумывать вызов.
- Сравнивать diagnostic delta затронутых объектов с исходным фоном EDT, а не требовать нулевых диагностик всего проекта.
- Старые PR #76 и #77 не закрывать до публикации и проверки заменяющего ready PR в `master`.

---

## File Map

- `QueryConsoleZUP/src/CommonModules/СемантическийАнализВыраженийУтилиты/Module.bsl` — единый диспетчер поиска полей; различает квалифицированный lookup и безопасный перебор неквалифицированного поля.
- `QueryConsoleZUP/src/DataProcessors/РеестрПоставщиковМетаданныхТаблиц/ObjectModule.bsl` — хранение упорядоченного состава поставщиков, агрегация корней и закрытая маршрутизация каталога.
- `QueryConsoleZUP/src/CommonModules/МетаданныеТаблицЗапроса/Module.bsl` — фабрики transport-safe элементов каталога, параметров и полей параметров.
- `QueryConsoleZUP/src/DataProcessors/ПоставщикМетаданныхИсполняемыхПредставлений/ObjectModule.bsl` — собственный корень `Представления` и полное преобразование legacy-параметров в нейтральный контракт.
- `QueryConsoleZUP/src/DataProcessors/ПоставщикМетаданныхСтандартныхТаблиц/ObjectModule.bsl` — заполнение общей нейтральной формы параметров стандартных таблиц без изменения их каталога.
- `QueryConsoleZUP/src/CommonModules/КонструкторЗапросовФормы/Module.bsl` — UI-фасад, работающий только с `Реестр`, и преобразование route/table identifiers в существующие строки дерева.
- `QueryConsoleZUP/src/CommonModules/ОбработкаПредставлениеЗапросов/Module.bsl` — единственный server-side adapter от краткого нейтрального описания к legacy runtime-описанию представления.
- `QueryConsoleZUP/src/DataProcessors/КонструкторЗапросов/Forms/ПараметрыИсполняемогоПредставления/Module.bsl` — построение и сохранение формы по нейтральным параметрам без прямых legacy lookup.
- `yaxunit/src/DataProcessors/КОНС_ПоставщикМетаданныхТаблицШпион/ObjectModule.bsl` — мок произвольного поставщика с каталогом и счётчиками точечных операций.
- `yaxunit/src/CommonModules/КОНС_Обр_МодельВыражений_МО/Module.bsl` — semantic path, локальные источники, derived contexts и отсутствие fallback/загрязнения.
- `yaxunit/src/CommonModules/КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО/Module.bsl` — DTO, маршруты, штатные каталоги и преобразование параметров.
- `yaxunit/src/CommonModules/КОНС_Обр_ПрикладныеПотребителиЗапроса_МО/Module.bsl` — UI-фасад с произвольным реестром и transport boundary.
- `yaxunit/src/CommonModules/КОНС_Обр_ИсполняемыеПредставления_МО/Module.bsl` — server-side adapter и сохранение runtime-контракта исполняемых представлений.
- `features/` — существующие Vanessa-сценарии каталога и параметров; новый сценарий добавляется только если существующие не наблюдают provider-owned корень и сохранение параметров.
- `docs/research/2026-09-02-metadata-provider-unified-verification.md` — фактическая матрица YAxUnit/EDT/runtime/Vanessa/benchmark и независимого review.

---

### Task 1: Закрыть семантические утечки локальных источников

**Files:**
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_МодельВыражений_МО/Module.bsl`
- Modify: `QueryConsoleZUP/src/CommonModules/СемантическийАнализВыраженийУтилиты/Module.bsl`

**Interfaces:**
- Consumes: `Контекст.РеестрПоставщиковМетаданныхТаблиц`, `Реестр.НайтиПоле(ИмяТаблицы, ИмяПоля)`, существующие типы `ИсточникДанныхВложенныйЗапрос`, `ИсточникДанныхВременнаяТаблица`, `ИсточникДанныхТаблицаЗначений`, `ИсточникДанныхТаблица`, `ИсполняемоеПредставление`.
- Produces: `НайтиПолеВИсточнике(ИмяПоля, Источник, Контекст, РазрешитьНеявноеПолеЛокальногоИсточника = Истина) Экспорт`; прежние три аргумента остаются совместимыми.
- Produces: `НайтиПолеВоВсехИсточниках()` вызывает диспетчер с `РазрешитьНеявноеПолеЛокальногоИсточника = Ложь`.

- [ ] **Step 1: Зафиксировать живую ревизию и исходные диагностики**

Через EDT-MCP прочитать оба изменяемых модуля, сохранить полученные revision/hash и diagnostic baseline. Точечным поиском повторно подтвердить callers `НайтиПолеВИсточнике`, `ТипПоляПоИмени`, `ОбработатьОбращениеКПолюИсточника` и `ТипЭлементаРазыменованияИзОписанияТипов`.

- [ ] **Step 2: Дополнить failing semantic tests**

Сохранить уже подготовленные тесты:

```bsl
Тесты.Добавить("СемантикаПолногоПутиИспользуетТолькоТочечныеМетодыПоставщика");
Тесты.Добавить("НеквалифицированноеПолеНеПриписываетсяВнешнейВт");
Тесты.Добавить("НеквалифицированноеПолеНеПриписываетсяТаблицеЗначений");
```

Добавить прямые тесты диспетчера:

```bsl
// Вложенный запрос и известная ВТ возвращают локальное поле и не трогают шпион.
// Квалифицированная неизвестная внешняя ВТ и таблица значений получают произвольный тип.
// Именованная таблица и исполняемое представление вызывают ровно НайтиПоле().
// Пустой реестр возвращает Неопределено без штатного fallback.
```

Для каждого локального источника проверить нулевые `КоличествоПоисковТаблицы()`, `КоличествоПоисковПоля()`, `КоличествоПолученийОписания()` и `КоличествоПроверокСуществования()`. Для полного пути `ВЫБРАТЬ Источник.Код ИЗ Тестовый.Источник КАК Источник` проверить один `НайтиТаблицу()`, один `НайтиПоле()` и нули у остальных счётчиков.

Отдельными assertions пройти callers: `ТипПоляПоИмени()` с квалифицированным полем, semantic visitor через полный parse/process path, и `ТипЭлементаРазыменованияИзОписанияТипов()` для ссылочного типа. Во всех именованных случаях разрешён только `Реестр.НайтиПоле()`; существующие tests `ПостроительМоделиЗапроса` и `ОбработкаПредставлениеЗапросов` должны продолжить подтверждать `НайтиТаблицу()` без полного описания.

- [ ] **Step 3: Запустить exact tests и получить RED**

Через EDT-MCP `run_yaxunit_tests` использовать launch `QueryConsoleZUP Semantic Tests`, extension `YAXUNIT`, `updateBeforeLaunch=true`, `updateScope="extension:QueryConsoleZUP_YAxUnit"`, timeout 120 секунд и exact tests из Step 2. Ожидаемый RED: неквалифицированный перебор считает неизвестную внешнюю ВТ/таблицу значений найденным полем или изменяет `ОписаниеВТ.Колонки`.

- [ ] **Step 4: Реализовать минимальное различие qualified/unqualified lookup**

Изменить сигнатуру и только две локальные ветки:

```bsl
Функция НайтиПолеВИсточнике(
	ИмяПоля,
	Источник,
	Контекст,
	РазрешитьНеявноеПолеЛокальногоИсточника = Истина) Экспорт

	// Ветка вложенного запроса остаётся без изменений.

	// В ветке неизвестного поля внешней ВТ до ДобавитьПолеВОписаниеВТ:
	Если Не РазрешитьНеявноеПолеЛокальногоИсточника Тогда
		Возврат Неопределено;
	КонецЕсли;

	// В ветке таблицы значений до создания произвольного поля:
	Если Не РазрешитьНеявноеПолеЛокальногоИсточника Тогда
		Возврат Неопределено;
	КонецЕсли;
```

В переборе всех источников передать `Ложь`:

```bsl
ТекущееПоле = НайтиПолеВИсточнике(
	ИмяПоля,
	КлючЗначение.Значение.Источник,
	Контекст,
	Ложь);
```

Не менять default вызовы `ТипПоляПоИмени()` и semantic visitor: квалифицированный lookup сохраняет текущий compatibility contract.

- [ ] **Step 5: Запустить GREEN и semantic regression modules**

Сначала повторить exact tests, затем последовательно модули:

```text
КОНС_Обр_МодельВыражений_МО
КОНС_Обр_ПостроениеИГенерацияЗапросов_МО
КОНС_Обр_ИсполняемыеПредставления_МО
```

Ожидаемый результат: все проверки GREEN; если есть прежний фон, записать точные тесты и сообщения отдельно, не считать их результатом этой правки.

- [ ] **Step 6: Перечитать изменения и проверить diagnostic delta**

Через EDT-MCP повторно прочитать оба модуля, проверить что hash соответствует записанному содержимому, и сравнить диагностики с Step 1. Точечный поиск должен показать отсутствие `ОписаниеТаблицы()` и `ТаблицаСуществует()` в semantic path.

- [ ] **Step 7: Commit semantic boundary**

```powershell
git add -- "QueryConsoleZUP/src/CommonModules/СемантическийАнализВыраженийУтилиты/Module.bsl" "yaxunit/src/CommonModules/КОНС_Обр_МодельВыражений_МО/Module.bsl"
git commit -m "fix: isolate local schemas during semantic lookup"
```

---

### Task 2: Сделать реестр владельцем каталога и маршрутов

**Files:**
- Modify: `QueryConsoleZUP/src/CommonModules/МетаданныеТаблицЗапроса/Module.bsl`
- Modify: `QueryConsoleZUP/src/DataProcessors/РеестрПоставщиковМетаданныхТаблиц/ObjectModule.bsl`
- Modify: `yaxunit/src/DataProcessors/КОНС_ПоставщикМетаданныхТаблицШпион/ObjectModule.bsl`
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО/Module.bsl`

**Interfaces:**
- Produces: `НовыйЭлементКаталога(Идентификатор, ИдентификаторРодителя = Неопределено, ИмяТаблицы = Неопределено, Представление = "", ЭтоГруппа = Ложь, ЕстьДочерние = Ложь, ВидИсточника = "", МаршрутКаталога = "")`.
- Produces: `Реестр.КорневыеЭлементыКаталога()` returning `Массив из Структура`.
- Produces: `Реестр.ДочерниеЭлементыКаталога(МаршрутКаталога)` returning empty array for malformed or unknown routes.
- Consumes dynamic provider contract: `Поставщик.ДочерниеЭлементы(ИдентификаторРодителя = Неопределено)`.
- Test provider setup becomes `Настроить(ИмяПоставщика, Сегменты, Таблицы, ЭлементыКаталогаПоРодителям = Неопределено)`.

- [ ] **Step 1: Write failing DTO and routing tests**

В provider test module изменить ожидание элемента каталога с 7 на 8 полей и проверить `МаршрутКаталога = ""` у фабрики. Добавить два шпиона в порядке `[Первый, Второй]` с различными сегментами и каталогами:

```bsl
КорниПервого.Вставить("", Новый Массив);
КорниПервого[""].Добавить(МетаданныеТаблицЗапроса.НовыйЭлементКаталога(
	"Корень", Неопределено, Неопределено, "Первый", Истина, Истина, "ТестоваяГруппа"));
ДетиПервого.Вставить("Корень", Новый Массив);
ДетиПервого["Корень"].Добавить(МетаданныеТаблицЗапроса.НовыйЭлементКаталога(
	"Дочерний|Узел", "Корень", "Тестовый.Таблица", "Таблица", Ложь, Истина, "ТестоваяТаблица"));
```

Проверить:

- корни агрегируются в порядке регистрации;
- каждый корень получает route первого сегмента конкретного поставщика;
- child route с opaque id `Дочерний|Узел` сохраняет второй `|` внутри идентификатора;
- пустой, без-разделителя и неизвестный segment route возвращают пустой массив;
- коллизия сегментов остаётся той же ошибкой инициализации.

- [ ] **Step 2: Run exact routing tests for RED**

Запустить exact tests нового DTO и маршрутов через тот же EDT-MCP launch. Ожидаемый RED: отсутствуют `МаршрутКаталога`, `КорневыеЭлементыКаталога` и `ДочерниеЭлементыКаталога`.

- [ ] **Step 3: Extend the transport factory and spy provider**

В `НовыйЭлементКаталога` добавить восьмое поле последним, сохранив совместимость позиционных вызовов. В шпионе сохранить каталог, а метод реализовать без production branching:

```bsl
&НаСервере
Функция ДочерниеЭлементы(ИдентификаторРодителя = Неопределено) Экспорт
	Если ЭлементыКаталогаПоРодителям = Неопределено Тогда
		Возврат Новый Массив;
	КонецЕсли;
	КлючРодителя = ?(ИдентификаторРодителя = Неопределено, "", ИдентификаторРодителя);
	Элементы = ЭлементыКаталогаПоРодителям.Получить(КлючРодителя);
	Возврат ?(Элементы = Неопределено, Новый Массив, Элементы);
КонецФункции
```

- [ ] **Step 4: Implement registry-owned routing**

Добавить `Перем ИнициализированныеПоставщики;`; в `Инициализировать()` атомарно присваивать его только после успешного построения индекса. Для выбора стабильного route segment брать первый элемент `Поставщик.Сегменты()`.

Публичные операции реализовать через приватные helpers:

```bsl
Функция КорневыеЭлементыКаталога() Экспорт
	Результат = Новый Массив;
	Для Каждого Поставщик Из ИнициализированныеПоставщики Цикл
		Сегменты = Поставщик.Сегменты();
		Если Сегменты.Количество() = 0 Тогда Продолжить; КонецЕсли;
		ДобавитьМаршрутизированныеЭлементы(
			Результат, Сегменты[0], Поставщик.ДочерниеЭлементы());
	КонецЦикла;
	Возврат Результат;
КонецФункции

Функция ДочерниеЭлементыКаталога(МаршрутКаталога) Экспорт
	ПозицияРазделителя = СтрНайти(МаршрутКаталога, "|");
	Если ПозицияРазделителя <= 1 Тогда Возврат Новый Массив; КонецЕсли;
	Сегмент = Лев(МаршрутКаталога, ПозицияРазделителя - 1);
	Идентификатор = Сред(МаршрутКаталога, ПозицияРазделителя + 1);
	Если ПустаяСтрока(Идентификатор) Тогда Возврат Новый Массив; КонецЕсли;
	Поставщик = ИндексПоставщиковПоСегментам.Получить(ВРег(Сегмент));
	Если Поставщик = Неопределено Тогда Возврат Новый Массив; КонецЕсли;
	Результат = Новый Массив;
	ДобавитьМаршрутизированныеЭлементы(
		Результат, Сегмент, Поставщик.ДочерниеЭлементы(Идентификатор));
	Возврат Результат;
КонецФункции
```

`ДобавитьМаршрутизированныеЭлементы()` создаёт новый transport-safe элемент через фабрику, копирует семь provider fields и устанавливает `МаршрутКаталога = Сегмент + "|" + Элемент.Идентификатор`; исходную структуру provider-а не изменять.

- [ ] **Step 5: Run routing tests GREEN and full provider module**

Повторить exact tests, затем весь `КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО`. Ожидаемый результат: GREEN и неизменные результаты старых lookup/cache tests.

- [ ] **Step 6: Re-read and commit registry catalogue**

Проверить EDT diagnostic delta четырёх модулей и выполнить:

```powershell
git add -- "QueryConsoleZUP/src/CommonModules/МетаданныеТаблицЗапроса/Module.bsl" "QueryConsoleZUP/src/DataProcessors/РеестрПоставщиковМетаданныхТаблиц/ObjectModule.bsl" "yaxunit/src/DataProcessors/КОНС_ПоставщикМетаданныхТаблицШпион/ObjectModule.bsl" "yaxunit/src/CommonModules/КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО/Module.bsl"
git commit -m "feat: route provider catalog through registry"
```

---

### Task 3: Передать владение корнем `Представления` executable-provider-у

**Files:**
- Modify: `QueryConsoleZUP/src/DataProcessors/ПоставщикМетаданныхИсполняемыхПредставлений/ObjectModule.bsl`
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО/Module.bsl`

**Interfaces:**
- Consumes: provider contract `ДочерниеЭлементы(ИдентификаторРодителя = Неопределено)`.
- Produces: root call returns exactly one group `Идентификатор="Представления"`, `Представление="Представления"`, `ЭтоГруппа=Истина`, `ЕстьДочерние=Истина`, `ВидИсточника="ИсполняемаяГруппа"`.
- Produces: `ДочерниеЭлементы("Представления")` returns the former root groups in the same order.

- [ ] **Step 1: Change executable catalogue tests to RED**

Изменить текущий тест, ожидающий первым `РегистрыНакопления`: сначала проверить единственный корень `Представления`, затем раскрыть его и проверить прежние root groups, их порядок, flags и ленивость. Отдельно убедиться, что `ОписаниеТаблицы()` при каталожном раскрытии не вызывается.

- [ ] **Step 2: Run exact executable catalogue tests**

Ожидаемый RED: текущий provider возвращает legacy root groups непосредственно на `Неопределено`.

- [ ] **Step 3: Implement one additional provider-owned level**

```bsl
Если ИдентификаторРодителя = Неопределено Тогда
	Элементы.Добавить(МетаданныеТаблицЗапроса.НовыйЭлементКаталога(
		"Представления", Неопределено, Неопределено, "Представления",
		Истина, Истина, "ИсполняемаяГруппа"));
	Возврат Элементы;
КонецЕсли;

Если ИдентификаторРодителя = "Представления" Тогда
	Для Каждого ИмяГруппы Из ПоставщикИсполняемыхПредставлений.ГруппыИсполняемыхПредставлений() Цикл
		Элементы.Добавить(НовыйЭлементГруппы(ИмяГруппы, "Представления"));
	КонецЦикла;
	Возврат Элементы;
КонецЕсли;
```

Оставить все более глубокие уровни и имена таблиц без изменений.

- [ ] **Step 4: Run GREEN and commit**

Запустить exact tests и полный provider module, проверить diagnostic delta, затем:

```powershell
git add -- "QueryConsoleZUP/src/DataProcessors/ПоставщикМетаданныхИсполняемыхПредставлений/ObjectModule.bsl" "yaxunit/src/CommonModules/КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО/Module.bsl"
git commit -m "feat: expose executable catalog root from provider"
```

---

### Task 4: Перевести UI-каталог на единственный реестр

**Files:**
- Modify: `QueryConsoleZUP/src/CommonModules/КонструкторЗапросовФормы/Module.bsl`
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ПрикладныеПотребителиЗапроса_МО/Module.bsl`

**Interfaces:**
- Consumes: `РеестрПоставщиковМетаданныхТаблиц.СоздатьРеестр()` for default composition, `КонтекстМетаданныхUI.Реестр.КорневыеЭлементыКаталога()`, `КонтекстМетаданныхUI.Реестр.ДочерниеЭлементыКаталога(МаршрутКаталога)`.
- Produces: `НовыйКонтекстМетаданныхUI()` returning structure with exactly one property `Реестр`.
- Produces: `ОписаниеСтрокиКаталога()` stores group route in `Описание.Имя`, but stores leaf full table name in `Описание.Имя`.
- Does not produce: provider-specific root, provider object or new form column.

- [ ] **Step 1: Write failing UI facade tests with a non-standard provider**

Изменить прежнее ожидание context count `3` на `1`, проверить наличие только `Реестр`. Создать context вручную:

```bsl
Поставщики = Новый Массив;
Поставщики.Добавить(Шпион);
Реестр = Обработки.РеестрПоставщиковМетаданныхТаблиц.СоздатьРеестр(Поставщики);
Контекст = Новый Структура("Реестр", Реестр);
Корни = КонструкторЗапросовФормы.ОписанияКорневыхСтрокКаталога(Контекст);
Дети = КонструкторЗапросовФормы.ОписанияДочернихСтрокКаталога(Контекст, Корни[0]);
```

Шпион использует сегмент `Тестовый`, group id `Корень`, table `Тестовый.Таблица`. Проверить, что UI-фасад не менялся для поддержки этого поставщика; группа хранит opaque route в `Имя`, лист хранит `Тестовый.Таблица`, а все описания строк не содержат `ДанныеПоставщика` и provider object.

- [ ] **Step 2: Run UI facade exact tests for RED**

Ожидаемый RED: context публикует два конкретных provider objects, корни строятся вручную, child dispatch зависит от `ВидИсточника`.

- [ ] **Step 3: Replace UI composition and dispatch**

`НовыйКонтекстМетаданныхUI()` должен использовать штатную manager factory:

```bsl
Функция НовыйКонтекстМетаданныхUI() Экспорт
	Возврат Новый Структура(
		"Реестр",
		Обработки.РеестрПоставщиковМетаданныхТаблиц.СоздатьРеестр());
КонецФункции
```

Корень и потомки получать только из реестра:

```bsl
ЭлементыКаталога = КонтекстМетаданныхUI.Реестр.КорневыеЭлементыКаталога();
// ... map each through ОписаниеСтрокиКаталога

ЭлементыКаталога = КонтекстМетаданныхUI.Реестр.ДочерниеЭлементыКаталога(
	ОписаниеРодителя.Имя);
```

В mapper:

```bsl
Если ЭлементКаталога.ЭтоГруппа Тогда
	Описание.Имя = ЭлементКаталога.МаршрутКаталога;
Иначе
	Описание.Имя = ЭлементКаталога.ИмяТаблицы;
КонецЕсли;
```

`Представление`, existing flags, images and leaf field expansion оставить текущими. Не добавлять provider-name branches и не менять `Form.form`.

- [ ] **Step 4: Run UI facade GREEN and regression module**

Повторить exact tests и весь `КОНС_Обр_ПрикладныеПотребителиЗапроса_МО`; дополнительно запустить `КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО` для route integration.

- [ ] **Step 5: Re-read, verify no provider identity leakage, and commit**

```powershell
rg -n "СтандартныйПоставщик|ПоставщикПредставлений|ПоставщикМетаданныхСтандартныхТаблиц|ПоставщикМетаданныхИсполняемыхПредставлений" "QueryConsoleZUP/src/CommonModules/КонструкторЗапросовФормы/Module.bsl"
git diff --name-only -- "QueryConsoleZUP/src/DataProcessors/КонструкторЗапросов/Forms/КонструкторЗапросов/Form.form"
```

Ожидается: первый поиск не находит provider identity, второй вывод пуст. После EDT diagnostic delta:

```powershell
git add -- "QueryConsoleZUP/src/CommonModules/КонструкторЗапросовФормы/Module.bsl" "yaxunit/src/CommonModules/КОНС_Обр_ПрикладныеПотребителиЗапроса_МО/Module.bsl"
git commit -m "refactor: build query catalog through registry"
```

---

### Task 5: Завершить нейтральный контракт параметров

**Files:**
- Modify: `QueryConsoleZUP/src/CommonModules/МетаданныеТаблицЗапроса/Module.bsl`
- Modify: `QueryConsoleZUP/src/DataProcessors/ПоставщикМетаданныхИсполняемыхПредставлений/ObjectModule.bsl`
- Modify: `QueryConsoleZUP/src/DataProcessors/ПоставщикМетаданныхСтандартныхТаблиц/ObjectModule.bsl`
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО/Module.bsl`

**Interfaces:**
- Produces parameter DTO fields exactly: `Имя`, `ВидПараметра`, `ТипЗначения`, `Обязательный`, `Варианты`, `Поля`, `ДопустимыеТипы`, `ДопустимПараметрЗапроса`, `ЗначениеПоУмолчанию`, `ДанныеПоставщика`.
- Produces: `НовыйОписаниеПоляПараметра(Имя = "", Обязательный = Ложь, Устарело = Ложь)` returning exactly `Имя,Обязательный,Устарело`.
- Consumes legacy constant fields `ТипКонстанты`, `ДоступныеЗначения`, `ДопустимПараметрЗапроса`, `ЗначениеПоУмолчанию`; filter fields `ДопустимыеТипы`, `ПоляФильтра`; selection fields `ДоступныеПоля`.

- [ ] **Step 1: Write failing factory and conversion tests**

Проверить exact field sets and defaults:

```bsl
Параметр = МетаданныеТаблицЗапроса.НовыйОписаниеПараметра();
ЮТест.ОжидаетЧто(Параметр.Количество()).Равно(10);
ЮТест.ОжидаетЧто(ТипЗнч(Параметр.ДопустимыеТипы)).Равно(Тип("Массив"));
ЮТест.ОжидаетЧто(Параметр.ДопустимПараметрЗапроса).ЭтоЛожь();
ЮТест.ОжидаетЧто(Параметр.ЗначениеПоУмолчанию).Равно(Неопределено);

Поле = МетаданныеТаблицЗапроса.НовыйОписаниеПоляПараметра("Код", Истина, Ложь);
ЮТест.ОжидаетЧто(Поле.Количество()).Равно(3);
```

На реальном executable description проверить:

- constant maps `ТипКонстанты -> ТипЗначения`, `ДоступныеЗначения -> Варианты`, query-parameter flag and default;
- VT filter maps `ПоляФильтра` to exact three-field DTOs and preserves mandatory/deprecated;
- selection maps `ДоступныеПоля` to three-field DTOs with both flags false;
- neutral nested `Поля` не содержат table-field fields или `ДанныеПоставщика`;
- standard-provider parameter has the same property set and safe defaults.

- [ ] **Step 2: Run parameter contract tests for RED**

Ожидаемый RED: отсутствуют три properties и factory поля параметра; executable provider кладёт table-field DTO в `Поля`.

- [ ] **Step 3: Extend neutral factories**

В `НовыйОписаниеПараметра` вставить:

```bsl
Описание.Вставить("ДопустимыеТипы", Новый Массив);
Описание.Вставить("ДопустимПараметрЗапроса", Ложь);
Описание.Вставить("ЗначениеПоУмолчанию", Неопределено);
```

Создать export factory:

```bsl
Функция НовыйОписаниеПоляПараметра(
	Имя = "", Обязательный = Ложь, Устарело = Ложь) Экспорт
	Возврат Новый Структура(
		"Имя,Обязательный,Устарело", Имя, Обязательный, Устарело);
КонецФункции
```

- [ ] **Step 4: Map executable legacy properties without leaking raw nested objects**

В `ПреобразоватьПараметр()` читать свойства через существующий `ПолучитьСвойство()`. После factory call установить three scalar/array properties. Для полей использовать отдельный converter:

```bsl
Функция ПреобразоватьПолеПараметра(СыроеПоле)
	Если ТипЗнч(СыроеПоле) = Тип("Строка") Тогда
		Возврат МетаданныеТаблицЗапроса.НовыйОписаниеПоляПараметра(СыроеПоле);
	КонецЕсли;
	Возврат МетаданныеТаблицЗапроса.НовыйОписаниеПоляПараметра(
		ПолучитьСвойство(СыроеПоле, "Имя", ""),
		ПолучитьСвойство(СыроеПоле, "Обязательный", Ложь),
		ПолучитьСвойство(СыроеПоле, "Устарело", Ложь));
КонецФункции
```

`Описание.ДанныеПоставщика = СыройПараметр` разрешено в полном server-side table description; содержимое `Описание.Поля` остаётся transport-safe.

- [ ] **Step 5: Fill standard-provider shared defaults**

Оставить имеющееся platform mapping `Имя`, `ТипЗначения`, `Варианты`, `ДоступныеПоля`; `ДопустимыеТипы` заполнять только если такое подтверждённое platform property фактически читается текущим кодом. Для отсутствующих properties оставить factory defaults, не изобретать platform API.

- [ ] **Step 6: Run GREEN, diagnostics and commit**

Запустить exact conversion tests и полный provider module. Проверить диагностический delta и:

```powershell
git add -- "QueryConsoleZUP/src/CommonModules/МетаданныеТаблицЗапроса/Module.bsl" "QueryConsoleZUP/src/DataProcessors/ПоставщикМетаданныхИсполняемыхПредставлений/ObjectModule.bsl" "QueryConsoleZUP/src/DataProcessors/ПоставщикМетаданныхСтандартныхТаблиц/ObjectModule.bsl" "yaxunit/src/CommonModules/КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО/Module.bsl"
git commit -m "feat: complete neutral table parameter contract"
```

---

### Task 6: Удалить legacy lookup из формы параметров

**Files:**
- Modify: `QueryConsoleZUP/src/CommonModules/ОбработкаПредставлениеЗапросов/Module.bsl`
- Modify: `QueryConsoleZUP/src/CommonModules/КонструкторЗапросовФормы/Module.bsl`
- Modify: `QueryConsoleZUP/src/DataProcessors/КонструкторЗапросов/Forms/ПараметрыИсполняемогоПредставления/Module.bsl`
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ИсполняемыеПредставления_МО/Module.bsl`
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_ПрикладныеПотребителиЗапроса_МО/Module.bsl`

**Interfaces:**
- Produces: `ОбработкаПредставлениеЗапросов.ИсполняемоеПредставлениеПоИмениТаблицы(ИмяТаблицы, РеестрПоставщиков) Экспорт` as the only server adapter allowed to read table `ДанныеПоставщика`.
- Produces: `КонструкторЗапросовФормы.ОписаниеТаблицыДляРедактораПараметров(ИмяТаблицы, КонтекстМетаданныхUI)` returning neutral full table description or `Неопределено`.
- Consumes form data from `ОписаниеТаблицы.Параметры` and fields defined in Task 5.
- Preserves command applicability to model type `ИсполняемоеПредставление`; standard virtual-table parameter editor remains out of scope.

- [ ] **Step 1: Write failing adapter and consumer tests**

В executable tests проверить:

```bsl
Результат = ОбработкаПредставлениеЗапросов.ИсполняемоеПредставлениеПоИмениТаблицы(
	"ИсполняемоеПредставление....", Реестр);
```

Для executable descriptor adapter возвращает модель; для standard descriptor и unknown table возвращает `Неопределено`; только этот adapter вправе читать raw payload. В consumer tests через шпион проверить, что `ОписаниеТаблицыДляРедактораПараметров()` вызывает один `ОписаниеТаблицы()`, возвращает neutral params и не вызывает legacy provider.

- [ ] **Step 2: Run exact tests for RED**

Ожидаемый RED: adapter/facade functions отсутствуют и форма всё ещё имеет три прямых вызова `ПоставщикИсполняемыхПредставлений.ОписаниеПредставленияПоИмениТаблицы`.

- [ ] **Step 3: Add guarded server adapter**

```bsl
Функция ИсполняемоеПредставлениеПоИмениТаблицы(
	ИмяТаблицы, РеестрПоставщиков) Экспорт
	Если РеестрПоставщиков = Неопределено Тогда Возврат Неопределено; КонецЕсли;
	ОписаниеТаблицы = РеестрПоставщиков.НайтиТаблицу(ИмяТаблицы);
	Если ОписаниеТаблицы = Неопределено
		Или ОписаниеТаблицы.ВидИсточника <> "ИсполняемоеПредставление" Тогда
		Возврат Неопределено;
	КонецЕсли;
	Возврат ИсполняемоеПредставлениеПоОписанию(
		ОписаниеТаблицы.ДанныеПоставщика);
КонецФункции
```

Не менять legacy fallback уже существующего `ОбработатьИсточникЗапроса()` для контекста вообще без свойства реестра; UI всегда создаёт реестр и этим fallback не пользуется.

- [ ] **Step 4: Add neutral form facade helpers**

```bsl
Функция ОписаниеТаблицыДляРедактораПараметров(
	ИмяТаблицы, КонтекстМетаданныхUI) Экспорт
	Возврат КонтекстМетаданныхUI.Реестр.ОписаниеТаблицы(ИмяТаблицы);
КонецФункции

Функция ПараметрыПоВиду(Параметры, ВидПараметра) Экспорт
	Результат = Новый Массив;
	Для Каждого Параметр Из Параметры Цикл
		Если Параметр.ВидПараметра = ВидПараметра Тогда
			Результат.Добавить(Параметр);
		КонецЕсли;
	КонецЦикла;
	Возврат Результат;
КонецФункции
```

Этот pure helper покрыть YAxUnit для `ОписаниеПараметраКонстанта`, `ОписаниеВТФильтра`, `ОписаниеОтбора` и пустого массива.

- [ ] **Step 5: Refactor form create/save/display to neutral parameters**

В каждой серверной операции создавать новый `КонтекстМетаданныхUI` и получать полное описание через facade. Если оно `Неопределено`, вызвать исключение `"Таблица " + ИмяТаблицыПредставления + " не найдена"`, согласованное с server consumer `ОбработатьИсточникЗапроса()`; не выполнять повторный direct lookup. Полное описание остаётся локальной server variable операции и не записывается в реквизиты формы или временное хранилище.

Заменить raw property mapping точно:

```text
ОписаниеПредставления.ОписаниеПараметров -> ПараметрыПоВиду(..., "ОписаниеПараметраКонстанта")
ОписаниеПредставления.ОписаниеВТФильтр   -> первый ПараметрыПоВиду(..., "ОписаниеВТФильтра")
ОписаниеПредставления.ОписаниеОтбора     -> первый ПараметрыПоВиду(..., "ОписаниеОтбора")
Тип                                      -> ВидПараметра
ТипКонстанты                             -> ТипЗначения
ДоступныеЗначения                        -> Варианты
ПоляФильтра / ДоступныеПоля              -> Поля
```

`ДопустимыеТипы`, `ДопустимПараметрЗапроса`, `ЗначениеПоУмолчанию`, `Обязательный` читать под нейтральными именами. `ДобавитьЭлементыОтображенияПараметров()` принимает массив neutral parameters, а не raw representation description.

Для `ПараметрыОткрытияРедактораВыражений()` модель источника получать через adapter Task 6 Step 3, а доступные поля отбора — из neutral parameter `Поля`. Форма не читает `ДанныеПоставщика`.

- [ ] **Step 6: Prove removal of all three direct calls**

```powershell
rg -n "ПоставщикИсполняемыхПредставлений|ДанныеПоставщика|ОписаниеПараметров|ОписаниеВТФильтр|ОписаниеОтбора|ТипКонстанты|ДоступныеЗначения|ПоляФильтра|ДоступныеПоля" "QueryConsoleZUP/src/DataProcessors/КонструкторЗапросов/Forms/ПараметрыИсполняемогоПредставления/Module.bsl"
```

Ожидается: отсутствуют `ПоставщикИсполняемыхПредставлений`, `ДанныеПоставщика` и raw description property accesses. Совпадения `ТипКонстанты*` и `ПоляФильтра*` допустимы только как существующие имена реквизитов/элементов формы, не как properties нейтрального descriptor.

- [ ] **Step 7: Run consumer regression and diagnostics**

Запустить exact adapter/helper tests, затем:

```text
КОНС_Обр_ИсполняемыеПредставления_МО
КОНС_Обр_ПрикладныеПотребителиЗапроса_МО
КОНС_Обр_ПостроениеИГенерацияЗапросов_МО
КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО
```

Проверить EDT diagnostic delta production form module, two common modules and tests. `Form.form` не должен измениться.

- [ ] **Step 8: Commit form boundary**

```powershell
git add -- "QueryConsoleZUP/src/CommonModules/ОбработкаПредставлениеЗапросов/Module.bsl" "QueryConsoleZUP/src/CommonModules/КонструкторЗапросовФормы/Module.bsl" "QueryConsoleZUP/src/DataProcessors/КонструкторЗапросов/Forms/ПараметрыИсполняемогоПредставления/Module.bsl" "yaxunit/src/CommonModules/КОНС_Обр_ИсполняемыеПредставления_МО/Module.bsl" "yaxunit/src/CommonModules/КОНС_Обр_ПрикладныеПотребителиЗапроса_МО/Module.bsl"
git commit -m "refactor: drive representation parameters from registry"
```

---

### Task 7: Проверить derived contexts и отсутствие fallback

**Files:**
- Modify: `yaxunit/src/CommonModules/КОНС_Обр_МодельВыражений_МО/Module.bsl`
- Modify only if a failing test proves loss: `QueryConsoleZUP/src/CommonModules/ОбработкаМоделиЗапроса/Module.bsl`

**Interfaces:**
- Consumes: parent `Контекст.РеестрПоставщиковМетаданныхТаблиц`.
- Produces: nested query, virtual-table parameter expression and periods-completion expression reuse the exact same registry object.
- Produces: a present but empty registry disables standard schema and legacy fallback.

- [ ] **Step 1: Add three derived-context tests and one empty-registry test**

Использовать шпион с уникальным сегментом and table. Для каждого пути выполнить реальный parser/model processing entry point, а не прямой вызов helper:

- вложенный запрос resolves named field through the same spy;
- выражение параметра виртуальной таблицы resolves referenced field through the same spy;
- выражение дополнения периодами resolves field through the same spy;
- context with initialized empty registry rejects a standard/executable table and does not call legacy provider.

Во всех случаях проверить ожидаемые point lookup counters и ноль full descriptions.

- [ ] **Step 2: Run exact tests and distinguish RED from missing fixture**

Если test data does not reach the intended derived-context constructor, исправить только fixture до наблюдаемого path. Production менять только если registry действительно теряется.

- [ ] **Step 3: Apply the smallest context propagation fix if RED proves it**

Если тест докажет регрессию, в `ОбработкаМоделиЗапроса` передавать тот же registry в существующие фабрики контекста без нового registry:

```bsl
ВложенныйКонтекст = КонтекстОбработкиЗапроса(
	ТекущийКонтекст.РеестрПоставщиковМетаданныхТаблиц);
```

Не создавать штатный реестр в helper и не добавлять fallback, когда property уже присутствует со значением `Неопределено` или empty registry.

- [ ] **Step 4: Run semantic regression and commit test/fix**

Запустить exact tests and entire `КОНС_Обр_МодельВыражений_МО`. Если production не менялся, commit only tests; otherwise include only proven context constructor:

```powershell
git add -- "yaxunit/src/CommonModules/КОНС_Обр_МодельВыражений_МО/Module.bsl" "QueryConsoleZUP/src/CommonModules/ОбработкаМоделиЗапроса/Module.bsl"
git commit -m "test: cover provider registry in derived contexts"
```

Перед commit убрать из index production file, если test показал, что исправление не требуется.

---

### Task 8: Full verification, performance, acceptance and replacement PR

**Files:**
- Create: `docs/research/2026-09-02-metadata-provider-unified-verification.md`
- Create: `docs/research/2026-09-02-metadata-provider-unified-pr.md`
- Review: complete `master...feature/metadata-provider` diff.

**Interfaces:**
- Produces: reproducible evidence for YAxUnit, EDT diagnostic delta, runtime, benchmark, Vanessa and independent review.
- Produces: one ready PR `feature/metadata-provider -> master` before old PR closure.

- [ ] **Step 1: Run focused YAxUnit modules without debugger**

Убедиться, что EDT debugger не attached и не блокирует infobase. Через EDT-MCP по одному запустить:

```text
КОНС_Обр_ПоставщикиМетаданныхТаблиц_МО
КОНС_Обр_МодельВыражений_МО
КОНС_Обр_ПрикладныеПотребителиЗапроса_МО
КОНС_Обр_ИсполняемыеПредставления_МО
КОНС_Обр_ПостроениеИГенерацияЗапросов_МО
```

Для каждого записать launch, update scope, duration, passed/failed/skipped и exact failure messages.

- [ ] **Step 2: Run full YAxUnit suite**

Использовать тот же launch/update scope и timeout не меньше фактически необходимого полному набору. Не выдавать partial run за full suite; записать operation result and report path.

- [ ] **Step 3: Run EDT diagnostic delta**

Для каждого изменённого production/test module сравнить diagnostics с baselines Tasks 1–7. В отчёте разделить new diagnostics, unchanged background and unavailable checks.

- [ ] **Step 4: Run parser-to-semantics benchmark because hot path changed**

Использовать утверждённый corpus и процедуру `queryconsole-parser-benchmarking`: без debugger, old/current calibration, одинаковый batch count, warm-up, median and p95 per real query plus aggregate. Сравнить с сохранённым pre-change baseline; не смешивать runtime startup and query timings.

- [ ] **Step 5: Restart runtime after actual infobase update and run smoke**

После загрузки общей ветки в тестовую ИБ завершить прежний runtime, убедиться в отсутствии блокирующего EDT debugger/client process, выполнить `runtime.ensure(mode="experiment")`; если вернулась operation, ждать через `operation.wait` с `timeout_s <= 30` повторными вызовами. Выполнить smoke каталога и parameter form; `runtime.close` не вызывать без реальной необходимости.

- [ ] **Step 6: Run Vanessa UI acceptance without debugger**

Перезапустить test client, закрыть повторяющиеся modal prompts manually if manager сообщает blocked state, затем выполнить существующие scenarios каталога and parameters, включая `ТестСотрудникиОрганизацииБезВТФизлица.feature` and `ТестПараметрыСрезаПоследних.feature`. На long pause запрашивать Vanessa/client state and screenshot. Записать passed/failed steps and modal/manual actions.

- [ ] **Step 7: Verify repository invariants**

```powershell
git diff --check
git status --short --branch
rg -n "ПоставщикИсполняемыхПредставлений|ДанныеПоставщика" "QueryConsoleZUP/src/DataProcessors/КонструкторЗапросов/Forms" "QueryConsoleZUP/src/CommonModules/КонструкторЗапросовФормы/Module.bsl"
rg -n "ОписаниеТаблицы\(|ТаблицаСуществует\(" "QueryConsoleZUP/src/CommonModules/СемантическийАнализВыраженийУтилиты/Module.bsl" "QueryConsoleZUP/src/DataProcessors/СемантическийАнализВыраженийПосетитель/ObjectModule.bsl"
git diff --name-only master...HEAD -- "**/Form.form"
```

Ожидается: clean diff check; только осознанные files в status; UI search без provider/raw accesses; semantic search без full/existence lookups; `Form.form` output empty.

- [ ] **Step 8: Perform independent read-only review**

Передать reviewer-у spec, этот plan and full `master...HEAD` diff. Review должен отдельно проверить semantic dispatch/callers, temporary/local schema contamination, registry route parsing first delimiter, custom provider UI, neutral parameter completeness, server-only raw adapter and absence of new cache lifetime. Исправить все Critical/High findings через новые failing tests and повторить affected verification.

- [ ] **Step 9: Write exact verification report and final commit**

В `docs/research/2026-09-02-metadata-provider-unified-verification.md` указать commit SHA, environment, all exact commands/tools, timings, results, failures, runtime MCP usefulness/errors, Vanessa MCP usefulness/errors, manual modal actions and remaining gaps. В `docs/research/2026-09-02-metadata-provider-unified-pr.md` поместить готовый PR body с разделами `Что изменено`, `Семантика`, `UI`, `Проверки`, `Производительность`, `Runtime и Vanessa`, `Известные ограничения` и фактическими результатами из verification report. Затем:

```powershell
git add -- "docs/research/2026-09-02-metadata-provider-unified-verification.md" "docs/research/2026-09-02-metadata-provider-unified-pr.md"
git commit -m "docs: record unified metadata provider verification"
```

- [ ] **Step 10: Push combined branch and create ready PR**

```powershell
git push -u origin feature/metadata-provider
gh pr create --base master --head feature/metadata-provider --title "feat: unify metadata provider boundaries" --body-file "docs/research/2026-09-02-metadata-provider-unified-pr.md"
```

PR body должен содержать semantic and UI scope, architecture boundary, exact test/benchmark/runtime/Vanessa evidence, independent review result and known gaps. Не использовать `--draft`.

- [ ] **Step 11: Close replaced PRs only after replacement is visible and ready**

Проверить URL/state нового PR, затем оставить в #76 and #77 comments со ссылкой на replacement and close them. Старые branches and worktrees не удалять в этом плане: это отдельная destructive cleanup operation после merge.
