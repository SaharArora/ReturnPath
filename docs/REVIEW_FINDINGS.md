# Fresh-context repository review

One read-only reviewer agent, separate context with no builder conversation, inspected the source/tests and `docs/REVIEWER_PROMPT.md`. It inherited the task model configuration; no separate model identifier was reported. Scope: financial authority, uncertainty, process ownership and independent oracle. No credentials were read and no connected actions ran.

Actual command: `RP_ENV_FILE=/dev/null RP_MODE=local RP_ALLOW_CONNECTED_WRITES=false .venv/bin/python -m pytest -q -p no:cacheprovider`. Reviewer result at that snapshot: 40 passed, two deprecation warnings, 5.17 seconds. This is not the final suite count.

Findings and builder follow-up:

- Launcher stopped surviving watchdog on worker death. Fixed launcher lifetime; added regression test. Standalone actual process watchdog test remains.
- Freshness compared the same timestamp to itself. Fixed observation-start versus decision-time clock; added delayed-read test. Added protected HTTP warehouse simulator observation for configured runtime.
- Persisted intake events stranded model/verification failures. Added durable bounded model call budget and rate-limited challenge replacement on rescans.
- Review/unknown evidence lacked actionable Slack handoff. Added deterministic review handoff independent of successful refund notification.
- Pagination test and fake retry semantics were too narrow. Added actual SDK HTTP transport pagination/failing-page tests and persistent error/expiry simulation.
- No connected evidence or completed packaging existed at review time. Packaging now explicitly records NOT_RUN/BLOCKED rather than claiming those effects.

The reviewer did not re-review the fixes or final packaging. Subsequent builder regression tests are not a second independent review. No rating/target score was requested or awarded.


## Second review: intake surfaces only

A second separate fresh-context reviewer read exactly README.md, JUDGE_GUIDE.md, submission.json, IMPLEMENTATION_STATUS.md, docs/RELIABILITY_BRIEF.md, docs/PROVENANCE.md, and the three selected evidence JSON/Markdown files. It ran no implementation or connected tests and did not read credentials. It found no substantive contradiction in job, model authority, simulation/real status, local outcome or limitations.

It identified a missing machine-readable link to the local demo and missing snapshot attribution in that trace. The builder added the evidence-index entry and run ID/UTC timestamp/commit/dirty-state/fingerprints to generated demo output, then reran the actual demo. At its snapshot the report contained 63 tests; later generated results supersede that count. No score was requested or assigned. These two reviews exhaust the planned review passes; fixes are checked by regression commands.
