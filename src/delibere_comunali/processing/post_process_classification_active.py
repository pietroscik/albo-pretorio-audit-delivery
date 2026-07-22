#!/usr/bin/env python3
"""
Post-processing module with Active Learning integration.

This module extends the optimized post-processing with Active Learning capabilities:
- Identifies uncertain predictions
- Requests user feedback for uncertain predictions
- Uses feedback to improve future predictions
- Tracks model performance over time

OPTIMIZATION: Combines caching, parallel processing, and active learning.
"""

import pandas as pd
import numpy as np
import joblib
import json
import logging
import hashlib
from pathlib import Path
from typing import Tuple, Dict, Any, Optional, List
from functools import lru_cache
from concurrent.futures import ThreadPoolExecutor, as_completed
from sklearn.model_selection import train_test_split
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.metrics import accuracy_score

from delibere_comunali.utils.config import get_tenant_dir
from delibere_comunali.utils.cache import LRUCache
from delibere_comunali.utils.logger import get_logger
from delibere_comunali.ml.feedback_handler import (
    Feedback,
    FeedbackStore,
    ActiveLearningManager,
    get_feedback_manager
)
from delibere_comunali.ml.active_learning import (
    UncertaintySampler,
    ActiveLearningPipeline,
    ModelPerformanceTracker,
    should_request_feedback,
    get_uncertain_samples
)

logger = get_logger(__name__)


# Cache globale per i risultati delle regole di classificazione
rule_cache = LRUCache(max_size=10000, default_ttl=3600)


def _generate_cache_key(text_str: str, oggetto_str: str) -> str:
    """Genera una chiave univoca per la cache basata su testo e oggetto."""
    combined = f"{text_str}|{oggetto_str}"
    return hashlib.md5(combined.encode('utf-8')).hexdigest()


class ClassificationScorer:
    """Classe per gestire il scoring e la confidenza della classificazione."""
    
    def __init__(self):
        self.confidence_thresholds = {
            'high': 0.7,
            'medium': 0.5,
            'low': 0.3
        }
        
        self.confidence_weights = {
            'rule_based': 0.9,
            'ml_high_conf': 0.85,
            'ml_medium_conf': 0.65,
            'ml_low_conf': 0.4,
            'manual': 1.0,
            'default': 0.5
        }
    
    def calculate_composite_confidence(
        self, 
        classification_method: str, 
        probability: Optional[float] = None, 
        rule_strength: Optional[float] = None
    ) -> Tuple[float, str]:
        """Calcola la confidenza composita."""
        if classification_method == 'rule_based':
            confidence = rule_strength if rule_strength is not None else self.confidence_weights['rule_based']
        elif classification_method.startswith('ml_predicted'):
            if probability is not None:
                confidence = probability
            else:
                confidence = self.confidence_weights.get(classification_method, 0.5)
        elif classification_method == 'manual':
            confidence = self.confidence_weights['manual']
        elif classification_method == 'high':
            confidence = self.confidence_weights['rule_based']
        else:
            confidence = self.confidence_weights.get(classification_method, 0.5)
        
        if confidence >= self.confidence_thresholds['high']:
            confidence_level = 'high'
        elif confidence >= self.confidence_thresholds['medium']:
            confidence_level = 'medium'
        else:
            confidence_level = 'low'
        
        return confidence, confidence_level


# Inizializza lo scorer globale
scorer = ClassificationScorer()


