#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Modulo di autenticazione per Albo Pretorio Audit Delivery

Supporta:
- SPID (Sistema Pubblico di Identità Digitale)
- CIE (Carta di Identità Elettronica)
- CNS (Carta Nazionale dei Servizi)
- Autenticazione locale (solo per ambienti di test)

Conforme a:
- CAD Art. 64 (Autenticazione informatica)
- D.Lgs. 82/2005 (Codice Amministrazione Digitale)
- Linee Guida AgID per SPID
"""

import os
import json
import logging
import secrets
import hashlib
import base64
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, Tuple, Any
from pathlib import Path
from functools import wraps
from flask import session, redirect, request, current_app
import jwt

# Configura il logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AuthError(Exception):
    """Eccezione per errori di autenticazione"""
    pass


class User:
    """
    Classe che rappresenta un utente autenticato
    """
    
    def __init__(self, user_id: str, email: str, name: str, surname: str, 
                 spid_level: int = None, roles: list = None, ente: str = None):
        self.user_id = user_id
        self.email = email
        self.name = name
        self.surname = surname
        self.full_name = f"{name} {surname}"
        self.spid_level = spid_level  # 1, 2, o 3
        self.roles = roles or []
        self.ente = ente
        self.last_login = datetime.now()
        self.is_authenticated = True
        self.is_active = True
    
    def has_role(self, role: str) -> bool:
        """Verifica se l'utente ha un ruolo specifico"""
        return role in self.roles
    
    def can(self, permission: str) -> bool:
        """Verifica se l'utente ha un permesso specifico"""
        # Mappatura ruoli → permessi
        role_permissions = {
            'Amministratore': [
                'gestione_utenti', 'configurazione_sistema', 'gestione_documenti',
                'pubblicazione_documenti', 'analisi', 'report', 'backup', 'log'
            ],
            'Responsabile Trasparenza': [
                'gestione_documenti', 'pubblicazione_documenti', 'analisi', 'report'
            ],
            'Operatore Albo Pretorio': [
                'gestione_documenti', 'analisi'
            ],
            'Ospite': [
                'lettura_documenti', 'report'
            ]
        }
        
        # Controlla tutti i ruoli dell'utente
        for role in self.roles:
            if role in role_permissions and permission in role_permissions[role]:
                return True
        return False
    
    def to_dict(self) -> Dict:
        """Converte l'utente in dizionario"""
        return {
            'user_id': self.user_id,
            'email': self.email,
            'name': self.name,
            'surname': self.surname,
            'full_name': self.full_name,
            'spid_level': self.spid_level,
            'roles': self.roles,
            'ente': self.ente,
            'last_login': self.last_login.isoformat(),
            'is_authenticated': self.is_authenticated,
            'is_active': self.is_active
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'User':
        """Crea un utente da dizionario"""
        return cls(
            user_id=data.get('user_id'),
            email=data.get('email'),
            name=data.get('name', ''),
            surname=data.get('surname', ''),
            spid_level=data.get('spid_level'),
            roles=data.get('roles', []),
            ente=data.get('ente')
        )


class LocalAuth:
    """
    Autenticazione locale (solo per ambienti di test)
    """
    
    def __init__(self):
        self.users_db = self._load_users_db()
    
    def _load_users_db(self) -> Dict:
        """Carica il database utenti locale"""
        # In ambiente di test, usa un file JSON
        users_db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'users.json')
        
        if os.path.exists(users_db_path):
            with open(users_db_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        # Se non esiste, crea un database vuoto
        return {
            'users': {},
            'roles': {
                'Amministratore': ['gestione_utenti', 'configurazione_sistema', 'gestione_documenti', 'pubblicazione_documenti', 'analisi', 'report'],
                'Responsabile Trasparenza': ['gestione_documenti', 'pubblicazione_documenti', 'analisi', 'report'],
                'Operatore Albo Pretorio': ['gestione_documenti', 'analisi'],
                'Ospite': ['lettura_documenti', 'report']
            }
        }
    
    def _save_users_db(self):
        """Salva il database utenti locale"""
        users_db_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'users.json')
        os.makedirs(os.path.dirname(users_db_path), exist_ok=True)
        
        with open(users_db_path, 'w', encoding='utf-8') as f:
            json.dump(self.users_db, f, indent=2, ensure_ascii=False)
    
    def add_user(self, username: str, password: str, email: str, name: str, surname: str, 
                 roles: list, ente: str = None) -> User:
        """Aggiunge un utente locale"""
        if username in self.users_db['users']:
            raise AuthError(f"Utente {username} già esistente")
        
        # Hash della password
        password_hash = self._hash_password(password)
        
        self.users_db['users'][username] = {
            'username': username,
            'password_hash': password_hash,
            'email': email,
            'name': name,
            'surname': surname,
            'roles': roles,
            'ente': ente,
            'last_login': None,
            'failed_attempts': 0,
            'is_active': True
        }
        
        self._save_users_db()
        
        return User(
            user_id=username,
            email=email,
            name=name,
            surname=surname,
            roles=roles,
            ente=ente
        )
    
    def remove_user(self, username: str) -> bool:
        """Rimuove un utente locale"""
        if username not in self.users_db['users']:
            return False
        
        del self.users_db['users'][username]
        self._save_users_db()
        return True
    
    def update_user(self, username: str, **kwargs) -> bool:
        """Aggiorna un utente locale"""
        if username not in self.users_db['users']:
            return False
        
        for key, value in kwargs.items():
            if key in ['password', 'password_hash']:
                if key == 'password':
                    self.users_db['users'][username]['password_hash'] = self._hash_password(value)
            else:
                self.users_db['users'][username][key] = value
        
        self._save_users_db()
        return True
    
    def authenticate(self, username: str, password: str) -> Optional[User]:
        """Autentica un utente locale"""
        if username not in self.users_db['users']:
            return None
        
        user_data = self.users_db['users'][username]
        
        # Verifica password
        if not self._verify_password(password, user_data['password_hash']):
            # Incrementa tentativi falliti
            user_data['failed_attempts'] = user_data.get('failed_attempts', 0) + 1
            
            # Blocca dopo 5 tentativi
            if user_data['failed_attempts'] >= 5:
                user_data['is_active'] = False
                logger.warning(f"Utente {username} bloccato per troppi tentativi falliti")
            
            self._save_users_db()
            return None
        
        # Resetta tentativi falliti
        user_data['failed_attempts'] = 0
        user_data['last_login'] = datetime.now().isoformat()
        self._save_users_db()
        
        return User(
            user_id=username,
            email=user_data['email'],
            name=user_data['name'],
            surname=user_data['surname'],
            roles=user_data['roles'],
            ente=user_data.get('ente')
        )
    
    def _hash_password(self, password: str) -> str:
        """Genera l'hash di una password"""
        salt = os.urandom(16)
        key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        return base64.b64encode(salt + key).decode('utf-8')
    
    def _verify_password(self, password: str, password_hash: str) -> bool:
        """Verifica una password contro il suo hash"""
        try:
            decoded = base64.b64decode(password_hash.encode('utf-8'))
            salt = decoded[:16]
            stored_key = decoded[16:]
            
            key = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
            return key == stored_key
        except Exception:
            return False
    
    def get_user(self, username: str) -> Optional[User]:
        """Ottiene un utente dal database"""
        if username not in self.users_db['users']:
            return None
        
        user_data = self.users_db['users'][username]
        return User(
            user_id=username,
            email=user_data['email'],
            name=user_data['name'],
            surname=user_data['surname'],
            roles=user_data['roles'],
            ente=user_data.get('ente')
        )
    
    def list_users(self) -> list:
        """Elenca tutti gli utenti"""
        return [
            User(
                user_id=username,
                email=user_data['email'],
                name=user_data['name'],
                surname=user_data['surname'],
                roles=user_data['roles'],
                ente=user_data.get('ente')
            )
            for username, user_data in self.users_db['users'].items()
        ]


