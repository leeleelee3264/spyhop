# Spyhop details

Reference for things the README doesn't need to say.

## At a glance

| | |
|---|---|
| What | A local web board of every Claude Code / Codex session running on this Mac (in Orca, Terminal, iTerm2, Ghostty, WezTerm, cmux or any terminal), each shown as its own progress (done · now · next steps) |
| Platform | macOS, Python 3.9+ (standard library only, no `pip install`) |
| Needs | one summarizer: `claude` or `codex` logged in, or a DeepSeek API key. The `orca` CLI is optional (adds workspace columns, moving and helper lines) |
| DeepSeek (optional) | Faster summaries (about 6 s per session). Store a key once: `security add-generic-password -s deepseek-api -a "$USER" -w '<key>'` |
| Start | Open Spyhop, or turn on **Start at login** in Settings |
| Stops | By itself after 30 minutes with no AI sessions open, and on logout |
| Is it running? | `curl -s http://127.0.0.1:47613/state.json` returns JSON |
| Logs | `/tmp/progress-board/watch.log` · `~/Library/Logs/spyhop.log` when started at login |
| Settings / groups | `~/.spyhop/config.json` · `~/.spyhop/groups.json` · TODO check marks in `~/.spyhop/overrides.json` |
| Diagnose | `/usr/bin/python3 /Applications/Spyhop.app/Contents/Resources/spyhop/board.py --doctor` (`--titles` to include titles) |
| Request key | `/tmp/progress-board/token` (changing requests must carry it; only the board page has it) |
| Cached summaries | `/tmp/progress-board/auto/<transcript>.json` (delete one to re-summarize that session from scratch) |
| Port | `127.0.0.1:47613` (local only) |

## When it runs

| | When |
|---|---|
| Starts | `./spyhop` · at login (if turned on in Settings) · when Claude or Codex is running (menu bar plugin checks every 5 s) |
| Stops | After 30 minutes with no AI sessions open, to save resources |

Only one board process runs at a time. The Orca tab opens `~/.spyhop/open.html`, which shows "Starting the board…" while the board is down and loads it as soon as it is up.

Typical cost on a Mac with ~11 sessions: about 60 MB of memory and around 1% of total CPU at the 10-second interval.

## How it works

1. Spyhop starts from the running `claude` and `codex` programs (`ps`), checked every second; a new or ended program redraws the board at once.
   - Claude: `~/.claude/sessions/<pid>.json` gives the session id, so the transcript is found no matter which folder it started in.
   - Codex: the rollout files the program (or the Codex app-server) has open, narrowed by the thread name in the pane title, a `resume` argument and start time.
   - A program inside an Orca pane is tied to that pane through its `ORCA_PANE_KEY`. Anything else becomes a card in a "folder · terminal" column.
2. Orca panes without a matched program fall back to matching by title (`~/.claude/projects/…` for Claude, `~/.codex/sessions/…` for Codex).
3. For sessions whose transcript changed, it asks the summarizer for a title, summary, steps and TODOs as JSON.
   - The first call reads the whole conversation. After that it only sends the previous summary plus the new part of the conversation, so titles and finished steps stay put.
   - When the new part contains a new request from you, the session is summarized from scratch instead, so the current step can't get stuck.
   - Each session is re-summarized at most once per 1–5 minutes, depending on the update interval.
   - Measured on one Mac over 30 minutes (6 sessions open, a few working, 10 s interval): 53 calls, 2,900 to 5,800 characters each (median about 4,500), 51 of them sending only the new part of the transcript.
4. Helper panes started through Orca orchestration are attached to the session that started them (via `parentPaneKey`, or the orchestration run's coordinator). Spyhop doesn't guess from names or content: any pane another session opened through Orca becomes a helper line, whether it is a cross-check, a review or a build.
   - A helper that reports done and then gets new work (more than 2 minutes later) becomes its own card.
   - Helpers are never closed automatically.
   - A cross-check run without Orca (the `codex` or `claude` CLI called from a session, or an in-process subagent) opens no pane, so it only shows up as a step in the calling session.
5. It renders the board right away with the summaries it already has and serves it on `127.0.0.1`. Summaries are refreshed in the background, and the board is redrawn as soon as they land. Reloading the page redraws it on the spot.

Panes whose transcript can't be found are left off the board, except a freshly started program, which shows as a "New session" card until its first message. `spyhop doctor` explains each case.

A Codex session counts as working until its last turn completes in the transcript; Claude sessions use Orca's agent state, or the status in `~/.claude/sessions/<pid>.json` outside Orca.

Claude models offered in Settings are the current ones plus any found in your recent transcripts. Codex models come from `~/.codex/models_cache.json`.

## Privacy

- Transcripts are sent to the summarizer you pick (and titles and summaries, for AI topic grouping). Before anything is sent, Spyhop masks strings that look like AWS keys, API tokens, JWTs and `password=`, `token:` or `api_key` values, quoted or not. This is a best-effort filter, not a guarantee.
- Summaries and state are kept in `/tmp/progress-board/`. Settings and topic groups live in `~/.spyhop/`.
- The server listens on `127.0.0.1` only and only acts on sessions currently shown on the board. Requests that change anything must carry a random key that only the board page contains, so other web pages can't call it.
- Board files are readable only by you (`/tmp/progress-board` is 0700).
- `~/.spyhop` is an empty git repo only because Orca registers projects from git repos. Spyhop never touches your own repositories.

## Files

Each product lives in its own folder and shares no code with the others.

| Folder | Product |
|---|---|
| `macos/` | Spyhop.app, installed with `brew install leeleelee3264/tap/spyhop`. `app/` is the Swift shell, `board/` is the board the app bundles (`board.py`, `panel.html`, `orca_art.py`, its tests and `tools/demo_screens.py`), `build.sh` builds the app and DMG |
| `legacy/mac-browser/` | The old browser version (browser board and SwiftBar menu bar). No longer released |
| `docs/`, `site/` | README pictures, details and the intro page |

Inside a board folder:

| File | Role |
|---|---|
| `board.py` | Session discovery, summaries, board HTML, local server, settings |
| `panel.html` | Menu bar panel |
| `orca_art.py` | Orca icon and animation art |
| `tools/demo_screens.py` | Regenerates the screenshots in `docs/screenshots` from demo data |
| `spyhop`, `menubar/spyhop.5s.py` | Brew command and SwiftBar plugin (`legacy/mac-browser/` only) |

### cmux socket access

Spyhop runs outside the cmux process tree. Select **Automation mode** under cmux **Settings → Automation → Socket Control Mode** to allow local automation from the same macOS user. The default **cmux processes only** mode rejects these commands; **Full open access** is unnecessary. Sessions can still be listed when socket access is denied, but Go to session can only bring cmux forward.

If `cmux ping` still reports access denied after changing the mode, restart cmux and retry. On cmux 0.64.4, the live listener kept enforcing the old mode until the app was restarted.
