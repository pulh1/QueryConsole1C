# Runtime baseline старых lexer и parser

## Provenance

- lexer_json_sha256: `1a8927bd6203ad4f8636a2249e1388fe09bd169f068f9744d45b273c72884f6d`
- parser_json_sha256: `709cae8deda9df266d19675508f9ad364729d34cb86589012574bdf5fe166d6c`
- source_ref: `origin/old_parser`
- source_commit: `59d538fd974c723c6b1cf336c61b0fea1aec8453`

## Lexer

| corpus | input_count | input_length | operation_count_per_iteration | median_ms | p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| query_examples_all_42 | 42 | 67253 | 42 | 465 | 521 |
| large_package | 1 | 8170 | 1 | 51 | 76 |
| long_field_list | 1 | 3190 | 1 | 34 | 55 |
| join_chain | 1 | 2962 | 1 | 24 | 28 |
| union_package_chain | 1 | 3081 | 1 | 19.75 | 25.5 |
| arithmetic_chain | 1 | 1089 | 1 | 18.5 | 32.5 |
| logical_chain | 1 | 1221 | 1 | 22 | 37.5 |
| dereference_chain | 1 | 854 | 1 | 17 | 24 |
| time_accounting_large | 1 | 160135 | 1 | 1218.5 | 1419 |

## Parser

| corpus | input_count | input_length | operation_count_per_iteration | median_ms | p95_ms |
| --- | ---: | ---: | ---: | ---: | ---: |
| query_examples_all_42 | 42 | 67253 | 42 | 1276 | 1456 |
| large_package | 1 | 8170 | 1 | 118 | 181 |
| long_field_list | 1 | 3190 | 1 | 115.5 | 145 |
| join_chain | 1 | 2962 | 1 | 82 | 111 |
| union_package_chain | 1 | 3081 | 1 | 82.5 | 103 |
| arithmetic_chain | 1 | 1089 | 1 | 53 | 83 |
| logical_chain | 1 | 1221 | 1 | 82 | 105 |
| dereference_chain | 1 | 854 | 1 | 22.25 | 34.5 |
| time_accounting_large | 1 | 160135 | 1 | 3333 | 3759 |
