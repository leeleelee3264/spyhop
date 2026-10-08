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
  <img alt="Homebrew" src="https://img.shields.io/badge/brew-leeleelee3264%2Ftap-1e293b?logo=homebrew&logoColor=white">
  <img alt="Claude Code" src="https://img.shields.io/badge/Claude%20Code-supported-1e293b">
  <img alt="Codex" src="https://img.shields.io/badge/Codex-supported-1e293b">
  <img alt="Orca" src="https://img.shields.io/badge/Orca-workspaces-1e293b">
</p>

![Board](docs/screenshots/board.png)

Running several Claude Code and Codex sessions at once, it's easy to lose track of which one finished, which one is waiting for you, and which one is stuck.
Spyhop reads each session's transcript and turns it into a card: its steps, its TODOs and whose turn it is.

## Install

```bash
brew install leeleelee3264/tap/spyhop
spyhop
```

- **Needs** [Orca](https://github.com/stablyai/orca) and one summarizer (below). Spyhop finds sessions through Orca, so without it the board is empty.
- **Opens** in Orca as a **Spyhop** workspace, and at `http://127.0.0.1:47613/`.
- **Menu bar** (optional): `brew install --cask swiftbar`, then run `spyhop` once more. The orca icon is added for you.

## Summarizer

Pick one in **Settings → Summarizer**. Only the ones on your Mac are listed.

| | What you need | Notes |
|---|---|---|
| Claude | `claude` CLI logged in | Haiku, Sonnet, Opus, Fable |
| Codex | `codex` CLI logged in | Models in your Codex list |
| DeepSeek | `security add-generic-password -s deepseek-api -a "$USER" -w '<key>'` | Fastest, about 6 s per session |

Transcripts are sent to the model you pick. Strings that look like keys and passwords are masked first, but pick a model your organization allows.

## What you get

- **Cards** with steps (`Done` · `Now` · `Next` · purple `Intercept` for a side task), sorted so sessions waiting for you come first.
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
