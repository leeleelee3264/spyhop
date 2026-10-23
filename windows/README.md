# Spyhop for Windows (community preview)

A side port of the Spyhop browser board for Windows. It lives only in this folder and shares no code with the macOS app: `board.py` here is a copy of `legacy/mac-browser/board.py` with Windows support added, so changes on one side do not reach the other. There is no installer and no automatic update.

## Get started

You need Windows 10 or 11, Python 3.9+ (`winget install Python.Python.3.12`), and a logged-in `claude` or `codex` CLI.

```powershell
git clone https://github.com/leeleelee3264/spyhop
.\spyhop\windows\spyhop.cmd install
```

Or download the repository as a ZIP from GitHub, unzip it, and run `windows\spyhop.cmd install`. To update, run `git pull` (or download the ZIP again).

`install` adds a **Spyhop** icon to the Start menu and the desktop. Open it like any app: the board shows in its own window, and the tray icon starts with it. `spyhop.cmd` with no option does the same without adding icons, and `spyhop.cmd uninstall` removes the icons and turns off Start at login. `spyhop.cmd doctor` explains how each session was found, or why it was not.

The Spyhop window is a Microsoft Edge app window (no address bar) with a profile of its own (`%LOCALAPPDATA%\Spyhop\window`), so it does not mix with your usual Edge and shows as its own button on the taskbar. Opening Spyhop again brings the same window back instead of opening another. The board also works in any browser at `http://127.0.0.1:47613/`. Unlike the macOS app, this saves no memory: the window uses the same engine as Edge.

A **tray icon** appears next to the clock, like the macOS app's menu bar icon. It shows how many sessions are waiting for you (gray when the board is off). Click it to open the small board panel; right-click it to see every session and jump to one, or to open the board window. It also restarts the board when Claude or Codex runs. Choose **Hide tray icon** at the bottom of its right-click menu to remove it; opening Spyhop brings it back. At login (Start at login) only the tray icon and the board start, no window, as on macOS.

`windows/spyhop.ico` is made from the macOS app icon by `python windows/tools/make_icon.py`; run it again when that icon changes.

## What works

- Sessions in Windows Terminal, VS Code, PowerShell or cmd are grouped by folder and terminal. Sessions the **Claude desktop app** runs show up under `folder · Claude app`.
- **Claude app Code tab sessions** used in the last 12 hours show up even when the app has put them to sleep, read from the app's own session records. Archived ones are left out.
- **Codex desktop app** threads (Codex inside the ChatGPT app, or the IDE extension) used in the last 12 hours show up under `folder · Codex app`, read from Codex's `state_N.sqlite`. Only threads you started are shown.
- **Cowork** sessions show up only when the app keeps their records on your computer (`local-agent-mode-sessions`). Recent Cowork versions keep sessions inside the Cowork virtual machine's disk, so those cannot be shown.
- **Go to session** brings that terminal or app window to the front. It cannot pick the exact tab.
- **End session** force-closes the AI program (Windows has no SIGTERM). The terminal tab stays. An ended session stays off the board even though the Claude or Codex app keeps its record, until you use it again (`~/.spyhop/ended.json`). On a desktop app session with no program running, End session just hides the card the same way.
- Summaries, AI topic grouping and **Start at login** (a `Spyhop` entry under `HKCU\...\CurrentVersion\Run`) work as on macOS.
- Not on Windows: Orca, moving sessions, and automatic updates.
- DeepSeek reads its key from the `DEEPSEEK_API_KEY` environment variable instead of the Keychain.

## Tests

```powershell
cd windows
python -X utf8 -m unittest discover -s tests
```

CI runs these on `windows-latest` for every pull request that touches `windows/` (see `.github/workflows/windows.yml`). The tray icon and window focus cannot be tested there.