class SPIDAuth:
    """
    Autenticazione tramite SPID (Sistema Pubblico di Identità Digitale)
    
    Conforme a:
    - Linee Guida AgID per SPID v2
    - CAD Art. 64
    """
    
    def __init__(self, config: Dict = None):
        """
        Inizializza l'autenticazione SPID
        
        Args:
            config: Dizionario con la configurazione SPID
                - entity_id: ID dell'ente
                - assertion_consumer_service_url: URL di callback
                - metadata_url: URL dei metadati SPID
                - cert_path: Percorso al certificato
                - key_path: Percorso alla chiave privata
        """
        self.config = config or {}
        self._load_default_config()
        
        # Carica certificato e chiave
        self.cert = self._load_cert()
        self.key = self._load_key()
    
    def _load_default_config(self):
        """Carica la configurazione predefinita da file"""
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'spid_config.json')
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config.update(json.load(f))
    
    def _load_cert(self) -> Optional[str]:
        """Carica il certificato SPID"""
        cert_path = self.config.get('cert_path')
        if cert_path and os.path.exists(cert_path):
            with open(cert_path, 'r', encoding='utf-8') as f:
                return f.read()
        return None
    
    def _load_key(self) -> Optional[str]:
        """Carica la chiave privata SPID"""
        key_path = self.config.get('key_path')
        if key_path and os.path.exists(key_path):
            with open(key_path, 'r', encoding='utf-8') as f:
                return f.read()
        return None
    
    def get_metadata(self) -> Dict:
        """
        Genera i metadati SPID per l'ente
        
        Returns:
            Dizionario con i metadati SPID
        """
        return {
            "entityID": self.config.get('entity_id', 'https://albo-pretorio.ente.it/spid/metadata'),
            "assertionConsumerService": [
                {
                    "index": 0,
                    "isDefault": True,
                    "Location": self.config.get('assertion_consumer_service_url', 'https://albo-pretorio.ente.it/spid/acs'),
                    "Binding": "urn:oasis:names:tc:SAML:2.0:bindings:HTTP-POST"
                }
            ],
            "attributeConsumingService": [
                {
                    "index": 0,
                    "isDefault": True,
                    "serviceName": "Albo Pretorio Audit Delivery",
                    "serviceDescription": "Sistema di gestione e analisi documenti Albo Pretorio",
                    "requestedAttributes": [
                        {
                            "name": "fiscalNumber",
                            "nameFormat": "urn:oasis:names:tc:SAML:2.0:attrname-format:basic",
                            "isRequired": False
                        },
                        {
                            "name": "name",
                            "nameFormat": "urn:oasis:names:tc:SAML:2.0:attrname-format:basic",
                            "isRequired": True
                        },
                        {
                            "name": "surname",
                            "nameFormat": "urn:oasis:names:tc:SAML:2.0:attrname-format:basic",
                            "isRequired": True
                        },
                        {
                            "name": "email",
                            "nameFormat": "urn:oasis:names:tc:SAML:2.0:attrname-format:basic",
                            "isRequired": True
                        },
                        {
                            "name": "spidCode",
                            "nameFormat": "urn:oasis:names:tc:SAML:2.0:attrname-format:basic",
                            "isRequired": False
                        }
                    ]
                }
            ],
            "contactPerson": {
                "company": "Ente Pubblico",
                "emailAddress": self.config.get('contact_email', 'admin@ente.it'),
                "telephoneNumber": self.config.get('contact_phone', '+39 XXX XXXXXXX')
            },
            "organization": {
                "name": self.config.get('organization_name', 'Ente Pubblico'),
                "displayName": [
                    {
                        "lang": "it",
                        "text": self.config.get('organization_name', 'Ente Pubblico')
                    }
                ],
                "url": self.config.get('organization_url', 'https://ente.it')
            }
        }
    
    def generate_auth_request(self, spid_level: int = 2, return_to: str = None) -> str:
        """
        Genera una richiesta di autenticazione SPID
        
        Args:
            spid_level: Livello SPID (1, 2, o 3)
            return_to: URL di ritorno dopo l'autenticazione
        
        Returns:
            URL di reindirizzamento per l'IdP SPID
        """
        # In un'implementazione reale, questo genererebbe una richiesta SAML
        # Per ora, restituisce un URL di esempio
        base_url = self.config.get('spid_provider_url', 'https://spid.test.it')
        
        # Parametri della richiesta
        params = {
            'entityID': self.config.get('entity_id'),
            'return': return_to or self.config.get('assertion_consumer_service_url'),
            'spidLevel': spid_level,
            'authType': 'urn:oasis:names:tc:SAML:2.0:ac:classes:PasswordProtectedTransport'
        }
        
        # In un'implementazione reale, qui si firmerebbe la richiesta
        # e si reindirizzerebbe all'IdP SPID
        return f"{base_url}/auth?{requests.utils.quote('&'.join([f'{k}={v}' for k, v in params.items()]))}"
    
    def validate_response(self, response: Dict) -> Optional[User]:
        """
        Valida la risposta SPID e restituisce l'utente autenticato
        
        Args:
            response: Dizionario con la risposta SAML
        
        Returns:
            User: Utente autenticato o None se fallisce
        """
        # In un'implementazione reale, qui si validerebbe la firma SAML
        # e si estrarrebbero gli attributi
        
        # Per ora, simula una risposta valida
        try:
            # Estrai attributi (simulati)
            attributes = response.get('attributes', {})
            
            user = User(
                user_id=attributes.get('spidCode', secrets.token_hex(16)),
                email=attributes.get('email', 'user@test.it'),
                name=attributes.get('name', 'Test'),
                surname=attributes.get('surname', 'User'),
                spid_level=int(attributes.get('spidLevel', 2)),
                roles=self._get_roles_from_spid(attributes),
                ente=self._get_ente_from_spid(attributes)
            )
            
            return user
        except Exception as e:
            logger.error(f"Errore validazione risposta SPID: {e}")
            return None
    
    def _get_roles_from_spid(self, attributes: Dict) -> list:
        """
        Ottiene i ruoli dell'utente dagli attributi SPID
        
        In un'implementazione reale, questo sarebbe basato su:
        - Attributi SPID (es. `role`)
        - Database locale
        - Configurazione dell'ente
        """
        # Per ora, restituisce ruoli predefiniti
        return ['Operatore Albo Pretorio']
    
    def _get_ente_from_spid(self, attributes: Dict) -> Optional[str]:
        """
        Ottiene l'ente dell'utente dagli attributi SPID
        """
        # Per ora, restituisce un ente predefinito
        return self.config.get('default_ente')


