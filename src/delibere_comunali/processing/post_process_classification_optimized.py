#!/usr/bin/env python3
"""
Modulo di post-processing OTTIMIZZATO per la classificazione dei documenti.
Questo modulo estende il post_process_classification.py originale con:
- Caching dei risultati delle regole di classificazione
- Parallelizzazione dell'applicazione delle regole
- Ottimizzazione della memoria con processing a batch
- Supporto per Active Learning incrementale

OPTIMIZATION: Added caching and parallel processing for rule-based classification.
"""

import argparse
import hashlib
import json
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache, partial
from pathlib import Path
from typing import Any, Dict, Optional, Tuple

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    precision_recall_fscore_support,
)
from sklearn.model_selection import GridSearchCV, train_test_split
from sklearn.pipeline import Pipeline
from sklearn.utils.class_weight import compute_class_weight

from delibere_comunali.utils.cache import LRUCache
from delibere_comunali.utils.config import get_tenant_dir

# Configura il logger
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ClassificationScorer:
    """
    Classe per gestire il scoring e la confidenza della classificazione.
    """

    def __init__(self):
        # Soglie di confidenza per la classificazione
        self.confidence_thresholds = {"high": 0.7, "medium": 0.5, "low": 0.3}

        # Pesi per il calcolo della confidenza composita
        self.confidence_weights = {
            "rule_based": 0.9,
            "ml_high_conf": 0.85,
            "ml_medium_conf": 0.65,
            "ml_low_conf": 0.4,
            "manual": 1.0,
            "default": 0.5,
        }

    def calculate_composite_confidence(
        self,
        classification_method: str,
        probability: float = None,
        rule_strength: float = None,
    ) -> Tuple[float, str]:
        """
        Calcola la confidenza composita in base al metodo di classificazione.

        Returns:
            Tuple[confidence_score, confidence_level]
        """
        if classification_method == "rule_based":
            confidence = (
                rule_strength
                if rule_strength is not None
                else self.confidence_weights["rule_based"]
            )

        elif classification_method.startswith("ml_predicted"):
            if probability is not None:
                confidence = probability
            else:
                confidence = self.confidence_weights.get(classification_method, 0.5)

        elif classification_method == "manual":
            confidence = self.confidence_weights["manual"]

        elif classification_method == "high":
            confidence = self.confidence_weights["rule_based"]

        else:
            confidence = self.confidence_weights.get(classification_method, 0.5)

        # Determina il livello di confidenza
        if confidence >= self.confidence_thresholds["high"]:
            confidence_level = "high"
        elif confidence >= self.confidence_thresholds["medium"]:
            confidence_level = "medium"
        else:
            confidence_level = "low"

        return confidence, confidence_level

    def get_quality_from_confidence(self, confidence_level: str) -> str:
        """
        Converte un livello di confidenza in un livello di qualità.
        """
        quality_map = {"high": "high", "medium": "medium", "low": "low"}
        return quality_map.get(confidence_level, "low")


# Inizializza lo scorer globale
scorer = ClassificationScorer()


# Cache globale per i risultati delle regole di classificazione
# Chiave: hash(test_str + oggetto_str), Valore: (categoria, confidenza, livello_confidenza)
rule_cache = LRUCache(max_size=10000, default_ttl=3600)  # 1 ora di TTL


def _generate_cache_key(text_str: str, oggetto_str: str) -> str:
    """Genera una chiave univoca per la cache basata su testo e oggetto."""
    combined = f"{text_str}|{oggetto_str}"
    return hashlib.md5(combined.encode("utf-8")).hexdigest()


