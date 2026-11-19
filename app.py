from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from pipeline import evaluate_and_forecast, load_dataset, prepare_dengue_data

BASE_DIR = Path(__file__).parent
DEFAULT_DATA_CANDIDATES = [
    BASE_DIR / "data" / "SINAN_-_Dengue.csv",
    BASE_DIR / "data" / "dengue_pe_2015_2026.csv.gz",
    BASE_DIR / "data" / "dengue_pe_2015_2026.csv",
]
DEFAULT_DATA = next((candidate for candidate in DEFAULT_DATA_CANDIDATES if candidate.exists()), None)
DASHBOARD_DATA = BASE_DIR / "dashboard_data"

# Metadados da extração 2026 utilizada nesta versão do painel.
DATA_2026_UPDATE_DATE = "14/11/2026"
DATA_2026_LAST_SYMPTOM_DATE = "2026-10-29"
DATA_2026_LAST_PARTIAL_WEEK = pd.Timestamp("2026-10-25")


def next_epidemiological_week_start() -> pd.Timestamp:
    """Retorna o próximo domingo, início da próxima semana epidemiológica."""
    today = pd.Timestamp(datetime.now(ZoneInfo("America/Recife")).date())
    days_since_sunday = (today.weekday() + 1) % 7
    current_week_start = today - pd.Timedelta(days=days_since_sunday)
    return current_week_start + pd.Timedelta(days=7)


def format_number(value: float) -> str:
    return f"{value:,.0f}".replace(",", ".")


st.set_page_config(page_title="EpiDengue | Pernambuco", page_icon="🦟", layout="wide")
st.title("🦟 EpiDengue")
st.subheader("Análise de dados e previsão de notificações prováveis de dengue em Pernambuco")
st.caption("Projeto acadêmico de Inteligência Artificial | SINAN | Histórico 2015–2025 + dados preliminares de 2026")

with st.expander("Sobre o projeto", expanded=True):
    st.write(
        "O EpiDengue analisa notificações de dengue registradas no SINAN para residentes de Pernambuco. "
        "Os registros são organizados por semana epidemiológica e utilizados por um modelo Random Forest Regressor "
        "para estimar a quantidade de notificações prováveis nas próximas semanas."
    )
    st.info(
        "Casos prováveis são definidos operacionalmente como as notificações, exceto aquelas classificadas como descartadas. "
        "Os dados de 2026 são preliminares e podem sofrer atualização. As estimativas são experimentais e não substituem previsões oficiais."
    )

st.sidebar.header("Base de dados")
st.sidebar.write(
    "O painel já inclui a série semanal agregada de 2015 a 2026. "
    "Para reprocessar uma extração completa do SINAN, envie um arquivo CSV/CSV.GZ. "
    "Se o arquivo estiver em ZIP, extraia o CSV antes de enviar."
)
uploaded = st.sidebar.file_uploader(
    "Enviar microdados do SINAN (opcional)",
    type=["csv", "gz", "xlsx", "xls", "parquet"],
    help="A extração original pode ser grande. Não a adicione ao repositório público. Para a demonstração, os dados agregados já estão incluídos.",
)

if uploaded is not None or DEFAULT_DATA is not None:
    source = uploaded if uploaded is not None else str(DEFAULT_DATA)
    source_name = uploaded.name if uploaded is not None else DEFAULT_DATA.name
    try:
        raw = load_dataset(source, source_name)
        prepared = prepare_dengue_data(raw)
        weekly = prepared.weekly
        meta = prepared.metadata
        annual = (
            prepared.filtered_records.groupby(prepared.filtered_records["DATA_REFERENCIA"].dt.year)
            .size().rename_axis("Ano").reset_index(name="Casos prováveis")
        )
        monthly_by_year = prepared.filtered_records.groupby([
            prepared.filtered_records["DATA_REFERENCIA"].dt.year,
            prepared.filtered_records["DATA_REFERENCIA"].dt.month,
        ]).size().unstack(0)
        monthly = monthly_by_year.mean(axis=1).reindex(range(1, 13), fill_value=0)
        monthly_title = "Média mensal da extração enviada"
        source_description = f"Microdados processados nesta sessão: {source_name}"
    except Exception as exc:
        st.error(f"Não foi possível processar o arquivo: {exc}")
        st.stop()
