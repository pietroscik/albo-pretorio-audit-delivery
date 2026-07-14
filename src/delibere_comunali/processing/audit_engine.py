import argparse
import pandas as pd
import numpy as np
import re
from pathlib import Path

class AuditEngine:
    def __init__(self, df: pd.DataFrame, feedback_base_path: Path = None):
        self.df = df.copy()
        self.feedback_base_path = feedback_base_path
        self._prepara_dati()
        # Applica il feedback supervisionato se disponibile
        if self.feedback_base_path:
            self._apply_supervised_feedback()

    def _apply_supervised_feedback(self):
        """
        Applica le correzioni supervisionate dal feedback_operatore.csv
        """
        feedback_path = self.feedback_base_path / "report" / "feedback_operatore.csv"
        if not feedback_path.exists():
            print(f"⚠️ File feedback_operatore.csv non trovato: {feedback_path}")
            return

        print(f"🔄 Applicazione feedback supervisionato da: {feedback_path}")
        try:
            # Legge il file di feedback con gestione delle strutture miste
            feedback_df = self._safe_read_csv_with_mixed_structure(feedback_path)
            if feedback_df.empty:
                print("⚠️ Nessun feedback da applicare")
                return

            corrections_applied = 0
            for _, row in feedback_df.iterrows():
                pdf_name = row['pdf_name']
                
                # Cerca corrispondenze parziali tra pdf_name e atto_group
                # Cerca in entrambi i sensi per gestire diversi formati
                mask = (
                    (self.df['atto_group'].str.contains(pdf_name.replace('.pdf', ''), case=False, na=False)) |
                    (pd.Series([pdf_name.replace('.pdf', '') in str(atto) for atto in self.df['atto_group']], dtype=bool))
                )
                
                if not mask.any():
                    # Se non troviamo corrispondenze dirette, prova una ricerca meno stretta
                    # Cerca parti del nome del file nel campo atto_group
                    pdf_parts = pdf_name.replace('.pdf', '').split('_')
                    if len(pdf_parts) > 1:
                        # Cerca le prime 2-3 parti del nome
                        search_term = '_'.join(pdf_parts[:3])  # Prendi le prime 3 parti
                        mask = self.df['atto_group'].str.contains(search_term, case=False, na=False)
                
                if mask.any():
                    structure_type = row['structure_type']
                    
                    if structure_type == 'new':
                        # Aggiorna tutti i campi corretti per la struttura nuova
                        if pd.notna(row.get('responsabile')) and str(row['responsabile']) != 'nan' and row['responsabile'] != '':
                            self.df.loc[mask, 'responsabile'] = row['responsabile']
                        
                        if pd.notna(row.get('beneficiario')) and str(row['beneficiario']) != 'nan' and row['beneficiario'] != '':
                            self.df.loc[mask, 'beneficiario'] = row['beneficiario']
                        
                        if pd.notna(row.get('cig')) and str(row['cig']) != 'nan' and row['cig'] != '':
                            self.df.loc[mask, 'cig'] = row['cig']
                        
                        if pd.notna(row.get('cup')) and str(row['cup']) != 'nan' and row['cup'] != '':
                            self.df.loc[mask, 'cup'] = row['cup']
                        
                        if pd.notna(row.get('importo_max')) and str(row['importo_max']) != 'nan' and row['importo_max'] != '':
                            self.df.loc[mask, 'importo_max'] = row['importo_max']
                        
                        if pd.notna(row.get('oggetto')) and str(row['oggetto']) != 'nan' and row['oggetto'] != '':
                            self.df.loc[mask, 'oggetto'] = row['oggetto']
                        
                        if pd.notna(row.get('category')) and str(row['category']) != 'nan' and row['category'] != '':
                            self.df.loc[mask, 'category'] = row['category']
                        
                        if pd.notna(row.get('data_atto')) and str(row['data_atto']) != 'nan' and row['data_atto'] != '':
                            self.df.loc[mask, 'data_atto'] = row['data_atto']
                        
                        if pd.notna(row.get('numero_atto')) and str(row['numero_atto']) != 'nan' and row['numero_atto'] != '':
                            self.df.loc[mask, 'numero_atto'] = row['numero_atto']
                            
                    elif structure_type == 'old':
                        # Aggiorna i campi disponibili per la struttura vecchia
                        if pd.notna(row.get('responsabile')) and str(row['responsabile']) != 'nan' and row['responsabile'] != '':
                            self.df.loc[mask, 'responsabile'] = row['responsabile']
                        
                        if pd.notna(row.get('beneficiario')) and str(row['beneficiario']) != 'nan' and row['beneficiario'] != '':
                            self.df.loc[mask, 'beneficiario'] = row['beneficiario']
                        
                        if pd.notna(row.get('category')) and str(row['category']) != 'nan' and row['category'] != '':
                            self.df.loc[mask, 'category'] = row['category']
                    
                    # Aggiorna le colonne normalizzate in base ai dati corretti
                    if 'beneficiario' in self.df.columns:
                        self.df.loc[mask, 'beneficiario_norm'] = self.df.loc[mask, 'beneficiario'].apply(self._normalizza_beneficiario)
                    if 'responsabile' in self.df.columns:
                        self.df.loc[mask, 'rup_norm'] = self.df.loc[mask, 'responsabile'].apply(self._normalizza_rup)
                    
                    corrections_applied += 1
                    print(f"✅ Aggiornati dati per {pdf_name} (trovato in {mask.sum()} record)")

            print(f"✅ Applicate {corrections_applied} correzioni supervisionate")
        except Exception as e:
            print(f"⚠️ Errore nell'applicazione del feedback supervisionato: {e}")

    def _safe_read_csv_with_mixed_structure(self, file_path):
        """
        Legge un file CSV che può contenere righe con strutture diverse (6 e 15 colonne)
        """
        import csv
        rows_6_fields = []
        rows_15_fields = []
        
        with open(file_path, 'r', encoding='utf-8') as f:
            reader = csv.reader(f)
            headers = next(reader)  # Salta l'header
            
            for row_num, row in enumerate(reader, start=2):  # Parti da 2 perché 1 è l'header
                if len(row) == 6:
                    # Struttura vecchia: pdf_name, responsabile, beneficiario, category, falso_positivo, timestamp
                    rows_6_fields.append({
                        'pdf_name': row[0],
                        'responsabile': row[1],
                        'beneficiario': row[2],
                        'category': row[3],
                        'falso_positivo': row[4],
                        'timestamp': row[5],
                        'structure_type': 'old'
                    })
                elif len(row) == 15:
                    # Struttura nuova: pdf_name, doc_type, responsabile, beneficiario, piva_beneficiario, 
                    # importo_max, cig, cup, data_atto, numero_atto, iban, oggetto, category, falso_positivo, timestamp
                    rows_15_fields.append({
                        'pdf_name': row[0],
                        'doc_type': row[1],
                        'responsabile': row[2],
                        'beneficiario': row[3],
                        'piva_beneficiario': row[4],
                        'importo_max': row[5],
                        'cig': row[6],
                        'cup': row[7],
                        'data_atto': row[8],
                        'numero_atto': row[9],
                        'iban': row[10],
                        'oggetto': row[11],
                        'category': row[12],
                        'falso_positivo': row[13],
                        'timestamp': row[14],
                        'structure_type': 'new'
                    })
                else:
                    print(f"⚠️ Riga {row_num} con {len(row)} campi ignorata: {row[:5]}...")
        
        # Converti in DataFrame
        df_6 = pd.DataFrame(rows_6_fields) if rows_6_fields else pd.DataFrame(columns=['structure_type'])
        df_15 = pd.DataFrame(rows_15_fields) if rows_15_fields else pd.DataFrame(columns=['structure_type'])
        
        # Combina i DataFrame
        if df_6.empty and df_15.empty:
            return pd.DataFrame()
        elif df_6.empty:
            return df_15
        elif df_15.empty:
            return df_6
        else:
            combined_df = pd.concat([df_6, df_15], ignore_index=True)
            return combined_df

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
        # Gestisce la data_atto che potrebbe non esistere
        if 'data_atto' in self.df.columns:
            self.df['data_parsed'] = pd.to_datetime(self.df['data_atto'], format='%d/%m/%Y', errors='coerce')
            self.df['anno_solare'] = self.df['data_parsed'].dt.year
            self.df['mese'] = self.df['data_parsed'].dt.month
        else:
            self.df['data_parsed'] = pd.NaT
            self.df['anno_solare'] = np.nan
            self.df['mese'] = np.nan
            
        self.df['importo_clean'] = pd.to_numeric(self.df['importo_max'], errors='coerce').fillna(0.0)
        
        # Normalizza i beneficiari e i responsabili
        if 'beneficiario' in self.df.columns:
            self.df['beneficiario_norm'] = self.df['beneficiario'].apply(self._normalizza_beneficiario)
        else:
            self.df['beneficiario_norm'] = "NON IDENTIFICATO"
            
        if 'rup_nome' in self.df.columns:
            self.df['rup_norm'] = self.df['rup_nome'].fillna(self.df['responsabile']).apply(self._normalizza_rup)
        elif 'responsabile' in self.df.columns:
            self.df['rup_norm'] = self.df['responsabile'].apply(self._normalizza_rup)
        else:
            self.df['rup_norm'] = "NON IDENTIFICATO"
        
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
        if 'tipo_procedura' not in self.df.columns:
            return  # Esci se la colonna non esiste
            
        affidamenti = self.df[self.df['tipo_procedura'].astype(str).str.contains('affidamento diretto|sotto soglia|art. 50', case=False, na=False)]
        selezionati = affidamenti[~affidamenti['beneficiario_norm'].isin(['DIVERSI/NON APPLICABILE', 'NON IDENTIFICATO'])]
        
        conteggi = selezionati['beneficiario_norm'].value_counts()
        if len(conteggi) >= 2:
            mean_aff = conteggi.mean()
            std_aff = conteggi.std()
            
            if std_aff > 0:
                # Anomalia se supera 2 deviazioni standard
                soglia_dinamica = mean_aff + (2 * std_aff)
            else:
                # Dataset troppo piccolo per Z-Score: fallback a soglia fissa (>= 3 affidamenti)
                soglia_dinamica = max(mean_aff, 3) - 1
            
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
        if 'category' in self.df.columns:
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
    parser.add_argument("--ente", default=None, help="Identificativo ente (opzionale)")
    parser.add_argument("--use-llm", action="store_true", help="Abilita arricchimento LLM (opzionale)")
    parser.add_argument("--llm-provider", default=None, help="Provider LLM (openai, gemini, mistral...)")
    parser.add_argument("--llm-model", default=None, help="Modello LLM da usare")
    args = parser.parse_args()

    base = Path(args.base)
    
    # Se --ente specificato e --base è il default, aggiusta il path
    if args.ente and args.base == "data/baiano/albo_download":
        base = Path(f"data/{args.ente}/albo_download")

    atti_path = base / "atti_parsed.csv"
    output_path = base / "atti_audited.csv"

    if not atti_path.exists():
        print(f"❌ File {atti_path} non trovato.")
        return

    print("🚀 Avvio Motore Audit Dinamico...")
    if args.use_llm:
        print(f"   LLM: {args.llm_provider or 'default'} / {args.llm_model or 'default'}")

    df = pd.read_csv(atti_path)

    # Passa il percorso base per permettere la lettura del feedback supervisionato
    engine = AuditEngine(df, feedback_base_path=base)
    df_audited = engine.run_audit()

    df_audited.to_csv(output_path, index=False)

    anomalie = df_audited[df_audited['risk_score'] > 0]
    print(f"✅ Audit completato. Identificati {len(anomalie)} atti con anomalie su {len(df)}.")
    print(f"💾 Dataset di audit salvato in: {output_path}")

if __name__ == "__main__":
    main()