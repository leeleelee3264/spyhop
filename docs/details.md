# Spyhop details

Everything that does not need to be in the README.

## At a glance

| | |
|---|---|
| What | A local web board of every Claude Code / Codex session running in Orca |
| Platform | macOS, Python 3.9+ (standard library only, no `pip install`) |
| Needs | `orca` CLI on `PATH` · one summarizer: `claude` or `codex` logged in, or a DeepSeek API key |
| Start | `./spyhop`, or turn on **Start at login** in Settings |
| Stops | By itself after 30 minutes with no AI sessions open, and on logout |
| Is it running? | `curl -s http://127.0.0.1:47613/state.json` returns JSON |
| Logs | `/tmp/progress-board/watch.log` · `~/Library/Logs/spyhop.log` when started at login |
| Settings / groups | `~/.spyhop/config.json` · `~/.spyhop/groups.json` |
| Cached summaries | `/tmp/progress-board/auto/<transcript>.json` (delete one to re-summarize that session from scratch) |
| Port | `127.0.0.1:47613` (local only) |

## Summarizers

Spyhop uses the first summarizer available (DeepSeek, then Claude, then Codex; the DeepSeek key is optional). Change it in Settings; only models available on your Mac are listed.

| Summarizer | Models you can pick | What you need | Where transcripts go |
|---|---|---|---|
| Claude (claude CLI) | Haiku, Sonnet, Opus, Fable — current models plus any found in your transcripts | `claude` installed and logged in | Anthropic |
| Codex (codex CLI) | Models listed in `~/.codex/models_cache.json` | `codex` installed and logged in | OpenAI |
| DeepSeek (API) | DeepSeek flash | An API key in the macOS keychain | DeepSeek |

```bash
# DeepSeek only: store the key in the keychain
security add-generic-password -s deepseek-api -a "$USER" -w '<your API key>'
```

When Claude or Codex CLI is the summarizer, Spyhop runs them without saving the summary call as a new conversation and with tools disabled. It uses your subscription. DeepSeek is the fastest (about 6 s per session).

## What `./spyhop` does

- Starts the board process in the background. Only one ever runs.
- **With Orca running**: registers a small project `~/.spyhop` (an empty git repo, because Orca only registers git repos from the CLI) with a **Spyhop** workspace, and opens the board in a browser tab there. Your own repositories are never touched.
- **Without Orca running**: opens the board in your default browser.

The Orca tab opens `~/.spyhop/open.html`, which shows "Starting the board…" while the server is down and loads the board as soon as it is up.

## Menu bar (optional)

Install [SwiftBar](https://github.com/swiftbar/SwiftBar), then link the plugin into its plugin folder:

```bash
ln -s "$PWD/menubar/spyhop.5s.py" "<SwiftBar plugin folder>/spyhop.5s.py"
```

An orca icon shows how many sessions are waiting for you; click it for a compact list. The plugin also starts the board when Claude or Codex is running.

## When it runs

| | When |
|---|---|
| Starts | `./spyhop` · at login (if turned on in Settings) · when Claude or Codex is running (menu bar plugin checks every 5 s) |
| Stops | After 30 minutes with no AI sessions open, to save resources |

Typical cost on a Mac with ~6 sessions: about 70–80 MB of memory and around 1% of total CPU at the 10-second interval.

## How it works

1. Every update, Spyhop asks Orca which panes are running agents and whether each one is working or waiting.
2. It matches each pane to its transcript (`~/.claude/projects/…` for Claude, `~/.codex/sessions/…` for Codex).
3. For sessions whose transcript changed, it asks the summarizer for a title, summary, steps and TODOs as JSON.
   - The first call reads the whole conversation. After that it only sends the previous summary plus the new part of the conversation, so titles and finished steps stay put.
   - Each session is re-summarized at most once per 1–5 minutes, depending on the update interval.
4. It renders the board and serves it on `127.0.0.1`.

## Privacy

- Transcripts are sent to the summarizer you pick. Before sending, Spyhop masks strings that look like AWS keys, API tokens, JWTs and `password=` values. This is a best-effort filter, not a guarantee — pick a model your organization allows.
- Summaries and state are kept in `/tmp/progress-board/`. Settings and topic groups live in `~/.spyhop/`.
- The server listens on `127.0.0.1` only and only acts on sessions currently shown on the board.

## Files

| File | Role |
|---|---|
| `spyhop` | Starts the board and opens it |
| `board.py` | Session discovery, summaries, board HTML, local server, settings |
| `panel.html` | Menu bar panel |
| `menubar/spyhop.5s.py` | SwiftBar plugin |
| `orca_art.py` | Orca icon and animation art |
| `tools/demo_screens.py` | Regenerates the screenshots in `docs/screenshots` from demo data |
