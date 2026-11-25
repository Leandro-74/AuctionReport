<h1 align="center">AuctionReport</h1>

<p align="center">
  Monta relatórios em Excel dos bens de leilão do município a partir de PDFs e do projeto de lei.
</p>

<p align="center">
  <a href="https://github.com/Leandro-74/AuctionReport">English</a> | <a href="README.pt-BR.md">Português</a>
</p>

## Sobre

O AuctionReport é uma ferramenta local em Python que monta os relatórios de bens de
leilão do município brasileiro. Ela lê os PDFs exportados pelo sistema BIRT
(Prefeitura, Saúde e, se houver, Educação), lê o projeto de lei que define os lotes e
cria uma planilha de entrada editável. Depois da conferência, gera o Excel final com a
aparência do modelo oficial.

A ferramenta funciona como interface TUI no terminal ou como programa de linha de
comando. Todo o processamento acontece no computador local.

## Funcionalidades

- Lê os PDFs do tipo **Termo de Responsabilidade** da Prefeitura, da Saúde e, se
  houver, da Educação.
- Lê o **Projeto de Lei** e identifica os lotes, os patrimônios citados e os valores
  avaliados.
- Cria uma planilha de entrada editável com todos os bens e uma sugestão de lote.
- Permite editar os dados pela própria TUI:
  - mover bens por **código, faixa de códigos ou texto da descrição** para outro lote;
  - alterar o valor, o grupo e a seção de um lote;
  - alterar descrição, contas, código e lote de um bem;
  - substituir um trecho da descrição em vários bens;
  - adicionar/remover lotes e bens;
  - editar grupos, contas bancárias, agência e CNPJ.
- Rateia o valor de cada lote entre os bens, com no máximo **duas casas decimais**.
- Coloca a diferença no **último bem** do lote, de forma que a soma feche exatamente.
- Gera o relatório final com a **aparência do modelo** da prefeitura:
  - abas principais por secretaria/grupo;
  - abas auxiliares por categoria (`Todos os Veículos`, `Veículos`,
    `Veículos Hospital`, `Mobiliário em Geral`, `Mobiliário em Geral H`,
    `Itens de Informática`);
  - abas de contas para depósito (`Conta Município`,
    `Conta Fundo Municipal de Saude`).
- Opcionalmente gera uma aba extra `Resumo` para conferência lote a lote.

## Requisitos

- Python 3.10 ou superior.
- Windows ou Linux.
- O `tkinter` é opcional. Ele ativa o seletor gráfico de arquivos. Sem ele, a TUI
  pede o caminho dos arquivos.

### Nota para Linux

O seletor gráfico de arquivos precisa do pacote `tk`:

- Arch Linux: `sudo pacman -S tk`
- Debian/Ubuntu: `sudo apt install python3-tk`

No Arch Linux, o `pip install` é bloqueado fora de um ambiente virtual. O script
`instalar.sh` cria a pasta `.venv` e instala as dependências nela.

## Instalação

### Windows

Dê dois cliques em `instalar.bat` ou execute:

```powershell
python -m pip install -r requirements.txt
```

### Linux

```bash
git clone https://github.com/Leandro-74/AuctionReport.git
cd AuctionReport
./instalar.sh
```

Se o script não estiver executável, use `bash instalar.sh` ou execute antes
`chmod +x instalar.sh iniciar.sh testar.sh`.

## Uso

### Windows

Dê dois cliques em `iniciar.bat` ou execute:

```powershell
python -m leilao
```

### Linux

```bash
./iniciar.sh
```

Ou use o ambiente virtual diretamente:

```bash
.venv/bin/python -m leilao
```

A TUI abre com o menu principal:

1. **Novo leilão** — abre o seletor gráfico de arquivos e cria a planilha de entrada.
2. **Abrir/editar** — carrega uma planilha de entrada e abre o menu de edição.
3. **Gerar relatório** — valida e gera o Excel no formato do modelo.
4. **Conferir** — mostra os totais e os avisos sem gerar arquivo.
5. **Grupos e contas** — edita os dados bancários e as abas.
6. **Modelo vazio** — cria uma planilha de entrada em branco.

Depois de importar, o programa já abre o painel de edição, mostrando:

- totais por grupo;
- lote a lote: valor, soma dos bens e status;
- avisos e erros.

Se o seletor gráfico não estiver disponível, a TUI pede o caminho diretamente. Pressione
Enter para pular um arquivo opcional.

## Edição por código

No menu **Abrir/editar**, as opções principais são:

### Mover bens

Exemplos de seleção:

| Seleção | O que move |
|---|---|
| `300-400` | Todos os códigos de 300 a 400 |
| `300,305,310` | Somente esses três códigos |
| `300..400` | O mesmo que `300-400` |
| texto `MESA` | Bens cuja descrição contém `MESA` |
| lote `08` + faixa `300-400` | Somente os códigos 300–400 que estão no lote 08 |

