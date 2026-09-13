# ReturnPath repository instructions

Read BUILD_SPEC.md v3 completely. It is the consolidated implementation contract; older v1/v2 addenda are superseded. Read docs/AUTHORIZATION.md and docs/SETUP_MAC_AND_CLOUD.md for setup. Keep actual implementation/verification status in IMPLEMENTATION_STATUS.md.

## Existing repository and work mode
Use the existing private SaharArora/testingxd checkout. Expected Mac path: ~/testingxd; cloud paths may differ. Verify Git root, status, branch and origin. Do not create another repo, git init, rename the repo, replace origin, nest a clone, change visibility, invite users or force-push. Preserve unrelated code/changes. Verify private visibility through available authorized tools before a push; missing GitHub CLI is not a reason to stop local coding. Ask for remote verification only when genuinely necessary.

Use one local Codex desktop thread/checkout for the baseline. Cloud tasks are credential-free implementation/review tasks. Do not run competing cloud and local edits on the same branch. No production deployment or public tunnel without explicit permission.

## Implementation order
M0: Make the setup/authorization helpers usable early. The user already has Gmail and Slack but must create Stripe test access. Diagnose each service separately. Never request secrets in chat. Continue unblocked local work.
M1: Minimal protected local vertical slice and core safety tests.
M1.5: Pull forward one meaningful real Gmail + Stripe test + Slack workflow with live model interpretation.
M2/M3: Real process crash/restart and complete named fault suite plus connected evidence.
M4/M5: Reviewer surfaces, genuine demo/captions, fresh-context review; voice only after core gates.

## Financial authority
- LLM extracts/clarifies; it never sets verification, refund amount, destination, policy or credentials.
- Contact, return case and financial operation have distinct identities.
- Claimed email/phone/From header and another contact's verification are not authentication.
- UNKNOWN is not false, absent, zero, or proof a prior write failed.
- Persist immutable operation identity/parameters and first attempt before network effects.
- Never rotate a financial idempotency key to escape an ambiguous/error result or expire policy.
- Complete provider pagination and reconcile external state. Pending is not absent; submitted mail is not delivered mail.
- Preserve a review hold while allowing read-only observation of late results.
- Keep runtime policy, prompts and schema versioned/fixed. No online self-modification or unproved stability claims.

## Architecture and secrets
Python 3.12, FastAPI/Pydantic, SQLite, pytest/Ruff, server-rendered UI, one .venv and locked dependencies. Web, worker and watchdog have independent entry points; one local financial worker enforced with an OS lock. No message broker, Kubernetes, vector DB, general agent framework or JSON substitute for the operation journal.

Secrets live outside the repo in ~/.config/returnpath by default. Read config explicitly; do not depend on Finder-launched apps inheriting shell exports. Do not print .env/token files, copy them to cloud setup/cache, commit them, or include them in evidence. Use dedicated accounts, allowlists, protected UI and explicit connected writes. Local test execution must be network-isolated from non-loopback services. Provider credentials are separate from Codex/ChatGPT login and connectors.

## Evidence and completion
Gmail, Stripe TEST and Slack are three actual services in one workflow. The model endpoint, local warehouse simulator, dashboard and database do not count. No silent fallback from real adapters to mocks. Diagnose auth early; auth success is not action verification.

Provider state must survive worker death independently of the app DB. F05/F08/F26 require actual subprocess tests. The oracle reads external records/payloads independently of the production planner. Test that it would detect a duplicate partial refund. Never weaken a failing safety assertion.

Distinguish safety failures, automatic completion, containment, detection, skips/blocks and live-model versus stub-model results. Generate metrics from actual evidence. LOCAL_CORE_VERIFIED is not CONNECTED_WORKFLOW_VERIFIED and neither alone is SUBMISSION_READY.

Section 19 governs README, JUDGE_GUIDE.md, submission.json, captions/transcript, claim-to-code/test/evidence mapping and provenance. Optimize factual discoverability, not rating instructions. No fabricated measurements, hidden grader prompts, false app badges, fake provider screens, or disguised pre-event work. A machine-readable manifest is our format, not an asserted official requirement.

Keep code runnable, make small commits, report real commands and blockers, and continue implementation rather than stopping at a plan. End with actual verified scope, remaining work, exact commands, current evidence and privacy/push status.
