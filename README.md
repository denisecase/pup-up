# Professional Python Project Companion

> An opinionated guide to professional Python project infrastructure.

A professional Python project includes the
configuration, conventions, automation, documentation, and validation that
allow the project to be developed and maintained reliably.

This repository contains:

- the source for the companion;
- maintained canonical project files;
- the rationale behind the selected infrastructure;
- automated builds for web, EPUB, and PDF editions.
- the PyPi `pup` package for updating infrastructure files

## Guiding Principle

Professional Python projects deserve intentional infrastructure.

The specific tools will evolve. The engineering concerns they address will
remain.

## Canonical Examples

The `canonical/` directory contains annotated examples of the project files
discussed in the companion.

These examples represent one opinionated professional standard.
Readers can fork the repository and adapt examples to
their own requirements.

## Install Tools

1. [Quarto CLI](https://quarto.org/)
2. [VS Code Editor](https://code.visualstudio.com/)
3. [VS Code Editor Quarto Extension](https://marketplace.visualstudio.com/items?itemName=quarto.quarto)
4. [Git](https://git-scm.com/)
5. [uv Python manager](https://docs.astral.sh/uv/)

## Build the Book

```shell
uv sync
quarto render
```

## Outputs

The book can be rendered as:

- an HTML website;
- an EPUB;
- a print-ready PDF.

## Update a Repo based on Templates

```shell
# see what files the command would update (optional, force latest)
uvx pup-up
uvx pup-up@latest

# actually add and overwrite the files listed (CAUTION: DESTRUCTIVE)
uvx pup-up --write
```

## Developer Command Reference

<details>
<summary>Show command reference</summary>

### In a machine terminal

Open a machine terminal where you want the project:

```shell
git clone https://github.com/denisecase/pup-up

cd pup-up
code .
```

### In a VS Code terminal

```shell
uv self update
uv python pin 3.14
uv lock --upgrade
uv sync --extra dev --extra docs

uvx pre-commit install
uvx pre-commit autoupdate

git add -A
uvx pre-commit run --all-files
# repeat if changes were made
uvx pre-commit run --all-files

# repo-specific
uv run pup-up
uv run pup-up --write

# types, tests, docs
uv run python -m pyright
uv run python -m pytest
uv run python -m zensical build

# save progress
git add -A
git commit -m "update"
git push -u origin main
```

</details>

## License

The book text and canonical examples may use different licenses. See
[LICENSE](LICENSE) and the licensing notes in the repository documentation.
