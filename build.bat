@echo off
cd /d "%~dp0"
python -m pip install -r requirements.txt || exit /b 1
python -m PyInstaller --noconfirm --clean --onefile --windowed ^
  --name "AFK Fortnite" ^
  --distpath publish --workpath build ^
  afk_gui.py || exit /b 1
echo.
echo Executavel gerado em publish\AFK Fortnite.exe
