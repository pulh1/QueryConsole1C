# QueryConsole parser benchmarking skill design

## Цель

Создать repo-local skill `queryconsole-parser-benchmarking`, который делает
повторяемыми runtime-замеры parser/lexer через EDT-MCP и YAxUnit и не допускает
ложную provenance или сравнение несовместимых серий.

## Наблюдаемые проблемы

- benchmark descriptor может содержать commit и SHA предыдущего parser;
- общий тестовый модуль регистрирует old/current parser и lexer, хотя запрос
  пользователя часто относится только к одной реализации;
- raw sidecar, durable evidence и Markdown-вывод легко перепутать;
- одиночная последовательная серия показывает направление, но не отделяет
  order/environment effect;
- параметры методики и набор corpus меняются, поэтому их нельзя дублировать в
  skill как константы.

## Размещение и границы

Skill размещается в `.codex/skills/queryconsole-parser-benchmarking/` и
содержит только `SKILL.md` и `agents/openai.yaml`. Отдельные scripts,
references и assets пока не нужны: исполняемые проверки уже находятся в
репозитории, а актуальные параметры живут в BSL harness и JSON sidecar.

Существующий `queryconsole-parsergen-development` остаётся источником правил
изменения generator и получает обязательную ссылку на новый skill для runtime
benchmark. Новый skill не проектирует parser и не меняет grammar semantics.

## Контракт workflow

1. Прочитать активный benchmark plan, harness и доступные тесты.
2. Зафиксировать точный scope: old/current, parser/lexer, timing/counters.
3. Перед запуском проверить чистоту дерева, актуальный parser artifact SHA и
   descriptor provenance. Не выдавать timing с заведомо ложной provenance.
4. Запускать через EDT-MCP `run_yaxunit_tests` ровно выбранные test names.
5. Сохранить raw sidecar отдельно от предыдущих evidence и проверить SHA
   исходного и durable файла.
6. Валидировать schema, corpus order/identity, input lengths, warmups, samples,
   batch и artifact rows по данным самого sidecar и актуальных validator scripts.
7. Считать median, p95, batch size и CV. Сравнивать только выровненные corpus.
8. Маркировать single sequential comparison как направляющее. Для финального
   verdict использовать counterbalanced/повторную серию, заданную актуальным
   plan или пользователем.
9. В handoff явно перечислять реально запущенные реализации, evidence paths,
   runtime/platform, проверки, ограничения и фоновые ошибки.

## Dynamic source of truth

Skill должен находить, а не запоминать:

- имена тестов и sidecar в
  `yaxunit/src/CommonModules/КОНС_Обр_БенчмаркПарсера_МО/Module.bsl`;
- текущую методику в harness и активном `docs/superpowers/plans/*benchmark*`;
- parser SHA через существующий provenance utility или эквивалентную проверку;
- runtime launch configuration через EDT-MCP discovery;
- corpus manifest и числовые ожидания через sidecar/validator.

Никакие commit IDs, SHA, даты evidence, количество corpus, warmup/sample count
или batch target не фиксируются в skill как вечные значения.

## Проверка skill

Проверить три сценария:

1. «Запусти только новый parser» — выбирается один test, old/lexer исключены,
   stale descriptor блокирует запуск до исправления provenance.
2. «Сравни старый и новый» — проверяется выравнивание corpus и различается
   sequential evidence и final counterbalanced verdict.
3. «Повтори замер быстро» — предыдущий durable JSON не перезаписывается, а
   methodology не угадывается по памяти.

Статически выполнить `quick_validate.py`, проверить отсутствие placeholders и
соответствие `agents/openai.yaml` содержимому skill.
