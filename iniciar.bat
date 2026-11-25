@echo off
chcp 65001 >nul
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
    echo.
    echo Python nao encontrado.
    echo Rode primeiro o instalar.bat ou instale o Python em https://www.python.org/downloads/
    echo.
    pause
    exit /b 1
)
python -c "import openpyxl, pdfplumber, rich" >nul 2>nul
if errorlevel 1 (
    echo.
    echo Dependencias nao instaladas. Rode o instalar.bat primeiro.
    echo.
    pause
    exit /b 1
)
python -m leilao
pause
