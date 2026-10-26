# Playtest reliability follow-up plan

This plan addresses only issues still actionable from `reproduction-and-root-causes.md`. The Oct 24 Discord production instance and its logs are unavailable, so this work will improve evidence for a recurrence but will not claim to identify that historical cause. Live Discord access and provider credentials are not assumed; local behavior is the acceptance target where possible.

## Work ownership and evidence layout

All work lives in this follow-up branch. Keep the historical incident report unchanged. This plan records scope and acceptance evidence; automated test results and local runtime commands belong in the final implementation notes/commit message. Do not save tokens, prompt text, player actions, Discord usernames, or message content in evidence.

| Work area | Owner | Files | Commit boundary |
|---|---|---|---|
| Shutdown lifecycle | Implementer | `bot/main.py`, `tests/test_main.py` | `fix: close bot resources reliably on shutdown` |
| Interaction diagnostics | Implementer | `bot/main.py`, `tests/test_main.py` | `ops: record slash-command acknowledgement timing` |
| Model error classification | Implementer | `bot/cogs/action.py`, `tests/test_action_cog.py` | `fix: explain unavailable Gemini model` |
| Local volume setup | Implementer | `compose.yaml`, `README.md` | `ops: declare SQLite volume as external` |
| Verification record | Implementer/reviewer | this plan and commit evidence | appended to plan before final commit |
| Scenario parser and `/행동` fixture coverage | QA owner | `scenario_parser.py`, its parser tests, `bot/cogs/action.py`, its action tests; use a fresh fixture | QA commit/result, never overwrite existing Google Doc or Discord scene position |
| Two-account narration quorum | QA owner | narration view tests and isolated Discord test channel | unit result; live result only if a second test identity is available |

## Prioritized implementation and acceptance plan

### 1. Make shutdown observable and finish every cleanup step

**Problem/evidence:** Local Docker replacement waited 30 seconds and ended with exit 137. On the follow-up image, repeated Docker stops also reached exit 137 without entering `CoCBot.close()`: the blocking `bot.run()` path had no application SIGTERM handler that routed termination through async cleanup. This explains the local reproduction; the old container logs and Oct 24 deployed revision are still unavailable. An exception in an earlier cleanup could also skip later cleanup.

**Change:** Run `bot.start()` in the app event loop, cancel it on SIGTERM, and always call `CoCBot.close()` in `finally`. Log entry, completion, elapsed milliseconds, and sanitized failure for each shutdown stage. Attempt Discord, web, and SQLite cleanup even if one stage raises, then raise a sanitized stage/type error so the process retains a non-zero failure signal. Do not include environment values or database contents.

**Acceptance evidence:** Unit tests prove SIGTERM cancels the running bot task and reaches cleanup, and that a failing cleanup stage does not prevent later stages. Docker stop on the rebuilt local image exited 0 in under one second with web, database, and Discord cleanup logs. The prior 137 reproduction is explained by missing SIGTERM routing in the old blocking entry point; Oct 24's separate cause still cannot be retroactively established without that deployment's logs/revision.

### 2. Add content-free slash-command timing

**Problem/evidence:** Three Oct 24 interactions timed out, but no process/revision/interaction logs were available. Logs must distinguish “Discord delivered the interaction” from “the command completed and acknowledged it.”

**Change:** Log command receipt and completion/error using interaction ID, command name, total command duration, whether the response is acknowledged at completion, and outcome. Never log command arguments, user text, user identity, token, or exception message from the provider.

**Acceptance evidence:** Unit tests assert a received event stores the start time and that both completion/error records carry the correlation ID, command duration, and acknowledgement-at-completion flag. No test/log record contains a sentinel command argument. This does not measure when the initial `send_message`/`defer` happened, so it cannot prove the three-second acknowledgement latency directly; it distinguishes receipt from later completion/error, and a receipt without either record indicates execution stalled after receipt. A live Discord run is supplementary and requires an available test account/bot.

### 3. Classify Gemini model-not-found separately

**Problem/evidence:** A Gemini 404 for `gemini-2.5-flash` appeared to the user as a generic command error. The configured model was changed afterward; no credential or provider call is required to test classification.

**Change:** Map HTTP 404 to a bounded `model_not_found` category and actionable Korean response that tells the administrator to check the configured model/API availability. Keep one provider attempt and do not log exception text, prompt, or key.

**Acceptance evidence:** Unit tests prove 404 gets its own response, 401/403, 429, 5xx, timeout and malformed response remain bounded categories, and analyzer is called once (no application retry).

### 4. Remove the existing Docker named-volume warning

**Problem/evidence:** Compose reused `coc-bot-data` but warned that it was created outside Compose.

