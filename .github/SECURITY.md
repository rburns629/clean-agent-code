# Security reporting policy

Report vulnerabilities privately through
[GitHub private vulnerability reporting](https://github.com/rburns629/clean-agent-code/security/advisories/new).
Private vulnerability reporting is enabled for this repository. Reports are reviewed
by the repository owner and authorized maintainers through GitHub's private workflow.

Include the affected revision, impact, safe reproduction steps, and suggested
mitigation. Use synthetic examples and redact secrets. Do not post exploit details,
credentials, or sensitive logs in public issues. Do not access others' data, disrupt
services, or run production exploits to prove a report.

If private reporting is unavailable, do not fall back to public disclosure of details.
A public request to restore the reporting channel should contain no vulnerability
details. Never use this repository's reporting URL for a different project's private
reports; consuming projects must configure their own channel.

Coordinate disclosure and remediation with maintainers. No response-time guarantee,
fixed disclosure deadline, supported-version commitment, or testing authorization
is implied. Include your affected revision so maintainers can determine scope.
Engineering guidance lives in [the security standard](../standards/SECURITY.md);
this file owns reporting policy.
