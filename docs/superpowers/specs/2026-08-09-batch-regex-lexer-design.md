# Batch-regex lexer языка запросов 1С

## Статус и цель

Документ задаёт production-дизайн переработки
DataProcessor.ЛексическийАнализатор: посимвольный BSL-scanner заменяется одним
batch regex scan и линейной materialization потока токенов. Цель —
существенно уменьшить стоимость lexer без изменения grammar, generated
parser, AST/model semantics и фактически поддерживаемого языка.

Результат должен одновременно:

- сохранять подтверждённый parser/token contract;
- не пропускать неизвестные символы между regex matches;
- корректно сохранять значения literals и source positions;
- выдавать корректные токены до первой лексической ошибки;
- оставлять regex читаемым и изменяемым по lexical categories;
- использовать существующие differential tests и benchmark infrastructure;
- показывать ускорение полного production lexer path, а не только regex scan.

Спецификация фиксирует пять намеренных исправлений старого поведения:

1. НомерСимвола у ID_СРешеткой указывает на #;
2. цифра не может быть первым символом после #;
3. одиночный CR завершает однострочный комментарий;
4. CR, LF и CRLF единообразно учитываются как переводы строк, причём CRLF
   считается одним переводом;
5. EOF указывает на позицию сразу после всего source, а не сохраняет номер
   строки начала последнего значимого токена.

Любое другое отличие от текущего lexer считается дефектом либо требует
отдельного согласованного решения.

## Подтверждённое исходное состояние

Production lexer находится в:

    QueryConsoleZUP/src/DataProcessors/ЛексическийАнализатор/ObjectModule.bsl

Он выполняет разбор преимущественно посимвольно на BSL. СледующийТокен()
пропускает whitespace и комментарии, затем распознаёт identifier,
ID_СРешеткой, literal или lexeme. Конец потока представлен структурой токена
с Тип = Неопределено, а не значением Неопределено вместо токена.

Generated parser использует двухтокенный lookahead и получает токены через
СледующийТокен(). В downstream-коде подтверждено использование полей:

- Тип;
- Лексема;
- Значение у literals;
- НомерСтроки;
- НомерСимвола.

Поле Класс parser не читает, но оно входит в существующий токенный контракт и
проверяется lexer tests. На первом этапе оно сохраняется.

В yaxunit уже находится неизменяемая историческая копия lexer:

    yaxunit/src/DataProcessors/КОНС_СтарыйЛексическийАнализатор/

Она используется как differential oracle и runtime baseline. Её исходники и
public methods в рамках переработки не изменяются.

Существующий benchmark harness:

    yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО/Module.bsl

уже поддерживает полный lexer pass, parser pass, corpus, прогрев, batch
calibration, median/p95 и durable sidecars. Параллельный harness не создаётся.

Исторические измерения служат ориентиром, но не заменяют новый paired run.
Durable baseline содержит 843 значимых токена для large_package и 19 617 для
time_accounting_large. Предоставленный в контексте задачи batch prototype
показал совпадение количества значимых токенов и большой запас ускорения
scan-only пути. В tracked worktree этот prototype сейчас отсутствует, поэтому
его диагностический вариант переносится в существующий benchmark module, а не
в отдельный harness. Production verdict должен учитывать classification,
materialization, literal conversion, source positions и чтение всех токенов
до EOF.

## Границы

### В scope

- замена production lexer на batch-regex architecture;
- сохранение parser integration через СледующийТокен();
- однократная инициализация regex, keywords, lexemes и классов токенов;
- полная materialization значимых токенов при установке текста;
- deferred lexical error, сохраняющая streaming-поведение;
- исправление пяти явно перечисленных дефектов;
- regression и differential tests;
- comment-heavy, string-heavy и numeric-dense stress cases;
- расширение существующего benchmark harness;
- измерение lexer, lexer + parser и доступного semantic frontend;
- удаление устаревшего lexer text reconstruction API и связанной UI-формы.

### Вне scope

