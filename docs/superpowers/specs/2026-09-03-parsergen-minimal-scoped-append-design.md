# Минимальный scoped append для parsergen

> **Status:** Superseded by [`2026-09-05-parsergen-minimal-multi-target-design.md`](2026-09-05-parsergen-minimal-multi-target-design.md). Historical design evidence is retained; scoped owner semantics are not part of parsergen 0.3.0.

## Цель

Добавить в разделённый semantic profile две формы:

```text
^Owner.Collection += anchor
^Owner.Collection += $CurrentField
```

Они добавляют одно значение в коллекцию ближайшего активного builder типа
`Owner`. Возможность нужна Worker-проекции BSL, но остаётся универсальной и не
содержит BSL-имён.

## Граница решения

Решение строится непосредственно поверх `origin/master`, где уже слит #78 с
разделением syntax grammar и semantic profile. В него не входят coalesced
semantic owners, `FactSeq`, `SemanticResultKind`, result-shape analysis,
performance benchmark framework или изменение существующих IR dataclass
contracts.

Единственный новый IR-примитив — value tap:

```python
AppendNearestOwner(owner, property, value, current_field, source_span)
```

Ровно одно из `value` и `current_field` заполнено. Anchor-форма получает уже
разобранное значение, записывает его во внешний owner и передаёт то же значение
существующему receiver. `$CurrentField` является zero-width эффектом и наружу
значение не возвращает.

## Семантика

- Выбирается ближайший активный owner с точным именем constructor.
- Вложенный owner того же типа затеняет внешний.
- Отсутствующий owner означает no-op, а не ошибку выполнения.
- Порядок эффектов совпадает с текстовым порядком semantic profile.
- Anchor разбирается ровно один раз, а каждый scoped append выполняется ровно
  один раз.
- Старые `Property += anchor`, propertyless `+= anchor`, `-=`, wrap и scalar
  bindings сохраняют прежний смысл и публичную модель.
- Combined grammar отвергает ведущий `^` с `GP010`.
- Generated Python backend поддерживает scoped append. Canonical BSL и hybrid
  backends fail closed до rendering/routing.
- Эффект разрешён в base-ветви direct left recursion и запрещён в recursive
  suffix.

## Валидация

Profile parser создаёт отдельные scoped records, не меняя поля существующего
`SemanticAlternative`. Source binding оборачивает единственное исходное
значение и прежний receiver, поэтому fan-out не превращается в коллекцию
семантических результатов.

До lowering проверяются:

- существование anchor и owner constructor;
- collection-категория target field и отсутствие конфликта со scalar field;
- доступность текущего builder для `$CurrentField`;
- definite scalar write поля `$CurrentField` на всех путях до эффекта;
- запрет эффекта в recursive LR suffix.

Для group используется пересечение definite writes, optional учитывает путь
без ветви, repeat трактуется консервативно, nonterminal call не переносит
состояние текущего builder.

## IR, optimizer и runtime

Scoped wrapper прозрачен для recognition и result selection. Existing
`ResolvedRegion(result_index=...)` продолжает определять, публикуется ли
значение наружу. Поэтому tap на punctuation/discard выполняется с payload, но
не превращает result-less region в value result.

В первой версии scoped IR является барьером для преобразующих semantic
optimizer passes; сохраняется только удаление недостижимых productions.
Legacy profiles используют прежний optimizer без изменений.

Generated Python включает owner stacks только если artifact реально содержит
scoped append. Stack открывается при создании соответствующего builder. При
успехе owner сначала freeze, затем снимается со stack, после чего готовый child
доставляется родителю. Общий `finally` очищает stacks после syntax, freeze или
append error. Legacy generated module должен остаться byte-identical.

## Совместимость и критерии приёмки

- Все существующие parsergen tests проходят.
- Существующие поля `SemanticAlternative`, `SourceConstructor`,
  `ConstructNode` и `ParserIr` не меняются.
- Нет imports/символов `FactSeq`, `SemanticResultKind`, coalescer operations или
  `semantic_result_shape.py`.
- Есть regressions для nearest-owner, shadowing, no-op, единственной доставки,
  `$CurrentField`, punctuation/discard, LR, cleanup, backend fences и ordinary
  heterogeneous wrap.
- Production diff — целевой максимум 2 000 добавленных строк; общий diff с
  тестами и документацией — целевой максимум 4 000 строк. Превышение требует
  отдельного объяснения до PR.
