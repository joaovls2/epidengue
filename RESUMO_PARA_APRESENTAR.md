# Resumo do projeto para revisão

## Título
Análise e previsão de notificações prováveis de dengue em Pernambuco (2015–2025)

## Problema
As notificações de dengue variam ao longo do tempo e apresentam períodos de maior concentração. A proposta é analisar o histórico de Pernambuco, identificar padrões semanais e estimar experimentalmente o volume de notificações nas semanas posteriores ao fim da série histórica.

## Objetivo
Desenvolver um algoritmo que utilize os registros históricos do SINAN para analisar a evolução semanal das notificações prováveis de dengue em Pernambuco e produzir estimativas para as quatro semanas seguintes ao último período disponível na base.

## Base de dados
SINAN - Dengue, Ministério da Saúde/DATASUS, obtida pela Plataforma de Dados Desidentificados (PDD-Cidacs/Fiocruz). Recorte: Pernambuco, 2015 a 2025. Arquivo original: 345.125 registros e 202 colunas. A seleção territorial prioriza residência (`SIGLAUFRES = PE`; códigos `ID_MN_RESI` iniciados em 26).

## Tratamento dos dados
- Manter notificações individuais (`TP_NOT = 2`).
- Identificar registros de dengue pelo campo `ID_AGRAVO` (`A90` nesta extração).
- Considerar notificações prováveis como notificações não descartadas: excluir `CLASSI_FIN = 5` (descartado) e, quando aparecer, `13` (chikungunya). Classificações inconclusivas e ainda não preenchidas permanecem na contagem, conforme a definição operacional adotada.
- Excluir duplicidades somente quando `NDUPLIC_N = 2`; valores em branco ou 0 não são tratados como duplicidade.
- Usar `DT_SIN_PRI` (início dos sintomas); quando ausente, utilizar `DT_NOTIFIC` como alternativa.
- Agregar registros em uma série semanal contínua, preenchendo semanas sem registro com zero.

Após os filtros, foram considerados 345.103 registros, distribuídos em 575 semanas. Três registros sem data de sintomas usaram a data de notificação; vinte registros com início de sintomas em 2014 ficaram fora do período; duas linhas não individuais ou sem tipo de notificação foram excluídas.

## Técnica de Inteligência Artificial
- Família: aprendizado supervisionado.
- Tarefa: regressão.
- Algoritmo: Random Forest Regressor.
- Entradas: notificações das 1, 2, 3, 4 e 52 semanas anteriores, médias móveis e posição da semana no ano.
- Saída: estimativa numérica de notificações prováveis para a semana seguinte.

## Experimento e avaliação
Os dados foram separados cronologicamente: 418 semanas para treinamento e 105 semanas para teste. A comparação preserva a ordem do tempo e utiliza as observações reais anteriores para estimar cada semana do período de teste (avaliação móvel de uma semana à frente). O Random Forest é comparado a uma referência sazonal simples que repete o valor da mesma semana do ano anterior.

| Métrica | Random Forest | Referência sazonal |
|---|---:|---:|
| MAE | 69,7 | 272,5 |
| RMSE | 118,2 | 365,3 |
| R² | 0,806 | -0,854 |

Nesta execução, o Random Forest teve erros menores do que a referência sazonal. Isso indica melhor desempenho neste conjunto de teste, mas não significa que o modelo esteja pronto para uso epidemiológico.

## Estimativas após o fim da base

A base termina em dezembro de 2025. As quatro estimativas geradas após esse recorte foram:

| Semana com início em | Notificações estimadas |
|---|---:|
| 04/01/2026 | 104 |
| 11/01/2026 | 109 |
| 18/01/2026 | 124 |
| 25/01/2026 | 125 |

Essas datas são posteriores ao recorte histórico, mas não constituem previsão atual para novembro de 2026. São uma demonstração experimental do algoritmo a partir da série 2015–2025.

## Limitações
- O SINAN registra notificações e não apenas casos confirmados; a contagem pode incluir registros em investigação.
- Há possibilidade de subnotificação, atraso e revisão dos registros.
- Três datas de início de sintomas ausentes foram substituídas pela data de notificação.
- Foram identificadas 19 divergências/ausências em `SG_UF`; como `SIGLAUFRES` indica PE e todos os códigos municipais de residência começam por 26, o filtro utiliza `SIGLAUFRES`.
- O modelo é experimental e não substitui previsões ou alertas das autoridades de saúde.
- A primeira e a última semana epidemiológica do recorte são parciais, pois a extração vai de 01/01/2015 a 31/12/2025. Isso pode influenciar especialmente a última defasagem usada nas estimativas.

## Visualizações no painel
- Evolução semanal das notificações prováveis.
- Totais por ano e média mensal no período.
- Comparação entre valores reais e previstos no período de teste.
- Estimativas após o fim do recorte histórico.
- Importância das variáveis utilizadas pelo Random Forest.