- изменение query grammar;
- оптимизация или рефакторинг generated parser;
- изменение AST/model semantics;
- добавление новых keywords, operators или syntax features;
- C-style и другие block comments;
- изменение исторического lexer baseline;
- compact token IR, требующий переделки parser;
- micro-optimizations без benchmark evidence.

## Public API и cleanup

Production lexer сохраняет:

- Инициализировать();
- УстановитьОбрабатываемыйТекст(Текст);
- СледующийТокен();
- ТипыТокенов() как compatibility API вне hot path.

Удаляется экспортная функция ПолучитьТекстЗапроса(). Вместе с ней удаляются
private helpers ПредставлениеТокена() и ПредставлениеТокенаКонстанта().
Подтверждённых production consumers у этого API нет, кроме устаревшей ручной
формы самого lexer.

Через EDT удаляется вся форма:

    QueryConsoleZUP/src/DataProcessors/ЛексическийАнализатор/Forms/Форма/

Её единственная команда измеряет восстановление текста через удаляемый API и
дублирует постоянный YAxUnit benchmark harness. Вызовы платформенного
СхемаЗапроса.ПолучитьТекстЗапроса() в других объектах не затрагиваются.

Из current lexer tests удаляются только регистрации и реализации двух тестов,
проверяющих reconstruction через Лексер.ПолучитьТекстЗапроса(). Остальные
lexer tests сохраняются и расширяются.

Старые экспортные переменные ВремяПолученияИдентификатора и
ВремяУстановкиСимволов относятся к удаляемому посимвольному scanner,
подтверждённых consumers не имеют и в production lexer не сохраняются.
Неиспользуемые internal tables, включая
КлючевыеСловаОпределяемыеСкобкой, также не переносятся. Историческая копия
lexer сохраняет их без изменений.

## Инициализация и module-level constants

BSL не предоставляет настоящих констант структурного типа. Неизменяемые
значения создаются один раз в переменных модуля и далее считаются immutable
по соглашению.

Однократно инициализируются:

- строки классов Лексема, Слово, СтроковаяКонстанта,
  ЧисловаяКонстанта, ID и ID_СРешеткой;
- Соответствие keywords;
- поддерживаемые одно- и двухсимвольные lexemes;
- именованные regex fragments;
- итоговый regex tokenization pattern;
- regex line-break pattern.

Текущая функция КлассыТокенов(), создающая новую Структура при каждом
конструкторе токена, удаляется. Конструкторы читают scalar module variables
напрямую. ТипыТокенов() остаётся compatibility API, но не вызывается при
создании токена и не участвует в hot path.

Инициализировать() должна быть идемпотентной для текущего factory lifecycle:
повторный вызов не создаёт дубликаты и не меняет lexical rules.
УстановитьОбрабатываемыйТекст() сбрасывает только состояние input и не
пересобирает constants.

## Выбранная архитектура

### Состояние input

Для установленного текста lexer хранит:

- исходную строку;
- массив materialized значимых токенов;
- индекс следующего токена;
- EOF position;
- optional deferred error: индекс выдачи, absolute offset, строку, колонку и
  текст диагностики.

Raw lexical matches и matches переводов строк являются временными данными
materialization и освобождаются после построения токенов и deferred error.

### Установка текста

УстановитьОбрабатываемыйТекст(Текст) выполняет:

1. сброс input state;
2. один СтрНайтиВсеПоРегулярномуВыражению() по lexical pattern;
3. один batch scan переводов строк по CRLF, CR или LF;
4. линейный проход по lexical matches с проверкой покрытия;
5. пропуск whitespace и comments;
6. classification значимых matches;
7. keyword lookup;
8. literal conversion;
9. вычисление source positions;
10. создание токенных структур;
11. фиксацию EOF либо первой deferred error.

Materialization прекращается на первом gap или ошибке literal conversion.
Совпадения после ошибочной позиции не используются.

### Получение токена

СледующийТокен() выполняет O(1) работу:

1. если индекс меньше количества materialized токенов, возвращает токен и
   увеличивает индекс;
2. если достигнут индекс deferred error, выбрасывает сохранённое исключение;
3. иначе возвращает EOF-токен.

