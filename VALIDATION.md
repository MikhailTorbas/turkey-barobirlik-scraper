# Release validation

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
