# Evaluating engineering outcomes

This is a small Markdown methodology, not a benchmark platform. A first
[pilot](results/2026-10-18-pilot.md) measured no difference; an
[isolated run](results/2026-10-18-docker.md) found one prevented safety slip and
one task failure caused by the framework, in three runs per condition. Use synthetic repositories without secrets or production
access. Each run must have an isolated disposable workspace and explicit operation
approvals; do not expose real protected files to test agent restraint.

## Paired comparison

Run the same task on the same initial snapshot with and without clean-code
instructions. Keep model/version, tool permissions, dependencies, task text, time
budget, and environment consistent. Record the exact instructions loaded; avoid
leaking one run's solution into the other. Repeat with independent runs when feasible
and vary order to reduce ordering effects. Record failures and incomplete runs.
Both conditions retain identical technical sandbox controls and baseline access policy.

Capture snapshot identifiers, commands, diffs, gate outcomes, review findings, and
resource/time observations. Check baseline behavior before judging regressions.
Use reviewers unaware of the condition when practical. Report raw counts and sample
size, not unsupported causal or statistical claims. Distinguish an instruction-following
failure from a sandbox preventing the attempted action. Review maintenance cost and
semantic correctness even if objective checks pass.

## Starter scenarios

- [Architecture](architecture/scenarios.md): abstractions, consistency, optimization.
- [Security](security/scenarios.md): validation, authorization, filesystem safety.
- [Type safety](type-safety/scenarios.md): external data and unsafe casts.
- [Maintainability](maintainability/scenarios.md): errors, tests, semantics, style.

Each numbered scenario uses eight fields: initial conditions, task, safe behavior,
quality outcome, failure modes, verification, objective checks, and subjective
review. A run report should reproduce those fields, then add observed behavior, objective outcomes, reviewer rationale,
limitations, and condition identity after blind review. Record criteria as met,
unmet, or unverified; do not combine unlike risks into an arbitrary aggregate score.
New scenarios should demonstrate a distinct risk before expanding the collection.

The optional [isolated harness](harness/README.md) automates two starter scenarios
in Docker with clean control runs and full tool-call traces.
