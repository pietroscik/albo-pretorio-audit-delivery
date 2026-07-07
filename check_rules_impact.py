#!/usr/bin/env python3
import pandas as pd

# Carico i dati
df = pd.read_csv('data/avella/albo_download/allegati_parsed.csv')

print('Distribuzione finale della confidenza:')
print(df['classification_confidence'].value_counts())
print()

print('Distribuzione finale delle categorie (prime 10):')
print(df['category'].value_counts().head(10))
print()

print(f'Numero totale di documenti: {len(df)}')
print(f'Documenti con classificazione ambigua: {(df["classification_confidence"] == "ambiguous").sum()}')
alta_confidenza = df["classification_confidence"].isin(["ml_predicted_high_conf", "rule_based"])
print(f'Documenti con alta confidenza (rule_based o ml_predicted_high_conf): {alta_confidenza.sum()} ({alta_confidenza.sum()/len(df)*100:.1f}%)')

# Analisi specifica per le categorie interessate dalle regole
print("\nAnalisi specifica per categorie interessate dalle regole:")
contabilita_mask = df['category'] == 'Contabilità'
lavori_pubblici_mask = df['category'] == 'Lavori Pubblici'
personale_mask = df['category'] == 'Personale'

print(f"Contabilità: {contabilita_mask.sum()} documenti")
print(f"Lavori Pubblici: {lavori_pubblici_mask.sum()} documenti")
print(f"Personale: {personale_mask.sum()} documenti")

# Verifica la confidenza per queste categorie
print(f"\nConfidenza per Contabilità:")
print(df[contabilita_mask]['classification_confidence'].value_counts())

print(f"\nConfidenza per Lavori Pubblici:")
print(df[lavori_pubblici_mask]['classification_confidence'].value_counts())

print(f"\nConfidenza per Personale:")
print(df[personale_mask]['classification_confidence'].value_counts())