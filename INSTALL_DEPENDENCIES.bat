@echo off
setlocal
chcp 65001 >nul
cd /d "%~dp0"
title Установка зависимостей игры
echo Будет создано отдельное окружение .venv в папке игры.
echo Нужен интернет. Другие окружения Python не изменяются.
if exist "%~dp0.venv\Scripts\python.exe" (
  "%~dp0.venv\Scripts\python.exe" "%~dp0launcher.py" --install
  goto finish
)
where py.exe >nul 2>nul
if not errorlevel 1 (
  py -3 "%~dp0launcher.py" --install
  goto finish
)
where python.exe >nul 2>nul
if not errorlevel 1 (
  python "%~dp0launcher.py" --install
  goto finish
)
set /p "GAME_PYTHON=Полный путь к python.exe версии 3.10-3.13: "
set "GAME_PYTHON=%GAME_PYTHON:"=%"
if not exist "%GAME_PYTHON%" (
  echo Файл не найден. См. docs\START_RU.md.
  pause
  exit /b 1
)
"%GAME_PYTHON%" "%~dp0launcher.py" --install --python "%GAME_PYTHON%"
:finish
if errorlevel 1 (
  echo Установка не завершена. См. сообщение выше и docs\START_RU.md.
  pause
  exit /b 1
)
pause
exit /b 0
