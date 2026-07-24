import re
import json
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
import pandas as pd
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.ensemble import RandomForestClassifier
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import LabelEncoder
from scipy.sparse import csr_matrix  # Import csr_matrix
import joblib


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
            # Se rf_model è un Random Forest standalone, non fare nulla di particolare
        except Exception as e:
            logger.warning(f"Impossibile estrarre componenti dal modello: {e}")

    def classify(self, oggetto: Optional[str], text: str) -> Tuple[Optional[str], Optional[str], Optional[float], Optional[str]]:
        """
        Classifica un documento in base all'oggetto e al testo.
        Ritorna: (categoria, sottocategoria, confidenza, termini_riconosciuti)
        """
        # Controllo aggiunto all'inizio per gestire completamente eventuali matrici sparse
        if hasattr(oggetto, 'toarray') or hasattr(oggetto, 'todense') or hasattr(oggetto, 'shape'):
            logger.warning("Oggetto sembra essere una matrice invece di testo, usando fallback a regole")
            oggetto = ""
        if hasattr(text, 'toarray') or hasattr(text, 'todense') or hasattr(text, 'shape'):
            logger.warning("Text sembra essere una matrice invece di testo, usando fallback a regole")
            text = ""
        
        if not text and not oggetto:
            return "unknown", None, None, None
            
        # Assicuriamoci che text e oggetto siano stringhe valide
        full_text = ""
        if oggetto:
            # Gestisci oggetto in modo molto robusto per evitare sparse matrix
            if isinstance(oggetto, str):
                full_text += oggetto
            elif hasattr(oggetto, '__str__') and not hasattr(oggetto, 'toarray'):
                try:
                    # Check if oggetto behaves like an array (avoiding truth value error)
                    if hasattr(oggetto, '__len__') and len(oggetto) > 0 and hasattr(oggetto, '__getitem__'):
                        # This could be an array-like object, convert safely
                        full_text += str(oggetto.flatten()[:50]) if hasattr(oggetto, 'flatten') else str(oggetto.flat)[:100] if hasattr(oggetto, 'flat') else str(oggetto)[:100]
                    else:
                        full_text += str(oggetto)
                except (ValueError, TypeError):
                    # If conversion fails, skip it
                    logger.debug(f"Cannot convert oggetto of type {type(oggetto)}, skipping")
            else:
                # Se oggetto è una sparse matrix o altro tipo problematico, lo ignoriamo
                logger.debug(f"Ignoring non-string oggetto of type: {type(oggetto)}")
        
        full_text += " "
        
        if text:
            # Gestisci text in modo molto robusto per evitare sparse matrix
            if isinstance(text, str):
                full_text += text
            elif hasattr(text, '__str__') and not hasattr(text, 'toarray'):
                try:
                    # Check if text behaves like an array (avoiding truth value error)
                    if hasattr(text, '__len__') and len(text) > 0 and hasattr(text, '__getitem__'):
                        # This could be an array-like object, convert safely
                        full_text += str(text.flatten()[:50]) if hasattr(text, 'flatten') else str(text.flat)[:100] if hasattr(text, 'flat') else str(text)[:100]
                    else:
                        full_text += str(text)
                except (ValueError, TypeError):
                    # If conversion fails, skip it
                    logger.debug(f"Cannot convert text of type {type(text)}, skipping")
            else:
                # Se text è una sparse matrix o altro tipo problematico, lo convertiamo in modo sicuro
                logger.debug(f"Converting non-string text of type: {type(text)}")
                if hasattr(text, 'toarray'):
                    # E' una sparse matrix, la convertiamo a stringa
                    try:
                        text_array = text.toarray() if hasattr(text, 'toarray') else text
                        full_text += str(text_array.flatten()[:100])  # Solo primi 100 elementi per sicurezza
                    except:
                        full_text += ""
                else:
                    full_text += str(text) if text is not None else ""
        
        # Controllo aggiunto per assicurarsi che full_text non sia un CSR matrix o altra struttura dati
        if hasattr(full_text, 'toarray') or hasattr(full_text, 'todense') or hasattr(full_text, 'shape'):
            logger.warning("Input sembra essere una matrice invece di testo, usando fallback a regole")
            return self._classify_by_rules("", str(oggetto) if oggetto is not None else "")
        
        # Converti a stringa e poi a minuscolo in modo sicuro
        try:
            full_text = str(full_text).lower()
        except Exception as e:
            logger.warning(f"Errore nella conversione del testo: {e}, usando fallback a regole")
            return self._classify_by_rules("", str(oggetto) if oggetto is not None else "")
            
        # Prova la classificazione ML se disponibile
        if self.rf_model:
            try:
                # Assicurati che il vectorizer sia disponibile
                if not self.vectorizer:
                    logger.warning("Vectorizer non disponibile, usando fallback a regole")
                    return self._classify_by_rules(full_text, str(oggetto) if oggetto is not None else "")
                
                # Verifica che full_text non sia una matrice prima della trasformazione
                if hasattr(full_text, 'shape'):
                    logger.warning("full_text ha shape (è una matrice), usando fallback a regole")
                    return self._classify_by_rules(full_text, str(oggetto) if oggetto is not None else "")
                
                # Trasforma il testo usando il vectorizer
                X = self.vectorizer.transform([full_text])
                
                # Predizione - controllo aggiunto per assicurarsi che X sia una matrice valida
                if hasattr(X, 'toarray'):
                    # E' una sparse matrix, va bene
                    pass
                else:
                    logger.warning("X non è una matrice valida per la classificazione ML")
                    raise ValueError("X non è una matrice valida")
                
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
                logger.warning(f"Errore nella classificazione ML: {e}, usando fallback a regole")
                return self._classify_by_rules(full_text, str(oggetto) if oggetto is not None else "")
        else:
            # Fallback a classificazione basata su regole
            return self._classify_by_rules(full_text, str(oggetto) if oggetto is not None else "")

    def _classify_by_rules(self, full_text: str, oggetto: Optional[str]) -> Tuple[Optional[str], Optional[str], Optional[float], Optional[str]]:
        """Classifica usando regole basilari."""
        recognized_terms = []
        
        # Assicuriamoci che full_text sia una stringa
        if not isinstance(full_text, str):
            if full_text is None:
                full_text = ""
            else:
                full_text = str(full_text)
        
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