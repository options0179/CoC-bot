# Follow-up QA evidence

Date: 2026-10-26  
QA branch: `review/playtest-followup-evidence`  
Implementation branch under review: `fix/playtest-followup` (`55b5d6b`, `110b88c`, `84ebbc9`, `6113d34`)

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

The implementation branch was subsequently rebased into this QA branch. The final combined results are below.

## Cause findings and unresolved observations

- The new tests demonstrate that the checked parser/action/narration paths currently behave as expected in deterministic local tests. No new product bug was reproduced in these three areas on the baseline branch.
- Prior incident notes report three Discord interaction timeouts on 2026-10-24 and one stale narration-button timeout on 2026-10-26. The deployed revision, process logs, and interaction acknowledgement trace were unavailable. Those records establish symptoms, not a root cause; the cause remains undetermined.
- Prior notes record a Gemini model request returning HTTP 404 for `gemini-2.5-flash`; a retry after changing model ID succeeded. This identifies a model-ID/provider endpoint mismatch for that request. A separate 503 is recorded without provider logs; its underlying cause is unknown.
- Prior notes record a manual `/판정` roll whose callback failed after rolling because `view=None` was passed. That code path was fixed before this follow-up baseline. It is a previously identified application cause, distinct from provider failures.
- In this QA attempt, using the system Python's `pytest` caused collection errors because dependencies were absent. Selecting the repository's existing Python 3.12 venv resolved it. This was tooling setup, not a product failure.
- The parent agent's read-only connected Drive lookup found the native document `유리파 관측소 - 플레이테스트 시나리오`, but its `get_document_tables` result was `tables: []`. No document was edited or shared. This does not prove that the full document has no tables through every export route; it does explain why a live test rule cannot currently be sourced from the table lookup, and it leaves the parser fixture independent from a confirmed real export.
- A Docker replacement previously ended the old container with exit 137 after the 30-second stop window. This QA agent did not inspect or mutate Docker. Exit 137 alone does not identify the blocked shutdown hook or signal handling cause.

## Final implementation verification

Implementation commits synchronized into this isolated QA branch by rebasing the two QA commits onto `fix/playtest-followup`; no implementation files were changed in the QA worktree. An additional parameterized end-to-end fixture case checks both success and failure branches.

Focused verification:

```text
/tmp/coc-bot-local-test-venv/bin/pytest -q tests/test_scenario_parser.py tests/test_narration_cog.py tests/test_action_cog.py tests/test_main.py
65 passed, 1 warning in 0.53s
```

Full suite:

```text
/tmp/coc-bot-local-test-venv/bin/pytest -q
226 passed, 1 warning in 0.85s
```

The one warning remains the Discord dependency's `audioop` deprecation. `git diff --check 5a698c8..fix/playtest-followup` also exited successfully. Source review found no player text, provider exception text, or credentials in the new runtime log fields. Runtime diagnostics record interaction ID, command name, elapsed time, outcome, acknowledgement-at-completion, and exception type; tests check redaction with sentinel inputs. The Gemini 404 message is bounded and analyzer invocation remains one attempt. Shutdown attempts web, database, and Discord cleanup in sequence even if one raises, and exposes only cleanup stage plus exception type.

| Evidence | Status |
|---|---|
| Implementation branch plan and scope reviewed | Complete: `follow-up-plan.md`, including acceptance criteria and explicit historical/live evidence limits |
| Final implementation commit(s) synchronized into this QA worktree | Complete: implementation commits `55b5d6b`, `110b88c`, `84ebbc9`, `6113d34`; QA commits rebased on top |
| Focused parser/narration/action/shutdown tests after synchronization | 65 passed; see command above |
| Full test suite after synchronization | 226 passed; see command above |
| Actual Discord two-account vote | Not performed; external services are outside this QA agent's scope |
| Real Google Docs export/provider call | Not performed. Parent's read-only lookup of `유리파 관측소 - 플레이테스트 시나리오` returned `tables: []`; no doc was changed |
| Live Gemini scenario-aware `/행동` run | Not performed; the connected scenario table lookup is empty and live Discord/Gemini access is outside this QA agent's scope |
| Graceful Docker shutdown and volume restart | Not performed by this QA agent |

## Remaining investigation proposals

1. If a Discord timeout recurs, capture the active git revision, process/container logs, bot Gateway reconnects, interaction defer/response timing, and Discord API error category around the same correlation ID. Without those, the earlier timeouts cannot be assigned to the app, Discord Gateway, or host.
2. Before another container replacement, preserve `docker inspect` state and logs, then measure SIGTERM handling and exit timing. A clean health response after restart does not prove graceful shutdown.
3. In the dedicated test server, run two accounts through the same narration control: one vote must leave the saved line unchanged and the second must advance it. The local unit case proves the callback logic in isolation, not Discord delivery or permission behavior.
4. Export a fresh Google Docs fixture and compare its table shape against the checked nested HTML case. This QA did not access Google or prove provider export output.
5. Register a scenario containing one valid check and run `/행동` once on an action that should succeed and once on one that should fail. Capture registered skill, roll, selected story branch, response timing, and sanitized Gemini error details. This QA did not use a Gemini key or make live calls.

## Implementation review notes

- The follow-up implementation adds per-stage shutdown completion/error logs and continues cleanup after a stage exception. The fake-cleanup regression test proves later cleanup functions are awaited. No Docker stop was run from this QA worktree, so graceful shutdown at runtime and the old exit 137 cause remain unverified.
- Slash-command logs use command names and interaction IDs for correlation and do not include interaction arguments. The tests exercise receipt, successful completion, and error logging with sentinel arguments. The recorded time is total command duration and acknowledgement state at completion; it does not measure exact first-ack latency. It supports diagnosing a future stall after receipt but cannot establish Discord-side delivery for old events.
- Gemini 404 now receives a distinct bounded Korean response and category. The test confirms no retry and no exception content in the response or log. Real model availability is not claimed.
- Compose declares `coc-bot-data` external and the README creates it before a clean-host startup. The implementation report records `docker compose config -q` success and no ownership warning with the existing volume. This QA agent did not start/restart Docker or inspect a container mount; persistence remains supported by prior evidence only.
- The native Drive document lookup returned no tables, so the new nested HTML fixture demonstrates parser behavior without confirming Google's live export serialization.
