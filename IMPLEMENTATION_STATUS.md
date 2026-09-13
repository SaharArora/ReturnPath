## Core bridge and recording checkpoint

Accepted offers now connect to the existing Stripe TEST worker through a separate immutable agreement journal. Fresh mailbox confirmation and required warehouse acceptance gate payment; original $30 case untouched. Original and agreement journals share one worker ownership lock. Operator and customer pages show connected status, dynamic notification amounts and inspection links. Independent `make agreement-oracle` added.

Prepared the user's already accepted order 7201: $120 TEST payment, $120 approved full-return refund. Verification email submitted. No new refund had been attempted at preparation; mailbox confirmation and simulated warehouse acceptance were pending. Do not call this connected refund completion or the required original $30 crash experiment.

Added a README-linked SVG workflow visual and proposed two-minute narration (not a transcript). Visual was rendered and inspected locally. Browser local-file navigation was blocked, so no local-file browser inspection is claimed.

## Core connection implementation plan

Preserve existing completed case and baseline constraints. Add a separate agreement execution journal using the existing worker/reconciliation/notification machinery; copy immutable accepted terms into it. Require a fresh trusted-address confirmation, explicit TEST payment preparation and operator-simulated return receipt when needed. Enforce unique merchant order binding, one worker lock across both journals, complete refund reads and fixed operation parameters. Verify fake/SDK failure cases before connected execution.

## README reliability clarification

Removed hosting and demo-status prose from README at user request; their truthful status remains in the submission manifest and implementation records. Added sourced product-scope comparison with Poke/Instinct, grounding sources, save-before-write, bounded retry, provider reconciliation, uncertainty and separate watchdog/restart explanations. Explicitly distinguished measured local behavior from untested distributed scaling and incomplete offer-to-Stripe integration. No new reliability or competitor-performance result is claimed.

## Current hosting decision

User selected free-only hosting; no paid Render resources authorized or provisioned. README simplified to the five requested sections, with reasons for design choices and explicit unfinished work. Repository visibility was independently checked as PUBLIC after the user changed it; older PRIVATE statements below describe historical checks. Free hosting requires adapting persistent storage; no Vercel compatibility or deployment is claimed.

## Hosting and natural-language checkpoint

User authorized hosting preparation; paid Render provisioning awaits budget/account confirmation. Added isolated hosted app factory, HTTPS cookies, exact host checks, financial/messaging credential rejection, no connected routes, persistent-disk blueprint and setup guide. No hosted URL exists yet.

Resolution prompt revision v2 accepts ordinary language and typos; bounded conversation history now supports short clarification replies. Old requests cannot silently change prompt revision. The deterministic stub remains a labeled offline control. Variable agreement-to-Stripe execution remains unfinished; this checkpoint does not claim that connection.

# Current checkpoint — expanded resolution workspace

This checkpoint supersedes earlier connectivity statements below.

- Ordinary connected run independently verified against Gmail, Stripe TEST and Slack in evidence/connected-ordinary-run.json. Exactly one $30 refund; connected crash NOT_RUN. Gmail supplied Message-ID not preserved; unknown-send recovery unverified.
- Two model roles, configurable offers, three-round bound, customer/operator views, immutable agreements and separate simulated refund ledger implemented. No variable-amount Stripe execution.
- Live-model smoke: 3/3 scenarios; deterministic baseline: 30/30. Full tests: 75 passed, two dependency warnings. These are bounded results, not general reliability guarantees.
- Browser verified localhost:8001/playground renders live-model/simulated-payment labels and two purchases.
- README contains all five required sections. Video, public deployment, expanded fault benchmark and connected crash remain unfinished.

# Implementation status

Existing `~/testingxd` checkout retained on `main`; no unrelated changes were present at start. Origin remains `https://github.com/SaharArora/testingxd`. GitHub API verified `PRIVATE`. Initial commit was `4aaa358`; first implementation checkpoint `03500d0`. No visibility/remote changes.

| Milestone | Implemented | Actual verification | Remaining blocker/limitation |
|---|---|---|---|
| M0 | Python 3.12 `.venv`, hash lock, explicit external config, private init/password hashing, Gmail loopback OAuth, per-service doctor, single checklist | `make setup` passed; doctor and auth-gmail fail safely on missing configuration; setup tests pass | Operator must create/configure accounts and consent locally |
| M1 | Fixed-amount pure guard, immutable SQLite operation, exact scoped verification, persistent provider simulator, protected UI | Offline tests and real-process loopback/login/case/worker/watchdog smoke passed | Prototype, single host; fixture-preverified local seed is labeled |
| M1.5/M3 | Actual Gmail/model/Stripe TEST/Slack adapter code, bounded clarification, TEST seed, complete SDK pagination, read-only independent Stripe oracle | Isolated actual-SDK transport tests passed; real service actions NOT_RUN | Missing Gmail/Stripe/Slack/model private configuration |
| M2 | Reconciliation, same-key retry bounds, notification uncertainty, independent watchdog, SIGKILL boundary, duplicate-contact recovery | `make demo` passes raw provider-state assertions; named tests include actual F05/F08/F26 subprocess behavior | Simulators are not real services; no universal safety/recovery proof |
| M4 | Fixed interpreter prompt/schema and synthetic live-eval fixtures; searchable guide | Boundary/stub tests run; live model NOT_RUN | Live model configuration and actual recording missing; voice deferred |
| M5 | README/guide/manifest, actual report, consistency/readiness gate, allowlisted exporter, provenance, fresh-context review | `make lint`, `make eval`, `make review-check`; `make submission-check` intentionally BLOCKED | Connected same-run and crash evidence, genuine video/transcript/captions, organizer access/eligibility |

