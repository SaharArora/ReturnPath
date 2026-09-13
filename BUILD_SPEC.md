# ReturnPath — Codex build specification

Version: 3.0 · September 13, 2026 · consolidated implementation contract  
Repository: `SaharArora/testingxd` · expected local checkout: `~/testingxd`  
Visibility: **private**  
Product type: merchant-side support agent; synthetic customers and test payments only.

## 0. Assignment and priority

Implement a working application, not just an architecture document or scaffold.

**Product:** A customer asks about an already-authorized return through email, or optionally by phone. The application establishes the relevant facts, performs the permitted partial refund, verifies the payment provider's state, and communicates the result. Interruptions and repeat contacts must not automatically become repeat financial actions.

**Core demonstration:** A $30 refund against a $100 test payment succeeds externally. The worker crashes before recording that result locally. After restart, and despite a duplicate customer contact, the system discovers the existing refund and continues without issuing another one.

Prioritize, in this order:

1. A correct, testable financial operation and crash-recovery protocol.
2. Real Gmail, Stripe test-mode, and Slack integrations, with an inspectable demonstration.
3. Meaningful language understanding, clarification, and cross-channel case association.
4. Optional, narrow Twilio voice intake after the core passes its acceptance gates.

Do not add general-purpose agents, merchant onboarding, arbitrary subscription cancellation, browser automation, a real carrier integration, or unrelated features. Do not train a model. Keep the workflow narrow rather than weakening its guarantees to fit more functionality.

The official public brief requires at least three external apps, a working project/repository, a two-minute demo, and a short system/reliability brief. Its largest categories are technical execution and reliability/evaluation. [S1] The page does not settle every question about advance preparation, private submission access, or simulated integrations. Record those as organizer questions; do not claim eligibility has been verified or publish the repo to solve access uncertainty.

## 1. How to execute this assignment

Read this entire specification and `AGENTS.md` before editing. This version incorporates and supersedes earlier handoffs and their addenda. `docs/AUTHORIZATION.md` and `docs/SETUP_MAC_AND_CLOUD.md` specify the operator setup. Section 19 specifies reviewer-facing evidence. Do not treat old chat instructions or archived drafts as competing specifications. Inspect the current directory, Git status, existing instructions, and tool availability. Do not overwrite unrelated work. Make a short milestone plan in `IMPLEMENTATION_STATUS.md`, then implement the milestones in Section 17. Keep working on unblocked milestones rather than stopping after planning.

Use the defaults here without requesting repeated product clarification. Ask only for genuinely missing authorization, credentials, or an existing-repository conflict that cannot safely be resolved. Consolidate credential requirements in one checklist. Do not ask the user to paste secrets into the conversation or commit them.

### Private repository handling

The user has already created and cloned `SaharArora/testingxd`. Work in this existing checkout; do not create another repository, run `git init` again, rename it, replace `origin`, or create a nested checkout. Verify the working directory, Git root, current changes, and `origin`. The product may be called ReturnPath while the repository remains `testingxd`. A cloud checkout may have a different filesystem path; verify its remote identity rather than requiring the literal Mac path.

With GitHub CLI, inspect `gh repo view SaharArora/testingxd --json visibility,nameWithOwner`. Read the remote's visibility and require `PRIVATE` **before the first push**. [S2] Never change visibility, enable Pages, invite collaborators, or publish a demo without explicit permission. If this check cannot run, continue locally and report push/visibility verification as blocked; do not assume a successful clone proves push authorization. Do not create a replacement remote.

Before committing, add ignore rules for secrets, OAuth credentials/tokens, `.env`, databases and WAL files, runtime logs, raw emails/transcripts, recordings, generated reports containing external data, virtual environments, and caches. Commit only synthetic fixtures and reviewed, redacted evidence. Do not automatically add an open-source license.

Make small milestone commits. Never force-push, reset unrelated changes, disable safety tests to get green checks, fabricate credentials, or report unexecuted tests as passing.

### Progress and final report

Maintain a status table: milestone, implemented functionality, actual verification command/result, remaining blocker. Distinguish **implemented**, **verified against simulator**, **verified against real test service**, and **blocked**. A stub is not an integration. A fixture parser is not a live LLM test.

At the end, report what runs, exact startup commands, tests actually executed, remaining limitations, and whether the existing private remote was actually verified and a push actually succeeded. Continue as far as the environment permits without claiming external connectivity that was not exercised.

## 2. Scope, modes, and business assumptions

Support one synthetic merchant, USD, captured card payments, and pre-existing approved return records. Each return has one fixed approved refund amount and at most one automatically created refund operation. The refund goes to the original payment method; never accept a destination supplied by a customer.

The merchant's order/return records supply order ownership, charge ID, currency, approved amount, and policy version. An explicit return-evidence simulator supplies warehouse acceptance evidence. Do not conflate a carrier delivery scan with merchant inspection or acceptance. The policy requires **warehouse acceptance**, not merely a customer claiming delivery.

Out of scope: calculating tax or shipping adjustments; creating return labels; exchanges; multiple currencies; Stripe Connect; disputes/chargebacks; multiple automatic refund attempts with new operation identities; medication/medical workflows; production security/compliance certification; and concurrent financial changes by unrelated systems.

Implement explicit modes:

| Mode | Behavior |
|---|---|
| `local` | No external calls. Persistent simulator adapters, deterministic fake interpreter, synthetic fixtures. Runs without credentials. |
| `connected-test` | Real LLM, Gmail, Stripe test-mode, and Slack adapters. Synthetic allowlisted recipients and test payments only. Return evidence remains visibly simulated. |

Optional voice uses real Twilio only when explicitly enabled. Do not silently fall back to fakes in `connected-test`. Fail configuration checks with an actionable error. Local mode must refuse non-loopback network access, including accidental model calls.

A separate explicit switch must enable connected test writes. Read-only diagnostics must not send emails, post Slack messages, create charges, or issue refunds. Live payments are unsupported even when write access is enabled. Missing keys must not obstruct the offline implementation.

## 3. Exact reference scenario

Seed a fictional merchant and an order with these immutable business values:

```text
merchant:             demo-merchant
order reference:      4127
original charge:      10,000 cents USD ($100)
approved return:      ret-4127-headphones
approved refund:      3,000 cents USD ($30)
warehouse accepted:   true
customer address:     configured, controlled demo mailbox
```

Never hard-code a real customer's address or provider object ID. In connected mode, create test objects through an explicit seed command and persist their actual returned IDs. A new rehearsal uses a new test order/charge namespace; restarting an existing case must not create new financial objects.

Customer input: “I returned the headphones from order 4127 and still haven't received my refund.”

Required path: interpret request → identify candidate return → verify customer control → observe merchant and payment facts → prepare one financial operation → execute if allowed → verify provider outcome → submit truthful customer communication → post/update an operational Slack case summary.

Fault path: arm the named post-provider-success failpoint → refund executes → worker is killed before its completion write → another contact arrives for the same return → restart worker → retrieve existing provider refund → complete remaining communication.

Final independent assertions:

```text
matching provider refund objects:   exactly 1
matching refund amount:             3,000 cents
aggregate refunded on demo charge:  3,000 cents
refund amount never taken from:     LLM output or customer text
customer contacts:                 may be multiple
financial operation for return:    exactly 1
```

