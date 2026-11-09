@echo off
chcp 65001 >nul
REM ============================================================
REM  智慧大屏 - Kiosk 全屏启动（值班/展厅/电视墙）
REM  用法：
REM    deploy\start-screen.bat                默认自动轮播（overview ↔ alerts），25s
REM    deploy\start-screen.bat alerts         固定“告警”布局
REM    deploy\start-screen.bat auto 30        自动轮播，30s
REM  说明：需先启动后端 + 前端（start-local.bat）；本脚本只负责全屏打开浏览器。
REM ============================================================
setlocal
set "BASE=http://localhost:3000/screen"
set "LAYOUT=%~1"
if "%LAYOUT%"=="" set "LAYOUT=auto"
set "ROTATE=%~2"
if "%ROTATE%"=="" set "ROTATE=25"

REM 固定布局时默认不轮播；不带布局参数则按 ROTATE 轮播
if /I "%LAYOUT%"=="auto" (
  set "URL=%BASE%?rotate=%ROTATE%&present=1"
) else (
  set "URL=%BASE%?layout=%LAYOUT%&rotate=%ROTATE%&present=1"
)

set "BROWSER="
if exist "%ProgramFiles%\Google\Chrome\Application\chrome.exe" set "BROWSER=%ProgramFiles%\Google\Chrome\Application\chrome.exe"
if not defined BROWSER if exist "%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe" set "BROWSER=%ProgramFiles(x86)%\Google\Chrome\Application\chrome.exe"
if not defined BROWSER if exist "%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe" set "BROWSER=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe"
if not defined BROWSER if exist "%ProgramFiles%\Microsoft\Edge\Application\msedge.exe" set "BROWSER=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe"

if not defined BROWSER (
  echo [大屏] 未找到 Chrome 或 Edge，请手动打开：
  echo        "%URL%"
  pause
  exit /b 1
)

echo [大屏] 正在全屏打开："%URL%"
start "" "%BROWSER%" --kiosk "--app=%URL%" --autoplay-policy=no-user-gesture-required --disable-pinch --overscroll-history-navigation=0
