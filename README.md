<h1 align="center">AuctionReport</h1>

<p align="center">
  Builds Excel reports for auctioned municipal assets from PDF reports and a bill of law.
</p>

<p align="center">
  <a href="https://github.com/Leandro-74/AuctionReport">English</a> | <a href="README.pt-BR.md">Português</a>
</p>

## About

AuctionReport is a local Python tool that prepares the asset reports for public
auctions of a Brazilian municipality. It reads the PDF reports exported by the BIRT
system (Prefeitura and Saúde), reads the bill of law that defines the lots, and
stores the auction in a SQLite database.

Each auction lives in its own folder, with the source PDFs and the generated files.
Data is edited in a terminal UI (TUI). The final XLSX is generated on demand. Open it
to review, then export to PDF manually if needed.

## Features

- Read the **Termo de Responsabilidade** PDFs from Prefeitura and Saúde.
- Read the **bill of law** and identify lots, asset codes and appraised values.
- Create a **folder and SQLite database** for each auction.
- Copy the source PDFs into the auction folder.
- Compare new PDFs with an existing auction and preview new, changed and missing
  assets before applying.
- Edit data in the TUI:
  - move assets by code, code range, description, origin or category;
  - change a lot's sale value, group and section;
  - change an asset's description, accounts, code, origin and lot;
  - replace a text fragment in several descriptions;
  - add or remove lots and assets;
  - edit groups, bank accounts, branch and CNPJ.
- Split each lot's value among its assets with at most **two decimal places**.
- Put the remainder on the **last asset** of the lot, so the sum matches exactly.
- Export the final report as **XLSX**.
- Migrate an old input workbook (`.xlsx`) to the new database format.
- Optionally generate an extra `Resumo` sheet for lot-by-lot checking.

## Requirements

- Python 3.10 or higher.
- Windows or Linux.

### Note for Linux

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

## Configuration

The repository contains only fictitious placeholders. To use real municipality data:

1. Copy `.env.example` to `.env`.
2. Fill in the municipality title, agency, CNPJs and checking accounts.
3. Keep `.env` only on your computer. It is ignored by Git.

The variables are:

| Variable | Purpose |
|---|---|
| `AUCTIONREPORT_MUNICIPIO` | Municipality name used in report titles |
| `AUCTIONREPORT_TITULO_SAUDE` | Health fund title |
| `AUCTIONREPORT_SUBTITULO_PREFEITURA` | Prefeitura subtitle |
| `AUCTIONREPORT_SUBTITULO_SAUDE` | Saúde subtitle |
| `AUCTIONREPORT_AGENCIA` | Default bank branch |
| `AUCTIONREPORT_CNPJ_MUNICIPIO` | Municipality CNPJ |
| `AUCTIONREPORT_CNPJ_SAUDE` | Health fund CNPJ |
| `AUCTIONREPORT_CONTA_PREFEITURA` | Prefeitura checking account |
| `AUCTIONREPORT_CONTA_SAUDE` | Saúde checking account |

You can also change these values later in the **Grupos e contas** menu.

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

1. **Novo leilão** — reads the PDFs and creates the auction folder and database.
2. **Abrir leilão** — opens an existing `leilao.db`.
3. **Editar leilão** — edits assets, lots, values and descriptions.
4. **Atualizar com PDFs** — compares new PDFs with the current auction.
5. **Exportar** — generates the XLSX report.
6. **Conferir** — shows totals and warnings without generating files.
7. **Grupos e contas** — edits bank data and sheets.
8. **Migrar planilha antiga** — converts an old input workbook into a database.
9. **Novo leilão vazio** — creates an empty auction with the default groups.

After opening an auction, the editing panel shows:

- totals by group;
- lot by lot: value, sum of assets and status;
- warnings and errors.

When the TUI asks for a file or folder, drag it into the terminal or type/paste the
path. Quotes and escaped spaces are handled automatically. Press Enter on an optional
file to skip it.

## Auction folder

Every auction is a folder:

```text
leiloes/
  2026-2/
    leilao.db
    documentos/
      Report_prefeitura.pdf
      Report_saude.pdf
      projeto_de_lei.pdf
    exportacoes/
      2026-11-25_1430_relatorio.xlsx
```

- `leilao.db` is the source of truth.
- `documentos/` keeps the source PDFs.
- `exportacoes/` receives the generated XLSX files.

To back up an auction, copy the whole folder. To archive an auction, move the folder.
No server is needed: SQLite is a single file and comes with Python.

## Updating an auction

When new PDF reports arrive:

