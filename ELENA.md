# Elena: setup and remaining-bar handover

## Active allocation — 16 November 2026

Michael explicitly reassigned the 29 locally unstarted bars between Elena and Giovanni. Your next-work list contains **15 bars**, approximately **11,233 profiles** against the 31 December 2025 TBB baseline. These are dated workload indicators, not coverage proof. TEAM.md is the authoritative ownership table.

Open this file, README.md, CLAUDE.md and TEAM.md with Claude Code. Clone the repository if new; otherwise stop any local parser cleanly before pulling updates. Use your private provider configuration outside Git. Run the offline setup/tests first. This reassignment is not permission to duplicate a queue or automatically launch the whole list: coordinate the paid start and runtime with Michael. Default on your Mac is one bar at a time, at most four browser slots including discovery, with the 900-second low-yield guard and existing provider/solver limits.

Search your Mac and any privately returned results before initializing each bar. The local coordinator has no saved production queues for this next-work list, but cannot observe your Mac. If you already started a listed/transferred bar, tell Michael before launching anything; preserve the queue, original run ID, remaining allowance and all ledgers. Do not create a fresh queue to replace existing work.

### Next-work list (in order)

| Order | Directory ID | Bar | 31 December 2025 approximate target | State |
|---|---|---|---:|---|
| 1 | 342 | İSTANBUL 2 NOLU | 3,979 | Check saved work; coordinate start |
| 2 | 10 | BALIKESİR | 1,878 | Check saved work; coordinate start |
| 3 | 25 | ERZURUM | 1,083 | Check saved work; coordinate start |
| 4 | 80 | OSMANİYE | 917 | Check saved work; coordinate start |
| 5 | 72 | BATMAN | 717 | Check saved work; coordinate start |
| 6 | 39 | KIRKLARELİ | 436 | Check saved work; coordinate start |
| 7 | 50 | NEVŞEHİR | 400 | Check saved work; coordinate start |
| 8 | 37 | KASTAMONU | 380 | Check saved work; coordinate start |
| 9 | 14 | BOLU | 371 | Check saved work; coordinate start |
| 10 | 53 | RİZE | 307 | Check saved work; coordinate start |
| 11 | 13 | BİTLİS | 226 | Check saved work; coordinate start |
| 12 | 49 | MUŞ | 207 | Check saved work; coordinate start |
| 13 | 76 | IĞDIR | 179 | Check saved work; coordinate start |
| 14 | 29 | GÜMÜŞHANE | 94 | Check saved work; coordinate start |
| 15 | 69 | BAYBURT | 59 | Check saved work; coordinate start |

### Previously started work retained for reconciliation

These bars are not part of the 29-bar new-work split. Do not initialize them again or clear recorded stops. Michael's saved covering queues must be transferred privately before another Mac resumes them. Pauses do not establish full coverage.

| Order | Directory ID | Bar | 31 December 2025 approximate target | State |
|---|---|---|---:|---|
| 1 | 35 | İZMİR | 14,300 | Saved work; coverage unverified |
| 2 | 42 | KONYA | 4,239 | Saved work; coverage unverified |
| 3 | 21 | DİYARBAKIR | 2,596 | Saved work; coverage unverified |
| 4 | 48 | MUĞLA | 2,487 | Saved work; coverage unverified |
| 5 | 31 | HATAY | 2,088 | Saved work; coverage unverified |
| 6 | 59 | TEKİRDAĞ | 1,448 | Saved work; coverage unverified |
| 7 | 44 | MALATYA | 1,143 | Saved work; coverage unverified |
| 8 | 17 | ÇANAKKALE | 930 | Saved work; coverage unverified |
| 9 | 47 | MARDİN | 848 | Saved work; coverage unverified |
| 10 | 67 | ZONGULDAK | 670 | Saved work; coverage unverified |
| 11 | 2 | ADIYAMAN | 644 | Saved work; coverage unverified |
| 12 | 28 | GİRESUN | 507 | Saved work; coverage unverified |
| 13 | 81 | DÜZCE | 420 | Saved work; coverage unverified |
| 14 | 15 | BURDUR | 396 | Saved work; coverage unverified |
| 15 | 40 | KIRŞEHİR | 345 | Saved work; coverage unverified |
| 16 | 4 | AĞRI | 281 | Saved work; coverage unverified |
| 17 | 56 | SİİRT | 266 | Saved work; coverage unverified |
| 18 | 11 | BİLECİK | 192 | Saved work; coverage unverified |
| 19 | 18 | ÇANKIRI | 163 | Saved work; coverage unverified |
| 20 | 8 | ARTVİN | 158 | Saved work; coverage unverified |
| 21 | 75 | ARDAHAN | 55 | Saved work; coverage unverified |