def apply_advanced_classification_rules_cached(
    text_str: str, oggetto_str: str = "", return_confidence: bool = False
) -> Any:
    """
    Applica regole avanzate di classificazione con caching dei risultati.

    OPTIMIZATION: Uses LRUCache to avoid recomputing rules for the same text.

    Args:
        text_str: Testo del documento
        oggetto_str: Oggetto del documento
        return_confidence: Se True, restituisce anche la confidenza

    Returns:
        category o Tuple[category, confidence_score, confidence_level]
    """
    # Normalizza gli input
    if pd.isna(text_str):
        text_str = ""
    if pd.isna(oggetto_str):
        oggetto_str = ""

    # Genera chiave cache
    cache_key = _generate_cache_key(text_str, oggetto_str)

    # Controlla se il risultato è in cache
    cached_result = rule_cache.get(cache_key)
    if cached_result is not None:
        if return_confidence:
            return cached_result
        else:
            return cached_result[0] if cached_result else None

    # Se non è in cache, calcola il risultato
    full_text = (oggetto_str + " " + text_str).lower()

    # Regole specifiche per distinguere tra categorie simili con pesi
    contabilita_terms = [
        ("impegno di spesa", 0.95),
        ("liquidazione", 0.95),
        ("fattura", 0.9),
        ("pagamento", 0.9),
        ("capitolo", 0.85),
        ("accertamento", 0.9),
        ("visto contabile", 0.95),
        ("mandato di pagamento", 0.95),
        ("certificato di pagamento", 0.95),
    ]

    lavori_pubblici_terms = [
        ("lavori pubblici", 0.95),
        ("progetto esecutivo", 0.95),
        ("manutenzione", 0.9),
        ("cantiere", 0.9),
        ("opera pubblica", 0.95),
        ("direzione lavori", 0.9),
        ("collaudo", 0.9),
        ("appalto", 0.85),
    ]

    personale_terms = [
        ("personale", 0.9),
        ("assunzioni", 0.95),
        ("concorso", 0.95),
        ("selezione", 0.9),
        ("progressione", 0.85),
        ("nomina", 0.9),
        ("incarico", 0.85),
    ]

    regolamenti_terms = [
        ("regolamento", 0.95),
        ("approvazione regolamento", 0.95),
        ("modifica regolamento", 0.95),
        ("delibera regolamento", 0.9),
    ]

    pubblicazioni_terms = [
        ("pubblicazione", 0.9),
        ("albo pretorio", 0.95),
        ("avviso", 0.85),
        ("bando", 0.9),
        ("manifestazione di interesse", 0.85),
    ]

    organizzazione_terms = [
        ("protocollo", 0.85),
        ("ufficio", 0.8),
        ("servizio", 0.8),
        ("settore", 0.8),
        ("organizzazione", 0.9),
    ]

    # Funzione per calcolare il punteggio di una categoria
    def calculate_category_score(terms_list):
        max_score = 0.0
        for term, weight in terms_list:
            if term in full_text:
                max_score = max(max_score, weight)
        return max_score

    # Calcola i punteggi per ogni categoria
    scores = {
        "Contabilità": calculate_category_score(contabilita_terms),
        "Lavori Pubblici": calculate_category_score(lavori_pubblici_terms),
        "Personale": calculate_category_score(personale_terms),
        "Regolamenti": calculate_category_score(regolamenti_terms),
        "Pubblicazioni": calculate_category_score(pubblicazioni_terms),
        "Organizzazione": calculate_category_score(organizzazione_terms),
    }

    # Trova la categoria con il punteggio più alto
    best_category = max(scores.items(), key=lambda x: x[1])

    if best_category[1] > 0.5:
        if return_confidence:
            confidence, confidence_level = scorer.calculate_composite_confidence(
                "rule_based", rule_strength=best_category[1]
            )
            result = (best_category[0], confidence, confidence_level)
        else:
            result = best_category[0]

        # Salva in cache
        rule_cache.set(cache_key, result)
        return result

    # Regole aggiuntive per casi specifici
    if any(
        term in full_text
        for term in ["ufficio tecnico", "ingegnere", "architetto", "progettazione"]
    ):
        result = (
            ("Lavori Pubblici", 0.9, "high") if return_confidence else "Lavori Pubblici"
        )
        rule_cache.set(cache_key, result)
        return result

    if any(
        term in full_text
        for term in [
            "ufficio ragioneria",
            "ragioniere",
            "contabilità",
            "tributo",
            "bilancio",
        ]
    ):
        result = ("Contabilità", 0.95, "high") if return_confidence else "Contabilità"
        rule_cache.set(cache_key, result)
        return result

    if any(
        term in full_text for term in ["ufficio personale", "dipendenti", "dirigenza"]
    ):
        result = ("Personale", 0.9, "high") if return_confidence else "Personale"
        rule_cache.set(cache_key, result)
        return result

    # Se nessuna regola specifica è applicabile
    if return_confidence:
        result = (None, 0.0, "low")
    else:
        result = None

    rule_cache.set(cache_key, result)
    return result