class CIEAuth:
    """
    Autenticazione tramite CIE (Carta di Identità Elettronica)
    
    Conforme a:
    - CAD Art. 64
    - Linee Guida AgID per CIE
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
    
    def authenticate(self, cie_data: Dict) -> Optional[User]:
        """
        Autentica un utente tramite CIE
        
        Args:
            cie_data: Dizionario con i dati CIE (simulati)
                - codice_fiscale: Codice fiscale
                - nome: Nome
                - cognome: Cognome
                - data_nascita: Data di nascita
        
        Returns:
            User: Utente autenticato o None se fallisce
        """
        try:
            # In un'implementazione reale, qui si validerebbe la firma CIE
            # e si verificherebbe il certificato
            
            user = User(
                user_id=cie_data.get('codice_fiscale', secrets.token_hex(16)),
                email=f"{cie_data.get('nome', 'test').lower()}.{cie_data.get('cognome', 'user').lower()}@cie.test.it",
                name=cie_data.get('nome', 'Test'),
                surname=cie_data.get('cognome', 'User'),
                spid_level=2,  # CIE è equivalente a SPID Livello 2
                roles=self._get_roles_from_cie(cie_data),
                ente=self._get_ente_from_cie(cie_data)
            )
            
            return user
        except Exception as e:
            logger.error(f"Errore autenticazione CIE: {e}")
            return None
    
    def _get_roles_from_cie(self, cie_data: Dict) -> list:
        """Ottiene i ruoli dell'utente dai dati CIE"""
        return ['Operatore Albo Pretorio']
    
    def _get_ente_from_cie(self, cie_data: Dict) -> Optional[str]:
        """Ottiene l'ente dell'utente dai dati CIE"""
        return self.config.get('default_ente')