else:
    try:
        weekly_df = pd.read_csv(
            DASHBOARD_DATA / "dengue_pe_semanal_2015_2026.csv",
            encoding="utf-8-sig",
            parse_dates=["semana_inicio"],
        )
        weekly = pd.Series(
            weekly_df["casos_provaveis"].astype(float).to_numpy(),
            index=pd.DatetimeIndex(weekly_df["semana_inicio"]),
            name="casos_provaveis",
        ).sort_index()

        annual = pd.read_csv(
            DASHBOARD_DATA / "dengue_pe_total_anual_2015_2026.csv",
            encoding="utf-8-sig",
        )
        annual = annual.rename(columns={"ano": "Ano", "casos_provaveis": "Casos prováveis"})

        # A sazonalidade mensal permanece baseada nos anos completos de 2015 a 2025.
        monthly_raw = pd.read_csv(
            DASHBOARD_DATA / "dengue_pe_total_mensal_2015_2025.csv",
            encoding="utf-8-sig",
        )
        monthly_by_year = monthly_raw.pivot(index="mes", columns="ano", values="casos_provaveis")
        monthly = monthly_by_year.mean(axis=1).reindex(range(1, 13), fill_value=0)
        monthly_title = "Sazonalidade: média de notificações por mês (2015–2025)"

        meta = {
            "registros_analisados": 368835,
            "data_inicial": "2015-01-01",
            "data_final": DATA_2026_LAST_SYMPTOM_DATE,
            "territorial_basis": "UF de residência (Pernambuco): SIGLAUFRES = PE em 2015–2025 e SG_UF = 26 em 2026",
            "date_used": "Data de início dos sintomas (DT_SIN_PRI)",
            "case_definition": "Notificações prováveis: notificações não descartadas; ID_AGRAVO = A90; CLASSI_FIN = 5 e 13 excluídos.",
            "linhas_originais": 834322,
            "linhas_apos_filtro_uf": 368857,
            "tipos_notificacao_nao_individuais_removidos": 2,
            "duplicidades_removidas": 0,
            "warnings": [
                f"A parcela de 2026 é preliminar; a extração oficial estava atualizada em {DATA_2026_UPDATE_DATE}.",
                f"A data de início de sintomas mais recente encontrada na extração de 2026 é {pd.Timestamp(DATA_2026_LAST_SYMPTOM_DATE):%d/%m/%Y}.",
            ],
        }
        source_description = (
            "Série agregada: PDD/Cidacs (2015–2025) + Portal de Dados Abertos do SUS/SINAN (2026). "
            "Os microdados individuais não são publicados no repositório."
        )
    except Exception as exc:
        st.error(f"Não foi possível carregar os dados agregados incluídos no projeto: {exc}")
        st.stop()

if "residência" not in meta["territorial_basis"].lower():
    st.warning(f"Atenção ao recorte territorial: {meta['territorial_basis']}.")
for warning in meta.get("warnings", []):
    st.warning(warning)

st.caption(source_description)
st.subheader("1. Visão geral da base")
col1, col2, col3, col4 = st.columns(4)
col1.metric("Registros analisados", format_number(meta["registros_analisados"]))
col2.metric("Total no período", format_number(float(weekly.sum())))
col3.metric("Média semanal", f"{weekly.mean():,.1f}".replace(",", "X").replace(".", ",").replace("X", "."))
col4.metric("Semanas no histórico", format_number(len(weekly)))

st.caption(
    f"Período dos registros: {pd.Timestamp(meta['data_inicial']):%d/%m/%Y} a "
    f"{pd.Timestamp(meta['data_final']):%d/%m/%Y} | Território: {meta['territorial_basis']} | "
    f"Data temporal: {meta['date_used']}"
)