def apply_rules_to_document(
    row: pd.Series, text_col: str = "text_preview", oggetto_col: str = "oggetto"
) -> Optional[Tuple[str, float, str]]:
    """
    Applica le regole di classificazione a una singola riga del DataFrame.

    OPTIMIZATION: Designed to be called in parallel for batch processing.

    Args:
        row: Series del DataFrame
        text_col: Nome della colonna con il testo
        oggetto_col: Nome della colonna con l'oggetto

    Returns:
        Tuple di (categoria, confidenza, livello_confidenza) o None
    """
    try:
        text_val = row[text_col] if text_col in row.index else ""
        oggetto_val = row[oggetto_col] if oggetto_col in row.index else ""

        return apply_advanced_classification_rules_cached(
            text_val, oggetto_val, return_confidence=True
        )
    except Exception as e:
        logger.warning(f"Error applying rules to document: {e}")
        return None


def resolve_ambiguities_with_ml_optimized(
    df: pd.DataFrame, model, vectorizer=None, max_workers: int = 4
) -> pd.DataFrame:
    """
    Risolvi le ambiguità utilizzando il modello ML e le regole avanzate con parallelizzazione.

    OPTIMIZATION: Uses parallel processing for rule application.

    Args:
        df: DataFrame con i documenti
        model: Modello ML addestrato
        vectorizer: Vettorizzatore per il modello
        max_workers: Numero massimo di worker paralleli

    Returns:
        DataFrame aggiornato
    """
    logger.info(
        "Risoluzione ambiguità con modello ML e regole avanzate (ottimizzato)..."
    )

    # Filtra solo i documenti ambigui o con bassa confidenza
    low_confidence_mask = df["classification_confidence"].isin(
        ["ambiguous", "low", "ml_predicted_low_conf"]
    )
    ambiguous_docs = df[low_confidence_mask].copy()

    if len(ambiguous_docs) == 0:
        logger.info("Nessun documento con bassa confidenza da risolvere.")
        return df

    logger.info(
        f"Trovati {len(ambiguous_docs)} documenti con bassa confidenza da risolvere."
    )

    # Applica le regole in parallelo
    text_col = "text_preview" if "text_preview" in df.columns else "text"
    oggetto_col = "oggetto" if "oggetto" in df.columns else "title"

    # Prepara i dati per il processing parallelo
    rows_to_process = []
    for idx, row in ambiguous_docs.iterrows():
        rows_to_process.append((idx, row, text_col, oggetto_col))

    # Processa in parallelo
    resolved_by_rules = 0
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = []
        for idx, row, t_col, o_col in rows_to_process:
            future = executor.submit(apply_rules_to_document, row, t_col, o_col)
            futures.append((idx, future))

        for idx, future in futures:
            result = future.result()
            if result and result[0] is not None:
                category, confidence, confidence_level = result
                df.loc[idx, "category"] = category
                df.loc[idx, "classification_confidence"] = confidence_level
                df.loc[idx, "classification_confidence_score"] = confidence
                df.loc[idx, "classification_method"] = "rule_based"
                resolved_by_rules += 1

    logger.info(
        f"Risolte {resolved_by_rules} ambiguità con regole avanzate (parallelo)."
    )

    # Per i documenti rimanenti, prova con il modello ML
    still_low_conf_mask = df["classification_confidence"].isin(["ambiguous", "low"])
    still_ambiguous_docs = df[still_low_conf_mask].copy()

    if len(still_ambiguous_docs) > 0:
        text_col = "text_preview" if "text_preview" in df.columns else "text"
        text_available = still_ambiguous_docs[text_col].notna() & (
            still_ambiguous_docs[text_col].astype(str).str.len() > 50
        )
        docs_with_text = still_ambiguous_docs[text_available].copy()

        if len(docs_with_text) > 0:
            try:
                # Prepara i dati per la classificazione ML
                X = docs_with_text[text_col].astype(str)

                # Predici con il modello
                if vectorizer:
                    X_vec = vectorizer.transform(X)
                    predictions = model.predict(X_vec)
                    prediction_probs = model.predict_proba(X_vec)
                else:
                    predictions = model.predict(X)
                    prediction_probs = model.predict_proba(X)

                max_probs = np.max(prediction_probs, axis=1)

                # Applica le predizioni ai documenti originali
                for i, idx in enumerate(docs_with_text.index):
                    df.loc[idx, "category"] = predictions[i]

                    # Calcola confidenza composita
                    confidence, confidence_level = (
                        scorer.calculate_composite_confidence(
                            "ml_predicted", probability=max_probs[i]
                        )
                    )

                    df.loc[idx, "classification_confidence"] = confidence_level
                    df.loc[idx, "classification_confidence_score"] = confidence
                    df.loc[idx, "classification_method"] = "ml_predicted"

                logger.info(f"Risolte {len(docs_with_text)} ambiguità con modello ML.")
            except Exception as e:
                logger.warning(f"Errore durante la classificazione ML: {e}")

    return df


