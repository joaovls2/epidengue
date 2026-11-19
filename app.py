from pathlib import Path

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

from pipeline import evaluate_and_forecast, load_dataset, prepare_dengue_data

BASE_DIR = Path(__file__).parent
DEFAULT_DATA_CANDIDATES = [
    BASE_DIR / "data" / "SINAN_-_Dengue.csv",
    BASE_DIR / "data" / "dengue_pe_2015_2025.csv.gz",
    BASE_DIR / "data" / "dengue_pe_2015_2025.csv",
]
DEFAULT_DATA = next((candidate for candidate in DEFAULT_DATA_CANDIDATES if candidate.exists()), None)
DASHBOARD_DATA = BASE_DIR / "dashboard_data"

st.set_page_config(page_title="Dengue PE | Análise e previsão", page_icon="🦟", layout="wide")
st.title("🦟 Análise e previsão de notificações prováveis de dengue em Pernambuco")
st.caption("Projeto acadêmico de Inteligência Artificial | SINAN | Período de análise: 2015–2025")

with st.expander("Sobre o projeto", expanded=True):
    st.write(
        "O projeto analisa notificações de dengue registradas no SINAN, utiliza o recorte de Pernambuco e agrega os registros por semana. "
        "Em seguida, utiliza um algoritmo Random Forest Regressor para estimar a quantidade de notificações prováveis nas semanas posteriores ao último período disponível."
    )
    st.info(
        "Definição operacional: casos prováveis são as notificações suspeitas, excluindo as classificadas como descartadas. "
        "Os dados são sujeitos a revisão e subnotificação; as estimativas são experimentais e não substituem previsões oficiais."
    )

st.sidebar.header("Base de dados")
st.sidebar.write(
    "O painel já inclui uma série semanal agregada da extração analisada. "
    "Para reprocessar os microdados originais, envie o CSV/CSV.GZ abaixo."
)
uploaded = st.sidebar.file_uploader(
    "Enviar microdados do SINAN (opcional)",
    type=["csv", "gz", "xlsx", "xls", "parquet"],
    help="A extração original pode ser grande. Não a adicione ao repositório público. Para a demonstração, a série semanal agregada já está incluída.",
)

prepared = None
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
        source_description = f"Microdados processados nesta sessão: {source_name}"
    except Exception as exc:
        st.error(f"Não foi possível processar o arquivo: {exc}")
        st.stop()
else:
    try:
        weekly_df = pd.read_csv(DASHBOARD_DATA / "dengue_pe_semanal_2015_2025.csv", encoding="utf-8-sig", parse_dates=["semana_inicio"])
        weekly = pd.Series(
            weekly_df["casos_provaveis"].astype(float).to_numpy(),
            index=pd.DatetimeIndex(weekly_df["semana_inicio"]),
            name="casos_provaveis",
        ).sort_index()
        annual = pd.read_csv(DASHBOARD_DATA / "dengue_pe_total_anual_2015_2025.csv", encoding="utf-8-sig")
        annual = annual.rename(columns={"ano": "Ano", "casos_provaveis": "Casos prováveis"})
        monthly_raw = pd.read_csv(DASHBOARD_DATA / "dengue_pe_total_mensal_2015_2025.csv", encoding="utf-8-sig")
        monthly_by_year = monthly_raw.pivot(index="mes", columns="ano", values="casos_provaveis")
        monthly = monthly_by_year.mean(axis=1).reindex(range(1, 13), fill_value=0)
        meta = {
            "registros_analisados": 345103,
            "data_inicial": "2015-01-01",
            "data_final": "2025-12-31",
            "territorial_basis": "UF de residência (SIGLAUFRES = PE)",
            "date_used": "Início dos sintomas (DT_SIN_PRI); 3 registros sem data usaram DT_NOTIFIC",
            "case_definition": "Notificações suspeitas não descartadas; excluídas CLASSI_FIN = 5 e classificação 13 quando aplicável.",
            "linhas_originais": 345125,
            "linhas_apos_filtro_uf": 345125,
            "tipos_notificacao_nao_individuais_removidos": 2,
            "duplicidades_removidas": 0,
            "warnings": [],
        }
        source_description = "Série semanal agregada real incluída no projeto (microdados individuais não são publicados no repositório)."
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
col1.metric("Registros analisados", f"{meta['registros_analisados']:,}".replace(",", "."))
col2.metric("Total no período", f"{int(weekly.sum()):,}".replace(",", "."))
col3.metric("Média semanal", f"{weekly.mean():,.1f}".replace(",", "X").replace(".", ",").replace("X", "."))
col4.metric("Semanas analisadas", f"{len(weekly):,}".replace(",", "."))

st.caption(
    f"Início dos sintomas considerado: {meta['data_inicial']} a {meta['data_final']} | "
    f"Território: {meta['territorial_basis']} | Data temporal: {meta['date_used']}"
)
if weekly.index.min().year < 2015:
    st.caption(
        f"A primeira semana epidemiológica começa em {weekly.index.min():%d/%m/%Y} "
        "porque contém os primeiros dias de 2015; registros com sintomas em 2014 foram excluídos."
    )

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