Stripe permits multiple partial refunds up to the original charge amount. [S3] Therefore an erroneous second $30 refund would not necessarily be stopped by the original $100 charge ceiling. Demonstrate application-level deduplication, not merely the provider's maximum-refund rule.

## 4. Minimal architecture and stack

Use Python 3.12, FastAPI, Pydantic, standard-library SQLite access, pytest, Ruff, and a small server-rendered HTML interface. Use a project-local `.venv`; do not install application packages into the user's Conda base environment. Every Make target must use the project environment explicitly, without assuming a prior shell activation. Use official provider SDKs where they simplify authentication and request validation. Use `pyproject.toml` and a reproducible checked-in dependency lock; prefer a pip-installable locked requirements file to minimize bootstrap tooling. Document and test the chosen versions. Run setup against the supported Python version and make missing/mismatched runtime errors actionable. Do not add an agent framework or orchestration framework unless an actual requirement cannot be implemented reasonably without it.

Use one codebase with three entry points: web/intake process, financial worker, and independent watchdog. These are not separately deployed microservices. The financial worker must not be hidden inside the web process's background-task lifecycle.

```text
email / optional phone
          |
    bounded interpreter
          |
    contact + candidate case
          |
  verification / trusted records
          |
      observations
          |
  deterministic planner + guard
          |
 durable operation / notification outbox
          |
        providers
          |
      re-observation

independent watchdog -> heartbeat / overdue-work alerts
independent test oracle -> simulator/provider facts, not agent success flags
```

Suggested structure; merge small modules instead of creating empty abstractions:

```text
AGENTS.md
BUILD_SPEC.md
IMPLEMENTATION_STATUS.md
README.md
Makefile
pyproject.toml
<dependency lock file>
.env.example
.github/workflows/ci.yml
src/returnpath/
  __main__.py
  config.py
  models.py
  storage.py
  interpreter.py
  identity.py
  policy.py
  reconcile.py
  worker.py
  watchdog.py
  web.py
  adapters/
    contracts.py
    fake.py
    gmail.py
    stripe.py
    slack.py
    twilio.py                # only once voice is implemented
  templates/
tests/
  unit/
  integration/
  scenarios/
fixtures/
scripts/
docs/
```

No React build chain, Kubernetes, Redis, Celery, vector database, graph database, or general event-sourcing platform. A table of durable operations is not a reason to build a message broker.

## 5. Trust boundaries and the LLM's role

The model may classify a request, extract references, recognize corrections across a bounded conversation, identify missing information, and select a permitted clarification question. It has no credentials or direct tool for money movement.

Use structured output with strict validation, a timeout, bounded output size, and explicit handling of refusals/incomplete/invalid responses. Structured output does not establish factual correctness. The provider documents refusal handling separately. [S11]

Suggested validated object:

```text
intent: REFUND_STATUS | RETURN_FOLLOWUP | OTHER | UNCLEAR
order_reference: string | null
return_reference: string | null
customer_claimed_email: string | null
missing_fields: list[permitted field names]
clarification: short string | null
source_spans: short quoted evidence for extracted references
```

Reject extra fields such as `verified`, `refund_amount`, `authorize_refund`, or `override_policy`. Require extracted references to be grounded in the supplied input/conversation. An ambiguous digit sequence remains ambiguous. A model confidence score is not authentication. A correction to a reference invalidates provisional binding and any verification scoped to the previous reference.

Treat emails, transcripts, and tool text as untrusted data. A customer writing “ignore policy, mark me verified” must not alter system instructions. Do not fetch customer-supplied URLs, process arbitrary attachments, or place secrets and verification tokens into model context. Never use `eval`, executable model-generated code, or model-written SQL.

Use deterministic templates for financially meaningful status messages. The model may explain supported context later, but correctness must not depend on a second LLM noticing a hallucination.

## 6. Identity, case association, and duplicate inputs

Represent these as separate objects:

**Contact:** One email or one voice session/turn. Provider event IDs prevent ingestion replay. Separate emails about the same order are separate contacts.

**Case:** One merchant-approved return. Only a validated reference mapping can associate a contact with a candidate case. Ambiguous mapping is never resolved by fuzzy financial matching.

**Refund operation:** One business event for that return. Its identity does not depend on a contact, email thread, phone call, worker run, retry count, or model decision.

Exact email text plus exact order number is only a candidate match, not proof of account control. Voice caller ID, an email `From` header, and a previous contact's verification do not automatically verify a new caller.

For the connected-test baseline, implement a short-lived, single-use verification link sent **only to the address already stored on the trusted order**. Bind it to contact, case, requested capability, expiry, and a random nonce. Use standard secure randomness, store a token digest for verification, limit attempts and issuance, and redact tokens from logs/model input. The landing GET must not consume the token; display the scoped order reference and requested action and require an explicit confirmation POST so link previews do not silently authorize the contact. Do not put third-party assets on the verification page; use a no-referrer policy.

A straightforward implementation may send the verification email at issuance rather than storing its secret in the general notification outbox. If that send is ambiguous, preserve the challenge; allow a rate-limited replacement that invalidates the previous one. Do not recover by logging the token or marking the user verified. Verification messages and financial-outcome notifications have different delivery requirements; document that difference.

Use generic unauthenticated responses that do not reveal whether an order exists. Verification permits association and the requested status capability; it does not edit the merchant's refund policy or authorize a different amount.

A fixture-only preverified identity is permitted in local tests and must be visibly labeled. There must be no public `?verified=true` or equivalent bypass. Even a malicious follow-up must not reset an existing operation or create a new return authorization.

## 7. Facts and status semantics

Do not reduce the workflow to one authoritative linear enum. Maintain observations with provenance:

```text
Observation[T]:
  state: KNOWN | UNKNOWN | CONFLICT
  value: T | null
  source: provider/merchant source
  source_object_id: string | null
  fetched_at: UTC timestamp
  source_version: optional
  error_code: optional
```

For boolean facts, known true, known false, and unknown are distinct. Timeouts, permission errors, failed pagination, stale observations, and malformed responses must not silently become `false`, zero, an empty list, or “not found.” Conflict is a review condition.

Facts needed in this scope: trusted customer/return binding; fixed approval and amount; warehouse acceptance; captured charge/currency/dispute status; all relevant refunds; customer notification submission state. Use a configurable 30-second freshness window for mutable prerequisites before a new financial request; stale required observations become unknown until refreshed. Trusted immutable approval records and consumed verification grants are not volatile provider observations. A recent read is still only that provider's observation, not an atomic snapshot of all systems.

Normalize payment observations as `ABSENT_OBSERVED`, `PENDING`, `SUCCEEDED`, `FAILED`, `CANCELED`, `REQUIRES_ACTION`, `UNKNOWN`, or `CONFLICT`, while preserving raw status. `ABSENT_OBSERVED` requires a successful complete listing but does not itself prove that an earlier ambiguous write never occurred.

Normalize notification delivery as `NOT_ATTEMPTED`, `ATTEMPT_STARTED`, `SUBMITTED`, `SEND_UNKNOWN`, or `NEEDS_REVIEW`. `SUBMITTED` means the provider acknowledged/disclosed the sent message, not that the customer received or read it.

Case labels such as `WAITING_FOR_VERIFICATION`, `WAITING_FOR_RECEIPT`, `RECONCILING_PAYMENT`, `PAYMENT_PENDING`, `NOTIFICATION_PENDING`, `RESOLVED`, and `NEEDS_REVIEW` are derived summaries, not financial authority.