def enhance_model_with_resolved_data_optimized(
    df: pd.DataFrame, base_path: Path, min_samples: int = 10
) -> Optional[Dict]:
    """
    Migliora il modello RF con i documenti già classificati con alta confidenza.

    OPTIMIZATION: Added min_samples parameter and better error handling.

    Args:
        df: DataFrame con i documenti
        base_path: Percorso base per salvare il modello
        min_samples: Numero minimo di campioni per categoria

    Returns:
        Dizionario con il modello e il vettorizzatore aggiornati, o None
    """
    # Filtra i documenti con classificazione affidabile (alta confidenza)
    high_confidence_mask = (
        (df["classification_confidence"] == "high")
        | (df["classification_confidence"] == "ml_predicted_high_conf")
        | (
            (df["classification_confidence"].isin(["high_ml", "ml_predicted"]))
            & (df.get("classification_confidence_score", 0) > 0.7)
        )
    )

    resolved_df = df[high_confidence_mask].copy()

    if len(resolved_df) < min_samples:
        logger.info(
            f"Troppo pochi documenti risolti ({len(resolved_df)}) per migliorare il modello."
        )
        return None

    # Controlla la distribuzione delle categorie
    category_counts = resolved_df["category"].value_counts()
    logger.info(f"Distribuzione delle categorie nei dati risolti: \n{category_counts}")

    # Filtra le categorie con troppo pochi esempi
    valid_categories = category_counts[category_counts >= min_samples].index
    filtered_df = resolved_df[resolved_df["category"].isin(valid_categories)].copy()

    if len(filtered_df) < min_samples:
        logger.warning(
            f"Dopo il filtro delle categorie rare, rimangono solo {len(filtered_df)} documenti."
        )
        return None

    # Prepara i dati per il training
    if "_text" in filtered_df.columns:
        X_text = (
            filtered_df["oggetto"].fillna("") + " " + filtered_df["_text"].fillna("")
        )
    else:
        X_text = filtered_df["oggetto"].fillna("")

    y = filtered_df["category"]

    # Controlla la distribuzione finale
    final_category_counts = y.value_counts()
    logger.info(f"Distribuzione finale delle categorie: \n{final_category_counts}")

    if len(final_category_counts) < 2:
        logger.warning("Numero insufficiente di categorie per il training (meno di 2).")
        return None

    # Usa stratify solo se tutte le categorie hanno almeno min_samples esempi
    min_count = final_category_counts.min()
    if min_count >= min_samples:
        try:
            X_train, X_test, y_train, y_test = train_test_split(
                X_text, y, test_size=0.2, random_state=42, stratify=y
            )
        except ValueError as e:
            logger.warning(
                f"Stratify fallito: {e}. Utilizzo divisione senza stratificazione."
            )
            X_train, X_test, y_train, y_test = train_test_split(
                X_text, y, test_size=0.2, random_state=42
            )
    else:
        logger.info(
            "Numero insufficiente di esempi per alcune categorie, divisione senza stratificazione"
        )
        X_train, X_test, y_train, y_test = train_test_split(
            X_text, y, test_size=0.2, random_state=42
        )

    # Crea un nuovo modello basato sui dati risolti
    vectorizer = TfidfVectorizer(
        max_features=10000, stop_words=None, ngram_range=(1, 2)
    )
    X_train_vec = vectorizer.fit_transform(X_train)
    X_test_vec = vectorizer.transform(X_test)

    # Alleniamo un nuovo modello Random Forest
    rf_new = RandomForestClassifier(
        n_estimators=100,
        random_state=42,
        n_jobs=-1,  # Usa tutti i core disponibili
        min_samples_split=5,
        min_samples_leaf=2,
    )
    rf_new.fit(X_train_vec, y_train)

    # Valuta le prestazioni
    y_pred = rf_new.predict(X_test_vec)
    accuracy = accuracy_score(y_test, y_pred)
    logger.info(f"Prestazioni del modello migliorato: Accuracy = {accuracy:.3f}")

    # Salva il modello migliorato
    model_path = base_path / "random_forest_model_enhanced.joblib"
    joblib.dump({"vectorizer": vectorizer, "model": rf_new}, model_path)
    logger.info(f"Modello migliorato salvato in: {model_path}")

    return {"vectorizer": vectorizer, "model": rf_new}


