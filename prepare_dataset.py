"""Prepara a base SINAN e exporta a série semanal para CSV."""
import argparse
from pathlib import Path

from pipeline import load_dataset, prepare_dengue_data, export_weekly_csv


def main():
    parser = argparse.ArgumentParser(description="Prepara microdados SINAN - Dengue para Pernambuco (2015-2025).")
    parser.add_argument("--input", required=True, help="Caminho do CSV, CSV.GZ, XLSX ou Parquet baixado da PDD-Cidacs.")
    parser.add_argument("--output", default="data/dengue_pe_semanal_2015_2025.csv", help="Caminho do CSV semanal de saída.")
    args = parser.parse_args()

    raw = load_dataset(args.input)
    result = prepare_dengue_data(raw)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    export_weekly_csv(result.weekly, output)

    print("Preparação concluída.")
    print(f"Registros originais: {result.metadata['linhas_originais']:,}")
    print(f"Registros analisados: {result.metadata['registros_analisados']:,}")
    print(f"Período: {result.metadata['data_inicial']} até {result.metadata['data_final']}")
    print(f"Total no período: {int(result.weekly.sum()):,}")
    print(f"Arquivo gerado: {output.resolve()}")
    print(f"Definição: {result.metadata['case_definition']}")
    for warning in result.metadata["warnings"]:
        print(f"ATENÇÃO: {warning}")


if __name__ == "__main__":
    main()
