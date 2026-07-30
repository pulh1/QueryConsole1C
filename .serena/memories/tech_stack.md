# Tech stack

- 1C:EDT configuration-extension project (`V8ExtensionNature`).
- 1C:Enterprise extension compatibility and EDT runtime manifest: 8.3.24.
- Configuration/extension name: `QueryConsole1C`; EDT project:
  `QueryConsoleZUP`; base project:
  `База_разработки_исполняемых_представлений_демо_ЗУП`.
- Russian BSL; project encoding UTF-8.
- Metadata sources are EDT `.mdo` plus BSL/form files under
  `QueryConsoleZUP/src`.
- Acceptance tests: Vanessa Automation/Gherkin in `features`; query fixtures
  use `.q1c`, JSON, and text expectations.
- No repository-local build tool, package manager, Vanessa runner command, or
  versioned EDT launch configuration is defined; discover external/user EDT
  launch state when needed.