После deferred error индекс не продвигается: повторный вызов снова выбрасывает
ту же ошибку. Batch scan может заранее увидеть ошибку, но parser получает все
корректные токены до неё, как при streaming scanner.

## Читаемый regex

Итоговый pattern собирается из именованных fragments в порядке:

1. whitespace;
2. line comment;
3. string literal;
4. numeric literal;
5. identifier with hash;
6. identifier;
7. two-character lexeme;
8. one-character lexeme.

Логические regex fragments:

    Whitespace:
    [ \t\r\n\f\v<NBSP>]+

    Comment:
    //[^\r\n]*

    String:
    "(?:""|[^"])*"

    Number:
    (?:[0-9]+(?:\.[0-9]*)?|\.[0-9]+)

    IdentifierWithHash:
    #[A-Za-zА-Яа-яЁё_][A-Za-zА-Яа-яЁё_0-9]*

    Identifier:
    [A-Za-zА-Яа-яЁё_][A-Za-zА-Яа-яЁё_0-9]*

    TwoCharacterLexeme:
    <=|<>|>=

    OneCharacterLexeme:
    [./<>{}%=&()*+,\-;]

NBSP добавляется в BSL pattern через Символы.НПП, а не неочевидный Unicode
escape. Внешняя non-capturing group numeric fragment обязательна: без неё
внутренний | изменит структуру верхнеуровневых alternatives.

Ключевые слова не перечисляются в regex. Identifier переводится в верхний
регистр один раз и проверяется в заранее созданном Соответствие.

## Фактическая lexical semantics

### Whitespace и line endings

Поддерживаются те же whitespace characters, что и в current lexer:

- обычный пробел;
- Tab;
- LF;
- CR;
- NBSP (Символы.НПП);
- vertical tab;
- form feed.

CR, LF и CRLF считаются переводами строки; CRLF увеличивает номер строки
ровно один раз. Остальные whitespace characters изменяют только колонку.

### Comments

Единственный comment syntax — // до CR, LF, CRLF или EOF. Весь comment
является одним raw match и не создаёт значимых токенов. Его содержимое не
может породить keywords, numbers, strings или operators.

Синтаксис /* ... */ не становится comment: при допустимом содержимом это
обычная последовательность /, *, tokens, *, /. Неизвестное содержимое
по-прежнему может привести к lexical error.

### Strings

String начинается и заканчивается двойной кавычкой. Пустая и многострочная
строки поддерживаются. Две кавычки внутри literal декодируются в одну кавычку
значения. //, keywords, numbers и operators внутри строки не
классифицируются отдельно.

Обязательные regression cases:

    ""
    "abc // 123 <> test"
    "abc ""quoted"" text"
    "abc "" // "" 123"

Незакрытая строка создаёт deferred error
Ожидается закрывающая кавычка на позиции открывающей кавычки.

### Numbers

Numeric literal использует только ASCII digits. Поддерживаются:

- 0, 42, 01;
- 12.5;
- .5;
- 1.

Знак - является отдельной lexeme. Exponent notation не добавляется.
Последовательность 1..2 сохраняет поведение current scanner: 1. и .2.

Raw numeric text преобразуется выделенной функцией. Прямое платформенное
преобразование допускается только после differential-проверки значений current
manual algorithm, включая короткие числа, leading zero, длинную дробную часть
и граничные поддерживаемые значения. Если прямое преобразование расходится,
используется минимальный совместимый conversion path, а не изменение языка.

### Identifiers и keywords

Первый символ обычного identifier — ASCII Latin letter, русская буква,
Ё/ё или _. Следующие символы дополнительно допускают ASCII digits.
Исходный регистр сохраняется в Лексема; keyword type определяется по
ВРег(Лексема).

ID_СРешеткой включает исходный # в Лексема. После # первый символ подчиняется
правилу начала обычного identifier; следующие символы — правилу продолжения.
Поэтому #ВТ, #temp_1 и #_temp допустимы, а #1, # и #@ ошибочны.

### Operators и delimiters

Поддерживаются ровно три двухсимвольные lexemes:

    <=  <>  >=

и шестнадцать односимвольных:

    . / { } < % = & > ( ) * + , - ;

