@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title persian fairytale. V2.
if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" "%~dp0launcher.py"
  goto finish
)
where py.exe >nul 2>nul
if not errorlevel 1 (
  py -3 "%~dp0launcher.py"
  goto finish
)
where python.exe >nul 2>nul
if not errorlevel 1 (
  python "%~dp0launcher.py"
  goto finish
)
echo Не найден Python в PATH. Укажите полный путь к python.exe.
echo Существующая среда вашего проекта не будет изменена.
set /p "GAME_PYTHON=Путь к python.exe: "
set "GAME_PYTHON=%GAME_PYTHON:"=%"
if not exist "%GAME_PYTHON%" (
  echo Файл не найден. См. docs\START_RU.md.
  pause
  exit /b 1
)
"%GAME_PYTHON%" "%~dp0launcher.py" --python "%GAME_PYTHON%"
:finish
if errorlevel 1 (
  echo.
  echo Подсказки по запуску: docs\START_RU.md
  pause
  exit /b 1
)
exit /b 0
