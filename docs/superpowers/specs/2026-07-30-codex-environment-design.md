# Codex Environment Design

## Goal

Prepare a durable Codex environment for QueryConsoleZUP that reflects the
actual EDT project, guides safe BSL and metadata changes, preserves useful
project context, and keeps local tool artifacts out of Git.

## Confirmed Project Facts

- The repository contains an EDT configuration extension in
  `QueryConsoleZUP/`.
- `QueryConsoleZUP/DT-INF/PROJECT.PMF` and
  `QueryConsoleZUP/src/Configuration/Configuration.mdo` declare compatibility
  with 1C:Enterprise 8.3.24.
- The extension name is `QueryConsole1C`; its metadata prefix is `КОНС_`.
- The core implements a multi-pass query-processing pipeline: lexical
  analysis, parsing, query-model construction, semantic processing, executable
  view processing, and execution or code generation.
- Automated acceptance coverage is stored in `features/` as 187 Vanessa
  Automation scenarios with query files and expected-result artifacts.
- The repository does not define a reproducible command or an EDT launch
  configuration for running those Vanessa Automation scenarios.
- EDT currently reports a substantial pre-existing diagnostics baseline.
  Completion checks must therefore focus on newly introduced problems and
  diagnostics for touched objects instead of claiming that the whole project
  is clean.

## Instruction Architecture

Use a small hierarchy of instruction files. Instructions closer to a changed
file refine the root rules without duplicating them.

### `AGENTS.md`

The root instructions cover:

- Russian as the default communication language;
- concise, evidence-based reporting;
- superpowers as the design, planning, debugging, TDD, and verification
  workflow;
- the repository source map and the distinction between the EDT extension,
  query examples, documentation, and Vanessa Automation scenarios;
- EDT-MCP as the primary source of truth for EDT metadata, forms, module
  structure, applications, and diagnostics;
- Serena as the primary tool for symbolic BSL navigation, reference analysis,
  and durable project memory;
- PowerShell-safe commands and conservative Git behavior;
- read-only inspection before changes;
- final reporting of changed files, checks run, remaining diagnostics, and
  checks that could not be executed.

The file must not claim that a metadata object, API, test command, or launch
configuration exists until it has been inspected.

### `QueryConsoleZUP/AGENTS.md`

The EDT subtree instructions cover:

- extension compatibility 8.3.24, Russian BSL, UTF-8, and prefix `КОНС_`;
- the compiler-like query-processing pipeline and its principal modules;
- preserving public interfaces, module regions, naming, formatting, execution
  contexts, and existing comments;
- EDT-MCP reads before edits;
- EDT-aware operations for metadata, forms, DCS, configuration structure, and
  `.mdo` files;
- targeted BSL edits through EDT-MCP or Serena with reference checks where
  interfaces change;
- validation of touched modules or metadata objects followed by a comparison
  against the existing project diagnostics baseline;
- avoiding broad rewrites or whole-file formatting during focused changes.

### `features/AGENTS.md`

The test subtree instructions cover:

- Vanessa Automation/Gherkin conventions already used by the repository;
- the relationship between feature scenarios, `.q1c` inputs, JSON expected
  results, generated-code expectations, and query-constructor expectations;
- preservation of Russian scenario wording, tab indentation, UTF-8 encoding,
  and existing BOM where present;
- updating all paired artifacts when a query or generated output changes;
- selecting the smallest relevant scenario set;
- explicitly reporting manual test requirements because no repository-local
  runner command is defined.

No further nested instruction files are required now. `QueryExamples/` has
specific file semantics, but its rules are small enough for the root source map
and Serena memories. A nested file should be added later only when that subtree
develops independent workflows or conventions.

## Documentation Layout

The current `docs/` directory contains only README image assets. Move
`docs/img/` to `documentation/img/` and update all six references in
`README.MD`.

Reserve `docs/superpowers/` for superpowers artifacts:

- `docs/superpowers/specs/` for approved designs;
- `docs/superpowers/plans/` for implementation plans.

This separates user-facing project documentation from agent workflow
documents without breaking the superpowers directory convention.

## Serena Configuration and Memory

Track `.serena/project.yml` and `.serena/memories/`. Keep
`.serena/project.local.yml` and `.serena/cache/` local.

Limit the BSL language-server workspace to `QueryConsoleZUP/src`. Repository
text search remains available outside that folder, while symbol indexing stays
focused on actual BSL source.

Create these durable memories:

- `mem:core` — top-level source map, project invariants, and references to the
  focused memories;
- `mem:architecture/query_pipeline` — stable compiler stages, principal
  modules, and responsibility boundaries;
- `mem:tech_stack` — EDT extension type, platform compatibility, language,
  encoding, and test technology;
- `mem:conventions` — BSL, metadata, query-example, and feature conventions
  that are not obvious from a single file;
- `mem:suggested_commands` — only commands that are actually available,
  including PowerShell-safe search and Git inspection; it must state that no
  repository-local Vanessa Automation command is defined;
- `mem:task_completion` — EDT diagnostics, reference checks, paired-artifact
  checks, and honest reporting of tests that were not run.

Memories must stay terse and reference one another through `mem:` links.
Volatile line numbers, current diagnostic counts, and branch-specific work
must not be stored.

## Git Ignore Policy

Create a root `.gitignore` with narrowly scoped sections:

- local agent state: `.serena/cache/`, `.serena/project.local.yml`, `.kilo/`,
  and `.kilocode/`;
- Windows and editor temporary files;
- Eclipse/EDT workspace state such as `.metadata/`, `.recommenders/`, and local
  `*.launch` files;
- generated 1C binaries and database dumps such as `.cf`, `.cfu`, `.cfe`,
  `.epf`, `.erf`, `.dt`, and `.1CD`;
- conventional build output directories at the repository root.

Do not ignore `.project`, the tracked project encoding preferences,
`.serena/project.yml`, Serena memories, `.codex/`, source metadata, query
examples, or test expectations.

## Validation

The implementation is complete when:

1. Git reports the image move as a rename or equivalent add/delete pair and
   all README image links resolve to existing files.
2. Instruction inheritance is unambiguous: root rules apply everywhere, EDT
   rules apply under `QueryConsoleZUP/`, and test rules apply under
   `features/`.
3. No project instruction points to an unavailable integration, invented test
   command, or incompatible platform version.
4. `.gitignore` ignores representative local artifacts while keeping all
   intended project configuration and memories visible to Git.
5. Serena lists all required memories and their `mem:` references are
   consistent; the user can additionally run `serena memories check` from the
   repository root.
6. A repository search confirms that README no longer references `docs/img/`.
7. Git diff contains only the approved Codex-environment, documentation-path,
   and ignore changes.

## Out of Scope

- Changes to BSL behavior or metadata objects.
- Changes from the `metadata-provider` feature implementation.
- Creation of a Vanessa Automation runner or EDT launch configuration.
- Repository-wide formatting or encoding normalization.
- Additional agent hierarchies without a demonstrated subtree-specific need.