Re-observe all registered demo cases on a bounded schedule, including cases whose cached summary says resolved. Otherwise a corrupted “done” flag could suppress recovery forever. A review hold prevents new financial effects, not read-only observation of a previously ambiguous payment.

## 8. Persistence and concurrency

Use SQLite transactions, foreign keys, parameterized queries, and explicit uniqueness constraints. SQLite's transaction support is relevant to the intended crash tests. [S10] Configure appropriate durability and busy handling; document local-filesystem assumptions. Never keep a database transaction open across an HTTP request or model call.

Required logical records (combine tables only when the separation remains explicit):

| Record | Required fields/constraints |
|---|---|
| orders | merchant/order key, trusted customer address, charge ID, integer currency amount |
| approved_returns | merchant/return key, order FK, approved cents, currency, immutable policy version |
| contacts | channel, provider event ID, input reference, candidate/bound case; unique channel + event key |
| cases | unique merchant + return key; derived state, review hold, next observation time |
| verifications | contact/case scope, token digest, expiry, consumed time, issuance/attempt limits |
| operations | unique merchant + return + operation kind; UUID, immutable params/hash, idempotency key, first attempt time, provider ID, execution state |
| notifications | unique semantic notification key; permitted recipient, immutable content, attempt time, provider ID, delivery state |
| observations/audit | source facts, timestamps, reason codes, request IDs; redacted |
| heartbeats/alerts | component heartbeat, last verified progress, alert key/status |

The merchant fixture, operation identity, immutable parameters, attempt journal, and verification state are trusted durable records in this fault model. Only designated cached conclusions may be deliberately corrupted. Do not claim recovery from arbitrary destruction of these records.

### Single financial executor

Deliberately support **one financial worker per merchant/test environment**. Enforce a process-lifetime OS advisory lock on the local machine, tied to the database/environment. On macOS/Linux, standard-library `fcntl.flock` is sufficient for this scope. A second financial worker must fail cleanly before any provider mutation. A killed process releases the lock through the OS; do not use a stale PID file as the lock.

Concurrent intake is allowed and uses database constraints. SQLite uniqueness and stable Stripe idempotency remain required even with the worker lock. Do not advertise distributed multi-worker correctness, distributed leases, or external fencing. Tests must actually attempt to start two workers.

Keep simulator provider storage separate from the application database. It must survive worker death and must not be reset during recovery.

## 9. Deterministic policy and financial protocol

Implement a pure `decide(observations, authorization, operation_record, policy, now)` function returning a typed decision and reason codes. Separate it from execution. Unknown values cannot satisfy required prerequisites. Unrelated failures, such as Slack being unavailable, need not block an otherwise safe payment; they block their own dependent steps.

Before the first refund request, require verified case authorization; one exact approved return; warehouse acceptance; positive integer approved cents; matching USD charge/currency; captured paid card charge; no unsupported dispute; no conflicting refund evidence; and test-mode enforcement. The amount comes from the approved return, never an LLM or caller. Pending refunds reserve their budget; they are not zero.

Create one durable operation using a unique business key `(merchant_id, return_id, approved_refund)`. Generate its opaque operation UUID once. Persist the exact charge, amount, currency, policy version, parameter hash, and idempotency key before any payment POST. Policy changes do not create a second operation for the same return; conflicting changes require review.

Use an opaque key such as `returnpath-refund:<operation_uuid>`. Include non-sensitive operation/return identifiers in provider metadata. Metadata is a correlation aid, not proof of authorization.

### Required execution/recovery procedure

1. Acquire the financial-worker lock. Read the durable operation and current prerequisites.
2. Read the charge and paginate the provider's refund list for that charge. If a provider refund ID is stored, retrieve it too. Do not invent a “lookup by idempotency key” endpoint. Stripe documents charge-filtered refund listing. [S5]
3. Match operation/return identifiers, charge, amount, and currency. A mismatch, unexpected unassigned refund, conflicting stored ID, or multiple matching refund objects creates a review hold. Do not compensate by creating a charge or another refund.
4. If a matching refund exists, reuse it. Pending means wait/observe; succeeded permits truthful notification; failed/canceled/requires-action requires explicit handling and no automatic new-key refund. Preserve raw evidence. [S4]
5. If no prior request has ever been attempted and all prerequisites are current, commit `ATTEMPT_STARTED` and `first_attempt_at`, then perform the POST with the persisted key and exact parameters.
6. If a previous request has an unknown outcome, resolve through provider reads and, only within the configured safe retry horizon, a retry with **the same key and identical parameters**. Never rotate the key to escape an error.
7. After a successful response, persist the provider ID and re-observe its status before a success notification. An HTTP success does not replace business-state verification.
8. After timeout, crash, lost response, or server error, preserve uncertainty. Do not set “failed/not refunded” merely because the response was lost.

Stripe retains idempotent results, including some error results, and keys may be pruned after at least 24 hours. [S6] Set a conservative application retry horizon of 23 hours from the first attempted request. Outside it, an unresolved financial write must stop for review, even if a later listing is empty. Continue read-only observation. Account for provider SDK retries explicitly; no hidden second retry loop with a new key.

Use retry budgets and durable `next_attempt_at`. Initial defaults: 10-second provider timeout, at most three attempts in an automatic retry episode with bounded backoff, then review/overdue state as appropriate. Honor documented retry guidance such as `Retry-After`. Persist financial attempt history across restart. Definite permission/configuration errors are not transient retry loops.

These are application policies, not claims about provider availability. Previously pending refunds may later resolve; continue scheduled observation without automatically starting another financial operation.

## 10. Integration contracts

Keep adapter interfaces small: observe relevant state, perform an allowed mutation, and report classified errors plus provider request IDs. Real and fake adapters use the same typed contracts. Never fake a real adapter's success when credentials are absent.

### Gmail — required

Use a dedicated test mailbox, `gmail.readonly` plus `gmail.send` OAuth permissions, and an allowlisted demo intake query. These scopes are mailbox-level; an intake query is an application filter, not a provider-enforced authorization boundary. Use a Desktop OAuth client with loopback authorization on the Mac, not a service account or a Gmail password. Validate the authorized mailbox against configuration. Avoid full mailbox-management scope unless a demonstrated feature requires it. Gmail documents separate read and send scopes. [S7]

Poll with pagination and persist Gmail message IDs before acknowledging ingestion. Exclude sent/self-generated messages to prevent loops. Repeated scans and repeated provider events must be harmless. Distinct emails remain distinct contacts and join the same verified return case.

For financial-outcome notifications, persist a unique notification record and its send-attempt marker before calling the API. Use proper MIME generation and a stable RFC Message-ID where supported; store the returned Gmail ID/thread ID. Send only to the trusted order address. Do not reply-all or use an unverified address extracted from speech.

Gmail's send endpoint does not document a Stripe-style idempotency-key parameter. [S8] Therefore after an ambiguous send, search/read sent-mail evidence using supported API functionality and verify recipient/content/correlation. A missing search hit is not proof that sending failed. If unresolved after a bounded observation period, retain `SEND_UNKNOWN` and require review rather than blindly sending again. Stable message IDs aid reconciliation; they are not an exactly-once guarantee. Verify actual message-ID/search behavior in connected contract tests.

Use templates distinguishing “request submitted,” “provider reports refund succeeded,” and “unable to verify status.” Never say the customer has received money based solely on a provider refund status.

