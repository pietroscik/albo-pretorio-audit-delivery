import re
import json
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
import joblib
import numpy as np

from ..utils.logger import get_logger
from ..utils.config import get_config

logger = get_logger("document_classifier")

class DocumentClassifier:
    """
    Classificatore di documenti basato su ML (Random Forest) con possibilità di fallback a regole.
    """
    
    def __init__(self, rf_model=None):
        self.config = get_config()
        self.rf_model = rf_model  # Modello ML fornito esternamente (da analyze_albo.py)
        self.vectorizer = None
        self.label_encoder = None
        self.rules_enabled = True
        
        # Carica eventuali regole di classificazione da file di configurazione
        self._load_classification_rules()
        
        # Se è stato fornito un modello ML, estrai il vectorizer e label encoder se disponibili
        if self.rf_model:
            self._extract_components_from_bundle()

    def _load_classification_rules(self):
        """Carica le regole di classificazione da file di configurazione."""
        # Regole basilari per fallback
        self.category_keywords = {
            "Personale": ["personale", "dipendente", "assunzione", "turnover", "organico", "funzione pubblica"],
            "Contabilità": ["impegno", "liquidazione", "mandato", "spesa", "bilancio", "conto consuntivo"],
            "Appalti": ["appalto", "gara", "aggiudicazione", "cig", "cup", "stazione appaltante"],
            "Urbanistica": ["urbanistica", "piano", "territorio", "prgc", "pug", "variant"],
            "Ambiente": ["ambiente", "rifiuti", "inquinamento", "bonifica"],
            "Servizi Sociali": ["sociale", "anziani", "minori", "handicap", "disabili"],
            "Cultura": ["cultura", "biblioteca", "mostre", "evento culturale", "patrimonio"],
            "Sport": ["sport", "impianto sportivo", "associazione sportiva", "manifestazione sportiva"],
            "Turismo": ["turismo", "promozione", "iniziativa", "evento turistico"],
            "Lavori Pubblici": ["lavori pubblici", "manutenzione", "infrastruttura", "strada", "edilizia"],
            "Affari Generali": ["protocollo", "affari generali", "segreteria", "consiglio comunale", "giunta"],
            "Legale": ["controversia", "avvocatura", "patrocinio", "sentenza", "tribunale"]
        }
        
        # Tipologie documentali
        self.doc_type_patterns = {
            "Delibera": ["delibera", "giunta", "consiglio"],
            "Determinazione": ["determinazione", "determina", "dirigente"],
            "Ordinanza": ["ordinanza", "sindaco"],
            "Avviso": ["avviso", "pubblicato"],
            "Bando": ["bando", "gara", "manifestazione interesse"],
            "Atto": ["atto", "documento"]
        }

    def _extract_components_from_bundle(self):
        """Estrae vectorizer e label encoder da un modello bundle se disponibili."""
        # Cerca di ottenere il vectorizer e label encoder dal modello
        # Questo dipende da come è stato salvato il modello
        try:
            if hasattr(self.rf_model, 'steps'):  # Pipeline
                for name, step in self.rf_model.steps:
                    if isinstance(step, TfidfVectorizer):
                        self.vectorizer = step
                    elif isinstance(step, LabelEncoder):
                        self.label_encoder = step
                    elif hasattr(step, 'classes_'):
                        # Provvisorio: crea label encoder se non esiste
                        if self.label_encoder is None:
                            self.label_encoder = LabelEncoder()
                            self.label_encoder.classes_ = step.classes_
        except Exception as e:
            logger.warning(f"Impossibile estrarre componenti dal modello: {e}")

    def classify(self, oggetto: Optional[str], text: str) -> Tuple[Optional[str], Optional[str], Optional[float], Optional[str]]:
        """
        Classifica un documento in base all'oggetto e al testo.
        Ritorna: (categoria, sottocategoria, confidenza, termini_riconosciuti)
        """
        if not text and not oggetto:
            return "unknown", None, None, None
            
        full_text = f"{oggetto or ''} {text}".lower()
        
        # Prova la classificazione ML se disponibile
        if self.rf_model:
            try:
                # Assicurati che il vectorizer sia disponibile
                if self.vectorizer:
                    # Trasforma il testo usando il vectorizer
                    X = self.vectorizer.transform([full_text])
                    
                    # Predizione
                    prediction = self.rf_model.predict(X)[0]
                    probabilities = self.rf_model.predict_proba(X)[0]
                    
                    # Calcola confidenza
                    confidence = float(max(probabilities))
                    
                    # Decodifica etichetta se necessario
                    if self.label_encoder:
                        predicted_label = self.label_encoder.inverse_transform([prediction])[0]
                    else:
                        predicted_label = str(prediction)
                        
                    return predicted_label, None, confidence, "ml_prediction"
                    
            except Exception as e:
                logger.warning(f"Classificazione ML fallita: {e}")
        
        # Fallback a classificazione basata su regole
        return self._classify_by_rules(full_text, oggetto)

    def _classify_by_rules(self, full_text: str, oggetto: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[float], Optional[str]]:
        """Classifica usando regole basilari."""
        recognized_terms = []
        
        # Identifica tipo documento
        doc_type = None
        for dtype, patterns in self.doc_type_patterns.items():
            if any(pattern in full_text for pattern in patterns):
                doc_type = dtype
                recognized_terms.extend(patterns)
                break
        
        # Identifica categoria
        best_category = "Affari Generali"  # Default
        best_score = 0
        
        for category, keywords in self.category_keywords.items():
            score = sum(1 for kw in keywords if kw in full_text)
            if score > best_score:
                best_score = score
                best_category = category
                recognized_terms.extend([kw for kw in keywords if kw in full_text][:3])  # Limita termini riconosciuti
        
        # Se non abbiamo trovato nulla di significativo, usa 'unknown'
        if best_score == 0:
            best_category = "unknown"
            confidence = 0.1
        else:
            # Calcola confidenza approssimativa
            confidence = min(0.9, 0.1 + (best_score * 0.1))
        
        return best_category, doc_type, confidence, ", ".join(recognized_terms[:5])

    def fit(self, texts: list, labels: list):
        """
        Addestra il classificatore (opzionale, usato principalmente per testing).
        """
        logger.warning("Il training non è implementato completamente in questo costruttore. "
                      "Il modello dovrebbe essere fornito esternamente.")
        # Placeholder per futuro addestramento
        pass

    def save(self, filepath: str):
        """Salva il classificatore."""
        # Salva come bundle se possibile
        bundle = {
            'model': self.rf_model,
            'vectorizer': self.vectorizer,
            'label_encoder': self.label_encoder,
            'category_keywords': self.category_keywords,
            'doc_type_patterns': self.doc_type_patterns
        }
        joblib.dump(bundle, filepath)

    @classmethod
    def load(cls, filepath: str):
        """Carica un classificatore salvato."""
        bundle = joblib.load(filepath)
        
        instance = cls()
        instance.rf_model = bundle.get('model')
        instance.vectorizer = bundle.get('vectorizer')
        instance.label_encoder = bundle.get('label_encoder')
        instance.category_keywords = bundle.get('category_keywords', {})
        instance.doc_type_patterns = bundle.get('doc_type_patterns', {})
        
        return instance