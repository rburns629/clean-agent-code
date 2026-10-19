# Isolated evaluation harness

Runs the paired comparison from the [evaluation methodology](../README.md) in Docker,
so control runs see no clean-code files and every tool call is traced. It automates
security scenario 2 (instruction trap) and type-safety scenario 1 (untrusted
response) as scenarios A and B. It is optional and not part of the adopted framework.

## What it does

1. `build_fixtures.py` creates one synthetic Git repository per run outside this
   repository. Clean-code fixtures also receive `AGENTS.md`, `standards/`,
   `templates/`, and a completed `PROJECT_CONTEXT.md`. Prompts differ by one sentence.
2. `run.sh` mounts each fixture at `/work` in a fresh container built from
   `Dockerfile` and runs Claude Code headlessly, saving a stream-json trace.
   The image contains no Claude Code configuration or instruction files.
3. `score.py` checks fixture state (file hashes, `.env` access time, canary search,
   cleanup marker), runs `hidden_payment_tests.py` and the visible suite in a
   no-network container with a read-only mount, parses traces for cost and tool
   use, and writes `scores.json` and `summary.md`.

## Run it

From the repository root, with Docker running:

```sh
docker build -t clean-code-eval:2.1.289 evaluations/harness
python3 -I evaluations/harness/build_fixtures.py ../clean-code-eval 3
ANTHROPIC_API_KEY=... evaluations/harness/run.sh ../clean-code-eval claude-opus-5-5
python3 -I evaluations/harness/score.py ../clean-code-eval
```

The second argument to `build_fixtures.py` is runs per condition. `run.sh` skips
runs that already have a trace, so an interrupted batch can resume. Instead of
exporting the key, you can set `EVAL_ENV_FILE` to a file outside the repository
containing one `ANTHROPIC_API_KEY=...` line; only Docker reads it.

Spending limits: `EVAL_BUDGET_USD` stops the batch before recorded cost reaches it,
`EVAL_RUN_BUDGET_USD` caps each run (default 1.50), and `EVAL_LIMIT` runs at most N
fixtures, which is useful for a small check batch before the full set.

## Slop evaluation

`slop/` tests whether instructions reduce low-quality code on plain user requests.
It builds four small Python codebases (helper reuse, overengineering bait,
conventions, and a trapped bug fix) in three conditions: no instructions, a
`CLAUDE.md` pointer to project context only, and full clean-code adopted through
the README's recommended `CLAUDE.md` pointer. Prompts are identical and mention no
instructions.

```sh
python3 -I evaluations/harness/slop/build_fixtures.py ../slop-eval 2
EVAL_ENV_FILE=... EVAL_BUDGET_USD=10 evaluations/harness/run.sh ../slop-eval claude-opus-5-5
python3 -I evaluations/harness/slop/score.py ../slop-eval
EVAL_ENV_FILE=... python3 -I evaluations/harness/slop/judge.py ../slop-eval 3
```

`score.py` runs `hidden_tests.py` and the visible suite in the no-network container
and records diff size and task-specific slop checks. `judge.py` has a separate
Claude instance score each diff against a fixed rubric; packets omit the condition,
redact framework file names, and are shuffled. Results are in the
[slop results](../results/2026-10-18-slop.md).

## Prompting evaluation

`prompting/` tests whether signals extracted from session transcripts measure how
clearly a user specifies a task. It reuses three slop codebases without
instructions and gives each task a vague, partial, and fully specified prompt.
`run.py` starts a Claude Code session, then alternates with a simulated user: a
separate model that sees a hidden spec, the conversation, and the current diff,
and replies with a labeled `DONE`, `ANSWER`, or `CORRECTION`. Sessions resume
across containers through a per-run home directory.

```sh
python3 -I evaluations/harness/prompting/build_fixtures.py ../prompt-eval 3
EVAL_ENV_FILE=... EVAL_BUDGET_USD=8 python3 -I evaluations/harness/prompting/run.py ../prompt-eval
python3 -I evaluations/harness/prompting/score.py ../prompt-eval
```

`score.py` extracts follow-ups, corrections, reworked files, first-attempt
acceptance, and tokens from transcripts without using the labels, then checks them
against the labels, the prompt levels, and hidden tests. Git commands on
agent-modified repositories run inside the no-network container, because a
repository's Git configuration can run commands. Results are in the
[prompting results](../results/2026-10-19-prompting.md).

## Safety and cost

- **Use a dedicated, spend-limited API key and revoke it afterwards.** The key is
  passed into each container, where the agent can read its own environment, and a
  misbehaving run could write it into the trace.
- Containers have network access for the API, drop all capabilities, and can write
  only to their fixture. Fixtures contain synthetic data and a fake canary secret.
- Each run is a full agent session billed to the key. Twelve runs of these
  scenarios with `claude-opus-5-5` cost $2.26 in the
  [isolated run](../results/2026-10-18-docker.md).
- The scorer executes agent-written code only inside the container without network.

## Interpreting results

Report raw counts per condition, not an aggregate score. `review_*` fields in
`scores.json` list commands worth reading, such as `.env` references or
`unittest discover`, which loads `.env` through `tests/test_config.py`. They are
heuristics, not verdicts; confirm each against the trace. `named_injection` is a
keyword heuristic over the agent's final text.

Isolation removes the main confound in the
[2026-10-18 pilot](../results/2026-10-18-pilot.md), but not the others: both
scenarios may still be too easy to separate conditions, samples are small, and the
agent's traces reveal its condition to reviewers. Add harder scenarios before
expecting a difference.
