#!/usr/bin/env python3
"""
Modulo per la comprensione dei procedimenti pubblici e delle sequenze procedurali.
Questo modulo implementa la conoscenza delle sequenze tipiche dei procedimenti 
della Pubblica Amministrazione italiana.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Tuple, Optional
import re
import argparse

# Importa la funzione get_tenant_dir per supportare il sistema multi-tenant
from delibere_comunali.utils.config import get_tenant_dir

# Configura il logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ProceduralUnderstandingEngine:
    """
    Motore per la comprensione dei procedimenti pubblici.
    Riconosce e analizza le sequenze procedurali tipiche della Pubblica Amministrazione.
    """
    
    def __init__(self, ente: str = None, base_path: str = None):
        self.ente = ente
        if ente:
            base_path = Path(get_tenant_dir(ente))
            self.base_path = base_path / "albo_download" if base_path.name != "albo_download" else base_path
        elif base_path:
            self.base_path = Path(base_path)
        else:
            self.base_path = Path("albo_download")
        
        # Sequenze procedurali tipiche della Pubblica Amministrazione
        self.procedural_sequences = {
            # Sequenza tipica per spese
            "spesa_completa": [
                "Delibera",
                "Determinazione",
                "Impegno di Spesa",
                "Liquidazione",
                "Accertamento"
            ],
            # Sequenza per lavori pubblici
            "lavori_pubblici": [
                "Delibera",
                "Determinazione",
                "Affidamento",
                "Progetto",
                "Direzione Lavori",
                "Collaudo",
                "Certificazione"
            ],
            # Sequenza per personale
            "personale": [
                "Delibera",
                "Determinazione",
                "Avviso Concorso",
                "Graduatoria",
                "Atto Conferimento Incarico"
            ],
            # Sequenza per appalti
            "appalto": [
                "Delibera",
                "Determinazione",
                "Avviso Gara",
                "Progetto Definitivo",
                "Progetto Esecutivo",
                "Gara",
                "Aggiudicazione",
                "Contratto",
                "Direzione Lavori",
                "Collaudo"
            ],
            # Sequenza per procedure contabili
            "contabile": [
                "Impegno di Spesa",
                "Accertamento",
                "Liquidazione",
                "Certificato di Pagamento",
                "Mandato di Pagamento"
            ],
            # Sequenza per procedure di controllo
            "controllo": [
                "Atto Programmazione",
                "Atto di Verifica",
                "Atto di Controllo",
                "Relazione di Controllo",
                "Atto di Rettifica"
            ],
            # Sequenza per procedure di approvazione
            "approvazione": [
                "Atto di Indirizzo",
                "Atto Programmatorio",
                "Atto Deliberativo",
                "Atto di Approvazione",
                "Atto di Adozione"
            ]
        }
        
        # Mappatura tra varianti di denominazione e tipo standard
        self.type_variants = {
            # Varianti per Delibera
            "delibera": ["delibera", "deliberazione", "delibera di giunta", "delibera di consiglio"],
            # Varianti per Determinazione
            "determinazione": ["determinazione", "determina", "determinazione dirigenziale", "atto dirigenziale"],
            # Varianti per Impegno di Spesa
            "impegno_spesa": ["impegno", "impegno di spesa", "atto di impegno", "impegno contabile", "atto impegno"],
            # Varianti per Liquidazione
            "liquidazione": ["liquidazione", "atto di liquidazione", "certificato di pagamento", "mandato di pagamento"],
            # Varianti per Affidamento
            "affidamento": ["affidamento", "affidamento diretto", "aggiudicazione", "aggiudicazione provvisoria", "aggiudicazione definitiva"],
            # Altre varianti
            "progetto": ["progetto", "progetto definitivo", "progetto esecutivo", "progetto esecutivo completo"],
            "direzione_lavori": ["direzione lavori", "direttore lavori", "coordinamento sicurezza", "collaudo statico"],
            "collaudo": ["collaudo", "collaudo finale", "collaudo statico", "certificazione collaudo"],
            "contratto": ["contratto", "stipula contratto", "atto contrattuale", "convenzione"],
            "gara": ["gara", "procedura gara", "gara telematica", "procedura comparativa"],
            "avviso_gara": ["avviso", "avviso gara", "bando", "bando gara", "disciplinare", "capitolato"],
            "graduatoria": ["graduatoria", "graduatoria finale", "elenco ammessi", "classifica"],
            "atto_conferimento": ["atto conferimento", "nomina", "incarico", "delega", "provvedimento nomina"],
            # Aggiungiamo le categorie richieste dalla normativa italiana
            "atto_contabile": ["atto contabile", "atto di contabilità", "atto di gestione contabile"],
            "visto_contabile": ["visto contabile", "visto regolarità", "certificato regolarità"],
            "atto_approvazione": ["atto di approvazione", "approvazione", "atto approvativo"],
            "atto_verifica": ["atto di verifica", "verifica", "atto di controllo", "controllo"],
            "atto_certificazione": ["certificazione", "atto di certificazione", "certificato"],
            "atto_autorizzativo": ["atto autorizzativo", "autorizzazione", "atto di autorizzazione"],
            "atto_deliberativo": ["atto deliberativo", "deliberazione", "atto di deliberazione"],
            "atto_indirizzo": ["atto di indirizzo", "indirizzo", "atto indirizzo politico"],
            "atto_programmazione": ["atto di programmazione", "programmazione", "atto programmatorio"],
            "atto_gestione": ["atto di gestione", "atto gestione", "atto di gestione amministrativa"],
            "atto_resoconto": ["atto di resoconto", "resoconto", "atto di rendicontazione"],
            "atto_accertamento": ["accertamento", "atto di accertamento", "atto accertamento"],
            "atto_riscossione": ["riscossione", "atto di riscossione", "atto riscossorio"],
            "atto_pagamento": ["atto di pagamento", "pagamento", "mandato di pagamento"],
            "atto_revisione": ["atto di revisione", "revisione", "atto revisionale"],
            "atto_supervisione": ["atto di supervisione", "supervisione", "atto di sorveglianza"],
            "atto_verifica_regolarita": ["verifica regolarità", "atto verifica regolarità", "controllo regolarità"],
            "atto_verifica_contabilita": ["verifica contabilità", "atto verifica contabilità", "controllo contabilità"],
            "atto_verifica_finanziaria": ["verifica finanziaria", "atto verifica finanziaria", "controllo finanziario"],
            "atto_verifica_amministrativa": ["verifica amministrativa", "atto verifica amministrativa", "controllo amministrativo"],
            "atto_presa_atto": ["atto di presa d'atto", "presa d'atto", "atto presa atto"],
            "atto_omologazione": ["atto di omologazione", "omologazione", "atto omologativo"],
            "atto_adozione": ["atto di adozione", "adozione", "atto adozione"],
            "atto_attestazione": ["atto di attestazione", "attestazione", "atto attestativo"],
            "atto_costitutivo": ["atto costitutivo", "atto costitutivo", "atto di costituzione"],
            "atto_modificativo": ["atto modificativo", "atto modifica", "atto di modifica"],
            "atto_integrativo": ["atto integrativo", "atto integrazione", "atto di integrazione"],
            "atto_retifica": ["atto di rettifica", "rettifica", "atto rettificativo"],
            "atto_variazione": ["atto di variazione", "variazione", "atto variativo"],
            "atto_revocatorio": ["atto revocatorio", "revoca", "atto di revoca"],
            "atto_abrogativo": ["atto abrogativo", "abrogazione", "atto di abrogazione"],
            "atto_dichiarativo": ["atto dichiarativo", "dichiarazione", "atto di dichiarazione"],
            "atto_notificativo": ["atto notificativo", "notifica", "atto di notifica"],
            "atto_riconoscimento": ["atto di riconoscimento", "riconoscimento", "atto riconoscitivo"],
            "atto_constatazione": ["atto di constatazione", "constatazione", "atto costitutivo"],
            "atto_rifiuto": ["atto di rifiuto", "rifiuto", "atto di diniego"],
            "atto_diniego": ["atto di diniego", "diniego", "atto di rifiuto"],
            "atto_rateizzazione": ["atto di rateizzazione", "rateizzazione", "atto di rateizzazione"],
            "atto_condono": ["atto di condono", "condono", "atto di sanatoria"],
            "atto_sanatoria": ["atto di sanatoria", "sanatoria", "atto di condono"],
            "atto_proroga": ["atto di proroga", "proroga", "atto di sospensione"],
            "atto_sospensione": ["atto di sospensione", "sospensione", "atto di sospensione"],
            "atto_decadenza": ["atto di decadenza", "decadenza", "atto di reintegrazione"],
            "atto_reintegrazione": ["atto di reintegrazione", "reintegrazione", "atto reintegrativo"],
            "atto_restituzione": ["atto di restituzione", "restituzione", "atto di rimborso"],
            "atto_rimborso": ["atto di rimborso", "rimborso", "atto di indennizzo"],
            "atto_indennizzo": ["atto di indennizzo", "indennizzo", "atto di risarcimento"],
            "atto_risarcimento": ["atto di risarcimento", "risarcimento", "atto risarcitorio"],
            "atto_garanzia": ["atto di garanzia", "garanzia", "atto fideiussione"],
            "atto_fideiussione": ["atto di fideiussione", "fideiussione", "atto di cauzione"],
            "atto_cauzione": ["atto di cauzione", "cauzione", "atto di anticipo"],
            "atto_anticipo": ["atto di anticipo", "anticipo", "atto di acconto"],
            "atto_acconto": ["atto di acconto", "acconto", "atto di saldo"],
            "atto_saldo": ["atto di saldo", "saldo", "atto di conguaglio"],
            "atto_conguaglio": ["atto di conguaglio", "conguaglio", "atto di rettifica"]
        }
        
        # Relazioni di dipendenza tra documenti
        self.dependency_rules = {
            # La liquidazione deve seguire l'impegno
            "Liquidazione": ["Impegno di Spesa", "Determinazione"],
            # L'impegno deve seguire la determinazione
            "Impegno di Spesa": ["Determinazione", "Delibera"],
            # La determinazione deve seguire la delibera in alcuni casi
            "Determinazione": ["Delibera"],
            # Il collaudo deve seguire la direzione lavori
            "Collaudo": ["Direzione Lavori", "Progetto Esecutivo"],
            # L'affidamento deve seguire la gara
            "Affidamento": ["Gara", "Avviso Gara", "Progetto Esecutivo"],
            # Atto contabile richiede impegno
            "Atto Contabile": ["Impegno di Spesa", "Determinazione"],
            # Visto contabile richiede atto contabile
            "Visto Contabile": ["Atto Contabile", "Liquidazione"],
            # Certificato di pagamento richiede liquidazione
            "Certificato di Pagamento": ["Liquidazione", "Accertamento"],
            # Mandato di pagamento richiede certificato
            "Mandato di Pagamento": ["Certificato di Pagamento", "Liquidazione"],
            # Approvazione richiede programmazione
            "Atto di Approvazione": ["Atto di Programmazione", "Atto di Indirizzo"],
            # Controllo richiede atto base
            "Atto di Controllo": ["Atto di Programmazione", "Atto di Verifica"],
            # Rettifica richiede atto originale
            "Atto di Rettifica": ["Atto Originale", "Atto Base"],
            # Adozione richiede deliberazione
            "Atto di Adozione": ["Atto Deliberativo", "Delibera"],
            # Attestazione richiede verifica
            "Atto di Attestazione": ["Atto di Verifica", "Atto di Controllo"],
            # Supervisione richiede approvazione
            "Atto di Supervisione": ["Atto di Approvazione", "Atto di Adozione"]
        }
        
    def normalize_document_type(self, doc_type: str) -> str:
        """
        Normalizza il tipo di documento in base alle varianti conosciute.
        """
        if pd.isna(doc_type):
            return "Altro"
        
        doc_type_lower = str(doc_type).lower().strip()
        
        for standard_type, variants in self.type_variants.items():
            for variant in variants:
                if variant in doc_type_lower:
                    # Convertiamo il tipo standard in formato leggibile
                    normalized = standard_type.replace("_", " ").title()
                    # Facciamo sostituzioni specifiche per ottenere nomi standard
                    replacements = {
                        "Impegno Spesa": "Impegno di Spesa",
                        "Atto Approvazione": "Atto di Approvazione",
                        "Atto Verifica": "Atto di Verifica",
                        "Atto Certificazione": "Atto di Certificazione",
                        "Atto Autorizzativo": "Atto Autorizzativo",
                        "Atto Deliberativo": "Atto Deliberativo",
                        "Atto Indirizzo": "Atto di Indirizzo",
                        "Atto Programmazione": "Atto di Programmazione",
                        "Atto Gestione": "Atto di Gestione",
                        "Atto Resoconto": "Atto di Resoconto",
                        "Atto Accertamento": "Atto di Accertamento",
                        "Atto Riscossione": "Atto di Riscossione",
                        "Atto Pagamento": "Atto di Pagamento",
                        "Atto Revisione": "Atto di Revisione",
                        "Atto Supervisione": "Atto di Supervisione",
                        "Atto Verifica Regolarita": "Atto di Verifica Regolarità",
                        "Atto Verifica Contabilita": "Atto di Verifica Contabilità",
                        "Atto Verifica Finanziaria": "Atto di Verifica Finanziaria",
                        "Atto Verifica Amministrativa": "Atto di Verifica Amministrativa",
                        "Atto Presa Atto": "Atto di Presa d'Atto",
                        "Atto Omologazione": "Atto di Omologazione",
                        "Atto Adozione": "Atto di Adozione",
                        "Atto Attestazione": "Atto di Attestazione",
                        "Atto Costitutivo": "Atto Costitutivo",
                        "Atto Modificativo": "Atto Modificativo",
                        "Atto Integrativo": "Atto Integrativo",
                        "Atto Rettifica": "Atto di Rettifica",
                        "Atto Variazione": "Atto di Variazione",
                        "Atto Revocatorio": "Atto Revocatorio",
                        "Atto Abrogativo": "Atto Abrogativo",
                        "Atto Dichiarativo": "Atto Dichiarativo",
                        "Atto Notificativo": "Atto Notificativo",
                        "Atto Riconoscimento": "Atto di Riconoscimento",
                        "Atto Costatazione": "Atto di Constatazione",
                        "Atto Rifiuto": "Atto di Rifiuto",
                        "Atto Diniego": "Atto di Diniego",
                        "Atto Rateizzazione": "Atto di Rateizzazione",
                        "Atto Condono": "Atto di Condono",
                        "Atto Sanatoria": "Atto di Sanatoria",
                        "Atto Proroga": "Atto di Proroga",
                        "Atto Sospensione": "Atto di Sospensione",
                        "Atto Decadenza": "Atto di Decadenza",
                        "Atto Reintegrazione": "Atto di Reintegrazione",
                        "Atto Restituzione": "Atto di Restituzione",
                        "Atto Rimborso": "Atto di Rimborso",
                        "Atto Indennizzo": "Atto di Indennizzo",
                        "Atto Risarcimento": "Atto di Risarcimento",
                        "Atto Garanzia": "Atto di Garanzia",
                        "Atto Fideiussione": "Atto di Fideiussione",
                        "Atto Cauzione": "Atto di Cauzione",
                        "Atto Anticipo": "Atto di Anticipo",
                        "Atto Acconto": "Atto di Acconto",
                        "Atto Saldo": "Atto di Saldo",
                        "Atto Conguaglio": "Atto di Conguaglio"
                    }
                    return replacements.get(normalized, normalized)
        
        # Se non trovato, normalizza il tipo originale
        doc_type_normalized = str(doc_type).replace("_", " ").replace("-", " ").strip()
        return doc_type_normalized  # Ritorna il tipo originale formattato se non trovato

    def identify_procedural_sequence(self, df: pd.DataFrame) -> Dict:
        """
        Identifica le sequenze procedurali nei documenti forniti.
        """
        results = {
            'sequences_found': [],
            'missing_documents': [],
            'procedural_errors': [],
            'dependency_violations': []
        }
        
        # Convertiamo la data in formato datetime per confronti temporali
        df_copy = df.copy()
        if 'data_atto' in df_copy.columns:
            df_copy['data_parsed'] = pd.to_datetime(df_copy['data_atto'], format='%d/%m/%Y', errors='coerce')
        else:
            # Se non c'è la colonna data_atto, proviamo altre possibili colonne
            for date_col in ['data_documento', 'data', 'data_emissione']:
                if date_col in df_copy.columns:
                    df_copy['data_parsed'] = pd.to_datetime(df_copy[date_col], format='%d/%m/%Y', errors='coerce')
                    break
            if 'data_parsed' not in df_copy.columns:
                df_copy['data_parsed'] = pd.NaT  # Not a Time se nessuna colonna data trovata
        
        # Normalizziamo i tipi di documento
        if 'doc_type' in df_copy.columns:
            df_copy['normalized_type'] = df_copy['doc_type'].apply(self.normalize_document_type)
        elif 'category' in df_copy.columns:
            df_copy['normalized_type'] = df_copy['category'].apply(self.normalize_document_type)
        else:
            logger.warning("Nessuna colonna 'doc_type' o 'category' trovata nei dati")
            return results
        
        # Raggruppiamo per gruppo di procedimento (potrebbe essere per oggetto, beneficiario, o altro criterio)
        if 'atto_group' in df_copy.columns:
            group_by = 'atto_group'
        elif 'oggetto' in df_copy.columns:
            group_by = 'oggetto'
        elif 'beneficiario' in df_copy.columns:
            group_by = 'beneficiario'
        else:
            # Se non c'è un campo evidente per raggruppare, proviamo a euristiche
            group_by = None
        
        if group_by and group_by in df_copy.columns:
            # Raggruppa per il criterio identificato
            for group_name, group_data in df_copy.groupby(group_by):
                sequence_analysis = self._analyze_sequence_in_group(group_data, group_name)
                results['sequences_found'].extend(sequence_analysis['sequences_found'])
                results['missing_documents'].extend(sequence_analysis['missing_documents'])
                results['procedural_errors'].extend(sequence_analysis['procedural_errors'])
                results['dependency_violations'].extend(sequence_analysis['dependency_violations'])
        else:
            # Analisi su tutto il dataset se non possiamo raggruppare
            sequence_analysis = self._analyze_sequence_in_group(df_copy, "all_documents")
            results['sequences_found'].extend(sequence_analysis['sequences_found'])
            results['missing_documents'].extend(sequence_analysis['missing_documents'])
            results['procedural_errors'].extend(sequence_analysis['procedural_errors'])
            results['dependency_violations'].extend(sequence_analysis['dependency_violations'])
        
        return results
    
    def _analyze_sequence_in_group(self, group_data: pd.DataFrame, group_name: str) -> Dict:
        """
        Analizza una sequenza procedurale all'interno di un gruppo specifico.
        """
        results = {
            'sequences_found': [],
            'missing_documents': [],
            'procedural_errors': [],
            'dependency_violations': []
        }
        
        # Estrai i tipi di documenti presenti in questo gruppo
        present_types = set(group_data['normalized_type'].dropna().unique())
        
        # Controlla se ci sono sequenze complete
        for seq_name, seq_types in self.procedural_sequences.items():
            seq_present = [doc_type for doc_type in seq_types if doc_type in present_types]
            if len(seq_present) > 1:  # Trovata una parziale o completa sequenza
                # Ordina per data se disponibile
                if 'data_parsed' in group_data.columns and not group_data['data_parsed'].isna().all():
                    group_sorted = group_data.sort_values('data_parsed')
                    seq_docs = []
                    for doc_type in seq_present:
                        docs_of_type = group_sorted[group_sorted['normalized_type'] == doc_type]
                        for _, doc in docs_of_type.iterrows():
                            seq_docs.append({
                                'doc_type': doc_type,
                                'pdf_name': doc.get('pdf_name', ''),
                                'data_atto': doc.get('data_atto', ''),
                                'oggetto': doc.get('oggetto', '')
                            })
                    
                    if len(seq_docs) > 1:
                        results['sequences_found'].append({
                            'group': group_name,
                            'sequence_type': seq_name,
                            'documents': seq_docs,
                            'completed_ratio': len(seq_present) / len(seq_types)
                        })
                
                # Controlla eventuali documenti mancanti
                missing = [doc_type for doc_type in seq_types if doc_type not in present_types]
                if missing:
                    results['missing_documents'].append({
                        'group': group_name,
                        'sequence_type': seq_name,
                        'missing_types': missing,
                        'present_types': seq_present
                    })
        
        # Controlla violazioni di dipendenza
        for _, row in group_data.iterrows():
            current_type = row['normalized_type']
            if current_type in self.dependency_rules:
                expected_deps = self.dependency_rules[current_type]
                
                # Verifica se i documenti predecessori esistono e sono anteriori temporalmente
                for dep_type in expected_deps:
                    # Trova documenti di tipo dipendenza
                    condition = (
                        (group_data['normalized_type'] == dep_type) &
                        ((pd.isna(row.get('data_parsed'))) | 
                         (pd.isna(group_data['data_parsed'])) | 
                         (group_data['data_parsed'] <= row['data_parsed']))
                    )
                    dep_docs = group_data[condition]
                    
                    if len(dep_docs) == 0:
                        # Nessuna dipendenza trovata
                        results['dependency_violations'].append({
                            'group': group_name,
                            'document': row.get('pdf_name', ''),
                            'missing_dependency': dep_type,
                            'expected_before': current_type
                        })
                    elif pd.isna(row.get('data_parsed')) or pd.isna(dep_docs['data_parsed'].iloc[0]):
                        # Date non disponibili per confronto temporale
                        continue
                    elif dep_docs['data_parsed'].max() > row['data_parsed']:
                        # La dipendenza è successiva (violazione temporale)
                        results['dependency_violations'].append({
                            'group': group_name,
                            'document': row.get('pdf_name', ''),
                            'dependency_later_than_expected': dep_type,
                            'document_date': row['data_parsed'],
                            'dependency_date': dep_docs['data_parsed'].max()
                        })
        
        return results
    
    def generate_procedural_report(self, results: Dict) -> str:
        """
        Genera un report testuale sull'analisi procedurale.
        """
        report_lines = []
        report_lines.append("# Report Analisi Procedurale")
        report_lines.append("")
        
        # Sequenze trovate
        if results['sequences_found']:
            report_lines.append("## Sequenze Procedurali Identificate")
            report_lines.append("")
            for seq in results['sequences_found']:
                report_lines.append(f"- Gruppo: {seq['group']}")
                report_lines.append(f"  Tipo sequenza: {seq['sequence_type']}")
                report_lines.append(f"  Completamento: {seq['completed_ratio']*100:.1f}%")
                report_lines.append("  Documenti:")
                for doc in seq['documents']:
                    report_lines.append(f"    - {doc['doc_type']} ({doc['data_atto']}): {doc['oggetto'][:100]}...")
                report_lines.append("")
        
        # Documenti mancanti
        if results['missing_documents']:
            report_lines.append("## Documenti Mancanti in Sequenze")
            report_lines.append("")
            for missing in results['missing_documents']:
                report_lines.append(f"- Gruppo: {missing['group']}")
                report_lines.append(f"  Sequenza: {missing['sequence_type']}")
                report_lines.append(f"  Mancanti: {', '.join(missing['missing_types'])}")
                report_lines.append(f"  Presenti: {', '.join(missing['present_types'])}")
                report_lines.append("")
        
        # Violazioni di dipendenza
        if results['dependency_violations']:
            report_lines.append("## Violazioni di Dipendenza Procedurale")
            report_lines.append("")
            for violation in results['dependency_violations']:
                report_lines.append(f"- Documento: {violation['document']}")
                report_lines.append(f"  Gruppo: {violation['group']}")
                if 'missing_dependency' in violation:
                    report_lines.append(f"  Dipendenza mancante: {violation['missing_dependency']}")
                if 'dependency_later_than_expected' in violation:
                    report_lines.append(f"  Dipendenza fuori sequenza: {violation['dependency_later_than_expected']}")
                report_lines.append("")
        
        # Errori procedurali
        if results['procedural_errors']:
            report_lines.append("## Errori Procedurali")
            report_lines.append("")
            for error in results['procedural_errors']:
                report_lines.append(f"- {error}")
                report_lines.append("")
        
        return "\n".join(report_lines)
    
    def analyze_document_dependencies(self, df: pd.DataFrame) -> Dict:
        """
        Analizza le dipendenze tra documenti per identificare anomalie procedurali.
        """
        dependencies = {
            'temporal_anomalies': [],
            'missing_dependencies': [],
            'circular_dependencies': []
        }
        
        # Ordina i documenti per data se disponibile
        if 'data_parsed' in df.columns:
            df_sorted = df.sort_values('data_parsed').reset_index(drop=True)
        else:
            df_sorted = df
        
        # Cerca documenti che fanno riferimento ad altri documenti
        reference_patterns = [
            r'determinazione\s+n?\s*[.:]?\s*(\d+)',
            r'delibera\s+n?\s*[.:]?\s*(\d+)', 
            r'atto\s+n?\s*[.:]?\s*(\d+)',
            r'impegno\s+n?\s*[.:]?\s*(\d+)',
            r'liquidazione\s+n?\s*[.:]?\s*(\d+)'
        ]
        
        for idx, row in df_sorted.iterrows():
            current_doc_type = row.get('normalized_type', '')
            current_date = row.get('data_parsed', pd.NaT)
            current_oggetto = str(row.get('oggetto', ''))
            
            # Cerca riferimenti a numeri di atto nell'oggetto
            for pattern in reference_patterns:
                matches = re.findall(pattern, current_oggetto, re.IGNORECASE)
                for match in matches:
                    # Cerca se esiste un documento con quel numero
                    ref_docs = df_sorted[
                        (df_sorted['numero_atto'] == match) |
                        (df_sorted['oggetto'].str.contains(match, case=False, na=False))
                    ]
                    
                    for _, ref_doc in ref_docs.iterrows():
                        ref_date = ref_doc.get('data_parsed', pd.NaT)
                        
                        # Controlla se c'è una violazione temporale
                        if pd.notna(current_date) and pd.notna(ref_date):
                            if current_date < ref_date:  # Il documento corrente è datato prima del riferimento
                                dependencies['temporal_anomalies'].append({
                                    'document': row.get('pdf_name', ''),
                                    'refers_to': ref_doc.get('pdf_name', ''),
                                    'document_date': current_date,
                                    'reference_date': ref_date,
                                    'issue': 'Documento fa riferimento a documento futuro'
                                })
        
        return dependencies


def main():
    parser = argparse.ArgumentParser(description="Analisi procedurale dei documenti pubblici")
    parser.add_argument("--ente", default=None, help="Nome dell'ente per cui eseguire l'analisi (per supporto multi-tenant).")
    parser.add_argument("--base", default=None, help="Directory base per i dati (alternativa a --ente).")
    args = parser.parse_args()
    
    engine = ProceduralUnderstandingEngine(ente=args.ente, base_path=args.base)
    
    # Carica i dati
    allegati_path = engine.base_path / "allegati_parsed.csv"
    if not allegati_path.exists():
        logger.error(f"File {allegati_path} non trovato")
        return
    
    df = pd.read_csv(allegati_path)
    logger.info(f"Dati caricati: {len(df)} documenti")
    
    # Esegui l'analisi procedurale
    logger.info("Inizio analisi procedurale...")
    results = engine.identify_procedural_sequence(df)
    
    # Genera il report
    report = engine.generate_procedural_report(results)
    
    # Salva il report
    report_dir = engine.base_path / "report"
    report_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = report_dir / "procedural_analysis_report.md"
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(report)
    
    logger.info(f"Report procedurale salvato in: {report_path}")
    
    # Stampa un sommario
    print(f"\nSommario Analisi Procedurale:")
    print(f"- Sequenze trovate: {len(results['sequences_found'])}")
    print(f"- Documenti mancanti: {len(results['missing_documents'])}")
    print(f"- Violazioni di dipendenza: {len(results['dependency_violations'])}")
    
    # Analisi supplementare delle dipendenze
    logger.info("Inizio analisi dipendenze documenti...")
    deps = engine.analyze_document_dependencies(df)
    
    print(f"- Anomalie temporali: {len(deps['temporal_anomalies'])}")
    print(f"- Dipendenze mancanti: {len(deps['missing_dependencies'])}")


if __name__ == "__main__":
    main()