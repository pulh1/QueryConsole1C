"""Small grammar inputs shared by parser tests."""

SYMBOL_CASES = (
    ("bare terminal", "<S> ::= WORD", "symbol", "Terminal"),
    ("quoted lexeme", "<S> ::= 'word'", "symbol", "Lexeme"),
    ("constant", "<S> ::= &Number", "symbol", "Constant"),
    ("identifier reference", "<S> ::= #Identifier", "symbol", "IdentifierRef"),
    ("parameterless call", "<S> ::= <A>", "symbol", "NonterminalCall"),
    ("nested arguments", '<S> ::= <A>(Call(1, 2), "a,b")', "symbol", "NonterminalCall"),
    ("escaped BSL quotes", '<S> ::= {Text = "a""b"}', "symbol", "Action"),
    ("empty alternative", "<S> ::= a | ", "diagnostic", "GP007"),
    ("duplicate formal parameters", "<S>(Value, Value) ::= a", "diagnostic", "GR002"),
)


NULLABLE_CASES = (
    ("direct epsilon", "<S> ::= ПУСТО", {"S"}),
    ("action then epsilon", "<S> ::= {x = 1} ПУСТО", {"S"}),
    (
        "transitive nullable chain",
        "<S> ::= <A>\n<A> ::= <B>\n<B> ::= ПУСТО",
        {"S", "A", "B"},
    ),
    ("token blocks nullable", "<S> ::= <A> b\n<A> ::= ПУСТО", {"A"}),
    (
        "all references nullable",
        "<S> ::= <A> <B>\n<A> ::= ПУСТО\n<B> ::= ПУСТО",
        {"S", "A", "B"},
    ),
    ("unproductive self cycle", "<S> ::= <S>", set()),
    (
        "cycle reached from epsilon",
        "<S> ::= <A>\n<A> ::= <S> | ПУСТО",
        {"S", "A"},
    ),
    (
        "duplicate nullable dependency",
        "<S> ::= <A> <A>\n<A> ::= ПУСТО",
        {"S", "A"},
    ),
    (
        "nullable alternative beside token alternative",
        "<S> ::= a | <A>\n<A> ::= ПУСТО",
        {"S", "A"},
    ),
)


FIRST_CASES = (
    ("single token", "<S> ::= a", 1, "S", {("a",)}),
    ("single reference", "<S> ::= <A>\n<A> ::= a", 1, "S", {("a",)}),
    ("alternatives", "<S> ::= a | b", 1, "S", {("a",), ("b",)}),
    (
        "nullable prefix",
        "<S> ::= <A> b\n<A> ::= ПУСТО",
        2,
        "S",
        {("b",)},
    ),
    (
        "two nullable prefixes",
        "<S> ::= <A> <B> c\n<A> ::= ПУСТО\n<B> ::= ПУСТО",
        2,
        "S",
        {("c",)},
    ),
    (
        "nullable production",
        "<S> ::= <A> <B>\n<A> ::= ПУСТО\n<B> ::= ПУСТО",
        2,
        "S",
        {()},
    ),
    ("truncates token sequence", "<S> ::= a b c", 2, "S", {("a", "b")}),
    (
        "recursive prefixes",
        "<S> ::= a <S> | b",
        2,
        "S",
        {("a", "a"), ("a", "b"), ("b",)},
    ),
    (
        "identifier token class",
        "#ID_X ::= ID | ГДЕ\n<S> ::= #ID_X",
        1,
        "S",
        {("ID",), ("ГДЕ",)},
    ),
    (
        "left recursive prefixes",
        "<S> ::= <S> a | b",
        2,
        "S",
        {("b",), ("b", "a")},
    ),
    (
        "unproductive mutual recursion",
        "<S> ::= <A>\n<A> ::= <S>",
        3,
        "S",
        set(),
    ),
)


FOLLOW_CASES = (
    ("start follows end", "<S> ::= <A>\n<A> ::= a", 1, "S", {("$",)}),
    ("reference inherits end", "<S> ::= <A>\n<A> ::= a", 1, "A", {("$",)}),
    ("terminal suffix", "<S> ::= <A> b\n<A> ::= a", 1, "A", {("b",)}),
    (
        "terminal suffix plus end",
        "<S> ::= <A> b\n<A> ::= a",
        2,
        "A",
        {("b", "$")},
    ),
    (
        "nullable suffix",
        "<S> ::= <A> <B> c\n<A> ::= a\n<B> ::= ПУСТО",
        2,
        "A",
        {("c", "$")},
    ),
    (
        "repeated occurrence",
        "<S> ::= <A> <A>\n<A> ::= a | ПУСТО",
        1,
        "A",
        {("a",), ("$",)},
    ),
    (
        "recursive occurrence",
        "<S> ::= <A>\n<A> ::= a <A> | ПУСТО",
        2,
        "A",
        {("$",)},
    ),
)


CONFLICT_DEPTH_CASES = (
    ("one shared token", "<S> ::= a b | a c", 1, 2),
    ("two shared tokens", "<S> ::= a b c | a b d", 2, 3),
)


VALIDATION_CASES = (
    ("empty grammar", "", {"Разобрать": "S"}, 2, ("VAL100", "VAL101")),
    (
        "unknown nonterminal",
        "<S> ::= <Missing>",
        {"Разобрать": "S"},
        2,
        ("RES001",),
    ),
    (
        "unknown identifier class",
        "<S> ::= #Missing",
        {"Разобрать": "S"},
        2,
        ("RES002",),
    ),
    (
        "empty identifier class",
        "#ID_X ::= \n<S> ::= a",
        {"Разобрать": "S"},
        2,
        ("RES003",),
    ),
    (
        "incompatible repeated headers",
        "<S>(X) ::= a\n<S>(Y) ::= b",
        {"Разобрать": "S"},
        2,
        ("GR001",),
    ),
    (
        "duplicate formal parameter",
        "<S>(X, X) ::= a",
        {"Разобрать": "S"},
        2,
        ("GR002",),
    ),
    (
        "too many call arguments",
        "<S> ::= <A>(1, 2)\n<A>(X) ::= a",
        {"Разобрать": "S"},
        2,
        ("GR003",),
    ),
    (
        "invalid epsilon mix",
        "<S> ::= ПУСТО a",
        {"Разобрать": "S"},
        2,
        ("GR004",),
    ),
    (
        "nonproductive dependency on self cycle",
        "<S> ::= <A>\n<A> ::= <A>",
        {"Разобрать": "S"},
        2,
        ("VAL200", "VAL202"),
    ),
    (
        "nullable zero-consumption cycle",
        "<S> ::= <A>\n<A> ::= <B>\n<B> ::= <A> | ПУСТО",
        {"Разобрать": "S"},
        2,
        ("VAL201", "VAL202"),
    ),
    (
        "valid right recursion",
        "<S> ::= a <S> | ПУСТО",
        {"Разобрать": "S"},
        2,
        (),
    ),
    (
        "valid consuming indirect recursion",
        "<S> ::= <A> | b\n<A> ::= a <S>",
        {"Разобрать": "S"},
        2,
        (),
    ),
    (
        "unreachable production",
        "<S> ::= a\n<Unused> ::= b",
        {"Разобрать": "S"},
        2,
        ("VAL102",),
    ),
    (
        "unused identifier definition",
        "#ID_Unused ::= ID\n<S> ::= a",
        {"Разобрать": "S"},
        2,
        ("VAL103",),
    ),
)