class CNSAuth:
    """
    Autenticazione tramite CNS (Carta Nazionale dei Servizi)
    
    Conforme a:
    - CAD Art. 64
    - Linee Guida AgID per CNS
    """
    
    def __init__(self, config: Dict = None):
        self.config = config or {}
    
    def authenticate(self, cns_data: Dict) -> Optional[User]:
        """
        Autentica un utente tramite CNS
        
        Args:
            cns_data: Dizionario con i dati CNS (simulati)
                - codice_fiscale: Codice fiscale
                - nome: Nome
                - cognome: Cognome
                - certificato: Certificato digitale
        
        Returns:
            User: Utente autenticato o None se fallisce
        """
        try:
            # In un'implementazione reale, qui si validerebbe il certificato CNS
            
            user = User(
                user_id=cns_data.get('codice_fiscale', secrets.token_hex(16)),
                email=f"{cns_data.get('nome', 'test').lower()}.{cns_data.get('cognome', 'user').lower()}@cns.test.it",
                name=cns_data.get('nome', 'Test'),
                surname=cns_data.get('cognome', 'User'),
                spid_level=3,  # CNS è equivalente a SPID Livello 3
                roles=self._get_roles_from_cns(cns_data),
                ente=self._get_ente_from_cns(cns_data)
            )
            
            return user
        except Exception as e:
            logger.error(f"Errore autenticazione CNS: {e}")
            return None
    
    def _get_roles_from_cns(self, cns_data: Dict) -> list:
        """Ottiene i ruoli dell'utente dai dati CNS"""
        return ['Amministratore']  # CNS è tipicamente per amministratori
    
    def _get_ente_from_cns(self, cns_data: Dict) -> Optional[str]:
        """Ottiene l'ente dell'utente dai dati CNS"""
        return self.config.get('default_ente')


