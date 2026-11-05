# Michael: national allocation and current-bar handover

## Your full national allocation — 5 November 2026

You exclusively own **21 bars** listed below. Current saved group (**paused after the discovery-yield guard**): **ADANA (1), GAZİANTEP (27), KAYSERİ (38), ŞANLIURFA (63), two browser slots each, eight total**. The guarded restart stopped all four queues after low-yield discovery. Preserve them and do not initialize any again. See COVERAGE_STATUS.md before another restart. The order below is a planning sequence, not an automatic paid-start instruction. For this explicitly authorized group, run four separate controllers with `--browser-slots 2` each. Keep at most eight browser slots total on your Mac, including discovery. Other bars in the sequence remain queued. Do not run four slots per assigned bar simultaneously.

| Order | Directory ID | Bar | Saved 2025 lawyer count | State |
|---|---|---|---|---|
| 1 | 1 | ADANA | 5,020 | Paused after low yield; preserve queue and coverage gaps |
| 2 | 27 | GAZİANTEP | 3,664 | Paused after low yield; preserve queue and coverage gaps |
| 3 | 38 | KAYSERİ | 3,254 | Paused after low yield; preserve queue and coverage gaps |
| 4 | 63 | ŞANLIURFA | 2,412 | Paused after low yield; preserve queue and coverage gaps |
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

Adana is one of the four saved, paused production queues. Its local receipt is `outputs/adana-production-2026-11-05/launch.json`; the active-task pointer is `work/active-parser-task.json`. These local files are outside this Git checkout, relative to Michael’s workspace, and are not distributed by cloning GitHub. They contain the durable queue path and exact resume command. Preserve them and use the receipt rather than initializing Adana again.

Antalya is paused with 8,256 completed profiles and 4,879 unique emails in its saved 5 November stop report; coverage reconciliation remains pending. Ankara has 26,400 completed profiles, four documented detail exceptions and a completed saved-roster reconciliation; exhaustive current coverage remains unverified. Neither queue is transferred or reset by this allocation.

For a new machine, follow README.md installation and private credential setup, then the per-bar instructions above. Existing source data must travel privately with the full stopped queue; GitHub has no production contacts or checkpoints.

## Current operational state — 6 November review

All four saved queues stopped safely by 22:49 Tbilisi time on 5 November, with `discovery_yield_paused`. The guarded restart completed three additional profiles: Gaziantep +2 and Kayseri +1. Totals are Adana 5,193; Gaziantep 3,741; Kayseri 3,304; Şanlıurfa 2,469. All discovered detail jobs are complete; 4,749 discovery queries remain pending. Full current coverage is unverified.

`work/active-parser-task.json` identifies the latest unified supervisor (`work/run_four_bar_guarded.py`), but that supervisor has exited. Do not signal its historical PID or launch older pair/standalone helpers. A future resume must verify queue leases, use the same saved run IDs/runtime/solver ledgers, and explicitly record recovery of each persistent yield pause after reviewing the coverage evidence. Ordinary restart intentionally cannot silently clear the pause.

The resolved Adana registration 2409 is complete and its email is blank on the source. It is not an unresolved extraction failure. Ankara and Antalya retain their earlier documented coverage exceptions. See [COVERAGE_STATUS.md](COVERAGE_STATUS.md) for the remaining dependency; no new bar or automatic paid restart is authorized by this status record.
