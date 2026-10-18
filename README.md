# clean-code

Practical engineering standards for repository-aware coding agents and their reviewers.
The goal is reliable software within each project's context, with evidence of quality.
Markdown guides decisions; it cannot guarantee security or enforce filesystem isolation.

## Document ownership

- [AGENTS.md](AGENTS.md): agent behavior and mandatory filesystem safeguards.
- [AUDIT.md](AUDIT.md): independent, evidence-based codebase assessment.
- [Architecture](standards/ARCHITECTURE.md): design and dependency decisions.
- [Security](standards/SECURITY.md): secure development and agent risks.
- [CLI operations](standards/CLI_OPERATIONS.md): cloud, infrastructure, and Git/GitHub safety.
- [Type safety](standards/TYPE_SAFETY.md): reliable data contracts.
- [Testing](standards/TESTING.md): behavioral verification.
- [Quality gates](standards/QUALITY_GATES.md): applicability, evidence, and readiness.
- [Project context](templates/PROJECT_CONTEXT.md): repository-specific extensions.
- [Evaluations](evaluations/README.md): compare outcomes without inventing improvements.

## Adopt in a project

Use clean-code as a set of reviewable repository instructions. There is no package
to install or application service to run. Start with one project and one bounded
engineering task, then adjust the project context based on what you learn.
The standards provide shared principles; project context defines how your languages,
frameworks, and tools implement and verify them.

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

### 3. Map principles to your languages and tools

Use the following examples to decide what belongs in project context. They are
interpretations of the shared standards, not mandatory tool installations or separate
rulesets for every language.

| Stack | Apply the principles | Record and verify |
| --- | --- | --- |
| TypeScript | Use accurate domain types, strict checking, and validation of untrusted input. | Existing compiler configuration, type-check command, lint/format checks, and behavioral tests. |
| Python | Use meaningful annotations and boundary validation without repetitive runtime checks inside trusted code. | Configured static analyzer, supported runtime, lint/format checks, and test commands. |
| Go | Handle errors explicitly and introduce small consumer-scoped interfaces where useful. | Build/static-analysis commands, behavioral tests, and concurrency checks when shared-state behavior is affected. |
| Rust | Preserve ownership and lifetime safety; justify cloning and review unsafe boundaries. | Build, lint/format checks, tests, and any unsafe-code invariants requiring review. |
| Java | Model domain contracts with generics, consistent nullability, and established error handling. | Existing build tool, compiler/static-analysis configuration, and unit/integration tests. |
| Terraform and cloud CLIs | Verify identities, targets, protected inputs, plans, and recovery before authorized changes. | Account/project/subscription and region, backend/workspace, safe validation/preview commands, and separate apply/deployment approval. |
| Git and GitHub | Preserve existing work and distinguish local changes from remote publication. | Repository/branch targets, permitted operations, review requirements, and push/merge/release approval scope. |

Use the tools and conventions already established in the repository. Record exact
commands from reviewed configuration and CI rather than guessing them. Include their
working directories, prerequisites, expected outcomes, and any writes or protected
inputs they require. An existing command is not automatically safe to execute.

For a repository with several languages, identify each component's language, owner,
reference files, and applicable commands separately. Include tests for contracts
between components, such as a frontend calling a backend API. A passing frontend
type check does not prove the backend validates requests or enforces authorization.

Link to the relevant standards instead of copying their detailed requirements into
project context. Start with the project's current needs; optional language/tool
extensions can be introduced later if repeated use demonstrates a concrete gap.

### 4. Connect the instructions to your agent

Use your coding agent's supported repository-instruction mechanism to direct it to
AGENTS.md, the completed context, and relevant standards. Arbitrary Markdown files
are not automatically loaded by every agent. Ask the agent to identify the documents
it consulted and the applicable project conventions before beginning a change.

For recurring work, merge a short pointer like this into the repository instructions
your agent actually reads, adjusting paths to match your adoption:

```text
Follow AGENTS.md and the applicable standards under standards/.
Read templates/PROJECT_CONTEXT.md before making changes.
Use its component-specific conventions, reference files, and verification commands.
Apply standards/CLI_OPERATIONS.md when using infrastructure or repository CLIs.
Preserve existing contracts and report the checks actually performed and their results.
```

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

### 5. Verify the result and enforce checks in CI

Review the diff for correct behavior, preserved contracts, security boundaries, and
unnecessary complexity. Require the agent to report the actual commands run and
remaining risks using [quality gates](standards/QUALITY_GATES.md). A successful
compile or a statement that instructions were followed is insufficient evidence.

Configure your own CI to run the project's applicable checks and require them in
review. Keep commands and prerequisites in project context current. This repository's
workflow validates its documentation; copying these standards does not install
language-specific checks or enforce them in your project.

Map the context's required commands to CI jobs for each affected component, and make
failures block the relevant review/merge path. Record conditional checks for changes
to APIs, databases, authorization, concurrency, or infrastructure. Use human review
for architecture and domain semantics that tools cannot assess. If a required check
cannot run, report the reason and remaining risk rather than treating it as passed.

### Auto-mode backups and cleanup

When auto mode is explicitly enabled, agents must verify a recovery backup before
an authorized operation renames, moves, deletes, or overwrites existing files.
Configure a safe backup location and recovery procedure in project context. If no
safe backup can be made, the agent must preserve originals and present a proposal.
Auto mode and backups do not waive path-specific operation approvals.

At handoff, the agent reports retained backups and asks whether you want to keep
them or review cleanup when ready. Nothing is automatically expired or deleted.
Cleanup requires your explicit approval of the exact artifacts to remove. See the
[backup procedure](standards/SECURITY.md#auto-mode-backups-and-cleanup) for verification,
protected-data handling, recovery, and cleanup safeguards. These instructions guide
agent behavior; adopting them does not install a backup tool.

### Use cloud and repository CLIs safely

Before asking an agent to use AWS, Azure, GCP, Terraform, or Git/GitHub, record the
approved identities, environments, resource/repository targets, and permitted
operations in project context. The [CLI policy](standards/CLI_OPERATIONS.md) separates
metadata reads from sensitive reads, local writes, and remote changes. Authorize
production access, deployments, permission changes, publication, and deletion
explicitly; a coding task or auto mode does not implicitly approve these actions.

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