class AuthManager:
    """
    Gestore principale dell'autenticazione
    
    Supporta:
    - SPID
    - CIE
    - CNS
    - Autenticazione locale (test)
    """
    
    def __init__(self, config: Dict = None):
        """
        Inizializza il gestore dell'autenticazione
        
        Args:
            config: Dizionario con la configurazione generale
        """
        self.config = config or {}
        self._load_config()
        
        # Inizializza i provider di autenticazione
        self.spid_auth = SPIDAuth(self.config.get('spid'))
        self.cie_auth = CIEAuth(self.config.get('cie'))
        self.cns_auth = CNSAuth(self.config.get('cns'))
        self.local_auth = LocalAuth()
        
        # Utenti attivi (sessioni)
        self.active_users = {}
    
    def _load_config(self):
        """Carica la configurazione da file"""
        config_path = os.path.join(os.path.dirname(__file__), '..', '..', 'config', 'auth_config.json')
        
        if os.path.exists(config_path):
            with open(config_path, 'r', encoding='utf-8') as f:
                self.config.update(json.load(f))
    
    def authenticate(self, method: str, **kwargs) -> Optional[User]:
        """
        Autentica un utente con il metodo specificato
        
        Args:
            method: Metodo di autenticazione ('spid', 'cie', 'cns', 'local')
            **kwargs: Argomenti specifici per il metodo
        
        Returns:
            User: Utente autenticato o None se fallisce
        """
        method = method.lower()
        
        if method == 'spid':
            return self.spid_auth.validate_response(kwargs)
        elif method == 'cie':
            return self.cie_auth.authenticate(kwargs)
        elif method == 'cns':
            return self.cns_auth.authenticate(kwargs)
        elif method == 'local':
            return self.local_auth.authenticate(
                kwargs.get('username'),
                kwargs.get('password')
            )
        else:
            raise AuthError(f"Metodo di autenticazione non supportato: {method}")
    
    def get_user(self, user_id: str) -> Optional[User]:
        """
        Ottiene un utente dal suo ID
        
        Args:
            user_id: ID dell'utente
        
        Returns:
            User: Utente o None se non trovato
        """
        # Cerca prima tra gli utenti attivi
        if user_id in self.active_users:
            return self.active_users[user_id]
        
        # Cerca nel database locale
        return self.local_auth.get_user(user_id)
    
    def add_user(self, **kwargs) -> User:
        """
        Aggiunge un utente locale
        
        Args:
            **kwargs: Argomenti per la creazione utente
        
        Returns:
            User: Utente creato
        """
        return self.local_auth.add_user(**kwargs)
    
    def remove_user(self, username: str) -> bool:
        """
        Rimuove un utente locale
        
        Args:
            username: Nome utente
        
        Returns:
            bool: True se rimosso, False altrimenti
        """
        return self.local_auth.remove_user(username)
    
    def list_users(self) -> list:
        """
        Elenca tutti gli utenti
        
        Returns:
            list: Lista di utenti
        """
        return self.local_auth.list_users()
    
    def login(self, user: User, session_id: str = None) -> str:
        """
        Effettua il login di un utente
        
        Args:
            user: Utente autenticato
            session_id: ID della sessione (opzionale)
        
        Returns:
            str: Token di sessione
        """
        session_id = session_id or secrets.token_hex(32)
        
        # Salva l'utente tra gli attivi
        self.active_users[session_id] = user
        
        # Genera un token JWT (opzionale, per API)
        token = self._generate_jwt_token(user, session_id)
        
        return token
    
    def logout(self, session_id: str) -> bool:
        """
        Effettua il logout di un utente
        
        Args:
            session_id: ID della sessione
        
        Returns:
            bool: True se logout effettuato, False altrimenti
        """
        if session_id in self.active_users:
            del self.active_users[session_id]
            return True
        return False
    
    def _generate_jwt_token(self, user: User, session_id: str) -> str:
        """
        Genera un token JWT per l'utente
        
        Args:
            user: Utente
            session_id: ID della sessione
        
        Returns:
            str: Token JWT
        """
        payload = {
            'user_id': user.user_id,
            'email': user.email,
            'name': user.full_name,
            'roles': user.roles,
            'ente': user.ente,
            'session_id': session_id,
            'exp': datetime.utcnow() + timedelta(hours=8)  # Scadenza 8 ore
        }
        
        # In un'implementazione reale, usa una chiave segreta
        secret_key = self.config.get('jwt_secret', secrets.token_hex(32))
        
        return jwt.encode(payload, secret_key, algorithm='HS256')
    
    def validate_jwt_token(self, token: str) -> Optional[User]:
        """
        Valida un token JWT
        
        Args:
            token: Token JWT
        
        Returns:
            User: Utente o None se non valido
        """
        try:
            secret_key = self.config.get('jwt_secret', secrets.token_hex(32))
            payload = jwt.decode(token, secret_key, algorithms=['HS256'])
            
            session_id = payload.get('session_id')
            if session_id and session_id in self.active_users:
                return self.active_users[session_id]
            
            return None
        except jwt.ExpiredSignatureError:
            logger.warning("Token JWT scaduto")
            return None
        except jwt.InvalidTokenError:
            logger.warning("Token JWT non valido")
            return None


