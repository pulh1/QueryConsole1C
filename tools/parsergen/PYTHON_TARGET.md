# Python target

`generate_python_semantic_parser(source, parser_ir, entrypoints)` is the one
production Python target. It accepts the common combined-grammar `ParserIr`
after semantic optimization and produces deterministic standalone Python
source plus immutable AST schema metadata.

Production formal parameters and nonterminal call arguments are unsupported by
the Python target. At the public generation boundary, any such declaration or
call anywhere in `SourceGrammar` (including nested or unreachable code) raises
`ValueError("Python target does not support production parameters or nonterminal call arguments")`
before AST schema discovery and rendering. Argument expressions are opaque BSL
text; Python does not evaluate them. The combined frontend, common IR and BSL
target retain their parameter/argument support.

The generated module publishes `GeneratedParser`, `GeneratedParseError`,
`SourceSpan`, generated frozen/slotted AST classes and `AST_CLASSES`. It imports
only the Python standard library; it does not import parsergen or interpret a
serialized operation table. Constructors define AST node identity, while
declarative bindings determine deterministic scalar, collection, concat,
increment and constant fields. Spans describe input tokens, not grammar source
coordinates.

AST constructor names may reuse Python built-in and dataclasses names. The
renderer gives its dependencies distinct internal aliases and resolves
constructors in the module namespace, so generated locals cannot shadow them.
Repeated identifier declarations form one deterministic union of token types.
For BSL, production formals must not shadow generated locals, template module
state, generated functions or the constructor-provider module; conflicting
names are rejected before rendering. Other BSL parameters and call expressions
remain supported.

The direct renderer uses ordinary production methods, locals, `if` and `while`.
It consumes the common immutable `RecursionPlan` for exact eligible direct
recursive call sites. A simple tail site becomes a production-local loop; a
value-carrying site uses only the local continuation storage prescribed by the
plan. Recursive eligibility, input-progress proof and result-flow analysis are
not reimplemented in this renderer.

There is no Python VM target, syntax-only target, separated semantic profile,
owner stack, scoped append or projection mode. Combined grammar with
declarative semantics is the only authoring format shared with canonical BSL;
the Python capability restriction above applies to that shared input model.

The package version is `0.3.0`. See the binding architecture and cross-target
fences in
[`2026-09-05-parsergen-minimal-multi-target-design.md`](../../docs/superpowers/specs/2026-09-05-parsergen-minimal-multi-target-design.md).
