# Turkey / TBB lawyer scraper

Private team source for the TBB directory scraper. Runs four local browser slots on one exclusively assigned bar, with retained-form searches, two-profile detail overlap, durable queue ownership, automatic discovery refill and checkpoint/resume.

**Team:** see [TEAM.md](TEAM.md). Michael starts with [MICHAEL.md](MICHAEL.md); Elena with [ELENA.md](ELENA.md); Pari with [PARI.md](PARI.md). **Giovanni:** start with [GIOVANNI.md](GIOVANNI.md). Keep your existing Istanbul queue. This repository contains code, synthetic test fixtures and instructions; it deliberately contains **no collected contacts, production checkpoints or credentials**. Cloning code does not download or recreate your saved progress.

## Install

Use macOS/Linux and Python 3.10+; the validated release environment uses Python 3.14. Native Windows is not validated. Hosted mode uses ZenRows Browser Sessions and does not need local Chromium.

```sh
git clone https://github.com/MikhailTorbas/turkey-barobirlik-scraper.git
cd turkey-barobirlik-scraper
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.lock.txt
.venv/bin/python -m unittest discover -s tests
```

Private repository access requires your own GitHub login. Optional local-browser tests are skipped by default. To run the full suite locally:

```sh
.venv/bin/python -m playwright install chromium
TBB_TEST_BROWSER=1 .venv/bin/python -m unittest discover -s tests
```

Tests use local servers, mocked providers and synthetic identities/contact data. They do not submit paid requests to TBB, ZenRows or CapSolver.

## Private configuration

Keep credentials outside the checkout, following `zenrows.example.json` and `capsolver.example.json`. Use the company's approved private channel. Set paths to existing owner-only files; do not put keys in command arguments or chat:

```sh
export TBB_CONNECTION_FILE=/absolute/private/zenrows.local.json
export TBB_SOLVER_FILE=/absolute/private/capsolver.local.json
chmod 600 "$TBB_CONNECTION_FILE" "$TBB_SOLVER_FILE"
```

## New colleagues: fresh queue

Follow the named handovers above. `prepare_queue.py --directory /absolute/new/queue --baro 35 --owner Elena` initializes a new four-slot single-bar queue offline. It refuses existing destinations and queues inside this checkout. Resume existing queues rather than initializing again. Use only the IDs assigned in TEAM.md.

## Existing queue: upgrade and continue

Stop the old runner before upgrading. Keep the entire queue, including ownership/discovery/worker checkpoints, state, solver ledgers and WAL files. Write into a **new directory outside this repository**:

```sh
.venv/bin/python upgrade_queue.py --source /absolute/existing/queue --destination /absolute/new-production/queue
.venv/bin/python queue_quality.py --directory /absolute/new-production/queue
```

The upgrade preserves original files and completion counts, reparses recoverable emails from stored raw evidence, queues eligible name-search failures for bounded exact-registration recovery, and regenerates exports. It never resets solver ledgers or elapsed runtime. Do not run both copies afterward.

Once Michael authorizes the next runtime allowance:

```sh
caffeinate -is .venv/bin/python refill_runner.py \
  --directory /absolute/new-production/queue \
  --seconds 28800 --uncapped \
  --solver-tasks 250 --discovery-solver-tasks 100 \
  --run-id production-01
```

On Linux omit `caffeinate -is`. This command starts paid collection. It is an eight-hour allowance, not an assertion that a bar will be finished in eight hours. If the prior run ID already consumed its time, it remains exhausted; a new ID explicitly starts a new authorized allowance while keeping completed work and consumed solver attempts.

Repeat the **same command, directory and run ID** to resume that allowance. For an explicit increase of solver limits or change to uncapped mode within an existing unconsumed allowance, add `--amend-budgets` once. This records the amendment and preserves elapsed time; it does not reset attempts or grant more time.

After investigating a `three_phases_without_progress` stop, an explicitly authorized recovery adds `--recover-stopped repair-2026-11-04` to the same launch command. The ID is recorded once: reusing it cannot repeatedly release new stops. Old failure states are saved in `operator_recoveries`; elapsed runtime, completed jobs, ownership and solver attempts remain intact. Solver-limit stops require an approved budget amendment instead. Never delete state/ledgers or repeatedly invent recovery IDs to bypass a persistent access problem.

Discovery backpressure excludes jobs stranded on stopped workers. Reports distinguish `runnable_ready` from `stranded_ready`, show recent throughput over up to five minutes alongside the lifetime average, and identify zero-browser waiting states. An unexplained inability to launch runnable work stops as `scheduler_no_launch` after two minutes; this is a fault to inspect, not completion.

## Limits and operational rules

- Michael owns Adana **1**; Giovanni Istanbul **34**; Elena İzmir **35**; Pari Bursa **16**. These are current starting bars; see TEAM.md and each named handover for all 83 exclusive assignments (21/20/21/21). Never run duplicate copies of a queue or an older overlapping allocation concurrently.
- Discovery temporarily uses one of four slots; the other three can keep checking details. There is no fifth discovery browser. At sufficient backlog, all four process details.
- `--uncapped` removes the **application** ceiling and exact-cap requirement. It does not remove provider dashboard caps, fund an account, purchase top-ups or change subscriptions. Provider limits still apply. Account-wide usage telemetry failures are logged and retried without stopping healthy uncapped collection; real auth/funding errors remain explicit. Capped mode is available with `--credit-cap` and without `--uncapped`.
- Solver ceilings are **lifetime attempts per existing ledger**, not additional attempts. Keep them funded and choose allowances for the approved duration; do not delete ledgers or loop-restart blocked work.
- Keep the Mac powered, lid open and connected. Ctrl-C once to pause; allow about two minutes for shutdown/export/billing observations. Resume rather than rebuilding a queue after a shutdown.
- Use official `(bar_association_id, bar_registration_number)` keys. Repeated TBB values are source-quality flags, not automatic merge keys. Source-not-found and extraction failures are not blank emails.
- National completeness is **not verified**. Pending queries are overlapping searches, not a count of missing lawyers. Retain capped partitions, pending/review work and independent roster discrepancies in reports.

