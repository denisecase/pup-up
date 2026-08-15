#Requires -Version 7.0

<#
============================================================
situp.ps1 (PUP-PACK REPOS)
============================================================
Updated: 2026-08-15 (uses pyproject.toml [dependency-groups]; uv sync installs dev and docs groups by default)

Situate project dependencies, lint, test, and build docs.
For Python tooling repos only.

Run with:
.\situp.ps1
#>

Set-StrictMode -Version Latest
$ErrorActionPreference = "Stop"

# ============================================================
# Precheck: pyproject.toml must use [dependency-groups], not the
# old [project.optional-dependencies]. With the old table, `uv sync`
# succeeds but does NOT install dev/docs, and later steps fail confusingly.
# ============================================================
if (Test-Path "pyproject.toml") {
    $pyproject = Get-Content "pyproject.toml" -Raw
    if ($pyproject -match '(?m)^\[project\.optional-dependencies\]') {
        Write-Host ""
        Write-Host "ERROR: pyproject.toml uses the old [project.optional-dependencies] table." -ForegroundColor Red
        Write-Host ""
        Write-Host "This repo has not been migrated. 'uv sync' would run but NOT install" -ForegroundColor Yellow
        Write-Host "the dev and docs dependencies, so linting, tests, and docs would fail." -ForegroundColor Yellow
        Write-Host ""
        Write-Host "FIX: open pyproject.toml and rename this one line:" -ForegroundColor Cyan
        Write-Host "    [project.optional-dependencies]   ->   [dependency-groups]" -ForegroundColor Cyan
        Write-Host ""
        Write-Host "Then run .\sit.ps1 again." -ForegroundColor Cyan
        Write-Host ""
        exit 1
    }
}
$dirty = git status --porcelain
if ($dirty) {
    Write-Host "ERROR: working tree is not clean. Commit or stash first." -ForegroundColor Red
    git status --short
    exit 1
}

function Invoke-Step {
    param([scriptblock]$Cmd)
    & $Cmd
    if ($LASTEXITCODE -ne 0) {
        Write-Host "FAILED (exit $LASTEXITCODE): $Cmd" -ForegroundColor Red
        exit $LASTEXITCODE
    }
}

Invoke-Step { uvx pup-clean@latest --delete }
Invoke-Step { uvx pup-up@latest --write }

# pup-up may write CRLF files on Windows; normalize to match .gitattributes
# BEFORE committing so pre-commit's LF hook doesn't rewrite them post-commit
git add --renormalize .

Invoke-Step { uv python install }
Invoke-Step { uv lock --upgrade }
Invoke-Step { uv sync }

Invoke-Step { uv run pre-commit install }
Invoke-Step { uv run pre-commit autoupdate }

# first pass may auto-fix and exit non-zero (normal); stage, then require clean
git add -A
uv run pre-commit run --all-files
git add -A
Invoke-Step { uv run pre-commit run --all-files }

Invoke-Step { uv run ruff format . }
uv run ruff check . --fix

Invoke-Step { uv run ty check }
Invoke-Step { uv run python -m pytest }
Invoke-Step { uv run python -m zensical build }

git add -A
if (git diff --cached --quiet) {
    Write-Host "No changes to commit." -ForegroundColor Yellow
} else {
    Invoke-Step { git commit -m "situp.ps1: update pup-pack scaffolding and dependencies" }
}

Write-Host "All commands executed successfully." -ForegroundColor Green
Write-Host "If you are happy with the changes, push them." -ForegroundColor Green
