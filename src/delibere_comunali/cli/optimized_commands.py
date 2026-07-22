"""
Optimized CLI commands for performance and stability improvements.
"""

import sys
import time
from pathlib import Path

import click


def add_optimized_commands(cli):
    """Add optimized commands to the Click CLI group."""

    @cli.command()
    @click.option(
        "--base", default="data/baiano/albo_download", help="Cartella base dei dati."
    )
    @click.option("--ente", default=None, help="Identificativo ente (opzionale)")
    @click.option(
        "--use-parallel/--no-parallel",
        default=True,
        help="Abilita/disabilita il processing parallelo",
    )
    @click.option(
        "--max-workers", default=4, type=int, help="Numero massimo di worker paralleli"
    )
    @click.option(
        "--batch-size",
        default=10,
        type=int,
        help="Dimensione del batch per il processing",
    )
    def ocr_parallel(
        base: str, ente: str, use_parallel: bool, max_workers: int, batch_size: int
    ):
        """
        Esegue l'estrazione OCR con processing parallelo ottimizzato.

        OPTIMIZATION: Nuovo comando per OCR parallelo con ThreadPoolExecutor.
        """
        try:
            from delibere_comunali.parsing.ocr_processor import (
                batch_extract_text_with_ocr,
            )
            from delibere_comunali.utils.config import get_tenant_dir

            effective_ente = ente or "baiano"
            effective_base = (
                Path(base) if base else get_tenant_dir(effective_ente) / "albo_download"
            )

            if not effective_base.exists():
                print(f"❌ Cartella base non trovata: {effective_base}")
                return

            print(f"🚀 Avvio OCR parallelo per {effective_base}")
            print(
                f"   Worker: {max_workers}, Batch: {batch_size}, Parallelo: {use_parallel}"
            )

            start_time = time.time()
            results = batch_extract_text_with_ocr(
                pdf_directory=effective_base,
                output_directory=effective_base / "ocr_output",
                use_parallel=use_parallel,
                max_workers=max_workers,
                batch_size=batch_size,
            )
            elapsed_time = time.time() - start_time

            print(f"✅ OCR completato in {elapsed_time:.2f} secondi")
            print(f"   Documenti elaborati: {len(results)}")

        except Exception as e:
            print(f"❌ Errore durante l'OCR parallelo: {e}", file=sys.stderr)

    @cli.command()
    @click.option(
        "--base", default="data/baiano/albo_download", help="Cartella base dei dati."
    )
    @click.option("--ente", default=None, help="Identificativo ente (opzionale)")
    @click.option(
        "--max-workers", default=4, type=int, help="Numero massimo di worker paralleli"
    )
    @click.option(
        "--min-samples",
        default=10,
        type=int,
        help="Numero minimo di campioni per categoria",
    )
    def post_process_optimized(
        base: str, ente: str, max_workers: int, min_samples: int
    ):
        """
        Esegue il post-processing ottimizzato con caching e parallelizzazione.

        OPTIMIZATION: Nuovo comando per post-processing con caching delle regole.
        """
        try:
            import pandas as pd

            from delibere_comunali.processing.post_process_classification_optimized import (
                add_confidence_to_existing_data,
                calculate_overall_quality_metrics,
                clear_cache,
                enhance_model_with_resolved_data_optimized,
                get_cache_stats,
                resolve_ambiguities_with_ml_optimized,
            )
            from delibere_comunali.utils.config import get_tenant_dir

            effective_ente = ente or "baiano"
            effective_base = (
                Path(base) if base else get_tenant_dir(effective_ente) / "albo_download"
            )

            if not effective_base.exists():
                print(f"❌ Cartella base non trovata: {effective_base}")
                return

            # Carica i dati
            allegati_path = effective_base / "allegati_parsed.csv"
            if not allegati_path.exists():
                print(f"❌ File allegati_parsed.csv non trovato in {effective_base}")
                return

            print(f"🚀 Avvio post-processing ottimizzato per {effective_base}")
            print(f"   Worker: {max_workers}, Min campioni: {min_samples}")

            # Carica il DataFrame
            df = pd.read_csv(allegati_path)
            print(f"   Documenti caricati: {len(df)}")

            # Aggiungi colonne di confidenza se non esistono
            df = add_confidence_to_existing_data(df)

            # Calcola metriche iniziali
            initial_metrics = calculate_overall_quality_metrics(df)
            print(
                f"   Metriche iniziali: {initial_metrics['classification_quality_index']:.2f} QI"
            )

            # Risolvi ambiguità con parallelizzazione
            start_time = time.time()

            # Carica il modello se esiste
            model_path = effective_base / "random_forest_model.joblib"
            model_loaded = False
            vectorizer_loaded = None

            if model_path.exists():
                try:
                    import joblib

                    model_bundle = joblib.load(model_path)
                    if isinstance(model_bundle, dict):
                        model = model_bundle.get("model")
                        vectorizer_loaded = model_bundle.get("vectorizer")
                    else:
                        model = model_bundle
                    model_loaded = True
                    print(f"   ✅ Modello ML caricato")
                except Exception as e:
                    print(f"   ⚠️  Errore nel caricamento del modello: {e}")

            # Applica il post-processing ottimizzato
            if model_loaded:
                df = resolve_ambiguities_with_ml_optimized(
                    df, model, vectorizer_loaded, max_workers=max_workers
                )
            else:
                # Solo regole senza ML
                df = resolve_ambiguities_with_ml_optimized(
                    df, None, None, max_workers=max_workers
                )

            # Migliora il modello
            enhance_model_with_resolved_data_optimized(
                df, effective_base, min_samples=min_samples
            )

            # Salva i risultati
            df.to_csv(allegati_path, index=False)

            elapsed_time = time.time() - start_time

            # Calcola metriche finali
            final_metrics = calculate_overall_quality_metrics(df)

            print(f"✅ Post-processing completato in {elapsed_time:.2f} secondi")
            print(
                f"   Metriche finali: {final_metrics['classification_quality_index']:.2f} QI"
            )
            print(
                f"   Miglioramento: +{final_metrics['classification_quality_index'] - initial_metrics['classification_quality_index']:.2f}"
            )

            # Statistiche cache
            cache_stats = get_cache_stats()
            print(f"   Cache: {cache_stats['hits']} hit, {cache_stats['misses']} miss")

        except Exception as e:
            print(
                f"❌ Errore durante il post-processing ottimizzato: {e}",
                file=sys.stderr,
            )

    @cli.command()
    def clear_ocr_cache():
        """
        Svuota la cache delle regole di classificazione.
        """
        try:
            from delibere_comunali.processing.post_process_classification_optimized import (
                clear_cache,
            )

            clear_cache()
            print("✅ Cache delle regole svuotata")
        except Exception as e:
            print(f"❌ Errore nello svuotamento della cache: {e}", file=sys.stderr)

    @cli.command()
    def check_config():
        """
        Verifica la configurazione del sistema e le variabili d'ambiente.
        """
        try:
            from delibere_comunali.utils.config import (
                get_config,
                get_db_connection_string,
                get_redis_connection_string,
            )

            config = get_config()

            print("📋 Configurazione del Sistema:")
            print("=" * 50)

            # Database
            print("\n🗄️  Database:")
            print(f"   Host: {config.get('DB_HOST')}")
            print(f"   Port: {config.get('DB_PORT')}")
            print(f"   Name: {config.get('DB_NAME')}")
            print(f"   Connection: {get_db_connection_string()}")

            # Redis
            print("\n🔴 Redis:")
            print(f"   Host: {config.get('REDIS_HOST')}")
            print(f"   Port: {config.get('REDIS_PORT')}")
            print(f"   Connection: {get_redis_connection_string()}")

            # OCR
            print("\n📄 OCR:")
            print(f"   Tesseract CMD: {config.get('TESSERACT_CMD')}")
            print(f"   DPI: {config.get('OCR_DPI')}")
            print(f"   Max Workers: {config.get('OCR_MAX_WORKERS')}")

            # Parallel Processing
            print("\n⚡ Parallel Processing:")
            print(f"   Max Workers: {config.get('MAX_PARALLEL_WORKERS')}")
            print(f"   Batch Size: {config.get('BATCH_SIZE')}")

            # File System
            print("\n📁 File System:")
            print(f"   Data Dir: {config.get_path('DATA_DIR')}")
            print(f"   Output Dir: {config.get_path('OUTPUT_DIR')}")
            print(f"   Cache Dir: {config.get_path('CACHE_DIR')}")

            # Carica file .env se esiste
            env_files = config.get_loaded_files()
            if env_files:
                print(f"\n📄 File di configurazione caricati:")
                for env_file in env_files:
                    print(f"   ✅ {env_file}")

        except Exception as e:
            print(
                f"❌ Errore nella verifica della configurazione: {e}", file=sys.stderr
            )