1. Open the auction.
2. Choose **Atualizar com PDFs**.
3. Select the updated reports and, if available, the updated bill of law.
4. Review the summary:
   - new assets;
   - changed assets and fields;
   - assets that no longer appear in the PDFs;
   - new lots from the bill of law;
   - warnings.
5. Confirm to apply the update.

The update is conservative:

- existing lots, accounts and notes are preserved;
- type, description and book value are updated from the PDF;
- new assets use the bill of law to suggest a lot;
- ambiguous codes are not assigned automatically;
- assets missing from the PDFs are kept and reported as warnings.

The source PDFs are copied into `documentos/` after a successful update.

## Editing by code

In the **Editar leilão** menu, the main options are:

### Move assets

Selection examples:

| Selection | What it moves |
|---|---|
| `300-400` | All codes from 300 to 400 |
| `300,305,310` | Only those three codes |
| `300..400` | Same as `300-400` |
| text `MESA` | Assets whose description contains `MESA` |
| lot `08` + range `300-400` | Only codes 300–400 that are in lot 08 |
| origin `Saúde` | Only assets from Saúde |

Before applying, the TUI shows a preview with the number of assets found and asks
for confirmation. If no filter is provided, the move is blocked to avoid moving
every asset by accident.

### Same code in different origins

Each asset code identifies one asset inside its origin. The same code can exist in
Prefeitura and in Saúde, for example code `3500`. When a code appears in more than
one origin, the TUI asks for the origin when editing and offers an origin filter when
moving or removing assets.

### Edit lot

Changes the sale value, the group (sheet) and the section (title) of the lot.

### Edit asset

Changes description, code, origin, lot, type, category, Conta Crédito, Conta Débito,
book value and note. Press Enter to keep the current value.

### Replace text

Replaces a text fragment in several descriptions, optionally filtered by lot,
category or origin. It also shows a preview before applying.

### Add or remove

Creates lots and assets, removes empty lots and deletes assets by code, range, text,
lot, category or origin.

Changes are saved automatically to the SQLite database.

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

The XLSX is intended for review. To print or share a PDF, open the XLSX in Excel or
LibreOffice and export it manually.

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
- `Relatório Veículos` — municipal vehicles (when there are also Saúde vehicles);
- `Relatório Veículos Hospital` — Saúde vehicles (when there are also municipal
  vehicles);
- `Relatório Mobiliário em Geral` — municipal furniture;
- `Relatório Mobiliário em Geral H` — Saúde hospital assets;
- `Relatório Itens de Informática` — municipal IT items;
- `Relatório Outros Bens` — other municipal categories, when present.

The `Resumo` sheet is optional and can be included when exporting.

## Command line

The TUI is the recommended flow, but the commands remain available for automation.

On Windows:

```powershell
python -m leilao novo --prefeitura "Report_prefeitura.pdf" --saude "Report_saúde.pdf" --pl "Projeto de Lei.pdf" --pasta leiloes/2026-2

python -m leilao conferir leiloes/2026-2/leilao.db

python -m leilao exportar leiloes/2026-2/leilao.db

python -m leilao exportar leiloes/2026-2/leilao.db --com-resumo

python -m leilao atualizar leiloes/2026-2/leilao.db --prefeitura "Report_prefeitura_novo.pdf"

python -m leilao atualizar leiloes/2026-2/leilao.db --prefeitura "Report_prefeitura_novo.pdf" --aplicar

python -m leilao migrar leilao_entrada.xlsx --pasta leiloes/2025-2
```

Without `--aplicar`, the `atualizar` command only shows the summary and warnings.

On Linux, use `./iniciar.sh` before the same arguments, or the virtual environment:

```bash
./iniciar.sh novo --prefeitura "Report_prefeitura.pdf" --pl "Projeto de Lei.pdf" --pasta leiloes/2026-2
.venv/bin/python -m leilao conferir leiloes/2026-2/leilao.db
.venv/bin/python -m leilao exportar leiloes/2026-2/leilao.db
```

The old XLSX commands are still available for legacy files:

- `importar` creates an old-style input workbook.
- `gerar` creates an XLSX report from an old input workbook.
- `modelo` creates a blank old-style input workbook.

## Database

The SQLite database stores groups, lots and assets. Assets are linked to lots by
internal IDs; the asset code is the business key used for search and reconciliation.

Rules enforced by the database and validation:

- lot numbers are unique inside the auction;
- group names are unique inside the auction;
- asset codes are unique inside each origin;
- the same asset code may exist in Prefeitura and Saúde;
- every lot must reference an existing group;
- every asset must reference an existing lot or have no lot.

The value split is calculated when the report is generated. It is not stored in the
database.

