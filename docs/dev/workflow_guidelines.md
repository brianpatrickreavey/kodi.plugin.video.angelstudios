# Workflow Guidelines

A practical guide for commit cadence, safe checkpoints, and lightweight workflows to keep changes recoverable and collaboration smooth.

## Purpose
- Keep history meaningful and revert-friendly.
- Reduce risk during cleanup/refactors and feature work.
- Provide small, verifiable steps that pass tests where possible.

## Commit Cadence
- Atomic commits: one logical change per commit (e.g., import cleanup, constants extraction, fixture docstrings).
- Tests-first: prefer commits that pass `make unittest-with-coverage`; use WIP commits only to checkpoint risky work.
- Frequency:
  - Cleanup/refactors: commit every 30–90 minutes or after each checklist item (Phase 0.1 → 0.2 → 0.3).
  - Feature development: commit at milestones (API contract, UI menu, tests added, integration complete). Squash later if desired.
  - High-risk changes (auth/session, interface boundaries): commit more frequently.

## Commit Practices
- Messages: explain what and why. Prefer Conventional Commits:
  - `feat:` new capability
  - `fix:` bug fix
  - `chore:` maintenance (cleanup, tooling)
  - `refactor:` implementation change without behavior change
  - `docs:` documentation only
- Scope: include a scope when helpful (e.g., `chore(cleanup): remove unused imports (Phase 0.1)`).

## Branching Strategy
- Use focused branches per phase/subtask: `cleanup/phase-0`, `cleanup/phase-1-fixtures`.
- Push early; open a draft PR for visibility and CI.
- Keep `main` clean; rebase/squash before merge.

## WIP, Fixups, and History Shaping
- WIP checkpoints are fine mid-risk:
  - `wip(fixtures): initial refactor scaffolding`
- Use `--fixup` and interactive rebase to clean history before merge:
  - `git commit --fixup <commit>` then `git rebase -i --autosquash`.

## Tags and Milestones
- Tag milestones to anchor bisects/rollbacks:
  - `phase-0-complete`, `phase-1-ready-for-review`.
- Annotated tags with a brief summary.

## PRs and Reviews
- Small PRs map to checklist items; easier to review and revert.
- Include a short risk assessment and validation notes (tests, lint) in the PR description.

## Suggested Commit Sequence (Cleanup Phase 0)
- 0.1 Remove unused imports
  - Commit: `chore(cleanup): remove unused imports (Phase 0.1)`
- 0.2 Remove duplicate test imports
  - Commit: `chore(tests): dedupe MagicMock imports (Phase 0.2)`
- 0.3 Extract cache TTL constants
  - Commit: `refactor(ui): extract cache TTL constants (Phase 0.3)`
- 0.4 Archive research docs
  - Commit: `docs(archive): move research docs to docs/archive (Phase 0.4)`
- 0.5 Verify relative imports (lib)
  - Commit: `chore(imports): enforce relative imports in lib (Phase 0.5)`
- 0.6 Verify KODI-agnostic interface modules
  - Commit: `chore(interface): verify Kodi-agnostic angel_* modules (Phase 0.6)`
- 0.7 Zero-risk lint fixes
  - Commit: `chore(lint): resolve flake8 issues without behavior change (Phase 0.7)`

## Quick Commands

Tested commit (small, atomic):

```bash
make unittest-with-coverage
git add -p
git commit -m "chore(cleanup): remove unused imports (Phase 0.1)"
git push -u origin cleanup/phase-0
```

WIP checkpoint:

```bash
git add -A
git commit -m "wip(fixtures): initial refactor scaffolding"
git push
```

Tag a milestone:

```bash
git tag -a phase-0-complete -m "Phase 0 complete"
git push origin phase-0-complete
```

Squash before merge:

```bash
git rebase -i origin/main
```

## Validation Before Committing
- Run tests: `make unittest-with-coverage`.
- Lint & format: `make lint` or `make format-and-lint` if configured.
- Confirm no behavior changes for Phase 0/low-risk refactors.

## Appendix: Conventional Commits Summary
- `feat`: new feature
- `fix`: bug fix
- `docs`: documentation changes only
- `style`: formatting (non-semantic)
- `refactor`: code change without behavior change
- `perf`: performance improvement
- `test`: add/update tests
- `build`: build system or dependencies
- `ci`: CI configuration
- `chore`: maintenance tasks
- `revert`: revert a previous commit
