# Release validation

Current validation: **23 November 2026**, code commit `cdb3a24`.

- Full suite: **202 tests run, 169 passed, 33 skipped** (opt-in browser fixtures were not run in this invocation).
- Real ZenRows + CapSolver acceptance: an injected transient search failure recovered in the same browser; 84 listing rows over five pages and two completed profiles with two emails were saved to isolated SQLite. Integrity check passed.
- November 18 acceptance covered fixed and incremental pagination, durable detail jobs and nine distinct completed profiles with four emails.
- Later persistent outer Cloudflare startup blocks remain possible. Session/transport failures do not prove TTL expiry, and HTTP success without a JSON directory response is not a completed query.
- All actual profiles, credentials and diagnostic queues remain outside Git. No production checkpoint, run ID, remaining allowance or provider cap was changed by these checks.
- `RELEASE.json` hashes identify the current runtime source files. Test counts above supersede the historical entries below.

## Verified-session reuse follow-up

Controller commit `d1af388`: **203 tests run, 170 passed, 33 skipped**. The new regression verifies that phase item caps no longer force fresh starts, while the remaining runtime, session TTL, solver limits and provider cap remain enforced. Existing tests retain stopped-role and idempotent recovery behavior.

Three isolated live startup comparisons reached the directory. Two Turkey-routed sessions (direct and homepage-first) each traversed 84 rows and a detail with an email. Default routing reached the form but was not searched after the separate diagnostic solver budget was exhausted. This is not proof of sustained access, reduced production block rates or a four-worker soak test. No production queue or stop was changed.

## Historical validation

Version: 2026-11-02 production fixes.

- The original source build passed 156 regression tests, including local Chromium fixtures.
- Targeted live acceptance checked seven matching detail views plus one exact-registration lookup with no result; the latter remained review work.
- Existing completed records were preserved. Stored-source multi-address/annotation repairs and exact-ID recovery were recorded in private upgrade/acceptance receipts.
- Both sampled repeated-TBB pairs were also displayed that way by the source, so the code flags source-quality issues rather than merging different bar registrations.
- Current fixes cover uncapped application mode, resilient usage telemetry, solver-budget amendments, exact-ID recovery, contact parsing, final exports and bounded shutdown.

For publication, DOM fixtures and linked test assertions use synthetic names, contacts and identifiers. Runtime modules remain identical to the validated source; the published test suite is re-run after fixture transformation. No collected dataset or private acceptance records are stored here.

The team handover update passed **158 tests**, including local Chromium tests. New offline tests cover fresh İzmir/Bursa discovery seeds, bar isolation, first-job dispatch and refusal to overwrite existing queues. No paid provider requests were made by these tests.

National completeness, unlimited managed-challenge access and larger multi-machine concurrency are not established by these tests. See README.md for the operating constraints.

The 4 November controller/solver fixes passed **164 tests**, including local Chromium. Regression coverage reproduces 800 pending jobs stranded on stopped workers and verifies discovery/healthy-worker progress; recorded recovery cannot be reapplied using the same ID. Solver tests verify polling retry uses the same task, uncertain creates are not retried, and HTTP error descriptions/credentials are not exposed. Original queues are backed up before live recovery.

The tail-stage update adds regression coverage for a hanging request beside a successful sibling, same-browser exact-ID recovery, streaming dispatch before discovery exits, uncommitted WAL rows being excluded, and dispatch immediately after discovery exits. A known live pending profile had 87 attempts with zero parsing failures; its retry history was preserved while routing it to exact-ID recovery.

The final slot-placement regression verifies pending detail work starts immediately and discovery uses a different empty slot. The final tail-stage suite contains 169 tests.

The closure update passed **171 tests**, including local Chromium. New checks verify exact not-found responses count as audit progress without creating contacts; roster-only mode leaves ordinary pending queries untouched and submits no broad searches. A separate offline closure-merge test verifies disjoint assignments, preserved completions/attempts and idempotent imports.

The adjustable-browser update passed **174 tests**, including local Chromium and localhost fixture servers. New scheduler tests verify one/two-slot caps include discovery, every pre-existing four-worker queue remains reachable, changing back to four preserves ownership/completions and records policy history, and an invalid slot count starts no children. Default four-slot tests remain unchanged. Live two-bar throughput/cost validation is a separate operational comparison; no speedup is claimed by these offline checks.

Restart-readiness update: **179 tests passed**, including local Chromium fixtures. Five added checks cover broad-search churn versus new identities, useful verified roster absences, counter regressions, idempotent recorded recovery, and a simulated controller that pauses despite successful overlapping searches and refuses to launch new paid children on ordinary resume. The default active-time window is 900 seconds and known pending detail work is drained first. A separate bounded live check completed the saved Adana registration 2409 with one additional solver task; it returned a verified source blank email, not an extraction failure. Exhaustive four-bar coverage remains unverified because validated independent full rosters were not obtained.
