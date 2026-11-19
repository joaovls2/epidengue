# Dengue IA - Pernambuco (2015-2025)

Projeto acadêmico de Inteligência Artificial para análise de notificações prováveis de dengue em Pernambuco e estimativa experimental das quatro semanas posteriores ao fim da série histórica.

## A aplicação já abre com dados

O diretório `dashboard_data/` contém apenas dados agregados por semana, ano e mês, calculados a partir da extração real do SINAN processada neste projeto. Assim, o painel pode ser implantado e aberto por outra pessoa sem precisar enviar os microdados individuais.

Para reprocessar uma extração completa, envie o CSV/CSV.GZ pela barra lateral ou coloque o arquivo original em `data/SINAN_-_Dengue.csv`. O arquivo original não deve ser enviado ao repositório público.

## Executar localmente (Windows)

Requisitos: Python 3.11 ou superior.

```powershell
py --version
py -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
streamlit run app.py
```

Se o PowerShell bloquear a ativação do ambiente virtual, use somente nesta janela:

```powershell
Set-ExecutionPolicy -Scope Process -ExecutionPolicy Bypass
.venv\Scripts\Activate.ps1
```

Também é possível ativar pelo Prompt de Comando (CMD):

```bat
.venv\Scripts\activate.bat
```

## Implantar na internet com Streamlit Community Cloud

1. Crie um repositório no GitHub.
2. Envie para ele os arquivos do projeto, incluindo `app.py`, `pipeline.py`, `requirements.txt`, `.streamlit/` e `dashboard_data/`.
3. **Não envie o CSV individual completo do SINAN**. O `.gitignore` já ignora arquivos CSV/CSV.GZ dentro de `data/`.
4. Acesse https://share.streamlit.io/ e entre com GitHub.
5. Clique em **Create app** e selecione o repositório, a branch `main` e o arquivo `app.py`.
6. Clique em **Deploy**. O Streamlit instala as dependências do `requirements.txt` e gera uma URL `*.streamlit.app`.

A aplicação inicializa com a série agregada em `dashboard_data/`, portanto o link abre com gráficos e resultados já disponíveis. É possível enviar uma nova extração pela barra lateral para reprocessá-la, mas isso não é necessário para a demonstração.

## O que o projeto faz

- Problema: analisar a evolução de notificações prováveis de dengue em Pernambuco.
- Fonte: SINAN - Dengue, Ministério da Saúde/DATASUS, extraído pela PDD-Cidacs/Fiocruz.
- Recorte: 2015 a 2025, por UF de residência.
- Definição operacional: notificações suspeitas não descartadas.
- Família de IA: aprendizado supervisionado.
- Tarefa: regressão.
- Algoritmo: Random Forest Regressor.
- Avaliação: divisão cronológica, comparada a uma referência sazonal de 52 semanas.
- Visualizações: série semanal, totais anuais, sazonalidade mensal, avaliação do modelo, estimativas e importância das variáveis.

## Limitações

O SINAN contém notificações e pode apresentar subnotificação, atraso e revisão. O modelo é experimental e não substitui previsões oficiais ou decisões da vigilância epidemiológica. A base termina em dezembro de 2025; as quatro estimativas apresentadas são para janeiro de 2026, não uma previsão atualizada.

Consulte `RESUMO_PARA_APRESENTAR.md` e `RESULTADOS_REAIS.md` para os detalhes da extração, do tratamento e do experimento.
