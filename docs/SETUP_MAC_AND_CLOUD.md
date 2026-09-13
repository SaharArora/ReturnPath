# Mac, GitHub, Codex desktop and optional cloud setup

Checked September 13, 2026. Primary references are in SETUP_SOURCES.md. Product/menu names may vary slightly with app version; use the controls for the existing local folder or selected cloud repository. You do not need Codex CLI for the desktop workflow.

## A. Install these instructions in your existing checkout

Your earlier clone succeeded. An empty working-tree listing is normal before files are committed. Do not clone again or reinitialize Git.

Download `returnpath_codex_handoff_v3.zip` to Downloads, then run:

```bash
cd ~/testingxd
pwd
git status
git remote -v
unzip -n ~/Downloads/returnpath_codex_handoff_v3.zip -d ~/Downloads
python3 ~/Downloads/returnpath_codex_handoff_v3/install_handoff.py --repo ~/testingxd
```

The installer requires the existing Git root and the exact SaharArora/testingxd origin (HTTPS or SSH). It replaces only the handoff's named documentation/config templates/bootstrap, merging `.gitignore`. Changed files are backed up under `~/.returnpath_handoff_backups/`; unrelated application code is not touched. It never creates a remote, commits, pushes or requests account access. Use `--dry-run` to preview. If it finds an unrelated AGENTS.md or a conflicting path/symlink, it stops for manual reconciliation rather than overwriting.

## B. Open Codex desktop locally

1. Sign in to the installed desktop app with the account that has Codex access.
2. Use the folder/project picker to open `~/testingxd`. In a macOS folder dialog, Command-Shift-G opens Go to Folder; enter that path.
3. Choose local execution/checkout, not Cloud or an isolated worktree for this first build. This avoids a second checkout missing local setup files. Verify the working directory and origin in the first response.
4. Start one new coding conversation. Paste CODEX_KICKOFF_PROMPT.md. No Codex CLI command is required.
5. Let it edit the repository and run the documented local commands with normal permission prompts. Do not disable approvals or grant unrestricted access as a setup shortcut.
6. It must implement M0 first: setup, configuration loading, Gmail browser-auth helper and separate read-only service diagnostics. You can create provider accounts/clients while unblocked code is implemented. Actual consent cannot be delegated by pasting passwords.

The agent must not install into Conda `(base)`. It should use a project `.venv` with Python 3.12 and locked dependencies, with Make commands referencing that interpreter directly. If Python 3.12 is absent, it must give you one explicit installation choice rather than silently use an incompatible interpreter. When Homebrew is already available, `brew install python@3.12` is one option; do not install Homebrew or modify system Python just because another bootstrap option exists.

Keep a checkpoint before switching to a cloud task or worktree. Never have two agents edit the same checkout/branch simultaneously.

## C. Commit and push the handoff

Before pushing, confirm the GitHub repository displays PRIVATE, or use an already-authenticated GitHub CLI:

```bash
gh repo view SaharArora/testingxd --json nameWithOwner,visibility
```

No need to install GitHub CLI just for this if you can verify private visibility in GitHub and Git already pushes successfully. Local clone access, cloud authorization, and judge access are separate permissions.

Stage only these instruction/configuration files; do not use `git add .` on an uninspected workspace:

```bash
cd ~/testingxd
git add .gitignore .env.example AGENTS.md BUILD_SPEC.md CODEX_KICKOFF_PROMPT.md START_HERE.md REVIEW_AND_STABILITY_ADDENDUM.md
git add docs/SETUP_MAC_AND_CLOUD.md docs/AUTHORIZATION.md docs/REVIEWER_PROMPT.md docs/SETUP_SOURCES.md
git add config/slack-app-manifest.yaml scripts/codex_cloud_setup.sh
git diff --cached --stat
git diff --cached
```

Inspect the staged text for accidental credentials or unrelated files. Then:

```bash
git commit -m "Add ReturnPath v3 build and setup specifications"
git push -u origin HEAD
git branch --show-current
```

Use the displayed branch in cloud setup; do not assume it is `main`. If Git reports missing author identity, set `user.name` and `user.email` locally to the real identity/email you choose; do not invent one. If push authentication fails, resolve your authorized GitHub login/credential helper, not repository visibility. When GitHub CLI is installed, its browser flow `gh auth login` followed by `gh auth setup-git` is an option. Never put an access token in a remote URL or paste it in chat.

## D. Optional Codex web/cloud setup

This is a separate execution environment, not a hosted copy of the app running on your laptop.

1. Open `https://chatgpt.com/codex` in the browser and sign in.
2. Use the Codex GitHub connection/onboarding flow. Select the SaharArora account and authorize the existing `testingxd` repository. A generic read-only ChatGPT GitHub connection may not by itself provide the coding environment; use the actual Codex repository/environment flow.
3. If the repo is absent, open the linked GitHub App repository settings, ensure it is installed for the correct account and `testingxd` is selected, then refresh. Do not make a private repo public to make it appear. Local clone access does not imply this app was authorized.
4. Open Codex environment settings, create an environment for `SaharArora/testingxd`, and select the pushed branch or commit. Choose Python 3.12 in package/runtime settings.
5. Configure these NONSECRET environment variables:

