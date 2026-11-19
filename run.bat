@echo off
chcp 65001 >nul
title Народный бенчмарк (локально)
cd /d "%~dp0"
if not exist .venv (
  echo [1/3] Создаю виртуальное окружение...
  python -m venv .venv
)
call .venv\Scripts\activate.bat
echo [2/3] Устанавливаю Django...
pip install -q "Django>=5.2,<6.0" "dj-database-url>=2.2" "whitenoise>=6.7"
python manage.py migrate -v 0
echo [3/3] Запускаю сайт на http://localhost:8765/ — окно не закрывайте.
start "" /min cmd /c "timeout /t 3 >nul & start http://localhost:8765/"
python manage.py serve --noreload
pause
