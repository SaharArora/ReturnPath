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
