<h1 align="center">AuctionReport</h1>

<p align="center">
  Builds Excel reports for auctioned municipal assets from PDF reports and a bill of law.
</p>

<p align="center">
  <a href="https://github.com/Leandro-74/AuctionReport">English</a> | <a href="README.pt-BR.md">Português</a>
</p>

## About

AuctionReport is a local Python tool that prepares the asset reports for public
auctions of the Brazilian municipality. It reads the PDF reports exported by
the BIRT system (Prefeitura, Saúde and, when available, Educação), reads the bill of
law that defines the lots, and builds an editable input workbook. After review, it
generates the final Excel file with the official template layout.

The tool runs as a terminal UI (TUI) or as a command-line program. All processing
happens on the local computer.

## Features

- Read the **Termo de Responsabilidade** PDFs from Prefeitura, Saúde and, when
  available, Educação.
- Read the **bill of law** and identify lots, asset codes and appraised values.
- Create an editable input workbook with all assets and a suggested lot for each one.
- Edit data in the TUI:
  - move assets by code, code range or description text;
  - change a lot's sale value, group and section;
  - change an asset's description, accounts, code and lot;
  - replace a text fragment in several descriptions;
  - add or remove lots and assets;
  - edit groups, bank accounts, branch and CNPJ.
- Split each lot's value among its assets with at most **two decimal places**.
- Put the remainder on the **last asset** of the lot, so the sum matches exactly.
- Generate the final report with the **template layout**:
  - main sheets by department/group;
  - auxiliary sheets by category (`Todos os Veículos`, `Veículos`,
    `Veículos Hospital`, `Mobiliário em Geral`, `Mobiliário em Geral H`,
    `Itens de Informática`);
  - deposit account sheets (`Conta Município`, `Conta Fundo Municipal de Saude`).
- Optionally generate an extra `Resumo` sheet for lot-by-lot checking.

## Requirements

- Python 3.10 or higher.
- Windows or Linux.
- `tkinter` is optional. It enables the graphical file picker. Without it, the TUI
  asks for the file paths.

### Note for Linux

The graphical file picker needs the `tk` package:

- Arch Linux: `sudo pacman -S tk`
- Debian/Ubuntu: `sudo apt install python3-tk`

On Arch Linux, `pip install` is blocked outside a virtual environment. The
`instalar.sh` script creates a `.venv` folder and installs the dependencies there.

## Installation

### Windows

Double-click `instalar.bat`, or run:

```powershell
python -m pip install -r requirements.txt
```

### Linux

```bash
git clone https://github.com/Leandro-74/AuctionReport.git
cd AuctionReport
./instalar.sh
```

If the script is not executable, run it with `bash instalar.sh` or use
`chmod +x instalar.sh iniciar.sh testar.sh` first.

## Usage

### Windows

Double-click `iniciar.bat`, or run:

```powershell
python -m leilao
```

### Linux

```bash
./iniciar.sh
```

Or use the virtual environment directly:

```bash
.venv/bin/python -m leilao
```

The TUI opens the main menu:

1. **Novo leilão** — opens the graphical file picker and creates the input
   workbook.
2. **Abrir/editar** — loads an input workbook and opens the editing menu.
3. **Gerar relatório** — validates the data and generates the Excel file in the
   template layout.
4. **Conferir** — shows totals and warnings without generating a file.
5. **Grupos e contas** — edits bank data and sheets.
6. **Modelo vazio** — creates a blank input workbook.

After importing, the program opens the editing panel, showing:

- totals by group;
- lot by lot: value, sum of assets and status;
- warnings and errors.

If the graphical file picker is unavailable, the TUI asks for the path directly.
Press Enter to skip an optional file.

## Editing by code

In the **Abrir/editar** menu, the main options are:

### Move assets

Selection examples:

| Selection | What it moves |
|---|---|
| `300-400` | All codes from 300 to 400 |
| `300,305,310` | Only those three codes |
| `300..400` | Same as `300-400` |
| text `MESA` | Assets whose description contains `MESA` |
| lot `08` + range `300-400` | Only codes 300–400 that are in lot 08 |

