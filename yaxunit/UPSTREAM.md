# Upstream YAxUnit

- Repository: https://github.com/bia-technologies/yaxunit
- Source directory: `exts/yaxunit/`
- Release tag: `25.12`
- Commit: `15f7ae557d17b59bd80daad503efd8a3114690e5`
- Integrated: 2026-07-31
- License: Apache License 2.0; see `LICENSE` and `COPYRIGHT`.

## Local adaptations

Only `DT-INF/PROJECT.PMF` differs from the upstream release:

- `Runtime-Version` is changed from `8.3.10` to `8.3.24`;
- `Base-Project` is changed from `configuration` to
  `База_разработки_исполняемых_представлений_демо_ЗУП`.

## Project-local test additions

In addition to the `DT-INF/PROJECT.PMF` adaptation above, the upstream files
remain unchanged except for:

- the compatibility registration of the Integration Services internal group
  `fb282519-d103-4dd3-bc12-cb271d631dfc` in
  `src/Configuration/Configuration.mdo`;
- registration of the following project-local common modules in that file:

- `КОНС_ТестовыеФабрикиСлужебный`;
- `КОНС_Обр_ЛексическийАнализатор_МО`;
- `КОНС_Обр_Парсер_МО`.
- `КОНС_Обр_ПарсерЗапросов_МО`.

Their metadata and BSL sources are stored under `src/CommonModules/`. The
compatibility row is required because EDT 2026.1 exports seven internal groups,
while the pinned YAxUnit 25.12 source contains six. All remaining upstream
files are unmodified copies of the pinned release.
