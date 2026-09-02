# Separated Parser Semantics Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional action-only semantic profile that binds to named anchors in one syntax grammar and feeds the existing lowering, Parser IR, decision DAG, and Python semantic codegen without changing the legacy combined-grammar path.

**Architecture:** Parse syntax annotations and semantic actions into new immutable sidecar models, then bind them into an ordinary ephemeral `SourceGrammar`. All existing lowering, resolution, analysis, Parser IR optimization, and codegen remain the single implementation after that boundary. Legacy APIs and dataclasses are not routed through the new models.

**Tech Stack:** Python 3.11+, frozen/slotted dataclasses, existing parsergen source grammar/lowering/Parser IR, pytest/unittest, SHA-256 golden checks.

**Spec:** `docs/superpowers/specs/2026-09-02-separated-parser-semantics-design.md`

## Global Constraints

- Existing `parse_grammar`, `parse_source_grammar`, `lower_source_grammar`, `build_parser_ir`, and `generate_python_semantic_parser` signatures remain unchanged.
- Existing `SourceGrammar`, `LoweringResult`, and `ParserIr` fields, equality, and constructors remain unchanged.
- Legacy combined grammar syntax and its diagnostic codes remain unchanged.
- Legacy representative generated `module_text` SHA-256 remains `5aa204ccdaddb8dba6d07da5f861bb1716be03a83d50e5ff8cacdbf44abcf01c`.
- Semantic profile files contain no syntax RHS and expose no numeric item paths.
- Separated semantics bind before lowering and Parser IR construction; no codegen overlay or consumer callback is allowed.
- Syntax annotations preserve all non-annotation offsets by replacing annotations only with equal-length spaces.
- Raw inline actions remain supported only in combined grammar; separated profile v1 is declarative-only.
- No Worker/BSL-specific knowledge enters QueryConsole1C/parsergen.

---

### Task 1: Freeze the legacy compatibility surface

**Files:**
- Create: `tools/parsergen/tests/test_separated_semantics_legacy.py`

**Interfaces:**
- Consumes: current combined-grammar public and internal APIs.
- Produces: an executable compatibility gate that every later task must keep green.

- [ ] **Step 1: Add the representative legacy builder and exact snapshots**

```python
from dataclasses import fields
import hashlib
from inspect import signature

from parsergen.analysis import compute_analysis
from parsergen.grammar_parser import parse_grammar
from parsergen.lowering import LoweringResult
from parsergen.parser_ir import ParserIr, build_parser_ir
from parsergen.python_semantic_codegen import generate_python_semantic_parser
from parsergen.resolver import resolve_grammar
from parsergen.source_model import SourceGrammar


LEGACY_SOURCE = (
    "#Name ::= ID\n"
    "<S> ::= @Assignment Name = #Name '=' Value = &NUMBER "
    "Enabled := Истина"
)


def _legacy_module_text() -> str:
    parsed = parse_grammar(LEGACY_SOURCE, "legacy.grammar")
    assert parsed.diagnostics == ()
    assert parsed.source_grammar is not None
    assert parsed.lowering is not None
    assert parsed.grammar is not None
    resolved = resolve_grammar(parsed.grammar)
    assert resolved.grammar is not None
    analysis = compute_analysis(resolved.grammar, 1, ("S",))
    parser_ir = build_parser_ir(
        parsed.source_grammar,
        parsed.lowering,
        resolved.grammar,
        analysis,
        entrypoint_productions=("S",),
    )
    return generate_python_semantic_parser(
        parsed.source_grammar,
        parser_ir,
        {"start": "S"},
    ).module_text


def test_legacy_dataclass_shapes_and_parse_signature_are_frozen() -> None:
    assert tuple(item.name for item in fields(SourceGrammar)) == (
        "productions", "identifier_definitions", "path"
    )
    assert tuple(item.name for item in fields(LoweringResult)) == (
        "grammar", "constructs", "production_origins", "alternative_origins",
        "diagnostics", "bindings", "left_recursions",
    )
    assert tuple(item.name for item in fields(ParserIr)) == (
        "productions", "matcher_definitions", "lookahead", "source_grammar",
        "entrypoint_productions",
    )
    assert str(signature(parse_grammar)) == (
        "(text: 'str', path: 'str' = '<memory>') -> 'ParseResult'"
    )


def test_legacy_python_semantic_module_text_is_byte_identical() -> None:
    digest = hashlib.sha256(_legacy_module_text().encode("utf-8")).hexdigest()
    assert digest == "5aa204ccdaddb8dba6d07da5f861bb1716be03a83d50e5ff8cacdbf44abcf01c"
```

