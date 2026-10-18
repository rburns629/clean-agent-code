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

Use clean-code as a set of reviewable repository instructions. There is no package
to install or application service to run. Start with one project and one bounded
engineering task, then adjust the project context based on what you learn.

### 1. Bring the documents into your repository

Download or clone this repository into a separate local directory:

```sh
git clone https://github.com/rburns629/clean-code.git
```

Review the documents before adopting them. The core working set is `AGENTS.md`,
`AUDIT.md`, `standards/`, and `templates/PROJECT_CONTEXT.md`. Record the upstream
commit you adopt so later updates can be reviewed as diffs.

For a new project, place those files at the project root, keeping their relative
layout. For an existing project, compare them with existing instructions first and
merge only the relevant guidance with owner approval. Preserve intentional project
architecture, terminology, and conventions; do not replace existing files wholesale.

Review documentation links as part of integration. The supplied files also reference
this README and other supporting documents. Retain those documents at their expected
paths, or update the references to your project's equivalent documentation. Keep
your project's README focused on your project. The evaluation documents and GitHub
community policies are optional adoption material. This repository's workflow is
specific to its own documentation inventory; use your project's CI for application
checks.

### 2. Describe your project

Use [PROJECT_CONTEXT.md](templates/PROJECT_CONTEXT.md) as the starting point for a
project-specific context file. A convenient location is `templates/PROJECT_CONTEXT.md`
with its placeholders replaced by applicable project facts. If you choose another
location, update its relative links and record that location in your instructions.

For an existing codebase, derive conventions from representative source files,
reference implementations, tests, and established tooling. For a new project, record
the initial choices and their reasons. Include:

- Architecture, domain terms, module ownership, and reference source paths.
- Supported languages, runtimes, deployment targets, and public contracts.
- Authentication, authorization, trust boundaries, and data sensitivity.
- Exact check-only commands for formatting, linting, types, builds, and tests.
- Test prerequisites, performance requirements, and known verification gaps.

Complete relevant fields only. Mark unknowns instead of inventing requirements, and
never include credentials or sensitive values. Resolve conflicts using the priority
order in AGENTS.md; project context cannot silently waive security, data integrity,
authorization, or filesystem safeguards.

### 3. Connect the instructions to your agent

Use your coding agent's supported repository-instruction mechanism to direct it to
AGENTS.md, the completed context, and relevant standards. Arbitrary Markdown files
are not automatically loaded by every agent. Ask the agent to identify the documents
it consulted and the applicable project conventions before beginning a change.

For a first task, adapt this prompt to your repository:

```text
Read AGENTS.md and the completed templates/PROJECT_CONTEXT.md. Consult the
standards relevant to this task and the permitted reference implementations.

Task: [describe the required behavior and acceptance criteria].

You may create: [specific new paths].
You may modify: [specific existing paths].
Other existing-file changes require approval. Do not inspect protected contents.

Preserve established contracts and conventions. Make the smallest coherent
change. Run the applicable safe checks and report each as Passed, Failed,
Not run, or Not applicable, with evidence and reasons for verification gaps.
```

Replace the brackets before use. Approval to modify named files does not grant
access to protected contents or authorize deletions, moves, configuration replacement,
or production operations. Name and approve those operations separately when needed.
If approval is unavailable, the agent should preserve originals and present a
proposal under the filesystem safeguards in AGENTS.md.

### 4. Verify the result

Review the diff for correct behavior, preserved contracts, security boundaries, and
unnecessary complexity. Require the agent to report the actual commands run and
remaining risks using [quality gates](standards/QUALITY_GATES.md). A successful
compile or a statement that instructions were followed is insufficient evidence.

Configure your own CI to run the project's applicable checks and require them in
review. Keep commands and prerequisites in project context current. This repository's
workflow validates its documentation; copying these standards does not install
language-specific checks or enforce them in your project.

## Audit an existing codebase

Use [AUDIT.md](AUDIT.md) for an independent assessment before adopting the framework
broadly or when reviewing a risky area. Start with a bounded scope:

```text
Read AUDIT.md, AGENTS.md, and the completed project context.
Audit [specific modules or feature] against the relevant standards.
Do not modify files or inspect protected contents. Run only safe, authorized checks.
Report findings with locations, evidence, impact, confidence, and focused remedies.
Separate confirmed defects from suspected risks and list verification limitations.
```

Review findings before authorizing remediation. An audit does not authorize file
changes, secret inspection, untrusted script execution, or production access.

## Maintain your adoption

Update project context as architecture, contracts, and tooling change. Review upstream
standards updates before merging them; preserve local decisions and document approved
exceptions with their rationale and review conditions.

To assess whether the framework helps your team, use the small paired-comparison
method in [evaluations](evaluations/README.md). Compare the same bounded tasks with
and without the instructions while keeping technical safeguards constant. Record
failures and review costs as well as successes; do not assume benefits without
measuring outcomes.

## Contribute and operate

See [contributing](.github/CONTRIBUTING.md) and the
[security reporting policy](.github/SECURITY.md). No evaluation results are claimed.
The reporting channel must be configured by the owner before public security intake.
Licensed under the MIT License. See `LICENSE` for the full terms.
