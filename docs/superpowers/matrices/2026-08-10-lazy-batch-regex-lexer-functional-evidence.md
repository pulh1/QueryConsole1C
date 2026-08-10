# Lazy batch-regex lexer: functional evidence

## Итог

Production lexer сохраняет batch-regex recognition, но больше не хранит
полный массив materialized tokens. СледующийТокен() последовательно читает
platform Match[], пропускает trivia и создаёт ровно один значимый token на
возврат.

Generated parser и его public integration contract не изменялись.
Performance benchmarks и profiler в этой задаче намеренно не запускались.

## Состояние lexer

После refactoring module state содержит:

- ИсходныйТекст;
- Совпадения;
- ИндексСледующегоСовпадения;
- ОжидаемаяПозиция;
- ПереводыСтрок;
- СостояниеПозиции;
- ПозицияEOF;
- ранее существовавшие immutable-after-init keyword, regex и token constants.

Удалены:

- Токены;
- ИндексСледующегоТокена;
- ОтложеннаяОшибка.

Актуальный EDT content hash production lexer: f954b1bb7b619052.

## Установка текста

УстановитьОбрабатываемыйТекст() выполняет:

1. сохранение source;
2. один основной СтрНайтиВсеПоРегулярномуВыражению() для lexical matches;
3. существующий отдельный scan переводов строк;
4. инициализацию match cursor, coverage и source-position state;
5. вычисление совместимой позиции EOF отдельным position state.

Метод не проверяет будущие gaps, не классифицирует matches, не преобразует
literals и не создаёт tokens.

## Последовательное чтение и coverage

СледующийТокен() сравнивает начало текущего match с ОжидаемаяПозиция.
Whitespace и // comment продвигают cursor без token allocation. Значимый match
получает source position, классифицируется и materializes один token.

Cursor обновляется только:

- после успешной проверки и пропуска trivia;
- после успешного построения значимого token.

После исчерпания matches отдельно проверяется непокрытый tail. Gap и tail не
могут исчезнуть из token stream.

## Lazy error reporting

Deferred error structure больше не нужна. При gap или conversion error lexer
вызывает совместимую диагностику непосредственно из СледующийТокен().
Ошибочный match cursor не продвигается, поэтому повторный вызов воспроизводит
то же исключение.

Test ОшибкаВыдаетсяТолькоПриДостиженииCursor устанавливает текст с двумя
корректными строками, comment trivia и неизвестным символом в третьей строке.
Установка завершается успешно, затем возвращаются шесть значимых tokens, после
чего возникает:

~~~text
{(3, 12)}: Не удалось разобрать запрос
~~~

## Source positions и EOF

Source positions используют прежний массив CR/LF/CRLF matches и одно
монотонное streaming state. После trivia или multiline literal функция позиции
догоняет нужный absolute offset без повторного поиска от начала source.

EOF сохраняет прежнюю token structure и координату сразу после source.
Повторные вызовы после EOF проверены на одинаковые type, line и column.

## Legacy-compatible # identifiers

Исторический scanner проверяет первый символ после # по полному множеству
identifier continuation, включающему цифры. Batch regex приведён к этому
контракту:

- #1 и #123Таблица являются ID_СРешеткой;
- # и #@ остаются lexical errors.

Эти cases находятся и в прямом regression test, и в synthetic old/new
differential corpus.

## Изменённые tests

Модуль КОНС_Обр_ЛексическийАнализатор_МО:

- заменил ошибочное ожидание rejection для #1 на positive и negative cases;
- добавил дальний lazy error-timing fixture;
- проверяет повторный EOF;
- сравнивает digit-leading # identifiers со старым lexer.

Актуальный EDT content hash test module: 7a21e2b9ae9c1b00.

## Functional verification

Baseline перед изменениями:

- lexer suite: 163 / 163 passed.

RED:

- ЦифраПослеРешеткиДопускается: 0 / 2 passed, 2 expected assertion
  failures, 0 errors.

Focused GREEN:

- hash identifier positive/negative: 4 / 4 passed;
- identifier and invalid-input group: 14 / 14 passed;
- lazy source/error/EOF/trivia/literal group: 21 / 21 passed;
- repeated EOF: 2 / 2 passed;
- synthetic differential after adding #1: 1 / 1 passed.

Full verification before review:

- lexer suite: 166 / 166 passed;
- differential/numeric exact tests: 4 / 4 passed;
- parser suites: 224 / 224 passed.

Fresh final combined verification after review:

- lexer + parser + parser-query modules: 390 / 390 passed;
- failed: 0;
- errors: 0;
- skipped: 0.

YAxUnit report:

~~~text
C:\Users\pkhlu\AppData\Local\Temp\edt-mcp-yaxunit\QueryConsoleZUP_______________cda425a32_62db746d033eac067054538fb99ecb6199778a90\report.md
~~~

EDT revalidation:

- production objects found/validated: 2 / 2;
- yaxunit objects found/validated: 3 / 3;
- targeted ERROR markers: 0.

Existing project background after validation:

- QueryConsoleZUP: 36 ERRORS;
- yaxunit: 13 ERRORS.

## Parser

Parser source was not changed. EDT content hash remains f536869601e718ca. Its
callers still set source and fill the existing two-token buffer through
СледующийТокен().

## Review

Correctness/readability review found no production findings. One verification
gap was found and fixed: digit-leading # identifiers were initially covered
only by direct regression tests, not by old/new differential input.

Architecture review confirmed:

- production state has no Token[];
- setter invokes no token constructor or literal conversion;
- СледующийТокен() materializes at most one significant token per return;
- already returned tokens are not retained by lexer;
- composed regex remains split by lexical category;
- parser, grammar and model files are unchanged.

## Performance evidence exclusion

No performance benchmark was run for this change.

Earlier runtime series used EDT launch configuration
QueryConsoleZUP Тонкий клиент with:

~~~xml
<booleanAttribute
    key="com._1c.g5.v8.dt.launching.core.ATTR_SHOW_PERFORMANCE"
    value="true"/>
~~~

Those absolute timings are not used as evidence here and require a separate
clean rerun with the flag disabled. The earlier timing calls themselves were
ordinary run_yaxunit_tests calls; later DEBUG launches were diagnostic only.
