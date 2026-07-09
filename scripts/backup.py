#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Script di Backup per Albo Pretorio Audit Delivery

Esegue backup completi e incrementali dei dati del sistema.
Conforme a:
- CAD Art. 50 (Sicurezza dei dati e dei sistemi)
- D.Lgs. 33/2013 Art. 8 (Conservazione dei documenti)

Uso:
    python3 scripts/backup.py --full --output /backup/albo_pretorio_$(date +%Y%m%d).zip
    python3 scripts/backup.py --incremental --output /backup/albo_pretorio_incr_$(date +%Y%m%d).zip
    python3 scripts/backup.py --verify --path /backup/albo_pretorio_20260710.zip
"""

import os
import sys
import json
import zipfile
import shutil
import logging
import hashlib
import argparse
from pathlib import Path
from datetime import datetime
import pandas as pd

# Aggiungi il percorso src al path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

# Configura il logger
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('logs/backup.log')
    ]
)
logger = logging.getLogger(__name__)


class BackupError(Exception):
    """Eccezione per errori di backup"""
    pass


class BackupManager:
    """
    Gestore dei backup per Albo Pretorio Audit Delivery
    """
    
    def __init__(self, config: Dict = None):
        """
        Inizializza il gestore dei backup
        
        Args:
            config: Dizionario con la configurazione di backup
        """
        self.config = config or self._load_config()
        self._validate_config()
    
    def _load_config(self) -> Dict:
        """Carica la configurazione da file"""
        config_path = Path(__file__).parent.parent / "config" / "backup_config.json"
        
        if config_path.exists():
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # Configurazione predefinita
        return {
            "backup_dir": "/backup/albo_pretorio",
            "data_dir": "albo_download",
            "temp_dir": "/tmp/albo_pretorio_backup",
            "retention_days": 30,
            "max_backup_size_gb": 10,
            "compression_level": 6,
            "exclude_patterns": ["*.log", "*.tmp", ".git", "__pycache__", "*.pyc"],
            "include_patterns": ["*.pdf", "*.xml", "*.csv", "*.json", "*.joblib"],
            "database": {
                "enabled": False,
                "type": "sqlite",  # sqlite, postgres, mysql
                "path": "data/albo_pretorio.db"
            }
        }
    
    def _validate_config(self):
        """Valida la configurazione"""
        required_keys = ["backup_dir", "data_dir"]
        for key in required_keys:
            if key not in self.config:
                raise BackupError(f"Configurazione mancante: {key}")
        
        # Crea le directory se non esistono
        for dir_key in ["backup_dir", "temp_dir"]:
            if dir_key in self.config:
                Path(self.config[dir_key]).mkdir(parents=True, exist_ok=True)
    
    def create_backup(self, backup_type: str = "full", output_path: str = None) -> str:
        """
        Crea un backup del sistema
        
        Args:
            backup_type: Tipo di backup ('full' o 'incremental')
            output_path: Percorso di output (opzionale)
        
        Returns:
            str: Percorso del file di backup creato
        """
        if backup_type not in ["full", "incremental"]:
            raise BackupError(f"Tipo di backup non valido: {backup_type}")
        
        # Determina il percorso di output
        if output_path is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            output_path = Path(self.config["backup_dir"]) / f"albo_pretorio_{backup_type}_{timestamp}.zip"
        else:
            output_path = Path(output_path)
        
        # Crea la directory temporanea
        temp_dir = Path(self.config["temp_dir"]) / f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        temp_dir.mkdir(parents=True, exist_ok=True)
        
        try:
            logger.info(f"Inizio backup {backup_type} in {temp_dir}")
            
            # Esegui il backup
            if backup_type == "full":
                self._backup_full(temp_dir)
            else:
                self._backup_incremental(temp_dir)
            
            # Comprimi il backup
            self._compress_backup(temp_dir, output_path)
            
            logger.info(f"Backup completato: {output_path}")
            return str(output_path)
            
        except Exception as e:
            logger.error(f"Errore durante il backup: {e}")
            raise BackupError(f"Backup fallito: {e}")
        finally:
            # Pulisci la directory temporanea
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _backup_full(self, temp_dir: Path):
        """
        Esegue un backup completo
        
        Args:
            temp_dir: Directory temporanea per il backup
        """
        logger.info("Esecuzione backup completo...")
        
        # Backup dei dati
        self._backup_data(temp_dir)
        
        # Backup del database (se abilitato)
        if self.config.get("database", {}).get("enabled", False):
            self._backup_database(temp_dir)
        
        # Backup della configurazione
        self._backup_config(temp_dir)
        
        # Backup dei log
        self._backup_logs(temp_dir)
    
    def _backup_incremental(self, temp_dir: Path):
        """
        Esegue un backup incrementale
        
        Args:
            temp_dir: Directory temporanea per il backup
        """
        logger.info("Esecuzione backup incrementale...")
        
        # Backup dei dati modificati
        self._backup_data(temp_dir, incremental=True)
        
        # Backup del database (se abilitato)
        if self.config.get("database", {}).get("enabled", False):
            self._backup_database(temp_dir, incremental=True)
    
    def _backup_data(self, temp_dir: Path, incremental: bool = False):
        """
        Esegue il backup dei dati
        
        Args:
            temp_dir: Directory temporanea per il backup
            incremental: Se True, esegue backup incrementale
        """
        data_dir = Path(self.config["data_dir"])
        
        if not data_dir.exists():
            logger.warning(f"Directory dati non trovata: {data_dir}")
            return
        
        # Crea la struttura delle directory
        backup_data_dir = temp_dir / "data"
        backup_data_dir.mkdir(parents=True, exist_ok=True)
        
        # Copia i file
        for item in data_dir.rglob("*"):
            if item.is_file():
                # Salta i file esclusi
                if self._should_exclude(item.name):
                    continue
                
                # Salta i file non inclusi (se specificati)
                if self.config.get("include_patterns") and not self._should_include(item.name):
                    continue
                
                # Per backup incrementale, copia solo i file modificati
                if incremental:
                    if not self._is_modified_since_last_backup(item):
                        continue
                
                # Copia il file
                relative_path = item.relative_to(data_dir)
                target_path = backup_data_dir / relative_path
                target_path.parent.mkdir(parents=True, exist_ok=True)
                
                shutil.copy2(item, target_path)
                logger.debug(f"Copiato: {item} -> {target_path}")
    
    def _backup_database(self, temp_dir: Path, incremental: bool = False):
        """
        Esegue il backup del database
        
        Args:
            temp_dir: Directory temporanea per il backup
            incremental: Se True, esegue backup incrementale
        """
        db_config = self.config.get("database", {})
        db_type = db_config.get("type", "sqlite")
        
        if db_type == "sqlite":
            db_path = Path(db_config.get("path", "data/albo_pretorio.db"))
            if db_path.exists():
                backup_db_dir = temp_dir / "database"
                backup_db_dir.mkdir(parents=True, exist_ok=True)
                
                if incremental:
                    # Per SQLite, il backup incrementale non è semplice
                    # Copia l'intero database
                    shutil.copy2(db_path, backup_db_dir / db_path.name)
                else:
                    shutil.copy2(db_path, backup_db_dir / db_path.name)
                
                logger.info(f"Backup database SQLite: {db_path}")
        
        elif db_type == "postgres":
            # Implementazione per PostgreSQL
            logger.warning("Backup PostgreSQL non ancora implementato")
        
        elif db_type == "mysql":
            # Implementazione per MySQL
            logger.warning("Backup MySQL non ancora implementato")
    
    def _backup_config(self, temp_dir: Path):
        """
        Esegue il backup della configurazione
        
        Args:
            temp_dir: Directory temporanea per il backup
        """
        config_dir = Path(__file__).parent.parent / "config"
        
        if config_dir.exists():
            backup_config_dir = temp_dir / "config"
            backup_config_dir.mkdir(parents=True, exist_ok=True)
            
            for config_file in config_dir.glob("*.json"):
                shutil.copy2(config_file, backup_config_dir / config_file.name)
                logger.debug(f"Copiato config: {config_file}")
            
            logger.info("Backup configurazione completato")
    
    def _backup_logs(self, temp_dir: Path):
        """
        Esegue il backup dei log
        
        Args:
            temp_dir: Directory temporanea per il backup
        """
        logs_dir = Path(__file__).parent.parent / "logs"
        
        if logs_dir.exists():
            backup_logs_dir = temp_dir / "logs"
            backup_logs_dir.mkdir(parents=True, exist_ok=True)
            
            for log_file in logs_dir.glob("*.log"):
                shutil.copy2(log_file, backup_logs_dir / log_file.name)
                logger.debug(f"Copiato log: {log_file}")
            
            logger.info("Backup log completato")
    
    def _should_exclude(self, filename: str) -> bool:
        """
        Verifica se un file deve essere escluso dal backup
        
        Args:
            filename: Nome del file
        
        Returns:
            bool: True se il file deve essere escluso
        """
        for pattern in self.config.get("exclude_patterns", []):
            if filename == pattern or filename.endswith(pattern):
                return True
        return False
    
    def _should_include(self, filename: str) -> bool:
        """
        Verifica se un file deve essere incluso nel backup
        
        Args:
            filename: Nome del file
        
        Returns:
            bool: True se il file deve essere incluso
        """
        include_patterns = self.config.get("include_patterns", [])
        if not include_patterns:
            return True
        
        for pattern in include_patterns:
            if filename == pattern or filename.endswith(pattern):
                return True
        return False
    
    def _is_modified_since_last_backup(self, file_path: Path) -> bool:
        """
        Verifica se un file è stato modificato dall'ultimo backup
        
        Args:
            file_path: Percorso del file
        
        Returns:
            bool: True se modificato
        """
        # In un'implementazione completa, qui si confronta con l'ultimo backup
        # Per ora, restituisce True per tutti i file (backup completo)
        return True
    
    def _compress_backup(self, temp_dir: Path, output_path: Path):
        """
        Comprime il backup in un file ZIP
        
        Args:
            temp_dir: Directory temporanea con i dati da comprimere
            output_path: Percorso del file ZIP di output
        """
        logger.info(f"Compressione backup: {temp_dir} -> {output_path}")
        
        with zipfile.ZipFile(
            output_path, 
            'w', 
            zipfile.ZIP_DEFLATED, 
            compresslevel=self.config.get("compression_level", 6)
        ) as zipf:
            for root, dirs, files in os.walk(temp_dir):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(temp_dir)
                    zipf.write(file_path, arcname)
        
        logger.info(f"Backup compresso: {output_path}")
    
    def verify_backup(self, backup_path: str) -> Dict:
        """
        Verifica l'integrità di un backup
        
        Args:
            backup_path: Percorso del file di backup
        
        Returns:
            Dict: Risultato della verifica
        """
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            raise BackupError(f"File di backup non trovato: {backup_path}")
        
        results = {
            'valid': True,
            'errors': [],
            'warnings': [],
            'files': 0,
            'size': 0
        }
        
        try:
            # Verifica che il file sia un ZIP valido
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                # Conta i file
                results['files'] = len(zipf.namelist())
                
                # Calcola la dimensione
                results['size'] = sum(
                    info.file_size for info in zipf.infolist()
                )
                
                # Verifica l'integrità di ogni file
                for info in zipf.infolist():
                    try:
                        zipf.read(info.filename)
                    except Exception as e:
                        results['valid'] = False
                        results['errors'].append(f"File corrotto: {info.filename} - {e}")
                
                # Verifica la presenza di file critici
                required_files = [
                    "data/allegati_parsed.csv",
                    "data/documenti_features.csv",
                    "config/auth_config.json"
                ]
                
                for required_file in required_files:
                    if required_file not in zipf.namelist():
                        results['warnings'].append(f"File mancante: {required_file}")
            
            if results['valid']:
                logger.info(f"Backup valido: {backup_path} ({results['files']} file, {results['size']} byte)")
            else:
                logger.error(f"Backup non valido: {backup_path}")
                
        except Exception as e:
            results['valid'] = False
            results['errors'].append(f"Errore verifica: {e}")
            logger.error(f"Errore verifica backup: {e}")
        
        return results
    
    def restore_backup(self, backup_path: str, restore_dir: str = None) -> Dict:
        """
        Ripristina un backup
        
        Args:
            backup_path: Percorso del file di backup
            restore_dir: Directory di destinazione (opzionale)
        
        Returns:
            Dict: Risultato del ripristino
        """
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            raise BackupError(f"File di backup non trovato: {backup_path}")
        
        # Determina la directory di ripristino
        if restore_dir is None:
            restore_dir = Path(self.config["data_dir"]).parent
        else:
            restore_dir = Path(restore_dir)
        
        results = {
            'success': True,
            'errors': [],
            'files_restored': 0
        }
        
        try:
            # Crea la directory temporanea per l'estrazione
            temp_extract_dir = Path(self.config["temp_dir"]) / f"restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            temp_extract_dir.mkdir(parents=True, exist_ok=True)
            
            # Estrai il backup
            with zipfile.ZipFile(backup_path, 'r') as zipf:
                zipf.extractall(temp_extract_dir)
            
            # Copia i file nella directory di destinazione
            for root, dirs, files in os.walk(temp_extract_dir):
                for file in files:
                    src_path = Path(root) / file
                    relative_path = src_path.relative_to(temp_extract_dir)
                    dest_path = restore_dir / relative_path
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    try:
                        shutil.copy2(src_path, dest_path)
                        results['files_restored'] += 1
                        logger.debug(f"Ripristinato: {src_path} -> {dest_path}")
                    except Exception as e:
                        results['success'] = False
                        results['errors'].append(f"Errore ripristino {src_path}: {e}")
            
            if results['success']:
                logger.info(f"Ripristino completato: {results['files_restored']} file")
            else:
                logger.error(f"Ripristino parziale: {results['files_restored']} file ripristinati, {len(results['errors'])} errori")
            
        except Exception as e:
            results['success'] = False
            results['errors'].append(f"Errore ripristino: {e}")
            logger.error(f"Errore ripristino backup: {e}")
        finally:
            # Pulisci la directory temporanea
            shutil.rmtree(temp_extract_dir, ignore_errors=True)
        
        return results
    
    def cleanup_old_backups(self):
        """
        Pulisce i backup vecchi in base alla retention policy
        """
        backup_dir = Path(self.config["backup_dir"])
        retention_days = self.config.get("retention_days", 30)
        
        if not backup_dir.exists():
            logger.warning(f"Directory backup non trovata: {backup_dir}")
            return
        
        now = datetime.now()
        cleaned_up = []
        
        for backup_file in backup_dir.glob("*.zip"):
            # Estrai la data dal nome file (formato: albo_pretorio_full_YYYYMMDD_HHMMSS.zip)
            try:
                filename = backup_file.name
                date_str = filename.split('_')[2]  # YYYYMMDD
                backup_date = datetime.strptime(date_str, "%Y%m%d")
                
                # Calcola l'età del backup
                age_days = (now - backup_date).days
                
                if age_days > retention_days:
                    # Elimina il backup
                    backup_file.unlink()
                    cleaned_up.append(backup_file.name)
                    logger.info(f"Eliminato backup vecchio: {backup_file.name} ({age_days} giorni)")
                    
            except Exception as e:
                logger.warning(f"Errore analisi backup {backup_file.name}: {e}")
        
        if cleaned_up:
            logger.info(f"Pulizia completata: {len(cleaned_up)} backup eliminati")
        else:
            logger.info("Nessun backup vecchio da eliminare")
        
        return cleaned_up
    
    def calculate_backup_hash(self, backup_path: str) -> str:
        """
        Calcola l'hash SHA-256 di un file di backup
        
        Args:
            backup_path: Percorso del file di backup
        
        Returns:
            str: Hash SHA-256
        """
        backup_path = Path(backup_path)
        
        if not backup_path.exists():
            raise BackupError(f"File di backup non trovato: {backup_path}")
        
        # Calcola l'hash del file
        sha256_hash = hashlib.sha256()
        
        with open(backup_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        
        return sha256_hash.hexdigest()


def main():
    """
    Funzione principale per eseguire il backup da riga di comando
    """
    parser = argparse.ArgumentParser(
        description='Script di Backup per Albo Pretorio Audit Delivery'
    )
    
    # Argomenti per il backup
    parser.add_argument(
        '--full', 
        action='store_true', 
        help='Esegue un backup completo'
    )
    parser.add_argument(
        '--incremental', 
        action='store_true', 
        help='Esegue un backup incrementale'
    )
    parser.add_argument(
        '--output', 
        type=str, 
        default=None,
        help='Percorso di output per il file di backup'
    )
    
    # Argomenti per il ripristino
    parser.add_argument(
        '--restore', 
        type=str, 
        default=None,
        help='Percorso del file di backup da ripristinare'
    )
    parser.add_argument(
        '--restore-dir', 
        type=str, 
        default=None,
        help='Directory di destinazione per il ripristino'
    )
    
    # Argomenti per la verifica
    parser.add_argument(
        '--verify', 
        type=str, 
        default=None,
        help='Percorso del file di backup da verificare'
    )
    
    # Argomenti per la pulizia
    parser.add_argument(
        '--cleanup', 
        action='store_true', 
        help='Pulisce i backup vecchi'
    )
    
    # Argomenti per l'hash
    parser.add_argument(
        '--hash', 
        type=str, 
        default=None,
        help='Calcola l\'hash di un file di backup'
    )
    
    args = parser.parse_args()
    
    # Inizializza il gestore dei backup
    backup_manager = BackupManager()
    
    try:
        # Esegui backup
        if args.full or args.incremental:
            backup_type = "full" if args.full else "incremental"
            output_path = backup_manager.create_backup(
                backup_type=backup_type,
                output_path=args.output
            )
            print(f"✅ Backup {backup_type} completato: {output_path}")
            
        # Esegui ripristino
        elif args.restore:
            results = backup_manager.restore_backup(
                backup_path=args.restore,
                restore_dir=args.restore_dir
            )
            if results['success']:
                print(f"✅ Ripristino completato: {results['files_restored']} file")
            else:
                print(f"❌ Ripristino fallito: {results['errors']}")
        
        # Esegui verifica
        elif args.verify:
            results = backup_manager.verify_backup(args.verify)
            if results['valid']:
                print(f"✅ Backup valido: {args.verify}")
                print(f"   File: {results['files']}")
                print(f"   Dimensione: {results['size'] / (1024 * 1024):.2f} MB")
            else:
                print(f"❌ Backup non valido: {args.verify}")
                print(f"   Errori: {results['errors']}")
        
        # Esegui pulizia
        elif args.cleanup:
            cleaned_up = backup_manager.cleanup_old_backups()
            print(f"✅ Pulizia completata: {len(cleaned_up)} backup eliminati")
        
        # Calcola hash
        elif args.hash:
            backup_hash = backup_manager.calculate_backup_hash(args.hash)
            print(f"Hash SHA-256: {backup_hash}")
        
        else:
            parser.print_help()
            
    except BackupError as e:
        logger.error(f"❌ Errore: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"❌ Errore inaspettato: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()
