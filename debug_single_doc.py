import pandas as pd
import numpy as np
from pathlib import Path
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '.'))

from src.delibere_comunali.parsing.entity_extractor import EntityExtractor
from src.delibere_comunali.parsing.tabular_extractor import TabularExtractor
from src.delibere_comunali.parsing.text_extractor import TextExtractor

# Carichiamo un documento di esempio
df = pd.read_csv('data/baiano/albo_download/allegati_parsed.csv')
sample_doc = df.iloc[0]  # Prendiamo il primo documento

print('=== ANALISI SINGOLO DOCUMENTO ===')
print(f'Nome file: {sample_doc["pdf_name"]}')
text_preview = sample_doc["text_preview"]
if pd.isna(text_preview):
    text_preview = ""
else:
    text_preview = str(text_preview)
print(f'Testo preview: {text_preview[:200]}...')

importi_raw = sample_doc["importi_raw"]
print(f'Importi raw: {importi_raw}')
print(f'Importo max: {sample_doc["importo_max"]}')

beneficiario = sample_doc["beneficiario"]
if pd.isna(beneficiario):
    beneficiario = None
else:
    beneficiario = str(beneficiario)
print(f'Beneficiario: {beneficiario}')

# Proviamo a estrarre manualmente da questo documento
pdf_path = Path(sample_doc['pdf_path'])
text_extractor = TextExtractor()
text, source = text_extractor.extract(pdf_path)

print(f'\n=== ESTRAZIONE MANUALE ===')
print(f'Source: {source}')
print(f'Lunghezza testo: {len(text)}')
print(f'Testo iniziale: {text[:500]}...')

# Estraiamo le entità usando EntityExtractor
entity_extractor = EntityExtractor()
entities = entity_extractor.extract_all(text, sample_doc['doc_type'])

print(f'\n=== ENTITA\' ESTRATTE ===')
print(f'CIG trovati: {entities["cig"]}')
print(f'CUP trovati: {entities["cup"]}')
print(f'Importi trovati: {entities["importi"]}')
print(f'Max importo: {entities["importo_max"]}')
print(f'Importi_count: {entities["importi_count"]}')
print(f'Beneficiari trovati: {entities["beneficiario"]}')
print(f'Responsabili trovati: {entities["responsabile"]}')

# Estrazione dati strutturati
try:
    tabular_extractor = TabularExtractor()
    layout_result = tabular_extractor.extract_structured_data(pdf_path)

    print(f'\n=== DATI STRUTTURATI ESTRATTI ===')
    print(f'Tabelle trovate: {len(layout_result.table_elements)}')
    for i, table in enumerate(layout_result.table_elements):
        print(f'Tabella {i+1} - Tipo: {table.table_type}, Pagine: {table.page_number}, Righe: {len(table.data) if table.data else 0}')
        if table.data:
            print(f'  Prime 3 righe: {table.data[:3]}')
except Exception as e:
    print(f'\nERRORE nell\'estrazione dati strutturati: {e}')