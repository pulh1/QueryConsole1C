# YAxUnit Engine Integration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Добавить в QueryConsoleZUP воспроизводимую копию EDT-проекта YAxUnit 25.12, подготовленную к подключению к текущей базовой конфигурации и запуску через EDT-MCP.

**Architecture:** Только `exts/yaxunit/` из зафиксированного upstream-тега копируется в корневой каталог `yaxunit/` как отдельный EDT-проект без submodule. Upstream-код и метаданные остаются неизменными; локально меняется только связь EDT-проекта с платформой и базовой конфигурацией, а происхождение фиксируется отдельными файлами.

**Tech Stack:** Git, PowerShell 7, 1C:Enterprise 8.3.24, 1C:EDT, EDT-MCP, YAxUnit 25.12.

## Global Constraints

- Источник: `C:\dev\Slills\repositories\yaxunit`.
- Upstream-тег: `25.12`.
- Upstream-коммит: `15f7ae557d17b59bd80daad503efd8a3114690e5`.
- Переносится только upstream-каталог `exts/yaxunit/`, а также корневые `LICENSE` и `COPYRIGHT`.
- Целевой EDT-проект: `yaxunit/`; вложенный `.git` и submodule запрещены.
- `yaxunit/src/` переносится без локальных изменений.
- Единственная адаптация upstream EDT-файлов: две строки `yaxunit/DT-INF/PROJECT.PMF`.
- `Runtime-Version`: `8.3.24`.
- `Base-Project`: `База_разработки_исполняемых_представлений_демо_ЗУП`.
- `configurationExtensionCompatibilityMode` остаётся `8.3.10`.
- Основное расширение `QueryConsoleZUP`, features, существующие skills и Serena memories не изменяются.
- Импорт готового EDT-проекта в workspace и снятие защит YAxUnit остаются явными ручными постусловиями.

---

### Task 1: Vendor the pinned YAxUnit EDT project

**Files:**

- Create: `yaxunit/.project`
- Create: `yaxunit/.settings/**`
- Create: `yaxunit/DT-INF/**`
- Create: `yaxunit/src/**`
- Create: `yaxunit/LICENSE`
- Create: `yaxunit/COPYRIGHT`
- Create: `yaxunit/UPSTREAM.md`

**Interfaces:**

- Consumes: локальный Git-репозиторий YAxUnit и объект тега `25.12`.
- Produces: отдельный EDT-проект `yaxunit` с точной upstream-копией 387 файлов и тремя файлами атрибуции.

- [ ] **Step 1: Verify source revision and destination preconditions**

Run from the QueryConsoleZUP repository root:

```powershell
$sourceRepo = 'C:\dev\Slills\repositories\yaxunit'
$targetRepo = (Resolve-Path '.').Path
$targetProject = Join-Path $targetRepo 'yaxunit'
$expectedSha = '15f7ae557d17b59bd80daad503efd8a3114690e5'
$actualSha = (git -C $sourceRepo rev-parse '25.12^{}').Trim()

if ($actualSha -ne $expectedSha) {
    throw "YAxUnit tag 25.12 resolved to $actualSha, expected $expectedSha"
}
if (Test-Path -LiteralPath $targetProject) {
    throw "Destination already exists: $targetProject"
}
git status --short
```

Expected: SHA matches, `yaxunit/` does not exist, and the worktree is clean.

- [ ] **Step 2: Extract only the approved files from the tag**

Run from the QueryConsoleZUP repository root:

```powershell
$sourceRepo = 'C:\dev\Slills\repositories\yaxunit'
$targetRepo = (Resolve-Path '.').Path
$targetProject = Join-Path $targetRepo 'yaxunit'
$tempRoot = [System.IO.Path]::GetTempPath()
$tempDir = Join-Path $tempRoot ('QueryConsoleZUP-yaxunit-' + [guid]::NewGuid().ToString('N'))
$archive = Join-Path $tempDir 'yaxunit-25.12.zip'
$extractDir = Join-Path $tempDir 'extract'

New-Item -ItemType Directory -Path $extractDir -Force | Out-Null
git -C $sourceRepo archive --format=zip --output=$archive 25.12 exts/yaxunit LICENSE COPYRIGHT
if ($LASTEXITCODE -ne 0) { throw 'git archive failed' }

Expand-Archive -LiteralPath $archive -DestinationPath $extractDir
Copy-Item -LiteralPath (Join-Path $extractDir 'exts/yaxunit') -Destination $targetProject -Recurse
Copy-Item -LiteralPath (Join-Path $extractDir 'LICENSE') -Destination (Join-Path $targetProject 'LICENSE')
Copy-Item -LiteralPath (Join-Path $extractDir 'COPYRIGHT') -Destination (Join-Path $targetProject 'COPYRIGHT')

$resolvedTemp = (Resolve-Path -LiteralPath $tempDir).Path
if (-not $resolvedTemp.StartsWith($tempRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to remove unexpected temporary path: $resolvedTemp"
}
Remove-Item -LiteralPath $resolvedTemp -Recurse -Force
```

