import argparse
import pandas as pd
import re
from pathlib import Path
from datetime import timedelta

def normalizza_beneficiario(nome: str) -> str:
    if not isinstance(nome, str) or not nome.strip():
        return "NON IDENTIFICATO"
        
    nome = nome.upper().strip()
    
    # 1. Filtro falsi positivi burocratici aggiornato
    falsi_positivi = [
        "MAGGIORMENTE QUALIFICAT", "CHE HA PRESENTATO", "IN REGOLA", 
        "DIVERSI BENEFICIARI", "DIVERSE DITTE", "OPERATORE ECONOMICO",
        "APPALTATRICE", "AGGIUDICATARI", "DIVERSI", "IMPRESA"
    ]
    for fp in falsi_positivi:
        if fp in nome:
            return "DIVERSI/NON APPLICABILE"

    # 2. Rimozione di titoli e forme giuridiche per accorpare i nomi
    stopwords = [
        r'\bPROFESSIONISTA\b', r'\bDITTA\b', r'\bSOCIET[AÀ]\b', 
        r'\bS\.?R\.?L\.?S?\b', r'\bS\.?P\.?A\.?\b', r'\bS\.?N\.?C\.?\b', r'\bS\.?A\.?S\.?\b',
        r'\bAVV\.?\b', r'\bING\.?\b', r'\bARCH\.?\b', r'\bDOTT\.?(SSA)?\b', r'\bGEOM\.?\b'
    ]
    for sw in stopwords:
        nome = re.sub(sw, '', nome, flags=re.IGNORECASE)
    
    # 3. Pulizia finale da spazi multipli e punteggiatura
    nome = re.sub(r'[^\w\s]', ' ', nome) # Rimuove punteggiatura
    nome = re.sub(r'\s+', ' ', nome).strip()
    
    # Correzione specifica per refusi OCR ricorrenti nei tuoi dati
    if "IORO EMANUELA" in nome or "IORIO EMANUELA" in nome:
        return "IORIO EMANUELA"
        
    return nome if nome else "NON IDENTIFICATO"

def normalizza_rup(testo_rup: str) -> str:
    """Normalizza il nome del Responsabile del Procedimento (RUP)."""
    if not isinstance(testo_rup, str) or not testo_rup.strip():
        return "NON IDENTIFICATO"
    
    testo = testo_rup.upper().strip()
    
    # Filtro barriera: se contiene verbi o formule giuridiche, non è un nome
    formule_burocratiche = [
        "VISTO", "VISTI", "PREMESSO", "ACCERTATA", "SULLA BASE", 
        "DECRETO", "FUNZIONI", "AI SENSI", "COMPETENZA", "MUNICIPIO",
        "URBANISTICO", "REGOLAMENTO", "PROMOZIONE", "FINANZIARIA", "NAZIONALE", 
        "RIPRESA", "CENSIMENTO", "DIPENDENTE", "CONCESSO", "CHE CON", "PRO TEMPORE"
    ]
    if any(formula in testo for formula in formule_burocratiche):
        return "NON IDENTIFICATO"
        
    # Mappatura Organigramma (Fuzzy Matching per ricompattare i nodi)
    if "NISI" in testo: return "ELISABETTA NISI"
    if "MONTUORI" in testo: return "NICOLA MONTUORI"
    if "VITALE" in testo: return "ANDREA VITALE"
    
    # Pulizia generica per nomi non in lista
    testo = re.sub(r'^(DOTT\.?|SSA|IL RESPONSABILE|DEL SERVIZIO|COPIA PIAZZA.*)\s+', '', testo).strip()
    return testo if testo else "NON IDENTIFICATO"

