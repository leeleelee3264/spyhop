<p align="center">
  <img src="docs/logo.svg" width="112" alt="Spyhop logo">
</p>

<h1 align="center">Spyhop</h1>

<p align="center">
  <b>Every AI coding session you have running, on one board.</b><br>
  <sub>What each Claude Code and Codex session is doing, how far it has come, and whether it is waiting for you.</sub>
</p>

<p align="center">
  <img alt="macOS" src="https://img.shields.io/badge/macOS-only-1e293b?logo=apple&logoColor=white">
  <img alt="Python 3.9+" src="https://img.shields.io/badge/python-3.9%2B-1e293b?logo=python&logoColor=white">
  <img alt="Claude Code" src="https://img.shields.io/badge/Claude%20Code-supported-1e293b">
  <img alt="Codex" src="https://img.shields.io/badge/Codex-supported-1e293b">
  <img alt="Orca" src="https://img.shields.io/badge/Orca-workspaces-1e293b">
</p>

<p align="center"><i>Spyhop: when an orca pokes its head straight out of the water to look around.</i></p>

![Board](docs/screenshots/board.png)

## Why

You run several Claude Code and Codex sessions at once and lose track of which one finished, which one is waiting for you, and which one has been stuck for ten minutes.
Spyhop turns every session into a card with its steps, its TODOs and whose turn it is, summarized from the transcript.

## Quick start

```bash
git clone https://github.com/leeleelee3264/spyhop.git
cd spyhop
./spyhop
```

- You need [Orca](https://github.com/stablyai/orca) and the `claude` CLI logged in. Nothing else: no `pip install`.
- **Without Orca the board stays empty** — Spyhop finds sessions through Orca today.
- The board opens in a **Spyhop** workspace in Orca, at `http://127.0.0.1:47613/`.

## Features

- **Cards with steps** — `Done` · `Now` · `Next`, plus purple **Intercept** for a quick side task in the middle of the main one.
- **My turn / Working** — sessions waiting for you sit at the top. A **No progress** badge appears when a working session hasn't moved for 5 minutes.
- **Detail view** — every step explained, the last reply, a TODO checklist, and the session ID to resume.
- **Group by AI topics** — instead of Orca workspaces, let the AI sort sessions into up to six topics. Drag a card to pin it to another group.
- **Settings** — summarizer model, theme, grouping, start at login, update interval, and the board's own CPU and memory.
- **Menu bar** (optional, with [SwiftBar](https://github.com/swiftbar/SwiftBar)) — an orca icon with the number of sessions waiting for you.

| Detail view | Settings |
|---|---|
| ![Detail](docs/screenshots/detail.png) | ![Settings](docs/screenshots/settings.png) |

| AI topics | Menu bar |
|---|---|
| ![AI groups](docs/screenshots/ai-groups.png) | <img src="docs/screenshots/panel.png" width="260" alt="Menu bar panel"> |

## Uninstall

Turn off **Start at login** in Settings, delete the repo folder and `~/.spyhop`, and remove the **.spyhop** project from Orca's sidebar.
The board stops by itself within 30 minutes once no sessions are open.

## More

Summarizer options (Claude, Codex, DeepSeek), the menu bar plugin, how it works, privacy and file locations: [docs/details.md](docs/details.md).

## TODO

- [ ] **Work without Orca** — find sessions from recent Claude/Codex transcripts and group them by AI topics.
- [ ] Many groups: minimum column width with sideways scroll; a "reset groups" button.
- [ ] Try "move to another workspace" end to end with real sessions.
- [ ] Keep one source of truth for the code.
- [ ] Add a license.
- [ ] Notify when a session turns to "My turn".
- [ ] Show PR status on cards.
- [ ] Setting for the language of card content.
