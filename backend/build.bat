@echo off
REM 织识一键打包：构建前端 + PyInstaller 打包（onedir）
REM 产物：backend\dist\织识\织识.exe
cd /d %~dp0..
echo [1/2] 构建前端...
cd frontend
call npm run build || exit /b 1
cd ..\backend
echo [2/2] PyInstaller 打包...
python -m PyInstaller weave.spec || exit /b 1
echo.
echo 完成：backend\dist\织识\织识.exe
echo 首次运行数据将保存在 %%APPDATA%%\织识\