### Stripe — required, test mode only

Require test credentials; reject recognizable live secret/restricted-key prefixes. Also check returned financial objects' `livemode` state and the seeded test-account context rather than relying solely on key spelling. Restrict to known seeded charge IDs and supported payment types. No arbitrary charge/refund endpoint exposed to the model or public web routes.

Implement retrieve-charge, list-all-refunds-for-charge, retrieve-refund, and create-approved-refund. Preserve provider statuses, IDs, and request IDs. Validate amounts as integer smallest units; no floating-point currency arithmetic. [S3, S4, S5]

An explicit seed command may create a supported test payment. Normal startup and read-only diagnostics must never create payments. Connected writes require an enable switch and configured demo limits.

### Slack — required

Use an installed bot in one allowlisted private operations channel. The included manifest requests `chat:write`, `groups:read`, and `groups:history`; the latter two support channel checks and reading back narrowly scoped case evidence. Explicitly invite the bot to the private channel. No Events API, Socket Mode, slash command, incoming webhook, or public HTTP callback is necessary for this baseline. Minimum behavior: post an actionable review case with reason, verified facts, missing/unknown evidence, operation ID, and a protected dashboard link; then update the known message when the review state changes. Also provide a concise resolved-case summary for the normal workflow. This is an operational handoff, not decorative logging. Slack documents message posting with `chat:write`. [S9]

Check both transport success and Slack's application response. Store channel and message timestamp. Retry/update known messages where safe. For a lost initial-post response, do not invent exactly-once semantics: deduplicate when discoverable and tolerate/document bounded duplicate **internal alerts**, or leave the send uncertain. That weaker internal-alert guarantee must not affect financial deduplication.

No Slack approval buttons are required. Human review is represented as a hold and actionable evidence; a dashboard button may request re-observation, but cannot bypass policy, mark an absent refund succeeded, or issue a new refund identity.

### Return evidence — explicitly simulated

Implement a tiny local HTTP endpoint with warehouse acceptance and optionally carrier status, backed by persistent synthetic data. Clearly label it `SIMULATED RETURN EVIDENCE` in UI, docs, and recordings. Support unknown/unavailable/conflicting responses through named failpoints. Do not count it as one of the real external apps.

### Twilio — optional, after core acceptance

Use inbound calls only. TwiML `Gather` supports speech/keypad input and supplies recognized speech to the application. [S12] Use `Say` for concise prompts. Do not add a separate streaming transcription stack unless the turn-based implementation cannot meet an actual requirement.

The voice path must: capture an incomplete request, ask at most two clarifying questions, handle an explicit corrected order reference, create a contact/candidate association, and continue via the same email verification process. A caller need not remain connected while a refund reconciles. Until separately verified, the caller hears only generic acknowledgment; do not reveal an existing case's private status because its original email contact was verified.

This baseline is intentionally an intake-and-handoff flow, not a full authenticated phone-support product. A phone verification code or verified readback is optional additional scope, not a prerequisite for calling the integration implemented.

Validate Twilio request signatures with the official helper and the actual configured public URL. Signature validation establishes request origin, not order ownership. [S13] Support duplicate webhook delivery using `CallSid` plus a server-issued turn ID; a CallSid alone cannot deduplicate every turn in a conversation. Cache/reuse responses for replayed turns. Apply strict model/webhook latency and turn limits, and fall back to a deterministic prompt or email handoff.

Do not record audio. Do not place outbound calls, disclose tokens, or disable signature checks to fix tunnel configuration. Keep cost limits and optional-feature switches explicit. Test real voice end-to-end separately from simulated transcripts.

## 11. Watchdog, recovery, and bounds

The watchdog runs in a separate invocation/process from the worker. Its baseline role is detection and alerting, not automatic process restart. The operator/test harness explicitly restarts the worker. Do not advertise automatic process self-healing unless a distinct bounded restart mechanism is actually implemented and tested. It does not call the interpreter or reuse the planner to decide whether progress is healthy.

Check a small set of facts: worker heartbeat freshness; age of unresolved financial attempts; age of unknown required evidence; overdue customer notification after verified payment success; and last verified business progress. A retry or log message is not necessarily progress. Record watchdog heartbeat separately and expose its age in the UI.

Initial configurable demo values: worker heartbeat every 5 seconds; watchdog observation every 10 seconds; stale-worker threshold 20 seconds; stale business-progress threshold 120 seconds. Use an injectable clock in deterministic tests. For a stale threshold H and observation period W, describe detection as at most approximately H + W plus scheduler/processing delay **while the watchdog runs and can read storage**. Measure actual process-test detection separately.

The watchdog must be able to submit its own Slack alert when the worker is dead; it cannot merely queue an alert only the dead worker can send. Persist alert identity and avoid unlimited repeated alerts. If Slack is down, expose pending alert state and emit a redacted local diagnostic. If shared storage is down, report a storage failure instead of declaring health.

Do not claim the monitor cannot fail. Worker and watchdog share host, storage, configuration, and possibly credentials. Host failure, storage corruption, and correlated logic errors are limitations, not solved problems.

Distinguish:

- **Automatic recovery:** the intended business outcome completes after the supported fault clears.
- **Safe containment:** the system blocks further unsafe effects and creates a review/input requirement.
- **Detection:** a condition is surfaced, whether or not recovery occurs.

Do not combine these into one success percentage. Do not assert a universal wall-clock recovery bound while dependencies remain unavailable or a bank refund remains pending.

## 12. Security, isolation, and operational limits

This is a test application, not production financial infrastructure. Use synthetic records and controlled inboxes/channels. Never test by touching unrelated personal mail or real customer finances.

Require authentication for the operator UI and every mutation route. Bind local mode to loopback. Public exposure for Twilio must not expose operator, simulator, fault-injection, or reset routes unauthenticated. Use proper session/CSRF protections for browser actions. Prefer local CLI failpoints to public buttons; any displayed control must call a protected endpoint.

Use allowlists for recipient mailboxes, Slack channels, seeded payment IDs, and enabled adapters. Bound input lengths, conversation turns, per-contact model calls, automatic retries, demo financial actions, and daily test activity. Verification challenges must be rate-limited so an unauthenticated caller cannot spam a customer's mailbox.

Sanitize displayed email/transcript text and escape HTML. Do not log raw secrets, authentication headers, verification URLs, OAuth tokens, full transcripts, or complete customer messages by default. Provide redacted diagnostic fields instead.

Provider-call code must never accept a refund amount, provider URL, recipient, or SQL fragment directly from model output. Secret-bearing config belongs in environment/local ignored files. Document minimal scopes and credential revocation. Do not weaken these controls for the recorded demo.

## 13. Interface and trace requirements

Build one clear dashboard with case list and case detail. Avoid a general chat UI.

Show: mode and real/simulated adapter badges; contacts associated with the case; verification state; authoritative observations with timestamps; current decision/reason; immutable refund operation and provider refund ID; notification submission state; review hold; worker/watchdog health; and an ordered event trace.

The main demonstration should make these three values visible together:

```text
Approved refund: $30
Actual provider refunds for this return: 1 × $30
Remaining work: customer notification / resolved
```

Use clear status labels, not unexplained confidence scores. Never show a green completion state when refund outcome or notification submission is unknown. The trace displays concise reason codes and evidence, not hidden model chain-of-thought.

