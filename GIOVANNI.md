# Giovanni: setup and remaining-bar handover

## Active allocation — 16 November 2026

Michael explicitly reassigned the 29 locally unstarted bars between Elena and Giovanni. Your next-work list contains **14 bars**, approximately **11,235 profiles** against the 31 December 2025 TBB baseline. These are dated workload indicators, not coverage proof. TEAM.md is the authoritative ownership table.

Open this file, README.md, CLAUDE.md and TEAM.md with Claude Code. Clone the repository if new; otherwise stop any local parser cleanly before pulling updates. Use your private provider configuration outside Git. Run the offline setup/tests first. This reassignment is not permission to duplicate a queue or automatically launch the whole list: coordinate the paid start and runtime with Michael. Default on your Mac is one bar at a time, at most four browser slots including discovery, with the 900-second low-yield guard and existing provider/solver limits.

Search your Mac and any privately returned results before initializing each bar. The local coordinator has no saved production queues for this next-work list, but cannot observe your Mac. If you already started a listed/transferred bar, tell Michael before launching anything; preserve the queue, original run ID, remaining allowance and all ledgers. Do not create a fresh queue to replace existing work.

### Next-work list (in order)

| Order | Directory ID | Bar | 31 December 2025 approximate target | State |
|---|---|---|---:|---|
| 1 | 620 | ANKARA 2 NOLU | 3,078 | Check saved work; coordinate start |
| 2 | 55 | SAMSUN | 2,385 | Check saved work; coordinate start |
| 3 | 46 | KAHRAMANMARAŞ | 1,632 | Check saved work; coordinate start |
| 4 | 23 | ELAZIĞ | 770 | Check saved work; coordinate start |
| 5 | 22 | EDİRNE | 665 | Check saved work; coordinate start |
| 6 | 77 | YALOVA | 442 | Check saved work; coordinate start |
| 7 | 71 | KIRIKKALE | 421 | Check saved work; coordinate start |
| 8 | 5 | AMASYA | 420 | Check saved work; coordinate start |
| 9 | 73 | ŞIRNAK | 413 | Check saved work; coordinate start |
| 10 | 24 | ERZİNCAN | 312 | Check saved work; coordinate start |
| 11 | 12 | BİNGÖL | 240 | Check saved work; coordinate start |
| 12 | 57 | SİNOP | 200 | Check saved work; coordinate start |
| 13 | 79 | KİLİS | 183 | Check saved work; coordinate start |
| 14 | 62 | TUNCELİ | 74 | Check saved work; coordinate start |

### Previously started work retained for reconciliation

These bars are not part of the 29-bar new-work split. Do not initialize them again or clear recorded stops. Michael's saved covering queues must be transferred privately before another Mac resumes them. Pauses do not establish full coverage.

| Order | Directory ID | Bar | 31 December 2025 approximate target | State |
|---|---|---|---:|---|
| 1 | 34 | İSTANBUL | 67,463 | Saved work; coverage unverified |

İstanbul 34 remains with Giovanni as a separate existing queue. Its latest completion is not verified locally; report your current status before switching bars. The new-work totals above exclude İstanbul.

## Persistent outer Cloudflare block — diagnosis update

A hosted browser connecting successfully does not mean the directory is accessible. If startup diagnostics show repeated managed-challenge observations and no search form, the ordinary in-form Turnstile solver is not reached. A recovery ID only releases a recorded local stop; it does not restore site access.

The updated scraper records `managed_challenge_blocked` when the outer challenge still occupies the page at the startup deadline. It preserves pending work and stops that controller role without automatically opening more sessions for the same block. Other healthy roles can finish known details. Existing pauses, consumed recovery IDs and runtime/solver ledgers are not reset by this update.

Elena's bar 342 log on 18 November shows nine blocked sessions, zero completed profiles and all 2,048 searches pending. Her `elena-access-review-20261118` ID is already consumed; **do not invent another ID or rerun the initializer**. The earlier yield pause was also reopened even though the prior instructions excluded that action. Keep the queue stopped. Pull this update only after clean shutdown. Request provider/site access diagnosis using the target directory URL, UTC failure timestamps and private sanitized diagnostics; do not post credentials or challenge artifacts to the public repository. There is no evidence in the supplied log that a different bar, larger solver budget, VPN change or repeated restart would fix this. After access is restored, coordinate one explicit recovery with Michael using the same queue and original run ID/remaining allowance.

