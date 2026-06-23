
import re
import pandas as pd
from pathlib import Path

class DelibereExtractor:
    """
    Classe ottimizzata per l'estrazione strutturata di entità da testi di delibere e determine.
    Conforme alle linee guida AGID e al Nuovo Codice Appalti (D.Lgs 36/2023).
    """
    
    def __init__(self):
        # Pattern CIG: solitamente 10 caratteri alfanumerici
        self.cig_pattern = re.compile(r'\bC\.?I\.?G\.?[\s:;]*([A-Z0-9]{10})\b', re.IGNORECASE)
        
        # Pattern CUP: solitamente 15 caratteri alfanumerici
        self.cup_pattern = re.compile(r'\bC\.?U\.?P\.?[\s:;]*([A-Z0-9]{15})\b', re.IGNORECASE)
        
        # Pattern Importi: intercetta formati italiani
        self.importo_pattern = re.compile(r'(?:€|euro|importo(?:\s+complessivo)?(?:\s+pari)?\s+a)\s*([\d\s]{1,11}(?:[.,]\d{2,3})*(?:[.,]\d{2})?)', re.IGNORECASE)
        
        # Pattern Partita IVA: 11 cifre numeriche
        self.piva_pattern = re.compile(r'\bP\.?I\.?V\.?A\.?[\s:;]*(\d{11})\b', re.IGNORECASE)
        
        # Pattern IBAN: IT seguito da 2 cifre, 1 lettera e 22 cifre (anche con spazi)
        self.iban_pattern = re.compile(r'\bIT\s*\d{2}\s*[A-Z]\s*\d{5}\s*\d{5}\s*[0-9A-Z\s]{12,15}\b', re.IGNORECASE)
        
        # Pattern Codice Appalti: D.Lgs 36/2023 o 50/2016
        self.appalti_pattern = re.compile(r'\bD\.?\s*Lgs\.?\s*(?:n\.?\s*)?(36/2023|50/2016|267/2000|163/2006|190/2012)\b', re.IGNORECASE)
        
        # Pattern Nuovo Codice Appalti (D.Lgs 36/2023) - Procedure specifiche
        self.procedure_appalti_pattern = re.compile(r'\b(affidamento\s+diretto|procedura\s+negoziata|accordo\s+quadro|sotto\s+soglia|sopra\s+soglia|art\.?\s*50|art\.?\s*108)\b', re.IGNORECASE)

        # Pattern Beneficiario: Intercetta nomi di ditte o persone dopo specifiche parole chiave
        self.beneficiario_pattern = re.compile(r'(?:ditta|societ[aà]|impresa|operatore economico|a favore d[ei]|liquidare a(?:lla)?|nei confronti d[ei])\s+([A-Z][A-Z0-9\s\.\&\-\']{3,60}?)(?:\s+con\s+sede|\s+p\.?iva|\s+c\.?f\.|\s+partita iva|\s+c\.?i\.?g\.?|,|/|\n)', re.IGNORECASE)

        # Pattern Capitolo di Spesa / PEG
        self.capitolo_pattern = re.compile(r'\b(?:capitolo|cap\.|capitolo di spesa n\.)\s*(?:n\.?\s*)?(\d+(?:\.\d+)*)\b', re.IGNORECASE)

        # Pattern Impegno di Spesa
        self.impegno_pattern = re.compile(r'\b(?:impegno|imp\.)\s*(?:di\s+spesa\s*)?(?:n\.?\s*)?(\d+)\s*(?:del|/|anno|\-)\s*(\d{4})\b', re.IGNORECASE)

        # Pattern RUP (Responsabile Unico del Procedimento/Progetto)
        self.rup_pattern = re.compile(r'\b(?:RUP|Responsabile Unico del(?:la)? (?:Progetto|Procedimento))\s+(?:risulta\s+essere\s+|[èe]\s+|il\s+|la\s+)?(?:Dott\.?|Dott\.?ssa|Sig\.?|Ing\.?|Arch\.?|Geom\.?)?\s*([A-Z][a-z]+(?:\s+[A-Z][a-z]+){1,3})\b')

        # Mappatura per numeri in lettere (Italiano)

        self.lettere_numeri = {
            'zero': 0, 'uno': 1, 'due': 2, 'tre': 3, 'quattro': 4, 'cinque': 5, 'sei': 6, 'sette': 7, 'otto': 8, 'nove': 9,
            'dieci': 10, 'undici': 11, 'dodici': 12, 'tredici': 13, 'quattordici': 14, 'quindici': 15, 'sedici': 16,
            'diciassette': 17, 'diciotto': 18, 'diciannove': 19, 'venti': 20, 'trenta': 30, 'quaranta': 40,
            'cinquanta': 50, 'sessanta': 60, 'settanta': 70, 'ottanta': 80, 'novanta': 90, 'cento': 100,
            'mille': 1000, 'mila': 1000, 'milione': 1000000, 'milioni': 1000000, 'miliardo': 1000000000
        }

    def clean_text(self, text: str) -> str:
        """Rimuove interruzioni di riga e doppi spazi per facilitare il regex matching."""
        if not text: return ""
        text = text.replace('\n', ' ').replace('\r', ' ')
        return re.sub(r'\s+', ' ', text)

    def _valida_partita_iva(self, piva: str) -> bool:
        if not piva or len(piva) != 11 or not piva.isdigit():
            return False
        s = 0
        for i in range(11):
            c = int(piva[i])
            if i % 2 != 0:
                c *= 2
                if c > 9:
                    c -= 9
            s += c
        return s % 10 == 0
        
    def _valida_iban(self, iban: str) -> bool:
        if not iban:
            return False
        iban = re.sub(r'\s+', '', iban).upper()
        return iban.startswith("IT") and len(iban) == 27

    def extract_entities(self, text: str) -> dict:
        if not isinstance(text, str):
            return {}
            
        cleaned_text = self.clean_text(text)
        anomalie = []
        
        cig_matches = self.cig_pattern.findall(cleaned_text)
        cig = cig_matches[0].upper() if cig_matches else None
        
        cup_matches = self.cup_pattern.findall(cleaned_text)
        cup = cup_matches[0].upper() if cup_matches else None
        
        # Miglioramento estrazione importi
        importi_matches = self.importo_pattern.findall(cleaned_text)
        importo_max = None
        if importi_matches:
            vals = []
            for imp in importi_matches:
                try:
                    # Rimuove spazi e gestisce formati 1.234,56 o 1234,56
                    s = imp.replace(' ', '').replace("'", "")
                    if ',' in s and '.' in s:
                        s = s.replace('.', '').replace(',', '.')
                    elif ',' in s:
                        s = s.replace(',', '.')
                    val = float(s)
                    if 0.01 < val < 1000000000: # Filtro rumore
                        vals.append(val)
                except: continue
            if vals: importo_max = max(vals)
            
        piva_matches = self.piva_pattern.findall(cleaned_text)
        piva = piva_matches[0] if piva_matches else None
        if piva and not self._valida_partita_iva(piva):
            anomalie.append(f"PIVA {piva} errata")

        iban_matches = self.iban_pattern.findall(cleaned_text)
        iban = re.sub(r'\s+', '', iban_matches[0]).upper() if iban_matches else None
        if iban and not self._valida_iban(iban):
            anomalie.append(f"IBAN {iban} errato")
            
        appalti_matches = self.appalti_pattern.findall(cleaned_text)
        codice_appalti = appalti_matches[0] if appalti_matches else None
        
        procedure = self.procedure_appalti_pattern.findall(cleaned_text)
        tipo_procedura = ", ".join(set(procedure)) if procedure else None

        # Nuovi campi AGID: Beneficiario, Capitolo, Impegno, RUP
        ben_matches = self.beneficiario_pattern.findall(cleaned_text)
        beneficiario = ben_matches[0].strip() if ben_matches else None

        cap_matches = self.capitolo_pattern.findall(cleaned_text)
        capitolo = cap_matches[0] if cap_matches else None

        imp_matches = self.impegno_pattern.findall(cleaned_text)
        impegno_num = imp_matches[0][0] if imp_matches else None
        impegno_anno = imp_matches[0][1] if imp_matches else None

        rup_matches = self.rup_pattern.findall(cleaned_text)
        rup = rup_matches[0].strip() if rup_matches else None

        return {
            "cig_estratto": cig,
            "cup_estratto": cup,
            "importo_max_estratto": importo_max,
            "piva_beneficiario": piva,
            "iban_estratto": iban,
            "codice_appalti": codice_appalti,
            "tipo_procedura": tipo_procedura,
            "beneficiario": beneficiario,
            "capitolo": capitolo,
            "impegno_num": impegno_num,
            "impegno_anno": impegno_anno,
            "responsabile": rup,
            "anomalie_rilevate": " | ".join(anomalie) if anomalie else None
        }
