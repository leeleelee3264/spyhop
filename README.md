# Spyhop

> *Spyhop*: when an orca pokes its head straight out of the water to look around.

**Spyhop shows every AI coding session you have running — Claude Code and Codex — on one board.**
For each session you see what it is working on, how far it has come, and whether it is waiting for you.

![Board](docs/screenshots/board.png)

It is built for [Orca](https://github.com/stablyai/orca): each Orca workspace becomes a column, and each pane running an agent becomes a card.

## Features

### Board

- **One card per session** with the title of the task, the model, and how long it has been waiting or working.
- **Steps** read top to bottom: `Done` · `Now` · `Next`, plus purple **Intercept** for a quick side task handled in the middle of the main one.
- **My turn / Working** counts in the header. Sessions waiting for you sit at the top of each column.
- **No progress** badge when a session has been "working" for 5+ minutes without a single new line in its transcript (a long test run, or a stuck tool).
- When the window is short, all cards in a column shrink together into progress bars.

### Detail view

Click a card to see each step with a one-line explanation, the last reply, a TODO checklist you can tick yourself, the raw last request and reply (rendered markdown), and the session ID (click to copy `claude --resume <id>` / `codex resume <id>`).
From here you can jump to the pane or end the session.

![Detail](docs/screenshots/detail.png)

### Group by AI topics

By default columns are Orca workspaces. Switch to **AI topics** and the summarizer sorts sessions into up to six topic groups.
Groups stick once assigned, and dragging a card onto another group pins it there. While new sessions are being sorted, a small spinner shows "Grouping N sessions by topic…".

![AI groups](docs/screenshots/ai-groups.png)

### Settings

Click the gear icon.

| Setting | What it does |
|---|---|
| Summarizer | The model that writes titles, steps and TODOs. Only models available on your Mac are listed (see below). |
| Theme | Classic (follows macOS dark mode), Material Indigo, Teal, You, Dark, Blue Grey. |
| Group by | Orca workspace or AI topics. |
| Orca animation | Little orcas spyhop out of the wave in the header. |
| Start at login | Starts the board when you log in to the Mac. Off by default. |
| Update every | 10 / 30 / 60 seconds. Longer means less CPU and fewer model calls. |
| Resource usage | Live CPU and memory of the board itself. |

![Settings](docs/screenshots/settings.png)

### Menu bar panel (optional)

With [SwiftBar](https://github.com/swiftbar/SwiftBar), an orca icon in the menu bar shows how many sessions are waiting for you. Click it for a compact list: sessions waiting for you first, then the working ones. Click a row to jump to that pane.

<img src="docs/screenshots/panel.png" width="320" alt="Menu bar panel">

## Requirements

- macOS and Python 3.9+
- [Orca](https://github.com/stablyai/orca) with the `orca` CLI on your `PATH`
  - Spyhop currently finds sessions through Orca. A mode that works without Orca is planned.
- At least one summarizer:

| Summarizer | Models you can pick | What you need | Where transcripts go |
|---|---|---|---|
| DeepSeek (API) | DeepSeek flash | An API key in the macOS keychain | DeepSeek |
| Claude (claude CLI) | Haiku, Sonnet, Opus, Fable — current models plus any found in your transcripts | `claude` installed and logged in | Anthropic |
| Codex (codex CLI) | Models listed in `~/.codex/models_cache.json` | `codex` installed and logged in | OpenAI |

```bash
# DeepSeek: store the key in the keychain
security add-generic-password -s deepseek-api -a "$USER" -w '<your API key>'
```

When Claude or Codex CLI is the summarizer, Spyhop runs them without saving the summary call as a new conversation and with tools disabled. It uses your subscription.

## Install

```bash
git clone https://github.com/leeleelee3264/spyhop.git
cd spyhop
./spyhop
```

`./spyhop` starts the board in the background and opens it:

- **With Orca**: it adds a small project `~/.spyhop` (an empty git repo, because Orca only registers git repos from the CLI) with a **Spyhop** workspace, and opens the board in a browser tab there. Your own repositories are never touched.
- **Without Orca running**: it opens the board in your default browser.

The board is served at **http://127.0.0.1:47613/** (menu bar panel: `/panel`).

### Start at login (optional)

Turn on **Start at login** in Settings, or:

```bash
./spyhop --autostart      # register a LaunchAgent
./spyhop --no-autostart   # remove it
```

### Menu bar (optional)

Install SwiftBar, then link the plugin into its plugin folder:

```bash
ln -s "$PWD/menubar/spyhop.5s.py" "<SwiftBar plugin folder>/spyhop.5s.py"
```

The plugin also restarts the board when Claude or Codex is running.

## When it runs

| | When |
|---|---|
| Starts | `./spyhop` · at login (if enabled) · when Claude or Codex is running (menu bar plugin checks every 5 s) |
| Stops | After 30 minutes with no AI sessions open, to save resources |

Only one board process runs at a time. The Orca tab opens `~/.spyhop/open.html`, which shows "Starting the board…" while the server is down and loads the board as soon as it is up.

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
| `board.py` | Session discovery, summaries, board HTML, local server, settings |
| `panel.html` | Menu bar panel |
| `menubar/spyhop.5s.py` | SwiftBar plugin |
| `orca_art.py` | Orca icon and animation art |
| `spyhop` | Launcher |
| `tools/demo_screens.py` | Regenerates the screenshots in `docs/screenshots` from demo data |

## TODO

- [ ] **Work without Orca** — find sessions from recent Claude/Codex transcripts and group them by AI topics. Today the board shows no cards without Orca.
- [ ] Many groups: keep a minimum column width and scroll sideways; add a "reset groups" button.
- [ ] Try "move to another workspace" end to end with real sessions.
- [ ] Keep one source of truth for the code (the author's running copy still lives outside this repo).
- [ ] Add a license.
- [ ] Notify when a session turns to "My turn" (macOS notification).
- [ ] Show PR status (merged, CI) on cards.
- [ ] Setting for the language of card content (titles, steps, TODOs).