## Cloudflare/access diagnosis and one-time recovery — 18 November 2026

Give these instructions to Claude Code when access fails. Michael authorizes **one recorded recovery for the current affected queue** for a confirmed access/session-related no-progress stop, after diagnosis and a safe backup. This is not a blanket authorization to recover other bars or repeatedly reopen stops. A recovery ID does not bypass Cloudflare.

1. Read CLAUDE.md, README.md, TEAM.md and this handover. Identify the current bar, authoritative queue, original run ID, exact launch command, remaining runtime and solver budgets. Verify processes and controller/worker leases before starting anything. Never run duplicate controllers or infer another Mac is inactive from local checks.
2. Inspect the latest `refill-report-*`, `refill-state-*`, phase events and relevant worker logs. Distinguish an active bounded retry, expired browser session, provider authentication/funding error, solver limit, discovery-yield pause and `three_phases_without_progress` stop. Not every Cloudflare response requires a recovery ID. Never print credentials or commit production data/logs.
3. Before modifying a checkpoint or applying recovery, gracefully stop any active controller once, wait for child cleanup and all queue leases to release, then back up the **entire stopped queue**, including SQLite databases and any WAL files, ownership, runtime state and solver ledgers. Run `queue_quality.py`; record completed profiles/emails and pending/review work before recovery. Do not back up a live queue by copying SQLite files independently.
4. Fix the diagnosed cause using the existing implementation where possible. Resume the **same queue, original run ID and recorded configuration**. Preserve completed profiles, pending/review jobs, official bar ID plus local registration identities, ownership, consumed runtime and all solver attempts. Keep the **900-second low-yield guard**, recorded browser-slot limits and provider caps. Do not substitute the historical launch examples elsewhere in this handover for the actual saved command.
5. Only for a confirmed access/session-related no-progress stop, after diagnosis and backup, append this single authorized recovery option to the saved launch command:

   ```text
   --recover-stopped giovanni-access-review-20261118
   ```

   Check the saved `operator_recoveries` history first. If this ID was already used for this queue, it grants no additional reset: do not rotate IDs, delete history, edit stop flags or clear counters manually. Record which queue used this authorization. Do not use it to reopen a discovery-yield pause.
6. This authorization does **not** allow budget increases, resetting an exhausted allowance, new run IDs to gain runtime, purchases, subscription changes, provider-cap changes or recovery of earlier stopped bars. If one of these is needed, or persistent Cloudflare blocking remains after bounded recovery, stop safely and report the specific blocker to Michael. Do not loop retries or manually solve Cloudflare while claiming an autonomous fix.
7. After resuming, verify actual increases in completed-profile counts and healthy leases; a live process alone is not proof of collection. Report the cause, fix, queue/run ID, backup location, profiles/emails before and after, remaining pending/review work, remaining runtime/solver limits and unresolved blockers. Include the agreed **31 December 2025 approximate baseline** when reporting bar coverage; a pause is not complete coverage.

### What your LLM must do for each bar

1. Read this entire handover, CLAUDE.md, README.md and TEAM.md. Verify the bar ID belongs to you. Locate your existing queue/launch receipt first. An existing queue must be resumed; never recreate it or copy another person's live queue.
2. Before changing bars, stop the old controller with Ctrl-C once, wait for checkpoint/export cleanup, confirm zero active children, and run `queue_quality.py`. Preserve its full queue, ownership database, discovery/worker checkpoints, runtime state and solver ledgers. Record whether coverage is complete, unverified, blocked or awaiting reconciliation; never call a time-limit/empty detail queue proof of coverage.
3. Inspect pending/review details, discovery and roster gaps. Reconcile against official roster evidence where available. If Michael explicitly defers closure, retain the old bar under your custody with a written remainder; do not erase pending searches or assign it to someone else.
4. For a genuinely new bar, use a separate directory outside the checkout. Replace BAR_ID with the numeric ID from your table, and RUN_ID with a unique operator/bar-specific ID. Do not run the initializer if that directory already exists. An assignment grants ownership; coordinate each paid launch/runtime allowance with Michael. No automatic loop across the table or automatic new run IDs.

