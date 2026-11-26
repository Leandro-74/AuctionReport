<p align="center"><img src="assets/logo.svg?v=2" alt="Logo do AuctionReport" width="120"></p>

<h1 align="center">AuctionReport</h1>

<p align="center">
  Monta relatórios em Excel dos bens de leilão do município a partir de PDFs e do projeto de lei.
</p>

<p align="center">
  <a href="https://github.com/Leandro-74/AuctionReport">English</a> | <a href="README.pt-BR.md">Português</a>
</p>

## Sobre

O AuctionReport é uma ferramenta local em Python que monta os relatórios de bens de
leilão de um município brasileiro. Ela lê os PDFs exportados pelo sistema BIRT
(Prefeitura e Saúde), lê o projeto de lei que define os lotes e guarda o leilão em um
banco SQLite.

Cada leilão fica em uma pasta própria, com os PDFs de origem e os arquivos gerados.
Os dados são editados em uma interface TUI no terminal. O XLSX final é gerado quando
necessário. Abra-o para revisar e exporte para PDF manualmente se precisar.

## Funcionalidades

- Lê os PDFs atuais de **Consulta de Bem** da Prefeitura e da Saúde, incluindo as
  contas de débito e crédito.
- Lê o **Projeto de Lei** e identifica os lotes, os patrimônios citados e os valores
  avaliados.
- Cria uma **pasta e um banco SQLite** para cada leilão.
- Copia os PDFs de origem para a pasta do leilão.
- Compara PDFs novos com um leilão existente e mostra bens novos, alterados e
  ausentes antes de aplicar.
- Permite editar os dados pela TUI:
  - mover bens por **código, faixa de códigos, texto da descrição, origem ou
    categoria** para outro lote;
  - alterar o valor, o grupo, a seção e a conta de depósito de um lote;
  - alterar descrição, contas, código, origem e lote de um bem;
  - substituir um trecho da descrição em vários bens;
  - adicionar/remover lotes e bens;
  - editar grupos, dados bancários padrão e contas compartilhadas;
  - editar a configuração padrão do usuário pela TUI.
- Permite informar o valor de venda de cada lote na criação ou depois; o valor do
  projeto de lei fica como lance inicial de referência.
- Rateia o valor de cada lote entre os bens, com no máximo **duas casas decimais**.
- Coloca a diferença no **último bem** do lote, de forma que a soma feche exatamente.
- Exporta o relatório final em **XLSX**.
- Migra uma planilha de entrada antiga (`.xlsx`) para o novo formato de banco.
- Opcionalmente gera uma aba extra `Resumo` para conferência lote a lote.

## Requisitos

- Python 3.10 ou superior.
- Windows ou Linux.

### Nota para Linux

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

### Executável para Windows