Antes de aplicar, a TUI mostra uma prévia com a quantidade e os bens encontrados e
pede confirmação. Se nenhum filtro for informado, a movimentação é bloqueada para
não mover tudo por acidente.

### Editar lote

Permite alterar o valor da venda, o grupo (aba) e a seção (título) do lote.

### Editar bem

Permite alterar descrição, código, lote, tipo, categoria, Conta Crédito, Conta Débito,
valor contábil e observação. Enter mantém o valor atual.

### Substituir texto

Troca um trecho da descrição em vários bens, opcionalmente filtrado por lote ou
categoria. Também mostra uma prévia antes de aplicar.

### Adicionar/remover

Permite criar lotes e bens, remover lotes vazios e excluir bens por código, faixa,
texto, lote ou categoria.

As alterações são salvas automaticamente na planilha de entrada. A versão anterior é
preservada como `leilao_entrada.backup.xlsx`.

> A edição é feita na **planilha de entrada**, que é a fonte dos dados. Depois de
> editar, use **Gerar relatório** para atualizar o Excel final. Edições feitas
> manualmente no relatório final não voltam para a planilha de entrada.

## Como o valor é dividido

O valor total do lote é dividido pelo número de bens. As parcelas ficam com duas casas
decimais e o que sobra vai para o último bem.

Exemplo real da planilha de 2025: o lote 14 tinha **211 bens** e foi vendido por
**R$ 50,00**.

- 210 bens × R$ 0,23 = R$ 48,30
- último bem = R$ 50,00 − R$ 48,30 = **R$ 1,70**
- soma = **R$ 50,00**

O quociente é truncado para baixo (`0,2369...` vira `0,23`), nunca arredondado para
cima, para a última parcela nunca ficar negativa. O programa confere a soma de cada
lote antes de gerar o arquivo.

## Relatório gerado

O padrão é gerar somente as abas do modelo. A aba `Resumo` é opcional e pode ser
incluída na hora de gerar.

Aparência reproduzida do modelo:

- abas principais com 6 colunas, título, dados da conta, total dos lotes e seções por
  lote;
- abas auxiliares: `Todos os Veículos` com 6 colunas (inclui Conta Crédito), as demais
  com 5 colunas (`Tipo de bem`, `Código`, `Conta Débito`, `Descrição`, `Valor`);
- abas de conta com 4 colunas e os blocos de agência, conta corrente, CNPJ e total;
- fontes Calibri/Arial, fundo cinza `D9D9D9`, bordas finas, formato `R$ #,##0.00`,
  larguras de coluna e margens iguais às do modelo.

As abas auxiliares são criadas automaticamente conforme os dados:

- `Relatório Todos os Veículos` — todos os veículos;
- `Relatório Veículos` — veículos da Prefeitura/Educação (quando há também veículos da
  Saúde);
- `Relatório Veículos Hospital` — veículos da Saúde (quando há também veículos
  municipais);
- `Relatório Mobiliário em Geral` — móveis municipais;
- `Relatório Mobiliário em Geral H` — bens hospitalares da Saúde;
- `Relatório Itens de Informática` — informática municipal;
- `Relatório Outros Bens` — outras categorias municipais, se houver.

> O modelo original tinha pequenas diferenças de preenchimento entre as abas
> auxiliares (algumas com fundo cinza mais escuro e linhas zebradas). A ferramenta
> uniformiza essas abas no mesmo padrão das abas principais, mantendo títulos,
> colunas, fontes, bordas, larguras e margens do modelo.

## Linha de comando

A TUI é o fluxo recomendado, mas os comandos continuam disponíveis para automação.

No Windows:

```powershell
python -m leilao importar --prefeitura "Report_prefeitura.pdf" --saude "Report_saúde.pdf" --pl "Projeto de Lei.pdf" -o leilao_entrada.xlsx

python -m leilao conferir leilao_entrada.xlsx

python -m leilao gerar leilao_entrada.xlsx -o relatorio_leilao.xlsx

python -m leilao gerar leilao_entrada.xlsx -o relatorio_leilao.xlsx --com-resumo

python -m leilao modelo -o modelo_leilao.xlsx
```

No Linux, use `./iniciar.sh` antes dos mesmos argumentos, ou o ambiente virtual:

```bash
./iniciar.sh importar --prefeitura "Report_prefeitura.pdf" --pl "Projeto de Lei.pdf" -o leilao_entrada.xlsx
.venv/bin/python -m leilao conferir leilao_entrada.xlsx
.venv/bin/python -m leilao gerar leilao_entrada.xlsx -o relatorio_leilao.xlsx
```

## A planilha de entrada

### Aba Bens