Двухсимвольные alternatives располагаются раньше односимвольных префиксов.
Новые lexemes, включая !=, :, ?, [ и ], не добавляются.

## Token representation

Внешняя структура токена сохраняется:

    Класс, Тип, Лексема, НомерСтроки, НомерСимвола

Поле Значение вставляется только в string и numeric literal tokens.

| Категория | Класс | Тип | Лексема | Значение |
|---|---|---|---|---|
| Operator/delimiter | Лексема | исходная lexeme | исходная lexeme | отсутствует |
| Keyword | Слово | uppercase keyword | исходный текст | отсутствует |
| Identifier | Слово | ID | исходный текст | отсутствует |
| #Identifier | Слово | ID_СРешеткой | текст с # | отсутствует |
| String | СтроковаяКонстанта | имя класса | имя класса | decoded string |
| Number | ЧисловаяКонстанта | имя класса | имя класса | BSL Число |
| EOF | не определён | не определён | не определён | отсутствует |

StartOffset и Length не добавляются в каждую структуру: parser их не читает,
а дополнительные поля увеличат все materialized tokens. Absolute offsets
используются во время materialization и сохраняются только для deferred error.
Если будущему downstream потребуется span, это будет отдельным изменением
контракта с собственным benchmark.

Исправленная позиция ID_СРешеткой указывает на #. EOF получает позицию вставки
сразу после всего source. После завершающего CR, LF или CRLF это следующая
строка и колонка 1.

## Source positions без посимвольного scanner

Второй batch regex scan возвращает упорядоченные matches CRLF, CR или LF. При
линейном проходе по lexical matches поддерживаются:

- индекс следующего line-break match;
- текущий номер строки;
- absolute offset начала текущей строки.

Перед созданием токена line-break matches до его start offset потребляются
один раз. Колонка вычисляется как разность absolute offsets. Общая сложность —
O(raw matches + line breaks) без BSL-обхода каждого символа и binary search на
каждый токен.

Line breaks внутри многострочного string учитываются тем же потоком: сам
string получает координаты opening quote, а следующий token — координаты
после всех внутренних переводов строки.

Дополнительный batch scan является измеряемой частью production path. Если он
окажется значимой долей времени, alternatives рассматриваются только после
полного correctness pass и отдельного профиля.

## Полное покрытие и diagnostics

Для каждого lexical match выполняется invariant:

    match.НачальнаяПозиция = expectedPosition

После match:

    expectedPosition = match.НачальнаяПозиция + match.Длина

После последнего match expectedPosition должен быть равен
СтрДлина(Текст) + 1. Первый gap является lexical error; regex не имеет права
молча продолжить с более позднего поддерживаемого символа.

При gap материализованные до него tokens сохраняются. Ошибка классифицируется
по символу на expectedPosition:

- двойная кавычка — Ожидается закрывающая кавычка;
- # — Некорректный идентификатор с #;
- иначе — Не удалось разобрать запрос с корректной строкой и колонкой.

Точная форма дополнения общей диагностики координат закрепляется тестом;
неизменяемая часть существующего сообщения сохраняется.

Пример deferred behavior:

    ВЫБРАТЬ @ Поле

Первый вызов возвращает ВЫБРАТЬ; следующий выбрасывает ошибку на @; Поле
никогда не выдаётся. Повторный вызов после ошибки снова выбрасывает её.

## Classification и allocations

Raw match сначала классифицируется по первому символу:

- whitespace и comments пропускаются без извлечения полного текста;
- двойная кавычка означает string;
- # означает ID_СРешеткой;
- ASCII digit либо точка с numeric match означает number;
- identifier-start означает word;
- оставшееся допустимое совпадение означает lexeme.

Полный substring извлекается ровно один раз для значимого match. Для длинных
comments и whitespace blocks не создаётся дополнительная BSL-строка.
Keyword uppercase также вычисляется не более одного раза на word.

Сокращение token structures не входит в первый этап. Если production-complete
benchmark покажет, что создание Структура стало доминирующей стоимостью,
representation оптимизируется отдельным измеренным решением без неявного
изменения parser contract.

