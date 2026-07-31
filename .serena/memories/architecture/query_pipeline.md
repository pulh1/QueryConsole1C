# Query processing pipeline

1. `DataProcessors/ЛексическийАнализатор` converts query text to tokens.
2. `DataProcessors/Парсер` performs table-driven parsing and builds the syntax
   representation.
3. `DataProcessors/ПостроительМоделиЗапроса` builds and edits the query model.
4. `CommonModules/ОбработкаМоделиЗапроса` performs semantic traversal and
   calculated-property processing.
5. `CommonModules/ОбработкаПредставлениеЗапросов` recognizes executable-view
   sources and prepares their model.
6. `CommonModules/ИсполнительПредставлений` executes the package or generates
   executable BSL/DCS query text; it may delegate filters/projections or
   materialize temporary tables.

- Model value constructors/utilities live in `МодельЗапроса*` and
  `ЭлементыМодели*` common modules.
- Executable-view descriptions/providers are discovered through provider and
  registry modules; inspect current definitions before extending the
  interface.
- UI entry points are `КонсольЗапросов` and `КонструкторЗапросов`.
