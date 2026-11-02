# Turkey / TBB lawyer scraper

Private team source for the TBB directory scraper. Runs four local browser slots on one exclusively assigned bar, with retained-form searches, two-profile detail overlap, durable queue ownership, automatic discovery refill and checkpoint/resume.

**Team:** see [TEAM.md](TEAM.md). Elena starts with [ELENA.md](ELENA.md); Pari with [PARI.md](PARI.md). **Giovanni:** start with [GIOVANNI.md](GIOVANNI.md). Keep your existing Istanbul queue. This repository contains code, synthetic test fixtures and instructions; it deliberately contains **no collected contacts, production checkpoints or credentials**. Cloning code does not download or recreate your saved progress.

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

## Limits and operational rules

- Michael owns Ankara **6**; Giovanni Istanbul **34**; Elena İzmir **35**; Pari Bursa **16**. See TEAM.md for exclusive assignments. Never run duplicate copies of a queue or an older overlapping allocation concurrently.
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
