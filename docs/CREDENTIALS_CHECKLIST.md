# One credentials checklist

Run locally in `~/testingxd`: `make setup`, then `make init-config`. The latter prompts privately for your operator password and preserves existing provider settings. Edit `~/.config/returnpath/returnpath.env` in a local text editor. Never paste credentials into chat.

- Gmail: dedicated support mailbox and separate controlled customer address. Enable Gmail API, configure External/Testing with the support test user, download Desktop OAuth JSON to `~/.config/returnpath/gmail-client.json`. Set both email addresses; run `make auth-gmail` and complete browser consent yourself. Scopes: readonly + send.
- Slack: use the supplied manifest, install the bot, invite it into one private demo channel. Save bot token and channel ID locally.
- Stripe: create your account yourself, use TEST/Sandbox access. Save test secret key locally. Run the Stripe doctor and record the confirmed account ID as `RP_STRIPE_ACCOUNT_ID`. No live activation needed for the intended test flow.
- Model: save a separately authorized API key and available model identifier locally. Codex sign-in does not supply these.
- Run `make doctor SERVICE=gmail`, `SERVICE=slack`, `SERVICE=stripe`, and `SERVICE=model`. These do not perform workflow writes. Model doctor only checks configuration.
- Keep writes disabled until safety tests pass. Browser consent and account creation remain your actions. Detailed provider steps: [AUTHORIZATION.md](AUTHORIZATION.md).

Connected workflow and recording remain unverified until actual same-run provider evidence exists.
