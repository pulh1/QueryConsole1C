"""Formal arguments must not shadow generated BSL locals or module state."""

import pytest

from tests.test_canonical_bsl_codegen import _build, _function


@pytest.mark.parametrize("parameter", [
    "ЭлементКоллекции", "элементколлекции", "ТекущийТокен", "тЕКУЩИЙтОКЕН",
    "ЛексическийАнализатор", "ОпределенияИдентификаторов", "БуферТокенов",
    "КоличествоПросматриваемыхСимволов", "ЭлементыМоделиЗапроса",
    "Терминал", "НеТерминалChild", "start", "РезультатПродукции",
    "ЭтотУзел", "СтекПродолжений", "Продолжение", "ЭлементПродолжения",
    "Значение17", "ТокенРешения0",
])
def test_bsl_rejects_formal_colliding_with_generated_namespace(parameter):
    with pytest.raises(ValueError, match="formal parameter .* collides with generated"):
        _build(
            f"<S>({parameter}) ::= @Node Items *= <Items> Next = <Child>({parameter})\n"
            "<Items> ::= @List += ITEM\n"
            "<Child>(Context) ::= @Child END",
            entrypoints={"start": "S"},
        )


def test_bsl_safe_formal_survives_collection_loop_and_child_actual():
    module = _build(
        "<S>(Context) ::= @Node Items *= <Items> Next = <Child>(Context)\n"
        "<Items> ::= @List += ITEM\n"
        "<Child>(Context) ::= @Child END",
        entrypoints={"start": "S"},
    ).module_text
    function = _function(module, "НеТерминалS")
    assert function.startswith("(Context = Неопределено)")
    assert "ЭтотУзел = ЭлементыМоделиЗапроса.Node(ТекущийТокен);" in function
    loop = "Для Каждого ЭлементКоллекции Из Значение1 Цикл"
    assert loop in function
    assert "ЭтотУзел.Items.Добавить(ЭлементКоллекции);" in function
    assert "Значение2 = НеТерминалChild(Context);" in function
    assert function.index(loop) < function.index("НеТерминалChild(Context)")
    assert function.count("Context =") == 1
