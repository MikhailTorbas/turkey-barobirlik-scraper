# Michael: national allocation and current-bar handover

## Your full national allocation — 5 November 2026

You exclusively own **21 bars** listed below. **Current authorized group: NİĞDE (51), YOZGAT (66), KARAMAN (70), KARABÜK (78), two browser slots each/eight maximum**, launched on 6 November after Michael's explicit instruction. Each fresh queue has uncapped application credits and a 900-second discovery-yield guard, with a seven-day safety backstop instead of an eight-hour cutoff. Other operators' assignments are unchanged.

The prior Adana (1), Gaziantep (27), Kayseri (38), Şanlıurfa (63), Eskişehir (26), Sakarya (54), Trabzon (61), Ordu (52), Sivas (58), Isparta (32), Uşak (64) and Aksaray (68) queues remain paused with saved data and unverified coverage. Preserve them; do not recreate or resume them alongside the current group. The sequence below is not an automatic paid-start instruction for later bars.

| Order | Directory ID | Bar | Saved 2025 lawyer count | State |
|---|---|---|---|---|
| 1 | 1 | ADANA | 5,020 | Paused after low yield; preserve queue and coverage gaps |
| 2 | 27 | GAZİANTEP | 3,664 | Paused after low yield; preserve queue and coverage gaps |
| 3 | 38 | KAYSERİ | 3,254 | Paused after low yield; preserve queue and coverage gaps |
| 4 | 63 | ŞANLIURFA | 2,412 | Paused after low yield; preserve queue and coverage gaps |
| 5 | 26 | ESKİŞEHİR | 1,991 | Paused after low yield; preserve queue and coverage gaps |
| 6 | 54 | SAKARYA | 1,558 | Paused after low yield; preserve queue and coverage gaps |
| 7 | 61 | TRABZON | 1,128 | Paused after low yield; preserve queue and coverage gaps |
| 8 | 52 | ORDU | 925 | Paused after low yield; preserve queue and coverage gaps |
| 9 | 58 | SİVAS | 821 | Paused after low yield; preserve queue and coverage gaps |
| 10 | 32 | ISPARTA | 711 | Paused after low yield; preserve queue and coverage gaps |
| 11 | 64 | UŞAK | 628 | Paused after low yield; preserve queue and coverage gaps |
| 12 | 68 | AKSARAY | 558 | Paused after low yield; preserve queue and coverage gaps |
| 13 | 51 | NİĞDE | 419 | Current authorized run, two slots; preserve new durable queue |
| 14 | 66 | YOZGAT | 384 | Current authorized run, two slots; preserve new durable queue |
| 15 | 70 | KARAMAN | 333 | Current authorized run, two slots; preserve new durable queue |
| 16 | 78 | KARABÜK | 275 | Current authorized run, two slots; preserve new durable queue |
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

## Previous four-bar group — paused after the 6 November review

All four saved queues stopped safely by 22:49 Tbilisi time on 5 November, with `discovery_yield_paused`. The guarded restart completed three additional profiles: Gaziantep +2 and Kayseri +1. Totals are Adana 5,193; Gaziantep 3,741; Kayseri 3,304; Şanlıurfa 2,469. All discovered detail jobs are complete; 4,749 discovery queries remain pending. Full current coverage is unverified.

The prior guarded supervisor (`work/run_four_bar_guarded.py`) has exited; its receipt is under `outputs/four-bar-yield-guard-restart-2026-11-05`. Do not signal its historical PID or launch older pair/standalone helpers. A future recovery of these old queues must verify leases, use their same saved run IDs/runtime/solver ledgers, and explicitly record recovery of persistent yield pauses.

The resolved Adana registration 2409 is complete and its email is blank on the source. It is not an unresolved extraction failure. Ankara and Antalya retain their earlier documented coverage exceptions. See [COVERAGE_STATUS.md](COVERAGE_STATUS.md) for the remaining dependency; no new bar or automatic paid restart is authorized by this status record.

## Previous Eskişehir/Sakarya/Trabzon/Ordu group

These four queues safely stopped with `discovery_yield_paused` by 03:02 Tbilisi time on 6 November. All 5,733 discovered profiles were completed; 3,654 contain emails (3,651 distinct email addresses across the group). Pending discovery remains saved and whole-bar coverage unverified. Their historical supervisor/receipts are `work/run_next_four_bars.py` and `outputs/next-four-bars-production-2026-11-06`. Do not restart from those historical receipts alongside the current group.

## Previous Sivas/Isparta/Uşak/Aksaray group

All four stopped safely with `discovery_yield_paused`. Saved completions: Sivas 831, Isparta 729, Uşak 640, Aksaray 480 (2,680 total). Source coverage remains unverified; Aksaray is below its dated 2025 baseline of 558 and requires targeted follow-up. Preserve every queue and pending search. Historical receipts: `outputs/third-four-bars-production-2026-11-06`; old supervisor `work/run_third_four_bars.py`. Do not restart it alongside the current group.

## Current four-bar launch — 6 November

Michael explicitly authorized Niğde 51, Yozgat 66, Karaman 70 and Karabük 78 after the previous group stopped. The single current supervisor is `work/run_fourth_four_bars.py`; verify its PID/status in `work/active-parser-task.json` and `outputs/fourth-four-bars-production-2026-11-06/status.json`. Signal that verified supervisor once to checkpoint/stop the group; wait for all queue leases to release before moving or resuming. Historical supervisor PIDs must not be signaled.

Fresh queues are `outputs/NAME-production-2026-11-06/queue` outside Git (NAME: `nigde`, `yozgat`, `karaman`, `karabuk`), run IDs `NAME-production-2026-11-06`. Exact commands are in the adjacent `launch-plan.json` and group `LAUNCH_PLAN.json`. Commands use `--seconds 604800 --uncapped --browser-slots 2 --solver-tasks 250 --discovery-solver-tasks 100 --discovery-idle-seconds 900`. The seven-day allowance is a safety backstop, replacing the prior eight-hour cutoff; the intended operational stop is drained detail work plus 15 active minutes without new identities/verified roster progress, or bounded recovery/provider/solver limits. This is not an unlimited retry policy or a coverage proof. Keep runtime and lifetime solver ledgers on resume; never clear yield/recovery stops automatically. No automatic rollover to later bars.

The saved official 31 December 2025 population baseline was checked before launch: Niğde 419, Yozgat 384, Karaman 333, Karabük 275. These are not current verified roster totals. Previous twelve bars and Ankara/Antalya retain their data and unresolved coverage work. Only Hakkari 30, Kars 36 and Bartın 74 remain unstarted in Michael's allocation after this launch.