def add_confidence_to_existing_data(df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggiunge le colonne di confidenza ai dati esistenti se non presenti.
    """
    # Aggiungi colonne di confidenza se non esistono
    if "classification_confidence" not in df.columns:
        confidence_map = {
            "high": "high",
            "medium": "medium",
            "low": "low",
            "ambiguous": "low",
            "high_ml": "high",
            "ml_predicted": "medium",
            "rule_based": "high",
        }

        df["classification_confidence"] = (
            df.get("confidence", "low").map(confidence_map).fillna("low")
        )

    if "classification_confidence_score" not in df.columns:
        score_map = {"high": 0.9, "medium": 0.7, "low": 0.4, "ambiguous": 0.3}
        df["classification_confidence_score"] = (
            df["classification_confidence"].map(score_map).fillna(0.3)
        )

    if "classification_method" not in df.columns:
        method_map = {
            "high": "rule_based",
            "medium": "ml_predicted",
            "low": "default",
            "ambiguous": "default",
            "high_ml": "ml_predicted",
            "ml_predicted": "ml_predicted",
            "rule_based": "rule_based",
        }
        df["classification_method"] = (
            df["classification_confidence"].map(method_map).fillna("default")
        )

    return df


def calculate_overall_quality_metrics(df: pd.DataFrame) -> Dict:
    """
    Calcola metriche di qualità complessive per la classificazione.
    """
    if df.empty:
        return {
            "total_documents": 0,
            "high_confidence_pct": 0,
            "medium_confidence_pct": 0,
            "low_confidence_pct": 0,
            "average_confidence_score": 0,
            "classification_quality_index": 0,
        }

    confidence_counts = df["classification_confidence"].value_counts()
    total = len(df)

    high_count = confidence_counts.get("high", 0)
    medium_count = confidence_counts.get("medium", 0)
    low_count = total - high_count - medium_count

    high_pct = (high_count / total) * 100 if total > 0 else 0
    medium_pct = (medium_count / total) * 100 if total > 0 else 0
    low_pct = (low_count / total) * 100 if total > 0 else 0

    avg_score = (
        df["classification_confidence_score"].mean()
        if "classification_confidence_score" in df.columns
        else 0
    )
    quality_index = high_pct * 1.0 + medium_pct * 0.7 + low_pct * 0.3

    return {
        "total_documents": total,
        "high_confidence_count": high_count,
        "medium_confidence_count": medium_count,
        "low_confidence_count": low_count,
        "high_confidence_pct": high_pct,
        "medium_confidence_pct": medium_pct,
        "low_confidence_pct": low_pct,
        "average_confidence_score": avg_score,
        "classification_quality_index": quality_index,
    }


def get_cache_stats() -> Dict[str, Any]:
    """
    Restituisce le statistiche della cache.
    """
    return {
        "hits": rule_cache.hits,
        "misses": rule_cache.misses,
        "size": len(rule_cache._cache),
        "max_size": rule_cache.max_size,
    }


def clear_cache() -> None:
    """
    Svuota la cache delle regole.
    """
    global rule_cache
    rule_cache = LRUCache(max_size=10000, default_ttl=3600)
    logger.info("Cache delle regole svuotata")
