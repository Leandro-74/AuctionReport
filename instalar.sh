#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if ! command -v python3 >/dev/null 2>&1; then
    echo "Python 3 não encontrado."
    echo "No Arch Linux, instale com: sudo pacman -S python"
    exit 1
fi

if ! python3 -c 'import sys; raise SystemExit(0 if sys.version_info >= (3, 10) else 1)'; then
    echo "É necessário Python 3.10 ou superior."
    python3 --version
    exit 1
fi

if [ ! -x .venv/bin/python ]; then
    echo "Criando o ambiente virtual em .venv..."
    python3 -m venv .venv
fi

.venv/bin/python -m pip install --upgrade pip
.venv/bin/python -m pip install -r requirements.txt

if ! command -v soffice >/dev/null 2>&1 && ! command -v libreoffice >/dev/null 2>&1; then
    echo
    echo "Aviso: LibreOffice não encontrado. A exportação em PDF ficará"
    echo "indisponível até que ele seja instalado."
    echo "No Arch Linux, instale com: sudo pacman -S libreoffice-fresh"
fi

echo
echo "Pronto! Use: ./iniciar.sh"
