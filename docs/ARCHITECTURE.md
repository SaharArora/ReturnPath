# Architecture

Python 3.12, locked pip dependencies, FastAPI server-rendered pages, SQLite journal, independent web/worker/watchdog entry points. `fcntl.flock` ties the single financial executor to the canonical local database path. The dev launcher leaves surviving components running after a child failure; the operator restarts the worker.

`identity.ingest` journals a contact before bounded interpretation. `interpreter.Interpretation` rejects extra authority fields and ungrounded references. `identity.issue/confirm` binds a short-lived hashed nonce to contact/case/refund-status capability. GET never consumes it; POST requires a session CSRF token. Trusted recipient comes from the seeded merchant record.

`policy.decide` is a pure fixed policy. `worker.tick` observes provider state before effects, persists immutable operation parameters/key and first attempt before POST, and re-observes before notification. Unknown write outcomes retain the same operation/key. The read path continues on holds and cached resolved cases. Outcome mail has a separate durable send marker and reconciles exact sent evidence instead of blindly retrying.

`connected.Connected` uses actual Gmail/Stripe/Slack APIs, without fake fallback. `fake.Fake` persists provider records in a separate database, permits multiple partial refunds, retains idempotent results including synthetic errors and models 24-hour expiry. `warehouse` exposes a protected loopback HTTP simulator endpoint; test-only fixtures may directly supply warehouse state.

`watchdog.inspect` runs without the planner and sends its own alert. `tests/test_core.py::oracle` and process tests inspect external simulator records independently. `oracle.stripe_records` is a separate read-only real TEST payment oracle, not yet exercised. The evidence checker validates recorded consistency, not provider authenticity.


## Resolution playground extension

`resolution.py` snapshots a validated merchant catalog, runs a customer advocate then a merchant representative with separate fixed prompts, validates catalog offer IDs, and stores expiring offers. An explicit customer-session acceptance transaction writes immutable agreement terms. The operator-only simulated executor uses the agreement ID in a separate provider ledger; replay reconciles the same entry. `resolution_web.py` provides session-scoped customer routes and authenticated operator inspection/execution. No customer request or model output supplies a financial amount.

The playground is isolated from the fixed Stripe TEST workflow. Variable agreements do not yet authorize connected refunds. A RUNNING round left by process death stays visibly unresolved; no unbounded retry or automatic restart is claimed. Reflection, public deployment and an expanded connected benchmark are not implemented.
