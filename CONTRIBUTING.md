# Contributing

Thanks for caring about agent-skill-manager. The project is intentionally
small (zero runtime deps, stdlib only) and we want to keep it that way —
so before opening a PR please skim this short guide.

## Commit message style

This project uses [Conventional Commits](https://www.conventionalcommits.org/),
enforced via [commitizen](https://commitizen-tools.github.io/commitizen/). The
header form is:

```
<type>(<optional scope>): <short imperative summary>

<optional body - wrap at 72 chars>

<optional footer - e.g. Closes #42>
```

Common types you will see in the git log:

| Type | Use for |
|------|---------|
| `feat` | new user-facing feature |
| `fix` | bug fix |
| `refactor` | code change that neither fixes a bug nor adds a feature |
| `perf` | performance improvement |
| `test` | adding or fixing tests only |
| `docs` | docs / README / CHANGELOG only |
| `chore` | tooling, CI, build, .gitignore, dependencies |
| `style` | formatting-only change (ruff auto-fixes) |

Scopes used so far: `cli`, `sync`, `audit`, `watch`, `sources`. Add a new
scope only if the change touches a self-contained module.

If you have commitizen installed (`pip install commitizen`), use:

```sh
cz commit
```

…which prompts for each field and lints the message before committing.
Without cz, just write the header manually and the `pre-push` hook will
remind you if you forget the type prefix.

## Local development

```sh
# clone + editable install with dev tooling (ruff, mypy, commitizen)
git clone git@github.com:yxdwind/agent-skill-manager.git
cd agent-skill-manager
pip install -e ".[dev]"

# run the full test matrix locally (defaults match CI)
pytest tests -q
ruff check src tests
mypy src
```

`pre-commit` is configured to run the same checks on every commit:

```sh
pip install pre-commit
pre-commit install         # one-time setup
```

## Adding a new product

1. Append a new entry to `PRODUCTS` in `src/config/products.py` with the
   same shape as the existing 15 entries. `macos_path`, `windows_path`,
   and optionally `linux_path` are the only required product-specific
   fields; everything else (notes, settings_file, extra_dirs_*) is
   optional.
2. Run `pytest tests/test_products.py` and
   `pytest tests/test_matrix.py::TestDeclarations` to confirm the new
   entry passes the doc-promised invariants (path uniqueness,
   expected count = 15 → 16, etc.).
3. Bump the `len(PRODUCTS) == 15` assertions in `tests/test_matrix.py`
   to 16. There are several of them; the test failure will list them.
4. Update `docs/product-matrix.md` if the new product needs a row.
5. Update the **SupportedsProducts** section of `README.md` /
   `README.en.md` so the table stays accurate.

## Adding a new audit rule

1. Add the regex tuple to either `PROMPT_PATTERNS` (instruction-level)
   or `CODE_PATTERNS` (script-level) in `src/services/audit.py`.
2. Drop a golden-sample skill under `tests/fixtures/malicious/<your_rule>/`
   containing a `SKILL.md` (or `SKILL.md` + the triggering file) that
   must trip your new rule.
3. Add a row to `EXPECTED_TRIGGERS` in `tests/test_malicious_fixtures.py`
   mapping `<your_rule>` → the minimum severity your finding must have
   (`critical_min=1` / `high_min=1` / etc.).
4. Run `pytest tests/test_malicious_fixtures.py -k your_rule` to verify.

## Pull request checklist

- [ ] `pytest tests -q` is green on your machine
- [ ] `ruff check src tests` is clean (run `ruff check --fix` if unsure)
- [ ] `mypy src` reports `Success: no issues found`
- [ ] New behaviour has a regression test
- [ ] Commit header follows Conventional Commits
- [ ] `CHANGELOG.md` Unreleased section updated if user-visible

## Code style

- Python ≥ 3.10, type hints encouraged (the project ships `from __future__
  import annotations` so PEP 604 unions work everywhere).
- Zero third-party **runtime** deps. Dev tools (`ruff`, `mypy`,
  `commitizen`, `pre-commit`) are opt-in via `pip install -e ".[dev]"`.
- Prefer small, focused functions. The audit's worst offender was a
  143-line `sync_skill`; that has been decomposed, please don't reintroduce
  it.

Thanks again — keep it small, keep it stdlib.