import re
import pandas as pd

def patch_file():
    with open("/home/pietroscik/delibere comunali/albo pretorio avella/enhanced_extractor.py", "a", encoding="utf-8") as f:
        f.write("""
    def extract_entities_full(self, testo: str, doc_type: str = "") -> dict:
        # 1. Eseguiamo il Router Pattern avanzato
        router_res = self.extract_entities(testo, doc_type)
        
        # 2. Ripristiniamo l'estrazione degli altri campi (CUP, CIG, ecc.)
        cig_pattern = re.compile(r'\\\\bC\\\\.?I\\\\.?G\\\\.?\\\\s*([A-Z0-9]{10})\\\\b', re.IGNORECASE)
        cup_pattern = re.compile(r'\\\\bC\\\\.?U\\\\.?P\\\\.?\\\\s*([A-Z0-9]{15})\\\\b', re.IGNORECASE)
        capitolo_pattern = re.compile(r'\\\\b(?:capitolo|cap\\\\.|capitolo di spesa n\\\\.)\\\\s*(?:n\\\\.?\\\\s*)?(\\\\d+(?:\\\\.\\\\d+)*)\\\\b', re.IGNORECASE)
        
        cig_matches = cig_pattern.findall(testo)
        cig = cig_matches[0].upper() if cig_matches else None
        
        cup_matches = cup_pattern.findall(testo)
        cup = cup_matches[0].upper() if cup_matches else None
        
        cap_matches = capitolo_pattern.findall(testo)
        capitolo = cap_matches[0] if cap_matches else None

        # RUP (Sintattico)
        pattern_istituzionale = re.compile(
            r"(?P<ruolo>RESPONSABILE|DIRIGENTE|FUNZIONARIO|IL R\\\\.U\\\\.P\\\\.?|IL SEGRETARIO|IL SINDACO|IL COORDINATORE)\\\\s+"
            r"(?:DEL|DELL['’]|DELLO|DELLA|DEGLI|GENERALE)?\\\\s*"
            r"(?P<area>(?:SETTORE|AREA|SERVIZIO|UFFICIO|DIREZIONE|COMUNE|COMANDO)\\\\s+[A-Z\\\\sÀ-ú]{3,100}?)\\\\s+"
            r"(?:(?P<titolo>DOTT\\\\.?|DOTT\\\\.SSA|DR\\\\.?|ING\\\\.?|ARCH\\\\.?|GEOM\\\\.?|AVV\\\\.?|RAG\\\\.?|PROF\\\\.?|COL\\\\.?|M\\\\.LLO)\\\\s+)?"
            r"(?P<nome>[A-Z][A-ZÀ-úa-z']+(?:\\\\s+[A-Z][A-ZÀ-úa-z']+){1,3})\\\\b",
            re.IGNORECASE
        )
        match_rup = pattern_istituzionale.search(testo)
        rup = match_rup.group("nome").upper().strip() if match_rup else None
        
        # Merge finale
        router_res.update({
            "cig_estratto": cig,
            "cup_estratto": cup,
            "capitolo": capitolo,
            "responsabile": rup
        })
        return router_res
""")
patch_file()