- [ ] **Step 2: Run the gate against the untouched implementation**

Run: `python -m pytest tools/parsergen/tests/test_separated_semantics_legacy.py -q`

Expected: `2 passed`; this is a characterization test and must be GREEN before feature code.

- [ ] **Step 3: Commit the compatibility gate**

```bash
git add tools/parsergen/tests/test_separated_semantics_legacy.py
git commit -m "test(parsergen): freeze legacy semantic parser contract"
```

### Task 2: Parse syntax grammar labels and anchors

**Files:**
- Create: `tools/parsergen/src/parsergen/separated_model.py`
- Create: `tools/parsergen/src/parsergen/syntax_grammar_parser.py`
- Create: `tools/parsergen/tests/test_syntax_grammar_parser.py`

**Interfaces:**
- Consumes: `parse_source_grammar(text, path) -> SourceParseResult`, `SourceGrammar`, and `SourceSpan`.
- Produces: `SyntaxItemAddress`, `SyntaxAlternativeName`, `SyntaxAnchor`, `SyntaxGrammar`, `SyntaxParseResult`, and `parse_syntax_grammar(text, path)`.

- [ ] **Step 1: Write RED tests for flat anchors, alternative names, and offset preservation**

```python
from parsergen.syntax_grammar_parser import parse_syntax_grammar


def test_parses_named_alternative_and_anchors_without_changing_symbols() -> None:
    source = (
        "#Name ::= ID\n"
        "<S> ::= [simple] target: #Name '=' value: &NUMBER"
    )
    result = parse_syntax_grammar(source, "syntax.grammar")

    assert result.diagnostics == ()
    assert result.grammar is not None
    assert result.grammar.source_sha256 == (
        "395836e0a59e8e91f5101414c411a94156e54baf5c053faeb4e3b9f5dda32688"
    )
    assert [(item.production, item.name) for item in result.grammar.alternatives] == [
        ("S", "simple")
    ]
    assert [item.name for item in result.grammar.anchors] == ["target", "value"]
    production = result.grammar.source_grammar.productions[0]
    assert production.alternatives[0].body.items[0].span.start.offset == source.index("#Name", source.index("<S>"))
    assert production.alternatives[0].body.items[1].span.start.offset == source.index("'='")
```

The literal above is the result of this independent check:

```powershell
@'
import hashlib
s = "#Name ::= ID\n<S> ::= [simple] target: #Name '=' value: &NUMBER"
print(hashlib.sha256(s.encode("utf-8")).hexdigest())
'@ | python -
```

- [ ] **Step 2: Write RED tests for nested groups, EBNF, direct LR, and diagnostics**

```python
def test_addresses_anchors_inside_named_group_alternatives() -> None:
    result = parse_syntax_grammar(
        "<S> ::= [root] head: ITEM ([tail] comma: ',' item: ITEM)*",
        "syntax.grammar",
    )
    assert result.diagnostics == ()
    assert result.grammar is not None
    assert {(a.address.alternative, a.name) for a in result.grammar.anchors} == {
        ("root", "head"), ("tail", "comma"), ("tail", "item")
    }


def test_rejects_duplicate_labels_anchors_and_combined_actions() -> None:
    result = parse_syntax_grammar(
        "<S> ::= [same] value: A value: B | [same] other: B @Node",
        "syntax.grammar",
    )
    assert {item.code for item in result.diagnostics} == {
        "SGP101", "SGP102", "SGP103"
    }
```

- [ ] **Step 3: Run the focused tests and confirm imports fail**

Run: `python -m pytest tools/parsergen/tests/test_syntax_grammar_parser.py -q`

Expected: collection ERROR with `ModuleNotFoundError: parsergen.syntax_grammar_parser`.

- [ ] **Step 4: Implement immutable syntax sidecar models**

