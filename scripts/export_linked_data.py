import argparse
import pandas as pd
from pathlib import Path
from rdflib import Graph, URIRef, Literal, Namespace
from rdflib.namespace import RDF, RDFS, XSD, DCTERMS
import json
import uuid
import os
from dotenv import load_dotenv

def main():
    parser = argparse.ArgumentParser(description="Esportazione Dati Albo in formato Linked Open Data (JSON-LD) secondo ontologie AGID.")
    parser.add_argument("--base", default="albo_download", help="Cartella base dei dati.")
    args = parser.parse_args()

    base = Path(args.base)
    atti_path = base / "atti_parsed.csv"
    report_dir = base / "report"
    report_dir.mkdir(exist_ok=True)
    
    out_jsonld = report_dir / "albo_linked_data.jsonld"

    if not atti_path.exists():
        print(f"File {atti_path} non trovato. Impossibile generare i LOD.")
        return

    df_atti = pd.read_csv(atti_path)

    # --- Definizione Spazi dei Nomi (Namespaces) OntoPiA / AGID ---
    COV = Namespace("https://w3id.org/italia/onto/COV/") 
    CPV = Namespace("https://w3id.org/italia/onto/CPV/") 
    TI = Namespace("https://w3id.org/italia/onto/TI/")   
    L0 = Namespace("https://w3id.org/italia/onto/l0/")   
    
    # Namespace dinamico per l'Ente configurato in .env
    load_dotenv()
    ente_uri_base = os.environ.get("ENTE_URI_LOD", "https://dati.comune.generic.it/resource/")
    ente_nome = os.environ.get("ENTE_NOME", "Comune Generico")
    ENTE = Namespace(ente_uri_base)

    g = Graph()
    g.bind("cov", COV)
    g.bind("cpv", CPV)
    g.bind("ti", TI)
    g.bind("l0", L0)
    g.bind("ente", ENTE)

    print("Conversione del dataset piatto in Linked Open Data (RDF)...")

    # Creazione del nodo Ente
    ente_clean_id = ''.join(e for e in ente_nome if e.isalnum())
    comune_uri = ENTE[ente_clean_id]
    g.add((comune_uri, RDF.type, COV.PublicOrganization))
    g.add((comune_uri, RDFS.label, Literal(ente_nome, lang="it")))

    count_atti = 0
    for _, row in df_atti.iterrows():
        if pd.isna(row['atto_group']): continue
        atto_id = str(row['atto_group']).strip()
        
        # URI dell'Atto
        atto_uri = ENTE[f"Atto/{atto_id}"]
        
        # L'atto è concettualmente un "Documento" e, se ha CIG, un "Contratto/Affidamento"
        g.add((atto_uri, RDF.type, L0.Document))
        g.add((atto_uri, RDFS.label, Literal(f"{row['doc_type']} n. {row.get('numero_atto', 'N/D')}", lang="it")))
        
        # --- LegalURN (NIR Standard) ---
        if pd.notna(row.get('legal_urn')):
            g.add((atto_uri, DCTERMS.identifier, Literal(str(row['legal_urn']))))

        # --- Stato Sottoscrizione ---
        if row.get('is_signed'):
            g.add((atto_uri, L0.description, Literal("Documento firmato digitalmente (PAdES/CAdES)", lang="it")))

        if pd.notna(row['oggetto']):
            g.add((atto_uri, DCTERMS.description, Literal(str(row['oggetto']).strip(), lang="it")))

        # --- Variabile Temporale (TI Ontology) ---
        if pd.notna(row['data_atto']):
            try:
                # Forza il formato ISO (YYYY-MM-DD) richiesto dallo standard XSD
                parsed_date = pd.to_datetime(row['data_atto'], format='%d/%m/%Y').strftime('%Y-%m-%d')
                
                # Creiamo un'entità tempo
                time_uri = ENTE[f"TimeEntity/{atto_id}"]
                g.add((time_uri, RDF.type, TI.TimeEntity))
                g.add((time_uri, TI.date, Literal(parsed_date, datatype=XSD.date)))
                g.add((atto_uri, TI.hasTimeEntity, time_uri))
            except Exception:
                pass # Salta se la data non è valida

        # --- Responsabile, Area e Ruolo (Ontologia COV/Org) ---
        # Compatibilità con nuove colonne o vecchia colonna 'responsabile'
        rup_name = None
        if pd.notna(row.get('rup_nome')):
            rup_name = str(row['rup_nome']).strip()
        elif pd.notna(row.get('responsabile')):
            rup_name = str(row['responsabile']).strip()

        if rup_name and rup_name != 'NON IDENTIFICATO':
            area_name = str(row.get('rup_area', row.get('ufficio', 'AREA NON SPECIFICATA'))).strip()
            ruolo_name = str(row.get('rup_ruolo', 'RESPONSABILE')).strip()

            # 1. Nodo Area (Settore/Ufficio)
            area_clean_id = ''.join(e for e in area_name if e.isalnum())
            area_uri = ENTE[f"Department/{area_clean_id}"]
            g.add((area_uri, RDF.type, COV.Organization)) 
            g.add((area_uri, RDFS.label, Literal(area_name, lang="it")))
            # Relazione Ente -> Area
            g.add((comune_uri, COV.hasSubOrganization, area_uri))

            # 2. Nodo Persona
            rup_clean_id = ''.join(e for e in rup_name if e.isalnum())
            rup_uri = ENTE[f"Person/{rup_clean_id}"]
            g.add((rup_uri, RDF.type, CPV.Person))
            g.add((rup_uri, RDFS.label, Literal(rup_name)))
            
            # Relazione Persona -> Area (Assegnazione)
            g.add((rup_uri, L0.description, Literal(f"{ruolo_name} presso {area_name}", lang="it")))
            g.add((area_uri, COV.hasMember, rup_uri))

            # 3. Relazione Persona -> Atto (Firma)
            g.add((atto_uri, COV.hasCreator, rup_uri))
            # Tag per analisi antifrode: tracciamo l'area di appartenenza del firmatario sull'atto
            g.add((atto_uri, L0.controlledVocabulary, Literal(f"Area_Firmataria:{area_name}")))

        # --- Sezione Appalti (CPV Ontology) ---
        cig_raw = str(row.get('cig', ''))
        if cig_raw and cig_raw != 'nan' and cig_raw != 'None':
            # Se ha un CIG, lo inquadriamo come Appalto/Contratto Pubblico
            g.add((atto_uri, RDF.type, CPV.Contract))
            
            cigs = [c.strip() for c in cig_raw.split(',') if c.strip()]
            for cig in cigs:
                g.add((atto_uri, CPV.hasCIG, Literal(cig)))

            # Importo dell'appalto
            if pd.notna(row.get('importo_max')) and row['importo_max'] > 0:
                g.add((atto_uri, CPV.contractAmount, Literal(float(row['importo_max']), datatype=XSD.decimal)))

            # Procedura
            if pd.notna(row.get('tipo_procedura')):
                proc_uri = ENTE[f"ProcedureType/{uuid.uuid4().hex[:8]}"]
                g.add((proc_uri, RDF.type, CPV.ProcedureType))
                g.add((proc_uri, RDFS.label, Literal(str(row['tipo_procedura']))))
                g.add((atto_uri, CPV.hasProcedureType, proc_uri))

        # --- Beneficiario / Operatore Economico ---
        ben_raw = str(row.get('beneficiario', ''))
        if ben_raw and ben_raw != 'nan' and ben_raw != 'None':
            bens = [b.strip() for b in ben_raw.split('|') if b.strip()]
            for ben in bens:
                ben_clean_id = ''.join(e for e in ben if e.isalnum())
                ben_uri = ENTE[f"Organization/{ben_clean_id}"]
                g.add((ben_uri, RDF.type, COV.Organization))
                g.add((ben_uri, RDFS.label, Literal(ben)))
                # Relazione: L'Ente stipula con il Beneficiario o lo definisce contraente
                g.add((atto_uri, CPV.hasContractor, ben_uri))
                
        count_atti += 1

    print(f"Generati RDF per {count_atti} Atti Amministrativi.")
    
    # Esportazione in JSON-LD
    print(f"Salvataggio in JSON-LD presso: {out_jsonld}")
    g.serialize(destination=str(out_jsonld), format='json-ld', indent=2)
    print("[OK] Linked Open Data pronti per la Piattaforma Digitale Nazionale (PDND).")

if __name__ == "__main__":
    main()
