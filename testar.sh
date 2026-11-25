#!/usr/bin/env bash
set -euo pipefail

cd "$(dirname "$0")"

if [ -x .venv/bin/python ]; then
    PYTHON=.venv/bin/python
elif command -v python3 >/dev/null 2>&1; then
    PYTHON=python3
else
    echo "Python 3 não encontrado. Rode ./instalar.sh primeiro."
    exit 1
fi

if ! "$PYTHON" -c 'import openpyxl, pdfplumber, rich' >/dev/null 2>&1; then
    echo "Dependências não instaladas. Rode ./instalar.sh primeiro."
    exit 1
fi

exec "$PYTHON" -m unittest discover -s tests -v "$@"