```python
@dataclass(frozen=True, slots=True)
class SyntaxItemAddress:
    production: str
    alternative: str | None
    path: tuple[int, ...]


@dataclass(frozen=True, slots=True)
class SyntaxAlternativeName:
    production: str
    name: str
    path: tuple[int, ...]
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class SyntaxAnchor:
    name: str
    address: SyntaxItemAddress
    span: SourceSpan
    target_span: SourceSpan


@dataclass(frozen=True, slots=True)
class SyntaxGrammar:
    source_grammar: SourceGrammar
    alternatives: tuple[SyntaxAlternativeName, ...]
    anchors: tuple[SyntaxAnchor, ...]
    source_sha256: str
    path: str


@dataclass(frozen=True, slots=True)
class SyntaxParseResult:
    grammar: SyntaxGrammar | None
    diagnostics: tuple[Diagnostic, ...]
```

- [ ] **Step 5: Implement annotation masking and structural address resolution**

`parse_syntax_grammar` must:

1. SHA-256 the original `text.encode("utf-8")`.
2. Scan only grammar bodies, respecting comments, quotes, angle brackets, and nested groups.
3. Record `[alternative]` and `anchor:` spans, then replace their non-newline characters with spaces.
4. Call the unchanged `parse_source_grammar(masked, path)`.
5. Traverse `SourceSequence`/`SourceGroup` recursively and match each recorded target start offset to exactly one `SourceItem`, storing its internal tuple path.
6. Emit `SGP101` duplicate alternative, `SGP102` duplicate anchor in one alternative, `SGP103` forbidden constructor/binding/action, and `SGP104` unresolved annotation.
7. Return `grammar=None` whenever any ERROR exists.

Keep scanner helpers private in `syntax_grammar_parser.py`; do not add a dialect flag to the legacy parser in this task.

- [ ] **Step 6: Run syntax parser and legacy gates**

Run: `python -m pytest tools/parsergen/tests/test_syntax_grammar_parser.py tools/parsergen/tests/test_separated_semantics_legacy.py -q`

Expected: all tests PASS and legacy digest remains exact.

- [ ] **Step 7: Commit syntax parsing**

```bash
git add tools/parsergen/src/parsergen/separated_model.py tools/parsergen/src/parsergen/syntax_grammar_parser.py tools/parsergen/tests/test_syntax_grammar_parser.py
git commit -m "feat(parsergen): parse named syntax grammar anchors"
```

### Task 3: Parse action-only semantic profiles

**Files:**
- Modify: `tools/parsergen/src/parsergen/separated_model.py`
- Create: `tools/parsergen/src/parsergen/semantic_profile_parser.py`
- Create: `tools/parsergen/tests/test_semantic_profile_parser.py`

**Interfaces:**
- Consumes: `BindingMode`, `SourceSpan`, and the profile syntax from the spec.
- Produces: `SemanticAnchorBinding`, `SemanticConstantBinding`, `SemanticAlternative`, `SemanticProfile`, `SemanticProfileParseResult`, and `parse_semantic_profile(text, path)`.

- [ ] **Step 1: Write RED tests covering the complete declarative vocabulary**

```python
from parsergen.semantic_profile_parser import parse_semantic_profile
from parsergen.source_model import BindingMode


def test_parses_constructor_anchor_bindings_and_constants() -> None:
    result = parse_semantic_profile(
        """profile worker
<S>[simple] {
    @Assignment
    Name = name
    Items += item
    Children *= children
    Path ~= part
    Count ++= mark
    Child => child
    Decorators +=> decorator
    += root_item
    -= ignored
    Enabled := Истина
    := Неопределено
}
""",
        "worker.semantic",
    )
    assert result.diagnostics == ()
    assert result.profile is not None
    alternative = result.profile.alternatives[0]
    assert alternative.constructor == "Assignment"
    assert [item.mode for item in alternative.anchor_bindings] == [
        BindingMode.SCALAR, BindingMode.APPEND, BindingMode.EXTEND,
        BindingMode.CONCAT, BindingMode.INCREMENT, BindingMode.WRAP,
        BindingMode.WRAP_PREPEND, BindingMode.APPEND, BindingMode.DISCARD,
    ]
    assert [(item.property, item.value) for item in alternative.constants] == [
        ("Enabled", "Истина"), (None, "Неопределено")
    ]
```

- [ ] **Step 2: Add RED diagnostics tests**

Cover `SPP100` missing/duplicate `profile`, `SPP101` malformed selector,
`SPP102` malformed block, `SPP103` duplicate constructor, `SPP104` unsupported
inline action, and `SPP105` malformed binding. Assert exact path, line, column,
and that source literals are absent from diagnostic messages.

