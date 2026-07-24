import argparse
import pandas as pd
import networkx as nx
from pathlib import Path
import numpy as np
import re

def clean_node(name):
    """Clean node names for use in the graph by removing special characters and normalizing."""
    if pd.isna(name) or name is None:
        return None
    name = str(name).strip()
    if not name or name.lower() in ['nan', 'none', 'null', '']:
        return None
    
    # Remove special characters and normalize
    cleaned = re.sub(r'[^\w\s\-_]', '', name)
    cleaned = re.sub(r'\s+', '_', cleaned.strip())
    return cleaned if cleaned else None

def clean_attributes(attrs):
    """Remove None values from attributes dict to make it compatible with GEXF export."""
    return {k: v for k, v in attrs.items() if v is not None}

# Main execution
def main():
    parser = argparse.ArgumentParser(description='Build knowledge graph from parsed documents')
    parser.add_argument('--ente', required=True, help='Entity name (e.g., avella)')
    parser.add_argument('--base', help='Base directory for data files (optional, defaults to data/{ente}/albo_download)')
    args = parser.parse_args()
    
    # Setup paths
    if args.base:
        base = Path(args.base)
    else:
        base = Path(f"data/{args.ente}/albo_download")
    
    # Caricamento dati
    csv_path = base / "allegati_parsed.csv"
    if not csv_path.exists():
        print(f"❌ File non trovato: {csv_path}")
        return
    
    # Check if the file is empty before attempting to read it
    if csv_path.stat().st_size == 0:
        print(f"⚠️  File {csv_path} è vuoto, creazione di un DataFrame vuoto")
        df_atti = pd.DataFrame()
    else:
        try:
            df_atti = pd.read_csv(csv_path)
        except pd.errors.EmptyDataError:
            print(f"⚠️  File {csv_path} non contiene colonne valide, creazione di un DataFrame vuoto")
            df_atti = pd.DataFrame()
    
    if df_atti.empty:
        print(f"✅ Caricati 0 atti da {csv_path} (file vuoto)")
    else:
        df_atti['data_parsed'] = pd.to_datetime(df_atti['data_atto'], format='%Y-%m-%d', errors='coerce')
        print(f"✅ Caricati {len(df_atti)} atti da {csv_path}")
    
    # Costruzione grafo
    G = nx.DiGraph()
    
    # Check if DataFrame is empty before processing
    if df_atti.empty:
        print("⚠️  Nessun dato da elaborare, creazione di un grafo vuoto")
    else:
        # Per il grafo multi-ente, usiamo pdf_name o atto_group come ID
        for _, row in df_atti.iterrows():
            atto_id = clean_node(row.get('pdf_name'))
            if not atto_id: continue
            
            doc_type = clean_node(row.get('doc_type')) or "unknown"
            importo = float(row.get('importo_max', 0)) if pd.notna(row.get('importo_max')) else 0.0
            # Evitiamo importi folli boilerplate nel grafo
            if importo > 5000000: importo = 0 
            
            data_atto = str(row['data_parsed'].date()) if pd.notna(row['data_parsed']) else ""
            
            # Nodo Atto - puliamo gli attributi da valori None
            node_attrs = clean_attributes({
                'type': 'Atto', 
                'doc_type': doc_type, 
                'importo': importo, 
                'data': data_atto
            })
            G.add_node(atto_id, **node_attrs)
            
            # Nodo RUP
            rup = clean_node(row.get('responsabile'))
            if rup and rup != "NON IDENTIFICATO":
                # Arricchiamo il nodo RUP con i nuovi attributi, se non esiste già
                if not G.has_node(rup):
                    rup_attrs = clean_attributes({
                        'type': 'RUP', 
                        'area': row.get('rup_area'), 
                        'ruolo': row.get('rup_ruolo')
                    })
                    G.add_node(rup, **rup_attrs)
                G.add_edge(rup, atto_id, relation="FIRMA_O_GESTISCE")
                    
            # Nodo Beneficiario
            ben = clean_node(row.get('beneficiario'))
            if ben and ben != "NON IDENTIFICATO":
                G.add_node(ben, type="Beneficiario")
                rel = "LIQUIDA" if doc_type in ["Determinazione", "VistoContabile"] else "AFFIDA"
                edge_attrs = clean_attributes({'relation': rel, 'importo': importo})
                G.add_edge(atto_id, ben, **edge_attrs)
                    
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
    
    # Costruzione grafo
    G = nx.DiGraph()
    
    # Per il grafo multi-ente, usiamo pdf_name o atto_group come ID
    for _, row in df_atti.iterrows():
        atto_id = clean_node(row.get('pdf_name'))
        if not atto_id: continue
        
        doc_type = clean_node(row.get('doc_type')) or "unknown"
        importo = float(row.get('importo_max', 0)) if pd.notna(row.get('importo_max')) else 0.0
        # Evitiamo importi folli boilerplate nel grafo
        if importo > 5000000: importo = 0 
        
        data_atto = str(row['data_parsed'].date()) if pd.notna(row['data_parsed']) else ""
        
        # Nodo Atto - puliamo gli attributi da valori None
        node_attrs = clean_attributes({
            'type': 'Atto', 
            'doc_type': doc_type, 
            'importo': importo, 
            'data': data_atto
        })
        G.add_node(atto_id, **node_attrs)
        
        # Nodo RUP
        rup = clean_node(row.get('responsabile'))
        if rup and rup != "NON IDENTIFICATO":
            # Arricchiamo il nodo RUP con i nuovi attributi, se non esiste già
            if not G.has_node(rup):
                rup_attrs = clean_attributes({
                    'type': 'RUP', 
                    'area': row.get('rup_area'), 
                    'ruolo': row.get('rup_ruolo')
                })
                G.add_node(rup, **rup_attrs)
            G.add_edge(rup, atto_id, relation="FIRMA_O_GESTISCE")
                
        # Nodo Beneficiario
        ben = clean_node(row.get('beneficiario'))
        if ben and ben != "NON IDENTIFICATO":
            G.add_node(ben, type="Beneficiario")
            rel = "LIQUIDA" if doc_type in ["Determinazione", "VistoContabile"] else "AFFIDA"
            edge_attrs = clean_attributes({'relation': rel, 'importo': importo})
            G.add_edge(atto_id, ben, **edge_attrs)
                
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
    try:
        nx.write_gexf(G, str(gexf_path))
        print(f"✅ Grafo salvato in: {gexf_path} ({G.number_of_nodes()} nodi, {G.number_of_edges()} archi)")
    except Exception as e:
        print(f"❌ Errore durante il salvataggio del file GEXF: {e}")
        # Salvataggio alternativo in altri formati
        try:
            nx.write_graphml(G, str(report_dir / "knowledge_graph.graphml"))
            print(f"⚠️  Grafo salvato in formato alternativo: {report_dir / 'knowledge_graph.graphml'}")
        except Exception as e2:
            print(f"❌ Errore durante il salvataggio in formato alternativo: {e2}")

if __name__ == "__main__":
    main()