@echo off
setlocal
cd /d "%~dp0"

rem CDN root on the machine that actually runs the server. Override with
rem ESTERIA_CDN_ROOT when the CDN lives somewhere else (for example a network mount).
if "%ESTERIA_CDN_ROOT%"=="" set "ESTERIA_CDN_ROOT=G:\EsteriaCDN"
if "%ESTERIA_CDN_ROOT:~-1%"=="\" set "ESTERIA_CDN_ROOT=%ESTERIA_CDN_ROOT:~0,-1%"

set "CHECK_ONLY="
if /i "%~1"=="/check" set "CHECK_ONLY=1"

if not exist "src\index.ts" (
	echo.
	echo Server source is missing from "%~dp0src".
	echo.
	exit /b 1
)

set "CLIENT_ROOT_DIR=%ESTERIA_CDN_ROOT%\client"
set "CLIENT_CHANNELS=live"
set "LAUNCHER_UPDATES_DIR=%ESTERIA_CDN_ROOT%\launcher-updates"
set "ADDONS_DIR=%ESTERIA_CDN_ROOT%\addons"
set "SOCIAL_DATA_DIR=%ESTERIA_CDN_ROOT%\social"
set "PORT=7384"

if exist "%ESTERIA_CDN_ROOT%\news.json" set "NEWS_FILE=%ESTERIA_CDN_ROOT%\news.json"
if exist "%ESTERIA_CDN_ROOT%\status.json" set "STATUS_FILE=%ESTERIA_CDN_ROOT%\status.json"
if exist "%ESTERIA_CDN_ROOT%\social.json" set "SOCIAL_FILE=%ESTERIA_CDN_ROOT%\social.json"
if exist "%ESTERIA_CDN_ROOT%\armory.json" set "ARMORY_FILE=%ESTERIA_CDN_ROOT%\armory.json"
if exist "%ESTERIA_CDN_ROOT%\database-index.json" set "DATABASE_FILE=%ESTERIA_CDN_ROOT%\database-index.json"

if not exist "%SOCIAL_DATA_DIR%" mkdir "%SOCIAL_DATA_DIR%"

echo Esteria CDN and account service
echo   Server    : %~dp0
echo   CDN root  : %ESTERIA_CDN_ROOT%
echo   Client    : %CLIENT_ROOT_DIR%\live
echo   Updates   : %LAUNCHER_UPDATES_DIR%
echo   Accounts  : %SOCIAL_DATA_DIR%
echo   Endpoint  : http://127.0.0.1:%PORT%
echo.

if not exist "%CLIENT_ROOT_DIR%\live\Wow.exe" (
	echo Warning: no Esteria client at "%CLIENT_ROOT_DIR%\live".
	echo The client channel reports unavailable until the client is staged there.
	echo.
)

if defined CHECK_ONLY (
	echo /check complete - nothing was started.
	exit /b 0
)

if not exist "node_modules" (
	echo Installing server dependencies...
	call npm install --no-audit --no-fund || exit /b 1
)

echo First start hashes the whole client into manifest-v2.json, which can take a while.
echo Press Ctrl+C to stop.
echo.

call npm run dev
