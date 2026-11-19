# EpiDengue - Pernambuco

Projeto acadêmico de análise de dados e previsão experimental de notificações prováveis de dengue em Pernambuco.

## Dados nesta versão

- 2015-2025: série histórica agregada proveniente da PDD/Cidacs.
- 2026: microdados públicos do SINAN/Dengue, Portal de Dados Abertos do SUS, filtrados para residentes em Pernambuco (SG_UF=26). A extração usada foi atualizada em 14/11/2026 e contém datas de início de sintomas até 29/10/2026.
- A primeira semana de 2015 e a última semana parcial de 2026 são exibidas no histórico, mas não são usadas para treinar ou avaliar o modelo. A última semana contém registros apenas até 29/10/2026.
- A sazonalidade mensal permanece calculada sobre os anos completos de 2015 a 2025.

## Algoritmo

Random Forest Regressor (aprendizado supervisionado, tarefa de regressão), com variáveis de defasagem semanal, médias móveis e posição da semana no ano. A avaliação utiliza divisão temporal, sem embaralhar as observações.

## Execução local

```bash
python -m venv .venv
# Windows Git Bash: source .venv/Scripts/activate
# Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -r requirements.txt
streamlit run app.py
```

## Arquivos de dados

- `dashboard_data/dengue_pe_semanal_2015_2026.csv`: série semanal combinada.
- `dashboard_data/dengue_pe_total_anual_2015_2026.csv`: totais anuais; 2026 é parcial.
- `dashboard_data/dengue_pe_total_mensal_2015_2025.csv`: sazonalidade baseada em anos completos.
- `dashboard_data/FONTE_DADOS_2026.txt`: critérios de extração e fonte.

Os microdados individuais não são incluídos no repositório.

## Limitações

A fonte de 2026 é preliminar e apresenta atraso entre a ocorrência dos sintomas e a publicação. Para prever a partir da próxima semana futura, o sistema pode produzir semanas intermediárias estimadas quando não existem observações recentes. Essas previsões devem ser interpretadas como experimento acadêmico, não como alerta epidemiológico oficial.
