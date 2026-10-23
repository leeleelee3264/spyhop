# Claude desktop app (Code tab) sessions on the board

Date: 2026-10-20
Updated: 2026-10-23

Implementation and tests live under `macos/board/`; the frozen `legacy/mac-browser/` implementation is unchanged. This covers local Code sessions, not sessions running on cloud or SSH hosts.

## Problem

Claude Code sessions started from the Claude desktop app's Code tab run with no
terminal (`tty` is `??`). `outside_terms()` treats every tty-less `claude` process
as a headless program and skips it, so these sessions never become cards.

Everything else Spyhop needs is already there: the desktop app registers each
session in `~/.claude/sessions/<pid>.json` with `entrypoint: "claude-desktop"`,
`hostSessionId` (`local_…`), `name`, `status` (`busy`/`idle`) and `sessionId`,
and writes the normal transcript under `~/.claude/projects/`.

## Design

### Detection (`agent_procs`, `outside_terms`)

- When reading `~/.claude/sessions/<pid>.json`, also keep `entrypoint`,
  `hostSessionId` and `name` on the agent dict (`a['desktop']`, `a['host_sid']`,
  `a['name']`). Mark the resolved transcript with `how='claude:desktop-app'`
  when `entrypoint == 'claude-desktop'`, else `how='claude:process'` as today.
- `outside_terms()` lets a tty-less process through when `a.get('desktop')` is
  true. All other tty-less processes are still skipped.
- Column id `term:Claude App:<cwd>`, display name `<folder> · Claude App`.
- `t['title']` is the app's session `name` so `board.py --doctor --titles` shows it.
  The card title still comes from the summarizer as for every other session.
- Busy/idle maps to `agent.state` exactly like terminal claude sessions.

### Go to session (`focus_outside`)

- A desktop session opens `claude://code/continue?session=<hostSessionId>` via
  `open <url>`, then explicitly bring Claude forward with `open -a Claude`. Returns `'tab'` when both calls succeed.
- If `hostSessionId` is missing or `open` fails, fall back to `_open_app('Claude')`
  and return `'app'` (or `''`).
- Deep-link format verified in `Claude.app` 2.42304.2 and live-tested with 3.6556.2 (`claudeURLHandler`,
  `/continue` with `?session=`).

### End session

Unchanged: SIGTERM to the pid. The app shows the session as ended.

### Not in scope

Dragging a card to another workspace (already blocked for all `term:` columns),
subagent/child sessions (still hidden), Windows.

### Docs

README "What works where" gets a "Claude app" column; the "Start or keep a
session running anywhere" line and `docs/details.md` mention the desktop app.

### Tests (`macos/board/tests/test_desktop.py`)

- Desktop registration + tty `??` → one term with column `Claude App` and
  `agent.state` from `status`.
- tty `??` without desktop registration → still skipped.
- `focus_outside` on a desktop agent runs `open claude://code/continue?session=local_x`
  and reports `'tab'`; when `open` fails it reports `'app'` after `_open_app('Claude')`.

Current validation: the macOS board suite passes locally. Live local Code sessions were used to verify discovery, busy/idle status, and switching between sessions. The installed Spyhop app was not replaced; live checks use the candidate Python implementation.
