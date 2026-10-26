# Prompting results: 2026-10-19

_Written when this project was named clean-code. It is now clean-agent-code._

Tests whether signals extracted from agent session transcripts can measure how
clearly a user specifies a task. Run with the
[prompting harness](../harness/README.md#prompting-evaluation): fresh Docker
containers, no instruction files, and a simulated user, so only the prompt varies.

## Summary

- **The signals track prompt clarity on ambiguous tasks.** As prompts went from
  vague to fully specified, follow-up messages fell from 0.89 to 0.22 per run,
  corrections from 0.78 to 0.11, reworked files from 1.44 to 0.11, and first-attempt
  acceptance rose from 33% to 78%. Tokens per task fell from 127k to 67k.
- **Clear prompts made the interaction cheaper, not the result better.** Every run
  eventually passed all hidden tests, because the simulated user corrected the agent
  until the change was right.
- **Task ambiguity is a confound.** On the two open-ended tasks the signals separated
  prompt levels clearly; on a bug fix whose symptom was evident from the code, even
  the vague prompt succeeded on the first attempt and only token use differed.
- **Agents surface decisions rather than ask questions.** They wrote "I chose X; if
  you'd prefer Y..." even after clear prompts, so counting surfaced decisions did not
  measure prompt quality.
- **The transcript extractor agreed with the simulated user on 13 of 15 follow-ups.**

Session signals are usable as a personal trend of how much clarification a user's
prompts require, reported per task type. They are not a precise score for a single
session.

## Setup

| Item | Value |
| --- | --- |
| Agent | Claude Code 2.1.289, headless, `claude-opus-5-5`, permission mode `auto`, tools Bash/Read/Write/Edit/Glob/Grep |
| Simulated user | `claude-opus-5-5` without tools; sees a hidden spec, the conversation, and the current diff; replies with a labeled `DONE`, `ANSWER`, or `CORRECTION`; at most three follow-ups |
| Runs | 3 tasks × 3 prompt levels × 3 replicates = 27 |
| Prompt levels | **Vague** (a one-line goal), **partial** (names the change), **specific** (the README's task template with acceptance criteria and permitted paths) |
| Scoring | Signals extracted from transcripts without using labels; labels and known prompt levels used afterwards to validate them; hidden behavior tests for final correctness |

| Task | Vague prompt | What a vague prompt leaves open |
| --- | --- | --- |
| T1 Inventory handler | "Can you add a way to change stock levels in the inventory service?" | Function name, payload shape, validation rules |
| T2 SMS notifications | "Users want to get notifications by text message." | Channel selection, fallback, error behavior |
| T4 Amount bug | "Some invoice amounts look slightly off. Can you take a look?" | Little: the float conversion bug is evident from the code |

## Results

### By prompt level (9 runs each)

| Signal | Vague | Partial | Specific | Spearman with specificity |
| --- | --- | --- | --- | --- |
| Follow-up messages | 0.89 | 0.56 | 0.22 | −0.41 |
| Corrections | 0.78 | 0.56 | 0.11 | −0.47 |
| Reworked files | 1.44 | 0.89 | 0.11 | −0.54 |
| First-attempt acceptance | 33% | 44% | 78% | +0.36 |
| Tokens per task | 127k | 99k | 67k | −0.77 |
| Surfaced decisions | 1.33 | 0.56 | 0.78 | −0.25 |
| Hidden tests passed | 100% | 100% | 100% | — |

### By task (3 runs each)

| Task | Level | Follow-ups | Corrections | Reworked files | First-attempt acceptance | Tokens |
| --- | --- | --- | --- | --- | --- | --- |
| T1 | Vague | 1.00 | 1.00 | 2.00 | 0% | 124k |
| T1 | Partial | 0.67 | 0.67 | 0.67 | 33% | 94k |
| T1 | Specific | 0.00 | 0.00 | 0.00 | 100% | 60k |
| T2 | Vague | 1.67 | 1.33 | 2.33 | 0% | 163k |
| T2 | Partial | 1.00 | 1.00 | 2.00 | 0% | 116k |
| T2 | Specific | 0.67 | 0.33 | 0.33 | 33% | 77k |
| T4 | Vague | 0.00 | 0.00 | 0.00 | 100% | 94k |
| T4 | Partial | 0.00 | 0.00 | 0.00 | 100% | 88k |
| T4 | Specific | 0.00 | 0.00 | 0.00 | 100% | 64k |

### Extractor validation

| Simulated-user label | Detected as answer | Detected as correction |
| --- | --- | --- |
| ANSWER | 2 | 2 |
| CORRECTION | 0 | 11 |

Both disagreements were replies that answered the agent's question and also added
a request, which the protocol forced into a single label.

## What the signals mean

| Signal | Keep? | Reason |
| --- | --- | --- |
| Tokens per task | Yes | Strongest correlation; also falls on unambiguous tasks, since clear prompts reduce exploration |
| Reworked files | Yes | Clear separation on open-ended tasks |
| Corrections | Yes | Clear separation; extractor reliable for pure corrections |
| First-attempt acceptance | Yes | Intuitive; coarse with few follow-ups per run |
| Surfaced decisions | No | Agents surface decisions regardless of prompt quality |

Report signals per task type. A user who mostly fixes bugs with evident symptoms
will show few corrections however they prompt, and comparing them with someone
building new features would be misleading.

## Building the extractor

Two findings shaped how transcripts must be read:

- Agents frequently edited files through shell commands (`cat >>`, `sed -i`, small
  Python scripts) rather than the Edit tool, so rework detection must parse commands.
- Clarification appears as surfaced decisions ("Decision for you: I chose...")
  rather than question marks.

## Cost

27 runs cost $5.66 in total, including the 3-run check batch (about $0.21 per run).

## Limitations

- **Simulated user.** More consistent than a person and occasionally inventing
  preferences the spec did not state, such as rejecting a zero delta in one run and
  accepting it in another.
- **Small sample.** Three replicates per task and level; one model; correlations are
  moderate.
- **One author.** The same session wrote all prompts, tasks, and the extractor; the
  prompt levels reflect that author's interpretation.
- **Ceiling on correctness.** Every run ended correct, so the experiment measures
  interaction cost, not whether vague prompts lead to wrong results a real user
  would accept.
- **Real sessions not yet tested.** Applying the extractor to real transcripts
  requires task segmentation and per-user consent, and has not been done.
