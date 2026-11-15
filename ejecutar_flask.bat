@echo off
cd /d "%~dp0"
if not exist "venv\Scripts\python.exe" (
  echo No se encontro el entorno virtual. Primero ejecuta: py -m venv venv
  echo Luego: venv\Scripts\activate y pip install -r requirements.txt
  pause
  exit /b 1
)
"venv\Scripts\python.exe" app.py
pause
