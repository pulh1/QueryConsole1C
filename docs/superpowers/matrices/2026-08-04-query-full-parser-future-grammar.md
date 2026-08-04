# Future-grammar coverage полного парсера — Task 10

Живой EDT-модуль: `CommonModules/КОНС_Обр_ПарсерБудущаяГрамматика_МО/Module.bsl`, content hash `7da7a5d46d80a7df`. Его explicit module-filter gate сохранён без изменений.

Task 10 exact module run: report `725d8a737_36b73a2a69d631547d3c684d8ed3e380dfdcbf45`, **7 total / 0 passed / 4 failed / 3 errors / 0 skipped**. Это ожидаемая opt-in RED-дистрибуция, а не main GREEN.

| Row | Test / case | Exact input | Desired contract | Actual evidence | Outcome | Budget |
|---|---|---|---|---|---|---|
| FG01 | `ПовторныеУнарныеЗнакиРазбираются` | `--1` | `УнарнаяОперация`; два сохранённых знака `-`; nested constant `1` | parser error: `Значение не является значением объектного типа (Знаки)`; AST contract не получен | ERROR / RED | pre-existing future RED; outside 101 |
| FG02 | `НеделяСохраняетИмяФункции` | `НЕДЕЛЯ(&Дата)` | `ФункцияЧастьПериодаЧислом`; parameter `Дата`; `ИмяФункции=НЕДЕЛЯ` | parsed; actual `ВРег(Узел.ИмяФункции)=ДЕНЬМЕСЯЦА` | FAILED / RED | pre-existing future RED; outside 101 |
| FG03 | `НезавершеннаяБинарнаяОперацияСообщаетОбОжидаемомТокене` | `1 +` | exception contains `Синтаксическая ошибка. Ожидается следующий токен` | actual `{(1, 3)}: Синтаксическая ошибка. Неожиданный токен "+"` | FAILED / RED | pre-existing future RED; outside 101 |
| FG04 | `МодификаторПолногоЗапросаБудущаяГрамматикаCase` / M06 | `ВЫБРАТЬ ПЕРВЫЕ 5 РАЗЛИЧНЫЕ РАЗРЕШЕННЫЕ 1` | first=5; distinct=Истина; allowed=Истина | parser error `Поле объекта не обнаружено (ВыбиратьРазрешенные)`; no AST; preflight `696aabbdb_543b4d259945c4b680c30f7339fac3665b8fc262` | ERROR / RED | represented executable modifier RED; inside 101 |
| FG05 | `МодификаторПолногоЗапросаБудущаяГрамматикаCase` / M07 | `ВЫБРАТЬ ПЕРВЫЕ 5 РАЗРЕШЕННЫЕ РАЗЛИЧНЫЕ 1` | first=5; distinct=Истина; allowed=Истина | parsed: first=5, allowed=Истина, actual distinct=Ложь; preflight `d8cfe1f1f_a05525b9f125c94d661adc63d2b86b36f58272aa` | FAILED / RED | represented executable modifier RED; inside 101 |
| FG06 | `МодификаторПолногоЗапросаБудущаяГрамматикаCase` / M10 | `ВЫБРАТЬ РАЗЛИЧНЫЕ ПЕРВЫЕ 5 РАЗРЕШЕННЫЕ 1` | first=5; distinct=Истина; allowed=Истина | parser error `Поле объекта не обнаружено (ВыбиратьРазрешенные)`; no AST; preflight `5b86b1cc0_8912c057bb228f05ce83c2d39adedd835b733d32` | ERROR / RED | represented executable modifier RED; inside 101 |
| FG07 | `МодификаторПолногоЗапросаБудущаяГрамматикаCase` / M14 | `ВЫБРАТЬ РАЗРЕШЕННЫЕ ПЕРВЫЕ 5 РАЗЛИЧНЫЕ 1` | first=5; distinct=Истина; allowed=Истина | parsed: first=5, allowed=Истина, actual distinct=Ложь; preflight `e522eafb6_f12ad5227705b0f2306214b2959313f133871e52` | FAILED / RED | represented executable modifier RED; inside 101 |

## Arithmetic boundary

- Main module GREEN: **97**.
- Modifier RED represented here: **4** (M06/M07/M10/M14).
- Represented executable: **97 + 4 = 101**.
- FG01–FG03 are three older opt-in REDs outside 101.
- K01–K03 are GAP evidence, not future tests and not executable cases.