Expected: `yaxunit/` contains the EDT project and the two upstream license files; the temporary directory is removed.

- [ ] **Step 3: Record exact upstream provenance**

Create `yaxunit/UPSTREAM.md` with `apply_patch`:

```markdown
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

Files under `src/` are an unmodified copy of the pinned upstream release.
```

- [ ] **Step 4: Verify the initial inventory before adaptation**

Run:

```powershell
$sourceRepo = 'C:\dev\Slills\repositories\yaxunit'
$targetProject = Join-Path (Resolve-Path '.').Path 'yaxunit'
$upstreamFiles = git -C $sourceRepo ls-tree -r --name-only 25.12 exts/yaxunit
$vendoredFiles = Get-ChildItem -LiteralPath $targetProject -Recurse -File

if ($upstreamFiles.Count -ne 387) {
    throw "Unexpected upstream inventory: $($upstreamFiles.Count) files"
}
if ($vendoredFiles.Count -ne 390) {
    throw "Unexpected vendored inventory: $($vendoredFiles.Count) files"
}
if (Test-Path -LiteralPath (Join-Path $targetProject '.git')) {
    throw 'Nested .git directory found'
}
git status --short
```

Expected: 387 upstream files, 390 target files including `LICENSE`, `COPYRIGHT`, and `UPSTREAM.md`, with no nested `.git`.

- [ ] **Step 5: Commit the upstream snapshot**

```powershell
git add -- yaxunit
git commit -m "chore: vendor YAxUnit 25.12"
```

Expected: one commit containing only `yaxunit/**`; at this point `PROJECT.PMF` still matches upstream.

---

### Task 2: Bind YAxUnit to the QueryConsoleZUP EDT environment

**Files:**

- Modify: `yaxunit/DT-INF/PROJECT.PMF`
- Modify: `THIRD_PARTY_NOTICES.md`

**Interfaces:**

- Consumes: upstream EDT project from Task 1 and the existing base project `База_разработки_исполняемых_представлений_демо_ЗУП`.
- Produces: an EDT descriptor ready for the current workspace plus repository-level Apache 2.0 attribution.

- [ ] **Step 1: Verify that the descriptor is still the upstream version**

Run:

```powershell
$pmfPath = 'yaxunit/DT-INF/PROJECT.PMF'
$pmf = Get-Content -LiteralPath $pmfPath -Raw
if ($pmf -notmatch 'Runtime-Version: 8\.3\.10') { throw 'Unexpected Runtime-Version' }
if ($pmf -notmatch 'Base-Project: configuration') { throw 'Unexpected Base-Project' }
```

Expected: both upstream values are present before adaptation.

- [ ] **Step 2: Apply the two approved EDT descriptor changes**

Use `apply_patch`:

```diff
-Runtime-Version: 8.3.10
+Runtime-Version: 8.3.24
-Base-Project: configuration
+Base-Project: База_разработки_исполняемых_представлений_демо_ЗУП
```

Apply this as two replacements so the resulting file is exactly:

```text
Manifest-Version: 1.0
Runtime-Version: 8.3.24
Base-Project: База_разработки_исполняемых_представлений_демо_ЗУП
```

- [ ] **Step 3: Add YAxUnit to the repository notices**

Insert the following section in `THIRD_PARTY_NOTICES.md` before `## MIT-licensed sources`:

```markdown
## Apache-2.0-licensed components

- [`bia-technologies/yaxunit`](https://github.com/bia-technologies/yaxunit),
  release `25.12`, revision
  `15f7ae557d17b59bd80daad503efd8a3114690e5`
  Copyright 2021-2026 BIA-Technologies Limited Liability Company —
  Apache License 2.0.

The vendored EDT project is stored in `yaxunit/`. Its full license and copyright
notice are preserved in `yaxunit/LICENSE` and `yaxunit/COPYRIGHT`; exact
provenance and local adaptations are recorded in `yaxunit/UPSTREAM.md`.
```

