#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modulo per la comprensione dei procedimenti pubblici e delle sequenze procedurali.
Questo modulo implementa la conoscenza delle sequenze tipiche dei procedimenti 
della Pubblica Amministrazione italiana con regole dinamiche, pesi e tolleranze temporali.
"""

import pandas as pd
import numpy as np
import logging
from pathlib import Path
from datetime import datetime, timedelta
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
    Riconosce e analizza le sequenze procedurali tipiche della Pubblica Amministrazione
    con supporto per regole dinamiche, pesi e tolleranze temporali.
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
            "atto_contabile": ["atto contabile", "atto di contabilit", "atto di gestione contabile"],
            "visto_contabile": ["visto contabile", "visto regolarit", "certificato regolarit"],
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
            "atto_verifica_regolarita": ["verifica regolarit", "atto verifica regolarit", "controllo regolarit"],
            "atto_verifica_contabilita": ["verifica contabilit", "atto verifica contabilit", "controllo contabilit"],
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
        
        # ========================================================================
        # FIX 3: REGOLAZIONE DINAMICA CON PESI E TOLLERANZE TEMPORALI
        # ========================================================================
        
        # Regole di dipendenza con pesi e tolleranze temporali
        # Struttura: {documento: {'required': [lista], 'optional': [lista], 'weights': {doc: peso}, 'tolerance_days': N}}
        self.dependency_rules = {
            # La liquidazione deve seguire l'impegno (peso 1.0 = obbligatorio)
            "Liquidazione": {
                "required": ["Impegno di Spesa"],
                "optional": ["Determinazione", "Delibera"],
                "weights": {"Impegno di Spesa": 1.0, "Determinazione": 0.7, "Delibera": 0.5},
                "tolerance_days": 30  # Tolleranza di 30 giorni tra impegno e liquidazione
            },
            # L'impegno deve seguire la determinazione
            "Impegno di Spesa": {
                "required": ["Determinazione"],
                "optional": ["Delibera"],
                "weights": {"Determinazione": 1.0, "Delibera": 0.8},
                "tolerance_days": 15
            },
            # La determinazione deve seguire la delibera in alcuni casi
            "Determinazione": {
                "required": [],
                "optional": ["Delibera"],
                "weights": {"Delibera": 0.6},
                "tolerance_days": 7
            },
            # Il collaudo deve seguire la direzione lavori
            "Collaudo": {
                "required": ["Direzione Lavori"],
                "optional": ["Progetto Esecutivo", "Certificazione"],
                "weights": {"Direzione Lavori": 1.0, "Progetto Esecutivo": 0.8, "Certificazione": 0.3},
                "tolerance_days": 90
            },
            # L'affidamento deve seguire la gara
            "Affidamento": {
                "required": ["Gara"],
                "optional": ["Avviso Gara", "Progetto Esecutivo", "Delibera"],
                "weights": {"Gara": 1.0, "Avviso Gara": 0.9, "Progetto Esecutivo": 0.7, "Delibera": 0.5},
                "tolerance_days": 60
            },
            # Atto contabile richiede impegno
            "Atto Contabile": {
                "required": ["Impegno di Spesa"],
                "optional": ["Determinazione"],
                "weights": {"Impegno di Spesa": 1.0, "Determinazione": 0.8},
                "tolerance_days": 10
            },
            # Visto contabile richiede atto contabile
            "Visto Contabile": {
                "required": ["Atto Contabile"],
                "optional": ["Liquidazione"],
                "weights": {"Atto Contabile": 1.0, "Liquidazione": 0.9},
                "tolerance_days": 5
            },
            # Certificato di pagamento richiede liquidazione
            "Certificato di Pagamento": {
                "required": ["Liquidazione"],
                "optional": ["Accertamento"],
                "weights": {"Liquidazione": 1.0, "Accertamento": 0.8},
                "tolerance_days": 15
            },
            # Mandato di pagamento richiede certificato
            "Mandato di Pagamento": {
                "required": ["Certificato di Pagamento"],
                "optional": ["Liquidazione"],
                "weights": {"Certificato di Pagamento": 1.0, "Liquidazione": 0.7},
                "tolerance_days": 7
            },
            # Approvazione richiede programmazione
            "Atto di Approvazione": {
                "required": ["Atto di Programmazione"],
                "optional": ["Atto di Indirizzo"],
                "weights": {"Atto di Programmazione": 1.0, "Atto di Indirizzo": 0.8},
                "tolerance_days": 30
            },
            # Controllo richiede atto base
            "Atto di Controllo": {
                "required": ["Atto di Programmazione"],
                "optional": ["Atto di Verifica"],
                "weights": {"Atto di Programmazione": 1.0, "Atto di Verifica": 0.9},
                "tolerance_days": 20
            },
            # Rettifica richiede atto originale
            "Atto di Rettifica": {
                "required": [],
                "optional": ["Atto Originale"],
                "weights": {"Atto Originale": 0.7},
                "tolerance_days": 180  # Può essere anche molto tempo dopo
            },
            # Adozione richiede deliberazione
            "Atto di Adozione": {
                "required": ["Atto Deliberativo"],
                "optional": ["Delibera"],
                "weights": {"Atto Deliberativo": 1.0, "Delibera": 0.9},
                "tolerance_days": 14
            },
            # Attestazione richiede verifica
            "Atto di Attestazione": {
                "required": ["Atto di Verifica"],
                "optional": ["Atto di Controllo"],
                "weights": {"Atto di Verifica": 1.0, "Atto di Controllo": 0.8},
                "tolerance_days": 10
            },
            # Supervisione richiede approvazione
            "Atto di Supervisione": {
                "required": ["Atto di Approvazione"],
                "optional": ["Atto di Adozione"],
                "weights": {"Atto di Approvazione": 1.0, "Atto di Adozione": 0.8},
                "tolerance_days": 45
            }
        }
        
        # Soglia minima per considerare una sequenza completa (50% come da analisi)
        self.completion_threshold = 0.5
        
        # Soglia di confidenza per la classificazione
        self.confidence_thresholds = {
            'high': 0.8,
            'medium': 0.6,
            'low': 0.4
        }
    
    def normalize_document_type(self, doc_type: str) -> str:
        """
        Normalizza il tipo di documento in base alle varianti conosciute.
        """
        if pd.isna(doc_type):
            return "Altro"
        
        doc_type_lower = str(doc_type).lower().strip()
        
        # Controllo specifico per evitare mappature scorrette
        # Se il tipo contiene "pubblicazione" o "trasparenza", non dovrebbe diventare "Atto di Attestazione"
        if "pubblicazione" in doc_type_lower or "trasparenza" in doc_type_lower:
            # Controlla se è effettivamente un tipo correlato a pubblicazione
            if "attestazione" in doc_type_lower and "pubblicazione" in doc_type_lower:
                # Questo è probabilmente un documento di attestazione di pubblicazione
                return "AttestazionePubblicazione"
            elif "pubblicazione" in doc_type_lower:
                return "Pubblicazione"
            else:
                return "Pubblicazione e Trasparenza"
        
        # Cerca corrispondenze con le varianti note
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

    def convert_category_to_document_type(self, category: str) -> str:
        """
        Converte una categoria in tipo di documento in modo più accurato,
        evitando mappature scorrette come 'Pubblicazione e Trasparenza' -> 'Atto di Attestazione'.
        """
        if pd.isna(category):
            return "Altro"
        
        category_lower = str(category).lower().strip()
        
        # Mappatura specifica da categoria a tipo di documento
        category_mapping = {
            "pubblicazione e trasparenza": "AttestazionePubblicazione",
            "pubblicazioni": "AttestazionePubblicazione",
            "contabilità": "Atto Contabile",
            "regolamenti": "Regolamento",
            "urbanistica": "Atto Urbanistico",
            "organizzazione": "Atto Organizzativo",
            "lavori pubblici": "Atto Lavori Pubblici",
            "personale": "Atto Personale",
            "contenzioso": "Atto Contenzioso",
            "servizi demografici": "Atto Anagrafe",
            "comunicazione istituzionale": "Comunicazione Istituzionale",
            "cultura e turismo": "Atto Cultura Turismo",
            "ambiente": "Atto Ambientale",
            "servizi sociali": "Atto Sociale",
            "affari generali": "Atto Amministrativo",
            "delibera di giunta": "Delibera",
            "commercio": "Atto Commerciale",
            "delibera di consiglio": "Delibera"
        }
        
        # Cerca corrispondenza esatta o parziale
        for cat_key, doc_type in category_mapping.items():
            if cat_key in category_lower:
                return doc_type
        
        # Se non trovata una mappatura specifica, ritorna la categoria stessa
        # ma in formato standardizzato
        return category.replace("_", " ").replace("-", " ").title()

    def calculate_sequence_completion_score(self, present_types: List[str], expected_sequence: List[str]) -> float:
        """
        Calcola il punteggio di completamento di una sequenza con pesi.
        
        FIX 3: Implementazione del scoring con pesi per valutare la completezza delle sequenze.
        """
        if not expected_sequence:
            return 0.0
        
        # Calcola il peso totale dei documenti presenti
        total_weight = 0.0
        max_possible_weight = 0.0
        
        for doc_type in expected_sequence:
            # Trova il peso del documento (1.0 per required, 0.5 per optional)
            doc_weight = 1.0  # Default per documenti required
            
            # Verifica se il documento è presente
            if doc_type in present_types:
                total_weight += doc_weight
            
            max_possible_weight += doc_weight
        
        # Calcola il punteggio di completamento
        if max_possible_weight > 0:
            completion_score = total_weight / max_possible_weight
        else:
            completion_score = 0.0
        
        return completion_score

    def calculate_dependency_score(self, current_type: str, available_types: List[str], 
                                   current_date: datetime = None, available_dates: Dict[str, datetime] = None) -> Tuple[float, Dict]:
        """
        Calcola il punteggio di dipendenza per un documento specifico.
        
        FIX 3: Implementazione del sistema di dipendenze con pesi e tolleranze temporali.
        
        Returns:
            Tuple[score, details] dove:
            - score: punteggio complessivo (0-1)
            - details: dizionario con dettagli sul calcolo
        """
        if current_type not in self.dependency_rules:
            return 1.0, {'status': 'no_dependencies'}  # Nessuna dipendenza = perfetto
        
        rule = self.dependency_rules[current_type]
        required_deps = rule.get('required', [])
        optional_deps = rule.get('optional', [])
        weights = rule.get('weights', {})
        tolerance_days = rule.get('tolerance_days', 30)
        
        total_score = 0.0
        total_weight = 0.0
        details = {
            'current_type': current_type,
            'required_deps': {},
            'optional_deps': {},
            'temporal_checks': {},
            'tolerance_days': tolerance_days
        }
        
        # Controlla dipendenze required
        for dep in required_deps:
            dep_weight = weights.get(dep, 1.0)
            total_weight += dep_weight
            
            if dep in available_types:
                # Dipendenza presente
                temporal_score = 1.0
                
                # Controlla tolleranza temporale se date disponibili
                if current_date and available_dates and dep in available_dates:
                    dep_date = available_dates[dep]
                    time_diff = (current_date - dep_date).days
                    
                    if time_diff < 0:
                        # Dipendenza successiva al documento corrente (violazione temporale)
                        temporal_score = 0.0
                        details['temporal_checks'][dep] = {
                            'status': 'violation',
                            'days_diff': time_diff,
                            'score': temporal_score
                        }
                    elif time_diff > tolerance_days:
                        # Dipendenza troppo vecchia
                        temporal_score = max(0.0, 1.0 - (time_diff - tolerance_days) / tolerance_days)
                        details['temporal_checks'][dep] = {
                            'status': 'tolerance_exceeded',
                            'days_diff': time_diff,
                            'score': temporal_score
                        }
                    else:
                        # Tutto OK
                        details['temporal_checks'][dep] = {
                            'status': 'ok',
                            'days_diff': time_diff,
                            'score': temporal_score
                        }
                
                total_score += dep_weight * temporal_score
                details['required_deps'][dep] = {
                    'present': True,
                    'weight': dep_weight,
                    'temporal_score': temporal_score
                }
            else:
                # Dipendenza mancante
                details['required_deps'][dep] = {
                    'present': False,
                    'weight': dep_weight,
                    'temporal_score': 0.0
                }
        
        # Controlla dipendenze optional
        for dep in optional_deps:
            dep_weight = weights.get(dep, 0.5)  # Peso inferiore per optional
            
            if dep in available_types:
                temporal_score = 1.0
                
                # Controlla tolleranza temporale se date disponibili
                if current_date and available_dates and dep in available_dates:
                    dep_date = available_dates[dep]
                    time_diff = (current_date - dep_date).days
                    
                    if time_diff < 0:
                        temporal_score = 0.0
                    elif time_diff > tolerance_days:
                        temporal_score = max(0.0, 1.0 - (time_diff - tolerance_days) / tolerance_days)
                
                total_score += dep_weight * temporal_score
                details['optional_deps'][dep] = {
                    'present': True,
                    'weight': dep_weight,
                    'temporal_score': temporal_score
                }
            else:
                # Optional mancante non penalizza
                details['optional_deps'][dep] = {
                    'present': False,
                    'weight': dep_weight,
                    'temporal_score': 1.0  # Non penalizza se mancante
                }
                total_score += dep_weight * 1.0
        
        # Calcola il punteggio finale
        if total_weight > 0:
            final_score = total_score / (total_weight + sum(weights.get(dep, 0.5) for dep in optional_deps))
        else:
            final_score = 1.0
        
        details['total_score'] = final_score
        details['total_weight'] = total_weight
        
        return final_score, details

    def identify_procedural_sequence(self, df: pd.DataFrame) -> Dict:
        """
        Identifica le sequenze procedurali nei documenti forniti.
        
        FIX 3: Versione aggiornata con supporto per scoring e tolleranze temporali.
        """
        results = {
            'sequences_found': [],
            'missing_documents': [],
            'procedural_errors': [],
            'dependency_violations': [],
            'sequence_scores': [],  # Nuovo: punteggi delle sequenze
            'dependency_scores': []  # Nuovo: punteggi delle dipendenze
        }
        
        # Convertiamo la data in formato datetime per confronti temporali
        df_copy = df.copy()
        if 'data_atto' in df_copy.columns:
            df_copy['data_parsed'] = pd.to_datetime(df_copy['data_atto'], format='%d/%m/%Y', errors='coerce')
        else:
            # Se non c' la colonna data_atto, proviamo altre possibili colonne
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
            # Solo se doc_type è 'unknown' o mancante, usiamo category come fallback
            # Ma facciamo una conversione più accurata per evitare mappature scorrette
            df_copy['normalized_type'] = df_copy.apply(lambda row: self.convert_category_to_document_type(row['category']), axis=1)
        else:
            logger.warning("Nessuna colonna 'doc_type' o 'category' trovata nei dati")
            return results
        
        # Raggruppiamo per gruppo di procedimento
        # Modifica: evitiamo di usare 'oggetto' come chiave di raggruppamento quando contiene
        # valori diversi per documenti che potrebbero far parte della stessa sequenza
        group_by = None
        if 'atto_group' in df_copy.columns:
            group_by = 'atto_group'
        elif 'cig' in df_copy.columns:
            group_by = 'cig'
        elif 'beneficiario' in df_copy.columns:
            group_by = 'beneficiario'
        elif 'project_id' in df_copy.columns:
            group_by = 'project_id'
        elif 'procedimento' in df_copy.columns:
            group_by = 'procedimento'
        elif 'oggetto' in df_copy.columns:
            # Solo se tutti i valori di 'oggetto' sono uguali, altrimenti non usiamo 'oggetto'
            # per evitare di dividere sequenze correlate in base a descrizioni diverse
            unique_objects = df_copy['oggetto'].nunique()
            # Se tutti i valori sono uguali, possiamo usare 'oggetto' come chiave
            if unique_objects == 1:
                group_by = 'oggetto'
            # Altrimenti, non usiamo 'oggetto' per evitare di dividere sequenze correlate
        else:
            group_by = None
        
        if group_by and group_by in df_copy.columns:
            for group_name, group_data in df_copy.groupby(group_by):
                sequence_analysis = self._analyze_sequence_in_group(group_data, group_name)
                results['sequences_found'].extend(sequence_analysis['sequences_found'])
                results['missing_documents'].extend(sequence_analysis['missing_documents'])
                results['procedural_errors'].extend(sequence_analysis['procedural_errors'])
                results['dependency_violations'].extend(sequence_analysis['dependency_violations'])
                results['sequence_scores'].extend(sequence_analysis.get('sequence_scores', []))
                results['dependency_scores'].extend(sequence_analysis.get('dependency_scores', []))
        else:
            # Analisi su tutto il dataset se non possiamo raggruppare
            sequence_analysis = self._analyze_sequence_in_group(df_copy, "all_documents")
            results['sequences_found'].extend(sequence_analysis['sequences_found'])
            results['missing_documents'].extend(sequence_analysis['missing_documents'])
            results['procedural_errors'].extend(sequence_analysis['procedural_errors'])
            results['dependency_violations'].extend(sequence_analysis['dependency_violations'])
            results['sequence_scores'].extend(sequence_analysis.get('sequence_scores', []))
            results['dependency_scores'].extend(sequence_analysis.get('dependency_scores', []))
        
        return results
    
    def _analyze_sequence_in_group(self, group_data: pd.DataFrame, group_name: str) -> Dict:
        """ Analizza una sequenza procedurale all'interno di un gruppo specifico.
        
        FIX 3: Versione aggiornata con scoring e tolleranze.
        """
        results = {
            'sequences_found': [],
            'missing_documents': [],
            'procedural_errors': [],
            'dependency_violations': [],
            'sequence_scores': [],
            'dependency_scores': []
        }
        
        # Estrai i tipi di documenti presenti in questo gruppo
        present_types = set(group_data['normalized_type'].dropna().unique())
        
        # Crea un dizionario con le date per ogni tipo di documento
        type_dates = {}
        if 'data_parsed' in group_data.columns:
            for _, row in group_data.iterrows():
                doc_type = row['normalized_type']
                date_val = row['data_parsed']
                if pd.notna(date_val):
                    if doc_type not in type_dates:
                        type_dates[doc_type] = []
                    type_dates[doc_type].append(date_val)
            
            # Per ogni tipo, prendi la data più recente
            for doc_type in type_dates:
                type_dates[doc_type] = max(type_dates[doc_type])
        
        # Controlla se ci sono sequenze complete
        for seq_name, seq_types in self.procedural_sequences.items():
            seq_present = [doc_type for doc_type in seq_types if doc_type in present_types]
            
            if len(seq_present) > 0:
                # Calcola il punteggio di completamento della sequenza
                completion_score = self.calculate_sequence_completion_score(seq_present, seq_types)
                
                # FIX 3: Aggiungi il punteggio di completamento ai risultati
                results['sequence_scores'].append({
                    'group': group_name,
                    'sequence_type': seq_name,
                    'completion_score': completion_score,
                    'quality': self._get_quality_from_score(completion_score),
                    'present_types': seq_present,
                    'missing_types': [doc_type for doc_type in seq_types if doc_type not in present_types]
                })
                
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
                                'completed_ratio': completion_score,
                                'quality': self._get_quality_from_score(completion_score)
                            })
                
                # Controlla eventuali documenti mancanti
                missing = [doc_type for doc_type in seq_types if doc_type not in present_types]
                if missing:
                    results['missing_documents'].append({
                        'group': group_name,
                        'sequence_type': seq_name,
                        'missing_types': missing,
                        'present_types': seq_present,
                        'completion_score': completion_score
                    })
        
        # FIX 3: Analisi avanzata delle dipendenze con pesi e tolleranze
        for _, row in group_data.iterrows():
            current_type = row['normalized_type']
            current_date = row.get('data_parsed', pd.NaT)
            
            if current_type in self.dependency_rules:
                # Calcola il punteggio di dipendenza
                dep_score, dep_details = self.calculate_dependency_score(
                    current_type, 
                    list(present_types), 
                    current_date if pd.notna(current_date) else None,
                    type_dates if type_dates else None
                )
                
                # Aggiungi i dettagli delle dipendenze ai risultati
                results['dependency_scores'].append({
                    'group': group_name,
                    'document': row.get('pdf_name', ''),
                    'document_type': current_type,
                    'dependency_score': dep_score,
                    'quality': self._get_quality_from_score(dep_score),
                    'details': dep_details
                })
                
                # Controlla violazioni di dipendenza (solo per required)
                rule = self.dependency_rules[current_type]
                required_deps = rule.get('required', [])
                
                for dep_type in required_deps:
                    # Verifica se la dipendenza esiste
                    if dep_type not in present_types:
                        results['dependency_violations'].append({
                            'group': group_name,
                            'document': row.get('pdf_name', ''),
                            'document_type': current_type,
                            'missing_dependency': dep_type,
                            'severity': 'high',  # Required missing = alta severità
                            'weight': rule.get('weights', {}).get(dep_type, 1.0)
                        })
                    elif pd.notna(current_date) and dep_type in type_dates:
                        # Controlla violazione temporale
                        dep_date = type_dates[dep_type]
                        time_diff = (current_date - dep_date).days
                        tolerance = rule.get('tolerance_days', 30)
                        
                        if time_diff < 0:
                            # La dipendenza è successiva (violazione temporale)
                            results['dependency_violations'].append({
                                'group': group_name,
                                'document': row.get('pdf_name', ''),
                                'document_type': current_type,
                                'dependency_later_than_expected': dep_type,
                                'document_date': current_date,
                                'dependency_date': dep_date,
                                'days_diff': time_diff,
                                'severity': 'critical',
                                'weight': rule.get('weights', {}).get(dep_type, 1.0)
                            })
                        elif time_diff > tolerance:
                            # Tolleranza superata
                            results['dependency_violations'].append({
                                'group': group_name,
                                'document': row.get('pdf_name', ''),
                                'document_type': current_type,
                                'dependency_too_old': dep_type,
                                'document_date': current_date,
                                'dependency_date': dep_date,
                                'days_diff': time_diff,
                                'tolerance_days': tolerance,
                                'severity': 'medium',
                                'weight': rule.get('weights', {}).get(dep_type, 1.0)
                            })
        
        return results
    
    def _get_quality_from_score(self, score: float) -> str:
        """
        Converte un punteggio in un livello di qualità.
        
        FIX 4: Implementazione del sistema di scoring con confidenza.
        """
        if score >= self.confidence_thresholds['high']:
            return "high"
        elif score >= self.confidence_thresholds['medium']:
            return "medium"
        else:
            return "low"

    def generate_procedural_report(self, results: Dict) -> str:
        """
        Genera un report testuale sull'analisi procedurale.
        
        FIX 3 & 4: Report aggiornato con punteggi e qualità.
        """
        report_lines = []
        report_lines.append("# Report Analisi Procedurale")
        report_lines.append("")
        
        # Statistiche generali
        report_lines.append("## Statistiche Generali")
        report_lines.append("")
        report_lines.append(f"- Sequenze analizzate: {len(results['sequences_found'])}")
        report_lines.append(f"- Violazioni di dipendenza: {len(results['dependency_violations'])}")
        report_lines.append(f"- Documenti mancanti: {len(results['missing_documents'])}")
        report_lines.append("")
        
        # Punteggi delle sequenze
        if results['sequence_scores']:
            report_lines.append("## Punteggi di Completamento Sequenze")
            report_lines.append("")
            
            # Calcola statistiche sui punteggi
            scores = [s['completion_score'] for s in results['sequence_scores']]
            avg_score = np.mean(scores) if scores else 0
            high_quality = sum(1 for s in results['sequence_scores'] if s['quality'] == 'high')
            medium_quality = sum(1 for s in results['sequence_scores'] if s['quality'] == 'medium')
            low_quality = sum(1 for s in results['sequence_scores'] if s['quality'] == 'low')
            
            report_lines.append(f"- Punteggio medio: {avg_score:.2%}")
            report_lines.append(f"- Alta qualità: {high_quality}")
            report_lines.append(f"- Media qualità: {medium_quality}")
            report_lines.append(f"- Bassa qualità: {low_quality}")
            report_lines.append("")
            
            for score_info in results['sequence_scores']:
                report_lines.append(f"- Gruppo: {score_info['group']}")
                report_lines.append(f"  Sequenza: {score_info['sequence_type']}")
                report_lines.append(f"  Punteggio: {score_info['completion_score']:.2%}")
                report_lines.append(f"  Qualità: {score_info['quality']}")
                report_lines.append(f"  Presenti: {', '.join(score_info['present_types'])}")
                report_lines.append(f"  Mancanti: {', '.join(score_info['missing_types'])}")
                report_lines.append("")
        
        # Punteggi delle dipendenze
        if results['dependency_scores']:
            report_lines.append("## Punteggi di Dipendenza")
            report_lines.append("")
            
            # Calcola statistiche
            dep_scores = [d['dependency_score'] for d in results['dependency_scores']]
            avg_dep_score = np.mean(dep_scores) if dep_scores else 0
            
            report_lines.append(f"- Punteggio medio dipendenze: {avg_dep_score:.2%}")
            report_lines.append("")
            
            for dep_info in results['dependency_scores']:
                if dep_info['dependency_score'] < 1.0:  # Solo mostriamo quelli con problemi
                    report_lines.append(f"- Documento: {dep_info['document']} ({dep_info['document_type']})")
                    report_lines.append(f"  Punteggio: {dep_info['dependency_score']:.2%}")
                    report_lines.append(f"  Qualità: {dep_info['quality']}")
                    
                    # Mostra dettagli delle violazioni
                    details = dep_info.get('details', {})
                    if 'required_deps' in details:
                        for dep, dep_data in details['required_deps'].items():
                            if not dep_data.get('present'):
                                report_lines.append(f"  Dipendenza mancante: {dep} (peso: {dep_data.get('weight', 1.0)})")
                    
                    if 'temporal_checks' in details:
                        for dep, check_data in details['temporal_checks'].items():
                            if check_data.get('status') != 'ok':
                                report_lines.append(f"  Problema temporale con {dep}: {check_data.get('status')} ({check_data.get('days_diff', 0)} giorni)")
                    
                    report_lines.append("")
        
        # Sequenze trovate
        if results['sequences_found']:
            report_lines.append("## Sequenze Procedurali Identificate")
            report_lines.append("")
            for seq in results['sequences_found']:
                report_lines.append(f"- Gruppo: {seq['group']}")
                report_lines.append(f"  Tipo sequenza: {seq['sequence_type']}")
                report_lines.append(f"  Completamento: {seq['completed_ratio']*100:.1f}%")
                report_lines.append(f"  Qualità: {seq['quality']}")
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
                report_lines.append(f"  Punteggio completamento: {missing.get('completion_score', 0):.2%}")
                report_lines.append("")
        
        # Violazioni di dipendenza
        if results['dependency_violations']:
            report_lines.append("## Violazioni di Dipendenza Procedurale")
            report_lines.append("")
            
            # Ordina per severità
            severity_order = {'critical': 0, 'high': 1, 'medium': 2, 'low': 3}
            sorted_violations = sorted(
                results['dependency_violations'], 
                key=lambda x: severity_order.get(x.get('severity', 'low'), 3)
            )
            
            for violation in sorted_violations:
                report_lines.append(f"- Documento: {violation['document']}")
                report_lines.append(f"  Gruppo: {violation['group']}")
                report_lines.append(f"  Tipo documento: {violation.get('document_type', 'N/D')}")
                
                if 'missing_dependency' in violation:
                    report_lines.append(f"  Dipendenza mancante: {violation['missing_dependency']} (peso: {violation.get('weight', 1.0)})")
                    report_lines.append(f"  Severità: {violation.get('severity', 'high')}")
                elif 'dependency_later_than_expected' in violation:
                    report_lines.append(f"  Dipendenza fuori sequenza: {violation['dependency_later_than_expected']}")
                    report_lines.append(f"  Data documento: {violation.get('document_date', 'N/D')}")
                    report_lines.append(f"  Data dipendenza: {violation.get('dependency_date', 'N/D')}")
                    report_lines.append(f"  Differenza giorni: {violation.get('days_diff', 0)}")
                    report_lines.append(f"  Severità: {violation.get('severity', 'critical')}")
                elif 'dependency_too_old' in violation:
                    report_lines.append(f"  Dipendenza troppo vecchia: {violation['dependency_too_old']}")
                    report_lines.append(f"  Data documento: {violation.get('document_date', 'N/D')}")
                    report_lines.append(f"  Data dipendenza: {violation.get('dependency_date', 'N/D')}")
                    report_lines.append(f"  Differenza giorni: {violation.get('days_diff', 0)}")
                    report_lines.append(f"  Tolleranza: {violation.get('tolerance_days', 30)} giorni")
                    report_lines.append(f"  Severità: {violation.get('severity', 'medium')}")
                
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
                        
                        # Controlla se c' una violazione temporale
                        if pd.notna(current_date) and pd.notna(ref_date):
                            if current_date < ref_date:  # Il documento corrente  datato prima del riferimento
                                dependencies['temporal_anomalies'].append({
                                    'document': row.get('pdf_name', ''),
                                    'refers_to': ref_doc.get('pdf_name', ''),
                                    'document_date': current_date,
                                    'reference_date': ref_date,
                                    'issue': 'Documento fa riferimento a documento futuro'
                                })
        
        return dependencies
    
    def get_dependency_rules(self) -> Dict:
        """
        Restituisce le regole di dipendenza correnti.
        """
        return self.dependency_rules
    
    def update_dependency_rule(self, doc_type: str, rule: Dict):
        """
        Aggiorna una regola di dipendenza.
        
        FIX 3: Permette l'aggiornamento dinamico delle regole.
        """
        if doc_type in self.dependency_rules:
            self.dependency_rules[doc_type].update(rule)
        else:
            self.dependency_rules[doc_type] = rule
        logger.info(f"Regola di dipendenza aggiornata per: {doc_type}")


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
    print(f"- Punteggi sequenze: {len(results['sequence_scores'])}")
    print(f"- Punteggi dipendenze: {len(results['dependency_scores'])}")
    print(f"- Documenti mancanti: {len(results['missing_documents'])}")
    print(f"- Violazioni di dipendenza: {len(results['dependency_violations'])}")
    
    # Analisi supplementare delle dipendenze
    logger.info("Inizio analisi dipendenze documenti...")
    deps = engine.analyze_document_dependencies(df)
    
    print(f"- Anomalie temporali: {len(deps['temporal_anomalies'])}")
    print(f"- Dipendenze mancanti: {len(deps['missing_dependencies'])}")


if __name__ == "__main__":
    main()