# Remove semanas parciais das extremidades antes de treinar e avaliar o modelo.
# A primeira pode começar antes de 01/01/2015; a última pode terminar depois
# da data mais recente disponível na extração.
model_weekly = weekly.copy()
first_data_date = pd.Timestamp(meta["data_inicial"]).normalize()
first_week_start = first_data_date.to_period("W-SAT").start_time
first_week_is_partial = first_data_date > first_week_start
if first_week_is_partial and first_week_start in model_weekly.index:
    model_weekly = model_weekly.loc[model_weekly.index > first_week_start]

last_data_date = pd.Timestamp(meta["data_final"]).normalize()
last_week_start = last_data_date.to_period("W-SAT").start_time
last_week_end = last_week_start + pd.Timedelta(days=6)
is_last_week_partial = last_data_date < last_week_end
partial_week_cases = 0

if is_last_week_partial and last_week_start in weekly.index:
    partial_week_cases = int(weekly.loc[last_week_start])
    model_weekly = model_weekly.loc[model_weekly.index < last_week_start]
    last_complete_week_start = last_week_start - pd.Timedelta(days=7)
    st.info(
        f"A última semana epidemiológica da extração ({last_week_start:%d/%m} a {last_week_end:%d/%m/%Y}) "
        f"está incompleta: foram registrados {partial_week_cases:,} casos até {last_data_date:%d/%m/%Y}. "
        f"Ela aparece no histórico, mas foi retirada do treinamento e da avaliação do modelo. "
        f"A última semana completa utilizada pelo algoritmo foi {last_complete_week_start:%d/%m} a "
        f"{(last_complete_week_start + pd.Timedelta(days=6)):%d/%m/%Y}."
    )
else:
    last_complete_week_start = model_weekly.index.max()

if first_week_is_partial:
    st.caption(
        f"A primeira semana ({first_week_start:%d/%m/%Y}) também é parcial, pois os registros começam em "
        f"{first_data_date:%d/%m/%Y}; ela foi mantida na visualização, mas não no treinamento."
    )

if len(model_weekly) < 80:
    st.error("A série possui poucas semanas completas para treinar e avaliar o modelo.")
    st.stop()

st.subheader("2. Análise exploratória dos dados")
weekly_df = weekly.rename("Casos prováveis").reset_index()
weekly_df.columns = ["Início da semana", "Casos prováveis"]
fig_week = px.line(
    weekly_df,
    x="Início da semana",
    y="Casos prováveis",
    title="Evolução semanal das notificações prováveis de dengue",
)
fig_week.update_traces(line=dict(width=1.5))
fig_week.update_layout(hovermode="x unified", margin=dict(l=10, r=10, t=55, b=10))
st.plotly_chart(fig_week, use_container_width=True)

annual_plot = annual.copy()
annual_plot["Ano"] = pd.to_numeric(annual_plot["Ano"], errors="coerce").astype("Int64")
annual_plot["Ano (rótulo)"] = annual_plot["Ano"].astype(str)
annual_plot.loc[annual_plot["Ano"].eq(2026), "Ano (rótulo)"] = "2026*"

months = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
monthly_df = pd.DataFrame({"Mês": months, "Média anual de notificações": monthly.reindex(range(1, 13), fill_value=0).values})
left, right = st.columns(2)
with left:
    fig_annual = px.bar(
        annual_plot,
        x="Ano (rótulo)",
        y="Casos prováveis",
        title="Total de notificações prováveis por ano",
    )
    fig_annual.update_layout(margin=dict(l=10, r=10, t=55, b=10), xaxis_title="Ano (* 2026 parcial)")
    st.plotly_chart(fig_annual, use_container_width=True)
with right:
    fig_month = px.bar(
        monthly_df,
        x="Mês",
        y="Média anual de notificações",
        title=monthly_title,
    )
    fig_month.update_layout(margin=dict(l=10, r=10, t=55, b=10))
    st.plotly_chart(fig_month, use_container_width=True)

