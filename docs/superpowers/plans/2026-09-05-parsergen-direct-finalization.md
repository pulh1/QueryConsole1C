# Parsergen Direct Target Finalization Implementation Plan

> **Status:** Superseded by `2026-09-05-parsergen-minimal-multi-target.md`. Commit `a012492` from Task 1 remains required regression evidence; the remaining tasks are replaced by the minimal architecture plan.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Preserve the generated direct Python target, remove projection-only scoped semantics, and close the semantic-equivalence gaps found by the final architecture review.

**Architecture:** Both combined grammars and separated syntax/semantic profiles lower into the existing common `SourceGrammar` and `ParserIr`. `DirectRenderAnalysis` proves which recursive sites can be rendered iteratively, and `python_direct_codegen` renders those sites without a VM or Python recursion. Scoped nearest-owner effects are removed completely; they are no longer required after the hot-reload consumer moved to the full AST.

**Tech Stack:** Python 3.11+, pytest, immutable parser IR, generated Python and BSL artifacts.

**Spec:** `docs/superpowers/specs/2026-09-04-direct-python-semantic-parser-design.md`

## Global Constraints

- The Python parser is generated from the common grammar and `ParserIr`; no handwritten BSL parser and no runtime parser VM.
- Canonical BSL generation remains byte-for-byte compatible.
- Combined grammar compatibility and the separated syntax/semantic-profile API already shipped by PR #78 remain supported.
- Recursive transformations must preserve semantic result flow, field defaults, effect order, source spans, and collection order.
- Lists of at least 1,500 elements must not depend on Python's recursion limit.
- Remove `AppendNearestOwner` and every scoped-owner runtime/IR/DSL path; do not replace the global optimizer barrier with another projection-specific mechanism.
- Parsergen remains domain-neutral: no BSL hot-reload or Worker-specific conditions.

---

### Task 1: Correct direct recursive continuations

**Files:**
- Modify: `tools/parsergen/src/parsergen/direct_render_analysis.py`
- Modify: `tools/parsergen/src/parsergen/python_direct_codegen.py`
- Test: `tools/parsergen/tests/test_direct_render_analysis.py`
- Test: `tools/parsergen/tests/test_python_direct_rendering.py`

**Interfaces:**
- Consumes: existing `RecursiveCallSite`, `ContinuationLayout`, `ResultFlowFact`, and the common `ParserIr`.
- Produces: a direct renderer whose iterative recursion is semantically equivalent to the pre-direct Python target for field defaults, discarded calls, and zero-width suffix operations.

- [ ] **Step 1: Add a failing regression for alternative-field leakage**

  Generate and execute this grammar with the existing `_generate`, `_execute`, and `_shape` helpers:

  ```text
  <S> ::= @Link X = A Rest = <S> | @Link Y = B
  ```

  Parse `A B` and assert that the outer `Link` has `X == "A"`, `Y is None`, and its nested `Rest` has `Y == "B"`. Run only this test and observe the current erroneous outer `Y == "B"`.

- [ ] **Step 2: Preserve the complete constructor state needed by continuation freeze**

  Change continuation layout/rendering so the finish function never reads stale constructor fields from the deepest activation's closure. Restore all fields that freeze reads: carry live values in continuation slots and initialize proven defaults inside the finish. Re-run the leakage regression and the existing continuation tests.

- [ ] **Step 3: Add a failing regression for a discarded direct self-call**

  Generate and execute:

  ```text
  <S> ::= 'a' -= <S> | @End STOP
  ```

  Parse `a STOP` and assert the result is `None`. Observe the current incorrect `End` result before changing production code.

- [ ] **Step 4: Require result-flow preservation for direct safe-tail classification**

  Apply the same result-flow proof already used by nested recursive sites to the direct-site path. A discarded recursive result must not become the production result after iteration. Re-run the new regression and result-flow analysis tests.

