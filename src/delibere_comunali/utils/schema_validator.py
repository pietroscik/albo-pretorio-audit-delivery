import argparse
import pandas as pd
from pathlib import Path

def parse_markdown_schema(md_path: Path):
    """Legge il file Markdown ed estrae il dizionario delle colonne e dei tipi attesi."""
    schema = {}
    with open(md_path, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    in_table = False
    for line in lines:
        if line.startswith('| Nome Colonna'):
            in_table = True
            continue
        if in_table and line.startswith('|---'):
            continue
        if in_table and line.startswith('|'):
            parts = [p.strip() for p in line.split('|')]
            if len(parts) >= 3:
                col_name = parts[1].replace('`', '')
                col_type = parts[2].replace('`', '').lower()
                if col_name:
                    schema[col_name] = col_type
    return schema

def validate_csv(csv_path: Path, schema: dict):
    print(f"📄 Validazione di '{csv_path.name}' in corso...\n")
    try:
        df = pd.read_csv(csv_path, low_memory=False)
    except Exception as e:
        print(f"❌ Errore nella lettura del CSV: {e}")
        return False

    csv_cols = set(df.columns)
    schema_cols = set(schema.keys())

    missing_cols = schema_cols - csv_cols
    extra_cols = csv_cols - schema_cols

    is_valid = True

    if missing_cols:
        print(f"❌ COLONNE MANCANTI NEL CSV (Richieste dallo schema):")
        for col in missing_cols:
            print(f"   - {col}")
        is_valid = False
    else:
        print("✅ Tutte le colonne principali richieste dallo schema sono presenti nel CSV.\n")

    if extra_cols:
        print(f"ℹ️ COLONNE EXTRA NEL CSV (Aggiuntive rispetto allo schema base):")
        for col in sorted(extra_cols):
            print(f"   - {col}")

    print("\n🔍 CONTROLLO TIPI DI DATO (Type Coercion):")
    for col, expected_type in schema.items():
        if col not in df.columns:
            continue
        
        actual_dtype = str(df[col].dtype)
        is_type_valid = False
        
        # Mappatura permissiva (Pandas converte spesso i bool/string con NaN in 'object')
        if expected_type == 'string' and actual_dtype in ['object', 'string']:
            is_type_valid = True
        elif expected_type == 'float' and actual_dtype in ['float64', 'float32', 'int64']:
            is_type_valid = True
        elif expected_type == 'boolean' and actual_dtype in ['bool', 'object']:
            is_type_valid = True

        if is_type_valid:
            print(f"  [OK] {col}: atteso '{expected_type}', Pandas ha rilevato '{actual_dtype}'")
        else:
            print(f"  [WARN] {col}: atteso '{expected_type}', Pandas ha rilevato '{actual_dtype}'")

    return is_valid

def main():
    parser = argparse.ArgumentParser(description="Verifica conformità CSV rispetto allo schema Markdown.")
    parser.add_argument("--schema", default="DATA_SCHEMA.md", help="Percorso del file Markdown con lo schema")
    parser.add_argument("--csv", default="data/baiano/albo_download/allegati_parsed.csv", help="Percorso del file CSV da validare")
    args = parser.parse_args()

    schema = parse_markdown_schema(Path(args.schema))
    if not schema:
        print("❌ Nessuna colonna trovata nello schema Markdown.")
        return

    validate_csv(Path(args.csv), schema)

if __name__ == "__main__":
    main()