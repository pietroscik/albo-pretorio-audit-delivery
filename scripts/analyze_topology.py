import argparse
import networkx as nx
import pandas as pd
from pathlib import Path
import sys
import logging
import re

# Aggiungi il percorso alla root del progetto per importare i moduli da src
sys.path.append(str(Path(__file__).resolve().parents[1]))

from src.delibere_comunali.utils.config import get_tenant_dir

logger = logging.getLogger("analyze_topology")
logging.basicConfig(level=logging.INFO)

def _normalizza_rup(nome_rup: str) -> str:
    """Normalizza i nomi dei RUP rimuovendo appellativi e formule burocratiche"""
    if not isinstance(nome_rup, str) or not nome_rup.strip():
        return "NON IDENTIFICATO"
    
    nome = nome_rup.upper().strip()
    
    # Rimuovi formule burocratiche
    formule_burocratiche = ["VISTO", "VISTI", "PREMESSO", "ACCERTATA", "SULLA BASE", "DECRETO", 
                           "FUNZIONI ATTRIBUITE", "AI SENSI", "IL RESPONSABILE", "DEL SERVIZIO", 
                           "COPIA PIAZZA", "F.TO", "FIRMA", "TIMBRO"]
    if any(formula in nome for formula in formule_burocratiche):
        return "NON IDENTIFICATO"
    
    # Rimuovi appellativi e titoli professionali
    nome = re.sub(r'^(DOTT\.?|ARCH\.?|ING\.?|GEOM\.?|AVV\.?|SSA|DR\.?|DOTT\.SSA|DR\.SSA)\s*', '', nome).strip()
    nome = re.sub(r'\b(DOTT\.?|ARCH\.?|ING\.?|GEOM\.?|AVV\.?|SSA|DR\.?|DOTT\.SSA|DR\.SSA)\b', '', nome).strip()
    
    # Rimuovi parole comuni che non fanno parte del nome
    nome = re.sub(r'\b(DEL|DELLA|DEI|DELL|DI|E|LA|IL|LO|LE|GLI|I|UN|UNA|PER|SU|DA|CON|SE|NON|MA|O|COME|A|IN|CONTRAENTE|RESPONSABILE)\b', ' ', nome)
    
    # Rimuovi caratteri speciali e comprimi spazi multipli
    nome = re.sub(r'[^\w\s]', ' ', nome)
    nome = re.sub(r'\s+', ' ', nome).strip()
    
    return nome if nome else "NON IDENTIFICATO"

