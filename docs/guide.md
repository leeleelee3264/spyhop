# Spyhop guide

Setup details, how-to steps and reference for Spyhop. For a quick start, see the [README](../README.md).

**Contents:** [Coming from the browser version](#coming-from-the-browser-version) · [How to](#how-to) · [Reference](#reference) · [How it works](#how-it-works)

## Coming from the browser version

Spyhop used to run in a browser tab with a SwiftBar menu bar icon. That version gets no more updates. On your next `brew update`, Homebrew moves you to the app: it installs it by itself, or prints these two commands to run:

```bash
brew trust --cask leeleelee3264/tap/spyhop
brew install --cask leeleelee3264/tap/spyhop
```

When the app opens, it takes over the board server and **Start at login**, and removes the Spyhop icon from SwiftBar (SwiftBar itself stays; quit or uninstall it yourself if you no longer use it). It then offers once to remove the old browser version. Settings, topic columns and checked TODOs are kept.

## How to

### Update

Choose **Spyhop → Check for Updates…** to review the new version’s release notes, then click **Update and restart**. Spyhop installs the update and reopens automatically. Settings, topic columns and your AI sessions are kept.

Coming from 2.0.0, install 2.1.0 through Homebrew once to get the in-app updater:

```bash
brew update
brew upgrade --cask leeleelee3264/tap/spyhop
open -a Spyhop
```

### Versioning

Spyhop uses `MAJOR.MINOR.PATCH`:

- **Minor** releases add compatible features or support, such as a new terminal (`2.0.0 → 2.1.0`). A larger feature list or a redesigned screen does not by itself require a major release.
- **Patch** releases fix bugs and make small compatible interface improvements (`2.1.0 → 2.1.1`).
- **Major** releases introduce incompatible changes to supported commands, settings or data that cannot be migrated automatically and require action from users.

Published versions and their assets are never rewritten. Installation or update-path changes are checked with an internal release candidate before the stable release. Test RC releases stay in private drafts; normal downloads, Homebrew and in-app updates offer stable releases only.

### Find a session that is missing or looks wrong

```bash
/usr/bin/python3 /Applications/Spyhop.app/Contents/Resources/spyhop/board.py --doctor            # explains, card by card, how each session was found or why it was not
/usr/bin/python3 /Applications/Spyhop.app/Contents/Resources/spyhop/board.py --doctor --titles   # same, with titles and prompts shown
```

tmux and SSH sessions outside Orca are not supported.

### Change the summarizer model

Open **Settings → Summarizer** and pick a `claude` or `codex` model. Transcripts go to the model you pick, so pick one your organization allows.

### Add OMP (Oh My Pi) sessions

Start OMP once after installing Spyhop, open Spyhop, then restart your OMP sessions so they load the bundled status extension. Moving OMP sessions between Orca workspaces is not supported yet. Details are under [OMP](#omp) in Reference.

### Add GitHub Copilot CLI sessions

Nothing to set up: running `copilot` sessions show up on their own. Moving Copilot sessions between Orca workspaces is not supported yet. Details are under [GitHub Copilot CLI](#github-copilot-cli) in Reference.

### Move a session to another Orca workspace

Drag its card to another column. The Orca pane moves there and the conversation continues in its original folder. Only sessions showing **My turn** can be moved, and only inside Orca.

### Group by topic instead of location

In **Settings → Group by**, pick **AI topics**. Drag a card to another topic to pin it there, or drop it on **+ New column** to make your own.

### Uninstall

Turn off **Start at login** in Settings first, and remove the **.spyhop** project from Orca's sidebar. Then:

```bash
brew uninstall --cask spyhop && rm -rf ~/.spyhop
```

## Reference

### What works where

| | Orca | Terminal, iTerm2, Ghostty, WezTerm, cmux | Claude desktop app (local Code sessions) | Other terminals |
|---|---|---|---|---|
| Card, steps, summary, detail view | ✅ | ✅ | ✅ | ✅ |
| Columns (Group by: Location) | Orca workspaces | folder and terminal (e.g. `workspace · iTerm2`) | folder (`workspace · Claude App`) | folder and terminal |
| Go to session | the exact pane | the exact tab | that session in the app | brings the app to the front |
| End session | closes that split pane | stops the AI program, the tab stays | stops the AI program, the session stays in the sidebar | stops the AI program, the tab stays |
| Drag a card to move the session to another workspace | ✅ | ❌ | ❌ | ❌ |
| Cross-check line under a card (panes started through Orca) | ✅ | ❌ | ❌ | ❌ |
| AI topic grouping | ✅ | ✅ | ✅ | ✅ |
| Doctor (`board.py --doctor`) | ✅ | ✅ | ✅ | ✅ |

cmux: in **Settings → Automation → Socket Control Mode**, select **Automation mode** so Spyhop can focus sessions from outside cmux. The default **cmux processes only** mode rejects external clients. **Full open access** is not needed. If the CLI still rejects access after changing this setting, restart cmux.

### On the board

- **Steps** on every card: `Done` · `Now` · `Next`, plus purple `Intercept` for a quick side task. When space runs out, cards shrink to progress bars (`3/4 · Review`).
- **No progress** badge when a working session hasn't written anything for 5 minutes.
- **Cross-check**: a pane a session starts through Orca orchestration (a Codex cross-check, a review) appears as one line under that session, and its result shows in the detail view. If that session's pane is closed, it shows as its own card.
- **Detail view**: every step explained, the last reply, a TODO checklist, the session ID, and buttons to jump to or end the session.
- **Filter and sort**: All / My turn / Working tabs with counts, and a Sort menu (Newest or Longest wait). Both choices are remembered.
- **Narrow windows**: columns wrap onto the next row (3 across in a 900px window, 1 on a phone).
- **Settings**: summarizer, group by (Location or AI topics), 9 themes, start at login, update interval, live CPU and memory.
- **Menu bar**: how many sessions are waiting for you; click a row to jump there. Built into the app.

### OMP

The status extension is installed at `~/.omp/agent/extensions/spyhop-status.ts` when the OMP agent directory exists (or `PI_CODING_AGENT_DIR` when set for `spyhop`). OMP must allow its normal extension discovery. It records only PID, process start time, session ID, transcript path, folder and busy/idle state in `~/.spyhop/omp/`. Tested with Oh My Pi 18.12.2.

### GitHub Copilot CLI

Spyhop finds each running `copilot` program through the `inuse.<pid>.lock` file Copilot keeps in its session folder under `~/.copilot/session-state/`, and reads that session's `events.jsonl`. Because every Copilot transcript has the same file name, Spyhop keeps a link named after the session ID in `~/.spyhop/copilot/`. A session waiting for your permission counts as your turn. Tested with Copilot CLI 1.0.105.

### Files

Settings and topic groups live in `~/.spyhop`; summaries and board state in `/tmp/progress-board/`. More in [docs/details.md](details.md#at-a-glance).

## How it works

- **Finding sessions.** Spyhop looks at the running `claude`, `codex`, `copilot` and OMP programs, so sessions show up wherever you start them. Orca, when present, adds exact panes, workspaces and cross-check links.
- **Summaries.** Only sessions whose transcript changed are summarized, at most once a minute each (every 3 or 5 minutes at the 30 s or 60 s update interval), and only the new part is sent. Idle sessions cost nothing. Measured over 30 minutes with 6 sessions open: 53 summarizer calls, about 4,500 characters each.
- **Privacy.** The only thing that leaves your Mac is the transcript, sent to the summarizer model you picked, with anything that looks like a key or password masked first.
- **Updates.** Spyhop checks for stable releases, shows a single update notice, and lets you review the offered version’s complete release notes before installing. It reopens automatically after installation. After an upgrade, the installed version’s New Features and Fixes appear once.

More on timing, privacy and internals: [docs/details.md](details.md).
