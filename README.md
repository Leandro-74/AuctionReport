# Leilão Auto

Ferramenta em Python para montar os relatórios de bens de leilão em Excel.

Ela lê os relatórios do sistema em PDF, lê o projeto de lei com a divisão dos lotes,
cria uma planilha de entrada editável e gera o relatório final com o valor de cada
lote rateado entre os bens.

## O que ela faz

- Lê os PDFs do tipo **Termo de Responsabilidade** (relatórios da Prefeitura, da Saúde e, se houver, da Educação).
- Lê o **Projeto de Lei** e identifica os lotes, os patrimônios citados e os valores avaliados.
- Cria `leilao_entrada.xlsx` com todos os bens e uma sugestão de lote para cada um.
- Rateia o valor de cada lote entre os bens, com no máximo **duas casas decimais**.
- Coloca a diferença no **último bem** do lote, de forma que a soma feche exatamente o valor do lote.
- Gera `relatorio_leilao.xlsx` no formato da planilha de exemplo, com uma aba por grupo/secretaria.
- Cria uma aba **Resumo** com os totais por grupo e a conferência de cada lote.
- Opcionalmente cria uma aba separada para cada lote com mais de um bem.

## Instalação

Requisitos: Python 3.10 ou superior e os pacotes `openpyxl` e `pdfplumber`.

No Windows, dê dois cliques em `instalar.bat`. Ou, no terminal:

```powershell
python -m pip install -r requirements.txt
```

## Uso rápido

1. Coloque os PDFs na mesma pasta do projeto.
2. Dê dois cliques em `iniciar.bat` (ou execute `python -m leilao`).
3. Escolha **1 - Importar PDFs** e informe os arquivos.
4. Abra a planilha `leilao_entrada.xlsx` e confira:
   - **Bens:** o lote de cada bem (linhas em amarelo estão sem lote e ficam de fora);
   - **Lotes:** o valor da venda de cada lote (pode começar com o valor avaliado do PL);
   - **Grupos:** os dados de conta de cada aba.
5. Volte ao menu e escolha **2 - Gerar relatório**.
6. O arquivo `relatorio_leilao.xlsx` será criado.

> A planilha `leilao_entrada.xlsx` que já está na pasta foi gerada a partir dos PDFs
> deste leilão. Ela serve como ponto de partida.
>
> Se você importar novamente, a planilha anterior é preservada como
> `leilao_entrada.backup.xlsx`.

## Linha de comando

Importar os PDFs:

```powershell
python -m leilao importar `
  --prefeitura "Report_prefeitura.pdf" `
  --saude "Report_saúde.pdf" `
  --pl "Projeto de Lei - Autoriza Alienação de Bens.pdf" `
  -o leilao_entrada.xlsx
```

Conferir sem gerar o Excel:

```powershell
python -m leilao conferir leilao_entrada.xlsx
```

Gerar o relatório:

```powershell
python -m leilao gerar leilao_entrada.xlsx -o relatorio_leilao.xlsx
```

Gerar também uma aba por lote com mais de um bem:

```powershell
python -m leilao gerar leilao_entrada.xlsx -o relatorio_leilao.xlsx --por-lote
```

Criar uma planilha de entrada vazia (modelo):

```powershell
python -m leilao modelo -o modelo_leilao.xlsx
```

Se o projeto de lei não for informado, a planilha é criada sem lotes sugeridos; nesse
caso preencha a aba **Lotes** manualmente.

## A planilha de entrada

### Aba Bens

Uma linha por bem:

| Coluna | Para que serve |
|---|---|
| Lote | Lote em que o bem entra. **Vazio = bem ignorado.** |
| Tipo de bem | Normalmente `Bens Móveis`. |
| Código | Patrimônio do bem. |
| Conta Crédito / Conta Débito | Contas contábeis. Podem ficar vazias se não forem usadas. |
| Descrição | Descrição que sai no relatório. |
| Valor Contábil | Valor do sistema, usado só como referência. |
| Origem | Prefeitura, Saúde ou Educação. |
| Categoria | Veículos, Mobiliário, Informática, Hospitalar ou Outros. |
| Observação | Texto livre. |

