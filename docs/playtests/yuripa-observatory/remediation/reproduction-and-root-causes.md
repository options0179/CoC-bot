# Reproduction and root causes

Scope: read-only inspection and local automated tests on branch `fix/scenario-aware-playtest-reliability`. No `.env` values, Docker environment inspection, Discord/browser actions, or external service mutations were used.

## Current observations

| Behavior | Expected by remediation design | Current code/evidence |
|---|---|---|
| `/행동` scene awareness | Use the channel's bound scenario, current scene, PC skills, and registered check rules to choose a validated rule and narrate the matching result branch. | `bot/cogs/action.py` calls `analyze_intent(설명, "")`; it supplies no scenario context and selects neither a registered rule nor scenario branch. This is a reproducible implementation gap, not a transient Gemini failure. The existing `test_action_cog.py` mocks the analyzer and does not assert scene lookup. |
| `/행동` analyzer error handling | Distinguish provider/network/timeout/response-format errors and finish the interaction with a useful bounded response. | The action command catches only `ValueError` and responds `행동을 분석하지 못했습니다. 다시 서술해 주세요.`. Other exceptions flow to the global app-command handler (`bot/main.py`), whose generic response is `명령어 처리 중 오류가 발생했습니다.`. The exact provider exception classes are not exercised by current tests. |
| Narration quorum with shared Keeper/PC account | Require two distinct eligible Discord accounts for a two-person Keeper+PC test. | Eligibility is a set of Discord IDs; `required_votes = (2 * len(eligible_user_ids) + 2) // 3`. If Keeper and PC use the same ID, they collapse to one eligible voter and one vote advances. This matches the historical playtest note and is also directly implied by current code. Current unit tests cover a Keeper-only one-voter quorum, but do not cover shared Keeper/PC identity. |
| Narration restart/persistent controls | Re-register usable controls on restart; stale controls should report that the position already moved. | `NarrationView` uses the default generated button custom ID and a 900-second in-memory view; `bot/main.py` has no persistent-view registration. Existing tests cover stale progression through an in-memory view, not restart recovery. |
| Scenario completion | Show completion in `/시나리오조회` after the last line. | The Oct 26 playtest record says completion and lookup display succeeded. Current tests also cover last-line completion and the scenario embed. |
| Local tests | Full automated suite passes. | Reproduced below: 177 passed, one `audioop` deprecation warning. |

## Reproduced now

Command: `/tmp/coc-bot-local-test-venv/bin/pytest -q`

Result: exit code 0; **177 passed, 1 warning in 0.83s**. Warning signature:

```text
DeprecationWarning: 'audioop' is deprecated and slated for removal in Python 3.13
```

Relevant test evidence:

- `tests/test_action_cog.py`: mocks analyzer and verifies basic roll, missing skill, unknown skill, `ValueError`, and missing key. It does not test real scenario context or provider-specific failure classes.
- `tests/test_narration_view.py`: tests distinct-user voting, duplicate vote, stale in-memory progression, one-person quorum, and end-of-scenario completion. It does not test same Discord ID assigned to Keeper and PC or process restart.
- `tests/test_embeds.py`, `tests/test_scenario_cog.py`: completion display behavior.
- `tests/test_intent_analyzer.py`: prompt and response parsing against fake model responses, not a live provider request.

The current implementation's analyzer context is visibly empty at `bot/cogs/action.py` (`analyze_intent, 설명, ""`), so the no-scene-context cause is confirmed by source. The same-account quorum cause is visible in `bot/cogs/narration.py` where eligible IDs are deduplicated into a set before quorum calculation. These are code-level reproductions; no external Discord run was performed for this report.

## Prior-run evidence (historical; not reproduced in this run)

These are recorded in `docs/playtests/yuripa-observatory/test-plan.md`, section 9.1 and section 10, and are not counted as this run's test outcomes:

- **2026-10-24 Discord timeout:** `/시나리오조회` twice showed Discord's `애플리케이션이 응답하지 않았어요`; `/판정 스킬값:50` also timed out. The contemporaneous diagnosis found the bot online, interaction endpoint URL empty, Gateway Intent active, and `#이벤트` permission allowing application commands. Local `/판정` code did not use DB or Gemini. The actual production process, deployment revision, and logs were unavailable, so the operating cause was not established.
- **2026-10-26 retired model ID:** first `/행동` returned Gemini HTTP 404 for `gemini-2.5-flash`; the record attributes it to an unavailable model ID, not a confirmed credential failure. After switching to `gemini-3.8-flash` and rebuilding the local image, `/행동` succeeded.
- **2026-10-26 generic error presentation:** the playtest record says the shared command error handler surfaced `명령어 처리 중 오류가 발생했습니다.` for the model error, while the cause was visible only in server logs.
- **2026-10-26 gameplay dice outcomes:** `/행동` chose 관찰력 65 and rolled 50 (success); `/판정` rolled 88 then push 89 (both failures); `/산정 0/1d4` rolled 55 (success, 0 loss); `/대립` rolled 90 and 72 (both failures, higher skill won per current opposed rule). These are gameplay RNG outcomes, **not technical failures** and should not be aggregated with provider errors or interaction timeouts.
- **2026-10-26 narration account setup:** the test used the same Discord user for Keeper and PC, so one vote advanced each line. The run verified sequential progression through 11 lines and completion, but did not verify a true two-account quorum. This is evidence of the test setup limitation and is consistent with the code-level quorum cause above.

## Not reproduced / evidence gaps

- No live Gemini 404/429/503, network failure, timeout, or malformed provider response was triggered. The historical 404 is prior-run evidence only.
- No current Discord interaction timeout was triggered. Historical production root cause remains unknown without the actual deployed service logs and revision.
- No two-account Discord narration quorum, stale Discord component after process restart, or restart recovery was run.
- No Docker Compose health, SQLite integrity, or restart-persistence check was run in this task.
- No registered scenario rules exist in the current parser/action path; therefore scenario-specific success/failure narration cannot be demonstrated through the live command. `scenario_parser.py` currently parses narration structure only.
- We have no evidence that dice failures are technical defects. The recorded failures above were ordinary random game results.

## Root-cause summary

1. **Missing scenario-aware behavior:** `/행동` explicitly passes an empty context and has no scenario-rule lookup/result-branch selection path. This is a current, source-confirmed feature gap.
2. **Shared identity reduces narration quorum:** eligible voters are unique Discord IDs, so one account representing both Keeper and PC is one voter. The historical one-account test therefore cannot validate two-person consent; if that setup is allowed in production, one click satisfies its one-voter quorum.
3. **Restart recovery is absent in current code:** narration controls are ephemeral in-memory views with generated custom IDs and no startup re-registration. Existing tests do not cover process restart.
4. **Historical provider mismatch:** the Oct 26 404 was recorded against the retired model ID and cleared after switching model IDs. It was not independently reprobed here.
5. **Historical Discord timeout remains undiagnosed:** Oct 24 evidence rules out several obvious local/portal causes but does not identify the production process failure. Do not attribute that timeout to the current code without deployment logs.

