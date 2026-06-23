import argparse
import pandas as pd
import re
import os
from pathlib import Path

def agentic_cleanup(base_path):
    print(f"🚀 Avvio Pulizia Agentica Discrezionale in {base_path}...")
    
    base = Path(base_path)
    allegati_file = base / "allegati_parsed.csv"
    
    if not allegati_file.exists():
        print(f"File {allegati_file} non trovato.")
        return

    # 1. Caricamento Dati
    df_allegati = pd.read_csv(allegati_file)
    
    # 2. Correzioni Discrezionali
    
    # A. Cluster: Manifesti e Comunicazioni (Sempre Importo 0)
    manifesto_mask = df_allegati['pdf_name'].str.contains('manifesto|leva|esami|avviso', case=False, na=False)
    df_allegati.loc[manifesto_mask, 'doc_type'] = 'Manifesto'
    df_allegati.loc[manifesto_mask, 'category'] = 'Comunicazione Istituzionale'
    df_allegati.loc[manifesto_mask, 'importo_max'] = 0.0
    df_allegati.loc[manifesto_mask, 'importo_sum'] = 0.0
    
    # B. Cluster: Convocazioni
    convocazione_mask = df_allegati['pdf_name'].str.contains('convocazione|consiglio', case=False, na=False)
    df_allegati.loc[convocazione_mask, 'doc_type'] = 'Convocazione'
    df_allegati.loc[convocazione_mask, 'category'] = 'Affari Istituzionali'
    df_allegati.loc[convocazione_mask, 'importo_max'] = 0.0
    
    # C. Correzione Bias Finanziario (Fondi Nazionali nelle premesse)
    fondi_terzi_mask = (df_allegati['importo_max'] > 500000) & (~df_allegati['category'].isin(['Lavori Pubblici', 'Contabilità']))
    df_allegati.loc[fondi_terzi_mask, 'anomalie'] = 'Importo di contesto (Fondo Nazionale)'
    df_allegati.loc[fondi_terzi_mask, 'importo_max'] = 0.0
    
    # D. Correzione Beneficiari Errati
    df_allegati.loc[df_allegati['piva_beneficiario'] == 'MUNICIPIO', 'piva_beneficiario'] = 'Personale Interno (Incentivi)'
    
    # E. Risoluzione Unknown tramite nome file (Euristica Agentica)
    df_allegati.loc[(df_allegati['doc_type'] == 'unknown') & (df_allegati['pdf_name'].str.contains('Determina', case=False)), 'doc_type'] = 'Determinazione'
    df_allegati.loc[(df_allegati['doc_type'] == 'unknown') & (df_allegati['pdf_name'].str.contains('Delibera', case=False)), 'doc_type'] = 'Delibera'

    # 3. Salvataggio Golden Set
    df_allegati.to_csv(allegati_file, index=False)
    print(f"✅ Golden Set generato: {len(df_allegati)} record processati.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--base", default="albo_download")
    args = parser.parse_args()
    agentic_cleanup(args.base)
