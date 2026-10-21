<p align="center">
  <img src="docs/logo.svg" width="112" alt="Spyhop logo">
</p>

<h1 align="center">Spyhop</h1>

<p align="center">
  <b>Every AI coding session on one board, each with its own progress.</b><br>
  <sub>See all your Claude Code, Codex and OMP sessions at once, and how far each one has come: done, now, next.</sub>
</p>

<p align="center"><a href="https://leeleelee3264.github.io/spyhop/"><b>Tour the features (intro page with demo video) →</b></a></p>

<p align="center">
  <img alt="macOS" src="https://img.shields.io/badge/macOS-only-1e293b?logo=apple&logoColor=white">
  <img alt="Homebrew" src="https://img.shields.io/badge/brew-leeleelee3264%2Ftap-1e293b?logo=homebrew&logoColor=white">
  <img alt="Claude Code" src="https://img.shields.io/badge/Claude%20Code-supported-1e293b">
  <img alt="Codex" src="https://img.shields.io/badge/Codex-supported-1e293b">
  <img alt="OMP" src="https://img.shields.io/badge/OMP-supported-1e293b">
  <img alt="Orca" src="https://img.shields.io/badge/Orca-optional-1e293b">
  <img alt="Terminals" src="https://img.shields.io/badge/Terminal%20%C2%B7%20iTerm2%20%C2%B7%20Ghostty%20%C2%B7%20WezTerm%20%C2%B7%20cmux-supported-1e293b">
</p>

![Board](docs/screenshots/board.png)

<sub>Demo data. The last column is a session started in iTerm2, outside Orca.</sub>

- **All sessions in one place.** Every Claude Code, Codex and OMP session you have open becomes a card on one board, with the ones waiting for you on top.
- **Progress for each session.** Spyhop reads the transcript and lays the work out as steps: what's done, what it's on now, what's next.
- **Grouped by topic.** Switch to AI topics and the AI puts sessions doing related work in one column, by what the work is about rather than which folder it runs in.

