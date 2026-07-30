# Conventions

- Preserve the edited BSL module's regions, execution directives, formatting,
  and public interfaces; avoid whole-file formatting for focused changes.
- Verify metadata/module/API existence and signatures through EDT-MCP or
  Serena before use.
- Metadata, forms, DCS, configuration structure, and `.mdo` changes are
  EDT-aware operations; revalidate touched objects.
- Query text uses `&Параметр`; never concatenate user values into query text.
- Query examples are UTF-8 `.q1c` XML documents containing query text and
  parameter values; preserve XML escaping and existing BOM.
- Vanessa features use Russian Gherkin and tab indentation. Changes may require
  synchronized `.feature`, `.q1c`, JSON, generated-code, and text expectations.
- Existing EDT diagnostics are not a clean baseline; distinguish pre-existing
  problems from regressions.