### Aba Lotes

Uma linha por lote:

| Coluna | Para que serve |
|---|---|
| Lote | Número do lote, com dois dígitos (`01`, `02`...). |
| Valor da venda | Valor arrematado do lote. É esse valor que será rateado. |
| Grupo | Nome do grupo da aba Grupos. Decide em qual aba o lote aparece. |
| Seção | Título da seção. Lotes com a mesma seção e o mesmo grupo ficam juntos. |
| Valor avaliado (PL) | Referência do projeto de lei. |
| Descrição do PL | Texto do projeto de lei, só para consulta. |

### Aba Grupos

Dados de cada aba do relatório: nome da aba, título, subtítulo, conta de depósito,
agência, conta corrente e CNPJ. Para criar uma aba nova, acrescente uma linha e use
esse nome na coluna **Grupo** dos lotes.

### Aba Avisos

Quando a importação gera avisos (bem sem lote, lote sem bens no relatório etc.),
eles também ficam registrados aqui.

## Como o valor é dividido

O valor total do lote é dividido pelo número de bens. As parcelas ficam com duas casas
decimais e o que sobra vai para o último bem.

Exemplo real da planilha de 2025: o lote 14 tinha **211 bens** e foi vendido por
**R$ 50,00**. O cálculo fica:

- 210 bens × R$ 0,23 = R$ 48,30
- último bem = R$ 50,00 − R$ 48,30 = **R$ 1,70**
- soma = **R$ 50,00**

O quociente é sempre truncado para baixo (`0,2369...` vira `0,23`), nunca arredondado
para cima, para a última parcela nunca ficar negativa. O programa confere a soma de
cada lote antes de gerar o arquivo.

## Conferência

A aba **Resumo** do relatório final mostra:

- totais por grupo (quantidade de bens e valor);
- lote a lote: valor do lote, soma dos bens e situação (`OK` ou `ERRO`);
- total geral.

O comando `python -m leilao conferir leilao_entrada.xlsx` faz a mesma conferência
no terminal e lista os erros e avisos.

## Observações e limites

- Os PDFs precisam ser os relatórios em tabela gerados pelo sistema (BIRT), com as
  colunas `Tipo do Bem`, `Código`, `Descrição` e `Valor Contábil`.
- As contas contábeis (Crédito/Débito) **não** vêm nos PDFs. O programa deixa as
  colunas vazias; preencha na aba Bens se o relatório precisar delas.
- A sugestão automática de lotes é um ponto de partida. Confira sempre a aba Bens,
  principalmente os bens da Saúde e os lotes genéricos (mobiliário, informática,
  hospitalar).
- Se um lote do projeto de lei não tiver nenhum bem nos relatórios, o programa cria
  uma linha a partir da descrição do PL e avisa. Confira a descrição, o código, as
  contas e o valor contábil dessa linha.
- Cada lote pertence a **um único grupo/aba**. Se um mesmo lote tiver bens de grupos
  diferentes, separe-o em dois lotes (por exemplo, `08` e `08-A`) com os valores
  correspondentes.
- Os números de lote devem ser únicos, mesmo entre grupos diferentes.
- Bens sem lote não entram no relatório e aparecem no aviso e na aba Avisos.

## Testes

```powershell
python -m unittest discover -s tests -v
```

Os testes incluem a reprodução do lote 14 real (211 bens, R$ 50,00), a leitura dos
PDFs de exemplo e a conferência de que todas as somas fecham.

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
  relatorio.py  geração do relatório final em Excel
  cli.py        menu e linha de comando
tests/
  test_money.py
  test_pdfs.py
  test_integracao.py
```