def main():
    parser = argparse.ArgumentParser(description="Analisi Topologica del Knowledge Graph degli Appalti.")
    parser.add_argument("--ente", required=True, help="Nome dell'ente da analizzare (es. avella).")
    parser.add_argument("--top-k", type=int, default=15, help="Numero di risultati da mostrare nelle top classifiche.")
    args = parser.parse_args()

    base = get_tenant_dir(args.ente)
    gexf_path = base / "report" / "knowledge_graph.gexf"
    report_path = base / "report" / "topological_insights.txt"

    if not gexf_path.exists():
        print(f"Errore: File {gexf_path} non trovato. Genera prima il Knowledge Graph.")
        return

    print("Caricamento del Knowledge Graph in memoria...")
    try:
        G = nx.read_gexf(str(gexf_path))
    except ValueError as e:
        logger.warning(f"GEXF corrotto ({e}), ricostruisco da CSV...")
        csv_path = gexf_path.parent / "allegati_parsed.csv"
        if not csv_path.exists():
            print(f"❌ Nessun CSV trovato in {csv_path}")
            sys.exit(1)
        df = pd.read_csv(csv_path)
        G = nx.DiGraph()
        for _, row in df.iterrows():
            src = str(row.get("responsabile", "unknown"))
            dst = str(row.get("oggetto", "unknown"))[:60]
            G.add_edge(src, dst)

    # Molti algoritmi di centralità richiedono grafi semplici (non multigraph).
    # Riduciamo il MultiDiGraph a un DiGraph per il calcolo delle metriche di base.
    G_simple = nx.DiGraph(G)

    print(f"Grafo caricato: {G_simple.number_of_nodes()} nodi, {G_simple.number_of_edges()} archi.")
    print("Calcolo delle metriche di centralità in corso...\n")

    # 1. Degree Centrality (Centralità di Grado)
    # Misura il numero di connessioni (archi entranti o uscenti) proporzionato alla rete.
    # Utile per trovare chi "muove" o "riceve" più atti.
    degree_cent = nx.degree_centrality(G_simple)
    
    # 2. In-Degree Centrality (Centralità in ingresso)
    # Misura chi riceve più collegamenti. 
    # Per i Beneficiari, indica quanti atti "puntano" a loro (LIQUIDA/AFFIDA).
    in_degree_cent = nx.in_degree_centrality(G_simple)

    # Separiamo i nodi per tipo
    beneficiari = {n: d for n, d in G_simple.nodes(data=True) if d.get('type') == 'Beneficiario'}
    rups = {n: d for n, d in G_simple.nodes(data=True) if d.get('type') == 'RUP'}
    capitoli = {n: d for n, d in G_simple.nodes(data=True) if d.get('type') == 'Capitolo'}

    insights = []
    insights.append("="*60)
    insights.append("REPORT ANALISI TOPOLOGICA - CENTRI DI CONCENTRAZIONE")
    insights.append("="*60 + "\n")

    # --- TOP BENEFICIARI (Per Numero di Relazioni in Ingresso) ---
    insights.append(f"--- I TOP {args.top_k} OPERATORI ECONOMICI (BENEFICIARI) ---")
    insights.append("Basato sul numero di atti che puntano a loro (In-Degree Centrality). Segnala potenziali concentrazioni di affidamenti.")
    ben_ranked = sorted(beneficiari.keys(), key=lambda x: in_degree_cent[x], reverse=True)
    
    for i, ben_id in enumerate(ben_ranked[:args.top_k], 1):
        # Calcoliamo il numero esatto di archi entranti
        in_edges = G_simple.in_edges(ben_id, data=True)
        num_affidamenti = len(in_edges)
        
        # Stimiamo il volume d'affari sommando l'attributo 'importo' degli archi entranti (se presente)
        volume_affari = 0.0
        # Dobbiamo tornare al MultiDiGraph originale per sommare tutti i pesi se c'erano archi multipli
        for u, v, data in G.in_edges(ben_id, data=True):
             volume_affari += float(data.get('importo', 0.0) or 0.0)

        # Ripuliamo il nome per la visualizzazione
        display_name = str(ben_id).strip()
        
        insights.append(f"{i:2d}. {display_name[:45]:<45} | Atti: {num_affidamenti:<3} | Volume stimato: € {volume_affari:,.2f}")

    insights.append("\n" + "="*60 + "\n")

    # --- TOP RUP (Per Numero di Relazioni Uscenti) ---
    # Per i RUP calcoliamo l'Out-Degree (quanti atti fanno partire/firmano)
    out_degree_cent = nx.out_degree_centrality(G_simple)
    insights.append(f"--- I TOP {args.top_k} RUP (RESPONSABILI DEL PROCEDIMENTO) ---")
    insights.append("Basato sul numero di atti collegati e gestiti.")
    rup_ranked = sorted(rups.keys(), key=lambda x: out_degree_cent[x], reverse=True)
    
    for i, rup_id in enumerate(rup_ranked[:args.top_k], 1):
        out_edges = G_simple.out_edges(rup_id)
        num_atti_gestiti = len(out_edges)
        # Normalizziamo il nome del RUP rimuovendo appellativi
        normalized_name = _normalizza_rup(str(rup_id))
        insights.append(f"{i:2d}. {normalized_name[:45]:<45} | Atti Gestiti: {num_atti_gestiti}")

    insights.append("\n" + "="*60 + "\n")

    # --- TOP CAPITOLI DI BILANCIO ---
    insights.append(f"--- I TOP {args.top_k} CAPITOLI DI SPESA PIU' SOLLECITATI ---")
    cap_ranked = sorted(capitoli.keys(), key=lambda x: in_degree_cent[x], reverse=True)
    
    for i, cap_id in enumerate(cap_ranked[:args.top_k], 1):
        in_edges = G_simple.in_edges(cap_id)
        num_atti = len(in_edges)
        label = capitoli[cap_id].get('label', str(cap_id))
        insights.append(f"{i:2d}. Capitolo {label:<36} | Atti Incidenti: {num_atti}")

    # Stampa a video
    report_text = "\n".join(insights)
    print(report_text)

    # Salvataggio su file
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_text)
    
    print(f"\n[OK] Report dettagliato salvato in: {report_path}")

if __name__ == "__main__":
    main()