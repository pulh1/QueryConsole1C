# Python target status

The first Python target milestone generates a standalone syntax recognizer from
the existing canonical Parser IR and decision DAG. It uses an explicit task
stack, so EBNF repetition and direct right recursion do not consume the Python
call stack.

The current generated `GeneratedParser.parse()` validates a token stream and
returns no semantic value. This is intentionally an intermediate spike, not the
completed Python target.

The next milestone must generate the AST model automatically from the grammar's
semantic declarations. Distinct grammar node alternatives should normally
become distinct Python classes; a separate string discriminator such as
`node_type` is not required. The target must then execute semantic Parser IR
operations and return instances of those generated classes, including source
spans needed for source-to-source transformations.