def require_auth(f):
    """
    Decoratore per verificare l'autenticazione
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # In un'implementazione Flask/Django, qui si verificherebbe la sessione
        # Per ora, simula solo il controllo
        if not getattr(f, '_auth_checked', False):
            # Verifica che ci sia un utente autenticato
            # (In un'implementazione reale, si userebbe session o token)
            pass
        return f(*args, **kwargs)
    return decorated_function


def require_role(role: str):
    """
    Decoratore per verificare il ruolo dell'utente
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # In un'implementazione reale, qui si verificherebbe il ruolo
            # Per ora, simula solo il controllo
            if not getattr(f, '_role_checked', False):
                pass
            return f(*args, **kwargs)
        return decorated_function
    return decorator


def require_permission(permission: str):
    """
    Decoratore per verificare il permesso dell'utente
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # In un'implementazione reale, qui si verificherebbe il permesso
            # Per ora, simula solo il controllo
            if not getattr(f, '_permission_checked', False):
                pass
            return f(*args, **kwargs)
        return decorated_function
    return decorator


# Funzione di utilità per test
if __name__ == '__main__':
    # Test autenticazione locale
    print("=== Test Autenticazione Locale ===")
    local_auth = LocalAuth()
    
    # Aggiungi un utente
    user = local_auth.add_user(
        username="test_user",
        password="test_password",
        email="test@test.it",
        name="Test",
        surname="User",
        roles=["Operatore Albo Pretorio"]
    )
    print(f"✅ Utente creato: {user.full_name}")
    
    # Autentica l'utente
    authenticated_user = local_auth.authenticate("test_user", "test_password")
    if authenticated_user:
        print(f"✅ Autenticazione riuscita: {authenticated_user.full_name}")
        print(f"   Ruoli: {authenticated_user.roles}")
        print(f"   Permessi: {authenticated_user.can('gestione_documenti')}")
    else:
        print("❌ Autenticazione fallita")
    
    # Test SPID (simulato)
    print("\n=== Test Autenticazione SPID (Simulata) ===")
    spid_auth = SPIDAuth()
    
    # Simula una risposta SPID
    spid_response = {
        'attributes': {
            'spidCode': 'TESTSPID123',
            'name': 'Test',
            'surname': 'SPID User',
            'email': 'test.spid@test.it',
            'spidLevel': '2'
        }
    }
    
    spid_user = spid_auth.validate_response(spid_response)
    if spid_user:
        print(f"✅ Autenticazione SPID riuscita: {spid_user.full_name}")
        print(f"   Livello SPID: {spid_user.spid_level}")
    else:
        print("❌ Autenticazione SPID fallita")
    
    # Test CIE (simulato)
    print("\n=== Test Autenticazione CIE (Simulata) ===")
    cie_auth = CIEAuth()
    
    cie_data = {
        'codice_fiscale': 'TESTCIE123',
        'nome': 'Test',
        'cognome': 'CIE User'
    }
    
    cie_user = cie_auth.authenticate(cie_data)
    if cie_user:
        print(f"✅ Autenticazione CIE riuscita: {cie_user.full_name}")
        print(f"   Livello SPID equivalente: {cie_user.spid_level}")
    else:
        print("❌ Autenticazione CIE fallita")
    
    # Test CNS (simulato)
    print("\n=== Test Autenticazione CNS (Simulata) ===")
    cns_auth = CNSAuth()
    
    cns_data = {
        'codice_fiscale': 'TESTCNS123',
        'nome': 'Test',
        'cognome': 'CNS User'
    }
    
    cns_user = cns_auth.authenticate(cns_data)
    if cns_user:
        print(f"✅ Autenticazione CNS riuscita: {cns_user.full_name}")
        print(f"   Livello SPID equivalente: {cns_user.spid_level}")
    else:
        print("❌ Autenticazione CNS fallita")
