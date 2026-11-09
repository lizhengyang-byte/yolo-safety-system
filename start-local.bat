@echo off
chcp 65001 >nul
REM ============================================================
REM  工地AI安全智能监测系统 - 本地一键启动（不使用 Docker）
REM  依赖：仓库根目录 .venv（含后端依赖）、frontend/node_modules 已安装
REM ============================================================
cd /d "%~dp0"

REM 1) 后端 FastAPI（SQLite，端口 8000）
start "yolo-backend" cmd /k "cd /d %~dp0backend && ..\.venv\Scripts\python.exe -m uvicorn app.main:app --host 127.0.0.1 --port 8000"

REM 2) 前端 Vite 开发服务器（端口 3000，代理 /api、/images 到后端）
start "yolo-frontend" cmd /k "cd /d %~dp0frontend && npm run dev"

REM 3) 推理服务（拉取后台已启用的摄像头/本地视频；无摄像头时自动退出）
REM    如需启用，取消下面一行的注释（确保已在后台录入摄像头）
REM start "yolo-inference" cmd /k "cd /d %~dp0 && set CONFIG_PATH=inference\config.local.yaml && .venv\Scripts\python.exe -m inference.main"

echo.
echo 已启动服务（各服务独立窗口，关闭窗口即停止）：
echo   后端接口文档: http://localhost:8000/docs
echo   后台数据看板: http://localhost:3000/dashboard   (默认账号 admin / admin123)
echo   智慧大屏:     http://localhost:3000/screen
echo   大屏 Kiosk:   deploy\start-screen.bat（全屏值班/电视墙）
echo   临时演示:     http://localhost:3000/demo
echo.
echo 提示：推理服务默认未启动，需先在后台「摄像头管理」录入设备，
echo       再取消本脚本第 3 步注释后重新运行。
echo.
REM 如需启动后自动打开智慧大屏，取消下一行注释（等待前端编译完成）
REM timeout /t 6 /nobreak >nul & start "" http://localhost:3000/screen
pause