**Change:** Declare the named volume as external with the fixed name `coc-bot-data`; document creating it once on a clean Docker host. Existing volume contents remain in place. No `down -v`, volume deletion, or data migration.

**Acceptance evidence:** `docker compose config -q` succeeds with an existing volume and emits no ownership warning; `docker compose up` mounts the existing named volume. README clean-host steps create the volume before startup. If Docker is unavailable, syntax/config evidence is insufficient to claim runtime volume preservation.

### 5. Reconfirm scenario parsing and action selection with an isolated fixture

**Problem/evidence:** The existing Google Doc `유리파 관측소 - 플레이테스트 시나리오` contains no `Checks` table (`get_document_tables` returned an empty list). The previously completed Discord scenario is at its ending. Reusing either would not test automatic registered-rule selection and could alter the existing play record.

**Change/owner:** QA owner uses a fresh representative Docs HTML fixture containing one valid rule, one duplicate ID, one blank row, and one unregistered skill; verify parser inclusion/rejection. Then use the parsed fixture in `/행동` tests for a valid rule, registered PC skill, success branch, failure branch, and invalid/ambiguous fallback. The implementer must keep the source parsing/action coverage green and avoid editing the existing native Doc or resetting Discord storage.

**Acceptance evidence:** QA test output names the new tests and demonstrates each case. Live Discord `/행동` is a separate optional check that requires a newly registered test scenario with a `Checks` table and an available test account; if that cannot be staged without touching existing state, record the exact blocker.

### 6. Reconfirm narration quorum with two distinct users

**Problem/evidence:** Existing live play used one account for Keeper and PC, so it did not prove that a second eligible user is required.

**Change/owner:** QA owner verifies the isolated view test has distinct Keeper and PC IDs, duplicate vote rejection, one-vote no-advance, and quorum advance. If a second Discord test identity is available, perform the same sequence in a fresh channel; do not touch the completed channel.

**Acceptance evidence:** Unit test output is required. Live evidence is recorded only if the second identity can be used; otherwise report that specific access limit.

## Verification matrix

| Requirement | Automated/local evidence | Live/host-dependent evidence |
|---|---|---|
| Cleanup continues after a failure | SIGTERM handler and failing-cleanup unit tests | Docker SIGTERM stop under 1 second, exit 0; logs show all three cleanup stages |
| Interaction is diagnosable without content | tests of receive/completion/error logs and redaction | recurrence needed to diagnose Discord-side delivery/latency |
| 404 is distinct, bounded, no retry | tests with fake provider exception | real provider model availability is not asserted |
| External named-volume config is warning-free | Compose config passed without warning | replacement container mounted `coc-bot-data:/app/data`; SQLite integrity was `ok`, and both scenario rows/positions matched the pre-restart snapshot |
| Docs parser and action mapping | tests over isolated HTML/check fixtures and mocked provider output | fresh live Google export and Discord run only if safely staged |
| Two-account narration quorum | unit tests with distinct users | second Discord account required for live proof |
| Historical Oct 24 root cause | not verifiable from retained artifacts | requires old process revision/logs, which were unavailable |

## Implementation evidence

| Item | Current result |
|---|---|
| Shutdown and SIGTERM | SIGTERM unit test and failing-cleanup test passed. The first local SIGTERM reproduced exit 137 without cleanup logs; after explicit signal routing, Docker stop exited 0 in under one second and logged all three cleanup stages. |
| Interaction diagnostics | Unit tests passed for receipt, successful completion, failed command, acknowledgement state, duration, and argument redaction. The duration is total command duration, not first-ack latency. |
| Gemini 404 | Unit test passed for a distinct bounded model error; the analyzer was called once and exception text was absent from logs and user response. |
| Compose volume declaration | `docker compose config -q` passed without a volume warning; the rebuilt container mounted `coc-bot-data:/app/data`. A pre-replacement SQLite backup and the running database both passed `PRAGMA integrity_check`; both scenario rows, channel IDs, and positions matched. |
| Full suite before QA additions | `223 passed, 1 warning`; the warning is the dependency's `audioop` deprecation. |

The original exit-137 behavior was reproduced before the signal fix, then resolved and verified against the rebuilt image using the existing data volume. The pre-replacement database backup is at `/tmp/coc-bot-before-followup.sqlite3`; no scenario or character data was changed by the runtime check.

## Evidence limits

The Oct 24 incident cause cannot be reconstructed without that deployed process/revision or its logs, even though the local exit-137 reproduction is now fixed. A second-user live quorum cannot be proven without a second eligible Discord identity. These limits do not prevent isolated parser/action/quorum regression tests. The native Google Doc and completed Discord scenario remain untouched; use a fresh fixture/channel for live validation.
