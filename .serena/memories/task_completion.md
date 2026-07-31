# Task completion

- Review `git diff`/`git status`; exclude unrelated user changes.
- BSL edit: syntax-check and inspect EDT diagnostics for each touched module or
  object.
- Metadata edit: use EDT-aware mutation, re-read/revalidate the touched object,
  then compare diagnostics with the pre-existing baseline.
- Public interface edit: find and update all references.
- Query/feature edit: check paired `.feature`, `.q1c`, JSON and text/code
  expectations; run the smallest available Vanessa scenario set.
- If Vanessa execution is unavailable, name the exact scenarios requiring
  manual execution.
- Final response: changed files, checks actually run, remaining errors, and
  unperformed manual checks.
