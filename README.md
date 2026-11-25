# AuctionReport

Ferramenta em Python para montar os relatórios de bens de leilão em Excel, com uma
interface TUI, seleção de arquivos pelo Explorer e edição dos bens por código.

Repositório: <https://github.com/Leandro-74/AuctionReport>

## O que ela faz

- Lê os PDFs do tipo **Termo de Responsabilidade** (Prefeitura, Saúde e, se houver, Educação).
- Lê o **Projeto de Lei** e identifica os lotes, os patrimônios citados e os valores avaliados.
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
  - abas auxiliares por categoria (`Todos os Veículos`, `Veículos`, `Veículos Hospital`,
    `Mobiliário em Geral`, `Mobiliário em Geral H`, `Itens de Informática`);
  - abas de contas para depósito (`Conta Município`, `Conta Fundo Municipal de Saude`).
- Opcionalmente gera uma aba extra `Resumo` para conferência lote a lote.

## Instalação

Requisitos: Python 3.10 ou superior.

No Windows, dê dois cliques em `instalar.bat`. Ou, no terminal:

```powershell
python -m pip install -r requirements.txt
```

O seletor de arquivos usa o `tkinter`, que já vem com o Python no Windows.

## Uso

Dê dois cliques em `iniciar.bat` ou execute:

```powershell
python -m leilao
```

A TUI abre com o menu principal:

1. **Novo leilão** — abre o seletor do Windows para escolher os PDFs e cria a planilha de entrada.
2. **Abrir/editar** — carrega uma planilha de entrada e abre o menu de edição.
3. **Gerar relatório** — valida e gera o Excel no formato do modelo.
4. **Conferir** — mostra os totais e os avisos sem gerar arquivo.
5. **Grupos e contas** — edita os dados bancários e as abas.
6. **Modelo vazio** — cria uma planilha de entrada em branco.

Depois de importar, o programa já abre o painel de edição, mostrando:
- totais por grupo;
- lote a lote: valor, soma dos bens e status;
- avisos e erros.

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

As alterações são salvas automaticamente na planilha de entrada. A versão anterior
é preservada como `leilao_entrada.backup.xlsx`.

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

- abas principais com 6 colunas, título, dados da conta, total dos lotes e seções por lote;
- abas auxiliares: `Todos os Veículos` com 6 colunas (inclui Conta Crédito), as demais
  com 5 colunas (`Tipo de bem`, `Código`, `Conta Débito`, `Descrição`, `Valor`);
- abas de conta com 4 colunas e os blocos de agência, conta corrente, CNPJ e total;
- fontes Calibri/Arial, fundo cinza `D9D9D9`, bordas finas, formato `R$ #,##0.00`,
  larguras de coluna e margens iguais às do modelo.

As abas auxiliares são criadas automaticamente conforme os dados:

- `Relatório Todos os Veículos` — todos os veículos;
- `Relatório Veículos` — veículos da Prefeitura/Educação (quando há também veículos da Saúde);
- `Relatório Veículos Hospital` — veículos da Saúde (quando há também veículos municipais);
- `Relatório Mobiliário em Geral` — móveis municipais;
- `Relatório Mobiliário em Geral H` — bens hospitalares da Saúde;
- `Relatório Itens de Informática` — informática municipal;
- `Relatório Outros Bens` — outras categorias municipais, se houver.

> O modelo original tinha pequenas diferenças de preenchimento entre as abas
> auxiliares (algumas com fundo cinza mais escuro e linhas zebradas). A ferramenta
> uniformiza essas abas no mesmo padrão das abas principais, mantendo títulos,
> colunas, fontes, bordas, larguras e margens do modelo.

## Linha de comando

A TUI é o fluxo recomendado, mas os comandos continuam disponíveis para automação:

```powershell
python -m leilao importar --prefeitura "Report_prefeitura.pdf" --saude "Report_saúde.pdf" --pl "Projeto de Lei.pdf" -o leilao_entrada.xlsx

python -m leilao conferir leilao_entrada.xlsx

python -m leilao gerar leilao_entrada.xlsx -o relatorio_leilao.xlsx

python -m leilao gerar leilao_entrada.xlsx -o relatorio_leilao.xlsx --com-resumo

python -m leilao modelo -o modelo_leilao.xlsx
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
Para criar uma aba nova, acrescente uma linha e use esse nome na coluna **Grupo** dos lotes.

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

```powershell
python -m unittest discover -s tests -v
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
leilao/
  money.py      dinheiro, formatação brasileira e rateio
  models.py     modelos de bem, lote, grupo e resultado
  pdfs.py       leitura dos relatórios e do projeto de lei
  entrada.py    criação e leitura da planilha de entrada
  edicao.py     movimentação e edição de bens/lotes/grupos
  relatorio.py  geração do Excel no formato do modelo
  tui.py        interface TUI e seleção nativa de arquivos
  cli.py        linha de comando
tests/
  test_money.py
  test_pdfs.py
  test_edicao.py
  test_template.py
  test_integracao.py
```
