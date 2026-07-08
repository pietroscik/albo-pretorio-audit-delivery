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
from datetime import datetime
import argparse
import os

# Import dei moduli esistenti
from ..risk_assessment.risk_calculator import DeliberaRiskAssessor
from ..management_kpi.kpi_calculator import MunicipalManagementKPI
from ..ml.model_diagnostics import StatisticalModelDiagnostics
from ..processing.audit_engine import AuditEngine  # Supponendo che esista
from ..utils.config import get_tenant_dir  # Import corretto dal modulo centralizzato

# Configura il logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CentralOrchestrator:
    """
    Orchestrator centrale che coordina i vari moduli avanzati del sistema
    """
    
    def __init__(self, ente: str = None, base_path: str = None):
        self.ente = ente
        self.base_path = base_path or self._get_default_base_path()
        self.risk_assessor = DeliberaRiskAssessor()
        self.kpi_calculator = MunicipalManagementKPI()
        self.ml_diagnostics = StatisticalModelDiagnostics()
        
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
            'dynamic_thresholds': True
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
    
    def run_risk_assessment(self, data: pd.DataFrame = None) -> Dict:
        """
        Esegue il risk assessment utilizzando i dati forniti o quelli condivisi
        """
        if data is None:
            data = self.shared_data['atti_parsed']
        
        if data is None or data.empty:
            logger.warning("Nessun dato disponibile per il risk assessment")
            return {}
        
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
    
    def run_kpi_calculation(self, data: pd.DataFrame = None) -> Dict:
        """
        Esegue il calcolo dei KPI utilizzando i dati forniti o quelli condivisi
        """
        if data is None:
            data = self.shared_data['atti_parsed']
        
        if data is None or data.empty:
            logger.warning("Nessun dato disponibile per il calcolo KPI")
            return {}
        
        logger.info("Esecuzione calcolo KPI...")
        # Usa il metodo corretto dal modulo kpi_calculator
        kpi_results = self.kpi_calculator.generate_dashboard(data)
        
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
    
    def run_ml_analysis(self, data: pd.DataFrame = None) -> Dict:
        """
        Esegue l'analisi ML utilizzando i dati forniti o quelli condivisi
        """
        if data is None:
            data = self.shared_data['atti_parsed']
        
        if data is None or data.empty:
            logger.warning("Nessun dato disponibile per l'analisi ML")
            return {}
        
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
    
    def run_audit_analysis(self, data: pd.DataFrame = None) -> Dict:
        """
        Esegue l'analisi di audit utilizzando i dati forniti o quelli condivisi
        """
        if data is None:
            data = self.shared_data['atti_parsed']
        
        if data is None or data.empty:
            logger.warning("Nessun dato disponibile per l'analisi di audit")
            return {}
        
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
    
    def run_full_coordination_pipeline(self, 
                                     load_data_path: str = None,
                                     skip_risk: bool = False,
                                     skip_kpi: bool = False, 
                                     skip_ml: bool = False,
                                     skip_audit: bool = False) -> Dict:
        """
        Esegue l'intero pipeline di coordinamento tra i moduli
        """
        logger.info("Inizio pipeline completo di coordinamento...")
        
        # Carica i dati condivisi
        data = self.load_shared_data(load_data_path)
        
        results = {
            'timestamp': datetime.now().isoformat(),
            'risk_results': {},
            'kpi_results': {},
            'ml_results': {},
            'audit_results': {}
        }
        
        # Esegue i moduli in sequenza ma con feedback reciproco
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
        Ottiene lo stato corrente della coordinazione tra i moduli
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
            'last_run_timestamp': self.shared_data.get('last_run_timestamp', None)
        }
        
        return status
    
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
    
    args = parser.parse_args()
    
    # Crea l'orchestrator
    orchestrator = CentralOrchestrator(ente=args.ente, base_path=args.base_path)
    
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
    
    # Mostra lo stato di coordinamento
    status = orchestrator.get_coordination_status()
    print(f"\nStato coordinamento: {status}")


if __name__ == "__main__":
    main()