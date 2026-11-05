# Team operating instructions

Read README.md, TEAM.md, the operator’s named handover (MICHAEL.md, GIOVANNI.md, ELENA.md or PARI.md) and RELEASE.json. This repository is code-only. Actual credentials, checkpoints, contacts and runtime reports belong outside the checkout and must not be committed or attached to GitHub issues/releases.

Prepare and test offline first. Paid scraping requires the coordinator's explicit launch instruction for the runtime/bar allocation. No install, test or repository automation should start paid work. Never buy credits, enable top-ups, change subscriptions, remove provider caps, add workers or switch bars automatically.

Giovanni owns Istanbul 34; Michael Adana 1 (Ankara 6 preserved with documented exceptions; Antalya 7 paused with unverified coverage); Elena İzmir 35; Pari Bursa 16. Those are the current starting bars, not the full allocations. TEAM.md and each operator’s named file list all 83 exclusive assignments (Michael 21, Giovanni 20, Elena 21, Pari 21). Use only the assigned bar and its durable queue, normally with one bar/four slots total per operator. Michael explicitly authorized Adana 1 + Gaziantep 27 + Kayseri 38 + Şanlıurfa 63 with `--browser-slots 2` on each controller, eight total. Resume each existing queue and inspect the local active-task receipt: it lists both supervising PIDs plus any separately recovered standalone controllers; signal every listed live controller/supervisor to pause the whole group. Other operators retain their previous slot limits. Preserve the entire queue, ownership database, runtime state and solver ledgers. Upgrade into a new directory and stop the old runner first. Do not run old/new copies concurrently.

Uncapped application mode is independent of the provider's dashboard caps. Temporary usage telemetry failure should be recorded, not treated as proof of exhausted credit. Preserve real provider/auth/access failures and bounded recovery limits. Do not manually solve Cloudflare for a claimed autonomous run.

Keep official bar/registration identities. Never fabricate email repairs or merge different profiles by repeated TBB values. Keep unknown/review work visible. Retain national coverage gaps explicitly.

Only a new explicitly authorized run ID grants a new runtime allowance. Identical run IDs/configuration resume remaining time. Budget amendments must be explicit and recorded; never delete elapsed time, solver attempts or no-progress stops to evade limits.

After diagnosis and explicit coordinator authorization, use `--recover-stopped UNIQUE_REPAIR_ID` once to release no-progress stops with preserved history. Reusing that ID is idempotent and cannot reset a new stop. Do not automatically rotate repair IDs. Review recent throughput and stranded backlog; a live controller with zero active browsers is not proof of collection.

Use local/mock tests for code changes. Do not run paid live tests through CI. Record the exact build, setup and source checks that actually ran, including optional browser-test skips. Preserve data before changes, test relevant behavior, and do not silently change the measured production build mid-run.

Michael’s Adana/Gaziantep/Kayseri/Şanlıurfa group was explicitly paused on 5 November for coverage reconciliation. Current assignment is retained; do not restart from historical launch receipts or interpret an eight-slot authorization as a request to run while paused. Check the local active-task pause receipt and MICHAEL.md.

Discovery yield guard: broad-search query completions are not new-profile yield. Default `--discovery-idle-seconds 900` pauses drained queues with `discovery_yield_paused`, preserves pending searches and persists on ordinary resume. Do not rotate run IDs or recovery IDs to evade this checkpoint. Review source coverage before an explicitly authorized recorded recovery; see README.md. The Adana 2409 follow-up is complete; broad scraping remains paused.
