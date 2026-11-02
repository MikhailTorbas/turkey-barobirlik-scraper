# Elena: İzmir, bar 35, four browser slots

Read this file and CLAUDE.md before setup. Your current allocation is **İzmir only (directory bar ID 35)**. Michael owns Ankara 6, Giovanni Istanbul 34, and the other colleague has a different bar. Do not switch bars, add slots or create another copy without coordinating through TEAM.md.

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

After stopping cleanly, return the **entire queue directory** privately with `RESULTS.md` and the quality report, including discovery, all four worker databases, ownership, WAL files if present, run state and solver ledgers. A CSV alone cannot resume. Exclude provider configuration files. Never upload collected data/credentials to commits, issues or releases. Do not automatically pick another bar; Michael reconciles coverage and assigns the next one. National completeness remains unverified.