- [ ] **Step 5: Add a failing regression for a zero-width suffix after recursion**

  Generate and execute:

  ```text
  <S> ::= @Link Value = ITEM Rest = <S> Kind := Истина | @End STOP
  ```

  Parse 1,500 `ITEM` tokens plus `STOP`; assert no `RecursionError`, exactly 1,500 linked nodes, `Kind is True` on every recursive node, and preserved input order. Observe the current `RecursionError` first.

- [ ] **Step 6: Analyze recursive calls before admissible semantic suffixes**

  Find the recursive call by scanning the alternative rather than requiring `operations[-1]` to be the call. Represent the suffix as continuation work and execute it during unwind, preserving the original order. Do not move effects before the recursive call unless the analyzer proves that transformation safe.

- [ ] **Step 7: Verify and commit Task 1**

  Run:

  ```powershell
  python -m pytest -q tests/test_direct_render_analysis.py tests/test_python_direct_rendering.py
  ```

  Commit only the Task 1 source and tests with message `fix(parsergen): preserve direct continuation semantics`.

---

### Task 2: Remove projection-only scoped append

**Files:**
- Delete: `tools/parsergen/src/parsergen/scoped_append_validation.py`
- Delete: `tools/parsergen/tests/test_scoped_append_backend_fences.py`
- Delete: `tools/parsergen/tests/test_scoped_append_parser_ir.py`
- Delete: `tools/parsergen/tests/test_scoped_append_python_runtime.py`
- Delete: `tools/parsergen/tests/test_scoped_append_validation.py`
- Modify: `tools/parsergen/src/parsergen/source_model.py`
- Modify: `tools/parsergen/src/parsergen/semantic_profile_parser.py`
- Modify: `tools/parsergen/src/parsergen/semantic_profile_binding.py`
- Modify: `tools/parsergen/src/parsergen/binding_validation.py`
- Modify: `tools/parsergen/src/parsergen/source_validation.py`
- Modify: `tools/parsergen/src/parsergen/lowering.py`
- Modify: `tools/parsergen/src/parsergen/parser_ir.py`
- Modify: `tools/parsergen/src/parsergen/parser_ir_optimization.py`
- Modify: `tools/parsergen/src/parsergen/direct_render_analysis.py`
- Modify: `tools/parsergen/src/parsergen/python_direct_codegen.py`
- Modify: `tools/parsergen/src/parsergen/python_semantic_codegen.py`
- Modify: `tools/parsergen/src/parsergen/canonical_bsl_codegen.py`
- Modify: `tools/parsergen/src/parsergen/hybrid_bsl_codegen.py`
- Modify: scoped-only assertions in remaining parsergen tests and architecture/direct-target documentation.

**Interfaces:**
- Consumes: Task 1's corrected direct continuation analysis.
- Produces: the minimal common IR/direct renderer without `SemanticScopedAppend`, `SourceScopedValue`, `AppendNearestOwner`, owner stacks, deferred queues, or a global optimizer barrier.

- [ ] **Step 1: Add a structural regression that names the intended minimal surface**

  Add a test that imports the public source/IR models and asserts ordinary append/assign operations remain available while scoped symbols are absent. Add a source scan assertion that `parser_ir_optimization.py` contains no `AppendNearestOwner` early-return barrier. Run it before production deletion and observe failure.

- [ ] **Step 2: Remove scoped DSL, binding, validation, and IR nodes**

  Remove scoped directives and their model fields from parsing through lowering. Delete scoped validation and the four scoped-only suites. Preserve the separated-profile constructs shipped by master (`parse_semantic_profile`, `bind_semantic_profile`, ordinary semantic actions).

- [ ] **Step 3: Remove scoped runtime rendering and optimizer barriers**

  Remove owner-state layouts, owner stacks, deferred queues, enqueue sequencing, scoped-effect propagation, cleanup paths, and canonical/hybrid scoped fences. Restore normal `optimize_parser_ir()` processing for every grammar. Preserve Task 1 continuation code and all direct-target behavior unrelated to scoped append.

