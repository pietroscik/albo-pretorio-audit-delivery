"""
CLI commands for Database and Feature Engineering operations.
"""

import click
import sys
import json
from pathlib import Path


def add_db_commands(cli):
    """Add database and feature engineering commands to the Click CLI group."""
    
    @cli.command()
    @click.option('--base', default='data/baiano/albo_download', help='Cartella base dei dati.')
    @click.option('--ente', default=None, help='Identificativo ente (opzionale)')
    @click.option('--output-dir', default='features', help='Cartella di output per le feature')
    @click.option('--use-tfidf/--no-tfidf', default=True, help='Usa TF-IDF')
    @click.option('--use-embeddings/--no-embeddings', default=False, help='Usa word embeddings')
    @click.option('--use-text-features/--no-text-features', default=True, help='Usa feature testuali')
    def extract-features(base: str, ente: str, output_dir: str, use_tfidf: bool, use_embeddings: bool, use_text_features: bool):
        """
        Estrae feature avanzate dai documenti per il modello ML.
        
        FEATURE ENGINEERING: Crea feature TF-IDF, embeddings e testuali.
        """
        try:
            from delibere_comunali.ml.feature_engineering import FeatureEngineer, get_feature_engineer
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
            
            print(f"🚀 Estrazione feature per {effective_ente}")
            print(f"   TF-IDF: {use_tfidf}, Embeddings: {use_embeddings}, Text Features: {use_text_features}")
            
            # Carica il DataFrame
            df = pd.read_csv(allegati_path)
            print(f"   Documenti caricati: {len(df)}")
            
            # Estrai le feature
            engineer = get_feature_engineer(
                use_tfidf=use_tfidf,
                use_embeddings=use_embeddings,
                use_text_features=use_text_features
            )
            
            # Usa il testo o il text_preview
            text_col = 'text_preview' if 'text_preview' in df.columns else 'text'
            texts = df[text_col].astype(str).tolist()
            
            # Fit e estrai feature
            engineer.fit(texts)
            
            # Estrai tutte le feature
            basic_features, tfidf_features, embedding_features = engineer.extract_combined_features(texts)
            
            # Salva le feature
            output_path = effective_base / output_dir
            output_path.mkdir(parents=True, exist_ok=True)
            
            # Salva feature di base
            basic_features_path = output_path / "basic_features.csv"
            basic_features.to_csv(basic_features_path, index=False)
            print(f"✅ Feature di base salvate in: {basic_features_path}")
            
            # Salva feature TF-IDF (se usate)
            if use_tfidf and tfidf_features is not None:
                import scipy.sparse
                tfidf_features_path = output_path / "tfidf_features.npz"
                scipy.sparse.save_npz(tfidf_features_path, tfidf_features)
                print(f"✅ Feature TF-IDF salvate in: {tfidf_features_path}")
            
            # Salva feature embeddings (se usate)
            if use_embeddings and embedding_features is not None:
                embeddings_path = output_path / "embeddings.npy"
                import numpy as np
                np.save(embeddings_path, embedding_features)
                print(f"✅ Feature embeddings salvate in: {embeddings_path}")
            
            # Salva il feature engineer
            engineer.save(output_path / "feature_engineer")
            print(f"✅ Feature engineer salvato in: {output_path / 'feature_engineer'}")
            
            print(f"\n📊 Riassunto Feature:")
            print(f"   Feature di base: {basic_features.shape[1]} colonne")
            if use_tfidf and tfidf_features is not None:
                print(f"   Feature TF-IDF: {tfidf_features.shape[1]} colonne")
            if use_embeddings and embedding_features is not None:
                print(f"   Feature embeddings: {embedding_features.shape[1]} colonne")
            
        except Exception as e:
            print(f"❌ Errore durante l'estrazione delle feature: {e}", file=sys.stderr)
    
    @cli.command()
    @click.option('--base', default='data/baiano/albo_download', help='Cartella base dei dati.')
    @click.option('--ente', default=None, help='Identificativo ente (opzionale)')
    def analyze-db(base: str, ente: str):
        """
        Analizza il database e mostra statistiche.
        
        DATABASE: Analisi delle tabelle e delle performance.
        """
        try:
            from delibere_comunali.utils.db_utils import get_query_optimizer
            
            effective_ente = ente or 'baiano'
            
            print(f"🚀 Analisi database per {effective_ente}")
            
            optimizer = get_query_optimizer()
            
            # Analizza le tabelle principali
            tables = ['documents', 'entities', 'classifications', 'feedback']
            
            for table in tables:
                try:
                    stats = optimizer.analyze_table(table)
                    if stats:
                        print(f"\n📋 Tabella: {table}")
                        print(f"   Dimensione: {stats.get('size', 'N/A')}")
                        print(f"   Righe: {stats.get('row_count', 'N/A')}")
                        print(f"   Colonne: {len(stats.get('columns', []))}")
                except Exception as e:
                    print(f"   ⚠️  Errore analisi tabella {table}: {e}")
            
            # Mostra query lente
            print(f"\n🐢 Query Lente:")
            slow_queries = optimizer.get_slow_queries(limit=5)
            if slow_queries:
                for i, query in enumerate(slow_queries, 1):
                    print(f"   {i}. Tempo medio: {query.get('mean_time', 'N/A')}, Chiamate: {query.get('calls', 'N/A')}")
                    print(f"      Query: {query.get('query', 'N/A')[:100]}...")
            else:
                print(f"   Nessuna query lenta trovata (pg_stat_statements non attivo)")
            
        except Exception as e:
            print(f"❌ Errore durante l'analisi del database: {e}", file=sys.stderr)
    
    @cli.command()
    @click.option('--table', required=True, help='Nome della tabella')
    @click.option('--columns', required=True, help='Colonne da indicizzare (separate da virgola)')
    @click.option('--unique/--no-unique', default=False, help='Crea indice univoco')
    @click.option('--index-name', default=None, help='Nome dell\'indice (opzionale)')
    def create-index(table: str, columns: str, unique: bool, index_name: str):
        """
        Crea un indice su una tabella del database.
        
        DATABASE: Ottimizzazione delle query con indici.
        """
        try:
            from delibere_comunali.utils.db_utils import get_query_optimizer
            
            column_list = [col.strip() for col in columns.split(',')]
            
            print(f"🚀 Creazione indice su {table} ({', '.join(column_list)})")
            
            optimizer = get_query_optimizer()
            success = optimizer.create_index(
                table=table,
                columns=column_list,
                index_name=index_name or None,
                unique=unique
            )
            
            if success:
                print(f"✅ Indice creato con successo")
            else:
                print(f"❌ Errore nella creazione dell'indice")
            
        except Exception as e:
            print(f"❌ Errore durante la creazione dell'indice: {e}", file=sys.stderr)
    
    @cli.command()
    @click.option('--query', required=True, help='Query SQL da spiegare')
    def explain-query(query: str):
        """
        Mostra il piano di esecuzione di una query SQL.
        
        DATABASE: Analisi delle performance delle query.
        """
        try:
            from delibere_comunali.utils.db_utils import get_query_optimizer
            
            print(f"🚀 Analisi query: {query[:50]}...")
            
            optimizer = get_query_optimizer()
            plan = optimizer.explain_query(query)
            
            if plan:
                print(f"\n📋 Piano di Esecuzione:")
                for i, step in enumerate(plan, 1):
                    print(f"   {i}. {step}")
            else:
                print(f"   Nessun piano di esecuzione restituito")
            
        except Exception as e:
            print(f"❌ Errore durante l'analisi della query: {e}", file=sys.stderr)
    
    @cli.command()
    def db-stats():
        """
        Mostra le statistiche del database.
        
        DATABASE: Statistiche generali del database.
        """
        try:
            from delibere_comunali.utils.db_utils import get_db_pool, get_redis_cache
            
            print("🚀 Statistiche Database")
            print("=" * 50)
            
            # Statistiche PostgreSQL
            pool = get_db_pool()
            engine = pool.get_engine()
            
            if engine:
                # Get database size
                with engine.connect() as conn:
                    result = conn.execute("""
                        SELECT 
                            pg_database.datname,
                            pg_size_pretty(pg_database_size(pg_database.datname)) as size
                        FROM pg_database 
                        WHERE datname = current_database()
                    """)
                    db_size = result.fetchone()
                    if db_size:
                        print(f"\n🗄️  PostgreSQL:")
                        print(f"   Database: {db_size[0]}")
                        print(f"   Dimensione: {db_size[1]}")
            
            # Statistiche Redis
            try:
                redis = get_redis_cache()
                stats = redis.get_stats()
                if stats.get('connected'):
                    print(f"\n🔴 Redis:")
                    print(f"   Connesso: {stats['connected']}")
                    print(f"   Memoria usata: {stats.get('used_memory', 'N/A')}")
                    print(f"   Chiavi: {stats.get('keys', 'N/A')}")
            except Exception as e:
                print(f"\n⚠️  Redis non disponibile: {e}")
            
        except Exception as e:
            print(f"❌ Errore durante il recupero delle statistiche: {e}", file=sys.stderr)
    
    @cli.command()
    @click.option('--pattern', default=None, help='Pattern per filtrare le chiavi (opzionale)')
    def clear-cache(pattern: str):
        """
        Svuota la cache Redis.
        
        DATABASE: Pulizia della cache.
        """
        try:
            from delibere_comunali.utils.db_utils import get_redis_cache
            
            redis = get_redis_cache()
            
            if pattern:
                deleted = redis.clear(pattern=pattern)
                print(f"✅ Svuotate {deleted} chiavi con pattern: {pattern}")
            else:
                deleted = redis.clear()
                print(f"✅ Svuotate tutte le chiavi della cache ({deleted})")
            
        except Exception as e:
            print(f"❌ Errore durante lo svuotamento della cache: {e}", file=sys.stderr)
    
    @cli.command()
    @click.option('--base', default='data/baiano/albo_download', help='Cartella base dei dati.')
    @click.option('--ente', default=None, help='Identificativo ente (opzionale)')
    @click.option('--feature-file', default='features/basic_features.csv', help='File con le feature')
    @click.option('--target-column', default='category', help='Colonna target')
    @click.option('--method', default='kbest', help='Metodo di selezione (kbest, rfe, pca)')
    @click.option('--k', default=1000, type=int, help='Numero di feature da selezionare')
    def select-features(base: str, ente: str, feature_file: str, target_column: str, method: str, k: int):
        """
        Seleziona le feature più importanti per il modello.
        
        FEATURE ENGINEERING: Selezione feature con metodi statistici.
        """
        try:
            from delibere_comunali.ml.feature_engineering import FeatureSelector
            from delibere_comunali.utils.config import get_tenant_dir
            import pandas as pd
            import numpy as np
            
            effective_ente = ente or 'baiano'
            effective_base = Path(base) if base else get_tenant_dir(effective_ente) / "albo_download"
            
            feature_path = effective_base / feature_file
            if not feature_path.exists():
                print(f"❌ File feature non trovato: {feature_path}")
                return
            
            print(f"🚀 Selezione feature per {effective_ente}")
            print(f"   Metodo: {method}, Feature da selezionare: {k}")
            
            # Carica i dati
            df = pd.read_csv(feature_path)
            
            # Carica il target
            allegati_path = effective_base / "allegati_parsed.csv"
            if allegati_path.exists():
                target_df = pd.read_csv(allegati_path)
                if target_column in target_df.columns:
                    y = target_df[target_column].values
                else:
                    print(f"   ⚠️  Colonna target '{target_column}' non trovata")
                    return
            else:
                print(f"   ⚠️  File allegati_parsed.csv non trovato")
                return
            
            # Seleziona le feature
            selector = FeatureSelector()
            X = df.values
            
            if method == 'kbest':
                X_selected = selector.select_k_best(X, y, k=k, score_func='f_classif')
                print(f"✅ Selezionate {X_selected.shape[1]} feature con SelectKBest")
            elif method == 'rfe':
                X_selected = selector.select_rfe(X, y, n_features_to_select=k)
                print(f"✅ Selezionate {X_selected.shape[1]} feature con RFE")
            elif method == 'pca':
                X_selected = selector.apply_pca(X, n_components=k)
                print(f"✅ Ridotte a {X_selected.shape[1]} componenti con PCA")
            else:
                print(f"   ⚠️  Metodo sconosciuto: {method}")
                return
            
            # Salva le feature selezionate
            output_path = feature_path.parent / f"selected_features_{method}_{k}.csv"
            pd.DataFrame(X_selected).to_csv(output_path, index=False, header=False)
            print(f"✅ Feature selezionate salvate in: {output_path}")
            
        except Exception as e:
            print(f"❌ Errore durante la selezione delle feature: {e}", file=sys.stderr)