For local demo only, expose CLI commands to seed a fresh scenario, arm a named fault, inspect external simulator state, and restart the worker. A stale-cache fault may change derived labels, never customer authorization, operation identity, or trusted order data. Recovery restart does not run seed/reset.

## 14. Fault-injection and independent evaluation

Build persistent fake adapters that model the important differences between providers. The fake payment provider must allow partial refunds, reject aggregate amounts above the charge, retain/replay idempotent responses, simulate key expiry, and support delayed/refund-failed states. The fake mail service must **not** magically deduplicate every send. Keep fake provider state separate from application state.

Named failpoints must target a specific case/operation and be armed/disarmed explicitly. They are disabled by default. A wrapper may let a real Stripe test request complete and then discard its response or kill the worker. Label that as an **application-side injected response-loss/crash after a real test API call**, not a genuine Stripe outage.

Use an independent test oracle that reads provider/simulator records and notification payloads. It must not import the production `decide` function or trust the application's `RESOLVED` flag to grade correctness. The fixture defines approved amount and identity. Count external effects and inspect their actual parameters. Distinguish invalid conditions already present in a seeded fixture from new violations caused by the application. A deliberately seeded duplicate-refund case passes containment only if it is detected and not worsened; the system cannot undo those historical refunds or relabel that case automatically recovered.

Implement these scenario families; parameterize only where it meaningfully expands coverage:

| ID | Scenario | Required observation |
|---|---|---|
| F01 | Ordinary authorized return | One correct partial refund; truthful notification; Slack summary |
| F02 | Identical email/event redelivered | No duplicate intake event or financial effect |
| F03 | Two distinct emails about one return | Two contacts, one case/financial operation |
| F04 | Voice/email contact replay | Correct provisional association; no inherited caller authentication |
| F05 | Start two financial workers | Second rejected by process lock; one execution owner |
| F06 | Crash before any payment POST | Restart resolves attempt uncertainty with same operation/key |
| F07 | Provider commits; response lost | Existing refund discovered or same-key result recovered |
| F08 | SIGKILL after provider success, before local write | External state survives; restart does not duplicate |
| F09 | Warehouse evidence unavailable | Unknown, not “not received”; no premature refund |
| F10 | Warehouse acceptance is known false | Wait without treating API success as return acceptance |
| F11 | Provider listing unavailable/incomplete | No inference of zero refunds; no blind new-key request |
| F12 | Refund pending | Poll; no second refund and no succeeded notification |
| F13 | Refund failed/canceled/requires action | Explicit review; no automatic replacement operation |
| F14 | Cached case label falsely says resolved or pending | Re-observation repairs derived state |
| F15 | Pre-existing unexpected/manual refund | Review; do not guess which return it belongs to |
| F16 | Matching refund on a later results page | Full pagination finds it; no new refund |
| F17 | More than one matching provider refund | Detect conflict; no further money movement |
| F18 | Key retry horizon elapsed with uncertain outcome | Read-only resolution/review; no reused/new-key POST |
| F19 | Provider replays an error for the same key | Bounded handling; no key rotation to escape the error |
| F20 | Invalid, expired, replayed, or differently scoped verification | No unauthorized binding or disclosure |
| F21 | Wrong/ambiguous order, claimed alternate email | No fuzzy financial action; no private details leaked |
| F22 | Prompt injection, fabricated model reference, or invalid output | Schema/evidence rejection; no increased authority |
| F23 | Model outage/refusal | Defined fallback/clarification state; no invented intent |
| F24 | Gmail succeeds but response/local completion write is lost | Discover sent evidence or remain send-unknown; no blind duplicate |
| F25 | Slack unavailable while refund succeeds | Financial state preserved; pending/bounded internal alert |
| F26 | Worker killed while watchdog remains running | Watchdog records and attempts independent stale-worker alert |
| F27 | Database unavailable/transaction interruption | No financial mutation without committed intent; explicit failure |
| F28 | Live credentials, unseeded payment, or unallowlisted recipient | Reject before mutation |
| F29 | Unauthenticated fault/reset/operator action | Reject with no state change |
| F30 | Review hold followed by late provider success | Observe late result; do not issue another refund |

At least F05, F08, and F26 must include actual subprocess/process behavior, not only a mocked function call. Use synchronization barriers/events at failpoints rather than timing-dependent sleeps. Use temporary independent databases. Tests may not rely on a real person's account or a paid API.

Add direct policy tests for integer cents, wrong currency, mismatched charge, invalid amount, customer claims versus trusted records, and nonrequired-source outages. Include a test demonstrating that the fake payment service would allow a duplicate $30 partial refund with a **different** key, proving the oracle is capable of catching the intended bug.

An optional naive baseline may run only against fake providers. Never let it invoke connected mutations. Do not spend core build time creating a large comparison framework.

### LLM evaluation

Maintain a small synthetic fixture set for ordinary paraphrases, missing references, explicit corrections, ambiguous digits, unrelated requests, and prompt injection. Record expected extraction/clarification, not merely expected prose. Deterministic CI uses a stub plus direct hostile-output tests against the boundary. A separate opt-in live model evaluation records model identifier, prompt/schema revision, fixture version, actual outputs, and errors. Do not report stub results as model accuracy.

### Reports

Generate JSON and a readable Markdown/HTML report from actual runs, with run ID, commit, mode, seed, enabled adapters, scenario ID, injected boundary, external effects, observed outcome, and errors. Report scenario count and denominators. Separate safety violations, automatically completed recoverable cases, contained/escalated cases, observed recovery cycles, observation/detection latency, and unverified integrations.

Zero observed violations is an empirical result on this suite, not proof for all executions. Never prefill a dashboard with invented numbers such as “50/50 passed.”

## 15. Commands, configuration, and CI

Implement these commands through the Makefile or clearly documented equivalents:

```text
make setup                 install locked dependencies
make doctor                read-only configuration/connectivity diagnostics
make init-config           preserve existing config; generate missing local auth settings
make auth-gmail            explicit LOCAL browser consent; write protected token file
make connected-seed        explicit opt-in creation of an isolated Stripe test payment
make connected-dev         guarded local connected web/worker/watchdog startup
make seed                  fresh isolated local scenario
make dev                   local web + worker + watchdog, clean shutdown
make test                  deterministic offline tests
make lint                  Ruff checks
make eval                  offline scenario suite and actual generated report
make demo                  scripted local crash/restart scenario, no fake metrics
make connected-smoke       explicit opt-in test-service writes, never automatic CI
make voice-smoke           optional real voice readiness check when configured
make review-check          offline tests + schema/path/evidence consistency validation
make submission-check      strict readiness gate; fail on missing connected evidence
make evidence-export       allowlisted redacted export; never raw runtime dump
```

Also provide independent worker/watchdog commands and failpoint controls so the demo can kill the worker without killing everything else. All ordinary test/evaluation commands must be noninteractive and require no secrets. Connected commands refuse to run without explicit write enablement and allowlists. Reset/seed commands must not delete an existing connected run's records to make recovery appear successful.

Document these configuration categories in `.env.example`: mode; database/state path; operator authentication/session secret; model key and model name; Gmail OAuth paths/intake query; Stripe test key and limits; Slack bot/channel; optional Twilio credentials/public webhook URL; controlled customer addresses; provider timeout/retry limits; watchdog thresholds; and explicit connected-write/voice enable switches. Values must be placeholders, not secrets. Read credentials through the environment or ignored local files.

