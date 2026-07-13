"""
Modulo di autenticazione per le dashboard Streamlit
Implementa un sistema di autenticazione di base per garantire l'accesso sicuro
alle funzionalità del sistema Albo Pretorio Audit Delivery
"""
import streamlit as st
import bcrypt
import os
from typing import Optional
import json
from datetime import datetime


class SimpleAuthenticator:
    """
    Classe per la gestione di un semplice sistema di autenticazione
    per le dashboard Streamlit
    """
    
    def __init__(self, credentials_file: str = "users.json"):
        self.credentials_file = credentials_file
        self.credentials = self._load_credentials()
    
    def _load_credentials(self) -> dict:
        """Carica le credenziali dall'archivio"""
        if os.path.exists(self.credentials_file):
            try:
                with open(self.credentials_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        
        # Usa credenziali di default se non esiste il file
        default_password = os.getenv("DEFAULT_ADMIN_PASSWORD", "admin123")
        hashed = bcrypt.hashpw(default_password.encode('utf-8'), bcrypt.gensalt())
        
        default_credentials = {
            "usernames": {
                "admin": {
                    "name": "Amministratore",
                    "password": hashed.decode('utf-8'),
                    "role": "admin",
                    "created_at": datetime.now().isoformat()
                }
            }
        }
        
        self._save_credentials(default_credentials)
        return default_credentials
    
    def _save_credentials(self, credentials: dict):
        """Salva le credenziali nell'archivio"""
        try:
            with open(self.credentials_file, 'w', encoding='utf-8') as f:
                json.dump(credentials, f, indent=2, ensure_ascii=False)
        except Exception as e:
            st.error(f"Errore nel salvataggio delle credenziali: {e}")
    
    def login(self, username: str, password: str) -> tuple[bool, Optional[str], Optional[str]]:
        """
        Esegue il login e restituisce (success, name, role)
        """
        if username in self.credentials.get("usernames", {}):
            stored_hash = self.credentials["usernames"][username]["password"]
            if bcrypt.checkpw(password.encode('utf-8'), stored_hash.encode('utf-8')):
                name = self.credentials["usernames"][username]["name"]
                role = self.credentials["usernames"][username].get("role", "user")
                return True, name, role
        
        return False, None, None
    
    def logout(self):
        """Esegue il logout"""
        st.session_state.authentication_status = False
        st.session_state.username = None
        st.session_state.name = None
        st.session_state.role = None
    
    def register_user(self, username: str, name: str, password: str, role: str = "user") -> bool:
        """Registra un nuovo utente"""
        if username in self.credentials.get("usernames", {}):
            return False  # Utente già esistente
        
        hashed = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt())
        
        if "usernames" not in self.credentials:
            self.credentials["usernames"] = {}
        
        self.credentials["usernames"][username] = {
            "name": name,
            "password": hashed.decode('utf-8'),
            "role": role,
            "created_at": datetime.now().isoformat()
        }
        
        self._save_credentials(self.credentials)
        return True


def authenticate_user():
    """
    Funzione helper per autenticare l'utente in Streamlit
    """
    # Inizializza lo stato di sessione se non esiste
    if 'authentication_status' not in st.session_state:
        st.session_state.authentication_status = None
        st.session_state.username = None
        st.session_state.name = None
        st.session_state.role = None
    
    auth = SimpleAuthenticator()
    
    if st.session_state.authentication_status:
        # Utente già autenticato
        return True, st.session_state.name, st.session_state.role
    else:
        # Mostra il form di login
        st.header("Accesso Sicuro")
        st.write("Inserisci le tue credenziali per accedere al sistema")
        
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        col1, col2 = st.columns([1, 1])
        with col1:
            login_button = st.button("Accedi")
        with col2:
            reset_button = st.button("Reset")
        
        if reset_button:
            st.session_state.authentication_status = None
            st.experimental_rerun()
        
        if login_button:
            if username and password:
                success, name, role = auth.login(username, password)
                if success:
                    st.session_state.authentication_status = True
                    st.session_state.username = username
                    st.session_state.name = name
                    st.session_state.role = role
                    st.success(f"Benvenuto, {name}!")
                    st.experimental_rerun()
                else:
                    st.error("Credenziali non valide")
            else:
                st.warning("Inserisci username e password")
        
        return False, None, None


def require_authentication(func):
    """
    Decoratore per richiedere l'autenticazione per accedere a una pagina
    """
    def wrapper(*args, **kwargs):
        authenticated, name, role = authenticate_user()
        if authenticated:
            return func(*args, **kwargs)
        else:
            st.info("Effettua il login per accedere a questa pagina")
            return None
    return wrapper