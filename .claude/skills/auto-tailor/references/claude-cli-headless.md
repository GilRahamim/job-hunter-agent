# Claude Code headless mode — verified facts (checked 2026-10-21)

Sources: https://code.claude.com/docs/en/headless.md · https://code.claude.com/docs/en/authentication.md
Re-check these pages when the CLI version changes; flags below list their minimum version where the docs give one.

## Running
- `claude -p "<prompt>"` (`--print`) runs non-interactively. Exit code 0 = success, non-zero = failure. Failures inside the run (e.g. missing authentication) are printed **as the result on stdout**.
- `--output-format text|json|stream-json`. `json` includes `result`, `session_id`, usage metadata and `total_cost_usd` (client-side estimate).
- Skills and custom commands work in `-p`: put `/skill-name args` in the prompt and Claude Code expands it. Terminal-only commands such as `/login` do not.
- Without `--bare`, `-p` loads hooks, skills, plugins, MCP servers, CLAUDE.md of the working directory — like an interactive session, and with **no workspace trust dialog**.
- Piped stdin is capped at 10 MB.
- SIGTERM → exit code 143, the turn is left unfinished.
- `--resume <session_id>` / `--continue` continue a conversation.

## Permissions
- `--allowedTools "Read,Edit,Bash(git diff *)"` — permission-rule syntax; the trailing ` *` (with the space) is a prefix match.
- `--permission-mode`: `acceptEdits` (writes files, auto-approves mkdir/touch/mv/cp; other shell commands still need allow rules), `dontAsk` (deny everything that would prompt), `auto` (a classifier reviews actions). Pass one explicitly: the built-in default can be `auto`.
- `--permission-prompts none` (CLI >= 2.1.259): anything that would prompt is denied, Claude is told not to retry, AskUserQuestion is removed. Older CLIs reject the flag as unknown → check `claude --version` and drop the flag (a `-p` run with no host denies prompts anyway) if older.

## Authentication (why the env matters)
Precedence, highest first:
1. Cloud provider vars (`CLAUDE_CODE_USE_BEDROCK` / `_VERTEX` / `_FOUNDRY`)
2. `ANTHROPIC_AUTH_TOKEN`
3. `ANTHROPIC_API_KEY` — **in `-p` mode always used when present** (interactive mode asks once)
4. `apiKeyHelper`
5. `CLAUDE_CODE_OAUTH_TOKEN` — 1-year token from `claude setup-token`; subscription (Pro/Max/Team/Enterprise); model requests only
6. Anthropic profiles / federation
7. `/login` subscription OAuth — default for Pro/Max

So: remove 2 and 3 from the child env; keep 5 if set.
- `--bare` reads **no** OAuth/keychain credentials and not `CLAUDE_CODE_OAUTH_TOKEN` → API key only. Never use it here.
- Windows stores the login in `%USERPROFILE%\.claude\.credentials.json`; `CLAUDE_CONFIG_DIR` moves it.
- A `/login` login warns 3 days before it expires; after expiry every request fails with "Login expired · Please run /login". `/status` shows which credential is active.