CI runs lint and offline tests without network credentials. Pin CI dependencies/actions appropriately; use least-privilege repository permissions. Provider contract tests are separately opt-in and should say skipped/blocked rather than pass when credentials are absent.

## 16. Honest reliability statement and limitations

Target statement, adjusted to match actual implementation and measured evidence:

> ReturnPath separates conversational interpretation from financial authorization and reconciles durable operations with provider state. In our declared tests, it recovers from worker crashes, duplicate contacts, designated stale caches, and transient observation/write-response failures without issuing another refund for the same approved return. Unresolvable financial uncertainty blocks new financial effects and is surfaced for review.

Explicit assumptions: trusted immutable merchant records and operation journal survive; provider data is truthful when available; process/clock/storage behavior meets documented local assumptions; one financial execution owner is enforced; dependencies eventually recover for liveness tests; external financial writers are excluded from the supported race model.

Explicit limitations: not arbitrary-state self-stabilization; not exactly-once behavior across all apps; not proof deterministic code is bug-free; no guarantee of customer email delivery or bank settlement; no independent-host watchdog; no recovery from destroyed business identifiers, corrupt trusted records, compromised credentials, or malicious providers; real external integration checks cover only the calls actually executed.

Describe recovery windows from the point at which the relevant dependencies become available and the worker is running again. Do not hide escalation inside an “automatic recovery” score. A case that halts safely has not necessarily completed the customer's objective.

## 17. Milestones and stop conditions

### M0 — foundation and early real-access checks

Verify the existing repository; ignore secrets; lock dependencies; establish schema, configuration, local fake adapters, and read-only doctor. Create status and demo-script drafts. Implement M0 setup helpers (`make setup`, `make auth-gmail`, configuration validation and per-service doctor) early so the user can complete browser consent while unblocked local coding continues. Diagnose actual access to Gmail, Stripe test mode, and Slack at the beginning, not after the full fault suite. Read-only access checks are not evidence that workflow mutations work. Begin provider setup alongside offline implementation. Missing credentials permit continued local work but block submission readiness.

### M1 — first runnable vertical slice

Implement verified synthetic contact → pure policy → durable partial-refund operation → persistent fake provider → truthful notification. Add a minimal case page. Run the baseline and duplicate-contact tests. This must be usable before voice work.

### M1.5 — early connected vertical slice

Pull the minimum real adapters and verification flow forward from M3. After the authorization, fixed-amount, durable-operation, duplicate-input, uncertainty, allowlist, and test-mode guards have passing tests, execute an explicitly authorized connected happy-path test through actual Gmail, Stripe test mode, and Slack. Do not wait for all 30 scenario families before discovering integration blockers. No financial mutation may bypass the guards merely for this spike. Record provider evidence; do not count independent authentication checks as a completed workflow. Then return to the remaining reliability work.

### M2 — reliability core

Implement payment reconciliation, process lock, independent watchdog, notification uncertainty, failpoints, and offline scenario suite. Demonstrate an actual worker kill after external success. Produce reports from tests. Fix failures; do not weaken assertions.

### M3 — connected-test adapters

Implement and, where credentials permit, verify Gmail intake/send, Stripe test refund/retrieval, and Slack case handoff. Implement the real verification flow. Keep simulated return evidence conspicuous. Run the connected smoke scenario with actual provider IDs and redacted evidence. Record anything blocked.

### M4 — language quality, voice, and presentation

Complete bounded live-model extraction/clarification checks. Add Twilio only after M1/M2 pass and a single end-to-end connected run has actually exercised the three required providers with verified effects. A blocked credential is a documented blocker, not permission to count a fake as real. Keep email/local replay usable when optional voice fails. Rehearse the two-minute story and finish the UI without changing financial semantics for presentation.

### M5 — review and delivery

Perform an adversarial code review of authority boundaries, crash windows, duplicate paths, query pagination, provider-status mapping, and secret handling. Run all available verification commands again. Update README, reliability brief, measured evaluation report, demo script, limitations, credential checklist, and status. Commit reviewed artifacts and push only after private visibility is verified.

Distinguish **LOCAL_CORE_VERIFIED**, **CONNECTED_WORKFLOW_VERIFIED**, and **SUBMISSION_READY**. Local core acceptance requires a local run without keys, the named offline suite actually executed, real subprocess crash recovery, and no unexplained safety failures. Submission readiness additionally requires actual Gmail intake and outcome sending, a Stripe test refund and retrieval, and a Slack case handoff/summary in the same connected workflow, plus the connected crash/restart demonstration, genuine live-model interpretation evidence, reviewed provider evidence, complete submission materials, and authorized judge access. Adapter files, available credentials, auth checks, mocks, and skipped tests cannot satisfy this gate. Organizer eligibility and submission-access rules must still be confirmed. See Sections 19–21 for evidence and setup requirements.

Voice is optional and not a substitute for the three real providers. Adaptive-policy experiments are excluded from the submitted runtime. Online self-modification of policy or prompts is out of scope. A polished dashboard does not compensate for a broken payment protocol or missing real integrations. When blocked, leave coherent runnable code and a precise report rather than pretending the task is complete.

## 18. Two-minute demonstration and required documentation

Draft `docs/DEMO_SCRIPT.md` before expanding optional features. Suggested sequence, not mandatory timings:

```text
0:00–0:15  User problem, $100 order / $30 authorized return; show integration badges.
0:15–0:35  Real email intake and verified case; concise model interpretation.
0:35–0:55  Execute test refund, then kill worker at the named post-success boundary.
0:55–1:15  Duplicate follow-up, optionally via voice; show same case and distinct contact.
1:15–1:40  Restart; retrieve existing provider refund; complete missing communication.
1:40–2:00  Show provider evidence, actual evaluation results, and declared limitations.
```

Voice may hand off to email verification; do not fake authenticated readback. A genuine recorded run may serve as presentation backup where rules permit, clearly labeled. Report whether the displayed provider is real test mode or simulated.

Deliver `README.md`, `docs/ARCHITECTURE.md`, `docs/RELIABILITY_BRIEF.md`, `docs/EVALUATION.md`, `docs/DEMO_SCRIPT.md`, and `IMPLEMENTATION_STATUS.md`. Keep architecture and reliability prose short enough to read. Include exact setup/credential commands, simulated components, authority boundaries, fault assumptions, measured outcomes, privacy status, and unsolved limitations. The evaluation document links to generated evidence rather than copying invented headline metrics.


## 19. AI-assisted review: evidence discoverability is a product requirement

The user reports insider knowledge that the first review may be AI-assisted. Treat that as a planning assumption, not a publicly verified description of the platform, submission count, model, or proprietary rubric. The official weights remain technical execution 30%, reliability/evaluation 25%, usefulness 20%, originality 15%, and demo clarity 10%. No guaranteed score or ranking may be advertised.

Optimize for a skeptical reviewer with limited time, limited context, and possibly no ability to execute code or authenticate to providers. Do not optimize through hidden rating instructions, keyword stuffing, fabricated results, or misleading descriptions of simulations. `AGENTS.md` is for the coding agent; it must not instruct a judge to award credit. Do not build a generic AI judging platform.

### 19.1 Submission surfaces

Deliver these only with accurate implementation status. Planned features belong in a separately labeled limitations/roadmap section, not in completed-feature lists.