Before applying, the TUI shows a preview with the number of assets found and asks
for confirmation. If no filter is provided, the move is blocked to avoid moving
every asset by accident.

### Edit lot

Changes the sale value, the group (sheet) and the section (title) of the lot.

### Edit asset

Changes description, code, lot, type, category, Conta Crédito, Conta Débito, book
value and note. Press Enter to keep the current value.

### Replace text

Replaces a text fragment in several descriptions, optionally filtered by lot or
category. It also shows a preview before applying.

### Add or remove

Creates lots and assets, removes empty lots and deletes assets by code, range, text,
lot or category.

Changes are saved automatically to the input workbook. The previous version is kept
as `leilao_entrada.backup.xlsx`.

> Editing is done in the **input workbook**, which is the source of the data. After
> editing, use **Gerar relatório** to update the final Excel file. Edits made
> manually in the final report do not go back to the input workbook.

## How values are split

The total value of the lot is divided by the number of assets. The installments have
two decimal places and the remainder goes to the last asset.

Real example from the 2025 workbook: lot 14 had **211 assets** and was sold for
**R$ 50.00**.

- 210 assets × R$ 0.23 = R$ 48.30
- last asset = R$ 50.00 − R$ 48.30 = **R$ 1.70**
- sum = **R$ 50.00**

The quotient is truncated down (`0.2369...` becomes `0.23`), never rounded up, so the
last installment is never negative. The program checks the sum of every lot before
generating the file.

## Generated report

By default, the program generates only the template sheets. The `Resumo` sheet is
optional and can be included when generating the file.

The template layout is reproduced with:

- main sheets with 6 columns, title, account data, total of the lots and sections per
  lot;
- auxiliary sheets: `Todos os Veículos` with 6 columns (includes Conta Crédito), the
  others with 5 columns (`Tipo de bem`, `Código`, `Conta Débito`, `Descrição`,
  `Valor`);
- account sheets with 4 columns and blocks for branch, checking account, CNPJ and
  total;
- Calibri/Arial fonts, gray `D9D9D9` background, thin borders, `R$ #,##0.00` format,
  column widths and margins equal to the template.

Auxiliary sheets are created automatically from the data:

- `Relatório Todos os Veículos` — all vehicles;
- `Relatório Veículos` — Prefeitura/Educação vehicles (when there are also Saúde
  vehicles);
- `Relatório Veículos Hospital` — Saúde vehicles (when there are also municipal
  vehicles);
- `Relatório Mobiliário em Geral` — municipal furniture;
- `Relatório Mobiliário em Geral H` — Saúde hospital assets;
- `Relatório Itens de Informática` — municipal IT items;
- `Relatório Outros Bens` — other municipal categories, when present.

> The original template had small filling differences between the auxiliary sheets
> (some with a darker gray background and zebra rows). The tool standardizes these
> sheets to the same pattern as the main sheets, keeping the template titles, columns,
> fonts, borders, widths and margins.

## Command line

The TUI is the recommended flow, but the commands remain available for automation.

On Windows:

```powershell
python -m leilao importar --prefeitura "Report_prefeitura.pdf" --saude "Report_saúde.pdf" --pl "Projeto de Lei.pdf" -o leilao_entrada.xlsx

python -m leilao conferir leilao_entrada.xlsx

python -m leilao gerar leilao_entrada.xlsx -o relatorio_leilao.xlsx

python -m leilao gerar leilao_entrada.xlsx -o relatorio_leilao.xlsx --com-resumo

python -m leilao modelo -o modelo_leilao.xlsx
```

On Linux, use `./iniciar.sh` before the same arguments, or the virtual environment:

```bash
./iniciar.sh importar --prefeitura "Report_prefeitura.pdf" --pl "Projeto de Lei.pdf" -o leilao_entrada.xlsx
.venv/bin/python -m leilao conferir leilao_entrada.xlsx
.venv/bin/python -m leilao gerar leilao_entrada.xlsx -o relatorio_leilao.xlsx
```

## Input workbook

### Bens sheet

