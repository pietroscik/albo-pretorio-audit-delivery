import argparse
import pandas as pd
import networkx as nx
from pathlib import Path
from dateutil import parser
import json
try:
    from pyvis.network import Network
except ModuleNotFoundError as exc:
    raise SystemExit(
        "Missing dependency 'pyvis'. Install with: pip install pyvis"
    ) from exc

def clean_node(val):
    if pd.isna(val): return None
    v = str(val).strip()
    return v if v else None

def save_interactive_graph(G, output_path):
    """Genera una versione HTML interattiva del grafo utilizzando PyVis."""
    net = Network(height="750px", width="100%", bgcolor="#ffffff", font_color="#000000", directed=True)
    
    # Mappa colori per tipo nodo
    color_map = {
        "Atto": "#1E3A8A",      # Blu scuro
        "RUP": "#10B981",       # Verde
        "Beneficiario": "#F59E0B", # Arancione
        "Capitolo": "#6366F1",  # Viola
        "CIG": "#EF4444"        # Rosso
    }
    
    for node, attrs in G.nodes(data=True):
        label = str(node)
        if attrs.get('type') == 'Atto':
            label = f"Atto: {attrs.get('doc_type', 'N/D')}\n€{attrs.get('importo', 0):,.2f}"
        
        net.add_node(node, label=label, title=label, color=color_map.get(attrs.get('type'), "#999999"))
        
    for source, target, data in G.edges(data=True):
        net.add_edge(source, target, title=data.get('relation', ''))
        
    net.toggle_physics(True)
    net.save_graph(str(output_path))

def main():
    parser_arg = argparse.ArgumentParser()
    parser_arg.add_argument("--base", default="albo_download")
    args = parser_arg.parse_args()
    
    base = Path(args.base)
    # Preferiamo allegati_parsed.csv che è quello arricchito dall'LLM
    atti_path = base / "allegati_parsed.csv"
    if not atti_path.exists():
        atti_path = base / "atti_parsed.csv"
    
    if not atti_path.exists():
        print(f"File {atti_path} non trovato. Impossibile costruire il grafo.")
        return
        
    df_atti = pd.read_csv(atti_path)
    
    # Conversione data
    df_atti['data_parsed'] = pd.to_datetime(df_atti['data_atto'], format='%d/%m/%Y', errors='coerce')
    df_atti = df_atti.sort_values(by='data_parsed', na_position='last')
    
    G = nx.MultiDiGraph()
    cig_timeline = {}
    
    # Per il grafo multi-ente, usiamo pdf_name o atto_group come ID
    for _, row in df_atti.iterrows():
        atto_id = clean_node(row.get('pdf_name'))
        if not atto_id: continue
        
        doc_type = clean_node(row.get('doc_type')) or "unknown"
        importo = float(row.get('importo_max', 0)) if pd.notna(row.get('importo_max')) else 0.0
        # Evitiamo importi folli boilerplate nel grafo
        if importo > 5000000: importo = 0 
        
        data_atto = str(row['data_parsed'].date()) if pd.notna(row['data_parsed']) else ""
        
        # Nodo Atto
        G.add_node(atto_id, type="Atto", doc_type=doc_type, importo=importo, data=data_atto)
        
        # Nodo RUP
        rup = clean_node(row.get('responsabile'))
        if rup and rup != "NON IDENTIFICATO":
            # Arricchiamo il nodo RUP con i nuovi attributi, se non esiste già
            if not G.has_node(rup):
                G.add_node(rup, type="RUP", area=row.get('rup_area'), ruolo=row.get('rup_ruolo'))
            G.add_edge(rup, atto_id, relation="FIRMA_O_GESTISCE")
                
        # Nodo Beneficiario
        ben = clean_node(row.get('beneficiario'))
        if ben and ben != "NON IDENTIFICATO":
            G.add_node(ben, type="Beneficiario")
            rel = "LIQUIDA" if doc_type in ["Determinazione", "VistoContabile"] else "AFFIDA"
            G.add_edge(atto_id, ben, relation=rel, importo=importo)
                
        # Nodo CIG
        cig = clean_node(row.get('cig'))
        if cig:
            G.add_node(cig, type="CIG")
            G.add_edge(atto_id, cig, relation="RIFERISCE_A")
            
        # Nodo Capitolo
        capitolo = clean_node(row.get('capitolo'))
        if capitolo and str(capitolo).upper() not in ["NON IDENTIFICATO", "NONE", "NAN"]:
            G.add_node(capitolo, type="Capitolo", label=str(capitolo))
            G.add_edge(atto_id, capitolo, relation="GRAVA_SU")

    # Esportazione
    report_dir = base / "report"
    report_dir.mkdir(exist_ok=True)
    
    gexf_path = report_dir / "knowledge_graph.gexf"
    nx.write_gexf(G, str(gexf_path))
    
    html_path = report_dir / "knowledge_graph.html"
    try:
        save_interactive_graph(G, html_path)
        print(f"✅ Grafo interattivo salvato in: {html_path}")
    except Exception as e:
        print(f"❌ Errore generazione HTML grafo: {e}")

if __name__ == "__main__":
    main()
