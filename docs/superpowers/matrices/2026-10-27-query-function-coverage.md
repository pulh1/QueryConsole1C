# Покрытие функций языка запросов

Дата проверки: 27.10.2026. Реализация: общий `ВызовФункции`, 48 имён
семантического каталога и 8 сохранённых специальных форм.

## Автоматические проверки модели

`КаталогФункцийПроходитПолныйЦиклИПроверяетАрность` проверяет для 47 имён
разбор → семантику → текст → повторный разбор, тип результата, равенство
дерева, обработку полного запроса и неправильную арность. Для 48-го имени,
`РАЗМЕРХРАНИМЫХДАННЫХ`, положительный полный цикл с полем проверяется
`РазмерХранимыхДанныхТребуетПоле`; ошибка арности включена в общий тест.

Эти проверки исполняют код модели на платформе, но не вычисляют перечисленные
функции запросом СУБД. Проверки непосредственного выполнения запроса выделены ниже.

| Имена каталога | Арность | Правило аргументов / результата |
|---|---|---|
| ПОДСТРОКА | 3 | Строка, число, число → строка |
| ГОД, КВАРТАЛ, МЕСЯЦ, ДЕНЬГОДА, ДЕНЬ, НЕДЕЛЯ, ДЕНЬНЕДЕЛИ, ЧАС, МИНУТА, СЕКУНДА | 1 | Дата → число |
| ЕСТЬNULL | 2 | Объединение описаний типов, сохранён контракт модели |
| ПРЕДСТАВЛЕНИЕ | 1 | Любой тип → строка; запрет результата в аргументах других общих функций |
| ПРЕДСТАВЛЕНИЕССЫЛКИ | 1 | Ссылка → строка; остальные типы сохраняются |
| ТИПЗНАЧЕНИЯ | 1 | Любой тип → тип |
| ДАТАВРЕМЯ | 3 / 6 | Целые числовые константы; календарная дата, год 1–3999 |
| СУММА, СРЕДНЕЕ | 1 | Число; признак агрегатности |
| МИНИМУМ, МАКСИМУМ | 1 | Сохраняют описание типа аргумента; признак агрегатности |
| СТРОКА | 1 | Примитивное значение → строка |
| ДЛИНАСТРОКИ | 1 | Строка → число |
| СОКРЛ, СОКРП, СОКРЛП, ВРЕГ, НРЕГ | 1 | Строка → строка |
| ЛЕВ, ПРАВ | 2 | Строка, число → строка |
| СТРНАЙТИ | 2 | Две строки → число |
| СТРЗАМЕНИТЬ | 3 | Три строки → строка |
| SIN, COS, TAN, ASIN, ACOS, ATAN, EXP, LOG, LOG10, SQRT, ЦЕЛ | 1 | Число → число |
| POW | 2 | Два числа → число |
| ОКР | 1 / 2 | Число, необязательная разрядность → число |
| РАЗМЕРХРАНИМЫХДАННЫХ | 1 | Поле таблицы → число |
| УНИКАЛЬНЫЙИДЕНТИФИКАТОР | 1 | Ссылка / Неопределено → UUID; NULL → NULL |
| АВТОНОМЕРЗАПИСИ | 0 | Самостоятельное поле создания ВТ без объединения → число |
| СГРУППИРОВАНОПО | 1 | Постоянное выражение либо точный ключ текущей группировки → булево |

Дополнительные проверки:

- Неизвестное имя и неправильная арность проходят синтаксис и отклоняются
  семантикой. Неправильные разделители отклоняются парсером.
- `НЕДЕЛЯ` сохраняет имя и генерирует `НЕДЕЛЯ(&Дата)`.
- `ГОД`, `ГОД.Поле`, `СТРОКА(123)` и `ВЫРАЗИТЬ(1 КАК СТРОКА(100))` различаются.
- Проверяются неизвестные типы параметров, несовместимые известные типы,
  составные типы, `NULL`, допустимые 3/6 аргументов даты и неверная дата.
- UUID проверен моделью для ссылочного поля, пустой ссылки, NULL,
  Неопределено и несовместимого числового типа.
- Контекст создания ВТ не передаётся во вложенный запрос; запрещены
  АВТОНОМЕРЗАПИСИ в арифметике, другом вызове, ГДЕ, объединении и параметрах
  виртуальной таблицы. СГРУППИРОВАНОПО проверен также в сортировке.
- СКД обходит вложенные общие вызовы; делегирование проверяет флаг функций,
  всех детей и запрещает агрегаты, контекстные функции и размер данных.
- Конструктор меняет агрегат, снимает и добавляет агрегирование, создаёт поле
  итогов с новым узлом; специальные КОЛИЧЕСТВО сохраняют отдельный узел.
- Размер данных принимает поле в скобочных оболочках и отклоняет приведение
  константы, даже когда парсер оборачивает его в Разыменование.

## Сохранённый специальный синтаксис