Michael covered all 21 earlier Elena bars. Hatay retains 400 stranded details; İzmir has review records and a dated-baseline gap. Muğla also has separate direct-parser evidence. Preserve these sources and coordinate recovery separately.

## Cloudflare/access diagnosis and one-time recovery — 18 November 2026

Give these instructions to Claude Code when access fails. Michael authorizes **one recorded recovery for the current affected queue** for a confirmed access/session-related no-progress stop, after diagnosis and a safe backup. This is not a blanket authorization to recover other bars or repeatedly reopen stops. A recovery ID does not bypass Cloudflare.

1. Read CLAUDE.md, README.md, TEAM.md and this handover. Identify the current bar, authoritative queue, original run ID, exact launch command, remaining runtime and solver budgets. Verify processes and controller/worker leases before starting anything. Never run duplicate controllers or infer another Mac is inactive from local checks.
2. Inspect the latest `refill-report-*`, `refill-state-*`, phase events and relevant worker logs. Distinguish an active bounded retry, expired browser session, provider authentication/funding error, solver limit, discovery-yield pause and `three_phases_without_progress` stop. Not every Cloudflare response requires a recovery ID. Never print credentials or commit production data/logs.
3. Before modifying a checkpoint or applying recovery, gracefully stop any active controller once, wait for child cleanup and all queue leases to release, then back up the **entire stopped queue**, including SQLite databases and any WAL files, ownership, runtime state and solver ledgers. Run `queue_quality.py`; record completed profiles/emails and pending/review work before recovery. Do not back up a live queue by copying SQLite files independently.
4. Fix the diagnosed cause using the existing implementation where possible. Resume the **same queue, original run ID and recorded configuration**. Preserve completed profiles, pending/review jobs, official bar ID plus local registration identities, ownership, consumed runtime and all solver attempts. Keep the **900-second low-yield guard**, recorded browser-slot limits and provider caps. Do not substitute the historical launch examples elsewhere in this handover for the actual saved command.
5. Only for a confirmed access/session-related no-progress stop, after diagnosis and backup, append this single authorized recovery option to the saved launch command:

   ```text
   --recover-stopped elena-access-review-20261118
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
export TBB_QUEUE="$HOME/TurkeyData/elena-bar-BAR_ID/queue"

# NEW allocation only: refuse existing destinations.
.venv/bin/python prepare_queue.py --directory "$TBB_QUEUE" --baro BAR_ID --owner Elena
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

## Historical İzmir setup — reference only; do not launch again
Read this file and CLAUDE.md before setup. İzmir (directory bar ID 35) has already been started by Michael; the examples below are historical. Use the generic BAR_ID commands above for your next-work list, not a new İzmir queue. Your full exclusive allocation is listed above. Coordinate paid starts and any change of owner through TEAM.md.

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

Michael supplies a separate **elena-private** folder containing `zenrows.local.json`, `capsolver.local.json` and a private copy of this handover with the actual credentials. This folder is NOT in GitHub. Transfer it privately, save it as `$HOME/.config/tbb-elena`, and keep it outside the checkout. Hosted Browser Sessions need the ZenRows API key/connection URL and CapSolver key; separate residential-proxy credentials are not used by this flow.

```sh
export TBB_CONNECTION_FILE="$HOME/.config/tbb-elena/zenrows.local.json"
export TBB_SOLVER_FILE="$HOME/.config/tbb-elena/capsolver.local.json"
chmod 700 "$HOME/.config/tbb-elena"
chmod 600 "$TBB_CONNECTION_FILE" "$TBB_SOLVER_FILE"
```

Run these exports again in a new terminal. Never paste keys into GitHub, prompts, screenshots or logs. Check provider authentication/funding errors explicitly; do not buy credits/change subscriptions or dashboard caps. Shared account capacity for all four people (up to 16 slots total) still needs a coordinated live check; successful single-Mac tests do not prove that limit.

## Create your queue ONCE (offline)

Only use this if you have no prior queue for this allocation. `prepare_queue.py` creates a new destination exclusively and refuses existing directories. It seeds both surname and given-name discovery, starts with zero collected contacts and makes no paid requests. Earlier small test data for this bar is not included, so this is a fresh production allocation, not a merger of Michael's historical pilots.

```sh
export TBB_QUEUE="$HOME/TurkeyData/elena-izmir/queue"
.venv/bin/python prepare_queue.py --directory "$TBB_QUEUE" --baro 35 --owner Elena
.venv/bin/python queue_quality.py --directory "$TBB_QUEUE"
```

Expected: bar 35, four worker folders, zero completed/owned profiles and pending discovery queries. If the folder already exists, inspect and resume it; never delete it or initialize a second runnable copy to work around an error. The saved bar-option catalog is dated; live startup confirms the selected ID against the website.

## Launch / resume the authorized session

Setup itself does not launch paid work. Coordinate the first launch with Michael so simultaneous-account capacity and shared usage have one baseline. Once Michael gives the start signal, use this command for an **eight-hour active allowance**:

```sh
caffeinate -is .venv/bin/python refill_runner.py \
  --directory "$TBB_QUEUE" --seconds 28800 --uncapped \
  --solver-tasks 250 --discovery-solver-tasks 100 \
  --run-id elena-izmir-01
