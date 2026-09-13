# Hosting the playground on Render

Status: configuration prepared and local boundary tests passed; no service purchased or deployed.

Use a single paid Python web service with a 1 GB persistent disk. Review Render's current quote before applying: https://render.com/docs/disks . Free web services cannot preserve this SQLite data with a persistent disk. Keep one instance and one Uvicorn worker.

1. Create/sign into your Render account at https://dashboard.render.com/ .
2. Connect GitHub and grant Render access only to the existing private `SaharArora/testingxd` repository. Keep the repository private.
3. Once `render.yaml` is pushed, choose **New → Blueprint**, select that repository and `main`. Review the paid service and disk before applying.
4. Enter the requested secrets directly in Render:
   - `OPENAI_API_KEY`: a separate deployment API project key with a small budget; never upload the Mac configuration or Gmail token files.
   - `RP_OPERATOR_PASSWORD`: a new hosted operator password, at least 12 characters.
   - `RP_MODEL`: choose a model available to the deployment API project; the blueprint starts with `gpt-4o-mini`.
   Render generates the separate session secret. The app reads Render's assigned hostname automatically.
5. Deploy and visit the assigned HTTPS URL. `/health` must return `status: ok` and `payments: simulated`.
6. Open `/playground`, start a purchase request, describe damage in your own words, answer clarification, and accept exact terms.
7. In a separate browser profile, open `/login`, then `/resolutions`. Inspect and execute the simulated agreement. Never enter customer identity or financial provider credentials into this demo.
8. Restart the service, revisit the case in the original browser, and confirm the agreement persists. Reconcile again and inspect one simulated provider record.

The entry point refuses Stripe/Slack/Gmail credential variables and connected-write enablement. Connected case, warehouse and email-verification routes are absent. Secure session cookies require HTTPS. Only the exact assigned hostname is accepted. The persistent daily model budget is 100 calls per deployed state; requests have at most three rounds. This is a bounded demo, not production abuse protection or a real-money service. Failed/interrupted model rounds require inspection and never authorize payment.

Do not restore an old disk snapshot to erase operations or repeat effects. Do not copy Mac databases, OAuth files or environment files to Render. The connected Stripe experiment remains on the Mac until a separate identity/provider deployment design is implemented and verified.

Official references: https://render.com/docs/web-services , https://render.com/docs/disks , https://render.com/docs/blueprint-spec .
