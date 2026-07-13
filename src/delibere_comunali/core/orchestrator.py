#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Orchestrator centrale per il sistema di audit dell'albo pretorio
Coordinatore i vari moduli avanzati (Risk Assessment, KPI, ML, Audit) per consentire
uno scambio di informazioni strutturato e un ciclo di feedback continuo
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any
import logging
import json
import hashlib
import pickle
from datetime import datetime
import argparse
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache, wraps

# Import dei moduli esistenti
from ..risk_assessment.risk_calculator import DeliberaRiskAssessor
from ..management_kpi.kpi_calculator import MunicipalManagementKPI
from ..ml.model_diagnostics import StatisticalModelDiagnostics
from ..processing.audit_engine import AuditEngine  # Supponendo che esista
from ..utils.config import get_tenant_dir  # Import corretto dal modulo centralizzato

# Configura il logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_data_hash(data: pd.DataFrame) -> str:
    """
    Genera un hash univoco per un DataFrame per il caching.
    """
    if data is None or data.empty:
        return "empty_dataframe"
    
    # Usa un sottoinsieme di colonne per il calcolo dell'hash (per evitare problemi con colonne temporali)
    hashable_cols = ['pdf_name', 'oggetto', 'doc_type', 'category']
    available_cols = [col for col in hashable_cols if col in data.columns]
    
    if not available_cols:
        # Se nessuna colonna disponibile, usa tutte le colonne
        available_cols = list(data.columns)
    
    # Crea una stringa rappresentativa dei dati
    data_str = str(data[available_cols].head(100).to_dict())  # Limita a 100 righe per performance
    
    # Usa SHA-256 invece di MD5 per motivi di sicurezza
    return hashlib.sha256(data_str.encode()).hexdigest()


class ResultCache:
    """
    Classe per gestire il caching dei risultati dei moduli.
    """
    
    def __init__(self, cache_dir: str = None, max_size: int = 100):
        self.cache_dir = cache_dir or "./cache"
        self.max_size = max_size  # Numero massimo di voci in cache
        self._cache: Dict[str, Any] = {}
        self._cache_order: List[str] = []  # Per implementare LRU manualmente
        
        # Crea la directory di cache se non esiste
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Carica la cache da disco se esiste
        self._load_cache_from_disk()
    
    def _get_cache_path(self, key: str) -> str:
        """Ottiene il percorso del file di cache per una chiave."""
        return os.path.join(self.cache_dir, f"{key}.pkl")
    
    def _load_cache_from_disk(self):
        """Carica la cache da disco."""
        try:
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.pkl')]
            for cache_file in cache_files:
                key = cache_file[:-4]  # Rimuovi estensione .pkl
                cache_path = self._get_cache_path(key)
                try:
                    with open(cache_path, 'rb') as f:
                        self._cache[key] = pickle.load(f)
                    self._cache_order.append(key)
                except Exception as e:
                    logger.warning(f"Errore nel caricamento della cache per {key}: {e}")
            
            # Limita la cache alla dimensione massima
            if len(self._cache_order) > self.max_size:
                self._cache_order = self._cache_order[-self.max_size:]
                self._cache = {k: self._cache[k] for k in self._cache_order}
            
            logger.info(f"Cache caricata da disco: {len(self._cache)} voci")
        except Exception as e:
            logger.warning(f"Errore nel caricamento della cache da disco: {e}")
    
    def get(self, key: str) -> Optional[Any]:
        """Ottiene un valore dalla cache."""
        if key in self._cache:
            # Aggiorna l'ordine per LRU (sposta in fondo)
            if key in self._cache_order:
                self._cache_order.remove(key)
            self._cache_order.append(key)
            return self._cache[key]
        return None
    
    def set(self, key: str, value: Any):
        """Imposta un valore nella cache."""
        # Se la chiave esiste già, rimuovila dall'ordine
        if key in self._cache_order:
            self._cache_order.remove(key)
        
        # Aggiungi il nuovo valore
        self._cache[key] = value
        self._cache_order.append(key)
        
        # Salva su disco
        self._save_to_disk(key, value)
        
        # Rimuovi voci vecchie se superiamo la dimensione massima
        if len(self._cache_order) > self.max_size:
            oldest_key = self._cache_order.pop(0)
            del self._cache[oldest_key]
            # Rimuovi anche da disco
            try:
                os.remove(self._get_cache_path(oldest_key))
            except Exception:
                pass
    
    def _save_to_disk(self, key: str, value: Any):
        """Salva una voce di cache su disco."""
        try:
            cache_path = self._get_cache_path(key)
            with open(cache_path, 'wb') as f:
                pickle.dump(value, f)
        except Exception as e:
            logger.warning(f"Errore nel salvataggio della cache per {key}: {e}")
    
    def clear(self):
        """Svuota la cache."""
        self._cache.clear()
        self._cache_order.clear()
        
        # Rimuovi tutti i file di cache da disco
        try:
            cache_files = [f for f in os.listdir(self.cache_dir) if f.endswith('.pkl')]
            for cache_file in cache_files:
                try:
                    os.remove(os.path.join(self.cache_dir, cache_file))
                except Exception:
                    pass
        except Exception as e:
            logger.warning(f"Errore nella pulizia della cache: {e}")
    
    def get_stats(self) -> Dict:
        """Ottiene statistiche sulla cache."""
        return {
            'size': len(self._cache),
            'max_size': self.max_size,
            'cache_dir': self.cache_dir
        }