```text
RP_MODE=local
RP_ALLOW_CONNECTED_WRITES=false
RP_ENABLE_VOICE=false
```

6. Use this setup command:

```bash
bash scripts/codex_cloud_setup.sh
```

The bundled script handles the initial specification-only repository without pretending tests ran. Once the Makefile exists it calls `make setup`; that target must install dependencies only, not seed or call external accounts. Run the same setup as maintenance if needed after dependency changes.

7. For an initial implementation task that may create dependency files after setup, allow agent internet access only to dependency sources `pypi.org` and `files.pythonhosted.org` as needed. Add official documentation domains only if needed for implementation research. Do not enable unrestricted access or provider write endpoints merely to remove an error. Setup-phase package installation already has network access. Offline test execution must prohibit non-loopback provider/model requests regardless of the cloud domain settings.
8. Leave Gmail/Slack/Stripe/model application secrets OUT of this cloud environment for this workflow. The documented cloud secret fields are available to setup, not generally the later agent phase. Do not copy them to `.env` or disk/cache as a workaround. Mac localhost callbacks do not reach a cloud container.
9. Start a task with the kickoff prompt plus: "This is the credential-free cloud phase. Implement/test local mode, report connected verification BLOCKED, and prepare a reviewable branch/PR. Do not perform external writes."
10. Review the diff and test results. Merge a reviewed PR through GitHub when appropriate. Once the local checkout is clean and on that base branch, pull:

```bash
cd ~/testingxd
git status
git pull --ff-only
```

Do not reset or overwrite local edits if Git refuses; reconcile them first. Then run connected authorization/tests locally using AUTHORIZATION.md. Cloud work does not automatically appear in your Mac checkout until Git synchronization occurs.

## E. Configuration on your laptop

After installing the handoff, create a private config directory. This command preserves an existing config rather than overwriting it:

```bash
cd ~/testingxd
mkdir -p ~/.config/returnpath
chmod 700 ~/.config/returnpath
if [ ! -f ~/.config/returnpath/returnpath.env ]; then
  cp .env.example ~/.config/returnpath/returnpath.env
fi
chmod 600 ~/.config/returnpath/returnpath.env
open -e ~/.config/returnpath/returnpath.env
```

Use plain text in the editor. Fill values only on the Mac, not in Codex chat. .env files are application data, not shell scripts; the program must parse the file and expand paths. Do not `source` untrusted config. Finder-launched apps do not necessarily inherit terminal exports, so the application explicitly reads its configured file. `RP_ENV_FILE` can point at a different private file; environment overrides must work for safe cloud/local tests.

A private repository is not a secret manager. Git ignore does not stop a locally permitted coding agent or subprocess reading credentials. Use dedicated test accounts, narrow scopes, allowlists and explicit writes. Do not grant app access to unrelated personal data.

## F. Commands after Codex implements M0 and the application

These are required interfaces in the spec, not pre-existing programs in this handoff:

```bash
cd ~/testingxd
make setup
make init-config
make auth-gmail
make doctor SERVICE=gmail
make doctor SERVICE=slack
make doctor SERVICE=stripe
make doctor SERVICE=model
make test
```

A `doctor` success is read-only auth/config capability, not proof that a full workflow works. If a command does not yet exist, complete M0 with Codex rather than guessing package names or flags.

After credentials/allowlists are correct, guards pass, and you intentionally set `RP_MODE=connected-test` and `RP_ALLOW_CONNECTED_WRITES=true` locally:

```bash
make connected-seed
make connected-dev
```

In another terminal, use the documented connected-smoke interaction or send the controlled customer email manually. `connected-seed` creates a new isolated test order/payment; never use it as a restart/recovery command. After the real demonstration, return write enablement to false. Offline CI/review tests must remain disconnected even when a local credential file exists.

## G. Common setup failures

| Symptom | Check |
|---|---|
| Empty `ls` after cloning | Normal for an empty repo; install files and commit once. |
| Cloud cannot see testingxd | Correct GitHub account/app install and explicit repo grant. |
| Code runs in desktop but not cloud | Pushed branch, package versions, dependency setup and no assumption of local tokens/files. |
| Desktop cannot find credentials after terminal export | Use the explicit private config file; verify path expansion. |
| Gmail 403 / access_denied | Correct test user, Gmail API enabled, right OAuth client and workspace policies. |
| Gmail invalid_grant later | Refresh-token expiry/revocation; reauthorize through the helper. |
| Slack channel_not_found / not_in_channel | Exact channel ID, bot invited, right workspace/token/scopes. |
| Stripe no test access | Correct sandbox/test context and account/key; do not switch to live keys. |
| Model auth/billing error | Runtime API project/key access is separate from Codex/ChatGPT subscription. |
| `make` target absent | Codex has not implemented that milestone yet. |

Before final submission arrange organizer-approved private source access or a sanitized archive, and verify advance-build rules. Neither publishing the repo nor handing a judge your API credentials is the default solution.
