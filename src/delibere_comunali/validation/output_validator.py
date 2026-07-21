#!/usr/bin/env python3
"""
Output Validator - Direct execution with ente parameter support
"""

import argparse
import sys
from pathlib import Path

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from delibere_comunali.utils.config import get_tenant_dir

# Import and run the original validate_output script's functionality directly
def main():
    # Parse ente argument
    parser = argparse.ArgumentParser(description="Valida gli output prodotti da analyze_albo.py")
    parser.add_argument("--ente", required=True, help="Nome dell'ente locale da analizzare")
    parser.add_argument("--max-unknown-doc-type-pct", type=float, default=35.0, 
                       help="Soglia percentuale massima di doc_type=unknown (warning se superata).")
    parser.add_argument("--fail-on-warning", action="store_true",
                       help="Se impostato, i warning fanno uscire con codice 1.")
    
    args = parser.parse_args()
    
    # Convert ente argument to what the original script expects
    # We'll replicate the original script's functionality but with ente-based path resolution
    import argparse as orig_argparse
    from pathlib import Path as orig_Path
    import pandas as pd
    from delibere_comunali.utils import logger  # Assuming this exists

    def pct(part, total):
        if not total:
            return 0.0
        return round((float(part) / float(total)) * 100.0, 2)

    def validate_file(path: orig_Path, required_cols):
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

    # Use ente to determine base path
    # get_tenant_dir already returns the full path including albo_download
    base = orig_Path(get_tenant_dir(args.ente))
    # If the path already includes albo_download, don't add it again
    if not str(base).endswith("albo_download"):
        base = base / "albo_download"
    
    issues = []
    warnings = []

    df_features, errs = validate_file(
        base / "documenti_features.csv",
        ["pdf_name", "oggetto", "categoria", "classification_confidence", "data_atto", "ufficio"],
    )
    if errs:
        issues.extend(errs)

    df_parsed, errs = validate_file(
        base / "allegati_parsed.csv",
        ["pdf_name", "oggetto", "categoria", "classification_confidence", "data_atto", "ufficio"],
    )
    if errs:
        issues.extend(errs)

    # Check for unknown document types if parsed data exists
    if df_parsed is not None and "categoria" in df_parsed.columns:
        unknown_count = len(df_parsed[df_parsed["categoria"] == "unknown"])
        total_count = len(df_parsed)
        unknown_pct = pct(unknown_count, total_count)
        
        if unknown_pct > args.max_unknown_doc_type_pct:
            warn_msg = f"Alta percentuale di documenti sconosciuti: {unknown_pct}% > {args.max_unknown_doc_type_pct}%"
            warnings.append(warn_msg)
            if args.fail_on_warning:
                issues.append(warn_msg)

    # Check for required JSON files
    for json_file in ["procedures.json", "anomalies.json"]:
        json_path = base / json_file
        if not json_path.exists():
            issues.append(f"file JSON mancante: {json_file}")

    # Report results
    print(f"Validazione output per ente: {args.ente}")
    print(f"Percorso base: {base}")
    print(f"{'='*50}")
    print(f"VALIDAZIONE OUTPUT - {args.ente.upper()}")
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