class CentralOrchestrator:
    """
    Orchestrator centrale che coordina i vari moduli avanzati del sistema
    """
    
    def __init__(self, ente: str = None, base_path: str = None, max_workers: int = 4):
        self.ente = ente
        self.base_path = base_path or self._get_default_base_path()
        self.risk_assessor = DeliberaRiskAssessor()
        self.kpi_calculator = MunicipalManagementKPI()
        self.ml_diagnostics = StatisticalModelDiagnostics()
        self.max_workers = max_workers  # Numero massimo di thread per parallelizzazione
        
        # Inizializza la cache
        cache_dir = os.path.join(self.base_path, "cache") if self.base_path else "./cache"
        self.cache = ResultCache(cache_dir=cache_dir, max_size=50)
        
        # Dati condivisi tra i moduli
        self.shared_data = {
            'atti_parsed': None,
            'risk_scores': {},
            'kpi_values': {},
            'ml_models': {},
            'audit_results': {},
            'feedback_data': None
        }
        
        # Parametri di coordinamento
        self.coordination_params = {
            'risk_kpi_feedback_enabled': True,
            'ml_model_adaptation_enabled': True,
            'dynamic_thresholds': True,
            'parallel_execution': True,  # Abilita parallelizzazione per default
            'use_caching': True  # Abilita caching per default
        }
    
    def _get_default_base_path(self) -> str:
        """Ottiene il percorso base predefinito"""
        if self.ente:
            tenant_dir = get_tenant_dir(self.ente)
            return str(tenant_dir)
        return "./data/default/albo_download"
    
    def load_shared_data(self, parsed_data_path: str = None) -> pd.DataFrame:
        """
        Carica i dati condivisi da utilizzare nei vari moduli
        """
        if parsed_data_path is None:
            # Cerca il file di dati parsati nei percorsi standard
            possible_paths = [
                f"{self.base_path}/atti_parsed.csv",
                f"{self.base_path}/atti_parsed.jsonl",
                f"{self.base_path}/documenti_features.csv",
                f"data/{self.ente}/atti_parsed.csv" if self.ente else "data/default/atti_parsed.csv"
            ]
            
            parsed_data_path = None
            for path in possible_paths:
                if os.path.exists(path):
                    parsed_data_path = path
                    break
        
        if parsed_data_path and os.path.exists(parsed_data_path):
            if parsed_data_path.endswith('.csv'):
                self.shared_data['atti_parsed'] = pd.read_csv(parsed_data_path)
            elif parsed_data_path.endswith('.jsonl'):
                self.shared_data['atti_parsed'] = pd.read_json(parsed_data_path, lines=True)
            logger.info(f"Dati condivisi caricati da: {parsed_data_path}")
        else:
            logger.warning(f"Nessun file di dati condivisi trovato in: {parsed_data_path}")
            # Crea un dataframe vuoto come fallback
            self.shared_data['atti_parsed'] = pd.DataFrame()
        
        return self.shared_data['atti_parsed']
    
    def _get_cache_key(self, module_name: str, data_hash: str) -> str:
        """Genera una chiave di cache univoca per un modulo e dati specifici."""
        return f"{module_name}_{data_hash}"
    
    def run_risk_assessment(self, data: pd.DataFrame = None, use_cache: bool = True) -> Dict:
        """
        Esegue il risk assessment utilizzando i dati forniti o quelli condivisi.
        Se use_cache è True, utilizza il caching per evitare calcoli ridondanti.
        """
        if data is None:
            data = self.shared_data['atti_parsed']
        
        if data is None or data.empty:
            logger.warning("Nessun dato disponibile per il risk assessment")
            return {}
        
        # Controlla se possiamo usare la cache
        if use_cache and self.coordination_params.get('use_caching', True):
            data_hash = get_data_hash(data)
            cache_key = self._get_cache_key('risk_assessment', data_hash)
            cached_result = self.cache.get(cache_key)
            
            if cached_result is not None:
                logger.info(f"Risultato risk assessment recuperato dalla cache per {cache_key}")
                self.shared_data['risk_scores'] = cached_result
                
                # Se abilitato, usa i risultati del risk assessment per influenzare i KPI
                if self.coordination_params['risk_kpi_feedback_enabled']:
                    self._update_kpi_parameters_from_risk(cached_result)
                
                return cached_result
        
        logger.info("Esecuzione risk assessment...")
        # Usa il metodo corretto dal modulo risk_assessment
        risk_results_df = self.risk_assessor.assess_all_delibere(data)
        
        # Converti il risultato in dizionario per la compatibilità
        risk_results = {
            'risk_by_document': risk_results_df.to_dict('records'),
            'summary_statistics': {
                'total_documents': len(risk_results_df),
                'average_risk_score': float(risk_results_df['risk_score'].mean()),
                'high_risk_count': int(len(risk_results_df[risk_results_df['risk_score'] > 70])),
                'risk_distribution': risk_results_df['risk_level'].value_counts().to_dict()
            }
        }
        
        # Salva in cache
        if use_cache and self.coordination_params.get('use_caching', True):
            data_hash = get_data_hash(data)
            cache_key = self._get_cache_key('risk_assessment', data_hash)
            self.cache.set(cache_key, risk_results)
        
        # Aggiorna i dati condivisi con i risultati del risk assessment
        self.shared_data['risk_scores'] = risk_results
        
        # Se abilitato, usa i risultati del risk assessment per influenzare i KPI
        if self.coordination_params['risk_kpi_feedback_enabled']:
            self._update_kpi_parameters_from_risk(risk_results)
        
        return risk_results
    
    def _update_kpi_parameters_from_risk(self, risk_results: Dict):
        """
        Aggiorna i parametri dei KPI in base ai risultati del risk assessment
        """
        if not risk_results or 'risk_by_document' not in risk_results:
            return
        
        avg_risk = np.mean([doc.get('final_score', 0) for doc in risk_results.get('risk_by_document', [])])
        
        # Ad esempio, se il rischio medio è alto, potrebbe essere necessario
        # adattare alcuni KPI per riflettere questa condizione
        logger.info(f"Rischio medio calcolato: {avg_risk:.2f}. Adattamento parametri KPI...")
    
    def run_kpi_calculation(self, data: pd.DataFrame = None, use_cache: bool = True) -> Dict:
        """
        Esegue il calcolo dei KPI utilizzando i dati forniti o quelli condivisi.
        Se use_cache è True, utilizza il caching per evitare calcoli ridondanti.
        """
        if data is None:
            data = self.shared_data['atti_parsed']
        
        if data is None or data.empty:
            logger.warning("Nessun dato disponibile per il calcolo KPI")
            return {}
        
        # Controlla se possiamo usare la cache
        if use_cache and self.coordination_params.get('use_caching', True):
            data_hash = get_data_hash(data)
            cache_key = self._get_cache_key('kpi_calculation', data_hash)
            cached_result = self.cache.get(cache_key)
            
            if cached_result is not None:
                logger.info(f"Risultato KPI recuperato dalla cache per {cache_key}")
                self.shared_data['kpi_values'] = cached_result
                
                # Se abilitato, usa i risultati KPI per influenzare le soglie del risk assessment
                if self.coordination_params['dynamic_thresholds']:
                    self._update_risk_thresholds_from_kpi(cached_result)
                
                return cached_result
        
        logger.info("Esecuzione calcolo KPI...")
        # Usa il metodo corretto dal modulo kpi_calculator
        kpi_results = self.kpi_calculator.generate_dashboard(data)
        
        # Salva in cache
        if use_cache and self.coordination_params.get('use_caching', True):
            data_hash = get_data_hash(data)
            cache_key = self._get_cache_key('kpi_calculation', data_hash)
            self.cache.set(cache_key, kpi_results)
        
        # Aggiorna i dati condivisi con i risultati del KPI
        self.shared_data['kpi_values'] = kpi_results
        
        # Se abilitato, usa i risultati KPI per influenzare le soglie del risk assessment
        if self.coordination_params['dynamic_thresholds']:
            self._update_risk_thresholds_from_kpi(kpi_results)
        
        return kpi_results
    
    def _update_risk_thresholds_from_kpi(self, kpi_results: Dict):
        """
        Aggiorna le soglie del risk assessment in base ai risultati KPI
        """
        # Ad esempio, se i KPI indicano bassa efficienza, potrebbe essere
        # necessario aumentare l'attenzione verso certi tipi di rischi
        efficiency_kpi = kpi_results.get('efficienza', {})
        low_efficiency = efficiency_kpi.get('tempo_medio_approvazione_gg', 0) > 30  # Esempio
        
        if low_efficiency:
            logger.info("Rilevata bassa efficienza. Adattamento soglie risk assessment...")
            # Qui potremmo modificare dinamicamente i pesi o le soglie del risk assessor
    
    def run_ml_analysis(self, data: pd.DataFrame = None, use_cache: bool = True) -> Dict:
        """
        Esegue l'analisi ML utilizzando i dati forniti o quelli condivisi.
        Se use_cache è True, utilizza il caching per evitare calcoli ridondanti.
        """
        if data is None:
            data = self.shared_data['atti_parsed']
        
        if data is None or data.empty:
            logger.warning("Nessun dato disponibile per l'analisi ML")
            return {}
        
        # Controlla se possiamo usare la cache
        if use_cache and self.coordination_params.get('use_caching', True):
            data_hash = get_data_hash(data)
            cache_key = self._get_cache_key('ml_analysis', data_hash)
            cached_result = self.cache.get(cache_key)
            
            if cached_result is not None:
                logger.info(f"Risultato ML recuperato dalla cache per {cache_key}")
                self.shared_data['ml_models'] = cached_result
                
                # Se abilitato, usa i risultati ML per influenzare il risk assessment e i KPI
                if self.coordination_params['ml_model_adaptation_enabled']:
                    self._adapt_models_based_on_ml_results(cached_result)
                
                return cached_result
        
        # Prepara i dati per l'analisi ML includendo anche i risultati del risk assessment
        processed_data = self._prepare_ml_input_data(data)
        
        logger.info("Esecuzione analisi ML...")
        
        # Esempio: esegue diagnosi statistiche del modello
        # Nota: questo è un esempio generico, l'implementazione reale dipenderà dai tuoi modelli ML
        ml_results = {}
        
        # Se abbiamo modelli ML salvati, possiamo caricarli e analizzarli
        # Altrimenti, eseguiamo solo diagnosi generali
        if len(processed_data) > 0:
            # Placeholder per l'analisi ML effettiva
            ml_results = {
                'sample_size': len(processed_data),
                'features_count': len(processed_data.select_dtypes(include=[np.number]).columns),
                'risk_correlation': self._calculate_risk_ml_correlation(processed_data)
            }
        
        # Salva in cache
        if use_cache and self.coordination_params.get('use_caching', True):
            data_hash = get_data_hash(data)
            cache_key = self._get_cache_key('ml_analysis', data_hash)
            self.cache.set(cache_key, ml_results)
        
        # Aggiorna i dati condivisi con i risultati ML
        self.shared_data['ml_models'] = ml_results
        
        # Se abilitato, usa i risultati ML per influenzare il risk assessment e i KPI
        if self.coordination_params['ml_model_adaptation_enabled']:
            self._adapt_models_based_on_ml_results(ml_results)
        
        return ml_results
    
    def _prepare_ml_input_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepara i dati per l'input ML includendo anche i risultati parziali
        """
        # Combina i dati originali con eventuali risultati già calcolati
        combined_data = data.copy()
        
        # Se abbiamo già calcolato i risk scores, aggiungiamoli come feature
        if self.shared_data['risk_scores']:
            risk_df = pd.DataFrame(self.shared_data['risk_scores'].get('risk_by_document', []))
            if not risk_df.empty and 'documento_id' in risk_df.columns:
                combined_data = combined_data.merge(risk_df[['documento_id', 'final_score']], 
                                                   on='documento_id', 
                                                   how='left', 
                                                   suffixes=('', '_risk'))
        
        return combined_data
    
    def _calculate_risk_ml_correlation(self, data: pd.DataFrame) -> Dict:
        """
        Calcola la correlazione tra i risultati del risk assessment e altre metriche ML
        """
        correlation_results = {}
        
        # Cerca colonne correlate ai risk scores
        risk_cols = [col for col in data.columns if 'risk' in col.lower() or 'score' in col.lower()]
        
        for col in risk_cols:
            if col in data.columns and pd.api.types.is_numeric_dtype(data[col]):
                # Calcola correlazioni con altre metriche
                numeric_cols = data.select_dtypes(include=[np.number]).columns
                correlations = {}
                for num_col in numeric_cols:
                    if num_col != col and not data[col].isna().all() and not data[num_col].isna().all():
                        corr_val = data[col].corr(data[num_col])
                        if not pd.isna(corr_val):
                            correlations[num_col] = corr_val
                
                if correlations:
                    correlation_results[col] = correlations
        
        return correlation_results
    
    def _adapt_models_based_on_ml_results(self, ml_results: Dict):
        """
        Adatta i modelli in base ai risultati ML
        """
        # Qui implementeremo l'adattamento dei modelli basato sui risultati ML
        logger.info("Adattamento modelli basato sui risultati ML...")
        
        # Esempio: se troviamo forti correlazioni tra risk scores e alcune variabili,
        # potremmo voler aggiustare i pesi nel risk calculator
        risk_correlations = ml_results.get('risk_correlation', {})
        
        for risk_col, correlations in risk_correlations.items():
            strong_correlations = {k: v for k, v in correlations.items() if abs(v) > 0.5}
            if strong_correlations:
                logger.info(f"Forte correlazione trovata per {risk_col}: {strong_correlations}")
                # Potremmo usare queste informazioni per aggiustare i pesi nel risk calculator
    
    def run_audit_analysis(self, data: pd.DataFrame = None, use_cache: bool = True) -> Dict:
        """
        Esegue l'analisi di audit utilizzando i dati forniti o quelli condivisi.
        Se use_cache è True, utilizza il caching per evitare calcoli ridondanti.
        """
        if data is None:
            data = self.shared_data['atti_parsed']
        
        if data is None or data.empty:
            logger.warning("Nessun dato disponibile per l'analisi di audit")
            return {}
        
        # Controlla se possiamo usare la cache
        if use_cache and self.coordination_params.get('use_caching', True):
            data_hash = get_data_hash(data)
            cache_key = self._get_cache_key('audit_analysis', data_hash)
            cached_result = self.cache.get(cache_key)
            
            if cached_result is not None:
                logger.info(f"Risultato audit recuperato dalla cache per {cache_key}")
                self.shared_data['audit_results'] = cached_result
                return cached_result
        
        # Combina i dati con i risultati degli altri moduli
        audit_input_data = self._prepare_audit_input_data(data)
        
        logger.info("Esecuzione analisi di audit...")
        
        # Placeholder per l'analisi di audit effettiva
        # Dovrà essere adattata in base all'implementazione reale di AuditEngine
        audit_results = {
            'total_documents': len(audit_input_data),
            'documents_with_risk': len(audit_input_data[audit_input_data.get('final_score', 0) > 50]) if 'final_score' in audit_input_data.columns else 0,
            'high_risk_threshold': 70
        }
        
        # Salva in cache
        if use_cache and self.coordination_params.get('use_caching', True):
            data_hash = get_data_hash(data)
            cache_key = self._get_cache_key('audit_analysis', data_hash)
            self.cache.set(cache_key, audit_results)
        
        # Aggiorna i dati condivisi con i risultati dell'audit
        self.shared_data['audit_results'] = audit_results
        
        return audit_results
    
    def _prepare_audit_input_data(self, data: pd.DataFrame) -> pd.DataFrame:
        """
        Prepara i dati per l'analisi di audit combinando tutte le informazioni disponibili
        """
        audit_data = data.copy()
        
        # Aggiungi informazioni dai risultati del risk assessment
        if self.shared_data['risk_scores'] and 'risk_by_document' in self.shared_data['risk_scores']:
            risk_df = pd.DataFrame(self.shared_data['risk_scores']['risk_by_document'])
            if not risk_df.empty and 'documento_id' in risk_df.columns:
                audit_data = audit_data.merge(risk_df, on='documento_id', how='left', suffixes=('', '_risk'))
        
        # Aggiungi informazioni dai risultati KPI se disponibili
        # Questo permette all'audit di considerare anche i KPI come fattori di rischio
        
        return audit_data
    
    def _run_single_module(self, module_name: str, data: pd.DataFrame) -> Dict:
        """
        Esegue un singolo modulo e restituisce i risultati.
        Metodo ausiliario per la parallelizzazione.
        """
        if module_name == 'risk':
            return self.run_risk_assessment(data, use_cache=True)
        elif module_name == 'kpi':
            return self.run_kpi_calculation(data, use_cache=True)
        elif module_name == 'ml':
            return self.run_ml_analysis(data, use_cache=True)
        elif module_name == 'audit':
            return self.run_audit_analysis(data, use_cache=True)
        else:
            return {}
    
    def run_full_coordination_pipeline(self, 
                                     load_data_path: str = None,
                                     skip_risk: bool = False,
                                     skip_kpi: bool = False, 
                                     skip_ml: bool = False,
                                     skip_audit: bool = False) -> Dict:
        """
        Esegue l'intero pipeline di coordinamento tra i moduli.
        Se parallel_execution è True, esegue i moduli indipendenti in parallelo.
        """
        logger.info("Inizio pipeline completo di coordinamento...")
        
        # Carica i dati condivisi
        data = self.load_shared_data(load_data_path)
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'risk_results': {},
            'kpi_results': {},
            'ml_results': {},
            'audit_results': {},
            'cache_stats': self.cache.get_stats()
        }
        
        # Determina quali moduli eseguire
        modules_to_run = []
        if not skip_risk:
            modules_to_run.append('risk')
        if not skip_kpi:
            modules_to_run.append('kpi')
        if not skip_ml:
            modules_to_run.append('ml')
        if not skip_audit:
            modules_to_run.append('audit')
        
        if self.coordination_params.get('parallel_execution', True) and len(modules_to_run) > 1:
            # Esecuzione parallela dei moduli indipendenti
            logger.info(f"Esecuzione parallela di {len(modules_to_run)} moduli con {self.max_workers} workers...")
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                # Sottometti tutti i task
                future_to_module = {
                    executor.submit(self._run_single_module, module, data): module 
                    for module in modules_to_run
                }
                
                # Processa i risultati man mano che diventano disponibili
                for future in as_completed(future_to_module):
                    module = future_to_module[future]
                    try:
                        module_results = future.result()
                        if module == 'risk':
                            results['risk_results'] = module_results
                        elif module == 'kpi':
                            results['kpi_results'] = module_results
                        elif module == 'ml':
                            results['ml_results'] = module_results
                        elif module == 'audit':
                            results['audit_results'] = module_results
                        
                        logger.info(f"Modulo '{module}' completato")
                    except Exception as exc:
                        logger.error(f"Modulo '{module}' generato un'eccezione: {exc}")
                        # In caso di errore, esegui il modulo in modo sequenziale
                        if module == 'risk':
                            results['risk_results'] = self.run_risk_assessment(data)
                        elif module == 'kpi':
                            results['kpi_results'] = self.run_kpi_calculation(data)
                        elif module == 'ml':
                            results['ml_results'] = self.run_ml_analysis(data)
                        elif module == 'audit':
                            results['audit_results'] = self.run_audit_analysis(data)
        else:
            # Esecuzione sequenziale (comportamento originale)
            logger.info("Esecuzione sequenziale dei moduli...")
            if not skip_risk:
                results['risk_results'] = self.run_risk_assessment(data)
            
            if not skip_kpi:
                results['kpi_results'] = self.run_kpi_calculation(data)
            
            if not skip_ml:
                results['ml_results'] = self.run_ml_analysis(data)
            
            if not skip_audit:
                results['audit_results'] = self.run_audit_analysis(data)
        
        # Salva i risultati coordinati
        self.save_coordinated_results(results)
        
        logger.info("Pipeline completo di coordinamento terminato.")
        return results
    
    def save_coordinated_results(self, results: Dict, output_dir: str = None):
        """
        Salva i risultati coordinati in formato strutturato
        """
        if output_dir is None:
            # Usa la directory tenant appropriata
            if self.ente:
                output_dir = str(Path(get_tenant_dir(self.ente)) / "report")
            else:
                output_dir = f"{self.base_path}/report"
            os.makedirs(output_dir, exist_ok=True)
        
        # Salva i risultati in un file JSON
        output_path = f"{output_dir}/coordinated_analysis_results.json"
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False, default=str)
        
        logger.info(f"Risultati coordinati salvati in: {output_path}")
        
        # Salva anche i singoli risultati in formato CSV se possibile
        self._save_individual_results_to_csv(results, output_dir)
    
    def _save_individual_results_to_csv(self, results: Dict, output_dir: str):
        """
        Salva i risultati individuali in formato CSV quando possibile
        """
        # Salva risk results se disponibili
        if results['risk_results'] and 'risk_by_document' in results['risk_results']:
            risk_df = pd.DataFrame(results['risk_results']['risk_by_document'])
            if not risk_df.empty:
                risk_df.to_csv(f"{output_dir}/risk_assessment_coordinated.csv", index=False)
        
        # Salva KPI results se disponibili
        if results['kpi_results']:
            kpi_df = pd.DataFrame([results['kpi_results']])
            kpi_df.to_csv(f"{output_dir}/kpi_manageriali_coordinated.csv", index=False)
    
    def get_coordination_status(self) -> Dict:
        """
        Ottiene lo stato corrente della coordinamento tra i moduli
        """
        status = {
            'modules_loaded': {
                'risk_assessor': self.risk_assessor is not None,
                'kpi_calculator': self.kpi_calculator is not None,
                'ml_diagnostics': self.ml_diagnostics is not None
            },
            'shared_data_status': {
                'atti_parsed': self.shared_data['atti_parsed'] is not None,
                'risk_scores': bool(self.shared_data['risk_scores']),
                'kpi_values': bool(self.shared_data['kpi_values']),
                'ml_models': bool(self.shared_data['ml_models']),
                'audit_results': bool(self.shared_data['audit_results'])
            },
            'coordination_params': self.coordination_params,
            'last_run_timestamp': self.shared_data.get('last_run_timestamp', None),
            'parallel_execution_enabled': self.coordination_params.get('parallel_execution', True),
            'caching_enabled': self.coordination_params.get('use_caching', True),
            'cache_stats': self.cache.get_stats()
        }
        
        return status
    
    def clear_cache(self):
        """
        Svuota la cache dei risultati.
        """
        self.cache.clear()
        logger.info("Cache svuotata")
    
    def enable_feedback_loop(self, feedback_source: str = "human_expert"):
        """
        Abilita il loop di feedback per aggiornare i modelli basandosi sui risultati
        """
        logger.info(f"Abilitazione loop di feedback da: {feedback_source}")
        
        # Qui implementeremo la logica per processare il feedback e aggiornare i modelli
        # In base ai requisiti specifici del sistema
        pass


def main():
    """
    Funzione principale per eseguire l'orchestrator da riga di comando
    """
    parser = argparse.ArgumentParser(description='Orchestrator centrale per il sistema di audit')
    parser.add_argument('--ente', type=str, required=True, help='Nome dell\'ente da analizzare')
    parser.add_argument('--base-path', type=str, default=None, help='Percorso base per i dati')
    parser.add_argument('--load-data', type=str, default=None, help='Percorso specifico per i dati parsati')
    parser.add_argument('--skip-risk', action='store_true', help='Salta l\'esecuzione del risk assessment')
    parser.add_argument('--skip-kpi', action='store_true', help='Salta l\'esecuzione del calcolo KPI')
    parser.add_argument('--skip-ml', action='store_true', help='Salta l\'esecuzione dell\'analisi ML')
    parser.add_argument('--skip-audit', action='store_true', help='Salta l\'esecuzione dell\'audit')
    parser.add_argument('--dry-run', action='store_true', help='Esegue una simulazione senza salvare risultati')
    parser.add_argument('--sequential', action='store_true', help='Forza esecuzione sequenziale (disabilita parallelizzazione)')
    parser.add_argument('--no-cache', action='store_true', help='Disabilita il caching')
    parser.add_argument('--workers', type=int, default=4, help='Numero massimo di thread worker per parallelizzazione')
    parser.add_argument('--clear-cache', action='store_true', help='Svuota la cache prima di eseguire')
    
    args = parser.parse_args()
    
    # Crea l'orchestrator
    orchestrator = CentralOrchestrator(ente=args.ente, base_path=args.base_path, max_workers=args.workers)
    
    # Disabilita la parallelizzazione se richiesto
    if args.sequential:
        orchestrator.coordination_params['parallel_execution'] = False
        logger.info("Esecuzione sequenziale forzata (parallelizzazione disabilitata)")
    
    # Disabilita il caching se richiesto
    if args.no_cache:
        orchestrator.coordination_params['use_caching'] = False
        logger.info("Caching disabilitato")
    
    # Svuota la cache se richiesto
    if args.clear_cache:
        orchestrator.clear_cache()
    
    # Esegue il pipeline completo
    results = orchestrator.run_full_coordination_pipeline(
        load_data_path=args.load_data,
        skip_risk=args.skip_risk,
        skip_kpi=args.skip_kpi,
        skip_ml=args.skip_ml,
        skip_audit=args.skip_audit
    )
    
    # Mostra un riepilogo dei risultati
    print("\n=== RIEPILOGO COORDINAMENTO ===")
    print(f"Timestamp: {results['timestamp']}")
    print(f"Risk Results: {len(results['risk_results']) if results['risk_results'] else 0} entries")
    print(f"KPI Results: {len(results['kpi_results']) if results['kpi_results'] else 0} categories")
    print(f"ML Results: {len(results['ml_results']) if results['ml_results'] else 0} entries")
    print(f"Audit Results: {len(results['audit_results']) if results['audit_results'] else 0} entries")
    print(f"Cache Stats: {results.get('cache_stats', {})}")
    
    # Mostra lo stato di coordinamento
    status = orchestrator.get_coordination_status()
    print(f"\nStato coordinamento: {status}")


if __name__ == "__main__":
    main()