- [ ] **Step 3: Run the profile tests and verify RED**

Run: `python -m pytest tools/parsergen/tests/test_semantic_profile_parser.py -q`

Expected: collection ERROR because the new module does not exist.

- [ ] **Step 4: Add the semantic profile models**

```python
@dataclass(frozen=True, slots=True)
class SemanticAnchorBinding:
    property: str | None
    mode: BindingMode
    anchor: str
    span: SourceSpan
    operator_span: SourceSpan


@dataclass(frozen=True, slots=True)
class SemanticConstantBinding:
    property: str | None
    value: str
    span: SourceSpan
    operator_span: SourceSpan


@dataclass(frozen=True, slots=True)
class SemanticAlternative:
    production: str
    alternative: str | None
    constructor: str | None
    constructor_span: SourceSpan | None
    anchor_bindings: tuple[SemanticAnchorBinding, ...]
    constants: tuple[SemanticConstantBinding, ...]
    span: SourceSpan


@dataclass(frozen=True, slots=True)
class SemanticProfile:
    name: str
    alternatives: tuple[SemanticAlternative, ...]
    source_sha256: str
    path: str


@dataclass(frozen=True, slots=True)
class SemanticProfileParseResult:
    profile: SemanticProfile | None
    diagnostics: tuple[Diagnostic, ...]
```

- [ ] **Step 5: Implement the line-oriented profile parser**

Use anchored regular expressions for `profile NAME`, `<Production>[alternative] {`,
`@Constructor`, anchor bindings, constants, and `}`. Preserve exact spans with a
single offset/line cursor. Strip `//` comments only outside identifiers and
constants. Reject any `{` inside a profile block as `SPP104`; never pass profile
text to the combined grammar parser.

- [ ] **Step 6: Run profile, syntax, and legacy tests**

Run: `python -m pytest tools/parsergen/tests/test_semantic_profile_parser.py tools/parsergen/tests/test_syntax_grammar_parser.py tools/parsergen/tests/test_separated_semantics_legacy.py -q`

Expected: all PASS.

- [ ] **Step 7: Commit profile parsing**

```bash
git add tools/parsergen/src/parsergen/separated_model.py tools/parsergen/src/parsergen/semantic_profile_parser.py tools/parsergen/tests/test_semantic_profile_parser.py
git commit -m "feat(parsergen): parse action-only semantic profiles"
```

### Task 4: Bind profiles into ordinary SourceGrammar

**Files:**
- Modify: `tools/parsergen/src/parsergen/separated_model.py`
- Create: `tools/parsergen/src/parsergen/semantic_profile_binding.py`
- Create: `tools/parsergen/tests/test_semantic_profile_binding.py`

**Interfaces:**
- Consumes: `SyntaxGrammar`, `SemanticProfile`, their named scopes, and existing `Source*` model classes.
- Produces: `SemanticBindingResult(source_grammar, diagnostics)` and `bind_semantic_profile(syntax, profile)`.

- [ ] **Step 1: Write the RED happy-path binding test**

```python
from parsergen.semantic_profile_binding import bind_semantic_profile
from parsergen.semantic_profile_parser import parse_semantic_profile
from parsergen.syntax_grammar_parser import parse_syntax_grammar


def test_binds_profile_to_an_ordinary_source_grammar() -> None:
    syntax = parse_syntax_grammar(
        "#Name ::= ID\n<S> ::= [simple] name: #Name '=' value: &NUMBER",
        "syntax.grammar",
    ).grammar
    profile = parse_semantic_profile(
        "profile worker\n<S>[simple] {\n@Assignment\nName = name\nValue = value\nEnabled := Истина\n}",
        "worker.semantic",
    ).profile
    assert syntax is not None and profile is not None

    result = bind_semantic_profile(syntax, profile)

    assert result.diagnostics == ()
    assert result.source_grammar is not None
    rendered_items = result.source_grammar.productions[0].alternatives[0].body.items
    assert type(rendered_items[0]).__name__ == "SourceConstructor"
    assert type(rendered_items[1]).__name__ == "SourceBinding"
    assert type(rendered_items[-1]).__name__ == "SourceConstantBinding"
```

- [ ] **Step 2: Write RED fail-closed cross-file diagnostics**

