# Suggested commands (PowerShell)

Repository inspection:

`git -c safe.directory="$((Resolve-Path '.').Path -replace '\\','/')" status --short --branch`

Fast file listing/search:

`rg --files`

`$pattern = 'literal-or-regex'; rg -n --glob '!**/.git/**' $pattern`

README documentation-link check:

`Select-String -LiteralPath 'README.MD' -Pattern 'documentation/img/' -AllMatches`

The repository defines no command for running Vanessa Automation and no EDT
launch configuration. Discover the user's external Vanessa setup instead of
inventing a command. Use EDT-MCP for project/module diagnostics.