- [ ] **Step 4: Verify descriptor and metadata invariants**

Run:

```powershell
Get-Content -LiteralPath 'yaxunit/DT-INF/PROJECT.PMF' -Raw
Select-String -LiteralPath 'yaxunit/.project' -Pattern '<name>yaxunit</name>','V8ExtensionNature'
Select-String -LiteralPath 'yaxunit/src/Configuration/Configuration.mdo' `
    -Pattern '<namePrefix>ЮТ</namePrefix>', `
             '<configurationExtensionCompatibilityMode>8.3.10</configurationExtensionCompatibilityMode>', `
             '<configurationExtensionPurpose>AddOn</configurationExtensionPurpose>'
rg -n 'bia-technologies/yaxunit|15f7ae557d17b59bd80daad503efd8a3114690e5' `
    yaxunit/UPSTREAM.md THIRD_PARTY_NOTICES.md
git diff --check
```

Expected: project name and extension nature remain upstream values; only runtime/base binding changes; notices contain the pinned revision; `git diff --check` reports nothing.

- [ ] **Step 5: Commit the local integration metadata**

```powershell
git add -- yaxunit/DT-INF/PROJECT.PMF THIRD_PARTY_NOTICES.md
git commit -m "build: bind YAxUnit to QueryConsoleZUP EDT project"
```

Expected: one commit with exactly two modified files.

---

### Task 3: Prove snapshot integrity and hand off EDT activation

**Files:**

- Verify: `yaxunit/**`
- Verify: `THIRD_PARTY_NOTICES.md`
- Verify: `docs/superpowers/specs/2026-07-31-yaxunit-engine-integration-design.md`
- Verify: `docs/superpowers/plans/2026-07-31-yaxunit-engine-integration.md`

**Interfaces:**

- Consumes: the vendored and adapted EDT project from Tasks 1–2.
- Produces: hash-level proof that upstream content is intact, a clean Git worktree, and exact manual steps for making YAxUnit visible to EDT-MCP.

- [ ] **Step 1: Recreate a clean upstream comparison tree**

Run from the QueryConsoleZUP repository root:

```powershell
$sourceRepo = 'C:\dev\Slills\repositories\yaxunit'
$tempRoot = [System.IO.Path]::GetTempPath()
$verifyDir = Join-Path $tempRoot ('QueryConsoleZUP-yaxunit-verify-' + [guid]::NewGuid().ToString('N'))
$archive = Join-Path $verifyDir 'yaxunit-25.12.zip'
$extractDir = Join-Path $verifyDir 'extract'

New-Item -ItemType Directory -Path $extractDir -Force | Out-Null
git -C $sourceRepo archive --format=zip --output=$archive 25.12 exts/yaxunit
if ($LASTEXITCODE -ne 0) { throw 'git archive failed' }
Expand-Archive -LiteralPath $archive -DestinationPath $extractDir
```

- [ ] **Step 2: Compare all upstream files except the documented descriptor**

Run in the same PowerShell session:

```powershell
$upstreamRoot = Join-Path $extractDir 'exts/yaxunit'
$targetRoot = Join-Path (Resolve-Path '.').Path 'yaxunit'
$mismatches = @()

Get-ChildItem -LiteralPath $upstreamRoot -Recurse -File | ForEach-Object {
    $relative = [System.IO.Path]::GetRelativePath($upstreamRoot, $_.FullName)
    if ($relative -eq 'DT-INF\PROJECT.PMF') { return }
    $targetFile = Join-Path $targetRoot $relative
    if (-not (Test-Path -LiteralPath $targetFile)) {
        $mismatches += "MISSING $relative"
        return
    }
    $sourceHash = (Get-FileHash -LiteralPath $_.FullName -Algorithm SHA256).Hash
    $targetHash = (Get-FileHash -LiteralPath $targetFile -Algorithm SHA256).Hash
    if ($sourceHash -ne $targetHash) { $mismatches += "CHANGED $relative" }
}

if ($mismatches.Count -gt 0) { throw ($mismatches -join [Environment]::NewLine) }
```

Expected: no missing or changed upstream file outside `PROJECT.PMF`; this includes every BSL, metadata, form, template, picture, and setting file.

