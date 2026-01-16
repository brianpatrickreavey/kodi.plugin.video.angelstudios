# Agents Directory

This directory stores durable, versioned plans and decision records to prevent loss of context between sessions and ensure reproducible workflows.

## Structure
- `plans/`: Long-form technical plans (architecture, refactors, rollout steps) with tracking sections for decisions and considerations.

## Workflow
- Plans are created on explicit request and reflect agreed, ask-first changes.
- Each plan includes:
  - **Plan**: Verbatim agreed execution steps.
  - **Decisions & Considerations**: Ongoing choices, trade-offs, and open items.
- Updates follow project conventions: small, focused edits; tests-first; no production changes without approval.

## Maintenance
- Plans are living documents; update after major decisions or milestones.
- Link plan items to related code paths and tests when implemented.
- Record cache TTLs, failure handling, and migration notes where relevant.

## Conventions
- Filenames use underscores (e.g., `angel_data_retrieval_and_caching_refactor_plan.md`).
- Keep sections concise; prefer bullets over prose for quick scanning.

## Current Plans
- See: `plans/angel_data_retrieval_and_caching_refactor_plan.md`

## Next
- Add new plan docs here as directives are approved.
