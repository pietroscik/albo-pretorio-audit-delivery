import re
import unicodedata
from typing import Optional

def normalize_text_for_ml(text: Optional[str]) -> str:
    """
    Normalizza il testo per l'uso nei modelli ML.
    Rimuove caratteri speciali, normalizza gli spazi e converte in minuscolo.
    """
    if not text or not isinstance(text, str):
        return ""
    
    # Normalizza la codifica Unicode
    text = unicodedata.normalize('NFKD', text)
    
    # Rimuove caratteri di controllo
    text = ''.join(ch for ch in text if ord(ch) >= 32 or ch in '\t\n\r')
    
    # Sostituisce sequenze multiple di spazi bianchi con uno spazio singolo
    text = re.sub(r'\s+', ' ', text)
    
    # Rimuove spazi iniziali e finali
    text = text.strip()
    
    return text