| Column | Purpose |
|---|---|
| Lote | Lot where the asset enters. **Empty = asset ignored.** |
| Tipo de bem | Usually `Bens Móveis`. |
| Código | Asset code. |
| Conta Crédito / Conta Débito | Accounting accounts. They may be empty. |
| Descrição | Description used in the report. |
| Valor Contábil | Value from the system, used only as reference. |
| Origem | Prefeitura, Saúde or Educação. |
| Categoria | Veículos, Mobiliário, Informática, Hospitalar or Outros. |
| Observação | Free text. |

### Lotes sheet

| Column | Purpose |
|---|---|
| Lote | Lot number, with two digits (`01`, `02`...). |
| Valor da venda | Winning bid value. This is the value that will be split. |
| Grupo | Group name from the Grupos sheet. Decides which sheet the lot appears in. |
| Seção | Section title. Lots with the same section and group stay together. |
| Valor avaliado (PL) | Reference from the bill of law. |
| Descrição do PL | Bill of law text, for reference only. |

### Grupos sheet

Sheet name, title, subtitle, deposit account, branch, checking account and CNPJ. To
create a new sheet, add a row and use that name in the **Grupo** column of the lots.

### Avisos sheet

Records import warnings (asset without lot, lot without assets in the report, and so
on).

## Notes and limits

- The PDFs must be the table reports generated by the system (BIRT), with the columns
  `Tipo do Bem`, `Código`, `Descrição` and `Valor Contábil`.
- Accounting accounts do not come in the PDFs. The program leaves the columns empty;
  fill them in the Bens sheet or in the TUI if the report needs them.
- The automatic lot suggestion is a starting point. Always review the Bens sheet,
  especially Saúde assets and generic lots.
- If a bill of law lot has no assets in the reports, the program creates a row from
  the bill description and shows a warning. Review the description, code, accounts
  and book value of that row.
- Each lot belongs to a **single group/sheet**. If the same lot has assets from
  different groups, split it into two lots (for example, `08` and `08-A`).
- Lot numbers must be unique, even across different groups.
- Assets without a lot do not enter the report and appear in the warning and in the
  Avisos sheet.

## Tests

On Windows:

```powershell
python -m unittest discover -s tests -v
```

On Linux:

```bash
./testar.sh
```

Or directly:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

The tests include:

- reproduction of the real lot 14 (211 assets, R$ 50.00);
- reading the sample PDFs;
- comparison of fonts, fills, borders, widths and margins with the template;
- moving assets by code range;
- editing lots, descriptions, accounts, adding and removing;
- checking that every sum matches.

> The municipality PDFs and workbooks are **not versioned** in the repository. To
> run the integration tests, put the sample files in the project root. Without them,
> those tests are skipped automatically.

## Project structure

```
AuctionReport/
  leilao/
    money.py       money, Brazilian formatting and value splitting
    models.py      asset, lot, group and result models
    pdfs.py        reading reports and the bill of law
    entrada.py     input workbook creation and reading
    edicao.py      asset, lot and group editing
    relatorio.py   final Excel generation in the template layout
    tui.py         TUI and native file selection
    cli.py         command line
  tests/
    test_money.py
    test_pdfs.py
    test_edicao.py
    test_template.py
    test_integracao.py
  instalar.bat / iniciar.bat   Windows setup and launcher
  instalar.sh / iniciar.sh     Linux setup and launcher
  testar.sh                    test runner on Linux
  README.md
  README.pt-BR.md
```

## Troubleshooting

- **`ModuleNotFoundError`**: run the installation step again:
  `./instalar.sh` on Linux or `instalar.bat` on Windows.
- **No file dialog on Linux**: install Tk (`sudo pacman -S tk` on Arch) and run the
  program again. Without Tk, type the file paths in the prompt.
- **Cannot save the workbook**: close the file in Excel or LibreOffice and try again.
- **Integration tests are skipped**: the sample PDFs and workbooks are missing from
  the project root.
- **`Permission denied` when running a script**: use `bash instalar.sh` or run
  `chmod +x instalar.sh iniciar.sh testar.sh`.

## Contributing

Found a bug or have an idea? Open an
[issue](https://github.com/Leandro-74/AuctionReport/issues) or send a pull request.
