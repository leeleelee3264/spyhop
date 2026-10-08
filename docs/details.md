# Spyhop details

Reference for things the README doesn't need to say.

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
| Request key | `/tmp/progress-board/token` (changing requests must carry it; only the board page has it) |
| Cached summaries | `/tmp/progress-board/auto/<transcript>.json` (delete one to re-summarize that session from scratch) |
| Port | `127.0.0.1:47613` (local only) |

## When it runs

| | When |
|---|---|
| Starts | `./spyhop` · at login (if turned on in Settings) · when Claude or Codex is running (menu bar plugin checks every 5 s) |
| Stops | After 30 minutes with no AI sessions open, to save resources |

Only one board process runs at a time. The Orca tab opens `~/.spyhop/open.html`, which shows "Starting the board…" while the board is down and loads it as soon as it is up.

Typical cost on a Mac with ~6 sessions: about 70–80 MB of memory and around 1% of total CPU at the 10-second interval.

## How it works

1. Every update, Spyhop asks Orca which panes are running agents and whether each one is working or waiting.
2. It matches each pane to its transcript (`~/.claude/projects/…` for Claude, `~/.codex/sessions/…` for Codex).
3. For sessions whose transcript changed, it asks the summarizer for a title, summary, steps and TODOs as JSON.
   - The first call reads the whole conversation. After that it only sends the previous summary plus the new part of the conversation, so titles and finished steps stay put.
   - When the new part contains a new request from you, the session is summarized from scratch instead, so the current step can't get stuck.
   - Each session is re-summarized at most once per 1–5 minutes, depending on the update interval.
4. Helper panes started through Orca orchestration are attached to the session that started them (via `parentPaneKey`, or the orchestration run's coordinator).
5. It renders the board and serves it on `127.0.0.1`.

A Codex session counts as working until its last turn completes in the transcript; Claude sessions use Orca's agent state.

Claude models offered in Settings are the current ones plus any found in your recent transcripts. Codex models come from `~/.codex/models_cache.json`.

## Privacy

- Transcripts are sent to the summarizer you pick. Before sending, Spyhop masks strings that look like AWS keys, API tokens, JWTs and `password=` values. This is a best-effort filter, not a guarantee.
- Summaries and state are kept in `/tmp/progress-board/`. Settings and topic groups live in `~/.spyhop/`.
- The server listens on `127.0.0.1` only and only acts on sessions currently shown on the board. Requests that change anything must carry a random key that only the board page contains, so other web pages can't call it.
- Board files are readable only by you (`/tmp/progress-board` is 0700).
- `~/.spyhop` is an empty git repo only because Orca registers projects from git repos. Spyhop never touches your own repositories.

## Files

| File | Role |
|---|---|
| `spyhop` | Starts the board and opens it |
| `board.py` | Session discovery, summaries, board HTML, local server, settings |
| `panel.html` | Menu bar panel |
| `menubar/spyhop.5s.py` | SwiftBar plugin |
| `orca_art.py` | Orca icon and animation art |
| `tools/demo_screens.py` | Regenerates the screenshots in `docs/screenshots` from demo data |
