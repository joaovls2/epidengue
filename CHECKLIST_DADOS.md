# Base de dados utilizada

O arquivo `SINAN_-_Dengue.csv` já foi obtido e conferido. Não é necessário fazer outro download para esta versão do projeto.

## Conferência realizada

- 345.125 registros e 202 colunas no CSV original.
- Todos os registros têm `SIGLAUFRES = PE`.
- Todos os códigos `ID_MN_RESI` começam por `26`, confirmando o recorte de municípios de Pernambuco.
- `NU_ANO`/ano de notificação cobre 2015 a 2025.
- `NATUREZA_DADO` está como `FINAL` em todos os registros.
- A série temporal usa `DT_SIN_PRI` (início dos sintomas); três registros sem essa data usam `DT_NOTIFIC` como alternativa.
- Vinte registros têm início dos sintomas em 2014 e são removidos do recorte 2015–2025.
- Duas linhas com `TP_NOT` diferente de 2 ou sem tipo informado são removidas para manter notificações individuais.
- Não há registros marcados como duplicidade (`NDUPLIC_N = 2`) nesta extração.

## Observação de qualidade

`SG_UF` tem 19 valores ausentes ou diferentes do código 26, mas `SIGLAUFRES` indica PE em todos os registros e `ID_MN_RESI` começa por 26 em todos. Por isso, o código usa `SIGLAUFRES` como campo principal para o recorte geográfico nesta extração.

## Rodar o projeto

1. Copie o CSV para a pasta `data/` com o nome `SINAN_-_Dengue.csv`; ou
2. Envie o arquivo pela barra lateral do painel Streamlit.

O pipeline carrega somente as colunas usadas na análise para reduzir o consumo de memória.