```sh
# Set these to your private local provider files; actual keys are never in Git.
export TBB_CONNECTION_FILE="/absolute/private/zenrows.local.json"
export TBB_SOLVER_FILE="/absolute/private/capsolver.local.json"
# Substitute your own user/bar directory. Keep one durable queue per bar.
export TBB_QUEUE="$HOME/TurkeyData/giovanni-bar-BAR_ID/queue"

# NEW allocation only: refuse existing destinations.
.venv/bin/python prepare_queue.py --directory "$TBB_QUEUE" --baro BAR_ID --owner Giovanni
.venv/bin/python queue_quality.py --directory "$TBB_QUEUE"

# Only after the paid-start instruction; eight-hour allowance example.
caffeinate -is .venv/bin/python refill_runner.py \
  --directory "$TBB_QUEUE" --seconds 28800 --uncapped \
  --solver-tasks 250 --discovery-solver-tasks 100 \
  --run-id RUN_ID
```

For an existing production queue, use its recorded command and limits instead of replacing them with this example. Resume with the identical queue, run ID and configuration. An exhausted allowance needs explicit authorization; never reset counters/ledgers. The connection/solver flags can be supplied explicitly instead of the environment variables. Keep keys, contacts and checkpoints outside Git. Funding/provider caps remain shared; do not buy credits, alter subscriptions or change dashboard limits.

5. Track new completed profiles, profiles/minute (recent and overall), profiles with email, unique emails, fill rate, pending/review statuses, active workers, solver attempts, reconnects/challenges, active runtime and timestamped shared-account credits. Shared-account deltas overlap: do not add simultaneous operators' totals. Distinguish source blanks/invalid emails from unknown extraction failures.
6. Return a private RESULTS.md, quality report and the entire stopped queue for each bar. GitHub stores ownership/instructions only. Keep Mac on AC with lid open while parsing; sleeping does not collect. Resume saved work after moving/shutdown.

## Existing starting-bar setup and recovery instructions
Your current starting bar remains **Istanbul, bar 34, four slots**; your full exclusive allocation is listed above. Your prior eight-hour run did not finish discovery/details. Use this updated source with your existing data; do not create an empty queue or start the old build alongside it.

1. Clone/install as in README.md. Give Claude access to this checkout and your existing local queue. Keep credentials outside the repository and chat.
2. Stop any old runner. Upgrade the entire stopped queue into a new local directory using `upgrade_queue.py`. Keep the old directory as backup. Alternatively, if Michael has supplied the latest already-upgraded queue, use that queue directly.
3. Read the upgrade receipt and `queue_quality.py` output. Confirm ownership, bar 34, preserved completions and persistent solver attempts. An upgrade from your original October return will include stored-source email repairs and exact-ID follow-ups; an already-upgraded queue may have those completed already.
4. Wait for Michael's paid-start instruction. Your historical `joint-eight-hour` allowance is exhausted. The README's new production run ID starts a new explicit allowance. It preserves completed work; it does not repeat successful profiles.
5. Start the four-slot command against the new directory. Keep the Mac awake/on AC/lid open. Use the identical command to resume after a pause. Do not reset ledgers, manually edit runtime or create duplicate runnable copies.
6. Return the full updated queue privately with a RESULTS.md and quality report. **Do not upload queues, contacts, credentials, logs or production archives to GitHub issues, commits or releases.**

The new code supports uncapped application operation, resilient usage telemetry, recorded solver-limit amendments, exact-ID recovery, source-written multi-address parsing and final export/shutdown fixes. Provider dashboard caps are separate and still apply until the account owner changes them. Check with Michael; do not purchase credits or alter subscriptions yourself.

A missing source record remains review work. Repeated TBB numbers do not justify merging people with different bar registrations. Discovery/roster gaps must remain visible; do not claim full Istanbul or nationwide coverage from a time-limit exit.
