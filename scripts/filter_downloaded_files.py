#!/usr/bin/env python3
"""
Script per filtrare i file scaricati dallo scraper che non sono veri allegati.
Questo modulo identifica e rimuove i file introduttivi scaricati erroneamente dallo scraper.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
import argparse
import re
from typing import List, Dict
import os

# Importa la funzione get_tenant_dir per supportare il sistema multi-tenant
from delibere_comunali.utils.config import get_tenant_dir

# Configura il logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def analyze_file_content(file_path: Path) -> Dict:
    """
    Analizza il contenuto di un file PDF per determinare se è un vero allegato o una pagina introduttiva.
    """
    try:
        import PyPDF2
        with open(file_path, 'rb') as f:
            try:
                pdf_reader = PyPDF2.PdfReader(f)
            except Exception as e:
                logger.warning(f"Impossibile leggere il PDF {file_path}: {e}")
                # Se non possiamo leggere il PDF, procediamo con l'analisi del nome del file
                pdf_reader = None
            
            if pdf_reader is None:
                # Fall back all'analisi del nome del file
                pass
            elif len(pdf_reader.pages) == 0:
                return {"is_attachment": False, "reason": "empty_pdf"}
            else:
                # Leggi le prime pagine per analisi (leggiamo più pagine per identificare file introduttivi)
                text_content = ""
                for i in range(min(3, len(pdf_reader.pages))):  # Leggi max 3 pagine
                    try:
                        page_text = pdf_reader.pages[i].extract_text()
                        text_content += page_text
                    except Exception as e:
                        logger.warning(f"Impossibile estrarre testo dalla pagina {i} del PDF {file_path}: {e}")
                        # Continua con le altre pagine o usa quanto estratto finora
                        continue
                
                text_lower = text_content.lower()
            
            # Cerca indicatori di file che NON sono introduttivi (documenti effettivi)
            # Questi sono documenti specifici che devono essere mantenuti
            non_intro_indicators = [
                "avviso di appalto aggiudicato", "convocazione consiglio", "convocazione del consiglio",
                "avviso di gara", "bando di gara", "aggiudicazione", "graduatoria", "contratto",
                "convenzione", "progetto definitivo", "progetto esecutivo", "collaudo", 
                "direzione lavori", "certificato di regolarità contributiva", "relazione di controllo",
                "parere del collegio sindacale", "atto di rettifica", "verifica di regolarità amministrativa",
                "verbale", "protocollo", "allegato", "documento", "tabelle", "elenco", "quadro",
                "cronoprogramma", "computo", "pianta", "progetto", "relazione", "calcolo",
                "preventivo", "stima", "metrico", "grafico", "foto", "immagine", "planimetria",
                "scheda tecnica", "specifiche tecniche", "capitolato", "disciplinare",
                "relazione geologica", "relazione geotecnica", "relazione strutturale",
                "relazione ambientale", "relazione economica", "quadro economico",
                "cronogramma fisico", "cronogramma finanziario", "scheda attività",
                "scheda intervento", "scheda progetto", "scheda opera", "scheda servizio",
                "scheda quadro", "scheda illustrativa", "scheda descrittiva",
                "scheda allegata", "scheda tecnica allegata", "scheda progettuale",
                "elenco prezzi", "elenco forniture", "elenco attrezzature", "elenco materiali",
                "elenco personale", "elenco documenti", "elenco allegati", "elenco tavole",
                "tavola", "pianta", "prospetto", "sezione", "particolare", "dettaglio",
                "modulo", "modello", "schema", "diagramma", "flusso", "organigramma",
                "matrice", "tabella", "quadro sinottico", "situazione", "stato di fatto",
                "stato di progetto", "stato di attuazione", "stato di avanzamento",
                "scheda rilievo", "scheda ispezione", "scheda verifica", "scheda controllo",
                "scheda monitoraggio", "scheda valutazione", "scheda analisi", "scheda osservazione",
                "computo metrico", "quadro economico", "cronoprogramma", "piano esecutivo",
                "piano di sicurezza", "piano di emergenza", "piano di evacuazione",
                "nomina", "incarico", "conferimento incarico", "graduatoria concorso", "provvisa",
                "impegno di spesa", "liquidazione", "accertamento", "mandato di pagamento",
                "certificato di pagamento", "ordine", "ordinanza", "determinazione", "delibera",
                "visto contabile", "atto attestazione", "avviso", "bando", "altro",
                "parere tecnico", "regolamento", "elenco", "attestazione pubblicazione",
                "atto deliberativo", "atto contabile", "atto autorizzativo", "atto amministrativo",
                "atto riscontrativo", "atto certificativo", "atto notificativo", "atto dichiarativo",
                "atto costitutivo", "atto modificativo", "atto integrativo", "atto revocatorio",
                "atto abrogativo", "atto resoconto", "atto di assegnazione", "atto di trasmissione",
                "atto di comunicazione", "atto di constatazione", "atto di riconoscimento",
                "atto di rifiuto", "atto di diniego", "atto di presa d'atto", "atto di omologazione",
                "atto di approvazione", "atto di adozione", "atto di attestazione", "atto di verifica",
                "atto di controllo", "atto di supervisione", "atto di rendicontazione", "atto di liquidazione",
                "atto di impegno", "atto di accertamento", "atto di riscossione", "atto di ritenuta",
                "atto di compensazione", "atto di rateizzazione", "atto di condono", "atto di sanatoria",
                "atto di proroga", "atto di sospensione", "atto di decadenza", "atto di reintegrazione",
                "atto di restituzione", "atto di rimborso", "atto di indennizzo", "atto di risarcimento",
                "atto di garanzia", "atto di fideiussione", "atto di cauzione", "atto di anticipo",
                "atto di acconto", "atto di saldo", "atto di conguaglio", "atto di rettifica",
                "atto di variazione", "atto di integrazione", "atto di correzione"
            ]
            
            # Se il file contiene uno di questi indicatori, è un documento effettivo e deve essere mantenuto
            for indicator in non_intro_indicators:
                if indicator in text_lower:
                    return {
                        "is_attachment": True,
                        "reason": f"contains_specific_document:{indicator}",
                        "matched_indicator": indicator
                    }
            
            # Cerca indicatori di file introduttivo specifici come "Dettagli file", "Scarica", "Indietro"
            # Questi indicano che il PDF contiene testo di una pagina web anziché un vero allegato
            web_page_indicators = [
                "dettagli file", "nome file originale", "hash", "dimensioni", 
                "link per il download", "scarica", "indietro", "download", 
                "torna indietro", "pagina precedente", "visualizza online",
                "formato pdf", "salva con nome", "apri con", "proprietà file",
                "informazioni file", "file properties", "back", "home", "menu",
                "pagina di", "scheda di", "dettaglio di", "anteprima di"
            ]
            
            web_matches = sum(1 for indicator in web_page_indicators if indicator in text_lower)
            
            # Se contiene molti indicatori di pagina web, è quasi certamente un file introduttivo
            if web_matches >= 2:  # Se contiene almeno 2 di questi indicatori
                return {
                    "is_attachment": False, 
                    "reason": "web_page_content",
                    "web_matches": web_matches
                }
            
            # Cerca indicatori di file introduttivo (esempio: il file menzionato contiene testo introduttivo)
            # Ma solo se non contiene già indicatori di documenti effettivi
            intro_indicators = [
                "pagina", "scheda", "dettaglio", "anteprima", "preview", "visualizza", "mostra",
                "descrizione", "introduzione", "copia", "copertina", "frontespizio", "indice", 
                "sommario", "prefazione", "pagina di presentazione", "pagina introduttiva",
                "pagina di dettaglio", "pagina di visualizzazione", "pagina di anteprima",
                "pagina di scheda", "pagina di riepilogo", "pagina di sintesi", "pagina di sommario"
            ]
            
            # Cerca indicatori di vero allegato
            attach_indicators = [
                "allegato", "documento", "tabelle", "elenco", "quadro", "cronoprogramma",
                "computo", "pianta", "progetto", "relazione", "calcolo", "preventivo",
                "stima", "metrico", "grafico", "foto", "immagine", "planimetria",
                "scheda tecnica", "specifiche tecniche", "capitolato", "disciplinare",
                "relazione geologica", "relazione geotecnica", "relazione strutturale",
                "relazione ambientale", "relazione economica", "quadro economico",
                "cronogramma fisico", "cronogramma finanziario", "scheda attività",
                "scheda intervento", "scheda progetto", "scheda opera", "scheda servizio",
                "scheda quadro", "scheda illustrativa", "scheda descrittiva",
                "scheda allegata", "scheda tecnica allegata", "scheda progettuale",
                "elenco prezzi", "elenco forniture", "elenco attrezzature", "elenco materiali",
                "elenco personale", "elenco documenti", "elenco allegati", "elenco tavole",
                "tavola", "pianta", "prospetto", "sezione", "particolare", "dettaglio",
                "modulo", "modello", "schema", "diagramma", "flusso", "organigramma",
                "matrice", "tabella", "quadro sinottico", "situazione", "stato di fatto",
                "stato di progetto", "stato di attuazione", "stato di avanzamento",
                "scheda rilievo", "scheda ispezione", "scheda verifica", "scheda controllo",
                "scheda monitoraggio", "scheda valutazione", "scheda analisi", "scheda osservazione",
                "computo metrico", "quadro economico", "cronoprogramma", "piano esecutivo",
                "piano di sicurezza", "piano di emergenza", "piano di evacuazione"
            ]
            
            intro_matches = sum(1 for indicator in intro_indicators if indicator in text_lower)
            attach_matches = sum(1 for indicator in attach_indicators if indicator in text_lower)
            
            # Se ci sono molti indicatori introduttivi e pochi di allegato, probabilmente è introduttivo
            # Ma solo se non contiene indicatori specifici di documenti effettivi
            if attach_matches == 0 and intro_matches > 2:
                # Tuttavia, se il file contiene parole chiave come "allegato", "documento", "elenco" ecc. 
                # ma in contesti come "allegato1781868743", potrebbe essere un vero allegato
                # Quindi dobbiamo controllare se questi termini sono usati in modo significativo
                import re
                # Cerchiamo se ci sono riferimenti a documenti reali (es. "allegato 1", "allegato A", "allegato n. 1")
                allegato_pattern = r"(allegato\s+\d+|allegato\s+[a-z]|allegato\s+n\.\s*\d+|allegato\s+a|allegato\s+b)"
                
                if re.search(allegato_pattern, text_lower):
                    # Anche se ha indicatori introduttivi, se contiene "allegato" in contesto significativo, potrebbe essere un vero allegato
                    return {
                        "is_attachment": True,
                        "reason": "contains_meaningful_allegato_reference",
                        "intro_matches": intro_matches,
                        "attach_matches": attach_matches
                    }
                
                return {
                    "is_attachment": False, 
                    "reason": "introductory_content",
                    "intro_matches": intro_matches,
                    "attach_matches": attach_matches
                }
            
            # Se non ci sono indicatori di allegato ma molti indicatori introduttivi
            if attach_matches == 0 and intro_matches > 1:
                return {
                    "is_attachment": False,
                    "reason": "introductory_no_attachments",
                    "intro_matches": intro_matches,
                    "attach_matches": attach_matches
                }
            
            return {
                "is_attachment": True,
                "reason": "likely_attachment",
                "intro_matches": intro_matches,
                "attach_matches": attach_matches
            }
    except ImportError:
        # Se PyPDF2 non è disponibile, usiamo solo analisi del nome del file
        logger.warning("PyPDF2 non disponibile, analisi basata solo sul nome del file")
        # Passiamo all'analisi basata sul nome del file
        pass
    except Exception as e:
        logger.warning(f"Errore nell'analizzare il contenuto di {file_path}: {e}")
        # Se non possiamo analizzare il contenuto, decidiamo in base al nome
        pass

    # Importa il modulo re per l'uso con le espressioni regolari
    import re
    
    # Se PyPDF2 non è disponibile o ci sono stati errori, analizziamo solo il nome del file
    name_lower = file_path.name.lower()
    
    # Indicatori di file che NON sono introduttivi (documenti effettivi) dal nome
    non_intro_name_indicators = [
        r"avviso[_\s]+di[_\s]+appalto[_\s]+aggiudicato",
        r"convocazione[_\s]+consiglio", 
        r"convocazione[_\s]+del[_\s]+consiglio",
        r"avviso[_\s]+di[_\s]+gara", 
        r"bando[_\s]+di[_\s]+gara", 
        r"aggiudicazione", 
        r"graduatoria", 
        r"contratto",
        r"convenzione", 
        r"progetto[_\s]+definitivo", 
        r"progetto[_\s]+esecutivo", 
        r"collaudo", 
        r"direzione[_\s]+lavori", 
        r"certificato[_\s]+di[_\s]+regolarit", 
        r"verbale", 
        r"protocollo", 
        r"allegato",
        r"impegno[_\s]+di[_\s]+spesa", 
        r"liquidazione", 
        r"accertamento", 
        r"mandato[_\s]+di[_\s]+pagamento",
        r"certificato[_\s]+di[_\s]+pagamento",
        r"ordine", 
        r"ordinanza", 
        r"determinazione", 
        r"delibera",
        r"visto[_\s]+contabile", 
        r"atto[_\s]+attestazione", 
        r"avviso", 
        r"bando", 
        r"altro",
        r"parere[_\s]+tecnico", 
        r"regolamento", 
        r"elenco", 
        r"attestazione[_\s]+pubblicazione"
    ]
    
    # Se il nome contiene indicatori di documenti effettivi, mantienilo
    for indicator in non_intro_name_indicators:
        if re.search(indicator, name_lower):
            return {
                "is_attachment": True,
                "reason": f"filename_contains_specific_document:{indicator}",
                "pattern_match": indicator
            }
    
    # Verifichiamo anche se il nome contiene "allegato" + un numero significativo (non solo un codice casuale)
    # Pattern per identificare file che potrebbero essere veri allegati
    allegato_with_number = r"allegato\d+"  # es. "allegato1781868743"
    if re.search(allegato_with_number, name_lower):
        # Se il nome contiene "allegato" + un numero, è probabile che sia un vero allegato
        # ma solo se non contiene anche indicatori di file introduttivi
        if not any(keyword in name_lower for keyword in ["copia", "pagina", "scheda", "dettaglio", "anteprima"]):
            return {
                "is_attachment": True,
                "reason": "filename_contains_allegato_with_number"
            }
    
    # Indicatori di file introduttivi dal nome - inclusi casi come "Copia" come parola intera
    intro_patterns = [
        r"pagina[_\s]", r"scheda[_\s]", r"dettaglio[_\s]", r"anteprima[_\s]", r"preview[_\s]",
        r"visualizza[_\s]", r"mostra[_\s]", r"_intro", r"_desc", r"_dettagli", r"_pagina", 
        r"\bcopia\b", r"\bdettaglio\b", r"\bscheda\b",  # "copia", "dettaglio", "scheda" come parole intere
        r"copertina", r"frontespizio", r"indice", r"sommario", r"prefazione",
        r"pagina[_\s]+di[_\s]+presentazione", r"pagina[_\s]+di[_\s]+introd", 
        r"pagina[_\s]+di[_\s]+dettaglio", r"pagina[_\s]+di[_\s]+visualizz",
        r"pagina[_\s]+di[_\s]+anteprima", r"pagina[_\s]+di[_\s]+scheda", 
        r"pagina[_\s]+di[_\s]+riepilogo", r"pagina[_\s]+di[_\s]+sintesi", 
        r"pagina[_\s]+di[_\s]+sommario"
    ]
    
    is_intro = any(re.search(pattern, name_lower) for pattern in intro_patterns)
    
    if is_intro:
        return {
            "is_attachment": False, 
            "reason": "introductory_filename",
            "pattern_match": [pattern for pattern in intro_patterns if re.search(pattern, name_lower)]
        }
    else:
        return {"is_attachment": True, "reason": "filename_suggests_attachment"}

def filter_downloaded_files(ente: str = None, base_path: str = None) -> None:
    """
    Filtra i file scaricati dallo scraper che non sono veri allegati.
    """
    if ente:
        base_path = Path(get_tenant_dir(ente))
        # Assicurati che la directory esista
        pdf_dir = base_path / "albo_download" / "pdf" if base_path.name != "albo_download" else base_path / "pdf"
    elif base_path:
        pdf_dir = Path(base_path) / "pdf"
    else:
        pdf_dir = Path("albo_download") / "pdf"
    
    if not pdf_dir.exists():
        logger.error(f"Directory PDF non trovata: {pdf_dir}")
        return
    
    # Leggi il file allegati_parsed.csv per confrontare
    allegati_parsed_path = pdf_dir.parent / "allegati_parsed.csv"
    if allegati_parsed_path.exists():
        # Check if the file is empty before attempting to read it
        if allegati_parsed_path.stat().st_size == 0:
            logger.warning(f"Il file {allegati_parsed_path} è vuoto, creazione di un DataFrame vuoto")
            df = pd.DataFrame()
        else:
            try:
                df = pd.read_csv(allegati_parsed_path)
            except pd.errors.EmptyDataError:
                logger.warning(f"Il file {allegati_parsed_path} non contiene colonne valide, creazione di un DataFrame vuoto")
                df = pd.DataFrame()
        logger.info(f"Dati caricati: {len(df)} record da allegati_parsed.csv")
    else:
        logger.warning(f"File allegati_parsed.csv non trovato: {allegati_parsed_path}")
        return
    
    # Ottieni la lista dei file PDF scaricati
    downloaded_files = list(pdf_dir.glob("*.pdf"))
    logger.info(f"Trovati {len(downloaded_files)} file PDF scaricati")
    
    # Crea un dizionario per mappare i nomi dei file ai percorsi
    file_dict = {f.name: f for f in downloaded_files}
    
    # Analizza ogni file scaricato
    files_to_remove = []
    files_to_keep = []
    
    for file_name, file_path in file_dict.items():
        analysis = analyze_file_content(file_path)
        
        # Controlla se il file appare come allegato nei dati
        file_in_data = df[df['pdf_name'].str.contains(file_name, na=False)]
        
        if not analysis["is_attachment"]:
            logger.info(f"File identificato come introduttivo: {file_name} (motivo: {analysis['reason']})")
            files_to_remove.append({
                "file_path": file_path,
                "reason": analysis["reason"],
                "in_dataframe": not file_in_data.empty,
                "details": analysis.get("pattern_match", analysis.get("intro_matches", 0))
            })
        else:
            logger.debug(f"Mantenendo file: {file_name}")
            files_to_keep.append(file_path)
    
    # Rimuovi i file identificati come introduttivi
    removed_count = 0
    for item in files_to_remove:
        file_path = item["file_path"]
        reason = item["reason"]
        in_dataframe = item["in_dataframe"]
        
        # Solo se il file appare nei dati, proviamo a rimuoverlo
        if in_dataframe:
            try:
                # Rimuovi il file fisico
                file_path.unlink()
                logger.info(f"Rimosso file: {file_path.name} (motivo: {reason})")
                removed_count += 1
                
                # Aggiorna il dataframe rimuovendo le righe corrispondenti
                df = df[~df['pdf_name'].str.contains(file_path.name, na=False)]
            except OSError as e:
                logger.warning(f"Impossibile rimuovere {file_path.name}: {e}")
        else:
            logger.debug(f"File non trovato nei dati, saltando: {file_path.name}")
    
    # Salva il dataframe aggiornato
    df.to_csv(allegati_parsed_path, index=False)
    logger.info(f"Aggiornato allegati_parsed.csv, rimosso {removed_count} file introduttivi")
    
    # Genera report
    report_dir = pdf_dir.parent / "report"
    report_dir.mkdir(exist_ok=True)
    
    report_path = report_dir / "filtered_files_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write("# Report Filtraggio File Scaricati\n\n")
        f.write(f"Totale file analizzati: {len(downloaded_files)}\n")
        f.write(f"File rimossi: {removed_count}\n")
        f.write(f"File mantenuti: {len(files_to_keep)}\n\n")
        
        if files_to_remove:
            f.write("## File Rimossi\n\n")
            for item in files_to_remove:
                f.write(f"- {item['file_path'].name} (motivo: {item['reason']})\n")
    
    logger.info(f"Report salvato in: {report_path}")

def main():
    parser = argparse.ArgumentParser(description="Filtra i file scaricati dallo scraper che non sono veri allegati")
    parser.add_argument("--ente", default=None, help="Nome dell'ente per cui filtrare i file (per supporto multi-tenant).")
    parser.add_argument("--base", default=None, help="Directory base per i dati (alternativa a --ente).")
    args = parser.parse_args()
    
    filter_downloaded_files(ente=args.ente, base_path=args.base)

if __name__ == "__main__":
    main()