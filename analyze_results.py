import pandas as pd
df = pd.read_csv('data/baiano/albo_download/allegati_parsed.csv')

print('=== ANALISI DETTAGLIATA DEI DATI ESTRATTI ===')
print(f'Totale documenti: {len(df)}')

# Controlliamo i documenti con testo significativo
docs_with_text = df[df['text_chars'] > 100]  # Solo documenti con almeno 100 caratteri
print(f'Documenti con testo significativo (>100 caratteri): {len(docs_with_text)}')

# Controlliamo quanti hanno dati estratti
print(f'\nDocumenti con importi_raw non vuoti: {df["importi_raw"].notna().sum()}')
print(f'Documenti con importi_raw non vuoti e != "[]": {(df["importi_raw"] != "[]").sum()}')

# Controlliamo i documenti che hanno importi non zero
importi_non_zero = df[(df['importo_max'].notna()) & (df['importo_max'] > 0)]
print(f'Documenti con importo_max > 0: {len(importi_non_zero)}')

# Analisi dei beneficiari
print(f'\nBeneficiari non nulli: {df["beneficiario"].notna().sum()}')
print(f'Beneficiari non nulli e != "": {(df["beneficiario"].notna() & (df["beneficiario"] != "")).sum()}')
if df['beneficiario'].notna().sum() > 0:
    print('Esempi di beneficiari trovati:')
    for benef in df[df['beneficiario'].notna()]['beneficiario'].head(5):
        print(f'  - "{benef}"')

# Analisi del metodo di estrazione
print(f'\nMetodi di estrazione utilizzati:')
print(df['extraction_method'].value_counts())

# Controlliamo i documenti con dati finanziari
print(f'\nDocumenti con quadro_economico non nullo: {df["quadro_economico"].notna().sum()}')
print(f'Documenti con capitolo non nullo: {df["capitolo"].notna().sum()}')

# Controlliamo la distribuzione dei tipi di documento
print(f'\nDistribuzione per tipo documento:')
for doc_type in df['doc_type'].unique():
    subset = df[df['doc_type'] == doc_type]
    has_benef = subset['beneficiario'].notna().sum()
    has_importi = (subset['importo_max'].notna() & subset['importo_max'] > 0).sum()
    print(f'  {doc_type}: {len(subset)} docs, {has_benef} con beneficiario, {has_importi} con importi')