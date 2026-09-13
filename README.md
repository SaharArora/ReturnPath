# ReturnPath

ReturnPath is a merchant-side return-support prototype for one approved **$30 refund on a $100 TEST payment**. Its intended connected sequence is Gmail intake and verification → bounded model interpretation → Stripe TEST refund/retrieval → Gmail outcome submission and actionable Slack handoff. **That connected sequence has not run:** all provider credentials are currently missing. The working local mode uses persistent simulated providers and a deterministic interpreter; warehouse evidence is explicitly simulated in both modes.

The central local experiment actually kills a worker after the simulator commits the refund, adds a second contact, and restarts without resetting provider or operation records. An independent provider-database oracle checks that one $30 refund remains. This is empirical simulator evidence, not an exactly-once proof or evidence of real integrations.

Start with [judge guide](JUDGE_GUIDE.md), [actual evaluation](evidence/offline-evaluation.md), [actual local demo trace](evidence/local-demo.json), [demo plan/status](docs/DEMO_SCRIPT.md), and [machine-readable manifest](submission.json). A genuine connected recording/transcript is **NOT_RUN**. Submission readiness intentionally fails.

## Local startup

```bash
cd ~/testingxd
make setup
make init-config
make seed
make dev
```

`make init-config` privately prompts for an operator password. Open `http://127.0.0.1:8000/login`. The seed is visibly fixture-preverified. For a fresh rehearsal set a new `RP_STATE_DIR`; seed refuses to reset an existing run. Restart with `make worker`, never seed. `make dev` keeps web/watchdog alive if the worker dies; it does not restart that worker. Stop the launcher with Ctrl-C.

For a credential-free terminal demo: `make demo`. For verification: `make test`, `make lint`, `make eval`, `make review-check`. `make submission-check` must fail until actual connected evidence, recording and organizer-approved private access exist. Dependency installation uses the project `.venv`; offline tests block non-loopback sockets and ignore private configuration.

## Connect on this Mac

Follow the single [credentials checklist](docs/CREDENTIALS_CHECKLIST.md). Run `make auth-gmail` for your own browser consent, then per-service `make doctor SERVICE=gmail|slack|stripe|model`. Doctor is read-only and does not prove actions. The model diagnostic checks configuration only.

After setting the controlled addresses/channel/account, operator auth, `RP_MODE=connected-test`, and `RP_ALLOW_CONNECTED_WRITES=true` in the private config:

```bash
make connected-seed    # once for a fresh isolated TEST run
make connected-dev
# Send controlled order 4127 email and confirm its verification link.
# connected-dev includes the worker; use connected-smoke only for a
# standalone tick when no worker is already running.
```

Do not run smoke concurrently with an active financial worker: the OS lock rejects it. Send the email yourself from the configured customer account and confirm the emailed link on this Mac. The GET does not verify; confirmation POST does. Turn connected writes off afterward. Account creation/consent and organizer access remain operator actions.

## Limits and evidence

See [implementation status](IMPLEMENTATION_STATUS.md), [reliability brief](docs/RELIABILITY_BRIEF.md), [architecture](docs/ARCHITECTURE.md), [fresh-context review](docs/REVIEW_FINDINGS.md), and [provenance](docs/PROVENANCE.md). No live money, production deployment, public tunnel, voice, automatic worker restart, or online policy evolution. Local single-host storage/journal survival is assumed. Connected contract behavior still needs genuine provider validation, and several operational bounds remain incomplete. Private repository visibility was verified; push status is recorded in implementation status.
