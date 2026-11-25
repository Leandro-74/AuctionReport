@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo Instalando as dependencias do AuctionReport...
where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo Python nao encontrado.
    echo Instale o Python 3.10 ou superior em https://www.python.org/downloads/
    echo e marque a opcao "Add Python to PATH".
    echo.
    pause
    exit /b 1
)
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
echo.
echo Para exportar PDF, instale o LibreOffice: https://www.libreoffice.org/
echo Pronto! Agora use o iniciar.bat.
pause