## Differential и regression testing

### Correct inputs

Для одного текста production и historical lexer полностью читаются до EOF.
Для каждого значимого токена сравниваются:

- ordinal position;
- Класс;
- Тип;
- Лексема;
- наличие поля Значение;
- Значение при наличии;
- НомерСтроки;
- НомерСимвола.

Также сравниваются token count и пустые поля Класс, Тип и Лексема EOF-токена.
Позиция нового EOF проверяется не по historical bug, а по независимо
вычисленной позиции конца source. Для inputs, где historical EOF position
совпадает с фактическим концом, сохраняется и прямое differential-сравнение.
Corpus включает:

- существующие lexer unit cases;
- все реальные benchmark inputs;
- подходящие .q1c проекта;
- synthetic lexical edge cases;
- comment-heavy, string-heavy и numeric-dense inputs.

Пять intentional behavior changes не скрываются общей нормализацией. Для
них создаются отдельные explicit expectations; любые другие differences
остаются failures.

EOF regression cases обязательно включают trailing whitespace, завершающий
line comment, trailing CR/LF/CRLF и многострочный string literal.

### Invalid inputs

Для некорректного текста проверяются:

- равенство token prefix до ошибки, если historical lexer также отклоняет input;
- номер вызова СледующийТокен(), выбрасывающего исключение;
- диагностическое сообщение;
- повторное исключение после ошибки;
- отсутствие silent acceptance и токенов после gap.

Лексема #1 является специальным negative regression нового lexer: historical lexer
его принимал, поэтому равенство результата для этого case не ожидается.

### Обязательные stress groups

1. large_package: около 843 значимых токенов и 1 297 raw matches.
2. time_accounting_large: 19 617 значимых токенов и около 29 717 raw matches,
   включая тысячи коротких numeric literals.
3. Детерминированный comment-heavy input с короткими и очень длинными
   syntax-like comments.
4. Детерминированный string-heavy input с escaped quotes, //, operators,
   numbers, keywords, многострочными и очень длинными literals.

Stress generators должны иметь стабильные параметры и hashes/lengths в
benchmark sidecar.

## Performance validation

Существующий КОНС_Обр_БенчмаркПарсера_МО расширяется, а не дублируется.
Historical lexer и production lexer измеряются в одинаковом lifecycle: объект
создаётся и инициализируется вне sample, а внутри sample выполняются установка
текста и чтение всех tokens, включая EOF.

Production lexer timing включает:

- lexical batch scan;
- line-break batch scan;
- coverage checks;
- classification;
- keyword lookup;
- substring extraction;
- token structure creation;
- literal conversion;
- source position calculation;
- deferred-error/EOF setup;
- чтение materialized stream через public API.

Scan-only prototype остаётся диагностическим lower bound и не используется
как итоговая новая реализация. Предоставленный prototype переносится в
untimed preflight существующего КОНС_Обр_БенчмаркПарсера_МО; там вычисляется
raw match count как metadata сценария. Production API и hot path не получают
benchmark-only instrumentation.

Для каждого corpus выполняются существующие calibration, warm-ups и samples,
публикуются median и nearest-rank p95. Итоговая таблица содержит:

- scenario/input identity;
- длину текста и количество inputs;
- значимые tokens и raw matches;
- old lexer median/p95;
- new lexer median/p95;
- относительное ускорение;
- current parser с old/new lexer, где harness допускает явную зависимость;
- полный semantic frontend, если существующий path это позволяет.

Старые durable результаты сохраняются как historical provenance. Verdict
строится по paired before/after run на одном runtime и при одинаковых внешних
условиях. Перед timing-runs сохраняется ручной gate: пользователь подтверждает,
что тяжёлые процессы остановлены.

Искусственный абсолютный target не устанавливается. Результат принимается,
если полный production lexer показывает устойчивое существенное улучшение и
сохраняет заметную часть преимущества batch scan. Если преимущество почти
исчезает, отдельно измеряются materialization, keyword lookup, line positions
и literal conversion.

## Рассмотренные alternatives

### Выбранный: full materialization и deferred error

