"""
CLI commands for Active Learning functionality.
"""

import click
import sys
import json
from pathlib import Path


def add_active_learning_commands(cli):
    """Add Active Learning commands to the Click CLI group."""
    
    @cli.command()
    @click.option('--base', default='data/baiano/albo_download', help='Cartella base dei dati.')
    @click.option('--ente', default=None, help='Identificativo ente (opzionale)')
    @click.option('--min-feedback', default=50, type=int, help='Numero minimo di feedback per retraining')
    def retrain-with-feedback(base: str, ente: str, min_feedback: int):
        """
        Retraina il modello ML con i feedback raccolti.
        
        ACTIVE LEARNING: Usa i feedback degli utenti per migliorare il modello.
        """
        try:
            from delibere_comunali.ml.feedback_handler import get_feedback_manager
            from delibere_comunali.utils.config import get_tenant_dir
            
            effective_ente = ente or 'baiano'
            effective_base = Path(base) if base else get_tenant_dir(effective_ente) / "albo_download"
            
            if not effective_base.exists():
                print(f"❌ Cartella base non trovata: {effective_base}")
                return
            
            print(f"🚀 Avvio retraining con feedback per {effective_ente}")
            
            manager = get_feedback_manager()
            
            # Controlla quanti feedback abbiamo
            feedback_count = manager.feedback_store.get_feedback_count()
            print(f"   Feedback disponibili: {feedback_count}")
            
            if feedback_count < min_feedback:
                print(f"   ⚠️  Servono almeno {min_feedback} feedback per il retraining")
                return
            
            # Retraina il modello
            success = manager.enhance_existing_model()
            
            if success:
                print(f"✅ Modello retrainato con successo con {feedback_count} feedback")
            else:
                print(f"❌ Errore durante il retraining")
            
        except Exception as e:
            print(f"❌ Errore durante il retraining con feedback: {e}", file=sys.stderr)
    
    @cli.command()
    @click.option('--base', default='data/baiano/albo_download', help='Cartella base dei dati.')
    @click.option('--ente', default=None, help='Identificativo ente (opzionale)')
    def show-feedback-stats(base: str, ente: str):
        """
        Mostra le statistiche dei feedback raccolti.
        
        ACTIVE LEARNING: Visualizza lo stato dei feedback per Active Learning.
        """
        try:
            from delibere_comunali.ml.feedback_handler import get_feedback_manager
            from delibere_comunali.utils.config import get_tenant_dir
            
            effective_ente = ente or 'baiano'
            effective_base = Path(base) if base else get_tenant_dir(effective_ente) / "albo_download"
            
            if not effective_base.exists():
                print(f"❌ Cartella base non trovata: {effective_base}")
                return
            
            print(f"📊 Statistiche Feedback per {effective_ente}")
            print("=" * 50)
            
            manager = get_feedback_manager()
            stats = manager.get_feedback_stats()
            
            print(f"\n📦 Totale Feedback: {stats['total_feedback']}")
            print(f"👥 Utenti Unici: {stats['users']}")
            print(f"📄 Documenti Unici: {stats['documents']}")
            
            if stats['categories']:
                print(f"\n📋 Feedback per Categoria:")
                for category, count in sorted(stats['categories'].items(), key=lambda x: x[1], reverse=True):
                    print(f"   {category}: {count}")
            
            if stats['latest_feedback']:
                print(f"\n⏰ Ultimo Feedback: {stats['latest_feedback']}")
            
            # Controlla se possiamo retrainare
            if stats['total_feedback'] >= 50:
                print(f"\n✅ Abbastanza feedback per retraining ({stats['total_feedback']} >= 50)")
            else:
                print(f"\n⚠️  Servono {50 - stats['total_feedback']} feedback in più per retraining")
            
        except Exception as e:
            print(f"❌ Errore durante il caricamento delle statistiche: {e}", file=sys.stderr)
    
    @cli.command()
    @click.option('--base', default='data/baiano/albo_download', help='Cartella base dei dati.')
    @click.option('--ente', default=None, help='Identificativo ente (opzionale)')
    @click.option('--output', default='feedback_requests.json', help='File di output per le richieste')
    def generate-feedback-requests(base: str, ente: str, output: str):
        """
        Genera un file con le richieste di feedback per documenti incerti.
        
        ACTIVE LEARNING: Identifica documenti con bassa confidenza.
        """
        try:
            from delibere_comunali.processing.post_process_classification_active import (
                get_active_learning_post_processor
            )
            from delibere_comunali.utils.config import get_tenant_dir
            import pandas as pd
            
            effective_ente = ente or 'baiano'
            effective_base = Path(base) if base else get_tenant_dir(effective_ente) / "albo_download"
            
            if not effective_base.exists():
                print(f"❌ Cartella base non trovata: {effective_base}")
                return
            
            # Carica i dati
            allegati_path = effective_base / "allegati_parsed.csv"
            if not allegati_path.exists():
                print(f"❌ File allegati_parsed.csv non trovato in {effective_base}")
                return
            
            print(f"🚀 Generazione richieste feedback per {effective_ente}")
            
            df = pd.read_csv(allegati_path)
            print(f"   Documenti caricati: {len(df)}")
            
            # Crea il post-processor con Active Learning
            post_processor = get_active_learning_post_processor()
            
            # Identifica documenti incerti
            uncertain_df = post_processor.identify_uncertain_predictions(df)
            print(f"   Documenti incerti: {len(uncertain_df)}")
            
            # Genera richieste di feedback
            feedback_requests = post_processor.request_feedback_for_uncertain(df)
            
            # Salva le richieste
            output_path = Path(output)
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(feedback_requests, f, indent=2, ensure_ascii=False)
            
            print(f"✅ Salvate {len(feedback_requests)} richieste di feedback in {output_path}")
            
        except Exception as e:
            print(f"❌ Errore durante la generazione delle richieste: {e}", file=sys.stderr)
    
    @cli.command()
    @click.option('--feedback-file', required=True, help='File JSON con i feedback da applicare')
    @click.option('--base', default='data/baiano/albo_download', help='Cartella base dei dati.')
    @click.option('--ente', default=None, help='Identificativo ente (opzionale)')
    def apply-feedback(base: str, ente: str, feedback_file: str):
        """
        Applica i feedback da un file JSON e aggiorna i dati.
        
        ACTIVE LEARNING: Applica correzioni utente e retrain modello.
        """
        try:
            from delibere_comunali.processing.post_process_classification_active import (
                get_active_learning_post_processor,
                Feedback
            )
            from delibere_comunali.utils.config import get_tenant_dir
            import pandas as pd
            import json
            
            effective_ente = ente or 'baiano'
            effective_base = Path(base) if base else get_tenant_dir(effective_ente) / "albo_download"
            
            if not effective_base.exists():
                print(f"❌ Cartella base non trovata: {effective_base}")
                return
            
            # Carica i dati
            allegati_path = effective_base / "allegati_parsed.csv"
            if not allegati_path.exists():
                print(f"❌ File allegati_parsed.csv non trovato in {effective_base}")
                return
            
            # Carica i feedback
            feedback_path = Path(feedback_file)
            if not feedback_path.exists():
                print(f"❌ File feedback non trovato: {feedback_path}")
                return
            
            with open(feedback_path, 'r', encoding='utf-8') as f:
                feedback_data = json.load(f)
            
            print(f"🚀 Applicazione di {len(feedback_data)} feedback per {effective_ente}")
            
            # Converte i feedback
            feedbacks = []
            for item in feedback_data:
                feedback = Feedback(
                    document_id=item.get('document_id', ''),
                    original_category=item.get('original_category', ''),
                    corrected_category=item.get('corrected_category', ''),
                    text=item.get('text', ''),
                    oggetto=item.get('oggetto', ''),
                    confidence=item.get('confidence'),
                    user_id=item.get('user_id')
                )
                feedbacks.append(feedback)
            
            # Carica il DataFrame
            df = pd.read_csv(allegati_path)
            
            # Applica i feedback
            post_processor = get_active_learning_post_processor()
            df_updated = post_processor.apply_feedback_and_update(df, feedbacks)
            
            # Salva i dati aggiornati
            df_updated.to_csv(allegati_path, index=False)
            
            print(f"✅ Applicati {len(feedbacks)} feedback e aggiornati i dati")
            
        except Exception as e:
            print(f"❌ Errore durante l'applicazione dei feedback: {e}", file=sys.stderr)
    
    @cli.command()
    @click.option('--base', default='data/baiano/albo_download', help='Cartella base dei dati.')
    @click.option('--ente', default=None, help='Identificativo ente (opzionale)')
    def clear-feedback(base: str, ente: str):
        """
        Svuota tutti i feedback raccolti.
        
        ACTIVE LEARNING: Rimuove tutti i feedback salvati.
        """
        try:
            from delibere_comunali.ml.feedback_handler import get_feedback_manager
            from delibere_comunali.utils.config import get_tenant_dir
            
            effective_ente = ente or 'baiano'
            effective_base = Path(base) if base else get_tenant_dir(effective_ente) / "albo_download"
            
            if not effective_base.exists():
                print(f"❌ Cartella base non trovata: {effective_base}")
                return
            
            manager = get_feedback_manager()
            manager.feedback_store.clear_feedback()
            
            print(f"✅ Tutti i feedback sono stati svuotati")
            
        except Exception as e:
            print(f"❌ Errore durante lo svuotamento dei feedback: {e}", file=sys.stderr)