- [ ] **Step 3: Verify the descriptor as a deterministic two-line adaptation**

Run:

```powershell
$upstreamPmf = Get-Content -LiteralPath (Join-Path $upstreamRoot 'DT-INF/PROJECT.PMF') -Raw
$expectedPmf = $upstreamPmf.Replace('Runtime-Version: 8.3.10', 'Runtime-Version: 8.3.24').Replace(
    'Base-Project: configuration',
    'Base-Project: База_разработки_исполняемых_представлений_демо_ЗУП'
)
$actualPmf = Get-Content -LiteralPath 'yaxunit/DT-INF/PROJECT.PMF' -Raw
if ($actualPmf -ne $expectedPmf) { throw 'PROJECT.PMF has undocumented differences' }
```

Expected: descriptor matches the exact two approved substitutions.

- [ ] **Step 4: Verify inventory, scope, and repository cleanliness**

Run:

```powershell
$actualRelative = Get-ChildItem -LiteralPath 'yaxunit' -Recurse -File |
    ForEach-Object { [System.IO.Path]::GetRelativePath((Resolve-Path 'yaxunit').Path, $_.FullName) }
$upstreamRelative = Get-ChildItem -LiteralPath $upstreamRoot -Recurse -File |
    ForEach-Object { [System.IO.Path]::GetRelativePath($upstreamRoot, $_.FullName) }
$expectedRelative = @($upstreamRelative) + @('LICENSE', 'COPYRIGHT', 'UPSTREAM.md')
$unexpected = Compare-Object -ReferenceObject $expectedRelative -DifferenceObject $actualRelative

if ($unexpected) { throw ($unexpected | Out-String) }
if (Get-ChildItem -LiteralPath 'yaxunit' -Recurse -Force -Directory -Filter '.git') {
    throw 'Nested .git directory found'
}

git diff --check 0ff2bf4..HEAD -- ':(exclude)yaxunit/**'
git diff --check ff3a1a9..HEAD -- yaxunit
git status --short
git diff --name-only 3eb6352..HEAD
```

Expected: inventory differs from upstream only by the three attribution files; no nested `.git`; worktree is clean; changes since the accepted spec are limited to the plan, `yaxunit/**`, and `THIRD_PARTY_NOTICES.md`.

The snapshot commit itself is excluded from `diff --check` because YAxUnit
25.12 contains pre-existing trailing whitespace. Hash comparison, rather than
rewriting third-party BSL, proves that this background is unchanged.

- [ ] **Step 5: Remove the verified temporary directory safely**

Run:

```powershell
$resolvedVerify = (Resolve-Path -LiteralPath $verifyDir).Path
if (-not $resolvedVerify.StartsWith($tempRoot, [System.StringComparison]::OrdinalIgnoreCase)) {
    throw "Refusing to remove unexpected temporary path: $resolvedVerify"
}
Remove-Item -LiteralPath $resolvedVerify -Recurse -Force
```

- [ ] **Step 6: Perform the one-time manual EDT activation**

In EDT:

1. Import `yaxunit/.project` as an existing project into the current workspace.
2. Confirm that the project is named `yaxunit` and linked to
   `База_разработки_исполняемых_представлений_демо_ЗУП`.
3. Update the development infobase with the dependent extensions.
4. For the installed YAxUnit extension, disable safe mode and protection from
   unsafe actions.

Then run these read-only EDT-MCP checks:

```text
list_projects()
get_project_errors(projectName="yaxunit")
list_configurations(
  projectName="База_разработки_исполняемых_представлений_демо_ЗУП",
  type="client"
)
```

Expected: `yaxunit` is open and ready as `V8ExtensionNature`; the existing
`QueryConsoleZUP Тонкий клиент` launch configuration remains available. Record
the existing EDT diagnostic background separately; do not claim it was caused
by the vendored project without a before/after comparison.

- [ ] **Step 7: Record the test-run command for the next iteration**

After `QueryConsoleZUPTests` contains at least one registered test, use:

```text
run_yaxunit_tests(
  launchConfigurationName="QueryConsoleZUP Тонкий клиент",
  updateBeforeLaunch=true,
  updateScope="all"
)
```

For a single-test debug session, use the same call with `tests` set to
`Module.Method` and `debug=true`, then call `wait_for_break`. Do not treat this
step as executed during engine-only integration.
