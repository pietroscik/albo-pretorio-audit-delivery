import argparse
import pandas as pd
import numpy as np
import re
from pathlib import Path

class AuditEngine:
    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()
        self._prepara_dati()

    def _normalizza_beneficiario(self, nome: str) -> str:
        if not isinstance(nome, str) or not nome.strip(): return "NON IDENTIFICATO"
        nome = nome.upper().strip()
        falsi_positivi = ["MAGGIORMENTE QUALIFICAT", "CHE HA PRESENTATO", "IN REGOLA", "DIVERSI BENEFICIARI", "DIVERSE DITTE", "OPERATORE ECONOMICO", "APPALTATRICE", "AGGIUDICATARI", "DIVERSI", "IMPRESA"]
        if any(fp in nome for fp in falsi_positivi): return "DIVERSI/NON APPLICABILE"
        stopwords = [r'\bPROFESSIONISTA\b', r'\bDITTA\b', r'\bSOCIET[AÀ]\b', r'\bS\.?R\.?L\.?S?\b', r'\bS\.?P\.?A\.?\b', r'\bS\.?N\.?C\.?\b', r'\bS\.?A\.?S\.?\b', r'\bAVV\.?\b', r'\bING\.?\b', r'\bARCH\.?\b', r'\bDOTT\.?(SSA)?\b', r'\bGEOM\.?\b']
        for sw in stopwords: nome = re.sub(sw, '', nome, flags=re.IGNORECASE)
        nome = re.sub(r'[^\w\s]', ' ', nome)
        nome = re.sub(r'\s+', ' ', nome).strip()
        if "IORO EMANUELA" in nome or "IORIO EMANUELA" in nome: return "IORIO EMANUELA"
        return nome if nome else "NON IDENTIFICATO"

    def _normalizza_rup(self, testo_rup: str) -> str:
        if not isinstance(testo_rup, str) or not testo_rup.strip(): return "NON IDENTIFICATO"
        testo = testo_rup.upper().strip()
        formule_burocratiche = ["VISTO", "VISTI", "PREMESSO", "ACCERTATA", "SULLA BASE", "DECRETO", "FUNZIONI ATTRIBUITE", "AI SENSI"]
        if any(formula in testo for formula in formule_burocratiche): return "NON IDENTIFICATO"
        testo = re.sub(r'^(DOTT\.?|SSA|IL RESPONSABILE|DEL SERVIZIO|COPIA PIAZZA.*)\s+', '', testo).strip()
        return testo if testo else "NON IDENTIFICATO"

    def _prepara_dati(self):
        """Prepara il dataset e inizializza le colonne di scoring"""
        self.df['data_parsed'] = pd.to_datetime(self.df['data_atto'], format='%d/%m/%Y', errors='coerce')
        self.df['anno_solare'] = self.df['data_parsed'].dt.year
        self.df['mese'] = self.df['data_parsed'].dt.month
        self.df['importo_clean'] = pd.to_numeric(self.df['importo_max'], errors='coerce').fillna(0.0)
        
        self.df['beneficiario_norm'] = self.df['beneficiario'].apply(self._normalizza_beneficiario)
        if 'rup_nome' in self.df.columns:
            self.df['rup_norm'] = self.df['rup_nome'].fillna(self.df['responsabile']).apply(self._normalizza_rup)
        else:
            self.df['rup_norm'] = self.df['responsabile'].apply(self._normalizza_rup)
        
        # INIZIALIZZAZIONE TELEMETRIA (Nuove colonne per la Dashboard)
        self.df['risk_score'] = 0.0
        self.df['anomalie_rilevate'] = ""

    def _add_anomaly(self, mask: pd.Series, score_penalty: float, flag_name: str):
        """Aggiunge punteggio di rischio e stringa di anomalia in modo vettorializzato"""
        self.df.loc[mask, 'risk_score'] += score_penalty
        
        current_flags = self.df.loc[mask, 'anomalie_rilevate'].astype(str)
        self.df.loc[mask, 'anomalie_rilevate'] = np.where(
            current_flags == "", 
            flag_name, 
            current_flags + " | " + flag_name
        )

    def valuta_rotazione_dinamica(self):
        """Sostituisce il limite fisso (>=4) con il calcolo Z-Score"""
        affidamenti = self.df[self.df['tipo_procedura'].astype(str).str.contains('affidamento diretto|sotto soglia|art. 50', case=False, na=False)]
        selezionati = affidamenti[~affidamenti['beneficiario_norm'].isin(['DIVERSI/NON APPLICABILE', 'NON IDENTIFICATO'])]
        
        conteggi = selezionati['beneficiario_norm'].value_counts()
        if len(conteggi) > 2:
            mean_aff = conteggi.mean()
            std_aff = conteggi.std()
            soglia_dinamica = mean_aff + (2 * std_aff) # Anomalia se supera 2 deviazioni standard
            
            beneficiari_anomali = conteggi[conteggi > soglia_dinamica].index
            mask = self.df['beneficiario_norm'].isin(beneficiari_anomali) & self.df['tipo_procedura'].astype(str).str.contains('affidamento', case=False, na=False)
            self._add_anomaly(mask, 35.0, "Rotazione Statistica Anomala")

    def valuta_smurfing(self):
        """Sindrome della soglia (Borderline 40k / 140k)"""
        mask_40k = (self.df['importo_clean'] >= 39000) & (self.df['importo_clean'] < 40000)
        mask_140k = (self.df['importo_clean'] >= 135000) & (self.df['importo_clean'] < 140000)
        self._add_anomaly(mask_40k | mask_140k, 50.0, "Smurfing (Importo Borderline)")

    def valuta_cig_fantasma(self):
        """Evasione Tracciabilità"""
        mask_no_cig = (
            (self.df['category'] == 'Contabilità') & 
            (self.df['importo_clean'] > 0) & 
            (self.df['cig'].isna() | self.df['cig'].astype(str).str.contains('0000|DA ASSEGNARE|N/D', na=True))
        )
        self._add_anomaly(mask_no_cig, 40.0, "CIG Fantasma (Spesa non tracciata)")

    def valuta_febbre_dicembre_dinamica(self):
        """Calcola la stagionalità dinamica per mese (Z-Score mensile) invece del 30% fisso"""
        if self.df['mese'].notna().sum() > 0:
            spesa_mensile = self.df.groupby('mese')['importo_clean'].sum()
            mean_spesa = spesa_mensile.mean()
            std_spesa = spesa_mensile.std()
            
            if std_spesa > 0 and 12 in spesa_mensile.index:
                # Se Dicembre supera la media mensile di 1.5 deviazioni standard
                if spesa_mensile[12] > (mean_spesa + 1.5 * std_spesa):
                    mask_dicembre = (self.df['mese'] == 12) & (self.df['importo_clean'] > 0)
                    self._add_anomaly(mask_dicembre, 25.0, "Febbre di Dicembre (Picco Spesa)")

    def run_audit(self) -> pd.DataFrame:
        """Esegue la pipeline di scoring"""
        self.valuta_rotazione_dinamica()
        self.valuta_smurfing()
        self.valuta_cig_fantasma()
        self.valuta_febbre_dicembre_dinamica()
        
        # Normalizza lo score a un massimo di 100
        self.df['risk_score'] = self.df['risk_score'].clip(upper=100.0)
        
        # Ordina per rischio decrescente
        self.df = self.df.sort_values(by='risk_score', ascending=False)
        return self.df

def main():
    parser = argparse.ArgumentParser(description="Motore Antifrode: Scoring Dinamico")
    parser.add_argument("--base", default="data/baiano/albo_download", help="Cartella base dei dati.")
    args = parser.parse_args()

    base = Path(args.base)
    atti_path = base / "atti_parsed.csv"
    output_path = base / "atti_audited.csv"

    if not atti_path.exists():
        print(f"❌ File {atti_path} non trovato.")
        return

    print("🚀 Avvio Motore Audit Dinamico...")
    df = pd.read_csv(atti_path)
    
    engine = AuditEngine(df)
    df_audited = engine.run_audit()
    
    # Salva il dataset arricchito per la Dashboard
    df_audited.to_csv(output_path, index=False)
    
    anomalie = df_audited[df_audited['risk_score'] > 0]
    print(f"✅ Audit completato. Identificati {len(anomalie)} atti con anomalie su {len(df)}.")
    print(f"💾 Dataset di audit salvato in: {output_path}")

if __name__ == "__main__":
    main()