class ActiveLearningPostProcessor:
    """
    Post-processor con integrazione Active Learning.
    
    Questo classe:
    1. Applica le regole di classificazione con caching
    2. Identifica le predizioni incerte
    3. Richiede feedback per le predizioni incerte
    4. Usa il feedback per migliorare il modello
    """
    
    def __init__(
        self,
        feedback_manager: Optional[ActiveLearningManager] = None,
        uncertainty_threshold: float = 0.7,
        max_workers: int = 4
    ):
        """
        Inizializza il post-processor con Active Learning.
        
        Args:
            feedback_manager: Gestore del feedback
            uncertainty_threshold: Soglia di incertezza per richiedere feedback
            max_workers: Numero massimo di worker paralleli
        """
        self.feedback_manager = feedback_manager or get_feedback_manager()
        self.sampler = UncertaintySampler(threshold=uncertainty_threshold)
        self.max_workers = max_workers
        self.performance_tracker = ModelPerformanceTracker()
    
    def apply_advanced_classification_rules_cached(
        self, 
        text_str: str, 
        oggetto_str: str = "", 
        return_confidence: bool = False
    ) -> Any:
        """Applica regole avanzate di classificazione con caching."""
        if pd.isna(text_str):
            text_str = ""
        if pd.isna(oggetto_str):
            oggetto_str = ""
        
        cache_key = _generate_cache_key(text_str, oggetto_str)
        cached_result = rule_cache.get(cache_key)
        if cached_result is not None:
            if return_confidence:
                return cached_result
            else:
                return cached_result[0] if cached_result else None
        
        full_text = (oggetto_str + " " + text_str).lower()
        
        # Regole specifiche
        contabilita_terms = [
            ("impegno di spesa", 0.95), ("liquidazione", 0.95), ("fattura", 0.9),
            ("pagamento", 0.9), ("capitolo", 0.85), ("accertamento", 0.9),
            ("visto contabile", 0.95), ("mandato di pagamento", 0.95)
        ]
        
        lavori_pubblici_terms = [
            ("lavori pubblici", 0.95), ("progetto esecutivo", 0.95), ("manutenzione", 0.9),
            ("cantiere", 0.9), ("opera pubblica", 0.95), ("direzione lavori", 0.9)
        ]
        
        personale_terms = [
            ("personale", 0.9), ("assunzioni", 0.95), ("concorso", 0.95),
            ("selezione", 0.9), ("progressione", 0.85), ("nomina", 0.9)
        ]
        
        def calculate_category_score(terms_list):
            max_score = 0.0
            for term, weight in terms_list:
                if term in full_text:
                    max_score = max(max_score, weight)
            return max_score
        
        scores = {
            'Contabilità': calculate_category_score(contabilita_terms),
            'Lavori Pubblici': calculate_category_score(lavori_pubblici_terms),
            'Personale': calculate_category_score(personale_terms),
            'Regolamenti': calculate_category_score([("regolamento", 0.95), ("approvazione regolamento", 0.95)]),
            'Pubblicazioni': calculate_category_score([("pubblicazione", 0.9), ("albo pretorio", 0.95)]),
            'Organizzazione': calculate_category_score([("protocollo", 0.85), ("ufficio", 0.8)])
        }
        
        best_category = max(scores.items(), key=lambda x: x[1])
        
        if best_category[1] > 0.5:
            if return_confidence:
                confidence, confidence_level = scorer.calculate_composite_confidence(
                    'rule_based', rule_strength=best_category[1]
                )
                result = (best_category[0], confidence, confidence_level)
            else:
                result = best_category[0]
            rule_cache.set(cache_key, result)
            return result
        
        # Regole aggiuntive
        if any(term in full_text for term in ["ufficio tecnico", "ingegnere", "architetto"]):
            result = ("Lavori Pubblici", 0.9, "high") if return_confidence else "Lavori Pubblici"
            rule_cache.set(cache_key, result)
            return result
        
        if any(term in full_text for term in ["ufficio ragioneria", "ragioniere", "contabilità"]):
            result = ("Contabilità", 0.95, "high") if return_confidence else "Contabilità"
            rule_cache.set(cache_key, result)
            return result
        
        if any(term in full_text for term in ["ufficio personale", "dipendenti"]):
            result = ("Personale", 0.9, "high") if return_confidence else "Personale"
            rule_cache.set(cache_key, result)
            return result
        
        if return_confidence:
            result = (None, 0.0, "low")
        else:
            result = None
        rule_cache.set(cache_key, result)
        return result
    
    def identify_uncertain_predictions(
        self, 
        df: pd.DataFrame, 
        confidence_column: str = "classification_confidence_score"
    ) -> pd.DataFrame:
        """
        Identifica le predizioni incerte che necessitano feedback.
        
        Args:
            df: DataFrame con i documenti
            confidence_column: Nome della colonna con i punteggi di confidenza
            
        Returns:
            DataFrame con solo i documenti incerti
        """
        if confidence_column not in df.columns:
            logger.warning(f"Colonna {confidence_column} non trovata")
            return pd.DataFrame()
        
        # Filtra documenti con bassa confidenza
        uncertain_mask = df[confidence_column] < self.sampler.threshold
        return df[uncertain_mask]
    
    def request_feedback_for_uncertain(
        self, 
        df: pd.DataFrame, 
        confidence_column: str = "classification_confidence_score"
    ) -> List[Dict[str, Any]]:
        """
        Crea richieste di feedback per i documenti incerti.
        
        Args:
            df: DataFrame con i documenti
            confidence_column: Nome della colonna con i punteggi di confidenza
            
        Returns:
            Lista di dizionari con le richieste di feedback
        """
        uncertain_df = self.identify_uncertain_predictions(df, confidence_column)
        
        feedback_requests = []
        for idx, row in uncertain_df.iterrows():
            request = {
                "document_id": row.get("pdf_name", row.get("id", str(idx))),
                "text": row.get("text", ""),
                "oggetto": row.get("oggetto", ""),
                "current_category": row.get("category", ""),
                "confidence": row.get(confidence_column),
                "timestamp": pd.Timestamp.now().isoformat()
            }
            feedback_requests.append(request)
        
        logger.info(f"Created {len(feedback_requests)} feedback requests for uncertain predictions")
        return feedback_requests
    
    def apply_feedback_and_update(
        self, 
        df: pd.DataFrame, 
        feedbacks: List[Feedback]
    ) -> pd.DataFrame:
        """
        Applica i feedback e aggiorna il DataFrame.
        
        Args:
            df: DataFrame originale
            feedbacks: Lista di Feedback con le correzioni
            
        Returns:
            DataFrame aggiornato con le correzioni
        """
        # Crea un dizionario per un accesso rapido ai feedback
        feedback_dict = {f.document_id: f for f in feedbacks}
        
        # Aggiorna il DataFrame con le correzioni
        for idx, row in df.iterrows():
            doc_id = row.get("pdf_name", row.get("id", str(idx)))
            if doc_id in feedback_dict:
                feedback = feedback_dict[doc_id]
                df.loc[idx, 'category'] = feedback.corrected_category
                df.loc[idx, 'classification_confidence'] = 'high'
                df.loc[idx, 'classification_confidence_score'] = 0.95
                df.loc[idx, 'classification_method'] = 'manual'
        
        # Salva i feedback
        for feedback in feedbacks:
            self.feedback_manager.submit_feedback(
                document_id=feedback.document_id,
                original_category=feedback.original_category,
                corrected_category=feedback.corrected_category,
                text=feedback.text,
                oggetto=feedback.oggetto,
                confidence=feedback.confidence,
                user_id=feedback.user_id
            )
        
        # Retrain se abbiamo abbastanza feedback
        if self.feedback_manager.feedback_store.get_feedback_count() >= 50:
            logger.info("Enough feedback collected, retraining model...")
            self.feedback_manager.enhance_existing_model()
        
        return df
    
    def process_with_active_learning(
        self, 
        df: pd.DataFrame, 
        model=None, 
        vectorizer=None
    ) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
        """
        Elabora il DataFrame con Active Learning.
        
        Args:
            df: DataFrame con i documenti
            model: Modello ML (opzionale)
            vectorizer: Vettorizzatore (opzionale)
            
        Returns:
            Tuple di (DataFrame aggiornato, lista di richieste di feedback)
        """
        # Aggiungi colonne di confidenza se non esistono
        df = self._add_confidence_columns(df)
        
        # Applica le regole con caching
        df = self._apply_rules_to_dataframe(df)
        
        # Identifica e richiedi feedback per predizioni incerte
        feedback_requests = self.request_feedback_for_uncertain(df)
        
        # Se abbiamo un modello, applica anche le predizioni ML
        if model is not None:
            df = self._apply_ml_predictions(df, model, vectorizer)
            
            # Re-identifica le predizioni incerte dopo ML
            feedback_requests = self.request_feedback_for_uncertain(df)
        
        return df, feedback_requests
    
    def _add_confidence_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        """Aggiunge le colonne di confidenza se non esistono."""
        if 'classification_confidence' not in df.columns:
            confidence_map = {
                'high': 'high', 'medium': 'medium', 'low': 'low',
                'ambiguous': 'low', 'high_ml': 'high', 'ml_predicted': 'medium'
            }
            df['classification_confidence'] = df.get('confidence', 'low').map(confidence_map).fillna('low')
        
        if 'classification_confidence_score' not in df.columns:
            score_map = {'high': 0.9, 'medium': 0.7, 'low': 0.4, 'ambiguous': 0.3}
            df['classification_confidence_score'] = df['classification_confidence'].map(score_map).fillna(0.3)
        
        if 'classification_method' not in df.columns:
            method_map = {
                'high': 'rule_based', 'medium': 'ml_predicted',
                'low': 'default', 'ambiguous': 'default'
            }
            df['classification_method'] = df['classification_confidence'].map(method_map).fillna('default')
        
        return df
    
    def _apply_rules_to_dataframe(self, df: pd.DataFrame) -> pd.DataFrame:
        """Applica le regole di classificazione al DataFrame."""
        text_col = 'text_preview' if 'text_preview' in df.columns else 'text'
        oggetto_col = 'oggetto' if 'oggetto' in df.columns else 'title'
        
        for idx, row in df.iterrows():
            text_val = row[text_col] if text_col in row.index else ""
            oggetto_val = row[oggetto_col] if oggetto_col in row.index else ""
            
            result = self.apply_advanced_classification_rules_cached(
                text_val, oggetto_val, return_confidence=True
            )
            
            if result and result[0] is not None:
                category, confidence, confidence_level = result
                df.loc[idx, 'category'] = category
                df.loc[idx, 'classification_confidence'] = confidence_level
                df.loc[idx, 'classification_confidence_score'] = confidence
                df.loc[idx, 'classification_method'] = 'rule_based'
        
        return df
    
    def _apply_ml_predictions(
        self, 
        df: pd.DataFrame, 
        model, 
        vectorizer=None
    ) -> pd.DataFrame:
        """Applica le predizioni ML al DataFrame."""
        text_col = 'text_preview' if 'text_preview' in df.columns else 'text'
        
        # Filtra documenti con bassa confidenza
        low_conf_mask = df['classification_confidence'].isin(['ambiguous', 'low'])
        low_conf_docs = df[low_conf_mask]
        
        if len(low_conf_docs) > 0:
            try:
                X = low_conf_docs[text_col].astype(str)
                
                if vectorizer:
                    X_vec = vectorizer.transform(X)
                else:
                    X_vec = X
                
                predictions = model.predict(X_vec)
                prediction_probs = model.predict_proba(X_vec)
                max_probs = np.max(prediction_probs, axis=1)
                
                for i, idx in enumerate(low_conf_docs.index):
                    df.loc[idx, 'category'] = predictions[i]
                    
                    confidence, confidence_level = scorer.calculate_composite_confidence(
                        'ml_predicted', probability=max_probs[i]
                    )
                    
                    df.loc[idx, 'classification_confidence'] = confidence_level
                    df.loc[idx, 'classification_confidence_score'] = confidence
                    df.loc[idx, 'classification_method'] = 'ml_predicted'
                
            except Exception as e:
                logger.warning(f"Error applying ML predictions: {e}")
        
        return df


# Funzione conveniente per accesso globale
_active_learning_post_processor: Optional[ActiveLearningPostProcessor] = None


def get_active_learning_post_processor(
    uncertainty_threshold: float = 0.7,
    max_workers: int = 4
) -> ActiveLearningPostProcessor:
    """
    Get the global ActiveLearningPostProcessor instance.
    
    Args:
        uncertainty_threshold: Soglia di incertezza
        max_workers: Numero massimo di worker
        
    Returns:
        ActiveLearningPostProcessor instance
    """
    global _active_learning_post_processor
    if _active_learning_post_processor is None:
        _active_learning_post_processor = ActiveLearningPostProcessor(
            uncertainty_threshold=uncertainty_threshold,
            max_workers=max_workers
        )
    return _active_learning_post_processor