## Reports and export

Controller status, state and phase events are `refill-report-*`, `refill-state-*` and `refill-events-*` inside the queue. Monitor completions/minute, refill, email evidence, pending/review totals, retries, solver attempts and shutdowns. Quality inspection and a new-file completion export:

```sh
.venv/bin/python queue_quality.py --directory /absolute/new-production/queue
.venv/bin/python queue_quality.py --directory /absolute/new-production/queue \
  --export-completed /absolute/new-export/completed.jsonl
```

The export refuses to overwrite an existing file. Worker exports contain this allocation's completions; retain/merge the earlier completed master separately. Exports are not resumable queues.

Shared account/key credit observations include other simultaneous users and delayed billing. **Do not sum overlapping Mac deltas.** Use one coordinated company before/after interval and disclose other usage. Changing counter scope or a billing-period reset prevents naive subtraction.

## Validation

See [VALIDATION.md](VALIDATION.md) and `RELEASE.json`. This source release includes the November operational fixes. No repository workflow or install command starts production scraping automatically.

## Tail-stage recovery and live refill

The controller reads committed discovery rows through read-only SQLite WAL snapshots while the discovery child is alive. It writes only idle worker checkpoints and reserves every identity in the existing ownership registry. New jobs need not wait for an entire discovery phase to exit. Uncommitted producer rows are never dispatched. Empty healthy slots can request discovery even when another worker holds a large backlog.

A request that fails while its sibling completes, with the original listing/form still alive and online, is deferred to bounded exact-registration recovery. It is not treated as browser expiry, a blank email or a completed profile. Full disconnects, verification responses and all-failed batches still use bounded session/access recovery. Exact-recovery attempt history survives pause/resume.

For queues with a saved independently sourced official roster, `--roster-lookups 30` prioritizes at most 30 missing roster identities per discovery phase, using the existing runtime and solver limits. This is optional (default 0), and policy changes are recorded in state. Roster candidates are dated observations, not proof of current TBB membership. Actual exact responses alone determine whether the site lists them; no missing profile is fabricated. Ordinary discovery remains queued afterward.

## Isolated roster-only audits

`turkey_scraper.py --roster-only --baro ID --max-roster-lookups 100 ...` operates on an explicitly prepared audit checkpoint with saved source candidates. It does not seed, submit or complete ordinary name-discovery queries. Do not change an existing ordinary checkpoint into this mode: the configuration guard rejects mixed use. Preserve the audit's assignment manifest, original attempt history and source evidence, and coordinate disjoint IDs before running more than one audit worker. The normal four-slot production command remains unchanged.

A confirmed exact-registration zero-result response is useful verification progress. Unanswered attempts are not progress. Neither counts as a completed profile or a blank email. Finishing a roster audit does not establish exhaustive current national/bar coverage; dated roster scope, source-name differences and unresolved identities remain explicit.

## Two bars sharing one Mac (experimental)

`refill_runner.py --browser-slots 2` limits that controller to **two live browser children including discovery**, while retaining all four durable worker checkpoints. Two exclusively owned bars may run from separate queues/controllers at two slots each, for at most four browsers total. The default remains four; do not launch two default controllers and assume the combined limit is four. Each queue still has its own ownership lease, run ID, runtime and solver ledgers. A slot-count change is recorded in operating-policy history without resetting those counters. All four saved detail queues remain eligible at reduced concurrency.

Pause the old four-slot run and verify all child processes have stopped before starting the two-slot pair. Resume an existing queue with its recorded command plus `--browser-slots 2`; initialize only a genuinely new bar. Do not run two controllers against the same queue. Shared-account credit deltas are overlapping account observations, not per-controller charges. Keep the current named bar ownership and paid-launch authorization rules. The initial operational comparison uses Adana's discovery tail and a fresh Gaziantep queue, so it does not establish a same-record speedup or sustained nationwide reliability.

## Stop low-yield discovery without losing coverage work

The controller now defaults to `--discovery-idle-seconds 900`. Completing overlapping search queries does **not** extend this window. New discovered identities or verified exact-roster checks do. Once known detail work and the unowned buffer are drained, 15 active minutes without such yield stops the controller with `discovery_yield_paused`.

This is a checkpoint for coverage reconciliation, not a claim that the bar is complete. Every pending discovery query, profile, solver attempt and elapsed runtime remains saved. Repeating the same launch command preserves this pause and starts no browser children. After reviewing the remainder, the coordinator can explicitly authorize `--recover-stopped UNIQUE_REVIEW_ID` once to open another observation window with the same run ID; it does not reset runtime or solver ledgers. A repeated recovery ID cannot reset a new pause. Changing a slot count or ordinary policy settings does not clear a recorded yield pause. `--discovery-idle-seconds 0` disables the guard only before it pauses; use it only with explicit authorization for the intended audit.

Reports expose `discovered_identities`, `discovery_idle_seconds`, `discovery_idle_limit_seconds` and `discovery_yield_pause`. A verified zero-result exact-roster check is useful audit work and extends the window; a blank HTTP response or a completed broad search is not new identity evidence. Source identity/audit counters decreasing raises an integrity error instead of silently resetting the window.
