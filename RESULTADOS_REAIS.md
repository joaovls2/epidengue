# Resultados obtidos com a base real do SINAN - Dengue

## Validação do arquivo recebido

- Arquivo: `SINAN_-_Dengue.csv` (extração da PDD-Cidacs).
- Estrutura do CSV original: 345.125 registros e 202 colunas.
- Todos os registros apresentam `SIGLAUFRES = PE`.
- Todos os códigos `ID_MN_RESI` começam com `26`, compatível com municípios de Pernambuco.
- `NATUREZA_DADO = FINAL` em todos os registros.
- `SG_UF` apresenta 19 valores ausentes ou diferentes de `26`; por isso, o filtro territorial usa `SIGLAUFRES`, corroborado por `ID_MN_RESI`.

**Conclusão da validação:** o arquivo está adequado ao recorte territorial de Pernambuco e contém dados do período de notificação de 2015 a 2025. A base é apropriada para o escopo inicial do projeto.

## Tratamento realizado

1. Seleção da UF de residência (`SIGLAUFRES = PE`).
2. Manutenção de notificações individuais (`TP_NOT = 2`).
3. Seleção de dengue (`ID_AGRAVO = A90` nesta extração).
4. Exclusão de duplicidade somente quando explicitamente marcada (`NDUPLIC_N = 2`). Nenhum registro desta extração tinha essa marca.
5. Definição operacional de notificação provável: notificação não descartada; foram excluídas as classificações de descartado (`CLASSI_FIN = 5`) e, quando aplicável, chikungunya (`13`).
6. Uso de `DT_SIN_PRI` como data de referência; em três registros sem data de sintomas foi usada `DT_NOTIFIC`.
7. Restrição da data de referência a 01/01/2015–31/12/2025 e agregação por semana epidemiológica.

Após o tratamento, foram considerados **345.103 registros**, distribuídos em **575 semanas**. Vinte registros com início dos sintomas em 2014 ficaram fora do período; duas linhas não individuais ou sem tipo de notificação foram removidas.

## Totais anuais

| Ano | Notificações prováveis |
|---:|---:|
| 2015 | 105.675 |
| 2016 | 58.899 |
| 2017 | 7.791 |
| 2018 | 11.141 |
| 2019 | 37.808 |
| 2020 | 20.004 |
| 2021 | 36.439 |
| 2022 | 16.094 |
| 2023 | 7.972 |
| 2024 | 22.275 |
| 2025 | 21.005 |
| **Total** | **345.103** |

## Algoritmo e experimento

- Família: aprendizado supervisionado.
- Tarefa: regressão.
- Algoritmo: Random Forest Regressor.
- Variáveis de entrada: defasagens de 1, 2, 3, 4 e 52 semanas, médias móveis e posição temporal da semana no ano.
- Separação cronológica: 418 semanas para treinamento e 105 para teste.
- Avaliação: previsão móvel de uma semana à frente, sem embaralhar a série.
- Referência de comparação: repetir a quantidade observada 52 semanas antes.

| Métrica | Random Forest | Referência sazonal |
|---|---:|---:|
| MAE | 69,7 | 272,5 |
| RMSE | 118,2 | 365,3 |
| R² | 0,806 | -0,854 |

Nesta execução, o Random Forest apresentou erro menor que a referência sazonal no período de teste. Isso é uma evidência inicial de desempenho dentro desta divisão temporal, não uma validação para uso operacional.

## Estimativas experimentais após a base

| Início da semana | Notificações estimadas |
|---|---:|
| 04/01/2026 | 104 |
| 11/01/2026 | 109 |
| 18/01/2026 | 124 |
| 25/01/2026 | 125 |

A extração termina em 31/12/2025. Essas estimativas são uma demonstração do funcionamento do modelo logo após o período histórico, não são uma previsão atualizada para novembro de 2026.

## Limitações para explicar na revisão

- A base contém notificações e não somente casos confirmados. A definição operacional utilizada mantém notificações não descartadas; algumas ainda podem estar inconclusivas ou sem classificação final.
- SINAN pode apresentar subnotificação, atraso e revisões.
- Três registros tiveram `DT_SIN_PRI` ausente e utilizaram `DT_NOTIFIC` como alternativa.
- As semanas epidemiológicas nas extremidades do recorte são parciais: a primeira começa em 28/12/2014 e a última em 28/12/2025. Os registros são filtrados por datas de 2015 a 2025, então essas semanas não contêm sete dias completos no recorte. Isso deve ser levado em conta na interpretação das previsões.
- O experimento usa apenas o histórico de notificações; ainda não incorpora clima, chuva, população ou ações de controle.
- O modelo não é ferramenta oficial de vigilância, não prevê risco individual e não substitui análises da Secretaria de Saúde.

## Arquivos derivados

Os CSVs gerados em `outputs/` contêm a série semanal tratada, a comparação do período de teste, as estimativas, os totais anuais e os totais mensais.