Add cases for unknown production (`SPB200`), unknown alternative (`SPB201`),
ambiguous unnamed alternative (`SPB202`), missing anchor (`SPB203`), wrong-scope
anchor (`SPB204`), duplicate profile selector (`SPB205`), incompatible reuse
(`SPB206`), and a final existing `validate_bindings` rejection (`SPB207`). For
each case assert the semantic span is primary and the relevant syntax declaration
is a `RelatedLocation`.

- [ ] **Step 3: Run the binder tests and verify RED**

Run: `python -m pytest tools/parsergen/tests/test_semantic_profile_binding.py -q`

Expected: collection ERROR because `semantic_profile_binding` does not exist.

- [ ] **Step 4: Implement immutable tree rewriting**

First add the result model to `separated_model.py`:

```python
@dataclass(frozen=True, slots=True)
class SemanticBindingResult:
    source_grammar: SourceGrammar | None
    diagnostics: tuple[Diagnostic, ...]
```

Implement a private recursive function with this contract:

```python
def _bind_sequence(
    sequence: SourceSequence,
    *,
    production: str,
    alternative_name: str | None,
    path: tuple[int, ...],
    bindings_by_path: Mapping[tuple[int, ...], SemanticAnchorBinding],
) -> SourceSequence:
    """Return a new sequence; never mutate syntax.source_grammar."""
```

For each item path, recursively rebuild `SourceGroup`, `SourceOptional`, and
`SourceRepeat`. When a path is bound, wrap the complete source value in
`SourceBinding`; its inner value retains syntax spans, while wrapper/operator
spans come from the semantic profile. Insert `SourceConstructor` before the first
item and `SourceConstantBinding` after the last item in profile order.

- [ ] **Step 5: Reuse existing semantic validators**

After cross-file resolution, call both `validate_source_grammar(bound)` and
`validate_bindings(bound)`. Convert their errors to `SPB207` diagnostics with
the original diagnostic as a related location; do not duplicate validator logic
inside the binder.

- [ ] **Step 6: Run binder and all preceding tests**

Run: `python -m pytest tools/parsergen/tests/test_semantic_profile_binding.py tools/parsergen/tests/test_semantic_profile_parser.py tools/parsergen/tests/test_syntax_grammar_parser.py tools/parsergen/tests/test_separated_semantics_legacy.py -q`

Expected: all PASS.

- [ ] **Step 7: Commit the binder**

```bash
git add tools/parsergen/src/parsergen/separated_model.py tools/parsergen/src/parsergen/semantic_profile_binding.py tools/parsergen/tests/test_semantic_profile_binding.py
git commit -m "feat(parsergen): bind profiles to named grammar anchors"
```

### Task 5: Prove EBNF, group, and left-recursion semantics

**Files:**
- Modify: `tools/parsergen/tests/test_semantic_profile_binding.py`
- Create: `tools/parsergen/tests/test_separated_semantics_parser_ir.py`
- Modify: `tools/parsergen/src/parsergen/semantic_profile_binding.py`
- Modify: `tools/parsergen/src/parsergen/syntax_grammar_parser.py`

**Interfaces:**
- Consumes: successful `SemanticBindingResult.source_grammar` and the unchanged lowering/resolution/analysis APIs.
- Produces: differential proof that separated semantics participate in existing lowering and Parser IR optimization.

- [ ] **Step 1: Add a normalization helper and combined-vs-separated RED test**

```python
def _semantic_shape(value: object) -> object:
    if isinstance(value, SourceSpan):
        return "<span>"
    if is_dataclass(value):
        return (
            type(value).__name__,
            tuple(
                (field.name, _semantic_shape(getattr(value, field.name)))
                for field in fields(value)
            ),
        )
    if isinstance(value, tuple):
        return tuple(_semantic_shape(item) for item in value)
    if isinstance(value, Mapping):
        return tuple(sorted((key, _semantic_shape(item)) for key, item in value.items()))
    return value
```

Build equivalent grammars containing constructor, scalar, optional, repeat,
append, extend, concat, increment, wrap, wrap-prepend, discard, and constants.
Assert normalized `SourceGrammar`, `LoweringResult`, and `ParserIr` equality.

- [ ] **Step 2: Add group and direct-left-recursion RED cases**

Use a named recursive alternative and named alternatives inside a repeated group.
Assert `LoweredLeftRecursion`, synthetic EBNF productions, `result_index`, and
optimized semantic operations match the equivalent combined grammar.

- [ ] **Step 3: Add the two-profile grammar-invariance test**

