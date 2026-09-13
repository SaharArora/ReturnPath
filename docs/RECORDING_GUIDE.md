# Recording guide — proposed narration, not a transcript

Use [the workflow visual](images/returnpath-workflow.svg) for the opening. It compares product scope with Poke, made by The Interaction Company of California, not unpublished safety implementations. Do not describe the local app as deployed or the simulated ledger as Stripe.

## Ready-to-record script for the current verified state

**0:00–0:15 — Show the workflow visual.**

“ReturnPath helps a customer and merchant agree on a return resolution, then checks that the agreed action actually happened. General assistants focus on everyday tasks. We focus on making the offer, approval and payment evidence visible.”

**0:15–0:45 — Show localhost:8001/playground and an actual conversation.**

“Here I describe a damaged item in my own words. The customer agent helps clarify what I want. The merchant agent can offer only the options in the merchant's saved rules. The customer chooses and accepts exact terms. The model cannot invent a refund amount or approve its own offer.”

**0:45–1:10 — Show the original Stripe TEST refund, Gmail and Slack.**

“This separate connected run verified Gmail intake, a thirty-dollar Stripe TEST refund and a Slack case update. We checked provider records, not just the app's success message. The accepted-offer connection is now implemented, but its new payment run is still awaiting customer verification and return evidence.”

**1:10–1:40 — Show the actual `make demo` output, clearly labeled LOCAL SIMULATOR.**

“In this local failure test, the provider saves the refund and we kill the worker before it records completion. Another contact arrives. The watchdog alerts, and the harness restarts the worker without clearing records. It finds the existing refund. An independent check still finds one refund, not two. The real Stripe crash test is still pending.”

**1:40–1:55 — Return to the visual or evaluation results.**

“Eighty-two automated tests pass. This is a single-machine prototype with simulated warehouse evidence, not a claim of unlimited reliability. The aim is simple: useful conversations, explicit permission and results you can check.”

This is a proposed script, not evidence of a recorded run. Describe only actions visible in your actual recording. If new connected verification completes, update that passage to its observed result.

## Suggested two-minute structure

**0:00–0:15 — Problem and scope.** Show the visual.

> “A return can get stuck between what the customer wants, what the merchant permits, and whether the refund actually happened. ReturnPath makes those steps explicit. Unlike a broad everyday-assistant product, we focus on one job and make the agreement and payment evidence inspectable.”

**0:15–0:45 — Agent behavior.** Show the localhost customer page. Start a fresh request with a natural description, answer its clarification, and show both agent responses. Use the wording that actually occurs.

> “The customer's agent clarifies what matters to them. The merchant's agent can offer only the options in the merchant's saved rules. Neither can invent an amount or accept on the customer's behalf. Here, the customer reviews and accepts these exact terms.”

Point out one useful clarification or grounded offer from the actual run. Avoid reading every line of conversation. An explanation shown by an agent is not proof that its action was authorized; the code checks the selected offer independently.

**0:45–1:10 — Real action.** After the new connected path has actually passed, show the agreement, trusted-mailbox confirmation and the matching Stripe TEST payment/refund. Then show Gmail and Slack.

> “The execution code checks the agreed terms and customer verification. It saves the payment operation before calling Stripe, then retrieves the provider's result. Gmail informs the customer and Slack gives the operator the evidence and next action.”

Until that full path is verified, describe the existing fixed $30 connected run separately. Do not edit two unrelated runs together to imply a single continuous agreement-to-refund demonstration.

**1:10–1:45 — Failure and recovery.** Use the genuine connected crash recording once available. Show the named boundary, kill, another contact, manual restart and independent provider count.

> “Now the worker dies after Stripe accepts the refund but before completion is saved locally. The watchdog alerts; I restart the worker. It retrieves the existing refund using the saved operation identity. The independent check must still find one refund, not two.”

Do not use this narration over a simulated crash without saying it is simulated. No automatic restart is implemented. Speed-ups or cuts should be labeled.

**1:45–2:00 — Result and honest scope.** Show the generated evaluation and the independent provider result.

> “The important result is what the provider records show after failure. These tests cover our stated single-worker setup; they do not prove every possible failure or distributed scale. The payment is Stripe TEST and warehouse evidence is simulated.”

## Before recording

- Finish the connected agreement run and crash test; capture actual results rather than narrating planned behavior.
- Use controlled demo accounts. Hide credentials and verification URLs, including browser address bars while a token is visible.
- Keep readable app names, accepted amounts and provider results on screen.
- Save a clean original recording. Create the final transcript and captions from what was actually said and shown.
- Add the final video link to README yourself, as requested. Keep the total at or below two minutes.
