from rapidfuzz import process, fuzz
import pandas as pd

def normalize_entities(df, threshold=85):
    unique_names = df['beneficiario'].dropna().unique()
    mapping = {}

    for name in unique_names:
        if name in mapping: continue
        # Trova tutti i nomi simili all'85%
        matches = process.extract(name, unique_names, scorer=fuzz.token_sort_ratio, limit=None)
        # Il nome canonico diventa quello più frequente o il più corto
        canonical_name = name 
        for match, score, index in matches:
            if score >= threshold:
                mapping[match] = canonical_name

    df['beneficiario_canonico'] = df['beneficiario'].map(mapping)
    return df