# Runtime MCP для проверки семантики metadata providers

Дата проверки: 2026-08-31.

## Итог

Runtime smoke на целевой базе недоступен и неприменим как проверка текущей
semantic-ветки: установленный `OnecInteractiveRuntime` CFE платформа не может
применить к этой базе, а runtime extension отсутствует в active session.
Это классифицировано как несовместимость platform/base/CFE, а не регрессия
metadata-provider кода.

Semantic acceptance текущей lazy-ветки выполнен напрямую через EDT-MCP/YAxUnit:
единый финальный запуск четырёх затронутых suites дал 65 tests, 65 passed,
0 failed, 0 errors и 0 skipped. Полный performance-контур от текста запроса до
непустой семантической модели измерен тем же YAxUnit harness без debugger.
Ни один runtime probe standard/executable/repeated/unknown не
интерпретировался без выполнения precondition «runtime extension загружен».

## Граница проверки

- Runtime service/repository не изменялся.
- Повторные `runtime.ensure`/restart не выполнялись после установления причины.
- Credentials, process identifiers и business data в отчёт не включены.
- Runtime MCP не использовался при реализации lazy lookup, записи BSL,
  функциональном acceptance или performance benchmark.
- Performance benchmark выполнен отдельно через EDT-MCP/YAxUnit: две
  контрбалансированные серии, включая повтор с симметричным preconditioning.

## Наблюдения frontend и service

1. BSL frontend `code.run_inline` рекламировал параметр `outputs`, но service
   отклонял BSL-запрос с ним как `invalid_request`. Возврат результата через
   messages работал, если `outputs` опустить. Это frontend/service contract
   defect, а не semantic-query defect.
2. Одна из ранних control operations завершилась по 10-секундному control
   timeout. Увеличение только этого timeout не устраняет установленную ниже
   несовместимость CFE.
3. Публичного механизма hot reload отдельного object module не обнаружено.
   Непубличный symbolic `CAPTURE` не использовался.
4. Позже stdio frontend вернул `Transport closed`, хотя persistent service
   оставался запущен. Последующая диагностика нижнего уровня использовалась
   только для классификации состояния platform/base, не как замена YAxUnit.

## Точная причина на целевой базе

Расширение `OnecInteractiveRuntime` присутствовало в database extensions и было
помечено active, но отсутствовало в списке расширений свежей active session. В
session были загружены semantic extension и `YAXUNIT`, runtime extension — нет.

Применение уже установленного CFE платформенной операцией, эквивалентной
`/UpdateDBCfg -Dynamic- -Extension OnecInteractiveRuntime`, завершилось кодом
101 и двумя диагностическими сообщениями платформы:

- `Значение контролируемого свойства РежимСовместимостиИнтерфейса у объекта не совпадает со значением в расширяемой конфигурации`;
- `Режим совместимости расширения конфигурации больше режима совместимости основной конфигурации`.

Целевая база использует платформу 8.3.27.2170, конфигурацию версии 3.1.36.41 с
режимом совместимости 8.3.24 и режимом совместимости расширений 8.3.27.
Поставляемый runtime CFE объявляет compatibility 8.3.27 и interface
compatibility `TaxiEnableVersion8_2`. На ранее успешной demo-базе версии
3.1.38.41 то же runtime extension загружается в session и сообщает версию
0.1.0; на целевой базе database extension version остаётся пустой и платформа
отказывается его применять.

Проверки альтернативных гипотез — отключение `YAXUNIT`, изменение runtime safe
mode и перестроение client cache — не активировали extension; все временные
изменения свойств были восстановлены. Следовательно, новый compatible CFE либо
совместимая base version нужны до содержательного runtime smoke.

## Полезность runtime MCP

- Platform-property и RDBG/server-breakpoint probes отделили зависание
  EDT/debugger от фактической применимости extension.
- Проверка active-session extensions исключила ложный вывод «CFE установлен,
  значит код загружен».
- Точная platform diagnostic от применения CFE заменила общий bootstrap timeout
  воспроизводимой классификацией причины.

## Стоимость и потенциальный вред

- Общий timeout первоначально провоцировал проверять несколько неверных
  startup-гипотез.
- Persistent service/client state и caches могли выдавать stale signals.
- Reversible experiments с extension properties и cleanup потребовали
  заметного времени, хотя не могли исправить несовместимый CFE.
- Потеря stdio transport вынудила перейти к более низкоуровневой диагностике с
  большим риском неверно смешать infrastructure и product evidence.

## Сравнение с EDT-MCP/YAxUnit

| Контур | Что доказал | Ограничение |
| --- | --- | --- |
| EDT source/structure/references | Актуальные BSL modules, `contentHash`, composition points и references | Статическая модель, не runtime semantics |
| EDT revalidation/diagnostics | Все 10 production/consumer и 5 test objects найдены; severe diagnostic counts не выросли | Большой существующий workspace background |
| YAxUnit через EDT-MCP | 65/65 в финальном semantic acceptance; полный benchmark в двух контрбалансированных сериях | Не заменяет отдельный runtime product transport |
| Runtime MCP | Точно классифицировал несовместимость установленного CFE и frontend defects | Semantic smoke неприменим без загруженного runtime extension |

Для acceptance metadata-provider semantics EDT-MCP/YAxUnit оказался более
надёжным прямым gate. Runtime MCP полезен как дополнительный probe только после
того, как новая session подтверждает загрузку ожидаемых runtime и semantic
extensions.

## Где runtime MCP использовался в этой работе

Runtime MCP использовался только до реализации lazy semantic path — для
проверки запуска service/frontend, наличия runtime extension в active session и
получения точной платформенной причины отказа применения CFE. Он не участвовал
в прототипировании контракта `НайтиТаблицу`/`НайтиПоле`, TDD-циклах,
редактировании модулей, финальных 65 тестах или измерениях производительности.

Практическая польза состояла в том, что инфраструктурный timeout удалось не
смешать с регрессией семантики. Практический вред — затраты времени на stale
service/client state, несовпадение frontend/service contract и эксперименты,
которые не могли сделать несовместимый CFE применимым. Для этой ветки
runtime MCP не дал дополнительного доказательства сверх EDT-MCP/YAxUnit.

## Рекомендация

1. До bootstrap проверять применимость CFE и наличие runtime extension в
   active-session list; при platform application diagnostics завершать fast.
2. Синхронизировать advertised `code.run_inline.outputs` с фактическим BSL
   service contract либо явно убрать параметр для BSL.
3. Добавить безопасную публичную операцию object-module hot reload или явно
   документировать, что поддерживается только полный reload extension.
4. Использовать runtime smoke standard/executable/repeated/unknown только на
   compatible base/CFE; до этого не трактовать timeout/transport failure как
   semantic regression.
