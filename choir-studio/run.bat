@echo off
cd /d "%~dp0"
set "CHOIR_NODE="
for /f "delims=" %%I in ('where node.exe 2^>nul') do if not defined CHOIR_NODE set "CHOIR_NODE=%%I"
if not defined CHOIR_NODE if exist "%ProgramFiles%\nodejs\node.exe" set "CHOIR_NODE=%ProgramFiles%\nodejs\node.exe"
if not defined CHOIR_NODE (
  echo Node.js was not found. Install Node.js 22 or later from https://nodejs.org/
  pause
  exit /b 1
)
echo Starting Choir Studio...
echo Open http://localhost:5173 in your browser.
"%CHOIR_NODE%" server.mjs --open
echo Server stopped. See any error above.
pause
