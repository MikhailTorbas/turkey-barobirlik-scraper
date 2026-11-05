# Pari: national allocation and current-bar handover

## Your full national allocation — 5 November 2026

You exclusively own **21 bars** listed below. Start/continue **BURSA (ID 16)**. The order below is a planning sequence, not an automatic paid-start instruction. Run **one bar at a time, at most four browser slots total on your Mac**; discovery uses one of those slots. Do not run four slots per assigned bar simultaneously.

| Order | Directory ID | Bar | Saved 2025 lawyer count | State |
|---|---|---|---|---|
| 1 | 16 | BURSA | 6,544 | Current bar: resume existing queue if present |
| 2 | 33 | MERSİN | 3,915 | Assigned to you; check for a saved queue before initialization |
| 3 | 41 | KOCAELİ | 3,182 | Assigned to you; check for a saved queue before initialization |
| 4 | 20 | DENİZLİ | 2,286 | Assigned to you; check for a saved queue before initialization |
| 5 | 9 | AYDIN | 1,924 | Assigned to you; check for a saved queue before initialization |
| 6 | 45 | MANİSA | 1,876 | Assigned to you; check for a saved queue before initialization |
| 7 | 65 | VAN | 1,064 | Assigned to you; check for a saved queue before initialization |
| 8 | 3 | AFYONKARAHİSAR | 856 | Assigned to you; check for a saved queue before initialization |
| 9 | 60 | TOKAT | 733 | Assigned to you; check for a saved queue before initialization |
| 10 | 19 | ÇORUM | 667 | Assigned to you; check for a saved queue before initialization |
| 11 | 43 | KÜTAHYA | 593 | Assigned to you; check for a saved queue before initialization |
| 12 | 77 | YALOVA | 442 | Assigned to you; check for a saved queue before initialization |
| 13 | 71 | KIRIKKALE | 421 | Assigned to you; check for a saved queue before initialization |
| 14 | 73 | ŞIRNAK | 413 | Assigned to you; check for a saved queue before initialization |
| 15 | 14 | BOLU | 371 | Assigned to you; check for a saved queue before initialization |
| 16 | 53 | RİZE | 307 | Assigned to you; check for a saved queue before initialization |
| 17 | 12 | BİNGÖL | 240 | Assigned to you; check for a saved queue before initialization |
| 18 | 57 | SİNOP | 200 | Assigned to you; check for a saved queue before initialization |
| 19 | 76 | IĞDIR | 179 | Assigned to you; check for a saved queue before initialization |
| 20 | 62 | TUNCELİ | 74 | Assigned to you; check for a saved queue before initialization |
| 21 | 69 | BAYBURT | 59 | Assigned to you; check for a saved queue before initialization |

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
export TBB_QUEUE="$HOME/TurkeyData/pari-bar-BAR_ID/queue"

# NEW allocation only: refuse existing destinations.
.venv/bin/python prepare_queue.py --directory "$TBB_QUEUE" --baro BAR_ID --owner Pari
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
Read this file and CLAUDE.md before setup. Your current starting bar is **Bursa (directory bar ID 16)**. Your full exclusive allocation is listed above. Coordinate paid starts and any change of owner through TEAM.md.

## Install (macOS)

Accept your private GitHub invitation and authenticate Git on this Mac. Use Python 3.10+ (the tested environment is 3.14). Linux is supported without `caffeinate`; native Windows is not validated.

```sh
git clone https://github.com/MikhailTorbas/turkey-barobirlik-scraper.git
cd turkey-barobirlik-scraper
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python -m unittest discover -s tests
```

No local Chromium install is needed for hosted production. Tests are offline/mock; optional local browser tests skip unless explicitly enabled. Do not run `git pull` into a running production process; pause first.

## Credentials

Michael supplies a separate **pari-private** folder containing `zenrows.local.json`, `capsolver.local.json` and a private copy of this handover with the actual credentials. This folder is NOT in GitHub. Transfer it privately, save it as `$HOME/.config/tbb-pari`, and keep it outside the checkout. Hosted Browser Sessions need the ZenRows API key/connection URL and CapSolver key; separate residential-proxy credentials are not used by this flow.

```sh
export TBB_CONNECTION_FILE="$HOME/.config/tbb-pari/zenrows.local.json"
export TBB_SOLVER_FILE="$HOME/.config/tbb-pari/capsolver.local.json"
chmod 700 "$HOME/.config/tbb-pari"
chmod 600 "$TBB_CONNECTION_FILE" "$TBB_SOLVER_FILE"
```

