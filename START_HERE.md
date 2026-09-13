# ReturnPath v3 — start here

This package is an implementation handoff, not a finished application. The bundled installer and cloud bootstrap are real utilities; `make auth-gmail`, `make doctor` and the application do not exist until Codex implements them. Old v1/v2 contract text is superseded by BUILD_SPEC.md v3.

## Recommended path

Use the Codex desktop app with the existing `~/testingxd` folder. Keep real Gmail OAuth and the connected demo on this Mac. Use Codex cloud only for credential-free code/tests or a separate review. Do not run two writers on the same branch.

1. Install the v3 payload with the ZIP's `install_handoff.py` (backs up prior instruction files outside the repo and merges `.gitignore`). It performs no commit, push, authorization or account changes.
2. Open `~/testingxd` in Codex desktop in local mode. Paste CODEX_KICKOFF_PROMPT.md. Ask it to make M0 setup/authorization helpers usable first, while continuing unblocked implementation.
3. Follow docs/AUTHORIZATION.md: create Stripe TEST access; install the Slack bot in a private demo channel; create a Google OAuth Desktop client and authorize the support mailbox locally; configure the model API separately.
4. Follow docs/SETUP_MAC_AND_CLOUD.md for Git commit/push and optional Codex web environment setup.
5. Keep secrets in `~/.config/returnpath`, not chat or Git. Allow real test writes only after the guards pass and you explicitly enable them.

## Core acceptance experiment

A $30 refund on a $100 test charge commits externally. Kill the worker before local completion. Ingest a duplicate contact. Restart without reset. Verify one $30 refund in provider state and complete the remaining work. Gmail, Stripe TEST, and Slack must participate in one real workflow; local warehouse evidence is visibly simulated.

## First Codex message

Use CODEX_KICKOFF_PROMPT.md in full. It fixes repository identity, setup order, real-app requirements, reliability boundaries, reviewer evidence and fixed-policy runtime behavior.

## Before submitting

Confirm organizer rules on advance work, Stripe test/sandbox use and private-source access. The code/specs and connected integrations are not verified merely because this package exists. Submission status must be generated from actual results. No account or GitHub permission has been changed by this handoff.
