"""Teste automatizado com registros sintéticos (somente para validar o código).
Os dados abaixo NÃO são dados epidemiológicos reais e não devem ser usados como resultado do projeto.
"""
import numpy as np
import pandas as pd

from pipeline import prepare_dengue_data, evaluate_and_forecast


def synthetic_dataset():
    rng = np.random.default_rng(42)
    dates = pd.date_range("2015-01-01", "2025-12-31", freq="7D")
    rows = []
    for i, date in enumerate(dates):
        count = max(0, int(80 + 40 * np.sin(2 * np.pi * date.dayofyear / 365.25) + rng.normal(0, 8)))
        for _ in range(count):
            rows.append({
                "SG_UF": "PE",
                "DT_SIN_PRI": date.strftime("%Y%m%d"),
                "DT_NOTIFIC": date.strftime("%Y%m%d"),
                "CLASSI_FIN": "10",
                "ID_AGRAVO": "1",
                "NDUPLIC_N": "0",
                "ID_MN_RESI": "261160",
            })
        rows.append({
            "SG_UF": "PE", "DT_SIN_PRI": date.strftime("%Y%m%d"), "DT_NOTIFIC": date.strftime("%Y%m%d"),
            "CLASSI_FIN": "5", "ID_AGRAVO": "1", "NDUPLIC_N": "0", "ID_MN_RESI": "261160",
        })
    rows.append({
        "SG_UF": "PB", "DT_SIN_PRI": "20230101", "DT_NOTIFIC": "20230101",
        "CLASSI_FIN": "10", "ID_AGRAVO": "1", "NDUPLIC_N": "0", "ID_MN_RESI": "250750",
    })
    return pd.DataFrame(rows)


def test_pipeline_runs():
    prepared = prepare_dengue_data(synthetic_dataset())
    assert len(prepared.weekly) > 500
    assert prepared.weekly.sum() > 0
    result = evaluate_and_forecast(prepared.weekly, forecast_weeks=4)
    assert len(result.forecast) == 4
    assert result.forecast["previsao"].ge(0).all()
    assert "MAE" in result.metrics["random_forest"]


if __name__ == "__main__":
    test_pipeline_runs()
    print("Teste concluído com dados sintéticos. O teste valida o funcionamento do código, não o desempenho com a base real.")