ВЫРАЗИТЬ, ТИП, ЗНАЧЕНИЕ, НАЧАЛОПЕРИОДА, КОНЕЦПЕРИОДА,
ДОБАВИТЬКДАТЕ, РАЗНОСТЬДАТ и КОЛИЧЕСТВО.
`ГРУППИРУЮЩИМ НАБОРАМ` в эту задачу не входит.

## Источник сигнатур и ограничения проверки

Первичный источник — локальная справка платформы 8.3.24.1758
`C:/Program Files/1cv8/8.3.24.1758/bin/shquery_ru.hbk`;
SHA256 `88c5fe533d9aafd2e9ce405ffa9ccafbc4377c58cad6216e4da02f3cf4a79aa8`.
Также проверено официальное [описание изменений платформы 8.3.20](https://dl03.1c.ru/content/Platform/8_3_20_1710/1cv8upd_8_3_20_1710.htm).

EDT выбирает для текущей базы **8.3.27.2170**. Фактического запуска на
8.3.24 не было; в доступной схеме EDT-MCP нет выбора версии платформы.
Прямое выполнение `ОКР(1.25)` и `ОКР(1.25,1)` прошло по отдельности на 8.3.27.

Совместный запуск спорных SQL-проб завершился сообщённой пользователем
неустранимой ошибкой СУБД `SQL error: Invalid syntax`. Конкретная из проб
не локализована. UUID(NULL), UUID(Неопределено) и СГРУППИРОВАНОПО без
группировки исключены из обычной регистрации тестов; их диагностические
методы сохранены для отдельной сверки на целевой платформе.
Правила UUID следуют справке. На этапе 27.10 дополнительный запрет
СГРУППИРОВАНОПО без группировки не вводился до runtime-сверки.
Эта часть уточнена исполнением 32 запросов и исправлением 04.11 на выбранной
пользователем платформе 8.3.27: постоянный аргумент допустим без группировки,
зависимый от записей должен совпадать с ключом текущего оператора.

Интерактивная проверка конструктора не выполнена: Computer Use отклонил
доступ к 1cv8c. Проверка сервисов конструктора через YAxUnit выполнена.

## Результаты прогонов

- parsergen после исправлений ревью: **761 passed, 1 skipped**, 50.02 с. Пропуск — создание Windows
  symlink без привилегии, WinError 1314; тот же пропуск был в baseline.
- Заключительный общий прогон восьми модулей YAxUnit после исправлений:
  **571 passed, 3 skipped**, без ошибок и падений.
  Первый пропуск существующий: `ПредставлениеРабочиеМестаСотрудников` читает
  `ОписаниеФильтра` вместо `ОписаниеВТФильтр`; этот дефект не менялся.
  Два других пропуска требуют `ДанныеФормыДерево` и были зарегистрированы
  тестами до изменения функций.
- Отдельная opt-in регрессия `НеделяСохраняетИмяФункции`: **1/1 passed**
  после миграции AST. Всего выполнено 572 успешных YAxUnit-сценария.
- `validate`, `generate --check`, `git diff --check` прошли.
- После точечной ревалидации новых диагностик в сопоставленных объектах
  относительно baseline нет. У парсера остаются предупреждения о префиксе
  имени и языке `ru` в неизменённом завершающем фрагменте модуля.
- Команда `tools/parsergen/benchmarks/audit_migration.py` из skill отсутствует
  в репозитории; её успешный запуск не заявляется.

## Независимое ревью

После пользовательского ревью выполнен дополнительный рефакторинг по
[согласованным семи замечаниям](../plans/2026-10-27-query-functions-review-fixes.md):
каталог вынесен в реестр с обёрткой повторного использования; массивы количеств
и допустимых типов заполняются непосредственно; фиксированный результат имеет
тип ОписаниеТипов, вывод по аргументам задаётся числом; сохранён булев признак
Агрегатная; специальные проверки выполняются по имени; базовый контекст
выражения отделён от сведений о запросе, корень хранится в посетителе.

Новые контрактные проверки дали 4 ожидаемых failures до реализации и **4/4
passed** после неё. Отдельная регрессия nullable первого аргумента и чистого
NULL следующего дала RED→GREEN. Полный модуль семантики: **35/35 passed**.
Итоговый общий прогон восьми модулей: **576 passed, 3 прежних skipped**.
В восьми затронутых объектах EDT сохранились **33 фоновых диагностики**,
новых нет; ERRORS нет. `validate`, `generate --check`, проверка байтовых
эталонов parsergen (**1/1 passed**) и `git diff --check` прошли.
Грамматика и generated parser не менялись.

Независимое ревью этих изменений отдельным агентом gpt-6-astra не выявило
существенных замечаний. Проверки на 8.3.24, прежние спорные SQL-пробы и UI
остаются обозначенными выше ограничениями.

Fresh-context ревью диапазона `382ed96..aa0dd53` выполнено отдельным агентом
gpt-6-astra. Приняты три P2-замечания: потеря оператора в сортировке,
обход ограничений через параметры ВТ и недостаточная проверка поля размера
данных. Все три воспроизведены реальными тестами YAxUnit (2 failures,
1 error), исправлены одним проходом; повторно **3/3 passed**.
После исправлений новых диагностик EDT нет; в 13 затронутых объектах остаётся
264 фоновых диагностики. Изменённый тестовый модуль не имеет ERRORS.

## Исправления по ревью семантики, 29.10.2026

Согласованный [план](../plans/2026-10-29-query-function-semantic-review.md)
выполнен относительно baseline-коммита `3f73387`. Предыдущие результаты выше
сохранены как история; текущий контракт описан в
[спецификации 29.10](../specs/2026-10-29-query-function-semantic-review-design.md).

- Реестр и его обёртка переименованы через EDT без КОНС_; UUID и флаги
  сохранены, у обёртки остаётся DuringSession.
- Ограничения типов — разреженное Соответствие с номерами аргументов с 1.
  Свободная позиция не создаёт записи; ограниченная содержит непустой массив.
  Оба читателя и вывод типов параметров используют новый контракт.
- Правила применения функций передаются явно и обязательно. Общий контекст
  не содержит текущего запроса, оператора и роли. Нет подмен/откатов контекста,
  отдельного начала обхода, готового посетителя в аргументах или хранения корня.
- Каждый анализ создаёт нового посетителя. Стек вызовов проверяет
  ПРЕДСТАВЛЕНИЕ в семи существующих парах callbacks: общий вызов, КОЛИЧЕСТВО,
  ВЫРАЗИТЬ и четыре периодные функции. Вложенный запрос имеет свой стек.
- ПроанализироватьВызовФункции проверяет аргументы и выводит тип результата.
  Все callers обработки/конструктора и самостоятельного вывода типа мигрированы.

| Проверка | Фактический результат |
| --- | --- |
| Baseline перед реализацией | 48/48 passed |
| Новый контракт ограничений | RED 6 ошибок отсутствующего поля/метода → GREEN 52/52 в двух модулях |
| Обязательные правила, отсутствие полей контекста | RED → GREEN 87/87 в трёх модулях |
| ПРЕДСТАВЛЕНИЕ в специальном синтаксисе | RED 6 случаев → GREEN 96/96 в трёх модулях |
| Полная матрица АвтоНомера и команды конструктора | 107/107 passed в трёх модулях |
| Итоговые восемь связанных модулей | 608 passed, 3 skipped, 0 failed, 0 errors (всего 611) |
| Два теста независимости посетителей после последней правки fixture | 2/2 passed |
| git diff HEAD --check | Пройден |
| Грамматика, parsergen и ПоставщикИсполняемыхПредставлений относительно baseline | Не изменены |
| Независимое read-only ревью реализации | Подтверждённых findings нет; код, тесты и метаданные проверены отдельным агентом |

Матрица АвтоНомера включает положительные случаи отдельного поля ВТ,
группировки с агрегатом в другом поле и объединения внутри источника.
Отрицательные случаи: обычная выборка, оба объединения верхнего уровня,
вложение в функцию/арифметику/ВЫБОР/скобки, WHERE, JOIN, HAVING, группировка,
сортировка, отбор СКД, параметр ВТ, итоги, индекс, дополнение периодами
и вложенный запрос. Проверены добавление поля конструктора, отклонение
недопустимых команд без изменения модели, генерация и повторный разбор,
включая сохранение имени НЕДЕЛЯ.

Прогон выполнен на **8.3.27.2170**, не на целевой 8.3.24.1758.
Подтверждённой конфигурации запуска тестов на 8.3.24 не было; ручная UI-проверка
конструктора не выполнена. Спорные UUID/GROUPING SQL-пробы не запускались.
Три прежних пропуска: несовпадение ОписаниеФильтра/ОписаниеВТФильтр в
ПредставлениеРабочиеМестаСотрудников и два сценария, требующие ДанныеФормыДерево.

Итоговая точечная ревалидация EDT охватывает 11 рабочих объектов и три тестовых
модуля. В тестах остаются прежние 33 диагностики, ERRORS=0. В рабочих объектах
все **36 ERRORS** относятся к неизменённой форме
DataCompositionAvailableTableParameters (Parameters/Items/ThisForm и другие
недоступные имена); чистота всего родительского объекта не заявляется.
Два новых extension-md-object-prefix ожидаемы по прямому требованию снять
КОНС_ с реестра; настройки общей проверки не менялись.

После полной ревалидации остаются также три constructor-function-return-section
на возврате РазобратьЗапрос: «Элементы с типом Массив не возвращается».
Метод и его возврат относительно baseline не изменены. После ревалидации
парсера и фабрики модели эти сообщения исчезают, после общей ревалидации
появляются вновь. Причина нестабильной диагностики не установлена; она не
скрыта подавлением и не объявлена исправленной. Новых ERRORS в изменённых
методах не обнаружено.

Остальные полностью полученные списки диагностик совпали с baseline без учёта
сдвига строк. Для конструктора сравнение дополнено 23 наборами MINOR по коду
проверки и списком MAJOR: отличий нет. Общий вывод MINOR ограничен сервером
100 000 символов; один из 400 фоновых MINOR не удалось выделить отдельно,
поэтому полное сравнение каждого его сообщения не заявляется.

Локальный отчёт итогового прогона:
`C:/Users/pkhlu/AppData/Local/Temp/edt-mcp-yaxunit/QueryConsoleZUP_______________66770191d_98fa4b5bebadec022956961323cd3134f9e2a7fa/report.md`.

## Уточнение СГРУППИРОВАНОПО, 04.11.2026

Пользователь согласовал исправление по результатам исполнения и указал
выполнять текущую работу на 8.3.27. Контракт и архитектура:
[спецификация](../specs/2026-11-04-groupedby-semantics-design.md),
[план](../plans/2026-11-04-groupedby-semantics.md). BASE — `bc42f70`.

Прямое исполнение через отдельные COM-процессы охватывает
[14 исходных запросов](../experiments/2026-10-29-groupedby-runtime.json)
и [18 дополнительных запросов](../experiments/2026-11-04-groupedby-runtime.json):
всего 32 разных запроса, 19 успешных и 13 ожидаемо отклонённых.
Версия загруженного comcntr.dll в каждом случае — 8.3.27.2170;
база файловая. Тексты шести новых ошибок дополнительно получены через
VBScript IDispatch, поскольку PowerShell скрывает описание COM-ошибки
за NullReferenceException. Сравнение с SQL-бэкендом не выполнялось.

Постоянные аргументы: литералы, параметр, арифметика, скалярная функция,
ВЫБОР и вложенный СГРУППИРОВАНОПО с постоянным аргументом — проходят
как с обычной группировкой, так и без неё; в опытах результат ЛОЖЬ.
СУММА(1), КОЛИЧЕСТВО(*) и подзапрос требуют контекста группировки;
без совпадения с ключом вызов недопустим. Поле при отсутствии группировки
внешнего оператора приводит к ошибке SQL; группировка во вложенном источнике
это не исправляет. Исходный NULL в ключе даёт ИСТИНА, NULL из-за пропуска
ключа в текущем наборе — ЛОЖЬ.

Семантика теперь получает признак ЗависитОтЗаписей из существующего обхода.
Кадр стека содержит имя и этот признак; поля, агрегаты, COUNT и подзапросы
отмечают активные кадры. Повторного обхода AST, подмены контекста и нового
жизненного цикла посетителя нет. Правило ПРЕДСТАВЛЕНИЕ сохранено.

Round-trip выявил связанный дефект: смесь агрегата и постоянного поля
создавала пустой СГРУППИРОВАТЬ ПО. Заголовок и ключи теперь выводит одна
private процедура генератора; дополнительные ключи рассчитываются один раз.
Если явных и дополнительных ключей нет, раздел не выводится. Автоматическое
дополнение группировки обычными полями источника сохранено отдельным тестом.

Новые регрессии: RED 15/15 (6 failures пропущенных запретов и 9 ошибок
отклонённых постоянных выражений). После семантического исправления —
14/15; оставшийся дефект генерации подтверждён точным сгенерированным
текстом. Отдельный generator RED: 1 preservation passed, 2 ошибки пустого
раздела. После обоих исправлений весь модуль семантики — **78/78**,
три связанных модуля — **124/124**.

Итоговый общий набор восьми модулей — **625 passed, 3 прежних skipped,
0 failed, 0 errors** (всего 628). Пропуски прежние: ОписаниеФильтра вместо
ОписаниеВТФильтр в ПредставлениеРабочиеМестаСотрудников и два сценария
с ДанныеФормыДерево. Процесс тестового клиента подтверждён как
`C:/Program Files/1cv8/8.3.27.2170/bin/1cv8c.exe`.
`git diff --check` пройден. Отчёт YAxUnit:
`C:/Users/pkhlu/AppData/Local/Temp/edt-mcp-yaxunit/QueryConsoleZUP_______________66770191d_98fa4b5bebadec022956961323cd3134f9e2a7fa/report.md`.

Точечная ревалидация: прежние **4** диагностики посетителя, **9** генератора
и **16** тестового модуля, ERRORS=0; новых диагностик нет.
Независимое read-only ревью реализации не выявило доказанных findings.
Матрица и итоговые результаты оформлены родительским агентом после ревью.
Метаданные, грамматика, AST, обходчик и ПоставщикИсполняемыхПредставлений
относительно BASE не изменены. Запуск на 8.3.24 не входит в текущий gate
по прямому указанию пользователя; свойства совместимости расширения сохранены.

Изменённые файлы по плану 04.11:

- [QueryConsoleZUP/src/DataProcessors/СемантическийАнализВыраженийПосетитель/ObjectModule.bsl](../../../QueryConsoleZUP/src/DataProcessors/СемантическийАнализВыраженийПосетитель/ObjectModule.bsl)
- [QueryConsoleZUP/src/DataProcessors/ГенераторТекстовЗапросов/ObjectModule.bsl](../../../QueryConsoleZUP/src/DataProcessors/ГенераторТекстовЗапросов/ObjectModule.bsl)
- [yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl](../../../yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl)
- [docs/superpowers/experiments/2026-10-29-groupedby-runtime.json](../../../docs/superpowers/experiments/2026-10-29-groupedby-runtime.json)
- [docs/superpowers/experiments/2026-11-04-groupedby-runtime.json](../../../docs/superpowers/experiments/2026-11-04-groupedby-runtime.json)
- [docs/superpowers/plans/2026-11-04-groupedby-semantics.md](../../../docs/superpowers/plans/2026-11-04-groupedby-semantics.md)
- [docs/superpowers/specs/2026-11-04-groupedby-semantics-design.md](../../../docs/superpowers/specs/2026-11-04-groupedby-semantics-design.md)
- [docs/superpowers/specs/2026-10-27-generic-query-function-calls-design.md](../../../docs/superpowers/specs/2026-10-27-generic-query-function-calls-design.md)
- [docs/superpowers/specs/2026-10-29-query-function-semantic-review-design.md](../../../docs/superpowers/specs/2026-10-29-query-function-semantic-review-design.md)
- [docs/superpowers/matrices/2026-10-27-query-function-coverage.md](../../../docs/superpowers/matrices/2026-10-27-query-function-coverage.md)

## Интерфейс реестра, 05.11.2026

Потребители и контрактные тесты обращаются к
РеестрФункцийЯзыкаЗапросов.ОписаниеФункцииЗапроса.
Этот метод нормализует имя и вызывает внутренний ПовтИсп-модуль,
который перенаправляет вызов в ОписаниеФункцииЗапросаСлужебный обычного реестра.
Служебная реализация находится в СлужебныеПроцедурыИФункции и сохраняет
Экспорт для вызова из ПовтИсп. Формирование 48 описаний не изменено;
настройки кеширования и метаданные сохранены. Прямых вызовов ПовтИсп
из потребителей и тестов нет.

Проверка 05.11 на 8.3.27.2170: **124/124 passed**, без ошибок и пропусков
в трёх связанных модулях семантики, модели выражений и построения/генерации.
Контрактные проверки каталога используют основной интерфейс реестра.
Тело формирования описания проверено как неизменённое; имена, сигнатуры,
результаты 48 функций сохранены. Диагностики EDT совпали с baseline:
30 в шести рабочих объектах и 16 в тестовом модуле, ERRORS=0.
`git diff --check` пройден. Метаданные, грамматика и
ПоставщикИсполняемыхПредставлений не менялись.

Изменённые файлы по замечанию 05.11:

- [QueryConsoleZUP/src/CommonModules/МодельЗапросаУтилиты/Module.bsl](../../../QueryConsoleZUP/src/CommonModules/МодельЗапросаУтилиты/Module.bsl)
- [QueryConsoleZUP/src/CommonModules/РеестрФункцийЯзыкаЗапросов/Module.bsl](../../../QueryConsoleZUP/src/CommonModules/РеестрФункцийЯзыкаЗапросов/Module.bsl)
- [QueryConsoleZUP/src/CommonModules/РеестрФункцийЯзыкаЗапросовПовтИсп/Module.bsl](../../../QueryConsoleZUP/src/CommonModules/РеестрФункцийЯзыкаЗапросовПовтИсп/Module.bsl)
- [QueryConsoleZUP/src/DataProcessors/ГенераторТекстовВыражений/ObjectModule.bsl](../../../QueryConsoleZUP/src/DataProcessors/ГенераторТекстовВыражений/ObjectModule.bsl)
- [QueryConsoleZUP/src/DataProcessors/ПроверкаПрименимостиОтбораПосетитель/ObjectModule.bsl](../../../QueryConsoleZUP/src/DataProcessors/ПроверкаПрименимостиОтбораПосетитель/ObjectModule.bsl)
- [QueryConsoleZUP/src/DataProcessors/СемантическийАнализВыраженийПосетитель/ObjectModule.bsl](../../../QueryConsoleZUP/src/DataProcessors/СемантическийАнализВыраженийПосетитель/ObjectModule.bsl)
- [yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl](../../../yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl)
- [docs/superpowers/specs/2026-10-27-generic-query-function-calls-design.md](../../../docs/superpowers/specs/2026-10-27-generic-query-function-calls-design.md)
- [docs/superpowers/matrices/2026-10-27-query-function-coverage.md](../../../docs/superpowers/matrices/2026-10-27-query-function-coverage.md)

## Решения при исполнении

| Решение | Основание и последствие |
|---|---|
| Продолжить исполнение после согласования без повторного разрешения | Пользователь принял план; ошибочное толкование означало бы преждевременное начало |
| Работать в текущей feature-ветке без нового worktree | К ней привязаны EDT и база; меньше изоляции, компенсировано точечными guarded-правками и коммитами |
| Использовать фактическую сигнатуру helper вывода типа параметра | Проверена через EDT; лишний аргумент из исходного плана нарушал бы вывод типа |
| Делать независимую часть модели до окончания спорных SQL-проб | AST не зависит от спорных сигнатур; при расхождении потребуется поправить описание функции и тест |
| Убрать неподтверждённые SQL-пробы из обычной регистрации | Совместный запуск дал fatal SQL; правила UUID до изолированной проверки опираются на справку |
| Не запрещать GROUPING без группировки до runtime-сверки | Требование принятой спецификации; спорный случай пока может быть отклонён самой платформой |
| Объединить implementation checkpoint после миграции consumers | Промежуточные коммиты сохраняли бы известный сбой конструктора/итогов; итоговый diff крупнее |
| Заменить отсутствующий migration audit фактическими доступными проверками | Скрипта нет в репозитории; отдельный migration audit не считается выполненным |
| Оставить непроверенные runtime/UI gates явными ограничениями | Справка и модель на 8.3.27 не доказывают поведение 8.3.24/UI; возможные расхождения потребуют доработки |
| Не расширять границы на двуязычность, группирующие наборы, точные позиции новых ошибок и performance benchmark | Это исключено scope либо не измерялось; для этих возможностей нужна отдельная работа |
| Сохранить текущую ветку без merge/push | Так предписывает принятый план; интеграция остаётся отдельным действием пользователя |

## Изменённые файлы по плану 29.10

- [docs/superpowers/matrices/2026-10-27-query-function-coverage.md](../../../docs/superpowers/matrices/2026-10-27-query-function-coverage.md)
- [docs/superpowers/plans/2026-10-27-query-functions-review-fixes.md](../../../docs/superpowers/plans/2026-10-27-query-functions-review-fixes.md)
- [docs/superpowers/plans/2026-10-29-query-function-semantic-review.md](../../../docs/superpowers/plans/2026-10-29-query-function-semantic-review.md)
- [docs/superpowers/specs/2026-10-27-generic-query-function-calls-design.md](../../../docs/superpowers/specs/2026-10-27-generic-query-function-calls-design.md)
- [docs/superpowers/specs/2026-10-29-query-function-semantic-review-design.md](../../../docs/superpowers/specs/2026-10-29-query-function-semantic-review-design.md)
- [QueryConsoleZUP/src/CommonModules/МодельЗапросаУтилиты/Module.bsl](../../../QueryConsoleZUP/src/CommonModules/МодельЗапросаУтилиты/Module.bsl)
- [QueryConsoleZUP/src/CommonModules/ОбработкаМоделиЗапроса/Module.bsl](../../../QueryConsoleZUP/src/CommonModules/ОбработкаМоделиЗапроса/Module.bsl)
- [QueryConsoleZUP/src/CommonModules/РеестрФункцийЯзыкаЗапросов/Module.bsl](../../../QueryConsoleZUP/src/CommonModules/РеестрФункцийЯзыкаЗапросов/Module.bsl)
- [QueryConsoleZUP/src/CommonModules/РеестрФункцийЯзыкаЗапросов/РеестрФункцийЯзыкаЗапросов.mdo](../../../QueryConsoleZUP/src/CommonModules/РеестрФункцийЯзыкаЗапросов/РеестрФункцийЯзыкаЗапросов.mdo)
- [QueryConsoleZUP/src/CommonModules/РеестрФункцийЯзыкаЗапросовПовтИсп/Module.bsl](../../../QueryConsoleZUP/src/CommonModules/РеестрФункцийЯзыкаЗапросовПовтИсп/Module.bsl)
- [QueryConsoleZUP/src/CommonModules/РеестрФункцийЯзыкаЗапросовПовтИсп/РеестрФункцийЯзыкаЗапросовПовтИсп.mdo](../../../QueryConsoleZUP/src/CommonModules/РеестрФункцийЯзыкаЗапросовПовтИсп/РеестрФункцийЯзыкаЗапросовПовтИсп.mdo)
- [QueryConsoleZUP/src/CommonModules/СемантическийАнализВыраженийУтилиты/Module.bsl](../../../QueryConsoleZUP/src/CommonModules/СемантическийАнализВыраженийУтилиты/Module.bsl)
- [QueryConsoleZUP/src/Configuration/Configuration.mdo](../../../QueryConsoleZUP/src/Configuration/Configuration.mdo)
- [QueryConsoleZUP/src/DataProcessors/ГенераторТекстовВыражений/ObjectModule.bsl](../../../QueryConsoleZUP/src/DataProcessors/ГенераторТекстовВыражений/ObjectModule.bsl)
- [QueryConsoleZUP/src/DataProcessors/КонструкторЗапросов/Forms/КонструкторЗапросов/Module.bsl](../../../QueryConsoleZUP/src/DataProcessors/КонструкторЗапросов/Forms/КонструкторЗапросов/Module.bsl)
- [QueryConsoleZUP/src/DataProcessors/ОбработчикРазыменованийДляСКДПосетитель/ObjectModule.bsl](../../../QueryConsoleZUP/src/DataProcessors/ОбработчикРазыменованийДляСКДПосетитель/ObjectModule.bsl)
- [QueryConsoleZUP/src/DataProcessors/ПостроительМоделиЗапроса/ObjectModule.bsl](../../../QueryConsoleZUP/src/DataProcessors/ПостроительМоделиЗапроса/ObjectModule.bsl)
- [QueryConsoleZUP/src/DataProcessors/ПроверкаПрименимостиОтбораПосетитель/ObjectModule.bsl](../../../QueryConsoleZUP/src/DataProcessors/ПроверкаПрименимостиОтбораПосетитель/ObjectModule.bsl)
- [QueryConsoleZUP/src/DataProcessors/СемантическийАнализВыраженийПосетитель/ManagerModule.bsl](../../../QueryConsoleZUP/src/DataProcessors/СемантическийАнализВыраженийПосетитель/ManagerModule.bsl)
- [QueryConsoleZUP/src/DataProcessors/СемантическийАнализВыраженийПосетитель/ObjectModule.bsl](../../../QueryConsoleZUP/src/DataProcessors/СемантическийАнализВыраженийПосетитель/ObjectModule.bsl)
- [yaxunit/src/CommonModules/КОНС_Обр_МодельВыражений_МО/Module.bsl](../../../yaxunit/src/CommonModules/КОНС_Обр_МодельВыражений_МО/Module.bsl)
- [yaxunit/src/CommonModules/КОНС_Обр_ПостроениеИГенерацияЗапросов_МО/Module.bsl](../../../yaxunit/src/CommonModules/КОНС_Обр_ПостроениеИГенерацияЗапросов_МО/Module.bsl)
- [yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl](../../../yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl)

## Файлы исходной реализации и прежних исправлений

- [QueryConsoleZUP/src/CommonModules/РеестрФункцийЯзыкаЗапросов/Module.bsl](../../../QueryConsoleZUP/src/CommonModules/РеестрФункцийЯзыкаЗапросов/Module.bsl)
- [QueryConsoleZUP/src/CommonModules/РеестрФункцийЯзыкаЗапросов/РеестрФункцийЯзыкаЗапросов.mdo](../../../QueryConsoleZUP/src/CommonModules/РеестрФункцийЯзыкаЗапросов/РеестрФункцийЯзыкаЗапросов.mdo)
- [QueryConsoleZUP/src/CommonModules/РеестрФункцийЯзыкаЗапросовПовтИсп/Module.bsl](../../../QueryConsoleZUP/src/CommonModules/РеестрФункцийЯзыкаЗапросовПовтИсп/Module.bsl)
- [QueryConsoleZUP/src/CommonModules/РеестрФункцийЯзыкаЗапросовПовтИсп/РеестрФункцийЯзыкаЗапросовПовтИсп.mdo](../../../QueryConsoleZUP/src/CommonModules/РеестрФункцийЯзыкаЗапросовПовтИсп/РеестрФункцийЯзыкаЗапросовПовтИсп.mdo)
- [QueryConsoleZUP/src/CommonModules/МодельЗапросаУтилиты/Module.bsl](../../../QueryConsoleZUP/src/CommonModules/МодельЗапросаУтилиты/Module.bsl)
- [QueryConsoleZUP/src/CommonModules/ОбработкаМоделиЗапроса/Module.bsl](../../../QueryConsoleZUP/src/CommonModules/ОбработкаМоделиЗапроса/Module.bsl)
- [QueryConsoleZUP/src/CommonModules/ОбходМоделиЯзыкаВыражений/Module.bsl](../../../QueryConsoleZUP/src/CommonModules/ОбходМоделиЯзыкаВыражений/Module.bsl)
- [QueryConsoleZUP/src/CommonModules/СемантическийАнализВыраженийУтилиты/Module.bsl](../../../QueryConsoleZUP/src/CommonModules/СемантическийАнализВыраженийУтилиты/Module.bsl)
- [QueryConsoleZUP/src/CommonModules/ЭлементыМоделиЗапроса/Module.bsl](../../../QueryConsoleZUP/src/CommonModules/ЭлементыМоделиЗапроса/Module.bsl)
- [QueryConsoleZUP/src/Configuration/Configuration.mdo](../../../QueryConsoleZUP/src/Configuration/Configuration.mdo)
- [QueryConsoleZUP/src/DataProcessors/ГенераторFeatureФайлов/ObjectModule.bsl](../../../QueryConsoleZUP/src/DataProcessors/ГенераторFeatureФайлов/ObjectModule.bsl)
- [QueryConsoleZUP/src/DataProcessors/ГенераторТекстовВыражений/ObjectModule.bsl](../../../QueryConsoleZUP/src/DataProcessors/ГенераторТекстовВыражений/ObjectModule.bsl)
- [QueryConsoleZUP/src/DataProcessors/ОбработчикРазыменованийДляСКДПосетитель/ObjectModule.bsl](../../../QueryConsoleZUP/src/DataProcessors/ОбработчикРазыменованийДляСКДПосетитель/ObjectModule.bsl)
- [QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl](../../../QueryConsoleZUP/src/DataProcessors/Парсер/ObjectModule.bsl)
- [QueryConsoleZUP/src/DataProcessors/Парсер/Templates/ОпределенияИдентификаторов/Template.txt](../../../QueryConsoleZUP/src/DataProcessors/Парсер/Templates/ОпределенияИдентификаторов/Template.txt)
- [QueryConsoleZUP/src/DataProcessors/ПостроительМоделиЗапроса/ObjectModule.bsl](../../../QueryConsoleZUP/src/DataProcessors/ПостроительМоделиЗапроса/ObjectModule.bsl)
- [QueryConsoleZUP/src/DataProcessors/ПроверкаПрименимостиОтбораПосетитель/ObjectModule.bsl](../../../QueryConsoleZUP/src/DataProcessors/ПроверкаПрименимостиОтбораПосетитель/ObjectModule.bsl)
- [QueryConsoleZUP/src/DataProcessors/СемантическийАнализВыраженийПосетитель/ObjectModule.bsl](../../../QueryConsoleZUP/src/DataProcessors/СемантическийАнализВыраженийПосетитель/ObjectModule.bsl)
- [QueryConsoleZUP/src/DataProcessors/Шаблон_ПосетительМоделиВыражений/ObjectModule.bsl](../../../QueryConsoleZUP/src/DataProcessors/Шаблон_ПосетительМоделиВыражений/ObjectModule.bsl)
- [docs/superpowers/matrices/2026-10-27-query-function-coverage.md](../../../docs/superpowers/matrices/2026-10-27-query-function-coverage.md)
- [docs/superpowers/plans/2026-10-27-generic-query-function-calls.md](../../../docs/superpowers/plans/2026-10-27-generic-query-function-calls.md)
- [docs/superpowers/plans/2026-10-27-query-functions-review-fixes.md](../../../docs/superpowers/plans/2026-10-27-query-functions-review-fixes.md)
- [docs/superpowers/specs/2026-10-27-generic-query-function-calls-design.md](../../../docs/superpowers/specs/2026-10-27-generic-query-function-calls-design.md)
- [tools/parsergen/grammar/query-language.grammar](../../../tools/parsergen/grammar/query-language.grammar)
- [tools/parsergen/tests/fixtures/reference_parser/ObjectModule.bsl](../../../tools/parsergen/tests/fixtures/reference_parser/ObjectModule.bsl)
- [tools/parsergen/tests/fixtures/reference_parser/Templates/ОпределенияИдентификаторов/Template.txt](../../../tools/parsergen/tests/fixtures/reference_parser/Templates/ОпределенияИдентификаторов/Template.txt)
- [tools/parsergen/tests/test_artifacts.py](../../../tools/parsergen/tests/test_artifacts.py)
- [tools/parsergen/tests/test_direct_python_bsl_artifact_fence.py](../../../tools/parsergen/tests/test_direct_python_bsl_artifact_fence.py)
- [tools/parsergen/tests/test_reference_parser.py](../../../tools/parsergen/tests/test_reference_parser.py)
- [tools/parsergen/tests/test_repository_grammar.py](../../../tools/parsergen/tests/test_repository_grammar.py)
- [tools/parsergen/tests/test_repository_grammar_metrics.py](../../../tools/parsergen/tests/test_repository_grammar_metrics.py)
- [tools/parsergen/tests/test_value_table_codec.py](../../../tools/parsergen/tests/test_value_table_codec.py)
- [yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl](../../../yaxunit/src/CommonModules/КОНС_ОМ_ОбработкаМоделиЗапроса/Module.bsl)
- [yaxunit/src/CommonModules/КОНС_Обр_МодельВыражений_МО/Module.bsl](../../../yaxunit/src/CommonModules/КОНС_Обр_МодельВыражений_МО/Module.bsl)
- [yaxunit/src/CommonModules/КОНС_Обр_Парсер_МО/Module.bsl](../../../yaxunit/src/CommonModules/КОНС_Обр_Парсер_МО/Module.bsl)
- [yaxunit/src/CommonModules/КОНС_Обр_ПарсерБудущаяГрамматика_МО/Module.bsl](../../../yaxunit/src/CommonModules/КОНС_Обр_ПарсерБудущаяГрамматика_МО/Module.bsl)
- [yaxunit/src/CommonModules/КОНС_Обр_ПостроениеИГенерацияЗапросов_МО/Module.bsl](../../../yaxunit/src/CommonModules/КОНС_Обр_ПостроениеИГенерацияЗапросов_МО/Module.bsl)