- [ ] **Step 4: Prove scoped complexity is gone and profiles still work**

  Run:

  ```powershell
  rg -n "AppendNearestOwner|SemanticScopedAppend|SourceScopedValue|scoped_append|scoped_owner|owner_stack|deferred_queue" tools/parsergen/src tools/parsergen/tests
  python -m pytest -q tests/test_semantic_profile_parser.py tests/test_semantic_profile_binding.py tests/test_separated_semantics_legacy.py tests/test_parser_ir_optimization.py tests/test_python_direct_rendering.py
  ```

  The `rg` command must have no hits; the tests must pass.

- [ ] **Step 5: Update docs and commit Task 2**

  Remove the obsolete scoped-append design/plan and scoped sections from `docs/architecture/parser-generator.md` and the direct-target documents. Keep the explanation of separated profiles and direct generated code. Commit with message `refactor(parsergen): remove scoped append semantics`.

---

### Task 3: Make compatibility fences exercise the generator

**Files:**
- Modify: `tools/parsergen/tests/test_direct_python_bsl_artifact_fence.py`
- Modify only if needed for a reusable pure generation seam: `tools/parsergen/src/parsergen/cli.py`

**Interfaces:**
- Consumes: canonical/hybrid generation already used by `generate_from_compilation` and `render_artifacts`.
- Produces: a test that hashes freshly generated bytes, not `git show HEAD` bytes.

- [ ] **Step 1: Replace the false-positive raw-byte test and observe RED**

  Build the repository parser configuration with `compile_from_config`, call `generate_from_compilation`, pass it through `render_artifacts`, and hash the returned `ArtifactSet` fields in the same fixed artifact order. Temporarily use an intentionally wrong expected digest for one field and observe the test fail on freshly generated bytes; then restore the frozen baseline digest.

- [ ] **Step 2: Verify canonical BSL compatibility and deterministic generation**

  Assert two independent in-memory generations are byte-identical and equal the frozen pre-direct digests. Keep `git show` out of the test. Run `generate --check` for the repository config and all BSL fence tests.

- [ ] **Step 3: Run the complete parsergen suite and commit Task 3**

  Run:

  ```powershell
  python -m pytest -q
  ```

  Expected baseline is at least `831 passed` with only the Windows symlink privilege skip. Commit with message `test(parsergen): verify freshly generated BSL bytes`.

---

### Task 4: Integrate current master and verify the consumer boundary

**Files:**
- No planned production edits; generated consumer artifacts may change only after an explicit byte diff is reviewed.

**Interfaces:**
- Consumes: Tasks 1–3 and current `origin/master` at `c24db4d332171acf43d5cb83f3233bd9e77cac55` or its fast-forward successor.
- Produces: a mergeable parsergen head, complete parsergen evidence, and an exact statement whether onec-interactive-runtime must regenerate its committed Python parser.

- [ ] **Step 1: Merge current master without rewriting published history**

  Fetch `origin/master`, merge it into the fix branch, and stop on any conflict rather than choosing a side mechanically. Do not rebase or force-push the published PR branch.

- [ ] **Step 2: Run parsergen verification**

  Run the complete parsergen suite, repository `validate`, repository `generate --check`, `git diff --check`, and the fresh BSL-byte fence.

- [ ] **Step 3: Compare the runtime consumer artifact**

  Regenerate the onec-interactive-runtime full semantic Python module into a temporary location using the final parsergen head. Compare bytes and semantic parser identity with the committed runtime artifact. If bytes differ, report the exact diff category and require a separate runtime regeneration/test/benchmark commit; do not silently overwrite the runtime repository from this task.

- [ ] **Step 4: Commit integration evidence if tracked files changed**

  Commit only intentional parsergen changes. Leave temporary artifacts untracked outside the repository and report all verification commands and outputs.