st.caption("* 2026 é parcial: a extração utilizada foi atualizada em 14/11/2026 e contém início de sintomas até 29/10/2026.")

st.subheader("3. Algoritmo de Inteligência Artificial")
st.write(
    "**Família:** aprendizado supervisionado | **Tarefa:** regressão | **Algoritmo:** Random Forest Regressor. "
    "O modelo utiliza defasagens das semanas anteriores, médias móveis e a posição da semana no ano para estimar a quantidade de notificações."
)

# A previsão é iniciada na próxima semana epidemiológica (domingo) após a data atual de Recife.
next_week_start = next_epidemiological_week_start()
first_model_forecast_date = model_weekly.index.max() + pd.Timedelta(days=7)
intermediate_weeks = max(0, int((next_week_start - first_model_forecast_date).days // 7))
forecast_horizon = intermediate_weeks + 4

try:
    result = evaluate_and_forecast(model_weekly, forecast_weeks=forecast_horizon)
except Exception as exc:
    st.error(f"A série foi preparada, mas não foi possível treinar o modelo: {exc}")
    st.stop()

st.subheader("4. Experimento e avaliação")
st.write("A avaliação preserva a ordem temporal: as semanas mais recentes ficam separadas para teste, sem embaralhar os dados.")
rf = result.metrics["random_forest"]
base = result.metrics["baseline_52_semanas"]
m1, m2, m3 = st.columns(3)
m1.metric("MAE - Random Forest", f"{rf['MAE']:.1f} casos")
m2.metric("RMSE - Random Forest", f"{rf['RMSE']:.1f} casos")
m3.metric("MAE - referência sazonal", f"{base['MAE']:.1f} casos")

comparison = result.comparison.reset_index().melt(
    id_vars="data",
    value_vars=["real", "random_forest", "baseline_52_semanas"],
    var_name="Série",
    value_name="Casos",
)
comparison["Série"] = comparison["Série"].map({
    "real": "Valor real",
    "random_forest": "Random Forest",
    "baseline_52_semanas": "Referência: mesma semana do ano anterior",
})
fig_test = px.line(comparison, x="data", y="Casos", color="Série", title="Comparação no período de teste")
fig_test.update_layout(hovermode="x unified", margin=dict(l=10, r=10, t=55, b=10))
st.plotly_chart(fig_test, use_container_width=True)

st.caption(
    f"Treinamento: {result.metrics['semanas_treino']} semanas | "
    f"Teste: {result.metrics['semanas_teste']} semanas | "
    f"R² no teste: {rf['R2']:.3f}. MAE mede o erro absoluto médio; RMSE penaliza mais erros grandes."
)

st.subheader("5. Previsão para as próximas quatro semanas")
st.write(f"Próxima semana epidemiológica futura: **{next_week_start:%d/%m/%Y}**.")
if intermediate_weeks > 0:
    st.warning(
        f"A extração não possui registros observados recentes o suficiente para chegar diretamente a essa data. "
        f"O modelo gera {intermediate_weeks} previsão(ões) intermediária(s), de "
        f"{first_model_forecast_date:%d/%m/%Y} até "
        f"{(first_model_forecast_date + pd.Timedelta(days=7 * (intermediate_weeks - 1))):%d/%m/%Y}, "
        "e utiliza essas estimativas como entrada para projetar as quatro semanas exibidas abaixo. "
        "Essas semanas intermediárias não são registros reais."
    )

future_forecast = result.forecast.loc[result.forecast.index >= next_week_start].head(4).copy()
if len(future_forecast) < 4:
    st.warning("Não foi possível gerar quatro semanas futuras completas com a série disponível.")
else:
    forecast_display = future_forecast.rename(columns={"previsao": "Casos estimados"}).reset_index()
    forecast_display["data"] = pd.to_datetime(forecast_display["data"]).dt.strftime("%d/%m/%Y")
    forecast_display = forecast_display.rename(columns={"data": "Início da semana"})
    st.dataframe(forecast_display, use_container_width=True, hide_index=True)

fig_future = go.Figure()
recent = model_weekly.tail(26)
fig_future.add_trace(go.Scatter(
    x=recent.index,
    y=recent.values,
    name="Histórico observado (semanas completas)",
    mode="lines",
))
fig_future.add_trace(go.Scatter(
    x=result.forecast.index,
    y=result.forecast["previsao"],
    name="Projeção do modelo",
    mode="lines+markers",
    line=dict(dash="dash"),
))
fig_future.add_vline(
    x=next_week_start,
    line_dash="dot",
    annotation_text="Início das semanas futuras exibidas",
    annotation_position="top right",
)
fig_future.update_layout(
    title="Histórico recente e projeção recursiva",
    xaxis_title="Semana epidemiológica (início no domingo)",
    yaxis_title="Notificações prováveis estimadas",
    hovermode="x unified",
    margin=dict(l=10, r=10, t=55, b=10),
)
st.plotly_chart(fig_future, use_container_width=True)

st.caption(
    "As projeções são experimentais. Como os registros de dengue podem ser notificados com atraso e revisados, "
    "o resultado depende da data de atualização da base e pode mudar em uma nova extração."
)

st.subheader("6. Variáveis mais utilizadas pelo modelo")
fig_importance = px.bar(
    result.feature_importance.head(10).sort_values("importancia"),
    x="importancia",
    y="variavel",
    orientation="h",
    title="Importância das variáveis no Random Forest",
)
fig_importance.update_layout(margin=dict(l=10, r=10, t=55, b=10), yaxis_title="Variável", xaxis_title="Importância")
st.plotly_chart(fig_importance, use_container_width=True)

st.subheader("7. Exportar resultados")
weekly_export = weekly.rename("casos_provaveis").rename_axis("semana_inicio").reset_index()
c1, c2 = st.columns(2)
c1.download_button(
    "Baixar série semanal tratada (CSV)",
    weekly_export.to_csv(index=False).encode("utf-8-sig"),
    file_name="dengue_pe_semanal_2015_2026.csv",
    mime="text/csv",
)
if len(future_forecast) > 0:
    forecast_export = future_forecast.rename(columns={"previsao": "casos_estimados"}).rename_axis("semana_inicio").reset_index()
    c2.download_button(
        "Baixar previsão das próximas semanas (CSV)",
        forecast_export.to_csv(index=False).encode("utf-8-sig"),
        file_name="previsao_dengue_pe_proximas_semanas.csv",
        mime="text/csv",
    )

with st.expander("Detalhes do tratamento dos dados"):
    st.write(f"**Definição utilizada:** {meta['case_definition']}")
    st.write(f"**Base territorial:** {meta['territorial_basis']}")
    st.write(f"**Data utilizada:** {meta['date_used']}")
    st.write(f"**Linhas recebidas na extração enviada ou consolidada:** {meta['linhas_originais']:,}")
    st.write(f"**Linhas após recorte territorial:** {meta['linhas_apos_filtro_uf']:,}")
    st.write(f"**Tipos de notificação não individuais removidos:** {meta['tipos_notificacao_nao_individuais_removidos']:,}")
    st.write(f"**Duplicidades explicitamente marcadas removidas:** {meta['duplicidades_removidas']:,}")
    st.write(f"**Registros considerados na série:** {meta['registros_analisados']:,}")
    if first_week_is_partial:
        st.write(f"**Primeira semana parcial (não usada no treinamento):** {first_week_start:%d/%m/%Y}")
    if is_last_week_partial:
        st.write(f"**Registros da última semana parcial (não usados no treinamento):** {partial_week_cases:,}")
    st.write(f"**Última semana completa usada no treinamento:** {last_complete_week_start:%d/%m/%Y} a {(last_complete_week_start + pd.Timedelta(days=6)):%d/%m/%Y}")

st.divider()
st.caption(
    "Projeto acadêmico experimental. Os dados do SINAN estão sujeitos a atrasos, subnotificação e revisões. "
    "As estimativas não constituem alerta epidemiológico nem orientação para decisões clínicas ou de gestão."
)