Bind two profiles to the same syntax grammar, one full and one compact. Assert
the lowered grammar symbols, resolution, FIRST/FOLLOW/SELECT, and canonical
decision outcomes match before semantic optimization. Assert final IR differences
are confined to semantic operations and semantic-transparency optimization.

- [ ] **Step 4: Run tests and inspect the first real mismatch**

Run: `python -m pytest tools/parsergen/tests/test_semantic_profile_binding.py tools/parsergen/tests/test_separated_semantics_parser_ir.py -xvv`

Expected: RED at the first unsupported nested/path case, not a legacy regression.

- [ ] **Step 5: Complete recursive annotation resolution and binding**

Fix only the failing structural cases. Internal tuple paths may change during
implementation, but semantic files and public diagnostics must continue to use
names only. Do not add special branches to `lowering.py`, `parser_ir.py`, or
`parser_ir_optimization.py` unless a differential test proves a general parsergen
bug; any such change requires a separate focused RED test.

- [ ] **Step 6: Run the focused differential suite GREEN**

Run: `python -m pytest tools/parsergen/tests/test_separated_semantics_parser_ir.py tools/parsergen/tests/test_semantic_profile_binding.py tools/parsergen/tests/test_left_recursion_lowering.py tools/parsergen/tests/test_binding_parser_ir.py tools/parsergen/tests/test_parser_ir_optimization.py -q`

Expected: all PASS.

- [ ] **Step 7: Commit structural semantics support**

```bash
git add tools/parsergen/src/parsergen/syntax_grammar_parser.py tools/parsergen/src/parsergen/semantic_profile_binding.py tools/parsergen/tests/test_semantic_profile_binding.py tools/parsergen/tests/test_separated_semantics_parser_ir.py
git commit -m "test(parsergen): prove separated semantics through Parser IR"
```

### Task 6: Publish additive API and executable codegen equivalence

**Files:**
- Modify: `tools/parsergen/src/parsergen/__init__.py`
- Modify: `tools/parsergen/tests/test_separated_semantics_parser_ir.py`
- Modify: `tools/parsergen/tests/test_separated_semantics_legacy.py`
- Modify: `tools/parsergen/pyproject.toml`
- Modify: `docs/architecture/parser-generator.md`

**Interfaces:**
- Consumes: the three new functions and models from Tasks 2–4.
- Produces: stable public imports, version `0.2.0`, documentation, and generated-parser execution equivalence.

- [ ] **Step 1: Add RED public import and version assertions**

```python
def test_separated_semantics_are_additive_public_api() -> None:
    import parsergen

    assert parsergen.__version__ == "0.2.0"
    assert callable(parsergen.parse_syntax_grammar)
    assert callable(parsergen.parse_semantic_profile)
    assert callable(parsergen.bind_semantic_profile)
    assert parsergen.SyntaxGrammar.__module__ == "parsergen.separated_model"
    assert parsergen.SemanticProfile.__module__ == "parsergen.separated_model"
```

- [ ] **Step 2: Add an executable combined-vs-separated parser test**

Generate both Python modules from equivalent grammars, `exec` them into separate
namespaces, parse identical token tuples, and compare a recursive projection of
AST class name, fields, collections, scalar values, and `SourceSpan`. Also compare
syntax-error position, actual token type, and expected token tuple.

- [ ] **Step 3: Run public/codegen tests and verify version RED**

Run: `python -m pytest tools/parsergen/tests/test_separated_semantics_legacy.py tools/parsergen/tests/test_separated_semantics_parser_ir.py -q`

Expected: only the new public export/version assertions fail.

- [ ] **Step 4: Export only new top-level entrypoints and models**

Update `parsergen.__init__.__all__` with:

```python
"SemanticBindingResult",
"SemanticProfile",
"SemanticProfileParseResult",
"SyntaxGrammar",
"SyntaxParseResult",
"bind_semantic_profile",
"parse_semantic_profile",
"parse_syntax_grammar",
```

Keep all existing exports in their existing order. Do not change the legacy
codegen signature; callers pass `parser_ir.source_grammar` as they do today.

- [ ] **Step 5: Bump package version and document both authoring modes**

Set `version = "0.2.0"` in `tools/parsergen/pyproject.toml` and
`__version__ = "0.2.0"` in `parsergen/__init__.py`. Extend
`docs/architecture/parser-generator.md` with the exact syntax/profile examples,
API pipeline, diagnostics ranges, identity composition, and the explicit ban on
RHS duplication/numeric public paths.