Run these exports again in a new terminal. Never paste keys into GitHub, prompts, screenshots or logs. Check provider authentication/funding errors explicitly; do not buy credits/change subscriptions or dashboard caps. Shared account capacity for all four people (up to 16 slots total) still needs a coordinated live check; successful single-Mac tests do not prove that limit.

## Create your queue ONCE (offline)

Only use this if you have no prior queue for this allocation. `prepare_queue.py` creates a new destination exclusively and refuses existing directories. It seeds both surname and given-name discovery, starts with zero collected contacts and makes no paid requests. Earlier small test data for this bar is not included, so this is a fresh production allocation, not a merger of Michael's historical pilots.

```sh
export TBB_QUEUE="$HOME/TurkeyData/pari-bursa/queue"
.venv/bin/python prepare_queue.py --directory "$TBB_QUEUE" --baro 16 --owner Pari
.venv/bin/python queue_quality.py --directory "$TBB_QUEUE"
```

Expected: bar 16, four worker folders, zero completed/owned profiles and pending discovery queries. If the folder already exists, inspect and resume it; never delete it or initialize a second runnable copy to work around an error. The saved bar-option catalog is dated; live startup confirms the selected ID against the website.

## Launch / resume the authorized session

Setup itself does not launch paid work. Coordinate the first launch with Michael so simultaneous-account capacity and shared usage have one baseline. Once Michael gives the start signal, use this command for an **eight-hour active allowance**:

```sh
caffeinate -is .venv/bin/python refill_runner.py \
  --directory "$TBB_QUEUE" --seconds 28800 --uncapped \
  --solver-tasks 250 --discovery-solver-tasks 100 \
  --run-id pari-bursa-01
```

There is one terminal/controller, not four manual copies. It schedules at most four hosted browser slots. Discovery temporarily takes one slot; detail jobs are assigned once and refilled automatically. A fresh allocation initially runs discovery before details can fill all slots. The run can stop before eight hours for exhausted work, authentication, solver/recovery limits or other reported failures. A time-limit exit is not proof of complete bar coverage.

Keep AC power, lid open and network connected. Check the first 10–15 minutes for increasing completed counts and sustained progress; if account concurrency errors appear, coordinate fewer simultaneous slots/users rather than restarting repeatedly. No manual CAPTCHA intervention is part of an autonomous run.

**Pause:** Ctrl-C once and allow about two minutes for checkpoint/export cleanup. **Resume:** restore the environment variables and run the exact same command, directory and run ID. Do not rerun the initializer. Mac sleep/shutdown interrupts work; saved checkpoints permit continuation, not collection while the Mac is off.

After the allowance is consumed, do not change the run ID automatically. Michael can explicitly authorize a new allowance. Solver limits are lifetime attempts per preserved ledger, not fresh budgets per terminal launch. An approved increase uses `--amend-budgets` with the same unconsumed run ID; never delete ledgers/state. `--uncapped` disables the local credit ceiling only; provider-side caps/funds still apply.

## Track and return results

Inspect `refill-report-pari-bursa-01.json`, `refill-events-pari-bursa-01.jsonl`, worker `refill-console.log` files and the quality report inside the queue. Keep diagnostics private. Controller reports include worker states, completed/email totals, active runtime, provider observations and recovery stops.

```sh
.venv/bin/python queue_quality.py --directory "$TBB_QUEUE"
```

Record the Git commit (`git rev-parse HEAD`), start/end times and timezone, active duration, new completed profiles, profiles/minute, profiles with email, unique email addresses, fill rate, pending/review states, CAPTCHA attempts, challenges/reconnects and stop/resume issues. Distinguish verified source blanks/invalid emails from unknown/extraction failures. Shared-key credit deltas overlap other users: send timestamped observations to Michael; do not add the four Macs' deltas together.

After stopping cleanly, return the **entire queue directory** privately with `RESULTS.md` and the quality report, including discovery, all four worker databases, ownership, WAL files if present, run state and solver ledgers. A CSV alone cannot resume. Exclude provider configuration files. Never upload collected data/credentials to commits, issues or releases. Follow your assigned sequence only after closure/reconciliation or Michael’s explicit deferred-closure instruction, with the paid runtime agreed. Ownership transfers require updating TEAM.md. National completeness remains unverified.
