"""Pipeline de análise e previsão exploratória de notificações prováveis de dengue.

Fonte esperada: microdados SINAN - Dengue (PDD/Cidacs ou arquivo equivalente).
O código padroniza nomes de colunas para aceitar tanto nomes em maiúsculas
(SINAN/DATASUS) quanto nomes em minúsculas (exportações da PDD).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO
import math
import re

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestRegressor
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score

START_DATE = pd.Timestamp("2015-01-01")
END_DATE = pd.Timestamp("2026-12-31")
STATE_CODE = "PE"


@dataclass
class PreparationResult:
    weekly: pd.Series
    filtered_records: pd.DataFrame
    metadata: dict


@dataclass
class ModelResult:
    comparison: pd.DataFrame
    metrics: dict
    forecast: pd.DataFrame
    model: RandomForestRegressor
    feature_importance: pd.DataFrame


def _normalize_column_name(name: object) -> str:
    return re.sub(r"[^A-Z0-9_]", "", str(name).strip().upper())


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result.columns = [_normalize_column_name(c) for c in result.columns]
    return result


def load_dataset(source: str | Path | BinaryIO, filename: str | None = None) -> pd.DataFrame:
    """Lê CSV/CSV.GZ, Excel ou Parquet. Não altera o arquivo original."""
    name = filename or (Path(source).name if isinstance(source, (str, Path)) else "arquivo.csv")
    suffix = name.lower()

    if suffix.endswith(".parquet"):
        return pd.read_parquet(source)
    if suffix.endswith((".xlsx", ".xls")):
        return pd.read_excel(source)
    if suffix.endswith((".csv", ".csv.gz", ".gz")):
        # A exportação PDD pode ser grande. Este projeto precisa apenas dos
        # campos abaixo, então usecols reduz o consumo de memória ao carregar.
        compression = "gzip" if suffix.endswith((".gz", ".csv.gz")) else "infer"
        required_columns = {
            "SIGLAUFRES", "SG_UF", "ID_MN_RESI", "SG_UF_NOT",
            "DT_SIN_PRI", "DT_NOTIFIC", "CLASSI_FIN", "ID_AGRAVO",
            "NDUPLIC_N", "TP_NOT", "SEM_PRI", "NATUREZA_DADO",
            "DATA_ATUALIZACAO_FONTE",
        }
        usecols = lambda column: _normalize_column_name(column) in required_columns
        try:
            return pd.read_csv(
                source, sep=None, engine="python", dtype=str,
                encoding="utf-8-sig", compression=compression, usecols=usecols,
            )
        except UnicodeDecodeError:
            if hasattr(source, "seek"):
                source.seek(0)
            return pd.read_csv(
                source, sep=None, engine="python", dtype=str,
                encoding="latin-1", compression=compression, usecols=usecols,
            )

    raise ValueError(
        "Formato não suportado. Envie CSV, CSV.GZ, XLSX ou Parquet. "
        f"Arquivo recebido: {name}"
    )


def _parse_sinan_dates(values: pd.Series) -> pd.Series:
    """Converte datas SINAN em formatos AAAAMMDD, DD/MM/AAAA ou ISO."""
    raw = values.astype("string").str.strip()
    raw = raw.replace({"": pd.NA, "NAN": pd.NA, "NAT": pd.NA, "NONE": pd.NA, "NULL": pd.NA})
    digits = raw.str.fullmatch(r"\d{8}", na=False)
    parsed = pd.Series(pd.NaT, index=raw.index, dtype="datetime64[ns]")
    if digits.any():
        parsed.loc[digits] = pd.to_datetime(raw.loc[digits], format="%Y%m%d", errors="coerce")
    remaining = ~digits & raw.notna()
    if remaining.any():
        parsed.loc[remaining] = pd.to_datetime(raw.loc[remaining], format="mixed", dayfirst=True, errors="coerce")
    return parsed


def _normalize_code(values: pd.Series) -> pd.Series:
    return values.astype("string").str.strip().str.replace(r"\.0$", "", regex=True)


def prepare_dengue_data(raw_df: pd.DataFrame) -> PreparationResult:
    """Filtra Pernambuco e 2015-2026 e agrega casos prováveis por semana epidemiológica.

    Prioriza UF/município de residência. Se a base não possuir SG_UF, usa
    SG_UF_NOT e registra essa limitação no metadata.
    """
    df = normalize_columns(raw_df)
    original_rows = len(df)
    warnings: list[str] = []

    # Recorte territorial: residência é preferível para análises epidemiológicas.
    # A exportação PDD enviada contém SIGLAUFRES (PE) e SG_UF codificado como 26.
    if "SIGLAUFRES" in df.columns:
        uf_col = "SIGLAUFRES"
        territorial_basis = "UF de residência (SIGLAUFRES)"
        state_values = _normalize_code(df[uf_col]).str.upper()
        df = df.loc[state_values.eq("PE")].copy()
    elif "SG_UF" in df.columns:
        uf_col = "SG_UF"
        territorial_basis = "UF de residência (SG_UF)"
        state_values = _normalize_code(df[uf_col]).str.upper()
        df = df.loc[state_values.isin(["PE", "26"])].copy()
    elif "ID_MN_RESI" in df.columns:
        uf_col = "ID_MN_RESI"
        territorial_basis = "Município de residência (código IBGE iniciado por 26)"
        state_values = _normalize_code(df[uf_col])
        df = df.loc[state_values.str.startswith("26", na=False)].copy()
        warnings.append("A UF de residência não estava disponível; o recorte foi feito pelo código municipal de residência iniciado por 26.")
    elif "SG_UF_NOT" in df.columns:
        uf_col = "SG_UF_NOT"
        territorial_basis = "UF de notificação (SG_UF_NOT), não residência"
        state_values = _normalize_code(df[uf_col]).str.upper()
        df = df.loc[state_values.isin(["PE", "26"])].copy()
        warnings.append("A base não continha UF de residência. Foi usada a UF de notificação; isso pode incluir pessoas residentes em outros estados atendidas em Pernambuco.")
    else:
        raise ValueError("Não encontrei SIGLAUFRES, SG_UF, ID_MN_RESI ou SG_UF_NOT para selecionar Pernambuco. Confira as colunas do arquivo.")

    rows_after_state = len(df)

    # Mantém somente notificações individuais, excluindo tipos agregados ou não informados.
    if "TP_NOT" in df.columns:
        before = len(df)
        df = df.loc[_normalize_code(df["TP_NOT"]).eq("2")].copy()
        removed_notification_types = before - len(df)
    else:
        removed_notification_types = 0
        warnings.append("TP_NOT não estava disponível; não foi possível restringir a análise a notificações individuais.")

    # Desde a adoção da ficha unificada, ID_AGRAVO distingue dengue de chikungunya.
    if "ID_AGRAVO" in df.columns:
        disease_code = _normalize_code(df["ID_AGRAVO"]).str.upper()
        recognized_codes = set(disease_code.dropna().unique())
        if "A90" in recognized_codes:
            df = df.loc[disease_code.eq("A90")].copy()
        elif any(v in recognized_codes for v in ("1", "2")):
            df = df.loc[disease_code.eq("1")].copy()

    # Remove duplicidades explicitamente marcadas como "duplicidade".
    duplicate_rows_removed = 0
    if "NDUPLIC_N" in df.columns:
        duplicate_flag = _normalize_code(df["NDUPLIC_N"])
        before = len(df)
        # Blank/0 = not identified; 1 = not duplicate; 2 = duplicate.
        # Keep missing values rather than treating NA as False in the row mask.
        keep_record = duplicate_flag.ne("2").fillna(True)
        df = df.loc[keep_record].copy()
        duplicate_rows_removed = before - len(df)

    # Casos prováveis: notificações suspeitas, excluindo as classificadas como descartadas.
    # CLASSI_FIN=5 é descartado; CLASSI_FIN=13 é chikungunya na ficha unificada.
    classification_column = "CLASSI_FIN" if "CLASSI_FIN" in df.columns else None
    case_definition = "Notificações prováveis (classificação final diferente de descartado)"
    if classification_column:
        classification = _normalize_code(df[classification_column])
        df = df.loc[~classification.isin(["5", "13"])].copy()
    else:
        case_definition = "Notificações de dengue (CLASSI_FIN ausente; não foi possível excluir descartados)"
        warnings.append("A coluna CLASSI_FIN não estava disponível. Os registros foram tratados como notificações, não como casos prováveis confirmados pela regra do Ministério da Saúde.")

    # Data de início dos sintomas é preferida para a série temporal.
    if "DT_SIN_PRI" in df.columns:
        date_used = "DT_SIN_PRI"
        symptom_date = _parse_sinan_dates(df["DT_SIN_PRI"])
        if "DT_NOTIFIC" in df.columns:
            notification_date = _parse_sinan_dates(df["DT_NOTIFIC"])
            missing_symptom = symptom_date.isna()
            symptom_date = symptom_date.fillna(notification_date)
            if missing_symptom.any():
                warnings.append(
                    f"{int(missing_symptom.sum())} registros sem data de sintomas usaram DT_NOTIFIC como alternativa."
                )
                date_used = "DT_SIN_PRI (com DT_NOTIFIC como alternativa)"
    elif "DT_NOTIFIC" in df.columns:
        date_used = "DT_NOTIFIC"
        symptom_date = _parse_sinan_dates(df["DT_NOTIFIC"])
        warnings.append("DT_SIN_PRI não estava disponível; a data de notificação foi usada como referência temporal.")
    else:
        raise ValueError("Não encontrei DT_SIN_PRI nem DT_NOTIFIC para organizar os registros no tempo.")

    df = df.assign(DATA_REFERENCIA=symptom_date)
    df = df.loc[df["DATA_REFERENCIA"].between(START_DATE, END_DATE, inclusive="both")].copy()
    df = df.loc[df["DATA_REFERENCIA"].notna()].copy()

    if df.empty:
        raise ValueError(
            "Nenhum registro restou após os filtros. Verifique se o arquivo contém Pernambuco e os anos 2015-2026, "
            "e se as colunas estão corretas."
        )

    # Semana epidemiológica brasileira: domingo a sábado. O rótulo representa o domingo de início.
    df["SEMANA_INICIO"] = df["DATA_REFERENCIA"].dt.to_period("W-SAT").dt.start_time
    weekly_counts = df.groupby("SEMANA_INICIO").size().sort_index()
    full_weeks = pd.date_range(weekly_counts.index.min(), weekly_counts.index.max(), freq="7D")
    weekly = weekly_counts.reindex(full_weeks, fill_value=0).astype(int)
    weekly.index.name = "semana_inicio"
    weekly.name = "casos_provaveis"

    metadata = {
        "linhas_originais": original_rows,
        "linhas_apos_filtro_uf": rows_after_state,
        "tipos_notificacao_nao_individuais_removidos": int(removed_notification_types),
        "registros_analisados": int(len(df)),
        "duplicidades_removidas": int(duplicate_rows_removed),
        "total_registros_excluidos_apos_filtros": int(original_rows - len(df)),
        "data_inicial": df["DATA_REFERENCIA"].min().date().isoformat(),
        "data_final": df["DATA_REFERENCIA"].max().date().isoformat(),
        "territorial_basis": territorial_basis,
        "date_used": date_used,
        "case_definition": case_definition,
        "warnings": warnings,
    }
    return PreparationResult(weekly=weekly, filtered_records=df, metadata=metadata)


def _build_feature_row(history: pd.Series, target_date: pd.Timestamp) -> dict:
    values = history.sort_index()
    row: dict[str, float] = {}
    for lag in (1, 2, 3, 4, 52):
        row[f"lag_{lag}"] = float(values.iloc[-lag]) if len(values) >= lag else 0.0
    row["media_movel_4"] = float(values.tail(4).mean()) if len(values) else 0.0
    row["media_movel_8"] = float(values.tail(8).mean()) if len(values) else 0.0
    week_number = int(target_date.isocalendar().week)
    row["semana_seno"] = math.sin(2 * math.pi * week_number / 52.18)
    row["semana_cosseno"] = math.cos(2 * math.pi * week_number / 52.18)
    row["ano"] = float(target_date.year)
    return row


def evaluate_and_forecast(weekly: pd.Series, forecast_weeks: int = 4) -> ModelResult:
    """Treina Random Forest com divisão temporal e compara com baseline sazonal."""
    series = weekly.astype(float).sort_index()
    if len(series) < 80:
        raise ValueError(
            f"A série possui apenas {len(series)} semanas. São necessárias pelo menos 80 semanas para treinar e avaliar o modelo com defasagem anual."
        )

    feature_rows = []
    targets = []
    target_dates = []
    for i in range(52, len(series)):
        target_date = series.index[i]
        feature_rows.append(_build_feature_row(series.iloc[:i], target_date))
        targets.append(float(series.iloc[i]))
        target_dates.append(target_date)

    X = pd.DataFrame(feature_rows, index=pd.DatetimeIndex(target_dates))
    y = pd.Series(targets, index=X.index, name="real")

    test_size = max(12, int(math.ceil(len(X) * 0.20)))
    split = len(X) - test_size
    if split < 30:
        raise ValueError("A base ficou pequena após a preparação. Reduza o número de defasagens ou aumente o período histórico.")

    X_train, X_test = X.iloc[:split], X.iloc[split:]
    y_train, y_test = y.iloc[:split], y.iloc[split:]

    model = RandomForestRegressor(
        n_estimators=250,
        max_depth=10,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    model.fit(X_train, y_train)
    prediction = np.maximum(0, model.predict(X_test))
    seasonal_baseline = X_test["lag_52"].to_numpy()

    def calculate_metrics(actual: pd.Series, predicted: np.ndarray) -> dict:
        return {
            "MAE": float(mean_absolute_error(actual, predicted)),
            "RMSE": float(np.sqrt(mean_squared_error(actual, predicted))),
            "R2": float(r2_score(actual, predicted)) if len(actual) > 1 else float("nan"),
        }

    rf_metrics = calculate_metrics(y_test, prediction)
    baseline_metrics = calculate_metrics(y_test, seasonal_baseline)

    comparison = pd.DataFrame({
        "data": y_test.index,
        "real": y_test.values,
        "random_forest": prediction,
        "baseline_52_semanas": seasonal_baseline,
    }).set_index("data")

    # Reajusta o modelo com todo o histórico antes de estimar as próximas semanas.
    final_model = RandomForestRegressor(
        n_estimators=250,
        max_depth=10,
        min_samples_leaf=2,
        random_state=42,
        n_jobs=-1,
    )
    final_model.fit(X, y)

    future_rows = []
    history = series.copy()
    next_date = history.index.max() + pd.Timedelta(days=7)
    for _ in range(forecast_weeks):
        features = _build_feature_row(history, next_date)
        X_next = pd.DataFrame([features], columns=X.columns)
        estimated = max(0.0, float(final_model.predict(X_next)[0]))
        rounded = int(round(estimated))
        future_rows.append({"data": next_date, "previsao": rounded})
        history.loc[next_date] = rounded
        next_date += pd.Timedelta(days=7)

    forecast = pd.DataFrame(future_rows).set_index("data")
    feature_importance = pd.DataFrame({
        "variavel": X.columns,
        "importancia": final_model.feature_importances_,
    }).sort_values("importancia", ascending=False)

    metrics = {
        "random_forest": rf_metrics,
        "baseline_52_semanas": baseline_metrics,
        "semanas_treino": int(len(X_train)),
        "semanas_teste": int(len(X_test)),
        "modelo": "Random Forest Regressor",
    }
    return ModelResult(
        comparison=comparison,
        metrics=metrics,
        forecast=forecast,
        model=final_model,
        feature_importance=feature_importance,
    )


def export_weekly_csv(weekly: pd.Series, path: str | Path) -> None:
    output = weekly.rename("casos_provaveis").to_frame()
    output.index.name = "semana_inicio"
    output.to_csv(path, encoding="utf-8-sig")
