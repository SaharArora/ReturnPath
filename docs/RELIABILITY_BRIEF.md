# Reliability brief

The observed local result is a recovered $30 simulator refund after an actual SIGKILL at the post-provider-success/pre-completion-write boundary. The harness explicitly restarts the worker. Duplicate contacts retain one return operation; the independent provider database, not the case success flag, determines refund count/amount. See [actual demo trace](../evidence/local-demo.json) and [actual test report](../evidence/offline-evaluation.json).

Authority remains outside the model: exact merchant approval, fixed integer cents, verified contact scope, durable parameters/hash/key, and complete payment reads. Unknown observations cannot authorize new money movement. Pending, failed and conflicting refunds do not create replacement identities. Retry policy is at most three attempts, one key, backoff, and a 23-hour first-attempt horizon. Provider SDK retries are disabled. Review holds continue read-only observation.

Mail submission is not delivery. Ambiguous sends remain unknown unless exact sent-mail correlation is found. Gmail Message-ID behavior is not yet verified against the real service. Slack lost initial posts remain uncertain; updates use known timestamps. The watchdog detects and alerts independently; no automatic restart is claimed. Default stale threshold 20 seconds plus 10-second polling gives approximately 30 seconds plus scheduling/storage/API delay while the monitor is functioning; the process test uses explicitly shortened thresholds, not a measurement of the default bound.

Assumptions: one financial owner on one local filesystem; SQLite journal and immutable merchant/operation records survive; truthful eventual provider reads; no competing external financial writer; operator-controlled test accounts. This does not recover from arbitrary trusted-record destruction, host/storage loss, credential compromise or malicious providers. The watchdog shares the host/storage and can fail.

Automatic completion, containment and detection are different. The report lists actual test nodes rather than combining them into a success percentage. Connected workflow/live model/recording remain NOT_RUN. Daily per-state connected reservations bound model/mail/refund/Slack calls; they are not an account-wide spending cap across separately configured state directories. All fault combinations and real-provider retry guidance remain unverified. This is a prototype, not production financial infrastructure or a formal exactly-once/self-stabilization claim.

## Expanded resolution checkpoint

The ordinary connected three-service run has independent provider readback in `evidence/connected-ordinary-run.json`; the connected crash has not run. Gmail rewrote the supplied Message-ID, so recovery of an uncertain send via that identifier is not verified. Known acknowledged message IDs can be retrieved and compared.

The two-agent playground uses fixed prompts and catalog authority, immutable accepted agreements and a separate simulated payment ledger. Three live-model smoke scenarios passed; they do not establish stochastic consistency or adversarial robustness. Tests reject unauthorized offers, cross-session acceptance, expiry/supersession and replayed simulated payments. Public hosting, variable-amount Stripe execution, reflection and crash recovery during negotiation remain unimplemented.
