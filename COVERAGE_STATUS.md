# Coverage review — 6 November 2026

Michael's Adana (1), Gaziantep (27), Kayseri (38) and Şanlıurfa (63) queues are **paused after low-yield discovery**. Existing ownership is unchanged. The local supervisor has exited; its recorded PID is historical.

| Bar | Completed profiles | Pending discovery searches |
|---|---:|---:|
| Adana | 5,193 | 786 |
| Gaziantep | 3,741 | 1,276 |
| Kayseri | 3,304 | 1,348 |
| Şanlıurfa | 2,469 | 1,339 |
| Total | 14,707 | 4,749 |

All discovered detail jobs are complete. This is not proof that all people have been discovered.

## Findings

- Each saved queue contains all 2,048 expected two-letter searches across both name fields. No completed query in these four discovery checkpoints was capped. There is no missing seed/subdivision job to repair in these checkpoints.
- Every currently observed identity has a name covered by the configured seed alphabet. This says nothing about unseen names, current source changes, or the pending queries.
- A separate bounded hosted-browser pilot compared common/diverse pending name searches with the existing alphabetical order. Eight searches succeeded before a ninth search was rejected; none discovered a new identity. Two follow-up searches repeated earlier rejected criteria successfully, again with no new identities. The comparison did not establish an improved discovery policy, and its partial result is not extrapolated to all bars.
- Successful previously rejected searches show that those criteria can work. The exact cause of the transient rejection was not captured in that first pilot. Retained-form rejection errors now include a bounded, redacted source alert reason for future diagnosis; errors are still rejected, never counted as verified empty results.
- All four production discovery checkpoint hashes were unchanged by the probes. Probe responses and receipts remain local; saved run IDs, runtime, solver ledgers, ownership and contacts were not reset.

## What remains

A complete current official roster/export, or completion of a documented conditional search strategy, is still required to establish coverage. The genuinely missing identity count is unknown. Do not report these bars as exhaustive or remove pending queries.

The [Adana roster page](https://www.adanabarosu.org.tr/baro-levhasi) uses TBB. The [Gaziantep](https://www.gaziantepbarosu.org.tr/AvukatArama), [Kayseri](https://www.kayseribarosu.org.tr/AvukatArama) and [Şanlıurfa](https://www.sanliurfabarosu.org.tr/AvukatArama) roster routes embed TBB. Gaziantep also publishes an E-LEVHA Drive link, but no accessible export was obtained from its view/preview/download routes. This does not establish that the document is unavailable to an authorized bar representative.

The Kayseri/Şanlıurfa new-license news pages are partial announcements, not full rosters. They are not imported as exhaustive identity sources. The named lawyer in the checked Şanlıurfa admission announcement was already saved.

For each bar, obtain an official dated CSV/XLSX/PDF or public download with local bar registration number, full name, category/status, total count and scope (all districts; inclusion/exclusion of trainees, transfers, deceased/deregistered lawyers). National identity numbers and birth dates are unnecessary. An accessible official link is sufficient; account credentials are unnecessary. Gaziantep can provide an accessible copy of its published E-LEVHA and confirm its date/scope. ZenRows support can help transport failures; it cannot establish the missing official roster universe.

Then use `roster_reconciliation.py` to retain source evidence, compare bar+registration identities, queue only missing official IDs, and investigate name conflicts. Preserve nonmatches and source scope/date differences. A complete official list at one date does not prove a later changing directory is exhaustive.

No request has been sent to any bar. These four queues remain paused pending a reviewed strategy; no automatic recovery follows from this report. The subsequent 26/54/61/52 group also paused after low yield, with saved data and unverified coverage. The 58/32/64/68 group has since also paused with unverified coverage; Aksaray has 480 saved profiles against a dated 2025 baseline of 558. That 51/66/70/78 group has also stopped with coverage unverified. The current batch is new bars 30/36/74 plus one reviewed saved-queue recovery of 78; see MICHAEL.md. The 900-second discovery-yield guard remains enabled.
