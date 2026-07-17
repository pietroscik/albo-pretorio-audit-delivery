import re
from typing import Dict, Any

class TextFeatureExtractor:
    """
    Calcola feature statistiche e quantitative dal testo di un documento.
    """
    def extract(self, text: str) -> Dict[str, Any]:
        """
        Estrae un dizionario di feature dal testo.
        """
        text = text or ""
        lower = text.lower()
        words = re.findall(r"\w+", lower, flags=re.UNICODE)
        years = sorted(set(re.findall(r"\b20\d{2}\b", text)))
        return {
            "text_chars": len(text),
            "text_words": len(words),
            "unique_words": len(set(words)),
            "euro_mentions": len(re.findall(r"€| euro\b", lower)),
            "cig_mentions": len(re.findall(r"\bcig\b", lower)),
            "cup_mentions": len(re.findall(r"\bcup\b", lower)),
            "date_mentions": len(re.findall(r"\b\d{1,2}/\d{1,2}/20\d{2}\b", text)),
            "years_mentioned": ",".join(years),
        }