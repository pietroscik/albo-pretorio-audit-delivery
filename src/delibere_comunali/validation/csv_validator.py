#!/usr/bin/env python3
"""
CSV Output Validator
Validates the output CSV files produced by the analysis pipeline
"""

import argparse
from pathlib import Path
import pandas as pd
import sys

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from delibere_comunali.utils.config import get_tenant_dir


def validate_file(path: Path, required_cols):
    """Validate a single CSV file for required columns."""
    if not path.exists():
        return None, [f"file mancante: {path}"]
    try:
        df = pd.read_csv(path, encoding="utf-8")
    except Exception as exc:
        return None, [f"lettura fallita ({path}): {exc}"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        return df, [f"colonne mancanti in {path.name}: {', '.join(missing)}"]
    return df, []


def validate_output_structure(base_path: Path) -> tuple[bool, list[str], list[str]]:
    """Validate the overall output structure and required files."""
    issues = []
    warnings = []
    
    # Define required files and their required columns
    required_files = {
        "allegati_parsed.csv": [
            "pdf_name", "data_atto", "oggetto", "categoria", "classification_confidence",
            "importo_max", "beneficiario", "responsabile", "ufficio", "cig", "cup"
        ],
        "procedures.json": [],  # JSON file - just check existence
        "anomalies.json": [],   # JSON file - just check existence
    }
    
    # Validate each required file
    for filename, required_cols in required_files.items():
        file_path = base_path / filename
        df, err = validate_file(file_path, required_cols)
        if err:
            issues.extend(err)
    
    # Check for additional important files
    optional_files = {
        "documenti_features.csv": ["pdf_name"],
        "allegati_classificati.csv": ["pdf_name", "category"],
        "report.md": [],
        "alert_antifrode.md": []
    }
    
    for filename, required_cols in optional_files.items():
        file_path = base_path / filename
        if file_path.exists():
            df, err = validate_file(file_path, required_cols)
            if err:
                warnings.extend(err)
        else:
            warnings.append(f"file opzionale mancante: {filename}")
    
    return len(issues) == 0, issues, warnings


def validate_data_quality(df: pd.DataFrame) -> list[str]:
    """Validate data quality within a DataFrame."""
    issues = []
    
    # Check for completely empty dataframes
    if df.empty:
        issues.append("DataFrame completamente vuoto")
        return issues
    
    # Check for null ratios in critical columns
    critical_cols = ['pdf_name', 'data_atto', 'oggetto']
    for col in critical_cols:
        if col in df.columns:
            null_ratio = df[col].isnull().sum() / len(df)
            if null_ratio > 0.5:  # More than 50% null
                issues.append(f"Colonna critica '{col}' con {null_ratio:.1%} valori nulli")
    
    # Check for reasonable date ranges if data_atto exists
    if 'data_atto' in df.columns:
        df_dates = pd.to_datetime(df['data_atto'], errors='coerce')
        valid_dates = df_dates.dropna()
        if not valid_dates.empty:
            date_range = valid_dates.max() - valid_dates.min()
            if date_range.days < 0:  # Future dates or wrong parsing
                issues.append("Date fuori intervallo ragionevole")
    
    # Check for realistic importo values if column exists
    if 'importo_max' in df.columns:
        importi = pd.to_numeric(df['importo_max'], errors='coerce').dropna()
        if not importi.empty:
            extreme_values = importi[(importi < 0) | (importi > 1e9)]  # Values over 1 billion
            if not extreme_values.empty:
                issues.append(f"Trovati {len(extreme_values)} importi estremi (>1 miliardo o <0)")
    
    return issues


def main():
    parser = argparse.ArgumentParser(description="Valida gli output CSV prodotti dal pipeline")
    parser.add_argument("--ente", required=True, help="Nome dell'ente locale da analizzare")
    args = parser.parse_args()

    ente = args.ente
    # get_tenant_dir already returns the full path including albo_download
    base_path = Path(get_tenant_dir(ente))
    # If the path already includes albo_download, don't add it again
    if not str(base_path).endswith("albo_download"):
        base_path = base_path / "albo_download"
    
    print(f"Validazione output per ente: {ente}")
    print(f"Percorso base: {base_path}")
    
    if not base_path.exists():
        print(f"ERRORE: Percorso base non esistente: {base_path}")
        sys.exit(1)
    
    # Validate overall structure
    is_valid, issues, warnings = validate_output_structure(base_path)
    
    # Load and validate main CSV if it exists
    main_csv_path = base_path / "allegati_parsed.csv"
    if main_csv_path.exists():
        try:
            df = pd.read_csv(main_csv_path)
            data_issues = validate_data_quality(df)
            issues.extend(data_issues)
            
            print(f"\nDati caricati: {len(df)} righe, {len(df.columns)} colonne")
            print(f"Colonne: {list(df.columns)}")
        except Exception as e:
            issues.append(f"Errore caricamento allegati_parsed.csv: {e}")
    else:
        issues.append(f"File principale mancante: {main_csv_path}")
    
    # Report results
    print(f"\n{'='*50}")
    print(f"VALIDAZIONE OUTPUT - {ente.upper()}")
    print(f"{'='*50}")
    
    if issues:
        print(f"\n🔴 ERRORI TROVATI ({len(issues)}):")
        for i, issue in enumerate(issues, 1):
            print(f"  {i}. {issue}")
    else:
        print(f"\n🟢 VALIDAZIONE PASSATA: Nessun errore critico trovato")
    
    if warnings:
        print(f"\n🟡 WARNING ({len(warnings)}):")
        for i, warning in enumerate(warnings, 1):
            print(f"  {i}. {warning}")
    
    print(f"\n{'='*50}")
    print(f"Riepilogo: {len(issues)} errori, {len(warnings)} warning")
    
    # Exit with error code if there are issues
    if issues:
        print("❌ Validazione fallita: errori critici trovati")
        sys.exit(1)
    else:
        print("✅ Validazione completata con successo")
        sys.exit(0)


if __name__ == "__main__":
    main()