# Release validation

Version: 2026-11-02 production fixes.

- The original source build passed 156 regression tests, including local Chromium fixtures.
- Targeted live acceptance checked seven matching detail views plus one exact-registration lookup with no result; the latter remained review work.
- Existing completed records were preserved. Stored-source multi-address/annotation repairs and exact-ID recovery were recorded in private upgrade/acceptance receipts.
- Both sampled repeated-TBB pairs were also displayed that way by the source, so the code flags source-quality issues rather than merging different bar registrations.
- Current fixes cover uncapped application mode, resilient usage telemetry, solver-budget amendments, exact-ID recovery, contact parsing, final exports and bounded shutdown.

For publication, DOM fixtures and linked test assertions use synthetic names, contacts and identifiers. Runtime modules remain identical to the validated source; the published test suite is re-run after fixture transformation. No collected dataset or private acceptance records are stored here.

National completeness, unlimited managed-challenge access and larger multi-machine concurrency are not established by these tests. See README.md for the operating constraints.
