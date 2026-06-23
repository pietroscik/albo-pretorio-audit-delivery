import pandas as pd
import json

corpus_file = 'data/albo_download/documenti_corpus.jsonl'
csv_file = 'data/albo_download/allegati_parsed.csv'

# Leggi il corpus
texts = {}
with open(corpus_file, 'r', encoding='utf-8') as f:
    for line in f:
        data = json.loads(line)
        texts[data.get('pdf_name')] = data.get('text', '')[:4000]

# Aggiorna il CSV
df = pd.read_csv(csv_file)
if 'pdf_name' in df.columns:
    df['text_preview'] = df['pdf_name'].map(texts).fillna(df.get('text_preview', ''))
    df.to_csv(csv_file, index=False)
    print("Testo RAW correttamente iniettato nel CSV con i line-break originali!")
else:
    print("Colonna pdf_name non trovata in allegati_parsed.csv")