```

There is one terminal/controller, not four manual copies. It schedules at most four hosted browser slots. Discovery temporarily takes one slot; detail jobs are assigned once and refilled automatically. A fresh allocation initially runs discovery before details can fill all slots. The run can stop before eight hours for exhausted work, authentication, solver/recovery limits or other reported failures. A time-limit exit is not proof of complete bar coverage.

Keep AC power, lid open and network connected. Check the first 10–15 minutes for increasing completed counts and sustained progress; if account concurrency errors appear, coordinate fewer simultaneous slots/users rather than restarting repeatedly. No manual CAPTCHA intervention is part of an autonomous run.

**Pause:** Ctrl-C once and allow about two minutes for checkpoint/export cleanup. **Resume:** restore the environment variables and run the exact same command, directory and run ID. Do not rerun the initializer. Mac sleep/shutdown interrupts work; saved checkpoints permit continuation, not collection while the Mac is off.

After the allowance is consumed, do not change the run ID automatically. Michael can explicitly authorize a new allowance. Solver limits are lifetime attempts per preserved ledger, not fresh budgets per terminal launch. An approved increase uses `--amend-budgets` with the same unconsumed run ID; never delete ledgers/state. `--uncapped` disables the local credit ceiling only; provider-side caps/funds still apply.

## Track and return results

Inspect `refill-report-elena-izmir-01.json`, `refill-events-elena-izmir-01.jsonl`, worker `refill-console.log` files and the quality report inside the queue. Keep diagnostics private. Controller reports include worker states, completed/email totals, active runtime, provider observations and recovery stops.

```sh
.venv/bin/python queue_quality.py --directory "$TBB_QUEUE"
```

Record the Git commit (`git rev-parse HEAD`), start/end times and timezone, active duration, new completed profiles, profiles/minute, profiles with email, unique email addresses, fill rate, pending/review states, CAPTCHA attempts, challenges/reconnects and stop/resume issues. Distinguish verified source blanks/invalid emails from unknown/extraction failures. Shared-key credit deltas overlap other users: send timestamped observations to Michael; do not add the four Macs' deltas together.

After stopping cleanly, return the **entire queue directory** privately with `RESULTS.md` and the quality report, including discovery, all four worker databases, ownership, WAL files if present, run state and solver ledgers. A CSV alone cannot resume. Exclude provider configuration files. Never upload collected data/credentials to commits, issues or releases. Follow your assigned sequence only after closure/reconciliation or Michael’s explicit deferred-closure instruction, with the paid runtime agreed. Ownership transfers require updating TEAM.md. National completeness remains unverified.
