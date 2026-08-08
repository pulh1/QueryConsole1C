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
- `КОНС_ОМ_ОбработкаМоделиЗапроса`.
- `КОНС_Обр_БенчмаркПарсера_МО`.

### Permanent benchmark corpus

- `CommonTemplate.КОНС_БенчмаркДанныеУчетаВремени` is a `TextDocument`
  source for the permanent `time_accounting_large` corpus at
  `src/CommonTemplates/КОНС_БенчмаркДанныеУчетаВремени/Template.txt`.
- Imported from
  `C:\work\1C\мои разработки\Теория копмиляторов\Генерация парсеров АКТУАЛЬНОЕ\заппросы\ДанныеУчетаВремени.txt`:
  289542 raw bytes, 5489 lines, 160135 UTF-8/LF-normalized characters,
  raw SHA-256 `43035fda34f0ccb05817d856374beba9e5539a3a99540fef9ba7d70d3656c93e`,
  normalized SHA-256 `5e4a617dd41f8af97434b797bac46c9f8ba3ca1d167db9d81828b6854f1fc9c5`.

### Temporary legacy runtime baseline

The following temporary metadata objects are project-local historical runtime
baseline dependencies:

- `CommonModule.КОНС_СтарыеЭлементыМоделиЗапроса`;
- `КОНС_СтарыйЛексическийАнализатор`;
- `КОНС_СтарыйПарсер`.

The permanent and temporary common-module metadata and BSL sources are stored
under `src/CommonModules/`; the permanent common-template corpus is stored
under `src/CommonTemplates/`; temporary DataProcessor metadata, BSL sources,
and templates are stored under `src/DataProcessors/`. The compatibility row is
required because EDT 2026.1 exports seven internal groups, while the pinned
YAxUnit 25.12 source contains six. All remaining upstream files are unmodified
copies of the pinned release.
