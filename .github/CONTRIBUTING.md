# Contributing

Read [document ownership](../standards/README.md) and the relevant standard
before proposing a change. Follow [filesystem safeguards](../AGENTS.md#mandatory-filesystem-safety).

Propose a standard with a concrete problem, affected projects, expected behavior,
verification method, maintenance cost, and a simpler alternative considered.
Search the relevant safe documents for an existing requirement before adding one;
link to its owner instead of duplicating detail. Explain compatibility and exceptions.

Report ambiguity with the exact rule, two plausible interpretations, and an example
where they produce different outcomes. Avoid including secrets or private code.
Submit scenarios using the [evaluation methodology](../evaluations/README.md), with
objective checks and human-review criteria. Report unsuccessful outcomes too.

Reviewers should check coherence, security, filesystem safety, practical applicability,
existing conventions, and incentives for overengineering. Separate machine-checkable
rules from judgment. Prefer focused changes with evidence over longer instructions.
Run the documentation workflow's validation logic locally or in CI; review links
and meaning manually. Existing files require explicit path-specific edit approval
under this framework's agent policy. Maintainers should configure required CI checks.