def main():
    parser = argparse.ArgumentParser(description="Motore Antifrode: Rilevamento Frazionamento Appalti.")
    parser.add_argument("--base", default="albo_download", help="Cartella base dei dati.")
    args = parser.parse_args()

    base = Path(args.base)
    atti_path = base / "atti_parsed.csv"
    report_path = base / "report" / "alert_antifrode.md"

    if not atti_path.exists():
        print(f"File {atti_path} non trovato.")
        return

    df = pd.read_csv(atti_path)
    
    # Prepariamo i dati
    df['data_parsed'] = pd.to_datetime(df['data_atto'], format='%d/%m/%Y', errors='coerce')
    df['anno_solare'] = df['data_parsed'].dt.year
    df['importo'] = pd.to_numeric(df['importo_max'], errors='coerce').fillna(0.0)
    
    # 1. Applica la normalizzazione
    df['beneficiario_norm'] = df['beneficiario'].apply(normalizza_beneficiario)
    df['rup_norm'] = df['responsabile'].apply(normalizza_rup)

    # Filtriamo solo gli affidamenti diretti o sottosoglia
    df_appalti = df[
        df['tipo_procedura'].astype(str).str.contains('affidamento diretto|sotto soglia|art. 50', case=False, na=False) |
        (df['importo'] > 0)
    ].copy()

    # Filtra solo gli atti validi per l'analisi (escludi quelli non identificati o generici)
    df_analisi = df_appalti[df_appalti['beneficiario_norm'] != "DIVERSI/NON APPLICABILE"].copy()
    df_analisi = df_analisi[df_analisi['beneficiario_norm'] != "NON IDENTIFICATO"]
    df_analisi = df_analisi[df_analisi['rup_norm'] != "NON IDENTIFICATO"]

    alerts = []
    alerts.append("# 🚨 Report Antifrode: Rilevamento Anomalie Amministrative")
    alerts.append("Analisi automatizzata dei pattern comportamentali basata sui dati estratti.\n")

    # 1. RILEVAMENTO FRAZIONAMENTO ARTIFICIOSO DEGLI APPALTI
    alerts.append("## 1. Sospetto Frazionamento (Art. 50 D.Lgs 36/2023)")
    alerts.append("*Pattern: Più affidamenti diretti alla stessa ditta, dallo stesso RUP, sullo stesso Capitolo, nello stesso Anno Solare.* \n")

    # Raggruppiamo per Anno Solare, Capitolo, Beneficiario e RUP Normalizzati
    raggruppamento = df_analisi.groupby(['anno_solare', 'capitolo', 'beneficiario_norm', 'rup_norm'])
    
    found_frazionamento = False
    for (anno, capitolo, beneficiario, rup), gruppo in raggruppamento:
        if len(gruppo) > 1:
            found_frazionamento = True
            volume_totale = gruppo['importo'].sum()
            
            alerts.append(f"### 🔴 ALERT ROSSO: Possibile Frazionamento Anno {anno:.0f}")
            alerts.append(f"- **Beneficiario:** {beneficiario}")
            alerts.append(f"- **RUP:** {rup}")
            alerts.append(f"- **Capitolo di Bilancio:** {capitolo}")
            alerts.append(f"- **Numero Affidamenti:** {len(gruppo)}")
            alerts.append(f"- **Volume Totale Sospetto:** € {volume_totale:,.2f}")
            
            for _, row in gruppo.iterrows():
                alerts.append(f"  ↳ {row['doc_type']} n.{row['numero_atto']} del {row['data_atto']} (CIG: {row['cig']}) - € {row['importo']:,.2f}")
            alerts.append("")

    if not found_frazionamento:
        alerts.append("✅ *Nessun sospetto di frazionamento rilevato secondo i parametri impostati.*\n")

    # 2. SINDROME DELLA SOGLIA (Smurfing degli Appalti)
    alerts.append("## 2. Sindrome della Soglia (Smurfing)")
    alerts.append("*Pattern: Importi calibrati appena sotto le soglie di legge (€40.000 o €140.000) per eludere le procedure di gara.* \n")
    
    soglie_sospette = df_analisi[
        ((df_analisi['importo'] >= 39000) & (df_analisi['importo'] < 40000)) | 
        ((df_analisi['importo'] >= 135000) & (df_analisi['importo'] < 140000))
    ]
    
    if not soglie_sospette.empty:
        for _, row in soglie_sospette.iterrows():
            alerts.append(f"### 🟠 ALERT ARANCIO: Importo Borderline")
            alerts.append(f"- **Atto:** {row['doc_type']} n.{row['numero_atto']} del {row['data_atto']}")
            alerts.append(f"- **Beneficiario:** {row['beneficiario_norm']}")
            alerts.append(f"- **Importo:** € {row['importo']:,.2f} (Soglia elusa: {'40k' if row['importo'] < 40000 else '140k'})")
            alerts.append(f"- **RUP:** {row['rup_norm']}")
            alerts.append("")
    else:
        alerts.append("✅ *Nessun importo borderline rilevato nelle soglie critiche.*\n")

    # 3. CIG FANTASMA (Evasione della Tracciabilità)
    alerts.append("## 3. CIG Fantasma (Evasione Tracciabilità)")
    alerts.append("*Pattern: Atti classificati come Contabilità con importo > 0 ma privi di CIG valido.* \n")
    
    # Escludiamo spese esenti CIG per legge: utenze, personale, tributi, rimborsi, economato
    esclusioni_cig = r'utenze|energia|gas|acqua|telefonic|personale|stipendi|f24|irap|inps|inail|economo|anticipazione|imposte|tasse|indennit[aà]|rimbors[oi]|matrimonio|patrocinio|parere|pubblicazione'

    cig_fantasma = df[
        (df['category'] == 'Contabilità') & 
        (df['importo'] > 0) & 
        (df['cig'].isna() | (df['cig'].astype(str).str.contains('0000000000|DA ASSEGNARE|N/D', case=False, na=True))) &
        (~df['oggetto'].astype(str).str.contains(esclusioni_cig, case=False, na=False))
    ]
    
    if not cig_fantasma.empty:
        alerts.append(f"🔴 **ALERT ROSSO:** Rilevati **{len(cig_fantasma)}** atti contabili senza CIG tracciabile.")
        for _, row in cig_fantasma.iterrows():
            alerts.append(f"- ↳ Atto {row['numero_atto']} del {row['data_atto']} - **Importo: € {row['importo']:,.2f}**")
        alerts.append("")
    else:
        alerts.append("✅ *Tutti gli atti contabili presentano un CIG tracciabile.*\n")

    # 4. LA FEBBRE DI DICEMBRE (Anomalia Temporale)
    alerts.append("## 4. La Febbre di Dicembre (Anomalia Temporale)")
    alerts.append("*Pattern: Concentrazione anomala di impegni spesa nell'ultima quindicina dell'anno.* \n")
    
    if not df['data_parsed'].dropna().empty:
        df_valid_dates = df.dropna(subset=['data_parsed'])
        spesa_per_mese = df_valid_dates.groupby(df_valid_dates['data_parsed'].dt.month)['importo'].sum()
        spesa_totale_anno = spesa_per_mese.sum()
        
        if 12 in spesa_per_mese and spesa_totale_anno > 0:
            spesa_dicembre = spesa_per_mese[12]
            percentuale_dicembre = (spesa_dicembre / spesa_totale_anno) * 100
            
            alerts.append(f"### 🟡 ANALISI TEMPORALE: Impegni a Dicembre")
            alerts.append(f"- **Volume spesa Dicembre:** € {spesa_dicembre:,.2f}")
            alerts.append(f"- **Incidenza sul totale annuo:** {percentuale_dicembre:.1f}%")
            
            if percentuale_dicembre > 30:
                alerts.append("⚠️ **RISCHIO ELEVATO:** Oltre il 30% della spesa è concentrato a Dicembre. Possibili affidamenti frettolosi per esaurimento capitoli.")
            elif percentuale_dicembre > 20:
                alerts.append("ℹ️ **ATTENZIONE:** Concentrazione di spesa superiore alla media stagionale.")
        else:
            alerts.append("ℹ️ *Dati insufficienti per il calcolo della stagionalità della spesa.*")
    alerts.append("")

    # 5. RISCHIO ELUSIONE PRINCIPIO DI ROTAZIONE
    alerts.append("## 5. Rischio Elusione Principio di Rotazione")
    alerts.append("*Operatori economici che hanno ricevuto un numero anomalo di affidamenti diretti.* \n")
    
    affidamenti_diretti = df_analisi[df_analisi['tipo_procedura'].astype(str).str.contains('affidamento diretto', case=False, na=False)]
    conteggio_aff = affidamenti_diretti['beneficiario_norm'].value_counts()
    
    found_rotazione = False
    for ben, conteggio in conteggio_aff.items():
        if conteggio >= 4:  # Soglia di attenzione: 4 affidamenti diretti
            found_rotazione = True
            vol = affidamenti_diretti[affidamenti_diretti['beneficiario_norm'] == ben]['importo'].sum()
            alerts.append(f"- 🟡 **ALERT GIALLO:** La ditta `{ben}` ha ricevuto **{conteggio} affidamenti diretti**, per un volume complessivo di **€ {vol:,.2f}**.")
            
    if not found_rotazione:
        alerts.append("✅ *Nessuna violazione macroscopica del principio di rotazione rilevata.*\n")

    report_text = "\n".join(alerts)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)
        
    print(f"[OK] Report Antifrode generato: {report_path}")

if __name__ == "__main__":
    main()