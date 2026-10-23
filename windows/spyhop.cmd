@echo off
rem Spyhop (Windows)
rem   spyhop            start the board and the tray icon, and open the board in its own window
rem   spyhop install    add Spyhop to the Start menu and the desktop
rem   spyhop uninstall  remove those icons and turn off Start at login
rem   spyhop doctor     explain how each session was found, or why it was not (add --titles to show titles)
setlocal
set "d=%~dp0"
set "PY=python"
set "PYW=pythonw"
where py >nul 2>nul && set "PY=py -3"
where pyw >nul 2>nul && set "PYW=pyw -3"

if /i "%~1"=="doctor" (
  %PY% -X utf8 "%d%board.py" --doctor %2 %3
  exit /b %errorlevel%
)
if /i "%~1"=="install" (
  %PY% -X utf8 "%d%tray.py" --install
  exit /b %errorlevel%
)
if /i "%~1"=="uninstall" (
  %PY% -X utf8 "%d%tray.py" --uninstall
  exit /b %errorlevel%
)

%PY% -X utf8 "%d%board.py" --ensure >nul || exit /b 1
rem The tray icon opens the board window (only one tray runs; a second start hands the request to it).
start "" %PYW% -X utf8 "%d%tray.py" --open-board
echo opened: Spyhop window
