@echo off
python -m pip install -r requirements.txt
python -m pip install pyinstaller
pyinstaller --clean --noconsole --onedir --name "Jupyter" main.py
pause
