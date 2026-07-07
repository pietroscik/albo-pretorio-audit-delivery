# scripts/validate_statistics.py
import pandas as pd
from delibere_comunali.utils.extraction_core import StatisticalValidator
import argparse
import json
import numpy as np
from datetime import date, datetime

def _json_default(o):
    if isinstance(o, (np.bool_,)):
        return bool(o)
    if isinstance(o, (np.integer,)):
        return int(o)
    if isinstance(o, (np.floating,)):
        return float(o)
    if isinstance(o, (pd.Timestamp, datetime, date)):
        return o.isoformat()
    if pd.isna(o):
        return None
    raise TypeError(f"Object of type {o.__class__.__name__} is not JSON serializable")

def main():
    parser = argparse.ArgumentParser(description="Valida statisticamente i dati estratti.")
    parser.add_argument('--base', type=str, default='./data/avella/albo_download',
                       help='Directory base dei dati')
    parser.add_argument('--output', type=str, default='anomalie_statistiche.json',
                       help='File di output')
    args = parser.parse_args()

    # Carica dati
    df = pd.read_csv(f'{args.base}/allegati_parsed.csv')

    # Inizializza validatore
    validator = StatisticalValidator(df)

    # Genera report
    stats_report = validator.get_statistics_report()
    print("📊 Report Statistico:")
    print(json.dumps(stats_report, indent=2))

    # Valida tutti i record
    results = []
    for idx, row in df.iterrows():
        if pd.notna(row.get('importo_max')):
            importo_validation = validator.validate_importo(row['importo_max'])
            beneficiario_validation = validator.validate_beneficiario(row.get('beneficiario'), df)
            contesto_validation = validator.validate_contesto(row)

            if not (importo_validation.is_valid and beneficiario_validation.is_valid and contesto_validation.is_valid):
                results.append({
                    'pdf_name': row.get('pdf_name'),
                    'importo': row.get('importo_max'),
                    'beneficiario': row.get('beneficiario'),
                    'data': row.get('data_atto'),
                    'anomalie': {
                        'importo': importo_validation.anomalies,
                        'beneficiario': beneficiario_validation.anomalies,
                        'contesto': contesto_validation.anomalies
                    },
                    'z_score': importo_validation.z_score,
                    'iqr_outlier': importo_validation.iqr_outlier,
                    'benford_compliant': importo_validation.benford_compliant
                })

    # Salva risultati
    output_path = f'{args.base}/{args.output}'
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(
            {"statistics": stats_report, "anomalies": results},
            f,
            indent=2,
            ensure_ascii=False,
            default=_json_default,
        )

    print(f"\n✅ Salvato report in {args.base}/{args.output}")
    print(f"🔍 Trovate {len(results)} anomalie statistiche")

if __name__ == '__main__':
    main()