- [ ] **Step 6: Run public, codegen, and legacy gates**

Run: `python -m pytest tools/parsergen/tests/test_separated_semantics_legacy.py tools/parsergen/tests/test_separated_semantics_parser_ir.py tools/parsergen/tests/test_python_semantic_codegen.py -q`

Expected: all PASS; the legacy hash is unchanged.

- [ ] **Step 7: Commit the public feature**

```bash
git add tools/parsergen/src/parsergen/__init__.py tools/parsergen/tests/test_separated_semantics_parser_ir.py tools/parsergen/tests/test_separated_semantics_legacy.py tools/parsergen/pyproject.toml docs/architecture/parser-generator.md
git commit -m "feat(parsergen): publish separated semantic profiles"
```

### Task 7: Run repository and downstream handoff gates

**Files:**
- Modify only if a gate exposes a defect: files already owned by Tasks 2–6.
- Do not modify: `tools/parsergen/grammar/query-language.grammar` or generated production BSL artifacts.

**Interfaces:**
- Consumes: complete parsergen `0.2.0` feature.
- Produces: release evidence and an exact commit/package identity for the Onec Interactive Runtime integration plan.

- [ ] **Step 1: Install the local package with test dependencies**

Run: `python -m pip install -e "tools/parsergen[test]"`

Expected: successful editable installation of `query-console-parsergen==0.2.0`.

- [ ] **Step 2: Run the complete parsergen suite**

Run: `python -m pytest tools/parsergen/tests -q`

Expected: all tests PASS with no new skips or xfails.

- [ ] **Step 3: Compile all parsergen Python sources**

Run: `python -m compileall -q tools/parsergen/src/parsergen`

Expected: exit code 0 and no output.

- [ ] **Step 4: Validate repository grammar and generated artifacts**

Run: `python -m parsergen validate --config parsergen.toml`

Expected: exit code 0.

Run: `python -m parsergen generate --config parsergen.toml --check`

Expected: exit code 0 and production generated artifacts are current.

- [ ] **Step 5: Prove production inputs and artifacts did not change**

Run: `git diff --exit-code -- tools/parsergen/grammar/query-language.grammar QueryConsoleZUP/src/DataProcessors/Парсер`

Expected: exit code 0 and empty output.

- [ ] **Step 6: Run diff hygiene and compatibility gates once more**

Run: `git diff --check`

Expected: exit code 0.

Run: `python -m pytest tools/parsergen/tests/test_separated_semantics_legacy.py -q`

Expected: all tests in the file PASS and the legacy module hash remains exact.

- [ ] **Step 7: Handle a gate failure with its own regression**

When all gates pass, skip this step and do not create an empty commit. When a
gate fails, add one focused regression to the test file owning that behavior and
the minimal fix in the corresponding source file, rerun Steps 2–6, then commit
only those exact paths:

```bash
git add tools/parsergen/src/parsergen/separated_model.py tools/parsergen/src/parsergen/syntax_grammar_parser.py tools/parsergen/src/parsergen/semantic_profile_parser.py tools/parsergen/src/parsergen/semantic_profile_binding.py tools/parsergen/tests/test_syntax_grammar_parser.py tools/parsergen/tests/test_semantic_profile_parser.py tools/parsergen/tests/test_semantic_profile_binding.py tools/parsergen/tests/test_separated_semantics_parser_ir.py
git commit -m "fix(parsergen): close separated semantics regression gates"
```

- [ ] **Step 8: Record the handoff identity without committing generated runtime code**

Run: `git rev-parse HEAD`

Run:

```powershell
@'
from hashlib import sha256
from pathlib import Path

root = Path("tools/parsergen/src")
package = root / "parsergen"
digest = sha256()
for source in sorted(package.rglob("*.py"), key=lambda item: item.as_posix()):
    digest.update(source.relative_to(root).as_posix().encode("utf-8"))
    digest.update(b"\0")
    digest.update(source.read_bytes().replace(b"\r\n", b"\n").replace(b"\r", b"\n"))
    digest.update(b"\0")
print(digest.hexdigest())
'@ | python -
```

Record both outputs in the implementation handoff. The runtime repository will
pin the commit and compute its own package SHA-256 when generating the Worker
parser; this plan does not edit the runtime repository.