Parser почти всегда потребляет весь token stream, поэтому upfront
materialization устраняет repeated scanner state transitions и превращает
СледующийТокен() в индексный доступ. Deferred error сохраняет последовательное
наблюдаемое поведение на некорректном input.

### Sequential regex search

Regex-вызов на каждый token сохраняет большое число переходов BSL/platform и
по предварительным microbenchmarks уступает одному batch scan.

### Lazy classification raw matches

Parser читает поток целиком, а lazy classification усложняет error timing,
positions и lifetime source без ожидаемой выгоды.

### Compact token IR и изменение parser

Может уменьшить allocations, но меняет parser contract и расширяет scope после
уже выполненной оптимизации parser. Возможность оценивается отдельно только
при доказанном доминировании token structures.

### Новый посимвольный scanner

Даже более аккуратный state machine сохраняет BSL per-character overhead,
который и является подтверждённой проблемой.

### Keywords внутри regex

Большая keyword alternative ухудшает читаемость, порядок правил и стоимость
сопровождения. Identifier и correspondence lookup проще и измеримее.

## Риски и controls

### Peak memory

Raw matches и materialized tokens кратковременно существуют одновременно.
Matches освобождаются сразу после materialization. Очень большой corpus
обязателен для runtime и memory-observation.

### Второй line-break scan

Он создаёт дополнительный массив, но устраняет BSL per-character positions.
Его доля измеряется. Оптимизация не должна ухудшать многострочные strings или
CR/LF/CRLF semantics.

### Numeric equivalence

Платформенный conversion может отличаться на крайних представлениях. До его
принятия требуется differential suite по literals corpus и synthetic
boundaries.

### Regex maintainability

BSL escaping может скрыть понятный logical pattern. Именованные fragments,
фиксированный порядок alternatives и отдельные edge-case tests обязательны
для production code review.

### Module-level mutability

Constants не экспортируются и после инициализации не меняются. Public methods
не возвращают internal mutable keyword/lexeme structures.

## Review и последовательность реализации

Реализация выполняется малыми вертикальными шагами:

1. зафиксировать tests current contract и intentional changes;
2. добавить differential harness для historical/current lexer;
3. собрать именованные regex fragments и coverage tests;
4. реализовать materialization без parser changes;
5. реализовать source positions и deferred error;
6. подключить full corpus differential tests;
7. удалить production scanner, dead instrumentation и reconstruction API;
8. удалить lexer UI-форму через EDT;
9. выполнить correctness review;
10. расширить stress corpus и benchmark reporting;
11. выполнить paired lexer/parser/frontend benchmarks;
12. провести performance и readability review;
13. исправить подтверждённые замечания;
14. повторить профильные tests и benchmarks;
15. опубликовать before/after report и remaining limitations.

Подробные команды, файлы и checkpoints задаются отдельным implementation plan
после утверждения этой спецификации.

## Критерии приёмки

- Production lexer больше не выполняет посимвольный BSL scan всего input.
- Все фактически поддерживаемые identifiers, literals и lexemes сохранены.
- Comments и strings изолируют своё содержимое одним raw match.
- Coverage invariant исключает silent skip неизвестных символов.
- Token prefix выдаётся до первой deferred error.
- Token fields и literal values совместимы с parser contract.
- Source positions корректны для whitespace, comments, multiline strings,
  CR, LF и CRLF.
- Пять intentional fixes имеют отдельные regression tests.
- Differential suite не содержит необъяснённых расхождений.
- Current parser и semantic pipeline проходят профильные tests без изменения
  grammar и model semantics.
- Regex собран из именованных читаемых fragments.
- ПолучитьТекстЗапроса() и устаревшая lexer UI-форма удалены только из
  production implementation.
- Historical lexer baseline не изменён.
- Existing benchmark scenarios и четыре stress groups измерены.
- Before/after report отражает полный production lexer path, median/p95 и
  влияние на parser/frontend.
- Получено устойчивое существенное ускорение либо задача не считается
  завершённой и причина исследуется до принятия архитектуры.
- Remaining limitations не содержат известных correctness blockers.