Um executável independente para Windows está disponível na página de
[Releases](https://github.com/Leandro-74/AuctionReport/releases):

1. Baixe `AuctionReport.exe`.
2. Execute.

Na primeira execução, o programa pede os dados do município e os salva automaticamente.
Não é necessário ter Python no computador de destino.

O `AuctionReport-windows.zip` opcional contém o executável, os READMEs e um
`config.example.json` fictício.

O Windows pode mostrar um aviso do SmartScreen por ser um executável sem assinatura;
escolha **Mais informações → Executar assim mesmo** se confiar no download.

Para gerar o executável na sua própria máquina Windows, execute `build_windows.bat`.

## Configuração

Não é necessário criar arquivo de configuração manualmente. Na primeira execução, a TUI
pede os dados do município e os salva no perfil do usuário:

- Windows: `%APPDATA%\AuctionReport\config.json`
- Linux: `~/.config/AuctionReport/config.json`

A opção **Configuração padrão** do menu principal edita o mesmo arquivo depois. O
formato é JSON, e `config.example.json` mostra o modelo fictício.

Se existir um `.env` antigo ao lado do executável ou do projeto, ele é importado
automaticamente na primeira vez.

Os campos são:

| Campo | Para que serve |
|---|---|
| `municipio` | Nome do município usado nos títulos dos relatórios |
| `titulo_saude` | Título do fundo de saúde |
| `subtitulo_prefeitura` | Subtítulo da Prefeitura |
| `subtitulo_saude` | Subtítulo da Saúde |
| `agencia` | Agência bancária padrão |
| `cnpj_municipio` | CNPJ do município |
| `cnpj_saude` | CNPJ do fundo de saúde |
| `conta_prefeitura` | Conta corrente da Prefeitura |
| `conta_saude` | Conta corrente da Saúde |

Esses valores são apenas padrões. Cada leilão guarda os próprios grupos e contas de
depósito no `leilao.db`, então eles podem variar por lote, leilão ou secretaria.

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

1. **Novo leilão** — lê os PDFs e cria a pasta e o banco do leilão.
2. **Abrir leilão** — abre um `leilao.db` existente.
3. **Editar leilão** — edita bens, lotes, valores e descrições.
4. **Atualizar com PDFs** — compara PDFs novos com o leilão atual.
5. **Exportar** — gera o relatório em XLSX.
6. **Conferir** — mostra os totais e os avisos sem gerar arquivos.
7. **Grupos e contas** — edita grupos e contas de depósito compartilhadas.
8. **Migrar planilha antiga** — converte uma planilha de entrada antiga em banco.
9. **Novo leilão vazio** — cria um leilão em branco com os grupos padrão.
10. **Configuração padrão** — edita a configuração do usuário.

Depois de abrir um leilão, o painel de edição mostra:

- totais por grupo;
- lote a lote: valor, soma dos bens e status;
- avisos e erros.

Quando a TUI pedir um arquivo ou uma pasta, arraste para o terminal ou digite/cole o
caminho. Aspas e espaços escapados são tratados automaticamente. Pressione Enter em um
arquivo opcional para pular.

## Pasta do leilão

Cada leilão é uma pasta:

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

- `leilao.db` é a fonte da verdade.
- `documentos/` guarda os PDFs de origem.
- `exportacoes/` recebe os arquivos XLSX gerados.

Para fazer backup de um leilão, copie a pasta inteira. Para arquivar, mova a pasta.
Não é preciso servidor: o SQLite é um único arquivo e já vem com o Python.

## Contas de depósito

Cada leilão tem as suas próprias contas de depósito:

- Cada grupo tem uma **conta padrão**, editada em **Grupos e contas → Editar grupo**.
- Um lote pode usar a conta padrão do grupo ou uma **conta específica**.
- Vários lotes podem compartilhar a mesma conta.
- **Grupos e contas → Contas de depósito** cria, edita e remove contas
  compartilhadas.
- Ao editar um lote, digite `padrao` para voltar à conta do grupo.
- Um lote sem conta específica usa os dados bancários do próprio grupo.

No relatório, os lotes que usam a mesma conta são agrupados em uma única aba de conta
com o valor total. Lotes que usam a conta padrão são agrupados por grupo.

## Atualizar um leilão

Quando chegam PDFs novos:

1. Abra o leilão.
2. Escolha **Atualizar com PDFs**.
3. Selecione os relatórios atualizados e, se houver, o projeto de lei atualizado.
4. Confira o resumo:
   - bens novos;
   - bens alterados e seus campos;
   - bens que não aparecem mais nos PDFs;
   - lotes novos do projeto de lei;
   - avisos.
5. Confirme para aplicar a atualização.

A atualização é conservadora:

- lotes, contas e observações existentes são preservados;
- tipo, descrição e valor contábil são atualizados a partir do PDF;
- bens novos usam o projeto de lei para sugerir o lote;
- lotes novos começam sem valor de venda; use **Registrar venda** se a venda ainda
  não estiver registrada, ou **Editar lote** depois de registrada;
- códigos ambíguos não são associados automaticamente;
- bens que sumiram dos PDFs são mantidos e aparecem como aviso.

Os PDFs de origem são copiados para `documentos/` depois de uma atualização bem-sucedida.

## Edição por código

No menu **Editar leilão**, as opções principais são:

### Mover bens

Exemplos de seleção:

| Seleção | O que move |
|---|---|
| `300-400` | Todos os códigos de 300 a 400 |
| `300,305,310` | Somente esses três códigos |
| `300..400` | O mesmo que `300-400` |
| texto `MESA` | Bens cuja descrição contém `MESA` |
| lote `08` + faixa `300-400` | Somente os códigos 300–400 que estão no lote 08 |
| origem `Saúde` | Somente os bens da Saúde |

Antes de aplicar, a TUI mostra uma prévia com a quantidade e os bens encontrados e
pede confirmação. Se nenhum filtro for informado, a movimentação é bloqueada para
não mover tudo por acidente.

### Mesmo código em origens diferentes

Cada código de patrimônio identifica um bem dentro da sua origem. O mesmo código pode
existir na Prefeitura e na Saúde, por exemplo o código `3500`. Quando um código aparece
em mais de uma origem, a TUI pede a origem ao editar e oferece um filtro de origem ao
mover ou remover bens.

### Editar lote

Permite alterar o valor da venda, o grupo (aba), a seção (título) e a conta de depósito
do lote.

### Editar bem

Permite alterar descrição, código, origem, lote, tipo, categoria, Conta Crédito, Conta
Débito, valor contábil e observação. Enter mantém o valor atual.

### Substituir texto

Troca um trecho da descrição em vários bens, opcionalmente filtrado por lote, categoria
ou origem. Também mostra uma prévia antes de aplicar.

### Adicionar/remover

Permite criar lotes e bens, remover lotes vazios e excluir bens por código, faixa,
texto, lote, categoria ou origem.

As alterações são salvas automaticamente no banco SQLite.

## Valor de venda e lance inicial

O valor do projeto de lei é o **lance inicial**, não o valor final de venda.

- Ao criar um leilão, a TUI pergunta se ele já foi realizado. Se já foi, você informa o
  valor de venda de cada lote na hora.
- Se ainda não foi realizado, o leilão é criado como **não vendido**. A coluna de valor
  mostra o lance inicial e o status é `NÃO VENDIDO`. Isso não é um erro.
- Enquanto a venda não estiver registrada, **Editar leilão** mostra a opção
  **Registrar venda**. Ela pede o valor de venda de todos os lotes e depois desaparece.
- Se o leilão for criado depois de realizado, a opção não aparece, pois a venda já está
  registrada.
- Depois de registrar a venda, os valores ainda podem ser ajustados em **Editar lote**.

O lance inicial fica no campo `Valor avaliado (PL)` como referência. A exportação do
XLSX fica bloqueada enquanto a venda não for registrada.

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

O XLSX serve para revisão. Para imprimir ou compartilhar um PDF, abra o XLSX no Excel
ou no LibreOffice e exporte manualmente.

Aparência reproduzida do modelo:

- abas principais com 6 colunas, título, dados da conta, total dos lotes e seções por
  lote;
- abas auxiliares: `Todos os Veículos` com 6 colunas (inclui Conta Crédito), as demais
  com 5 colunas (`Tipo de bem`, `Código`, `Conta Débito`, `Descrição`, `Valor`);
- abas de conta com 4 colunas e os blocos de agência, conta corrente, CNPJ e total;
- uma aba por conta usada; lotes que compartilham a mesma conta dividem a aba e o
  total;
- fontes Calibri/Arial, cabeçalhos cinza `D9D9D9`, linhas alternadas em branco e
  `F2F2F2`, bordas finas `999999`, formato `R$ #,##0.00`, larguras de coluna e
  margens iguais às do modelo.

As abas auxiliares são criadas automaticamente conforme os dados:

- `Relatório Todos os Veículos` — todos os veículos;
- `Relatório Veículos` — veículos municipais (quando há também veículos da Saúde);
- `Relatório Veículos Hospital` — veículos da Saúde (quando há também veículos
  municipais);
- `Relatório Mobiliário em Geral` — móveis municipais;
- `Relatório Mobiliário em Geral H` — bens hospitalares da Saúde;
- `Relatório Itens de Informática` — informática municipal;
- `Relatório Outros Bens` — outras categorias municipais, se houver.

A aba `Resumo` é opcional e pode ser incluída na exportação.

## Linha de comando

A TUI é o fluxo recomendado, mas os comandos continuam disponíveis para automação.

No Windows:

```powershell
python -m leilao novo --prefeitura "Report_prefeitura.pdf" --saude "Report_saúde.pdf" --pl "Projeto de Lei.pdf" --pasta leiloes/2026-2

python -m leilao conferir leiloes/2026-2/leilao.db

python -m leilao exportar leiloes/2026-2/leilao.db

python -m leilao exportar leiloes/2026-2/leilao.db --com-resumo

python -m leilao atualizar leiloes/2026-2/leilao.db --prefeitura "Report_prefeitura_novo.pdf"

python -m leilao atualizar leiloes/2026-2/leilao.db --prefeitura "Report_prefeitura_novo.pdf" --aplicar

python -m leilao migrar leilao_entrada.xlsx --pasta leiloes/2025-2
```

Sem `--aplicar`, o comando `atualizar` apenas mostra o resumo e os avisos.

No Linux, use `./iniciar.sh` antes dos mesmos argumentos, ou o ambiente virtual:

```bash
./iniciar.sh novo --prefeitura "Report_prefeitura.pdf" --pl "Projeto de Lei.pdf" --pasta leiloes/2026-2
.venv/bin/python -m leilao conferir leiloes/2026-2/leilao.db
.venv/bin/python -m leilao exportar leiloes/2026-2/leilao.db
```

Os comandos antigos de XLSX continuam disponíveis para arquivos legados:

- `importar` cria uma planilha de entrada no formato antigo.
- `gerar` cria um relatório XLSX a partir de uma planilha de entrada antiga.
- `modelo` cria uma planilha de entrada vazia no formato antigo.

## Banco de dados

O banco SQLite guarda grupos, contas de depósito, lotes e bens. Os bens são ligados aos
lotes por IDs internos; o código do patrimônio é a chave de negócio usada na busca e na
reconciliação.

Regras conferidas pelo banco e pela validação:

- os números de lote são únicos dentro do leilão;
- os nomes de grupo são únicos dentro do leilão;
- os nomes de conta são únicos dentro do leilão;
- os códigos de bem são únicos dentro de cada origem;
- o mesmo código pode existir na Prefeitura e na Saúde;
- todo lote precisa apontar para um grupo existente;
- um lote pode apontar para uma conta, e a mesma conta pode ser usada por vários lotes;
- todo bem precisa apontar para um lote existente ou ficar sem lote.

O rateio é calculado na geração do relatório. Ele não é gravado no banco.

Bancos criados antes do suporte a contas de depósito são migrados automaticamente. Os
lotes existentes continuam usando a conta padrão do grupo até que uma conta específica
seja escolhida.

## Planilha de entrada antiga

Uma `leilao_entrada.xlsx` antiga pode ser migrada com **Migrar planilha antiga** ou
com o comando `migrar`. Depois da migração, edite os dados pela TUI e exporte o novo
relatório.

A planilha antiga tem estas abas:

### Aba Bens

| Coluna | Para que serve |
|---|---|
| Lote | Lote em que o bem entra. Vazio = bem ignorado. |
| Tipo de bem | Normalmente `Bens Móveis`. |
| Código | Patrimônio do bem. |
| Conta Crédito / Conta Débito | Contas contábeis. Podem ficar vazias. |
| Descrição | Descrição que sai no relatório. |
| Valor Contábil | Valor do sistema, usado só como referência. |
| Origem | Prefeitura ou Saúde. |
| Categoria | Veículos, Mobiliário, Informática, Hospitalar ou Outros. |
| Observação | Texto livre. |

### Aba Lotes

| Coluna | Para que serve |
|---|---|
| Lote | Número do lote, com dois dígitos (`01`, `02`...). |
| Valor da venda | Valor arrematado do lote. É esse valor que será rateado. Pode ficar vazio até o leilão acontecer. |
| Grupo | Nome do grupo da aba Grupos. |
| Seção | Título da seção. |
| Valor avaliado (PL) | Lance inicial de referência do projeto de lei. |
| Descrição do PL | Texto do projeto de lei, só para consulta. |

### Aba Grupos

Nome da aba, título, subtítulo, conta de depósito, agência, conta corrente e CNPJ.

## Observações e limites

- Os PDFs precisam ser os relatórios atuais de **Consulta de Bem** gerados pelo sistema
  (BIRT), com as colunas `Tipo`, `Código`, `Complemento`, `Conta Débito` e
  `Conta Crédito`.
- Os novos relatórios incluem as contas de débito e crédito. Eles não incluem o valor
  contábil, então `Valor Contábil` fica vazio até ser preenchido pela TUI.
- A sugestão automática de lotes é um ponto de partida. Confira sempre os bens,
  principalmente os bens da Saúde e os lotes genéricos.
- Se um lote do projeto de lei não tiver nenhum bem nos relatórios, o programa cria
  uma linha a partir da descrição do PL e avisa. Confira descrição, código, contas e
  valor contábil dessa linha.
- Se um código do projeto de lei corresponder a mais de um bem (por exemplo, o mesmo
  código na Prefeitura e na Saúde), a associação automática é ignorada e um aviso pede
  para atribuir o lote manualmente.
- Cada lote pertence a **um único grupo/aba**. Se um mesmo lote tiver bens de grupos
  diferentes, separe-o em dois lotes (por exemplo, `08` e `08-A`).
- Os números de lote devem ser únicos, mesmo entre grupos diferentes.
- Bens sem lote não entram no relatório e aparecem nos avisos.

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

Os testes usam os valores fictícios padrão; não é necessário ter configuração do usuário.

Os testes incluem:

- reprodução do lote 14 real (211 bens, R$ 50,00);
- leitura dos PDFs de exemplo;
- comparação de fontes, preenchimentos, bordas, larguras e margens com o modelo;
- movimentação de bens por faixa de código e filtro por origem;
- persistência em SQLite, atualizações, remoções e migração de planilha antiga;
- contas de depósito compartilhadas por vários lotes;
- leitura e gravação da configuração JSON;
- reconciliação de PDFs novos com um leilão existente;
- fluxo de exportação XLSX;
- conferência de que todas as somas fecham.

> Os PDFs e as planilhas do município **não são versionados** no repositório.
> Para rodar os testes de integração, coloque os novos relatórios em `novo_modelo/` e
> o projeto de lei na raiz do projeto. Sem eles, esses testes são ignorados
> automaticamente.

## Estrutura do projeto

```
AuctionReport/
  leilao/
    money.py        dinheiro, formatação brasileira e rateio
    models.py       modelos de bem, lote, grupo e resultado
    config.py       dados padrão do município carregados do perfil do usuário
    config_store.py configuração JSON, caminhos e importação do .env antigo
    pdfs.py         leitura dos relatórios e do projeto de lei
    banco.py        persistência SQLite, pastas de leilão e migração
    atualizacao.py  reconciliação de PDFs novos com um leilão existente
    entrada.py      suporte à planilha de entrada antiga e validação
    edicao.py       movimentação e edição de bens/lotes/grupos
    relatorio.py    geração do Excel no formato do modelo
    exportacao.py   fluxo de exportação XLSX
    tui.py          interface TUI e entrada de caminhos
    cli.py          linha de comando
  tests/
    test_money.py
    test_pdfs.py
    test_edicao.py
    test_template.py
    test_banco.py
    test_contas.py
    test_atualizacao.py
    test_exportacao.py
    test_cli.py
    test_config_store.py
    test_importacao.py
    test_tui.py
    test_integracao.py
  main.py                      ponto de entrada do executável
  build_windows.bat            geração local do executável Windows
  .github/workflows/release.yml  geração da release Windows
  instalar.bat / iniciar.bat   instalação e execução no Windows
  instalar.sh / iniciar.sh     instalação e execução no Linux
  testar.sh                    execução dos testes no Linux
  assets/logo.svg              logo do projeto
  assets/logo.ico              ícone do executável Windows
  config.example.json          modelo de configuração com valores fictícios
  README.md
  README.pt-BR.md
```

## Solução de problemas

- **`ModuleNotFoundError`**: rode a instalação novamente: `./instalar.sh` no Linux ou
  `instalar.bat` no Windows.
- **Não consigo salvar o leilão**: feche outros programas que possam estar usando o
  `leilao.db` e tente novamente.
- **Os testes de integração são ignorados**: faltam os PDFs e as planilhas de exemplo
  na raiz do projeto.
- **`Permission denied` ao rodar um script**: use `bash instalar.sh` ou execute
  `chmod +x instalar.sh iniciar.sh testar.sh`.

## Contribuição

Encontrou um problema ou tem uma ideia? Abra uma
[issue](https://github.com/Leandro-74/AuctionReport/issues) ou envie um pull request.
