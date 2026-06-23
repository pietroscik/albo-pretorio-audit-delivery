#!/usr/bin/env python3
import re
import sys
import json
from pathlib import Path

def validate_amounts(text, metadata_amounts):
    """
    Applica lo scoring di contesto agli importi estratti per garantirne la veridicità.
    """
    results = []
    
    # Zone Detection migliorata
    zones = {
        "preamble": "",
        "disposition": "",
        "accounting": ""
    }
    
    # Pattern di split più robusti
    text_upper = text.upper()
    
    # Trova gli indici delle sezioni chiave
    idx_preamble = -1
    for k in ["PREMESSO CHE", "VISTO:", "CONSIDERATO"]:
        idx = text_upper.find(k)
        if idx != -1:
            idx_preamble = idx
            break
            
    idx_disposition = -1
    for k in ["DETERMINA", "DELIBERA", "ORDINA"]:
        idx = text_upper.find(k)
        if idx != -1:
            idx_disposition = idx
            break
            
    idx_accounting = text_upper.find("VISTO DI REGOLARITÀ CONTABILE")
    if idx_accounting == -1:
        idx_accounting = text_upper.find("IMPEGNO DEFINITIVO")

    for amount in metadata_amounts:
        # Formattazione per la ricerca nel testo (es. 113.011,53)
        amount_val = float(amount)
        amount_str = f"{amount_val:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
        # Versione senza decimali se .00
        amount_simple = f"{int(amount_val):,}".replace(",", ".")
        
        pos = text.find(amount_simple)
        if pos == -1:
            # Prova con la versione a virgola
            pos = text.replace(".", ",").find(amount_str)
            
        score = 50 
        
        if pos != -1:
            # Assegnazione zona basata sulla posizione
            if idx_accounting != -1 and pos >= idx_accounting:
                score += 70 # Massima fiducia: tabella contabile
            elif idx_disposition != -1 and pos >= idx_disposition:
                score += 40 # Alta fiducia: dispositivo
            elif idx_preamble != -1 and pos >= idx_preamble:
                # Siamo nelle premesse: controlliamo se è un fondo nazionale
                score -= 30
                surrounding = text[max(0, pos-150):min(len(text), pos+150)].lower()
                if any(k in surrounding for k in ["nazionale", "decreto", "ministero", "complessivo"]):
                    score -= 50 # Penalità severa per fondi nazionali
            
            # Bonus per vicinanza a CIG o Beneficiario
            surrounding_small = text[max(0, pos-50):min(len(text), pos+50)].lower()
            if "cig" in surrounding_small or "€" in surrounding_small:
                score += 10
        
        results.append({
            "amount": amount,
            "score": score,
            "veridicity": "high" if score > 100 else ("medium" if score > 50 else "low"),
            "detected_at": pos
        })
    
    return sorted(results, key=lambda x: x['score'], reverse=True)

if __name__ == "__main__":
    # Esempio di utilizzo via CLI
    if len(sys.argv) < 3:
        print(json.dumps({"error": "Usage: finance_validator.py <text_path> <amounts_json>"}))
        sys.exit(1)
        
    text = Path(sys.argv[1]).read_text(encoding="utf-8")
    amounts = json.loads(sys.argv[2])
    print(json.dumps(validate_amounts(text, amounts), indent=2))