## Legacy input workbook

An old `leilao_entrada.xlsx` can be migrated with **Migrar planilha antiga** or the
`migrar` command. After migration, edit the data in the TUI and export the new
report.

The legacy workbook has these sheets:

### Bens sheet

| Column | Purpose |
|---|---|
| Lote | Lot where the asset enters. Empty = asset ignored. |
| Tipo de bem | Usually `Bens Móveis`. |
| Código | Asset code. |
| Conta Crédito / Conta Débito | Accounting accounts. They may be empty. |
| Descrição | Description used in the report. |
| Valor Contábil | Value from the system, used only as reference. |
| Origem | Prefeitura or Saúde. |
| Categoria | Veículos, Mobiliário, Informática, Hospitalar or Outros. |
| Observação | Free text. |

### Lotes sheet

| Column | Purpose |
|---|---|
| Lote | Lot number, with two digits (`01`, `02`...). |
| Valor da venda | Winning bid value. This is the value that will be split. |
| Grupo | Group name from the Grupos sheet. |
| Seção | Section title. |
| Valor avaliado (PL) | Reference from the bill of law. |
| Descrição do PL | Bill of law text, for reference only. |

### Grupos sheet

Sheet name, title, subtitle, deposit account, branch, checking account and CNPJ.

## Notes and limits

- The PDFs must be the table reports generated by the system (BIRT), with the columns
  `Tipo do Bem`, `Código`, `Descrição` and `Valor Contábil`.
- Accounting accounts do not come in the PDFs. The program leaves the columns empty;
  fill them in the TUI if the report needs them.
- The automatic lot suggestion is a starting point. Always review the assets,
  especially Saúde assets and generic lots.
- If a bill of law lot has no assets in the reports, the program creates a row from
  the bill description and shows a warning. Review the description, code, accounts
  and book value of that row.
- If a bill of law code matches more than one asset (for example, the same code in
  Prefeitura and Saúde), the automatic lot assignment is skipped and a warning asks
  for manual assignment.
- Each lot belongs to a **single group/sheet**. If the same lot has assets from
  different groups, split it into two lots (for example, `08` and `08-A`).
- Lot numbers must be unique, even across different groups.
- Assets without a lot do not enter the report and appear in the warnings.

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

The tests use the fictitious defaults; no `.env` file is required.

The tests include:

- reproduction of the real lot 14 (211 assets, R$ 50.00);
- reading the sample PDFs;
- comparison of fonts, fills, borders, widths and margins with the template;
- moving assets by code range and filtering by origin;
- SQLite persistence, updates, removals and legacy workbook migration;
- reconciliation of new PDFs with an existing auction;
- XLSX export workflow;
- checking that every sum matches.

> The municipality PDFs and workbooks are **not versioned** in the repository. To
> run the integration tests, put the sample files in the project root. Without them,
> those tests are skipped automatically.

## Project structure

```
AuctionReport/
  leilao/
    money.py        money, Brazilian formatting and value splitting
    models.py       asset, lot, group and result models
    config.py       municipality defaults loaded from .env
    pdfs.py         reading reports and the bill of law
    banco.py        SQLite storage, auction folders and migration
    atualizacao.py  reconciliation of new PDFs with an existing auction
    entrada.py      legacy input workbook support and validation
    edicao.py       asset, lot and group editing
    relatorio.py    final Excel generation in the template layout
    exportacao.py   XLSX export workflow
    tui.py          TUI and path input
    cli.py          command line
  tests/
    test_money.py
    test_pdfs.py
    test_edicao.py
    test_template.py
    test_banco.py
    test_atualizacao.py
    test_exportacao.py
    test_cli.py
    test_importacao.py
    test_integracao.py
  instalar.bat / iniciar.bat   Windows setup and launcher
  instalar.sh / iniciar.sh     Linux setup and launcher
  testar.sh                    test runner on Linux
  .env.example                 fictitious configuration template
  README.md
  README.pt-BR.md
```

## Troubleshooting

- **`ModuleNotFoundError`**: run the installation step again:
  `./instalar.sh` on Linux or `instalar.bat` on Windows.
- **Cannot save the auction**: close other programs that may be using `leilao.db`
  and try again.
- **Integration tests are skipped**: the sample PDFs and workbooks are missing from
  the project root.
- **`Permission denied` when running a script**: use `bash instalar.sh` or run
  `chmod +x instalar.sh iniciar.sh testar.sh`.

## Contributing

Found a bug or have an idea? Open an
[issue](https://github.com/Leandro-74/AuctionReport/issues) or send a pull request.
