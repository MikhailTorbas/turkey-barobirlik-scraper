# Michael: national allocation and current-bar handover

## Your full national allocation — 5 November 2026

You exclusively own **21 bars** listed below. Current running group (**controlled restart with discovery-yield guard**): **ADANA (1), GAZİANTEP (27), KAYSERİ (38), ŞANLIURFA (63), two browser slots each, eight total**. All four saved queues were explicitly resumed after the readiness review; preserve them and do not initialize any again. The order below is a planning sequence, not an automatic paid-start instruction. For this explicitly authorized group, run four separate controllers with `--browser-slots 2` each. Keep at most eight browser slots total on your Mac, including discovery. Other bars in the sequence remain queued. Do not run four slots per assigned bar simultaneously.

| Order | Directory ID | Bar | Saved 2025 lawyer count | State |
|---|---|---|---|---|
| 1 | 1 | ADANA | 5,020 | Guarded restart, two slots; preserve queue and coverage gaps |
| 2 | 27 | GAZİANTEP | 3,664 | Guarded restart, two slots; preserve queue and coverage gaps |
| 3 | 38 | KAYSERİ | 3,254 | Guarded restart, two slots; preserve queue and coverage gaps |
| 4 | 63 | ŞANLIURFA | 2,412 | Guarded restart, two slots; preserve queue and coverage gaps |
| 5 | 26 | ESKİŞEHİR | 1,991 | Assigned to you; check for a saved queue before initialization |
| 6 | 54 | SAKARYA | 1,558 | Assigned to you; check for a saved queue before initialization |
| 7 | 61 | TRABZON | 1,128 | Assigned to you; check for a saved queue before initialization |
| 8 | 52 | ORDU | 925 | Assigned to you; check for a saved queue before initialization |
| 9 | 58 | SİVAS | 821 | Assigned to you; check for a saved queue before initialization |
| 10 | 32 | ISPARTA | 711 | Assigned to you; check for a saved queue before initialization |
| 11 | 64 | UŞAK | 628 | Assigned to you; check for a saved queue before initialization |
| 12 | 68 | AKSARAY | 558 | Assigned to you; check for a saved queue before initialization |
| 13 | 51 | NİĞDE | 419 | Assigned to you; check for a saved queue before initialization |
| 14 | 66 | YOZGAT | 384 | Assigned to you; check for a saved queue before initialization |
| 15 | 70 | KARAMAN | 333 | Assigned to you; check for a saved queue before initialization |
| 16 | 78 | KARABÜK | 275 | Assigned to you; check for a saved queue before initialization |
| 17 | 30 | HAKKARİ | 219 | Assigned to you; check for a saved queue before initialization |
| 18 | 36 | KARS | 203 | Assigned to you; check for a saved queue before initialization |
| 19 | 74 | BARTIN | 184 | Assigned to you; check for a saved queue before initialization |
| 20 | 7 | ANTALYA | 8,038 | Retained: paused; coverage reconciliation pending |
| 21 | 6 | ANKARA | 26,206 | Retained: audited with four detail exceptions; not certified exhaustive |

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
export TBB_QUEUE="$HOME/TurkeyData/michael-bar-BAR_ID/queue"

# NEW allocation only: refuse existing destinations.
.venv/bin/python prepare_queue.py --directory "$TBB_QUEUE" --baro BAR_ID --owner Michael
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

## Michael’s saved production queues

Adana is the current production run. Its local receipt is `outputs/adana-production-2026-11-05/launch.json`; the active-task pointer is `work/active-parser-task.json`. These local files are outside this Git checkout, relative to Michael’s workspace, and are not distributed by cloning GitHub. They contain the durable queue path and exact resume command. Preserve them and use the receipt rather than initializing Adana again.

Antalya is paused with 8,256 completed profiles and 4,879 unique emails in its saved 5 November stop report; coverage reconciliation remains pending. Ankara has 26,400 completed profiles, four documented detail exceptions and a completed saved-roster reconciliation; exhaustive current coverage remains unverified. Neither queue is transferred or reset by this allocation.

For a new machine, follow README.md installation and private credential setup, then the per-bar instructions above. Existing source data must travel privately with the full stopped queue; GitHub has no production contacts or checkpoints.

The continuing pair is controlled locally by `work/run_adana_gaziantep.py`, with the current supervisor PID and queue paths in `work/active-parser-task.json`. Gaziantep preserves `gaziantep-comparison-2026-11-05` as its run ID so prior work/runtime/solver history are retained. The timed comparison was interrupted before its automatic Adana-only restoration; it must not be relaunched alongside this pair.

The active four-bar group is recorded in `work/active-parser-task.json`, which lists **two supervisor PIDs**, their status files and all four queue paths. Pause both supervisors **and every separately recorded controller** to stop the entire group. Kayseri/Şanlıurfa are controlled locally by `work/run_kayseri_sanliurfa.py`; the existing Adana/Gaziantep supervisor remains running. Do not start a second copy of either pair or exceed eight total browsers.

Adana’s original child stopped on three solver-failure phases and received one recorded recovery (`adana-solver-refresh-20261105`). Its recovered controller is listed separately in `standalone_controllers` in the active-task receipt; pause it too. The first pair supervisor’s old Adana child report is historical, not the recovered controller’s current state. Use Adana’s queue report for its live state. No elapsed time, saved jobs or solver ledgers were reset.

**Earlier pause on 5 November (historical):** both supervisors and the standalone Adana recovery controller were stopped cleanly. All controller/worker leases released, with full queue backups and a reconciliation report saved locally under `outputs/four-bar-reconciliation-2026-11-05`. There is one unattempted Adana detail (registration 2409); its email is unknown. No validated exhaustive independent roster was obtained for these four bars; retain the coverage gap and pending discovery. `work/active-parser-task.json` is marked paused. The two-bar helper scripts launch paid work and must not run until Michael gives a resume instruction.

**Restart-readiness follow-up:** the saved Adana registration 2409 was completed in one bounded live check using one additional solver task. Its email is verified blank on the source; it is no longer pending. All four bars now have zero unfinished discovered details. Whole-bar coverage remains unverified. The new 900-active-second discovery-yield guard prevents paid overlapping-search tails from running indefinitely; review README.md before a recorded recovery. Broad scraping stays paused until Michael requests restart.

**Current restart:** Michael explicitly resumed all four bars after the readiness review, using one local `work/run_four_bar_guarded.py` supervisor. `work/active-parser-task.json` now identifies that one supervisor and its four queues; signal that verified PID once to pause the whole group. This supersedes the two-pair/standalone process layout above. Do not launch historical helper scripts alongside the unified supervisor. Every controller uses two browser slots, the same original run ID/runtime/solver ledger, and `--discovery-idle-seconds 900`. A low-yield or bounded recovery stop remains stopped until reviewed; no automated recovery/run-ID rotation. Independent full coverage remains unverified.
