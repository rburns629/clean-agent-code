# clean-code

Practical engineering standards for repository-aware coding agents and their reviewers.
The goal is reliable software within each project's context, with evidence of quality.
Markdown guides decisions; it cannot guarantee security or enforce filesystem isolation.

## Document ownership

- [AGENTS.md](AGENTS.md): agent behavior and mandatory filesystem safeguards.
- [AUDIT.md](AUDIT.md): independent, evidence-based codebase assessment.
- [Architecture](standards/ARCHITECTURE.md): design and dependency decisions.
- [Security](standards/SECURITY.md): secure development and agent risks.
- [Type safety](standards/TYPE_SAFETY.md): reliable data contracts.
- [Testing](standards/TESTING.md): behavioral verification.
- [Quality gates](standards/QUALITY_GATES.md): applicability, evidence, and readiness.
- [Project context](templates/PROJECT_CONTEXT.md): repository-specific extensions.
- [Evaluations](evaluations/README.md): compare outcomes without inventing improvements.

## Adopt in a project

Read the repository's existing instructions and representative code first. Adopt the
high-level agent instructions and relevant standards using the host agent's supported
instruction mechanism; arbitrary Markdown files are not automatically loaded. Keep
relative links valid when copying files. Fill applicable project-context fields with
observed conventions, commands, and owner-approved exceptions. Record where the
completed context lives in the consuming repository's agent instructions.

Resolve conflicts using the priority order in AGENTS.md. Project context cannot
silently waive security, data integrity, authorization, or filesystem safeguards.
Use the project's actual compiler, analyzers, tests, and CI to enforce applicable
gates. Require reviewers to assess decisions tooling cannot verify.

This repository's workflow checks documentation only. It does not enforce standards
in consuming repositories. Configure their CI separately using
[quality gates](standards/QUALITY_GATES.md).

## Contribute and operate

See [contributing](.github/CONTRIBUTING.md) and the
[security reporting policy](.github/SECURITY.md). No evaluation results are claimed.
The reporting channel must be configured by the owner before public security intake.
Licensed under the MIT License. See `LICENSE` for the full terms.
