# ReturnPath

## 1. What it does

ReturnPath helps a customer get a return or refund resolved without repeating the same story to support.

A customer can write “the package was broken,” “damanged item,” or describe the problem in their own words. One AI agent helps explain what the customer wants. A second represents the merchant and offers only the options the merchant allows. If something is unclear, they ask a question. The customer reviews and accepts the exact terms.

**Why two agents?** The customer and merchant have different needs. Showing both sides makes it clear what was requested, what was offered and what was agreed.

**Why separate agreement from payment?** A persuasive message is not permission to move money. Code checks the accepted terms, records the operation before sending it, and checks the payment provider afterward. After an interruption, it should find an existing refund rather than create another one.

### What works today

- **Try a resolution:** customer and operator pages, natural-language conversations, different merchant-approved offers, saved agreements and simulated refunds. Offers come from [merchant settings](config/resolutions.json), not amounts invented by an agent.
- **Real app demonstration:** Gmail intake and verification, a $30 Stripe TEST refund on a $100 payment, a customer email and a Slack update. [All three were checked in the same run](evidence/connected-ordinary-run.json).

**Still to finish:** connecting negotiated offers to Stripe, testing a crash during a real Stripe run, free hosting and the demo video. The negotiated-offer playground currently uses simulated payments. The fixed $30 example remains a repeatable test of duplicate-refund prevention.

## 2. External apps

| App | Why we use it |
|---|---|
| Gmail | Customers can contact support by email and receive verification and refund updates. |
| Stripe | Creates the TEST refund and provides records we can check independently. |
| Slack | Gives the support operator a case update, supporting facts and the next action. |

These are the three connected apps. The model API and simulated warehouse do not count as additional apps. No real money is moved.

## 3. Run it

Requires Python 3.12. Setup uses a project-specific environment and locked dependencies so installations are repeatable.

```bash
cd ~/testingxd
make setup
make init-config
make playground
```

Open **http://127.0.0.1:8001/playground**. The default uses a simple offline test substitute for the AI.

For real AI conversations, follow the [credentials checklist](docs/CREDENTIALS_CHECKLIST.md), set `RP_MODE=connected-test` in the private configuration, then run:

```bash
RP_RESOLUTION_MODEL=live make playground
```

Choose a purchase, describe the problem, answer any questions and accept an offer. For the operator view, open `/login`, then `/resolutions`. Use a separate browser profile to keep customer and operator sessions separate.

For the Gmail/Stripe/Slack demonstration, complete the same checklist, enable controlled TEST writes and run:

```bash
make doctor
make connected-seed    # once for a NEW test case only
make connected-dev
```

Send an email from the configured customer mailbox with `order 4127` in the body, then confirm the emailed verification link. **For an existing case, restart with only `make connected-dev`. Never reseed it.** Stop with Ctrl+C.

Keep passwords, API keys and Gmail tokens outside the repository. We use SQLite to keep the local setup small and preserve records across restarts. A free hosted version needs separate persistent storage; no public deployment is running yet. Paid hosting is not being provisioned.

## 4. How we check reliability

```bash
make test
make lint
make demo
make review-check
make stripe-oracle    # independently reads the existing Stripe TEST refund
make submission-check
```

- **77 tests passed:** [test report](evidence/offline-evaluation.md). Checks include customer access, changed or expired offers, repeated acceptance and repeated refund attempts.
- **Local crash test passed:** [recorded result](evidence/local-demo.json). A process is killed after the simulated provider saves a refund, then restarted. The independent check finds one refund. This has not yet been repeated with Stripe.
- **Real Stripe check passed:** one $30 refund on the $100 TEST payment, verified from provider records rather than the app's success label.
- **Four language examples passed:** [actual model results](evidence/language-smoke.json), including typos and clarification replies. This is a small check, not proof that every conversation works.

The watchdog detects and alerts; a person restarts the worker. Uncertain email delivery is not treated as proof that sending failed. Gmail changed our supplied Message-ID, so recovery from an uncertain send still needs work.

Missing evidence keeps `submission-check` blocked. See the [reliability notes](docs/RELIABILITY_BRIEF.md), [implementation status](IMPLEMENTATION_STATUS.md) and [submission manifest](submission.json) for details.

## 5. Demo video

**Not recorded yet.** The final video will be no longer than two minutes and linked here. It will show the customer request, agent responses, the three apps and the failure/recovery test, with simulated parts clearly labeled. [Recording plan](docs/DEMO_SCRIPT.md).

[Build history and AI assistance](docs/PROVENANCE.md) · [Reviewer guide](JUDGE_GUIDE.md)
