# Python Semantic Parser Target Design

## Goal

Add a separate parsergen backend that turns canonical semantic Parser IR and
decision DAGs into a standalone Python parser returning generated AST classes.
It is the generator-side prerequisite for the 1C Interactive Runtime notebook
binder/lowering, but contains no notebook, runtime-context, worker, RDBG, or MCP
knowledge.

The existing `python_codegen.py` remains the fast syntax-only recognizer. The
semantic backend is a new module rather than a mode flag in the recognizer.
Both targets must ultimately consume the same `build_parser_ir()` result:
syntax codegen projects away semantic operations while semantic codegen
executes them. `build_syntax_parser_ir()` is retained only as a compatibility
bridge until the current syntax-only BSL grammar and benchmark adapter are
migrated; it is not a second long-term IR contract.

## Public boundary

```python
generate_python_semantic_parser(
    source: SourceGrammar,
    parser_ir: ParserIr,
    entrypoints: Mapping[str, str],
) -> GeneratedPythonSemanticParser
```

The caller must supply `build_parser_ir(...)`, not
`build_syntax_parser_ir(...)`. The result contains deterministic standalone
`module_text` and immutable AST schema metadata. The generated module imports
only Python's standard library and expects token objects with `type`, `text`,
`start`, and `end` attributes. It publishes `GeneratedParser`,
`GeneratedParseError`, `SourceSpan`, one class per grammar constructor, and an
`AST_CLASSES` mapping.

## Generated AST model

Each distinct `ConstructNode.constructor` becomes a distinct frozen slotted
dataclass. No node-type string field is generated: Python class identity is the
node type. Constructor and property names remain Unicode and are emitted as
valid Python identifiers after strict validation; invalid or colliding names
fail generation.

Every node has a `span: SourceSpan` covering the consumed input from the start
of its production alternative through the last token consumed by that
alternative. Empty constructs receive a zero-width span at the current input
offset. Grammar source spans remain generator diagnostics only and are never
substituted for input spans.

Fields are inferred from semantic Parser IR operations targeting the active
constructor:

- scalar/constant/wrap fields start as `None`;
- append/extend fields start as mutable lists and freeze to tuples;
- concat fields start as an empty string;
- increment fields start at zero;
- root collection append freezes into the reserved `items` tuple field.

The same constructor/property must have one compatible binding category across
all productions and branches. Existing binding validation remains the primary
grammar diagnostic; the Python backend independently rejects inconsistent IR.
Generated field order is deterministic: first semantic occurrence in source
production/alternative/operation order, with `span` last in the public
constructor signature.

Terminal semantic values follow the canonical BSL backend: terminals and
lexemes yield normalized `token.type`, identifier references yield
`token.text`, and constants use `token.value` when present or `token.text`
otherwise. Symbol nodes returned by nonterminals are passed through unchanged.
Canonical constants map `Истина`/`Ложь`/`Неопределено` to
`True`/`False`/`None`; other dotted constants remain their canonical string.

## Iterative semantic runtime

The generated parser uses one explicit `while tasks:` trampoline. Python call
stack depth must not depend on BSL production recursion, EBNF repetition,
optional nesting, or direct-left-recursion folds. A 5,000-element repeat and a
5,000-link direct right-recursive input remain acceptance gates without
changing `sys.setrecursionlimit()`.

Runtime frames own:

- the selected production/branch operation sequence;
- operation index and produced values;
- the active node builder and input start offset;
- a continuation describing where the result is delivered.

Nested nonterminal calls receive their own builder and return a frozen value to
the parent frame. `Dispatch`, `OptionalBranch`, and `RepeatLoop` select the same
serialized canonical DAG leaves as the syntax target. Bound-value regions use
their explicit `result_index`; no implicit "last temporary" rule is introduced.
`LeftFold`, `WrapValue`, and `WrapOptional` are executed from their explicit IR
contracts and do not reconstruct source grammar semantics.

The parser requires full token consumption and returns the selected entrypoint
value. Syntax-only entrypoints may return `None`; semantic entrypoints with an
ambiguous or missing result are rejected by existing validation/IR construction
or fail generation.

## Source spans and immutability

Builders are private generated-runtime objects. AST instances are created only
when their owning semantic frame completes, after the final input position is
known. Collections are converted to tuples recursively at node finalization;
already frozen child nodes are reused. The generated AST contains no parser,
builder, token stream, or mutable list references.

## Diagnostics and safety

Generation fails on source/IR mismatch, syntax-only semantic IR, unknown
entrypoint, invalid/colliding class or field names, reserved generated names,
incompatible property binding categories, unsupported semantic operation, and
malformed decision references.

Runtime syntax errors retain token position, actual type, and expected types.
Semantic runtime errors identify the generated operation and property but do
not include token text or user values. Generated source is deterministic for
the same Source Grammar, Parser IR, DAGs, and entrypoint mapping.

## Acceptance

Focused grammars must prove constructors, scalar/optional values, constants,
append/extend, concat/increment, grouped dispatch, repeats, wraps, transparent
productions, right recursion, and direct-left-recursion folds. Tests compare
class identity, fields, tuple immutability, exact input spans, syntax errors,
and deterministic module text.

The full parsergen suite must remain green and the syntax-only target output for
the existing BSL grammar must remain byte-identical. This milestone does not
edit the runtime BSL grammar or implement notebook lowering; those are separate
consumer-side changes after the semantic generator is published.

The follow-up grammar migration must make the strict BSL grammar semantically
complete enough for `build_parser_ir()`. After the syntax target consumes that
same IR with semantic operations projected away, the compatibility
`build_syntax_parser_ir()` entry point can be deprecated and then removed.
