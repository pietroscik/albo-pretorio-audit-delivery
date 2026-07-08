#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modulo per la gestione centralizzata dei dati condivisi tra i moduli
Implementa un sistema di coordinamento dati che permette ai vari moduli
di scambiarsi informazioni in modo strutturato
"""

import pandas as pd
import numpy as np
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any, Union
import logging
import json
from datetime import datetime
import os
import hashlib
from dataclasses import dataclass, asdict
from enum import Enum

# Configura il logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class DataType(Enum):
    """Tipi di dati supportati nel coordinatore"""
    PARSABLE_DOCUMENTS = "atti_parsed"
    RISK_ASSESSMENT = "risk_scores"
    MANAGEMENT_KPI = "kpi_values"
    ML_MODELS = "ml_models"
    AUDIT_RESULTS = "audit_results"
    FEEDBACK_DATA = "feedback_data"
    QUALITY_METRICS = "quality_metrics"

@dataclass
class DataEntry:
    """Classe per rappresentare un'entry di dati condivisi"""
    data_type: DataType
    data: Any
    timestamp: datetime
    source_module: str
    version: str = "1.0"
    metadata: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.metadata is None:
            self.metadata = {}

class DataCoordinator:
    """
    Coordinatore centralizzato per la gestione dei dati condivisi tra i moduli
    """
    
    def __init__(self, base_path: str = None):
        self.base_path = base_path or "./data/default"
        self.data_store: Dict[str, DataEntry] = {}
        self.dependency_graph: Dict[str, List[str]] = {}
        self.change_log: List[Dict[str, Any]] = []
        
        # Crea le directory necessarie
        os.makedirs(f"{self.base_path}/shared_data", exist_ok=True)
        os.makedirs(f"{self.base_path}/report", exist_ok=True)
    
    def register_dependency(self, source_module: str, target_module: str):
        """
        Registra una dipendenza tra due moduli
        """
        if source_module not in self.dependency_graph:
            self.dependency_graph[source_module] = []
        
        if target_module not in self.dependency_graph[source_module]:
            self.dependency_graph[source_module].append(target_module)
    
    def put_data(self, key: str, data: Any, source_module: str, 
                 data_type: DataType = None, metadata: Dict[str, Any] = None) -> str:
        """
        Memorizza dati nel coordinatore con chiave specifica
        """
        if data_type is None:
            # Deduce automaticamente il tipo di dato
            if isinstance(data, pd.DataFrame):
                data_type = DataType.PARSABLE_DOCUMENTS
            elif isinstance(data, dict) and 'risk' in key.lower():
                data_type = DataType.RISK_ASSESSMENT
            elif isinstance(data, dict) and 'kpi' in key.lower():
                data_type = DataType.MANAGEMENT_KPI
            elif isinstance(data, dict) and 'model' in key.lower():
                data_type = DataType.ML_MODELS
            else:
                data_type = DataType.QUALITY_METRICS  # Tipo predefinito
        
        entry = DataEntry(
            data_type=data_type,
            data=data,
            timestamp=datetime.now(),
            source_module=source_module,
            metadata=metadata or {}
        )
        
        old_entry = self.data_store.get(key)
        self.data_store[key] = entry
        
        # Logga il cambiamento
        change_info = {
            'timestamp': datetime.now().isoformat(),
            'operation': 'PUT',
            'key': key,
            'data_type': data_type.value,
            'source_module': source_module,
            'old_exists': old_entry is not None
        }
        self.change_log.append(change_info)
        
        logger.debug(f"Dati memorizzati con chiave '{key}' dal modulo '{source_module}'")
        return key
    
    def get_data(self, key: str) -> Optional[DataEntry]:
        """
        Recupera dati dal coordinatore con chiave specifica
        """
        entry = self.data_store.get(key)
        if entry:
            # Logga il recupero
            change_info = {
                'timestamp': datetime.now().isoformat(),
                'operation': 'GET',
                'key': key,
                'data_type': entry.data_type.value,
                'target_module': 'unknown'  # Questo dovrebbe essere passato come parametro
            }
            self.change_log.append(change_info)
        
        return entry
    
    def get_data_value(self, key: str) -> Optional[Any]:
        """
        Recupera solo il valore dei dati con chiave specifica
        """
        entry = self.get_data(key)
        return entry.data if entry else None
    
    def has_data(self, key: str) -> bool:
        """
        Controlla se esistono dati con la chiave specificata
        """
        return key in self.data_store
    
    def remove_data(self, key: str) -> bool:
        """
        Rimuove dati dal coordinatore con chiave specifica
        """
        if key in self.data_store:
            del self.data_store[key]
            
            change_info = {
                'timestamp': datetime.now().isoformat(),
                'operation': 'REMOVE',
                'key': key
            }
            self.change_log.append(change_info)
            
            return True
        return False
    
    def get_data_by_type(self, data_type: DataType) -> Dict[str, DataEntry]:
        """
        Recupera tutti i dati di un certo tipo
        """
        return {key: entry for key, entry in self.data_store.items() 
                if entry.data_type == data_type}
    
    def get_data_by_source(self, source_module: str) -> Dict[str, DataEntry]:
        """
        Recupera tutti i dati provenienti da un certo modulo
        """
        return {key: entry for key, entry in self.data_store.items() 
                if entry.source_module == source_module}
    
    def get_recent_changes(self, minutes: int = 60) -> List[Dict[str, Any]]:
        """
        Recupera i cambiamenti recenti entro un certo numero di minuti
        """
        cutoff_time = datetime.now() - pd.Timedelta(minutes=minutes)
        return [change for change in self.change_log 
                if datetime.fromisoformat(change['timestamp']) > cutoff_time]
    
    def update_data(self, key: str, new_data: Any, source_module: str = None) -> bool:
        """
        Aggiorna dati esistenti mantenendo i metadati originali
        """
        if key in self.data_store:
            old_entry = self.data_store[key]
            new_entry = DataEntry(
                data_type=old_entry.data_type,
                data=new_data,
                timestamp=datetime.now(),
                source_module=source_module or old_entry.source_module,
                metadata=old_entry.metadata
            )
            self.data_store[key] = new_entry
            
            change_info = {
                'timestamp': datetime.now().isoformat(),
                'operation': 'UPDATE',
                'key': key,
                'data_type': old_entry.data_type.value,
                'source_module': source_module or old_entry.source_module
            }
            self.change_log.append(change_info)
            
            return True
        return False
    
    def get_data_dependencies(self, key: str) -> List[str]:
        """
        Ottiene i moduli che dipendono dai dati con la chiave specificata
        """
        # Cerca tutte le chiavi che contengono dati del modulo sorgente
        source_module = self.data_store.get(key).source_module if key in self.data_store else None
        if source_module and source_module in self.dependency_graph:
            return self.dependency_graph[source_module]
        return []
    
    def save_to_persistent_storage(self, key: str = None) -> bool:
        """
        Salva i dati persistenti su disco
        """
        try:
            storage_dir = f"{self.base_path}/shared_data"
            os.makedirs(storage_dir, exist_ok=True)
            
            if key:
                # Salva solo una specifica chiave
                if key in self.data_store:
                    entry = self.data_store[key]
                    file_path = f"{storage_dir}/{key}.json"
                    
                    # Serializza i dati in modo sicuro
                    serializable_data = self._make_serializable(entry.data)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump({
                            'data_type': entry.data_type.value,
                            'data': serializable_data,
                            'timestamp': entry.timestamp.isoformat(),
                            'source_module': entry.source_module,
                            'version': entry.version,
                            'metadata': entry.metadata
                        }, f, indent=2, ensure_ascii=False)
                    
                    logger.debug(f"Dati salvati su disco: {file_path}")
                    return True
            else:
                # Salva tutti i dati
                for key, entry in self.data_store.items():
                    file_path = f"{storage_dir}/{key}.json"
                    serializable_data = self._make_serializable(entry.data)
                    
                    with open(file_path, 'w', encoding='utf-8') as f:
                        json.dump({
                            'data_type': entry.data_type.value,
                            'data': serializable_data,
                            'timestamp': entry.timestamp.isoformat(),
                            'source_module': entry.source_module,
                            'version': entry.version,
                            'metadata': entry.metadata
                        }, f, indent=2, ensure_ascii=False)
                
                # Salva anche il log delle modifiche
                log_path = f"{storage_dir}/change_log.json"
                with open(log_path, 'w', encoding='utf-8') as f:
                    json.dump(self.change_log, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Tutti i dati salvati su disco in: {storage_dir}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Errore durante il salvataggio su disco: {e}")
            return False
    
    def load_from_persistent_storage(self, key: str = None) -> bool:
        """
        Carica i dati persistenti da disco
        """
        try:
            storage_dir = f"{self.base_path}/shared_data"
            if not os.path.exists(storage_dir):
                logger.info(f"Directory di archiviazione non trovata: {storage_dir}")
                return False
            
            if key:
                # Carica una specifica chiave
                file_path = f"{storage_dir}/{key}.json"
                if os.path.exists(file_path):
                    with open(file_path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    entry = DataEntry(
                        data_type=DataType(data['data_type']),
                        data=self._restore_from_serialized(data['data']),
                        timestamp=datetime.fromisoformat(data['timestamp']),
                        source_module=data['source_module'],
                        version=data.get('version', '1.0'),
                        metadata=data.get('metadata', {})
                    )
                    
                    self.data_store[key] = entry
                    logger.debug(f"Dati caricati da disco: {file_path}")
                    return True
            else:
                # Carica tutti i file nella directory
                for file_name in os.listdir(storage_dir):
                    if file_name.endswith('.json') and file_name != 'change_log.json':
                        file_path = f"{storage_dir}/{file_name}"
                        key = file_name.replace('.json', '')
                        
                        with open(file_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                        
                        entry = DataEntry(
                            data_type=DataType(data['data_type']),
                            data=self._restore_from_serialized(data['data']),
                            timestamp=datetime.fromisoformat(data['timestamp']),
                            source_module=data['source_module'],
                            version=data.get('version', '1.0'),
                            metadata=data.get('metadata', {})
                        )
                        
                        self.data_store[key] = entry
                
                # Carica anche il log delle modifiche se esiste
                log_path = f"{storage_dir}/change_log.json"
                if os.path.exists(log_path):
                    with open(log_path, 'r', encoding='utf-8') as f:
                        self.change_log = json.load(f)
                
                logger.info(f"Tutti i dati caricati da disco: {storage_dir}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"Errore durante il caricamento da disco: {e}")
            return False
    
    def _make_serializable(self, obj: Any) -> Any:
        """
        Converte un oggetto in un formato serializzabile in JSON
        """
        if isinstance(obj, pd.DataFrame):
            return {
                '__type__': 'DataFrame',
                'data': obj.to_dict(orient='records'),
                'columns': obj.columns.tolist()
            }
        elif isinstance(obj, pd.Series):
            return {
                '__type__': 'Series',
                'data': obj.to_dict(),
                'name': obj.name
            }
        elif isinstance(obj, np.ndarray):
            return {
                '__type__': 'ndarray',
                'data': obj.tolist(),
                'shape': obj.shape
            }
        elif isinstance(obj, np.integer):
            return int(obj)
        elif isinstance(obj, np.floating):
            return float(obj)
        elif isinstance(obj, np.bool_):
            return bool(obj)
        elif isinstance(obj, (list, tuple)):
            return [self._make_serializable(item) for item in obj]
        elif isinstance(obj, dict):
            return {key: self._make_serializable(value) for key, value in obj.items()}
        elif isinstance(obj, (datetime, pd.Timestamp)):
            return obj.isoformat()
        else:
            # Per oggetti complessi, cerca di convertirli in dizionario
            try:
                return str(obj)
            except:
                return repr(obj)
    
    def _restore_from_serialized(self, obj: Any) -> Any:
        """
        Ripristina un oggetto da formato serializzato
        """
        if isinstance(obj, dict) and '__type__' in obj:
            obj_type = obj['__type__']
            data = obj['data']
            
            if obj_type == 'DataFrame':
                return pd.DataFrame(data, columns=obj['columns'])
            elif obj_type == 'Series':
                ser = pd.Series(data, name=obj.get('name'))
                return ser
            elif obj_type == 'ndarray':
                return np.array(data).reshape(obj['shape'])
        
        elif isinstance(obj, dict):
            return {key: self._restore_from_serialized(value) for key, value in obj.items()}
        elif isinstance(obj, list):
            return [self._restore_from_serialized(item) for item in obj]
        elif isinstance(obj, str):
            # Prova a vedere se è un timestamp
            try:
                return datetime.fromisoformat(obj)
            except ValueError:
                return obj
        else:
            return obj
    
    def get_data_summary(self) -> Dict[str, Any]:
        """
        Ottiene un riepilogo di tutti i dati nel coordinatore
        """
        summary = {
            'total_entries': len(self.data_store),
            'data_types': {},
            'by_source': {},
            'timestamps': {
                'earliest': None,
                'latest': None
            },
            'storage_path': self.base_path
        }
        
        timestamps = []
        for key, entry in self.data_store.items():
            # Conta per tipo di dato
            dt = entry.data_type.value
            summary['data_types'][dt] = summary['data_types'].get(dt, 0) + 1
            
            # Conta per modulo sorgente
            src = entry.source_module
            summary['by_source'][src] = summary['by_source'].get(src, 0) + 1
            
            timestamps.append(entry.timestamp)
        
        if timestamps:
            summary['timestamps']['earliest'] = min(timestamps).isoformat()
            summary['timestamps']['latest'] = max(timestamps).isoformat()
        
        return summary


def get_global_data_coordinator() -> DataCoordinator:
    """
    Funzione per ottenere un'istanza singleton del coordinatore dati
    """
    if not hasattr(get_global_data_coordinator, '_instance'):
        get_global_data_coordinator._instance = DataCoordinator()
    return get_global_data_coordinator._instance


# Funzioni di utilità per l'integrazione con altri moduli
def put_module_data(module_name: str, data_key: str, data: Any, 
                   data_type: DataType = None, metadata: Dict[str, Any] = None) -> str:
    """
    Funzione di utilità per memorizzare dati da un modulo
    """
    coordinator = get_global_data_coordinator()
    return coordinator.put_data(data_key, data, module_name, data_type, metadata)


def get_module_data(data_key: str) -> Optional[DataEntry]:
    """
    Funzione di utilità per recuperare dati
    """
    coordinator = get_global_data_coordinator()
    return coordinator.get_data(data_key)


def has_module_data(data_key: str) -> bool:
    """
    Funzione di utilità per controllare l'esistenza di dati
    """
    coordinator = get_global_data_coordinator()
    return coordinator.has_data(data_key)


def update_module_data(data_key: str, new_data: Any, module_name: str = None) -> bool:
    """
    Funzione di utilità per aggiornare dati esistenti
    """
    coordinator = get_global_data_coordinator()
    return coordinator.update_data(data_key, new_data, module_name)


def main():
    """
    Funzione main per consentire l'interazione con il DataCoordinator da riga di comando
    """
    import argparse
    import json
    
    parser = argparse.ArgumentParser(description='Interfaccia CLI per il DataCoordinator')
    parser.add_argument('--ente', type=str, required=True, 
                       help='Nome dell\'ente per cui gestire i dati')
    parser.add_argument('--action', type=str, choices=['list', 'get', 'save', 'load', 'summary', 'clear'], 
                       default='summary', help='Azione da eseguire')
    parser.add_argument('--key', type=str, help='Chiave del dato da ottenere/salvare')
    parser.add_argument('--data', type=str, help='Dati da salvare in formato JSON')
    parser.add_argument('--module', type=str, help='Nome del modulo associato')
    
    args = parser.parse_args()
    
    # Ottieni l'istanza del coordinatore dati
    coordinator = get_global_data_coordinator()
    
    if args.action == 'list':
        # Lista tutte le chiavi
        keys = coordinator.list_keys()
        print(f"Chiavi disponibili: {keys}")
    
    elif args.action == 'get':
        # Ottiene un dato specifico
        if not args.key:
            print("Errore: --key richiesta per l'azione 'get'")
            return
        data = coordinator.get_data(args.key)
        if data is not None:
            print(json.dumps(data, indent=2, default=str))
        else:
            print(f"Nessun dato trovato per la chiave: {args.key}")
    
    elif args.action == 'save':
        # Salva un dato specifico
        if not args.key or not args.data:
            print("Errore: --key e --data richieste per l'azione 'save'")
            return
        try:
            parsed_data = json.loads(args.data)
            coordinator.save_data(args.key, parsed_data, args.module or 'cli')
            print(f"Dato salvato con successo per la chiave: {args.key}")
        except json.JSONDecodeError:
            print("Errore: --data deve essere un JSON valido")
    
    elif args.action == 'load':
        # Carica dati da persistenza
        coordinator.load_from_disk()
        print("Dati caricati da persistenza")
    
    elif args.action == 'clear':
        # Cancella tutti i dati
        coordinator.clear_all_data()
        print("Tutti i dati cancellati")
    
    elif args.action == 'summary':
        # Mostra sommario dei dati
        summary = coordinator.get_summary()
        print(json.dumps(summary, indent=2, default=str))


if __name__ == "__main__":
    main()