## Exact current evidence

Selected measured report: [offline JSON](evidence/offline-evaluation.json), [readable result](evidence/offline-evaluation.md). Counts are generated from actual pytest runs; do not infer an exhaustive scenario-recovery rate. [Local demo trace](evidence/local-demo.json) records actual SIGKILL, second contact, independently running watchdog, explicit harness restart, and one 3000-cent refund with one simulator outcome mail. No connected actions have been executed. Two dependency deprecation warnings remain.

One independent fresh-context read-only review ran 40 tests at its earlier snapshot and found real gaps; see [review record](docs/REVIEW_FINDINGS.md). Builder fixes and later regression tests are not a second independent review. SDK transport tests caught and corrected synchronous-client and metadata API mismatches; a temporary two-test failure was fixed without weakening assertions.

## Startup

`cd ~/testingxd`; `make setup`; `make init-config`; `make seed`; `make dev`. Open `http://127.0.0.1:8000/login`. Configure providers only in `~/.config/returnpath/returnpath.env`; follow [one checklist](docs/CREDENTIALS_CHECKLIST.md). Run `make auth-gmail`, then `make doctor SERVICE=gmail`, `slack`, `stripe`, `model` separately. Never paste secrets into chat.

For connected use, intentionally set connected-test/write enablement in the private config, run `make connected-seed` once, then `make connected-dev`. Send the controlled email and explicitly confirm the emailed link. Restart using `make worker`, never reseed. A second worker is rejected. The watchdog detects/alerts and does not restart workers. `make stripe-oracle` independently retrieves TEST payment records after a connected run. Disable writes afterward.

## Remaining limitations and gates

No actual Gmail intake/send, Stripe TEST refund/retrieval, Slack handoff, live-model response, connected crash run or genuine recording was available. These are hard blockers to CONNECTED_WORKFLOW_VERIFIED and SUBMISSION_READY. Full v3 acceptance remains unclaimed: named tests cover declared cases, not every fault combination; per-state daily caps are not account-wide caps; live Retry-After/notification correlation behavior needs actual contract validation; watchdog is on the same host/storage. No voice, production/public deployment or automatic process restart.

Private visibility: verified through GitHub API. Push: succeeded to existing origin/main through `39e5f38` (implementation `02ae815`); this documentation checkpoint follows. Organizer private-source access/advance-work eligibility: not verified. No synthetic transcript or self-awarded score was created.

Final selected evaluation: 66 tests, 0 failures, 0 errors, 0 skipped (generated from the selected report). Lint, local demo, offline review consistency and real-process UI smoke passed. submission-check, live-model-eval and connected-smoke returned BLOCKED/nonzero as expected.

## Preview accessibility fix

The previous preview was unreachable because no server remained running; the private GitHub checklist link returned 404 in the signed-out in-app browser. Added a loopback setup-only page when operator config is absent, plus locally served checklist and authorization instructions. Verified both rendered in the actual in-app browser. Protected app routes remain inaccessible before operator setup. `make web` is the setup preview command; operator creates their password privately with `make init-config`.

Operator password setup completed by user. Activated protected local web/worker/watchdog; created initial local fixture only because no case records existed. Login form verified in browser. Local simulation reached RESOLVED; no connected services were invoked. Documentation routes now remain accessible after setup.


## Connected intake diagnosis — September 13

Plan: reproduce silent interpretation failures, fix MIME whitespace handling with regression tests, verify actual model interpretation, then resume controlled intake without resetting financial state.

Two Gmail contacts were present with three failed interpretation attempts each and no verification or financial operations. Read-only Gmail retrieval plus a live model diagnostic reproduced `Ungrounded model evidence`: the model flattened MIME line wrapping in a quoted span. Canonicalize whitespace before both inference and exact validation; retain reference grounding and size limits. Added secret-free intake, interpretation and verification-submission console events. Existing exhausted retry budgets remain preserved; they are not silently reset. Connected completion and crash evidence remain unverified.

Verification for this fix: `make lint` passed; `make test` passed 68 tests (two dependency deprecation warnings). Three explicit live-model diagnostic calls on the previously failing ingested email passed after normalization; these probes did not change contact retry budgets or send mail. Running processes still require restart to load the fix. No connected workflow completion is claimed.

## Expanded product milestone plan

User-authorized scope revision: build two bounded agents, merchant-configured resolution choices, durable accepted agreements and one application with customer and operator perspectives. Keep the original fixed-payment execution/crash fixture intact as a regression. No voice, marketplace or cross-case learning.

1. Correct Slack URL readback and test unchanged-update suppression.
2. Add isolated resolution storage, validated merchant offer catalog, two role-specific agents, bounded rounds and immutable acceptance.
3. Add customer playground and operator inspection with scoped access, truthful simulator/live-model labels.
4. Run safety tests and a repeatable negotiation benchmark; consolidate judge requirements in README.
5. Deployment and actual expanded connected execution remain gates until verified; no invented video or connected benchmark results.

Hosting/language verification: 77 offline tests and lint passed; 4/4 live-language smoke scenarios passed, including two clarification follow-ups. No hosted service provisioned. Restarted only the playground process on port 8001; existing Stripe records unchanged.
