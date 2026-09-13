# ReturnPath evidence guide

## Job and current status

A merchant has approved a partial return refund, but the customer still asks where it is. ReturnPath separates understanding that request from permission to move money. The demonstration fixture is deliberately a $100 charge with a $30 approved refund: a second erroneous $30 refund would still fit within the provider's charge ceiling. The intended useful result is one verified refund, a truthful customer update, and an actionable operational handoff.

The local product now includes a two-agent resolution playground with configurable merchant offers, explicit acceptance, immutable agreements, customer/operator views and simulated settlement. Separately, [independent provider readback](evidence/connected-ordinary-run.json) verifies the original ordinary Gmail/Stripe TEST/Slack run. The connected crash experiment has not run. [The manifest](submission.json) records three verified service roles but remains incomplete for submission.

## Three-service sequence and AI role

The implemented connected path in [connected.py](src/returnpath/connected.py) polls the allowlisted Gmail query, reads a controlled customer's plain-text message, and persists its provider event identity. [identity.ingest](src/returnpath/identity.py) calls the [bounded interpreter](src/returnpath/interpreter.py). Its fixed schema only extracts intent/references or asks for an order reference. Extra authority fields and fabricated source spans are rejected. Offline tests use a deterministic stub. The connected intake used the configured model; a separate two-agent smoke ran three synthetic scenarios successfully. Neither result establishes broad model accuracy.

A candidate order match is not authentication. The verification message goes to the address in the trusted merchant record. A random challenge is scoped to contact/case/capability, stored as a digest, expires, and requires explicit CSRF-protected POST confirmation. A new contact does not inherit another contact's verification. The model cannot change the $30 amount, original destination, case approval or operation key.

After verified prerequisites, the worker creates/reconciles a Stripe TEST refund, submits a deterministic Gmail outcome message, then posts or updates and reads back a private Slack case summary. Unknown/conflicting prerequisites receive an actionable handoff. Actual ordinary-run service effects were independently retrieved; connected crash recovery remains unverified. The model endpoint and local warehouse HTTP simulator do not count as external apps.

## Crash experiment and independent result

[make demo](scripts/demo.py) actually launches processes and records [this local trace](evidence/local-demo.json). A named boundary stops the worker after the separate simulator database commits success and before local completion recording. The harness sends SIGKILL, persists a second contact, observes an independently running watchdog alert, and explicitly restarts the worker. It never reseeds during recovery.

The final assertion reads provider rows independently of the application's success label: exactly one refund, 3000 cents total, and one outcome mail. [Process tests](tests/test_process.py) additionally attempt two financial workers and check OS-lock rejection. [The duplicate oracle test](tests/test_core.py) intentionally issues a second partial refund under a different key and proves the oracle fails. This demonstrates the intended bug is detectable; it is not a proof covering every execution or an actual Stripe outage.

## Reproduce and inspect

Use Python 3.12, run `make setup`, then `make test`, `make demo`, and `make eval`. Setup installs hash-locked dependencies into `.venv`; offline execution ignores Mac credentials and blocks non-loopback network sockets. For the protected dashboard run `make init-config`, `make seed`, and `make dev`; log in at localhost using the password chosen privately. Restart a worker with `make worker`, not seed. The watchdog detects and alerts; it does not automatically restart anything.

The [generated evaluation](evidence/offline-evaluation.json) contains actual pytest nodes, results, durations, commit/dirty state and source/lock/prompt fingerprints. Counts represent tests, not an invented automatic-recovery percentage. `make review-check` validates offline consistency. `make submission-check` intentionally fails on missing connected crash evidence, video/transcript and organizer-approved private access. Hashes detect local inconsistency, not provider authenticity.

## Claim-to-evidence map

| Bounded claim | Category | Implementation / test / evidence | Status |
|---|---|---|---|
| C01 Three real services in one useful run | Technical execution/usefulness | [Adapter](src/returnpath/connected.py), [manifest](submission.json) | NOT_TESTED |
| C02 Post-success kill preserves one $30 refund | Reliability | [Worker](src/returnpath/worker.py), [process tests](tests/test_process.py), [local trace](evidence/local-demo.json) | SUPPORTED locally |
| C03 Distinct contacts retain one operation | Reliability | [Journal](src/returnpath/storage.py), [core tests](tests/test_core.py) | SUPPORTED locally |
| C04 Unknown facts do not authorize POST | Reliability | [Pure policy](src/returnpath/policy.py), [review regression tests](tests/test_review_fixes.py) | SUPPORTED within tests |
| C05 Named live model interprets input | AI contribution | [Interpreter](src/returnpath/interpreter.py), [manifest](submission.json) | NOT_TESTED |
| C06 Independent watchdog detects dead worker | Reliability | [Watchdog](src/returnpath/watchdog.py), [process tests](tests/test_process.py), [trace](evidence/local-demo.json) | SUPPORTED locally |

## Limits, provenance and access

Read the [reliability brief](docs/RELIABILITY_BRIEF.md), [fresh-context findings](docs/REVIEW_FINDINGS.md), and [provenance](docs/PROVENANCE.md). The prototype assumes surviving trusted records, one host/executor, truthful eventual provider observations and no competing external financial writer. It does not guarantee email delivery, bank settlement, distributed exactly-once behavior or arbitrary-state recovery. Operational limits remain incomplete. Voice is deferred. No genuine video was recorded, so no transcript/captions were invented. Private visibility was verified; organizer access/eligibility remains unresolved. AI-assisted initial review is a planning assumption, not knowledge of a platform/model or a request for a score.


## Customer and merchant agents

Run `RP_RESOLUTION_MODEL=live make playground` with private model configuration and open localhost:8001/playground. A merchant catalog supplies immutable offer terms, including different refund amounts. The advocate interprets the customer preference; the merchant agent responds under the same catalog authority. Unknown offer IDs and extra authority fields are rejected. Both use fixed prompts, and neither can accept on the customer's behalf. Explicit acceptance binds exact expiring terms to the session owner. Operator routes require password authentication; changing sessions cannot grant access to another customer's agreement.

The playground payment provider is a separate simulated ledger. Agreement identity deduplicates replay and the operator may supply explicitly simulated warehouse acceptance. This path is not yet connected to Stripe, Gmail or Slack; the original fixed $30 regression carries that evidence. Negotiation does not establish identity or merchant approval. A round interrupted during model execution remains unresolved for operator inspection. Reflection and automatic restart are not implemented.

[Resolution tests](tests/test_resolution.py) exercise unauthorized offers, expiry, supersession, cross-customer access, CSRF and replay. [Live smoke results](evidence/resolution-live-evaluation.json) report three scenarios with one trial each. Repeating the deterministic baseline is a control check, not a stochastic consistency claim. The current interface is local; there is no public deployment URL. The README contains all five requested judge sections and explicitly marks the missing video.
