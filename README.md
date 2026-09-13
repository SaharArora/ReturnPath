# ReturnPath

## 01 · Project overview

**ReturnPath helps a customer and merchant agree on a return resolution, then makes the resulting action inspectable.** A customer advocate interprets preferences; a merchant representative proposes an option from a trusted catalog. The customer accepts exact terms before execution. The agents cannot invent refund amounts, change merchant authority or confirm their own success.

One server-rendered application provides a session-scoped **customer workspace** and a password-protected **operator workspace**. The playground supports different purchases and merchant-approved refund amounts, clarification, up to three rounds, expiring offers, immutable accepted agreements, and separately persisted simulated refund records. Configure the catalog in [config/resolutions.json](config/resolutions.json); it is snapshotted when a request starts. The initial catalog includes $24/$120 and $15/$65 choices—not just the original $30 example.

**Two paths are deliberately labeled:**

- **Resolution playground:** two model roles, configurable offers and agreement-bound **simulated payments**. It has no access to the connected financial executor. Use live models explicitly, or a clearly labeled deterministic offline baseline.
- **Connected execution regression:** actual Gmail → model → verified customer contact → $30 Stripe TEST refund on a $100 payment → Gmail outcome → Slack. This fixed amount remains a safety/crash fixture. Variable negotiated agreements are **not yet connected to Stripe**.

This is a single-merchant prototype, not a general marketplace. No voice, cross-case learning or self-modifying policy. The app is currently **local, not publicly deployed**. A guarded [Render deployment configuration](render.yaml) and [exact hosting steps](docs/HOSTING_RENDER.md) are prepared; account setup and paid-resource approval are pending.

[Implementation status](IMPLEMENTATION_STATUS.md) · [Judge guide](JUDGE_GUIDE.md) · [Machine-readable submission](submission.json) · [Architecture](docs/ARCHITECTURE.md)

## 02 · External apps used

| App | Concrete job | Verification status |
|---|---|---|
| Gmail | Read customer request; send contact-verification and outcome emails | Actual intake and sends observed; operator confirmed receiving the outcome |
| Stripe | Create/retrieve the controlled TEST payment and partial refund | Independent oracle observed exactly one $30 succeeded refund on the $100 TEST charge |
| Slack | Post an actionable case update and retrieve it | Independent case-message readback passed; URL-format comparison fixed and regression-tested |

The model API and local warehouse/payment simulators **do not count** as external apps. Account authentication alone is not action verification. [Redacted same-run provider evidence](evidence/connected-ordinary-run.json) verifies the ordinary three-service run. The connected crash/restart experiment is still pending. The agent playground does not inherit the connected fixture's evidence.

## 03 · Setup instructions

Requires Python 3.12. Use the existing checkout and its locked `.venv`:

```bash
cd ~/testingxd
make setup
make init-config
make playground
```

Open **http://127.0.0.1:8001/playground**. Choose a demo purchase, describe your preference (for example, “I would prefer to keep it if compensation is reasonable”), review both agent outputs and accept exact terms. The default model mode is a **deterministic offline baseline**. Live mode accepts natural descriptions, typos and paraphrases; it is not restricted to example phrases. Conversation history is scoped to this request, so clarification answers retain context. Damage is a claim, not automatic evidence or authorization.

For the actual two-model-role experience, configure the model API locally, keep `RP_MODE=connected-test`, and start:

```bash
RP_RESOLUTION_MODEL=live make playground
```

This web-only command starts no financial worker. Open **http://127.0.0.1:8001/login**, sign in with your operator password, then visit **/resolutions** to inspect the agreement and execute/reconcile its simulated refund. Return-required offers need explicit operator-simulated warehouse acceptance. Customer sessions cannot call operator execution routes. Login changes the session; use a separate browser profile for simultaneous customer/operator views.

Use [one credentials checklist](docs/CREDENTIALS_CHECKLIST.md) for Gmail, Slack, Stripe TEST and the model. Secrets stay outside the repository in `~/.config/returnpath`. Never paste them into chat or commit them. Browser consent belongs to the operator.

For the original connected workflow:

```bash
make doctor
# Only for a NEW isolated rehearsal, never an existing case:
make connected-seed
make connected-dev
```

An existing seeded case restarts with **only `make connected-dev`**. Send the controlled customer email with `order 4127` in its body, then explicitly confirm the emailed link on this Mac. Keep only one financial worker running. Stop with Ctrl+C. Do not run `connected-smoke` alongside a worker.

The playground uses separate `resolutions.sqlite` and `resolution-provider.sqlite` files. It cannot replace, reset or spend against the connected fixture. Public hosting and remote-customer OAuth/verification remain unimplemented; localhost is not a deployment link.

## 04 · Reliability testing

```bash
make lint
make test
make resolution-eval
make eval
make demo
make review-check
make stripe-oracle        # read-only actual Stripe TEST verification
make submission-check
```

The suite checks immutable financial parameters, exact contact verification, single-worker ownership, complete provider pagination, bounded same-key retries, UNKNOWN handling and notification uncertainty. Real subprocess tests exercise worker death with surviving simulator records. The independent watchdog detects/alerts; **an operator restarts the worker**.

New resolution tests cover unauthorized agent offers, cross-customer access, CSRF, expired/superseded acceptance, immutable agreements, required warehouse evidence and replay against a separate simulated provider ledger. Two agents exchanging text is not itself evidence of safety.

- [Natural-language smoke](evidence/language-smoke.json) covers typo/paraphrase inputs and clarification follow-ups; one trial each, with no claim of exhaustive language coverage.
- [Actual two-agent smoke results](evidence/resolution-live-evaluation.json): three live-model scenarios, one trial each; not a broad reliability benchmark.
- [Actual offline test report](evidence/offline-evaluation.md) and [machine-readable results](evidence/offline-evaluation.json).
- [Actual local process-crash trace](evidence/local-demo.json)—simulated providers, not connected crash evidence.
- `make resolution-eval` runs three preference/clarification scenarios ten times with the deterministic baseline. It is **not** a stochastic reliability estimate.
- `.venv/bin/python scripts/resolution_eval.py --live --trials 1` runs the same three synthetic scenarios with actual model calls. Costs API usage; no app-provider writes. Reports go to ignored `.runtime/` until reviewed for export. One successful trial per scenario is only a smoke test.
- [Reliability brief](docs/RELIABILITY_BRIEF.md) and [provenance](docs/PROVENANCE.md) state scope and limitations.

`make stripe-oracle` must report one matching refund, aggregate `3000` cents and matching successful retrieval for the original case. Gmail did not preserve our supplied Message-ID; unknown-send correlation remains unverified and must not trigger a blind resend. Missing connected crash evidence, video or organizer access must keep `submission-check` **BLOCKED**. We do not claim exactly-once delivery, universal reliability or production security certification.

## 05 · Demo video — maximum two minutes

**Not recorded yet. No video URL is available.** [Recording plan and status](docs/DEMO_SCRIPT.md).

The final recording must show the user task, all three real apps, actual model contribution, exact accepted/approved terms, provider evidence and the deliberate crash/restart. Label simulated parts and any cuts. Add the genuine video link here, plus matching transcript and captions; do not substitute an invented transcript or a simulator recording for connected evidence.

Private source access and event eligibility still require organizer confirmation. The repository remains private; no judge credentials or hidden grading instructions are included.
