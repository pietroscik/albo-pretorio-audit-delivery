"""
Privacy Guard Module for GDPR Compliance and Sensitive Data Handling.

This module implements privacy-by-design principles for the RegTech framework,
ensuring compliance with GDPR regulations when processing public administration documents.
"""

import re
import hashlib
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from cryptography.fernet import Fernet
import json

from ..utils.config import get_config
from ..utils.logger import get_logger
from ..models.parsed_document import ParsedDocument

logger = get_logger(__name__)


class PrivacyGuard:
    """
    Privacy guard for handling sensitive data in accordance with GDPR regulations.
    Implements privacy-by-design principles for public administration document processing.
    """
    
    def __init__(self):
        self.config = get_config()
        self.encryption_key = self._get_encryption_key()
        self.cipher_suite = Fernet(self.encryption_key)
        self.sensitive_fields = {
            'personal_identifiers': [
                'nome', 'cognome', 'codice_fiscale', 'partita_iva', 
                'email', 'telefono', 'indirizzo', 'iban'
            ],
            'financial_data': [
                'importo', 'costo', 'budget', 'ammontare', 'valore'
            ],
            'contractual_data': [
                'cig', 'cup', 'numero_gara', 'protocollo'
            ]
        }
        self.pseudonymization_map = {}
        
    def _get_encryption_key(self) -> bytes:
        """Get encryption key from config or generate a new one."""
        key_path = Path(self.config.data_dir) / ".encryption_key"
        if key_path.exists():
            return key_path.read_bytes()
        else:
            key = Fernet.generate_key()
            key_path.parent.mkdir(parents=True, exist_ok=True)  # Ensure directory exists
            key_path.write_bytes(key)
            return key
    
    def pseudonymize_sensitive_data(self, text: str) -> str:
        """
        Pseudonymize sensitive data in text content.
        
        Args:
            text: Input text to pseudonymize
            
        Returns:
            Pseudonymized text
        """
        # Pattern for Italian fiscal codes
        fiscal_code_pattern = r'\b[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]\b'
        text = re.sub(fiscal_code_pattern, lambda m: self._hash_and_map(m.group()), text)
        
        # Pattern for Italian VAT numbers
        vat_pattern = r'\b[0-9]{11}\b'
        text = re.sub(vat_pattern, lambda m: self._hash_and_map(m.group()), text)
        
        # Pattern for email addresses
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
        text = re.sub(email_pattern, lambda m: self._hash_and_map(m.group()), text)
        
        # Pattern for phone numbers
        phone_pattern = r'\b(?:\+39)?\s?(?:0[0-9]{1,4}|\(0[0-9]{1,4}\))[\s\-\./]?[0-9\s\-\./]{6,10}\b'
        text = re.sub(phone_pattern, lambda m: self._hash_and_map(m.group()), text)
        
        # Pattern for IBAN
        iban_pattern = r'\b[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}\b'
        text = re.sub(iban_pattern, lambda m: self._hash_and_map(m.group()), text)
        
        return text
    
    def anonymize_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Anonymize sensitive fields in a DataFrame.
        
        Args:
            df: Input DataFrame to anonymize
            
        Returns:
            Anonymized DataFrame
        """
        df_copy = df.copy()
        
        for col in df_copy.columns:
            if any(sensitive in col.lower() for sensitive_list in self.sensitive_fields.values() 
                   for sensitive in sensitive_list):
                
                # Apply different anonymization based on data type
                if df_copy[col].dtype == 'object':
                    df_copy[col] = df_copy[col].apply(
                        lambda x: self._anonymize_field(str(x)) if pd.notna(x) else x
                    )
                elif col in self.sensitive_fields['financial_data']:
                    # For financial data, apply perturbation
                    df_copy[col] = df_copy[col].apply(
                        lambda x: self._perturb_amount(x) if pd.notna(x) else x
                    )
        
        return df_copy
    
    def encrypt_sensitive_document(self, document: ParsedDocument) -> ParsedDocument:
        """
        Encrypt sensitive parts of a parsed document.
        
        Args:
            document: Input ParsedDocument to encrypt
            
        Returns:
            Encrypted ParsedDocument
        """
        encrypted_doc = ParsedDocument()
        
        # Copy all attributes
        for attr in dir(document):
            if not attr.startswith('_') and hasattr(document, attr):
                value = getattr(document, attr)
                if isinstance(value, str) and self._is_sensitive_field(attr):
                    setattr(encrypted_doc, attr, self._encrypt_field(value))
                else:
                    setattr(encrypted_doc, attr, value)
        
        return encrypted_doc
    
    def decrypt_sensitive_document(self, document: ParsedDocument) -> ParsedDocument:
        """
        Decrypt sensitive parts of a parsed document.
        
        Args:
            document: Input ParsedDocument to decrypt
            
        Returns:
            Decrypted ParsedDocument
        """
        decrypted_doc = ParsedDocument()
        
        # Copy all attributes
        for attr in dir(document):
            if not attr.startswith('_') and hasattr(document, attr):
                value = getattr(document, attr)
                if isinstance(value, bytes) and self._is_sensitive_field(attr):
                    try:
                        decrypted_value = self.cipher_suite.decrypt(value).decode()
                        setattr(decrypted_doc, attr, decrypted_value)
                    except:
                        # If decryption fails, keep original value
                        setattr(decrypted_doc, attr, value)
                else:
                    setattr(decrypted_doc, attr, value)
        
        return decrypted_doc
    
    def apply_retention_policy(self, data_path: Path, retention_days: int = 1825) -> bool:
        """
        Apply data retention policy (default 5 years for administrative documents).
        
        Args:
            data_path: Path to data to apply retention policy
            retention_days: Number of days to retain data (default 1825 = 5 years)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            cutoff_date = datetime.now() - timedelta(days=retention_days)
            
            for file_path in data_path.rglob('*'):
                if file_path.is_file():
                    file_modified = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_modified < cutoff_date:
                        logger.info(f"Deleting expired file: {file_path}")
                        file_path.unlink()
            
            return True
        except Exception as e:
            logger.error(f"Error applying retention policy: {e}")
            return False
    
    def generate_privacy_report(self, entities: List[str]) -> Dict[str, Any]:
        """
        Generate a privacy compliance report.
        
        Args:
            entities: List of entities to include in the report
            
        Returns:
            Privacy compliance report
        """
        report = {
            'generated_at': datetime.now().isoformat(),
            'entities_processed': entities,
            'sensitive_fields_detected': [],
            'pseudonymization_applied': True,
            'data_retention_compliant': True,
            'gdpr_compliance_score': 100.0,
            'recommendations': []
        }
        
        # Add detected sensitive fields
        for entity in entities:
            entity_path = Path(self.config.data_dir) / entity
            if entity_path.exists():
                # Check for sensitive data in files
                sensitive_found = self._scan_for_sensitive_data(entity_path)
                report['sensitive_fields_detected'].extend(sensitive_found)
        
        # Calculate compliance score
        if report['sensitive_fields_detected']:
            report['gdpr_compliance_score'] = max(0, 100 - len(report['sensitive_fields_detected']) * 2)
        
        # Add recommendations
        if report['sensitive_fields_detected']:
            report['recommendations'].append(
                "Apply pseudonymization to detected sensitive fields"
            )
        
        return report
    
    def right_to_be_forgotten(self, user_identifier: str, data_path: Path) -> bool:
        """
        Implement the right to be forgotten (GDPR Art. 17).
        
        Args:
            user_identifier: Identifier of the user requesting deletion
            data_path: Path to search for user data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            deleted_count = 0
            
            # Search for files containing the user identifier
            for file_path in data_path.rglob('*'):
                if file_path.is_file() and file_path.suffix.lower() in ['.csv', '.json', '.txt']:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    
                    if user_identifier.lower() in content.lower():
                        logger.info(f"Deleting file containing user data: {file_path}")
                        file_path.unlink()
                        deleted_count += 1
            
            logger.info(f"Right to be forgotten executed: {deleted_count} files deleted")
            return True
        except Exception as e:
            logger.error(f"Error executing right to be forgotten: {e}")
            return False
    
    def _hash_and_map(self, original_value: str) -> str:
        """Hash a value and store the mapping for later reference."""
        hash_value = hashlib.sha256(original_value.encode()).hexdigest()[:12]
        self.pseudonymization_map[hash_value] = original_value
        return f"PSEUDO_{hash_value}"
    
    def _anonymize_field(self, field_value: str) -> str:
        """Anonymize a field value."""
        if pd.isna(field_value) or field_value == '':
            return field_value
        
        # For names, replace with generic placeholders
        if any(name in field_value.lower() for name in ['nome', 'cognome']):
            return 'NOME_ANONIMO'
        
        # For other sensitive data, pseudonymize
        return self.pseudonymize_sensitive_data(field_value)
    
    def _perturb_amount(self, amount: Any) -> Any:
        """Apply small perturbation to financial amounts."""
        try:
            numeric_amount = float(amount)
            # Apply small random perturbation (+/- 1%)
            import random
            perturbation = random.uniform(-0.01, 0.01)
            perturbed_amount = numeric_amount * (1 + perturbation)
            return round(perturbed_amount, 2)
        except:
            return amount
    
    def _encrypt_field(self, field_value: str) -> bytes:
        """Encrypt a field value."""
        if pd.isna(field_value) or field_value == '':
            return field_value.encode() if isinstance(field_value, str) else b''
        
        return self.cipher_suite.encrypt(field_value.encode())
    
    def _is_sensitive_field(self, field_name: str) -> bool:
        """Check if a field is considered sensitive."""
        field_lower = field_name.lower()
        return any(
            sensitive in field_lower 
            for sensitive_list in self.sensitive_fields.values() 
            for sensitive in sensitive_list
        )
    
    def _scan_for_sensitive_data(self, path: Path) -> List[str]:
        """Scan a directory for sensitive data patterns."""
        sensitive_found = []
        
        for file_path in path.rglob('*'):
            if file_path.is_file() and file_path.suffix.lower() in ['.csv', '.json', '.txt']:
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    
                    # Check for patterns
                    if re.search(r'\b[A-Z]{6}[0-9]{2}[A-Z][0-9]{2}[A-Z][0-9]{3}[A-Z]\b', content):
                        sensitive_found.append('codice_fiscale')
                    if re.search(r'\b[0-9]{11}\b', content):
                        sensitive_found.append('partita_iva')
                    if re.search(r'\b[A-Z]{2}[0-9]{2}[A-Z0-9]{1,30}\b', content):
                        sensitive_found.append('iban')
                    if re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', content):
                        sensitive_found.append('email')
                        
                except Exception as e:
                    logger.warning(f"Error scanning file {file_path}: {e}")
        
        return list(set(sensitive_found))


# Global privacy guard instance
_privacy_guard = None


def get_privacy_guard() -> PrivacyGuard:
    """
    Get the global privacy guard instance.
    
    Returns:
        PrivacyGuard instance
    """
    global _privacy_guard
    if _privacy_guard is None:
        _privacy_guard = PrivacyGuard()
    return _privacy_guard


def main():
    """Test function for privacy guard."""
    print("Testing Privacy Guard...")
    
    guard = get_privacy_guard()
    
    # Test pseudonymization
    test_text = "Contatto: Mario Rossi, CF: RSSMRA80A01H501Z, P. IVA: 12345678901, Email: mario@example.com"
    pseudonymized = guard.pseudonymize_sensitive_data(test_text)
    print(f"Original: {test_text}")
    print(f"Pseudonymized: {pseudonymized}")
    
    # Test dataframe anonymization
    df = pd.DataFrame({
        'nome': ['Mario Rossi', 'Luigi Bianchi'],
        'codice_fiscale': ['RSSMRA80A01H501Z', 'BNCGLU85B02H501Z'],
        'importo': [1000.0, 2500.5],
        'descrizione': ['Servizio', 'Fornitura']
    })
    anonymized_df = guard.anonymize_dataframe(df)
    print("\nOriginal DataFrame:")
    print(df)
    print("\nAnonymized DataFrame:")
    print(anonymized_df)


if __name__ == "__main__":
    main()