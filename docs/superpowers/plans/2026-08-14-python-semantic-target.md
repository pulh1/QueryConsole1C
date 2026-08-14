# Python Semantic Parser Target Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Generate a standalone iterative Python parser and distinct immutable AST classes from canonical semantic Parser IR/DAGs.

**Architecture:** Keep `python_codegen.py` unchanged as the syntax recognizer. Add `python_semantic_codegen.py`, statically infer an AST schema from semantic IR, serialize all canonical decisions and operations, and emit a small explicit-stack semantic VM plus generated dataclasses.

**Tech Stack:** Python 3.11+, frozen/slotted dataclasses, canonical Parser IR and decision DAG, pytest/unittest.

---

### Task 1: AST schema and generated classes

**Files:**
- Create: `tools/parsergen/src/parsergen/python_semantic_codegen.py`
- Create: `tools/parsergen/tests/test_python_semantic_codegen.py`

- [ ] Write RED tests for distinct constructor classes, inferred scalar/collection/concat/increment fields, deterministic ordering, reserved-name rejection, and source/IR binding.
- [ ] Implement immutable schema extraction and deterministic dataclass emission without a node-type field.
- [ ] Execute generated modules and inspect published `AST_CLASSES`.
- [ ] Run focused tests GREEN and commit.

### Task 2: Iterative core semantic execution

**Files:**
- Modify: `tools/parsergen/src/parsergen/python_semantic_codegen.py`
- Modify: `tools/parsergen/tests/test_python_semantic_codegen.py`

- [ ] Add RED cases for constructors, scalar/constant fields, transparent values, terminal/identifier/constant capture, exact spans, syntax diagnostics, and full-consumption checks.
- [ ] Serialize productions, canonical DAGs, symbols, regions, and binding operations.
- [ ] Implement explicit task/frame execution for production calls, consume, construct, scalar/constant/append/extend/concat/increment, and result delivery.
- [ ] Prove 5,000 direct-right-recursive calls without changing recursion limit.
- [ ] Run focused tests GREEN and commit.

### Task 3: Canonical control flow and complete semantic IR

**Files:**
- Modify: `tools/parsergen/src/parsergen/python_semantic_codegen.py`
- Modify: `tools/parsergen/tests/test_python_semantic_codegen.py`

- [ ] Add grouped RED cases for dispatch, optional present/absent, repeat/plus, bound branch values, wrap/prepend, and direct-left-recursion folds.
- [ ] Implement all canonical semantic operation/value variants using continuations on the same explicit task loop.
- [ ] Prove 5,000 repeat items and a long left fold do not consume Python stack.
- [ ] Add malformed-IR fail-closed mutations and deterministic-source checks.
- [ ] Run focused tests GREEN and commit.

### Task 4: Public integration and regression

**Files:**
- Modify: `tools/parsergen/src/parsergen/__init__.py`
- Modify: `docs/architecture/parser-generator.md`
- Modify: `tools/parsergen/tests/test_python_codegen.py` only for byte-identity regression if needed.

- [ ] Export the semantic target result/function without changing the syntax target API.
- [ ] Document token, AST class, source-span, and semantic-operation contracts.
- [ ] Document one canonical `build_parser_ir()` end state; keep `build_syntax_parser_ir()` only as a compatibility bridge until the strict BSL grammar has complete bindings.
- [ ] Run focused tests, the complete parsergen suite, compileall, and diff-check.
- [ ] Confirm existing generated BSL and Python syntax artifacts are unchanged.
- [ ] Use verification/review skills, push the feature branch, and create a ready (non-draft) PR against `master`.
