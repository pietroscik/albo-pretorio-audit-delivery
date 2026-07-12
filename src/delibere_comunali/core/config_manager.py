#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Enterprise Configuration Manager
Unifica tutti i sistemi di configurazione del progetto in un'unica interfaccia
per facilitare la gestione dei parametri in ambienti enterprise
"""

import json
import os
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, asdict
from datetime import datetime
import logging

from ..utils.config import AppConfig, get_config
from .data_coordinator import DataCoordinator
from .orchestrator import CentralOrchestrator

# Configura il logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class EnterpriseParams:
    """
    Struttura dati per i parametri enterprise
    """
    # Parametri generali
    ente: str = "default"
    base_path: str = "./data/default/albo_download"
    output_path: str = "./output"
    
    # Parametri di coordinamento
    enable_coordination: bool = True
    enable_parallel_processing: bool = True
    max_workers: int = 4
    enable_caching: bool = True
    
    # Parametri di analisi
    skip_risk_assessment: bool = False
    skip_kpi_calculation: bool = False
    skip_ml_analysis: bool = False
    skip_audit: bool = False
    
    # Parametri di performance
    batch_size: int = 10
    chunk_size: int = 512
    similarity_threshold: float = 0.7
    
    # Parametri di debug
    dry_run: bool = False
    verbose: bool = False
    log_level: str = "INFO"


class ConfigManager:
    """
    Gestore centralizzato per tutti i parametri del sistema enterprise
    """
    
    def __init__(self, ente: str = None, base_path: str = None):
        self.ente = ente or os.getenv("ENTE", "default")
        self.base_path = base_path or os.getenv("BASE_PATH", f"./data/{self.ente}/albo_download")
        
        # Carica la configurazione di base
        self.app_config = get_config()
        
        # Inizializza il coordinatore dati
        self.data_coordinator = DataCoordinator(base_path=self.base_path)
        
        # Inizializza i parametri enterprise
        self.enterprise_params = EnterpriseParams(
            ente=self.ente,
            base_path=self.base_path
        )
        
        # Percorso per il file di configurazione persistente
        self.config_file_path = Path(self.base_path) / "config" / "enterprise_config.json"
        self.config_file_path.parent.mkdir(parents=True, exist_ok=True)
    
    def update_params(self, **kwargs):
        """
        Aggiorna i parametri enterprise con i valori forniti
        """
        for key, value in kwargs.items():
            if hasattr(self.enterprise_params, key):
                setattr(self.enterprise_params, key, value)
                logger.debug(f"Aggiornato parametro {key} = {value}")
            else:
                logger.warning(f"Il parametro {key} non esiste in EnterpriseParams")
    
    def load_from_file(self, config_path: str = None) -> bool:
        """
        Carica la configurazione da un file JSON
        """
        path = Path(config_path) if config_path else self.config_file_path
        
        if not path.exists():
            logger.info(f"File di configurazione non trovato: {path}")
            return False
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                config_data = json.load(f)
            
            # Aggiorna i parametri enterprise
            for key, value in config_data.get('enterprise_params', {}).items():
                if hasattr(self.enterprise_params, key):
                    setattr(self.enterprise_params, key, value)
            
            # Aggiorna la configurazione applicativa se presente
            app_config_data = config_data.get('app_config', {})
            if app_config_data:
                logger.info("Caricamento configurazione applicativa non implementato direttamente, "
                           "aggiornare manualmente i parametri ambiente")
            
            logger.info(f"Configurazione caricata da: {path}")
            return True
        except Exception as e:
            logger.error(f"Errore nel caricamento della configurazione da {path}: {e}")
            return False
    
    def save_to_file(self, config_path: str = None) -> bool:
        """
        Salva la configurazione corrente in un file JSON
        """
        path = Path(config_path) if config_path else self.config_file_path
        
        config_data = {
            'timestamp': datetime.now().isoformat(),
            'ente': self.ente,
            'base_path': str(self.base_path),
            'enterprise_params': asdict(self.enterprise_params),
            'app_config_summary': {
                'scraper_enabled': True,
                'ocr_enabled': self.app_config.ocr.tesseract_cmd is not None,
                'llm_enabled': self.app_config.llm.api_key is not None,
                'rag_enabled': True,
                'performance_settings': {
                    'max_workers': self.app_config.performance.max_workers,
                    'batch_size': self.app_config.performance.batch_size,
                    'cache_enabled': self.app_config.performance.cache_enabled
                }
            }
        }
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(config_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Configurazione salvata in: {path}")
            return True
        except Exception as e:
            logger.error(f"Errore nel salvataggio della configurazione in {path}: {e}")
            return False
    
    def get_active_config(self) -> Dict[str, Any]:
        """
        Ottiene la configurazione attiva in formato dizionario
        """
        return {
            'enterprise_params': asdict(self.enterprise_params),
            'app_config': {
                'scraper': {
                    'base_url': self.app_config.scraper.base_url,
                    'delay': self.app_config.scraper.delay,
                    'timeout': self.app_config.scraper.timeout,
                    'max_pages': self.app_config.scraper.max_pages
                },
                'ocr': {
                    'tesseract_cmd': self.app_config.ocr.tesseract_cmd,
                    'lang': self.app_config.ocr.lang,
                    'enabled': self.app_config.ocr.tesseract_cmd is not None
                },
                'llm': {
                    'api_key_set': self.app_config.llm.api_key is not None,
                    'model_priority': self.app_config.llm.model_priority,
                    'temperature': self.app_config.llm.temperature
                },
                'rag': {
                    'chunk_size': self.app_config.rag.chunk_size,
                    'similarity_threshold': self.app_config.rag.similarity_threshold,
                    'top_k': self.app_config.rag.top_k
                },
                'performance': {
                    'max_workers': self.app_config.performance.max_workers,
                    'batch_size': self.app_config.performance.batch_size,
                    'cache_enabled': self.app_config.performance.cache_enabled
                }
            },
            'paths': {
                'ente': self.ente,
                'base_path': str(self.base_path),
                'data_dir': str(self.app_config.data_dir),
                'output_dir': str(self.app_config.output_dir),
                'cache_dir': str(self.app_config.cache_dir)
            }
        }
    
    def create_orchestrator(self) -> CentralOrchestrator:
        """
        Crea un orchestrator configurato secondo i parametri enterprise
        """
        orchestrator = CentralOrchestrator(
            ente=self.ente,
            base_path=self.base_path,
            max_workers=self.enterprise_params.max_workers
        )
        
        # Configura i parametri di coordinamento
        orchestrator.coordination_params.update({
            'risk_kpi_feedback_enabled': True,
            'ml_model_adaptation_enabled': True,
            'dynamic_thresholds': True,
            'parallel_execution': self.enterprise_params.enable_parallel_processing,
            'use_caching': self.enterprise_params.enable_caching
        })
        
        return orchestrator
    
    def validate_config(self) -> Dict[str, Any]:
        """
        Valida la configurazione corrente e restituisce uno stato
        """
        validation_results = {
            'ente_valid': self.ente and len(self.ente.strip()) > 0,
            'base_path_exists': Path(self.base_path).exists(),
            'required_dirs_exist': {
                'data': (Path(self.base_path) / "atti_parsed.csv").exists() or 
                         (Path(self.base_path) / "atti_parsed.jsonl").exists(),
                'config': self.config_file_path.parent.exists()
            },
            'services_available': {
                'ocr': self.app_config.ocr.tesseract_cmd is not None,
                'llm': self.app_config.llm.api_key is not None,
                'cache': self.app_config.performance.cache_enabled
            },
            'param_consistency': {
                'max_workers_valid': 1 <= self.enterprise_params.max_workers <= 16,
                'batch_size_valid': 1 <= self.enterprise_params.batch_size <= 100,
                'threshold_valid': 0.0 <= self.enterprise_params.similarity_threshold <= 1.0
            }
        }
        
        # Calcola lo stato complessivo
        validation_results['overall_status'] = all([
            validation_results['ente_valid'],
            validation_results['base_path_exists'],
            all(validation_results['required_dirs_exist'].values()),
            all(validation_results['param_consistency'].values())
        ])
        
        return validation_results
    
    def get_param_recommendations(self) -> Dict[str, Any]:
        """
        Fornisce raccomandazioni sui parametri in base alle risorse disponibili
        """
        import psutil
        import multiprocessing
        
        cpu_count = multiprocessing.cpu_count()
        memory_gb = round(psutil.virtual_memory().total / (1024**3), 2)
        
        recommendations = {
            'max_workers': min(cpu_count, 8),  # Non più di 8 per evitare overload
            'batch_size': 10 if memory_gb >= 8 else 5,  # Batch più piccoli per sistemi con poca RAM
            'enable_parallel_processing': cpu_count > 1,
            'enable_caching': True,
            'similarity_threshold': 0.7 if memory_gb >= 16 else 0.6,
            'system_specs': {
                'cpu_cores': cpu_count,
                'memory_gb': memory_gb
            }
        }
        
        return recommendations


def get_enterprise_config(ente: str = None, base_path: str = None) -> ConfigManager:
    """
    Funzione factory per ottenere un'istanza del ConfigManager
    """
    if not hasattr(get_enterprise_config, '_instance'):
        get_enterprise_config._instance = {}
    
    key = f"{ente or 'default'}_{base_path or 'default'}"
    
    if key not in get_enterprise_config._instance:
        get_enterprise_config._instance[key] = ConfigManager(ente, base_path)
    
    return get_enterprise_config._instance[key]


def main():
    """
    Funzione main per la gestione della configurazione da riga di comando
    """
    import argparse
    
    parser = argparse.ArgumentParser(description='Gestore configurazione enterprise')
    parser.add_argument('--ente', type=str, required=True, help='Nome dell\'ente')
    parser.add_argument('--base-path', type=str, help='Percorso base per i dati')
    parser.add_argument('--action', type=str, choices=['show', 'save', 'load', 'validate', 'recommend'], 
                       default='show', help='Azione da eseguire')
    parser.add_argument('--config-path', type=str, help='Percorso specifico per il file di configurazione')
    parser.add_argument('--update-param', nargs=2, metavar=('KEY', 'VALUE'), 
                       action='append', help='Aggiorna un parametro specifico (usa ripetutamente)')
    
    args = parser.parse_args()
    
    # Crea il gestore configurazione
    config_manager = get_enterprise_config(args.ente, args.base_path)
    
    # Aggiorna i parametri se specificati
    if args.update_param:
        updates = {}
        for key, value in args.update_param:
            # Converti il valore al tipo appropriato
            if value.lower() in ('true', 'false'):
                value = value.lower() == 'true'
            elif value.isdigit():
                value = int(value)
            elif '.' in value and value.replace('.', '').replace('-', '').isdigit():
                value = float(value)
            updates[key] = value
        
        config_manager.update_params(**updates)
    
    if args.action == 'show':
        config = config_manager.get_active_config()
        print(json.dumps(config, indent=2, default=str))
    
    elif args.action == 'save':
        success = config_manager.save_to_file(args.config_path)
        print(f"Salvataggio {'riuscito' if success else 'fallito'}")
    
    elif args.action == 'load':
        success = config_manager.load_from_file(args.config_path)
        print(f"Caricamento {'riuscito' if success else 'fallito'}")
    
    elif args.action == 'validate':
        validation = config_manager.validate_config()
        print(json.dumps(validation, indent=2, default=str))
    
    elif args.action == 'recommend':
        recommendations = config_manager.get_param_recommendations()
        print(json.dumps(recommendations, indent=2, default=str))


if __name__ == "__main__":
    main()