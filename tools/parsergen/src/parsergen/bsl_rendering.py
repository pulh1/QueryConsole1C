from __future__ import annotations

import re


_BSL_IDENTIFIER = re.compile(
    r"[A-Za-zА-Яа-яЁё_][0-9A-Za-zА-Яа-яЁё_]*\Z"
)

# 1C:Enterprise Developer Guide, "Reserved words", defines the classic
# bilingual language core. The grouped additions below cover the current
# exception, handler, async, literal, and preprocessor constructs which may
# also occur in generated modules. Keep the categories explicit: this is a
# code-generation safety boundary, not a convenient sample of common words.
_BSL_CONTROL_KEYWORDS = (
    "Если", "If",
    "Тогда", "Then",
    "ИначеЕсли", "ElsIf",
    "Иначе", "Else",
    "КонецЕсли", "EndIf",
    "Для", "For",
    "Каждого", "Each",
    "Из", "In",
    "По", "To",
    "Пока", "While",
    "Цикл", "Do",
    "КонецЦикла", "EndDo",
    "Попытка", "Try",
    "Исключение", "Except",
    "КонецПопытки", "EndTry",
    "ВызватьИсключение", "Raise",
    "Перейти", "Goto",
    "Возврат", "Return",
    "Продолжить", "Continue",
    "Прервать", "Break",
)
_BSL_DECLARATION_KEYWORDS = (
    "Процедура", "Procedure",
    "КонецПроцедуры", "EndProcedure",
    "Функция", "Function",
    "КонецФункции", "EndFunction",
    "Перем", "Var",
    "Экспорт", "Export",
    "Знач", "Val",
    "Асинх", "Async",
)
_BSL_OPERATOR_AND_LITERAL_KEYWORDS = (
    "И", "And",
    "Или", "Or",
    "Не", "Not",
    "Новый", "New",
    "Выполнить", "Execute",
    "Ждать", "Await",
    "ДобавитьОбработчик", "AddHandler",
    "УдалитьОбработчик", "RemoveHandler",
    "Истина", "True",
    "Ложь", "False",
    "Неопределено", "Undefined",
    "Null",
)
_BSL_PREPROCESSOR_KEYWORDS = (
    "Область", "Region",
    "КонецОбласти", "EndRegion",
)
_BSL_RESERVED_KEYWORDS = frozenset(
    keyword.casefold()
    for category in (
        _BSL_CONTROL_KEYWORDS,
        _BSL_DECLARATION_KEYWORDS,
        _BSL_OPERATOR_AND_LITERAL_KEYWORDS,
        _BSL_PREPROCESSOR_KEYWORDS,
    )
    for keyword in category
)


def validate_bsl_identifier(name: str, origin: str) -> None:
    if _BSL_IDENTIFIER.fullmatch(name) is None:
        raise ValueError(
            f"{origin} {name!r} is not a valid BSL identifier"
        )
    if name.casefold() in _BSL_RESERVED_KEYWORDS:
        raise ValueError(
            f"{origin} {name!r} is a reserved BSL keyword"
        )


def validate_bsl_member_name(name: str, origin: str) -> None:
    if _BSL_IDENTIFIER.fullmatch(name) is None:
        raise ValueError(
            f"{origin} {name!r} is not a valid BSL member name"
        )


def bsl_string(value: str) -> str:
    escaped = value.replace('"', '""')
    return f'"{escaped}"'


def normalize_newlines(text: str) -> str:
    return (
        text.replace("\r\n", "\n")
        .replace("\r", "\n")
        .replace("\n", "\r\n")
    )
