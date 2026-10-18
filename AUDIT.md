# Independent engineering audit

Evaluate actual behavior and evidence against the [standards](README.md#document-ownership)
and the consuming project's context. Following instructions is not proof of quality.
Apply [agent access safeguards](AGENTS.md#mandatory-filesystem-safety) throughout.
An audit authorizes observation, not remediation, execution of untrusted code, secret
inspection, or production access.

## Method

1. Define scope, revision or snapshot, languages, critical assets, trust boundaries,
   applicable standards, and known access limitations.
2. Read permitted documentation, representative source and configuration, and CI.
   Trace important success and failure paths across actual module boundaries.
3. Evaluate architecture, security, data contracts, testing, maintenance burden,
   compatibility, migrations, and documented operational/performance requirements.
4. Run only safe, authorized checks after reviewing what commands execute and load.
   Record exact commands, environment, outcomes, and unavailable infrastructure.
5. Separate confirmed defects, suspected risks, and improvements. Seek counterevidence
   and distinguish intentional conventions from demonstrable defects.

## Report

For each finding record location, evidence, violated contract or standard, impact,
reproduction when safe, confidence, and a focused corrective recommendation.
Prioritize by demonstrated impact and likelihood; explain urgency rather than using
arbitrary scores. Do not expose credentials or sensitive payloads in reproductions.
Include strengths, exceptions, coverage gaps, and the limits of sampled inspection.
Report applicable gates as Passed, Failed, Not run, or Not applicable with reasons
as required by [quality gates](standards/QUALITY_GATES.md).

A clean automated scan is not a clean audit. Do not certify uninspected code or
infer production readiness from absent findings. Propose remediation separately;
obtain required path-specific approval before modifying existing files.
