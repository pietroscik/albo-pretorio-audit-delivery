"""
Modulo di autenticazione per le dashboard Streamlit
Implementa un sistema di autenticazione di base per garantire l'accesso sicuro
alle funzionalità del sistema Albo Pretorio Audit Delivery
"""
import streamlit as st
import os
from typing import Optional
import json
from datetime import datetime

# Lazy import for optional bcrypt dependency
try:
    import bcrypt
    BCRYPT_AVAILABLE = True
except ImportError:
    bcrypt = None
    BCRYPT_AVAILABLE = False


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
            except Exception as e:
                # Log the exception for debugging
                import logging
                logging.warning(f"Failed to load JSON from auth file: {e}")
                pass
        
        # Restituisce credenziali di default se il file non esiste o è corrotto
        return {}
    
    def _save_credentials(self, credentials: dict):
        """Salva le credenziali nell'archivio"""
        try:
            with open(self.credentials_file, 'w', encoding='utf-8') as f:
                json.dump(credentials, f, indent=2, ensure_ascii=False)
        except Exception as e:
            st.error(f"Errore nel salvataggio delle credenziali: {e}")
    
    def _hash_password(self, password: str) -> str:
        """Hash della password usando bcrypt se disponibile"""
        if not BCRYPT_AVAILABLE:
            # Se bcrypt non è disponibile, usa un metodo meno sicuro come fallback
            import hashlib
            return hashlib.sha256(password.encode()).hexdigest()
        
        # Usa bcrypt se disponibile
        salt = bcrypt.gensalt()
        hashed = bcrypt.hashpw(password.encode(), salt)
        return hashed.decode('utf-8')
    
    def _check_password(self, password: str, hashed: str) -> bool:
        """Verifica la password usando bcrypt se disponibile"""
        if not BCRYPT_AVAILABLE:
            # Fallback: confronto con hash SHA256
            import hashlib
            return hashlib.sha256(password.encode()).hexdigest() == hashed
        
        # Usa bcrypt per verificare la password
        return bcrypt.checkpw(password.encode(), hashed.encode())
    
    def register_user(self, username: str, password: str, role: str = "user") -> bool:
        """Registra un nuovo utente"""
        if username in self.credentials:
            return False  # Utente già esistente
        
        self.credentials[username] = {
            "password": self._hash_password(password),
            "role": role,
            "created_at": datetime.now().isoformat()
        }
        self._save_credentials(self.credentials)
        return True
    
    def login(self, username: str, password: str):
        """Effettua il login e restituisce (success, username, role)"""
        if not BCRYPT_AVAILABLE:
            st.warning("⚠️ Attenzione: Sistema di autenticazione meno sicuro attivo (bcrypt non installato)")
            st.info("Per una maggiore sicurezza, esegui: pip install bcrypt")
        
        if username not in self.credentials:
            return False, None, None
        
        stored_data = self.credentials[username]
        if self._check_password(password, stored_data["password"]):
            return True, username, stored_data.get("role", "user")
        
        return False, None, None
    
    def logout(self):
        """Effettua il logout cancellando le sessioni"""
        for key in list(st.session_state.keys()):
            if key.startswith('auth_') or key in ['authenticated', 'user_name', 'user_role']:
                del st.session_state[key]


def authenticate_user():
    """
    Funzione per autenticare l'utente con gestione delle sessioni Streamlit.
    Restituisce (authenticated, user_name, user_role).
    Se bcrypt non è disponibile, fornisce un fallback meno sicuro.
    """
    # Controlla se l'utente è già autenticato
    if 'authenticated' in st.session_state and st.session_state.authenticated:
        return st.session_state.authenticated, st.session_state.user_name, st.session_state.user_role
    
    # Se non è autenticato, mostra il form di login
    auth = SimpleAuthenticator()
    
    # Se bcrypt non è disponibile, mostra un avviso
    if not BCRYPT_AVAILABLE:
        st.warning("🔐 Modalità di autenticazione di fallback attiva (bcrypt non installato)")
        st.info("Per una maggiore sicurezza, esegui: `pip install bcrypt`")
        
        # In modalità fallback, permetti accesso diretto se non ci sono utenti registrati
        if not auth.credentials:
            # Nessun utente registrato, permetti accesso diretto
            st.session_state.authenticated = True
            st.session_state.user_name = "guest"
            st.session_state.user_role = "guest"
            return True, "guest", "guest"
    
    with st.form("login_form"):
        st.subheader("🔐 Accesso al sistema")
        username = st.text_input("Nome utente")
        password = st.text_input("Password", type="password")
        submit = st.form_submit_button("Accedi")
        
        if submit:
            if username and password:
                success, name, role = auth.login(username, password)
                if success:
                    st.session_state.authenticated = True
                    st.session_state.user_name = name
                    st.session_state.user_role = role
                    st.rerun()
                else:
                    st.error("Credenziali non valide")
            else:
                st.error("Inserisci nome utente e password")
    
    # Non autenticato
    return False, None, None


def require_auth():
    """
    Decoratore per richiedere l'autenticazione in pagine specifiche.
    Se l'utente non è autenticato, mostra la pagina di login.
    """
    authenticated, user_name, user_role = authenticate_user()
    
    if not authenticated:
        st.stop()  # Ferma l'esecuzione se non autenticato
    
    return authenticated, user_name, user_role


# Funzione per la registrazione di un nuovo utente (opzionale)
def register_new_user():
    """Form per registrare un nuovo utente"""
    auth = SimpleAuthenticator()
    
    with st.form("register_form"):
        st.subheader("Registrati")
        username = st.text_input("Nuovo nome utente")
        password = st.text_input("Nuova password", type="password")
        role = st.selectbox("Ruolo", ["user", "admin"])
        submit = st.form_submit_button("Registra")
        
        if submit:
            if username and password:
                if auth.register_user(username, password, role):
                    st.success("Utente registrato con successo!")
                else:
                    st.error("Nome utente già esistente")
            else:
                st.error("Compila tutti i campi")