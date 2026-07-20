#!/usr/bin/env python3
"""
Script per creare un utente amministratore per la dashboard Streamlit.

Questo script è utile per la configurazione iniziale del sistema,
quando non è ancora stato creato nessun utente.
"""
import argparse
import sys
from pathlib import Path

# Aggiungi la root del progetto al path per permettere l'import di 'src'
project_root = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(project_root))

try:
    from src.delibere_comunali.web.auth import SimpleAuthenticator
except ImportError:
    print("Errore: Impossibile importare il modulo di autenticazione.")
    print("Assicurati di eseguire lo script dalla cartella principale del progetto (es. python scripts/create_admin_user.py ...)")
    sys.exit(1)

def main():
    parser = argparse.ArgumentParser(description="Crea un utente amministratore per la dashboard.")
    parser.add_argument("--username", default="admin", help="Nome utente per l'amministratore (default: admin)")
    parser.add_argument("--password", required=True, help="Password per l'amministratore")
    
    args = parser.parse_args()
    
    auth = SimpleAuthenticator()
    
    if auth.register_user(args.username, args.password, role="admin"):
        print(f"\n✅ Utente amministratore '{args.username}' creato con successo!")
        print("\nOra puoi usare queste credenziali per accedere alla dashboard.")
    else:
        print(f"\n⚠️ L'utente '{args.username}' esiste già.")

if __name__ == "__main__":
    main()