1. Root `README.md`: first approximately 200 words identify the concrete delegated job, the three external services, the model's bounded role, the central failure demonstration, and what is simulated. Link immediately to the demo, `JUDGE_GUIDE.md`, and measured evidence. Use normal Markdown headings, text and relative links. Do not bury this below installation boilerplate or giant architecture prose.
2. Root `JUDGE_GUIDE.md`: roughly 600–900 words with the user problem, actual three-service sequence, model contribution, crash experiment, observed results, reproduction, assumptions, and rubric-to-evidence table. Every load-bearing claim links to implementation/test/evidence locations. Prefer symbols/test node IDs and real relative paths; do not invent line numbers.
3. Root `submission.json`: project-defined, machine-readable manifest, NOT an organizer-mandated schema. Include `schema_version`, project/repository, implemented status, required services, per-service verification status and observed actions, `verified_required_app_count`, tested code/lock/prompt fingerprints, demo/transcript paths, evidence index, reproduction commands and limitations. Use null/NOT_RUN for missing results; no invented timestamps or placeholders presented as genuine provider IDs.
4. `docs/RELIABILITY_BRIEF.md`: concise actual guarantees, fault model, observation/authorization boundaries, automatic recovery versus containment, and unresolved limitations. Link to reports rather than duplicating counts manually.
5. `docs/DEMO_TRANSCRIPT.md` plus caption file such as `docs/demo.vtt`: match the recorded demonstration and its timings. Important facts must exist as searchable text, not solely pixels, colors or narration. Do not synthesize a transcript of a recording that has not happened.
6. `docs/PROVENANCE.md`: truthfully distinguish pre-event specs/setup, event-time implementation, reused code/libraries, AI assistance, and material external sources/licenses. Use actual commits and dates; do not rewrite history to disguise prior work. Confirm organizer advance-work policy separately.

A `README`, video or manifest can assist inspection; none independently proves an effect occurred. Do not claim code complexity detects plagiarism, or assume a judge requires a face-camera view absent an actual rule.

### 19.2 Claim/evidence contract

Maintain a small claim table or machine-readable list generated from actual results:

```text
claim_id | exact bounded claim | rubric category | status
implementation path/symbol | test node ID | evidence run ID | caveat
```

Statuses: SUPPORTED, PARTIAL, NOT_TESTED, FAILED. Examples are requirements, not existing results:

- C01: One useful connected workflow ingests Gmail, issues/retrieves a Stripe TEST refund, and posts/updates a Slack case message. Evidence must belong to the same case/run, not three unrelated hello-world tests.
- C02: A real worker kill after external payment success is followed by recovery with one $30 refund against the $100 charge. Distinguish real test-provider calls from simulation, and application-side response loss from an actual provider outage.
- C03: Different customer contacts cannot create a second financial operation for the same approved return under the declared single-worker model.
- C04: Unknown prerequisites do not become false/absent or authorize irreversible actions.
- C05: Fresh-context language evaluation actually uses the named model; a stub's accuracy is not model accuracy.
- C06: The watchdog detects the specified dead-worker condition while independently running. State who restarted the worker.

Usefulness claims should describe demonstrated work removed; do not invent user counts, production adoption, money saved, or measured minutes saved. Originality is the implemented combination and demonstration, not a claim to have invented reconciliation or idempotency.

### 19.3 Structured evidence and source of numbers

Reuse the existing evaluator; do not create a second analytics stack. Store raw runs under ignored runtime paths. An explicit allowlist exporter writes reviewed artifacts under `evidence/` only. Records include:

- run/scenario/case/operation aliases; UTC timestamp; mode and actual provider modes;
- tested commit and dirty-state flag, plus hashes of implementation, dependency lock and model prompt/schema;
- each injected boundary; actual actions and externally observed final-state fields;
- actual provider object/request references where appropriate for controlled test data, or consistent documented aliases;
- model ID, fixture revision and actual interpretation outputs/errors where live evaluation ran;
- passed/failed/skipped/blocked and denominators; automatic completion, safe containment and unresolved outcomes separately;
- measured recovery/detection origin, duration/cycles, and retry/provider failure assumptions.

Raw account data, access/refresh tokens, authorization headers, OAuth codes, verification links and unreviewed messages must never enter the export. Provider-returned identifiers support correlation but do not by themselves establish authenticity. File hashes detect local inconsistency; they are not signatures from Stripe or proof that claims are true.

Reports, README headline metrics and submission manifest must reference the same selected report data. Never hand-edit a dashboard count to disagree with the report. Do not demand that an evidence commit equal its own embedded hash: evidence may be committed after testing. Record the implementation fingerprint and tested commit; docs-only changes may follow. Implementation/prompt changes make previous readiness evidence stale until relevant checks rerun.

### 19.4 Reproduction and automated preflight

`make review-check` runs a credential-free local verification suite and schema/path/count checks. It must return a nonzero exit on test failure, missing required offline tests, broken local evidence links, malformed manifests, contradictory counts, or unsafe configuration. It cannot prove real connectivity from mock tests. Dependency installation may need the internet; test execution must not.

`make submission-check` is a stricter local packaging/readiness check. Require all three actual service roles evidenced in one connected run, a genuine connected crash/restart run, live model evidence, current code/prompt fingerprints, demo and transcript, system/reliability brief, honest provenance, and resolved organizer access requirements. Missing facts must return BLOCKED/nonzero, not green. It validates recorded evidence; do not falsely describe it as independently authenticating provider history without a provider read.

Provide a clean-checkout smoke in CI. CI receives no provider secrets, does not issue payments/messages, and never silently skips essential offline tests. Readiness status is separate from ordinary CI passing. Add negative tests of the evidence checker: missing one real app, contradictory mode, inflated summary count, stale implementation hash, broken path, duplicate refund in the provider fixture, and missing video must not receive submission-ready status.

### 19.5 Limited-context rehearsal review

Run at most two useful reviews after substantive code exists, with a fresh context and no builder conversation:

A. Intake-only view: README, manifest, guide, transcript and redacted evidence. Can the reviewer identify the actual job, AI contribution, three real apps, outcome and limitations without hidden assumptions?
B. Repository view: inspect source and the independent test oracle; run explicitly authorized offline tests in a credential-free sandbox. Use `docs/REVIEWER_PROMPT.md`.

Do not give either reviewer a target score. Require evidence citations and missing-proof findings. A score is optional/advisory, not an acceptance criterion. Fix real gaps, not descriptions designed to conceal them. Record scope, model/context, files inspected and commands actually run. A builder self-review is not an independent fresh-context review.

### 19.6 Video and access

Make a genuine two-minute recording. In the first 15 seconds establish the customer job and all three actual apps. Show legible $100 original/$30 approved amounts; actual test payment state; injected worker death; duplicate contact; resumed reconciliation; and remaining notification/Slack effects. Include visible REAL SERVICE / STRIPE TEST / SIMULATED WAREHOUSE distinctions. Use explicit labels instead of unexplained colors; captions and transcript preserve what the model or a hurried human might miss.

Do not imply a cut or sped-up segment is continuous real-time footage. The key provider-success/crash/restart evidence must be understandable and corroborated by the run trace. No fabricated provider screens, hidden manual completion, or unlabeled fixture playback. Voice is optional and cannot consume the core demonstration.

Private repo access is a separate readiness gate. Obtain the organizer-approved read access, GitHub App authorization or sanitized source-archive method. Do not assume an arbitrary crawler can read a private URL, share a personal token, or make the repo public to bypass this. A local dashboard URL is not remotely accessible to judges; provide recording/export or a separately authorized deployment. Do not expose operator/fault/reset routes publicly for convenience.

