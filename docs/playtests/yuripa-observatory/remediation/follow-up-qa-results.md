# Follow-up QA evidence

Date: 2026-10-26  
QA branch: `review/playtest-followup-evidence`  
Implementation branch under review: `fix/playtest-followup`

This report is maintained in an isolated QA worktree. It records test evidence only; it does not change the implementation worktree or call Discord, Google, Gemini, Docker, or production services.

## Baseline test coverage found

Before adding tests, the three relevant files already contained 50 tests:

- `tests/test_scenario_parser.py` had a hand-written Docs-like fixture asserting a valid check and indirectly exercising a duplicate ID, blank result, invalid skill, unrelated table, and no-check scenario. It did not assert those invalid rows as one named combined export case or model a realistic nested Docs HTML cell structure.
- `tests/test_narration_cog.py` covered one account acting as Keeper and PC (one vote is enough), and repeated `/낭독시작` messages with two eligible account IDs. The repeated-start case checked a single final advance, but did not explicitly assert that the first distinct voter leaves the position unchanged and the second distinct voter triggers it.
- `tests/test_action_cog.py` covered current scene context, passed check rules, use of the registered skill, result branch, error paths, and stale scene movement. Its check rule was hand-built rather than parsed from a Docs export, leaving the parser-to-command handoff untested as one flow.

## Added regression coverage

Three tests were added in the isolated QA branch:

1. `test_parse_google_docs_export_checks_and_skip_incomplete_or_unsafe_rows` uses nested `p`/`span` table cells. It expects one valid check and verifies that a blank ID, duplicate ID, unregistered skill, and short row are ignored.
2. `test_distinct_keeper_and_pc_accounts_both_vote_before_advancing` verifies eligible IDs `{100, 101}`, a two-vote quorum, no database advance after the Keeper's first vote, and one advance after the PC's second vote.
3. `test_google_docs_check_flows_through_action_to_matching_skill_and_story_branch` parses a Docs-shaped HTML source, passes that resulting scenario to `/행동`, and checks exact scene context, parsed rule ID, character skill lookup, deterministic dice stub, and the matching success text.

These are deterministic local unit tests. Discord, Google Docs, Gemini, network calls, and real dice randomness are not invoked. The exact source-to-handler path is covered with provider and database boundaries stubbed.

## Commands and observed results

The default Python 3.14 `pytest` executable could not collect the parser and action tests because its environment lacks `openpyxl`:

```text
pytest -q tests/test_scenario_parser.py tests/test_narration_cog.py tests/test_action_cog.py
2 collection errors: ModuleNotFoundError: No module named 'openpyxl'
```

This is an interpreter/environment mismatch, not a failed assertion. The repo's locked dependency includes `openpyxl==3.1.5`; the existing project test venv is Python 3.12 and contains it. Using that interpreter:

```text
/tmp/coc-bot-local-test-venv/bin/pytest -q tests/test_scenario_parser.py tests/test_narration_cog.py tests/test_action_cog.py
53 passed, 1 warning in 0.53s
```

Full suite on the same baseline implementation revision before integration:

```text
/tmp/coc-bot-local-test-venv/bin/pytest -q
220 passed, 1 warning in 0.93s
```

The one warning is `DeprecationWarning: 'audioop' is deprecated and slated for removal in Python 3.13`, imported by the installed Discord voice module. It did not fail a test.

These baseline results are not final branch verification. After the implementation agent completes, this QA branch must include its final implementation commits and the full suite must run again here. Results from that run belong below.

## Cause findings and unresolved observations

- The new tests demonstrate that the checked parser/action/narration paths currently behave as expected in deterministic local tests. No new product bug was reproduced in these three areas on the baseline branch.
- Prior incident notes report three Discord interaction timeouts on 2026-10-24 and one stale narration-button timeout on 2026-10-26. The deployed revision, process logs, and interaction acknowledgement trace were unavailable. Those records establish symptoms, not a root cause; the cause remains undetermined.
- Prior notes record a Gemini model request returning HTTP 404 for `gemini-2.5-flash`; a retry after changing model ID succeeded. This identifies a model-ID/provider endpoint mismatch for that request. A separate 503 is recorded without provider logs; its underlying cause is unknown.
- Prior notes record a manual `/판정` roll whose callback failed after rolling because `view=None` was passed. That code path was fixed before this follow-up baseline. It is a previously identified application cause, distinct from provider failures.
- In this QA attempt, using the system Python's `pytest` caused collection errors because dependencies were absent. Selecting the repository's existing Python 3.12 venv resolved it. This was tooling setup, not a product failure.
- A Docker replacement previously ended the old container with exit 137 after the 30-second stop window. This QA agent did not inspect or mutate Docker. Exit 137 alone does not identify the blocked shutdown hook or signal handling cause.

## Final implementation verification

Pending the implementation agent's completion and branch synchronization.

| Evidence | Status |
|---|---|
| Implementation branch plan and scope reviewed | Pending |
| Final implementation commit(s) synchronized into this QA worktree | Pending |
| Focused parser/narration/action tests after synchronization | Pending |
| Full test suite after synchronization | Pending |
| Actual Discord two-account vote | Not performed; external services are outside this QA agent's scope |
| Real Google Docs export/provider call | Not performed; external services are outside this QA agent's scope |
| Live Gemini scenario-aware `/행동` run | Not performed; would require external API and Discord |
| Graceful Docker shutdown and volume restart | Not performed by this QA agent |

## Remaining investigation proposals

1. If a Discord timeout recurs, capture the active git revision, process/container logs, bot Gateway reconnects, interaction defer/response timing, and Discord API error category around the same correlation ID. Without those, the earlier timeouts cannot be assigned to the app, Discord Gateway, or host.
2. Before another container replacement, preserve `docker inspect` state and logs, then measure SIGTERM handling and exit timing. A clean health response after restart does not prove graceful shutdown.
3. In the dedicated test server, run two accounts through the same narration control: one vote must leave the saved line unchanged and the second must advance it. The local unit case proves the callback logic in isolation, not Discord delivery or permission behavior.
4. Export a fresh Google Docs fixture and compare its table shape against the checked nested HTML case. This QA did not access Google or prove provider export output.
5. Register a scenario containing one valid check and run `/행동` once on an action that should succeed and once on one that should fail. Capture registered skill, roll, selected story branch, response timing, and sanitized Gemini error details. This QA did not use a Gemini key or make live calls.
