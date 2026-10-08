<p align="center">
  <img src="docs/logo.svg" width="112" alt="Spyhop logo">
</p>

<h1 align="center">Spyhop</h1>

<p align="center">
  <b>Every AI coding session on one board, each with its own progress.</b><br>
  <sub>See all your Claude Code and Codex sessions at once, and how far each one has come: done, now, next.</sub>
</p>

<p align="center">
  <img alt="macOS" src="https://img.shields.io/badge/macOS-only-1e293b?logo=apple&logoColor=white">
  <img alt="Homebrew" src="https://img.shields.io/badge/brew-leeleelee3264%2Ftap-1e293b?logo=homebrew&logoColor=white">
  <img alt="Claude Code" src="https://img.shields.io/badge/Claude%20Code-supported-1e293b">
  <img alt="Codex" src="https://img.shields.io/badge/Codex-supported-1e293b">
  <img alt="Orca" src="https://img.shields.io/badge/Orca-workspaces-1e293b">
</p>

![Board](docs/screenshots/board.png)

Spyhop does two things:

- **All sessions in one place.** Every Claude Code and Codex session you have open becomes a card on one board, with the ones waiting for you on top. No more flipping through panes to find out which one finished or got stuck.
- **Progress for each session.** Spyhop reads the transcript and lays the work out as steps — what's done, what it's on now, what's next — like a progress page for every session. As the work moves, finished steps stay put and the current step moves forward, so you can tell how far it has come at a glance.

## Install

```bash
brew install leeleelee3264/tap/spyhop
spyhop
```

- **Needs** [Orca](https://github.com/stablyai/orca) and one summarizer (below). Spyhop finds sessions through Orca, so without it the board is empty.
- **Opens** in Orca as a **Spyhop** workspace, and at `http://127.0.0.1:47613/`.
- **Menu bar** (optional): `brew install --cask swiftbar`, then run `spyhop` once more. The orca icon is added for you.

## Summarizer

Spyhop uses the AI you already have: a logged-in `claude` or `codex` CLI. Switch models in **Settings → Summarizer**.
Transcripts go to the model you pick (keys and passwords are masked first), so pick one your organization allows.

## What you get

- **Step flow** on every card: `Done` · `Now` · `Next`, plus purple `Intercept` for a quick side task. When space runs out, cards shrink to progress bars (`3/4 · Review`).
- **No progress** badge when a working session hasn't written anything for 5 minutes.
- **Helpers**: panes a session starts through Orca orchestration (a cross-check, a review) appear as one line under that session, not as their own card.
- **Detail view**: every step explained, the last reply, a TODO checklist, the session ID, and buttons to jump to or end the session.

![Detail](docs/screenshots/detail.png)

- **Group by AI topics** instead of Orca workspaces. Drag a card to another group to pin it there.

![AI groups](docs/screenshots/ai-groups.png)

- **Settings**: summarizer, 10 themes (GitHub, Catppuccin, Solarized, Rosé Pine, Tokyo Night, Dracula, Nord…), start at login, update interval, live CPU and memory.

![Settings](docs/screenshots/settings.png)

- **Menu bar**: how many sessions are waiting for you; click a row to jump there.

<img src="docs/screenshots/panel.png" width="320" alt="Menu bar panel">

## Uninstall

```bash
brew uninstall spyhop && rm -rf ~/.spyhop
```

Turn off **Start at login** in Settings first, and remove the **.spyhop** project from Orca's sidebar.

## More

How it works, privacy and file locations: [docs/details.md](docs/details.md).

## TODO

- [ ] Work without Orca: find sessions from recent transcripts and group them by AI topics.
- [ ] Many groups: sideways scroll and a "reset groups" button.
- [ ] Moving a session to another workspace, made safe end to end.
- [ ] Notify when a session turns to "My turn".