months = ["Jan", "Fev", "Mar", "Abr", "Mai", "Jun", "Jul", "Ago", "Set", "Out", "Nov", "Dez"]
monthly_df = pd.DataFrame({"Mês": months, "Média anual de notificações": monthly.values})
left, right = st.columns(2)
with left:
    fig_annual = px.bar(annual, x="Ano", y="Casos prováveis", title="Total de notificações prováveis por ano")
    fig_annual.update_layout(margin=dict(l=10, r=10, t=55, b=10))
    st.plotly_chart(fig_annual, use_container_width=True)
with right:
    fig_month = px.bar(monthly_df, x="Mês", y="Média anual de notificações", title="Sazonalidade: média de notificações por mês (2015–2025)")
    fig_month.update_layout(margin=dict(l=10, r=10, t=55, b=10))
    st.plotly_chart(fig_month, use_container_width=True)

st.subheader("3. Algoritmo de Inteligência Artificial")
st.write(
    "**Família:** aprendizado supervisionado | **Tarefa:** regressão | **Algoritmo:** Random Forest Regressor. "
    "O modelo usa as últimas semanas, médias móveis e a posição da semana no ano para estimar a quantidade da semana seguinte."
)

try:
    result = evaluate_and_forecast(weekly, forecast_weeks=4)
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
    id_vars="data", value_vars=["real", "random_forest", "baseline_52_semanas"],
    var_name="Série", value_name="Casos",
)
comparison["Série"] = comparison["Série"].map({
    "real": "Valor real", "random_forest": "Random Forest", "baseline_52_semanas": "Referência: mesma semana do ano anterior"
})
fig_test = px.line(comparison, x="data", y="Casos", color="Série", title="Comparação no período de teste")
fig_test.update_layout(hovermode="x unified", margin=dict(l=10, r=10, t=55, b=10))
st.plotly_chart(fig_test, use_container_width=True)

st.caption(
    f"Treinamento: {result.metrics['semanas_treino']} semanas | "
    f"Teste: {result.metrics['semanas_teste']} semanas | "
    f"R² no teste: {rf['R2']:.3f}. MAE mede o erro absoluto médio; RMSE penaliza mais erros grandes."
)

st.subheader("5. Estimativa das quatro semanas após o recorte histórico")
st.caption(
    "As estimativas partem da última semana disponível na base (dezembro de 2025). "
    "Como o recorte termina em 2025, as datas previstas são de janeiro de 2026; "
    "não representam uma previsão atualizada para novembro de 2026."
)
forecast_display = result.forecast.copy()
forecast_display.index.name = "Início da semana"
forecast_display = forecast_display.rename(columns={"previsao": "Casos estimados"})
st.dataframe(forecast_display, use_container_width=True)

fig_future = go.Figure()
recent = weekly.tail(26)
fig_future.add_trace(go.Scatter(x=recent.index, y=recent.values, name="Histórico", mode="lines"))
fig_future.add_trace(go.Scatter(x=result.forecast.index, y=result.forecast["previsao"], name="Estimativa", mode="lines+markers", line=dict(dash="dash")))
fig_future.update_layout(title="Histórico recente e estimativa para as próximas semanas", xaxis_title="Semana", yaxis_title="Notificações prováveis", hovermode="x unified", margin=dict(l=10, r=10, t=55, b=10))
st.plotly_chart(fig_future, use_container_width=True)

st.subheader("6. Variáveis mais utilizadas pelo modelo")
fig_importance = px.bar(
    result.feature_importance.head(10).sort_values("importancia"),
    x="importancia", y="variavel", orientation="h",
    title="Importância das variáveis no Random Forest",
)
fig_importance.update_layout(margin=dict(l=10, r=10, t=55, b=10), yaxis_title="Variável", xaxis_title="Importância")
st.plotly_chart(fig_importance, use_container_width=True)

st.subheader("7. Exportar resultados")
weekly_export = weekly.rename("casos_provaveis").rename_axis("semana_inicio").reset_index()
forecast_export = result.forecast.rename(columns={"previsao": "casos_estimados"}).rename_axis("semana_inicio").reset_index()
c1, c2 = st.columns(2)
c1.download_button(
    "Baixar série semanal tratada (CSV)",
    weekly_export.to_csv(index=False).encode("utf-8-sig"),
    file_name="dengue_pe_semanal_2015_2025.csv",
    mime="text/csv",
)
c2.download_button(
    "Baixar estimativas (CSV)",
    forecast_export.to_csv(index=False).encode("utf-8-sig"),
    file_name="previsao_dengue_pe_4_semanas.csv",
    mime="text/csv",
)

with st.expander("Detalhes do tratamento dos dados"):
    st.write(f"**Definição utilizada:** {meta['case_definition']}")
    st.write(f"**Base territorial:** {meta['territorial_basis']}")
    st.write(f"**Data utilizada:** {meta['date_used']}")
    st.write(f"**Linhas recebidas na extração original:** {meta['linhas_originais']:,}")
    st.write(f"**Linhas após recorte territorial:** {meta['linhas_apos_filtro_uf']:,}")
    st.write(f"**Tipos de notificação não individuais removidos:** {meta['tipos_notificacao_nao_individuais_removidos']:,}")
    st.write(f"**Duplicidades explicitamente marcadas removidas:** {meta['duplicidades_removidas']:,}")
    st.write(f"**Registros considerados na série:** {meta['registros_analisados']:,}")

st.divider()
st.caption(
    "Projeto acadêmico experimental. Os dados do SINAN estão sujeitos a atrasos, subnotificação e revisões. "
    "As estimativas não constituem alerta epidemiológico nem orientação para decisões clínicas ou de gestão."
)