| Coluna | Para que serve |
|---|---|
| Lote | Lote em que o bem entra. **Vazio = bem ignorado.** |
| Tipo de bem | Normalmente `Bens Móveis`. |
| Código | Patrimônio do bem. |
| Conta Crédito / Conta Débito | Contas contábeis. Podem ficar vazias. |
| Descrição | Descrição que sai no relatório. |
| Valor Contábil | Valor do sistema, usado só como referência. |
| Origem | Prefeitura, Saúde ou Educação. |
| Categoria | Veículos, Mobiliário, Informática, Hospitalar ou Outros. |
| Observação | Texto livre. |

### Aba Lotes

| Coluna | Para que serve |
|---|---|
| Lote | Número do lote, com dois dígitos (`01`, `02`...). |
| Valor da venda | Valor arrematado do lote. É esse valor que será rateado. |
| Grupo | Nome do grupo da aba Grupos. Decide em qual aba o lote aparece. |
| Seção | Título da seção. Lotes com a mesma seção e o mesmo grupo ficam juntos. |
| Valor avaliado (PL) | Referência do projeto de lei. |
| Descrição do PL | Texto do projeto de lei, só para consulta. |

### Aba Grupos

Nome da aba, título, subtítulo, conta de depósito, agência, conta corrente e CNPJ.
Para criar uma aba nova, acrescente uma linha e use esse nome na coluna **Grupo** dos
lotes.

### Aba Avisos

Registra os avisos da importação (bem sem lote, lote sem bens no relatório etc.).

## Observações e limites

- Os PDFs precisam ser os relatórios em tabela gerados pelo sistema (BIRT), com as
  colunas `Tipo do Bem`, `Código`, `Descrição` e `Valor Contábil`.
- As contas contábeis não vêm nos PDFs. O programa deixa as colunas vazias; preencha
  na aba Bens ou pela TUI se o relatório precisar delas.
- A sugestão automática de lotes é um ponto de partida. Confira sempre a aba Bens,
  principalmente os bens da Saúde e os lotes genéricos.
- Se um lote do projeto de lei não tiver nenhum bem nos relatórios, o programa cria
  uma linha a partir da descrição do PL e avisa. Confira descrição, código, contas e
  valor contábil dessa linha.
- Cada lote pertence a **um único grupo/aba**. Se um mesmo lote tiver bens de grupos
  diferentes, separe-o em dois lotes (por exemplo, `08` e `08-A`).
- Os números de lote devem ser únicos, mesmo entre grupos diferentes.
- Bens sem lote não entram no relatório e aparecem no aviso e na aba Avisos.

## Testes

No Windows:

```powershell
python -m unittest discover -s tests -v
```

No Linux:

```bash
./testar.sh
```

Ou diretamente:

```bash
.venv/bin/python -m unittest discover -s tests -v
```

Os testes incluem:

- reprodução do lote 14 real (211 bens, R$ 50,00);
- leitura dos PDFs de exemplo;
- comparação de fontes, preenchimentos, bordas, larguras e margens com o modelo;
- movimentação de bens por faixa de código;
- edição de lotes, descrições, contas, adição e remoção;
- conferência de que todas as somas fecham.

> Os PDFs e as planilhas do município **não são versionados** no repositório.
> Para rodar os testes de integração, coloque os arquivos de exemplo na raiz do
> projeto. Sem eles, esses testes são ignorados automaticamente.

## Estrutura do projeto

```
AuctionReport/
  leilao/
    money.py       dinheiro, formatação brasileira e rateio
    models.py      modelos de bem, lote, grupo e resultado
    pdfs.py        leitura dos relatórios e do projeto de lei
    entrada.py     criação e leitura da planilha de entrada
    edicao.py      movimentação e edição de bens/lotes/grupos
    relatorio.py   geração do Excel no formato do modelo
    tui.py         interface TUI e seleção nativa de arquivos
    cli.py         linha de comando
  tests/
    test_money.py
    test_pdfs.py
    test_edicao.py
    test_template.py
    test_integracao.py
  instalar.bat / iniciar.bat   instalação e execução no Windows
  instalar.sh / iniciar.sh     instalação e execução no Linux
  testar.sh                    execução dos testes no Linux
  README.md
  README.pt-BR.md
```

## Solução de problemas

- **`ModuleNotFoundError`**: rode a instalação novamente: `./instalar.sh` no Linux ou
  `instalar.bat` no Windows.
- **Nenhuma janela de arquivos no Linux**: instale o Tk (`sudo pacman -S tk` no Arch) e
  abra o programa de novo. Sem o Tk, digite os caminhos no prompt.
- **Não consigo salvar a planilha**: feche o arquivo no Excel ou no LibreOffice e tente
  novamente.
- **Os testes de integração são ignorados**: faltam os PDFs e as planilhas de exemplo
  na raiz do projeto.
- **`Permission denied` ao rodar um script**: use `bash instalar.sh` ou execute
  `chmod +x instalar.sh iniciar.sh testar.sh`.

## Contribuição

Encontrou um problema ou tem uma ideia? Abra uma
[issue](https://github.com/Leandro-74/AuctionReport/issues) ou envie um pull request.