**Contents:** [Get started](#get-started) · [How to](#how-to) · [Reference](#reference) · [How it works](#how-it-works) · [Roadmap](#roadmap)

## Get started

You need macOS, Homebrew, and a logged-in `claude` or `codex` CLI (Spyhop uses it to summarize). [Orca](https://github.com/stablyai/orca) is optional.

1. Install and start:

   ```bash
   brew install leeleelee3264/tap/spyhop
   spyhop
   ```

2. The board opens in Orca as a **Spyhop** workspace if you have it, and always at `http://127.0.0.1:47613/`.
3. Start or keep a Claude Code or Codex session running anywhere (Orca, Terminal, iTerm2, Ghostty, WezTerm, cmux). It shows up as a card within a few seconds, and its steps fill in once the first summary is done.
4. Click a card to see every step, the last reply and its TODO list. **Go to session** jumps to that pane or tab.
5. Optional, menu bar: `brew install --cask swiftbar`, then run `spyhop` once more. The orca icon shows how many sessions are waiting for you.

## How to

### Update

```bash
brew upgrade spyhop && spyhop
```

A running board switches to the new version by itself within a minute after `brew upgrade`. Settings, topic columns and your AI sessions are kept. If your board started on 0.5.0 or older, run `spyhop` once after upgrading.

### Find a session that is missing or looks wrong

```bash
spyhop doctor            # explains, card by card, how each session was found or why it was not
spyhop doctor --titles   # same, with titles and prompts shown
```

tmux and SSH sessions outside Orca are not supported.

### Change the summarizer model

Open **Settings → Summarizer** and pick a `claude` or `codex` model. Transcripts go to the model you pick, so pick one your organization allows.

### Add OMP (Oh My Pi) sessions

Start OMP once after installing Spyhop, run `spyhop`, then restart your OMP sessions so they load the bundled status extension. Moving OMP sessions between Orca workspaces is not supported yet. Details are under [OMP](#omp) in Reference.

### Move a session to another Orca workspace

Drag its card to another column. The Orca pane moves there and the conversation continues in its original folder. Only sessions showing **My turn** can be moved, and only inside Orca.

### Group by topic instead of location

In **Settings → Group by**, pick **AI topics**. Drag a card to another topic to pin it there, or drop it on **+ New column** to make your own.

### Uninstall

Turn off **Start at login** in Settings first, and remove the **.spyhop** project from Orca's sidebar. Then:

```bash
brew uninstall spyhop && rm -rf ~/.spyhop
```

## Reference

### Commands

| Command | What it does |
|---|---|
| `spyhop` | Starts the board (or switches to a newly installed version) and opens it |
| `spyhop doctor` | Explains how each session was found, or why it was not. Titles are hidden unless you add `--titles` |

### What works where

| | Orca | Terminal, iTerm2, Ghostty, WezTerm, cmux | Other terminals |
|---|---|---|---|
| Card, steps, summary, detail view | ✅ | ✅ | ✅ |
| Columns (Group by: Location) | Orca workspaces | folder and terminal (e.g. `workspace · iTerm2`) | folder and terminal |
| Go to session | the exact pane | the exact tab | brings the app to the front |
| End session | closes that split pane | stops the AI program, the tab stays | stops the AI program, the tab stays |
| Drag a card to move the session to another workspace | ✅ | ❌ | ❌ |
| Cross-check line under a card (panes started through Orca) | ✅ | ❌ | ❌ |
| AI topic grouping | ✅ | ✅ | ✅ |
| `spyhop doctor` | ✅ | ✅ | ✅ |

### On the board

- **Steps** on every card: `Done` · `Now` · `Next`, plus purple `Intercept` for a quick side task. When space runs out, cards shrink to progress bars (`3/4 · Review`).
- **No progress** badge when a working session hasn't written anything for 5 minutes.
- **Cross-check**: a pane a session starts through Orca orchestration (a Codex cross-check, a review) appears as one line under that session, and its result shows in the detail view. If that session's pane is closed, it shows as its own card.
- **Detail view**: every step explained, the last reply, a TODO checklist, the session ID, and buttons to jump to or end the session.
- **Filter and sort**: All / My turn / Working tabs with counts, and a Sort menu (Newest or Longest wait). Both choices are remembered.
- **Narrow windows**: columns wrap onto the next row (3 across in a 900px window, 1 on a phone).
- **Settings**: summarizer, group by (Location or AI topics), 9 themes, start at login, update interval, live CPU and memory.
- **Menu bar**: how many sessions are waiting for you; click a row to jump there.

### OMP

The status extension is installed at `~/.omp/agent/extensions/spyhop-status.ts` when the OMP agent directory exists (or `PI_CODING_AGENT_DIR` when set for `spyhop`). OMP must allow its normal extension discovery. It records only PID, process start time, session ID, transcript path, folder and busy/idle state in `~/.spyhop/omp/`. Tested with Oh My Pi 18.12.2.

### Files

Settings and topic groups live in `~/.spyhop`; summaries and board state in `/tmp/progress-board/`. More in [docs/details.md](docs/details.md#at-a-glance).

## How it works

- **Finding sessions.** Spyhop looks at the running `claude`, `codex` and OMP programs, so sessions show up wherever you start them. Orca, when present, adds exact panes, workspaces and cross-check links.
- **Summaries.** Only sessions whose transcript changed are summarized, at most once a minute each (every 3 or 5 minutes at the 30 s or 60 s update interval), and only the new part is sent. Idle sessions cost nothing. Measured over 30 minutes with 6 sessions open: 53 summarizer calls, about 4,500 characters each.
- **Privacy.** The only thing that leaves your Mac is the transcript, sent to the summarizer model you picked, with anything that looks like a key or password masked first.
- **Updates.** After `brew upgrade`, the running board notices the new version within a minute and hands over to it. The version next to the title stays highlighted until you rest the pointer on it; the tooltip links to the release notes.

More on timing, privacy and internals: [docs/details.md](docs/details.md).

## Roadmap

- [x] Work without Orca: sessions in Terminal, iTerm2, Ghostty and WezTerm, grouped by folder and terminal.
- [x] `spyhop doctor` to explain missing or wrong cards.
- [ ] A "reset groups" button for AI topics.
- [ ] Moving a session to another workspace, made safe end to end.
- [ ] Notify when a session turns to "My turn".
- [ ] Search past Claude and Codex sessions and reopen one (`claude --resume` / `codex resume`) from the board.