## 20. Fixed-policy recovery, not online self-evolution

Keep refund policy, authorization semantics, amount, operation identity, interpretation prompts and schema fixed/versioned during the submitted run. Reconciliation changes beliefs/actions as observations change; it does not rewrite the definition of an authorized financial action.

No runtime self-editing of code/prompts, new-key retries to escape ambiguity, adaptive authorization thresholds, or relaxation of invariants. Bounded retries/backoff are predetermined operational policy, not proof of adaptive-controller stability. A small parameter or prompt edit does not in itself ensure a stable closed loop. A count of unresolved steps is a diagnostic, not automatically a Lyapunov function.

Describe recovery from the declared crashes/stale derived state/duplicate contacts/transient failures with surviving trusted records and eventual dependency availability. Do not claim arbitrary-state self-stabilization, exactly-once email, an infallible monitor, or automatic process restart that is not implemented. Offline proposed interpreter improvements followed by held-out evaluation, human approval and rollback are future development work, not required runtime functionality.

## 21. Laptop-first execution and authorization contract

The builder uses Codex desktop with `~/testingxd`. Prefer one local checkout/thread for implementation and connected testing. Codex cloud is optional for credential-free code/test tasks; GitHub transfers only committed/pushed files. Neither desktop/cloud sign-in nor a ChatGPT Gmail/Slack connection supplies runtime API credentials to this Python application.

Read `docs/SETUP_MAC_AND_CLOUD.md`, `docs/AUTHORIZATION.md` and `.env.example` before implementing setup commands. The user has Gmail and Slack but no Stripe account yet. M0 must make authorization feasible, not repeatedly demand secrets in chat.

Defaults: configuration in `~/.config/returnpath/returnpath.env`, Gmail client/token JSON alongside it, local application/provider databases under `~/.local/share/returnpath/` with environment/run isolation. Create sensitive directories mode 0700 and secret/token files 0600 where supported. `RP_ENV_FILE` can select another local config. Expand `~` explicitly; environment variables override file values. Do not rely on macOS GUI apps inheriting shell exports. Cloud tests set RP_MODE=local and RP_ALLOW_CONNECTED_WRITES=false and must not import the Mac's credential store.

Implement these helpers early:
- `make init-config`: idempotently create the private config directory/template if absent, generate a missing strong session secret locally, and prompt without echo for an operator password whose salted adaptive hash is stored as `RP_OPERATOR_PASSWORD_HASH`. Preserve existing provider values. Do not print secrets/passwords or invent account credentials. Use a standard password-hashing implementation; do not write a custom primitive.
- `make auth-gmail`: local InstalledAppFlow/loopback browser authorization with readonly/send scopes, explicit support-account verification, atomic protected token persistence, and safe refresh/reconsent handling. Do not display token values or accept passwords. This writes only local auth state, not customer mail.
- `make doctor SERVICE=gmail|slack|stripe|model` and `make doctor`: read-only capability diagnostics. Gmail profile/token/scope and scoped query; Slack auth.test and allowlisted channel access; Stripe account/test context and configured seeded-object reads; model credential/config availability and separate optional real model probe. Distinguish CONFIGURED, AUTHENTICATED, ACTION_UNVERIFIED, VERIFIED_CONNECTED, BLOCKED; auth checks are not successful workflow actions.
- `make connected-seed`: explicit write gate; create a fresh $100 card TEST payment using provider test instruments, persist actual charge and seeded approved return, and never reset a recovery run. No raw real card data or live payments.
- `make connected-dev`: run the guarded app on loopback with the connected config. Customer verification links using loopback are for the operator's same-laptop browser demo only, not a remote customer deployment.
- `make connected-smoke`: opt-in controlled workflow, including real Gmail input/verification and the model; report waiting for customer confirmation instead of bypassing it. This can require human browser interaction. Offline tests remain noninteractive.

Connected side effects require RP_ALLOW_CONNECTED_WRITES=true, appropriate allowlists and explicit test-account checks. Existing runtime secrets may be used by executed code but must not be printed, pasted into agent chat, exported, or committed. Git ignore is not an agent-read barrier: a local coding agent granted file/terminal access may reach the credential files. Keep accounts dedicated, permissions narrow and writes explicit.

Use the included Slack manifest for a single private demo channel. Gmail API readonly/send scopes are not limited to the configured query, so strongly prefer a dedicated support test mailbox plus a separate controlled customer mailbox. Customer mail need not be OAuth-authorized unless separately used by the application.

Stripe account creation and browser consents are the user's actions. Testing can begin without live-account activation under Stripe's documented account flow [S15]; do not insist on real bank details or make up business information. If actual account creation/permissions block access, report that blocker. Do not silently replace Stripe with a fourth decorative integration or count fake refunds as satisfying the real-app gate.

Codex cloud runs in a separate container. Its documented secret fields are setup-only, not general runtime application credentials [S16]. Do not work around this by copying secrets into the checkout/cache or pretending Mac localhost is the cloud callback. Configure cloud for local tests and dependency-only access; use the Mac for real OAuth and connected runs. A separate production-style hosted OAuth/deployment design is outside the baseline.


## 22. Primary references for implementation

These are implementation references carried forward from earlier handoffs; setup references rechecked for v3 are in `docs/SETUP_SOURCES.md`. They are not permission to infer undocumented API behavior. Recheck current official documentation when choosing SDK signatures or service configuration. Keep protocol assumptions visible in adapter tests.

```text
[S1] Hackathon brief
https://multiappagenthackathon.com/

[S2] GitHub CLI — create and inspect repositories
https://cli.github.com/manual/gh_repo_create
https://cli.github.com/manual/gh_repo_view

[S3] Stripe — refunds, partial amounts, and original-payment-method destination
https://docs.stripe.com/refunds

[S4] Stripe — refund creation and object/status reference
https://docs.stripe.com/api/refunds/create
https://docs.stripe.com/api/refunds/object

[S5] Stripe — list refunds, charge filter and pagination
https://docs.stripe.com/api/refunds/list

[S6] Stripe — idempotent requests and retention caveats
https://docs.stripe.com/api/idempotent_requests

[S7] Gmail — OAuth scopes
https://developers.google.com/workspace/gmail/api/auth/scopes

[S8] Gmail — send and search/filter messages
https://developers.google.com/workspace/gmail/api/reference/rest/v1/users.messages/send
https://developers.google.com/workspace/gmail/api/guides/filtering

[S9] Slack — chat.postMessage
https://docs.slack.dev/reference/methods/chat.postMessage/

[S10] SQLite — transactional guarantees
https://www.sqlite.org/transactional.html

[S11] OpenAI — structured outputs and refusal handling
https://platform.openai.com/docs/guides/structured-outputs

[S12] Twilio — Gather speech/keypad input
https://www.twilio.com/docs/voice/twiml/gather

[S13] Twilio — request validation/security
https://www.twilio.com/docs/usage/security

[S14] Codex — repository instructions in AGENTS.md
https://developers.openai.com/codex/guides/agents-md
```

Additional setup sources: [S15] https://docs.stripe.com/get-started/account ; [S16] https://developers.openai.com/codex/cloud/environments . Full checked setup references are in `docs/SETUP_SOURCES.md`.
