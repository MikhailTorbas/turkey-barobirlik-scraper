# Team operating instructions

Read README.md, TEAM.md, the operator’s named handover (MICHAEL.md, GIOVANNI.md, ELENA.md or PARI.md) and RELEASE.json. This repository is code-only. Actual credentials, checkpoints, contacts and runtime reports belong outside the checkout and must not be committed or attached to GitHub issues/releases.

Prepare and test offline first. Paid scraping requires the coordinator's explicit launch instruction for the runtime/bar allocation. No install, test or repository automation should start paid work. Never buy credits, enable top-ups, change subscriptions, remove provider caps, add workers or switch bars automatically.

Giovanni owns Istanbul 34; Elena İzmir 35; Pari Bursa 16. These are starting bars, not their full allocations. TEAM.md and the named handovers list all 83 exclusive assignments. Michael's current explicitly authorized group is Niğde 51, Yozgat 66, Karaman 70 and Karabük 78, two live slots each/eight maximum including discovery. Adana 1, Gaziantep 27, Kayseri 38, Şanlıurfa 63, Eskişehir 26, Sakarya 54, Trabzon 61, Ordu 52, Sivas 58, Isparta 32, Uşak 64 and Aksaray 68 remain paused with coverage unverified; Ankara/Antalya remain saved with documented exceptions. Preserve every durable queue, ownership database, runtime state and solver ledger. Check the local active-task receipt for the single current supervisor. No old pair/standalone helpers alongside it. Other operators retain their previous slot limits.

Uncapped application mode is independent of the provider's dashboard caps. Temporary usage telemetry failure should be recorded, not treated as proof of exhausted credit. Preserve real provider/auth/access failures and bounded recovery limits. Do not manually solve Cloudflare for a claimed autonomous run.

Keep official bar/registration identities. Never fabricate email repairs or merge different profiles by repeated TBB values. Keep unknown/review work visible. Retain national coverage gaps explicitly.

Only a new explicitly authorized run ID grants a new runtime allowance. Identical run IDs/configuration resume remaining time. Budget amendments must be explicit and recorded; never delete elapsed time, solver attempts or no-progress stops to evade limits.

After diagnosis and explicit coordinator authorization, use `--recover-stopped UNIQUE_REPAIR_ID` once to release no-progress stops with preserved history. Reusing that ID is idempotent and cannot reset a new stop. Do not automatically rotate repair IDs. Review recent throughput and stranded backlog; a live controller with zero active browsers is not proof of collection.

Use local/mock tests for code changes. Do not run paid live tests through CI. Record the exact build, setup and source checks that actually ran, including optional browser-test skips. Preserve data before changes, test relevant behavior, and do not silently change the measured production build mid-run.

Discovery yield guard: broad-search query completions are not new-profile yield. Default `--discovery-idle-seconds 900` pauses drained queues with `discovery_yield_paused`, preserves pending searches and persists on ordinary resume. Do not rotate run IDs or recovery IDs to evade this checkpoint. Review source coverage before explicitly authorized recorded recovery; see README.md.

Latest explicit launch, 6 November: Michael authorized the next four exclusively assigned bars (51/66/70/78). Fresh queues use the above guard and a seven-day safety backstop (`--seconds 604800`), replacing the eight-hour cutoff; one local `work/run_fourth_four_bars.py` supervisor controls all four at two slots each. The active-task receipt identifies its verified PID/status/queue paths. No automated recovery or rollover to additional bars. The previous twelve bars (1/27/38/63, 26/54/61/52 and 58/32/64/68) remain stopped, with all saved data and coverage gaps intact. Read MICHAEL.md and COVERAGE_STATUS.md.
