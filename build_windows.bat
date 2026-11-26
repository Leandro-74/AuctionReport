@echo off
chcp 65001 >nul
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
    echo Python nao encontrado. Instale o Python 3.10 ou superior.
    pause
    exit /b 1
)

python -m pip install --upgrade pip
python -m pip install -r requirements.txt pyinstaller

python -m PyInstaller ^
    --noconfirm ^
    --clean ^
    --onefile ^
    --console ^
    --name AuctionReport ^
    --icon assets\logo.ico ^
    --collect-all pdfplumber ^
    --collect-all pdfminer ^
    --collect-all pypdfium2 ^
    --collect-all rich ^
    main.py

if errorlevel 1 (
    echo Falha ao gerar o executavel.
    pause
    exit /b 1
)

copy /Y config.example.json dist\config.example.json >nul
copy /Y README.md dist\README.md >nul
copy /Y README.pt-BR.md dist\README.pt-BR.md >nul

powershell -NoProfile -Command ^
    "Compress-Archive -Path 'dist\AuctionReport.exe','dist\config.example.json','dist\README.md','dist\README.pt-BR.md' -DestinationPath 'AuctionReport-windows.zip' -Force"

echo.
echo Pronto: AuctionReport-windows.zip
pause
