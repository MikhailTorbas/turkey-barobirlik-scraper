# Giovanni: national allocation and current-bar handover

## Your full national allocation — 5 November 2026

You exclusively own **20 bars** listed below. Start/continue **İSTANBUL (ID 34)**. The order below is a planning sequence, not an automatic paid-start instruction. Run **one bar at a time, at most four browser slots total on your Mac**; discovery uses one of those slots. Do not run four slots per assigned bar simultaneously.

| Order | Directory ID | Bar | Saved 2025 lawyer count | State |
|---|---|---|---|---|
| 1 | 34 | İSTANBUL | 67,463 | Current bar: resume saved Istanbul queue |
| 2 | 342 | İSTANBUL 2 NOLU | 3,979 | Assigned to you; check for a saved queue before initialization |
| 3 | 620 | ANKARA 2 NOLU | 3,078 | Assigned to you; check for a saved queue before initialization |
| 4 | 55 | SAMSUN | 2,385 | Assigned to you; check for a saved queue before initialization |
| 5 | 10 | BALIKESİR | 1,878 | Assigned to you; check for a saved queue before initialization |
| 6 | 46 | KAHRAMANMARAŞ | 1,632 | Assigned to you; check for a saved queue before initialization |
| 7 | 25 | ERZURUM | 1,083 | Assigned to you; check for a saved queue before initialization |
| 8 | 80 | OSMANİYE | 917 | Assigned to you; check for a saved queue before initialization |
| 9 | 23 | ELAZIĞ | 770 | Assigned to you; check for a saved queue before initialization |
| 10 | 72 | BATMAN | 717 | Assigned to you; check for a saved queue before initialization |
| 11 | 22 | EDİRNE | 665 | Assigned to you; check for a saved queue before initialization |
| 12 | 39 | KIRKLARELİ | 436 | Assigned to you; check for a saved queue before initialization |
| 13 | 5 | AMASYA | 420 | Assigned to you; check for a saved queue before initialization |
| 14 | 50 | NEVŞEHİR | 400 | Assigned to you; check for a saved queue before initialization |
| 15 | 37 | KASTAMONU | 380 | Assigned to you; check for a saved queue before initialization |
| 16 | 24 | ERZİNCAN | 312 | Assigned to you; check for a saved queue before initialization |
| 17 | 13 | BİTLİS | 226 | Assigned to you; check for a saved queue before initialization |
| 18 | 49 | MUŞ | 207 | Assigned to you; check for a saved queue before initialization |
| 19 | 79 | KİLİS | 183 | Assigned to you; check for a saved queue before initialization |
| 20 | 29 | GÜMÜŞHANE | 94 | Assigned to you; check for a saved queue before initialization |

Counts are the saved TBB baseline dated 31 December 2025. They are workload indicators, not current roster sizes or proof of completeness. Allocation is even by bar count (21/20/21/21); Istanbul makes equal total lawyer counts impossible while keeping the existing single-bar ownership. The newly assigned bars were spread using those saved counts. Do not take another operator's bar. TEAM.md is the master ownership list.

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
