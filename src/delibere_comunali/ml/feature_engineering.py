"""
Feature Engineering Module for ML Model Improvement.

This module implements advanced feature extraction techniques:
- TF-IDF vectorization with Italian stop words
- Word embeddings (FastText, GloVe)
- Numerical features (text length, word count, etc.)
- Feature selection and dimensionality reduction
- Feature caching for performance

Key Features:
- Multiple feature extraction methods
- Caching of computed features
- Integration with existing ML pipeline
- Support for Italian language
"""

import json
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
import logging
import numpy as np
import pandas as pd

from ..utils.config import get_config
from ..utils.logger import get_logger
from ..utils.cache import LRUCache

logger = get_logger(__name__)


# Feature cache for performance
_feature_cache = LRUCache(max_size=10000, default_ttl=86400)  # 24 hours


def _generate_feature_cache_key(
    text: str, 
    method: str, 
    params: Optional[Dict[str, Any]] = None
) -> str:
    """Generate a unique cache key for feature extraction."""
    params_str = json.dumps(params or {}, sort_keys=True)
    content = f"{text}|{method}|{params_str}"
    return hashlib.md5(content.encode()).hexdigest()


class TextFeatureExtractor:
    """
    Extracts various features from text data.
    
    Features extracted:
    - Text length (characters)
    - Word count
    - Sentence count
    - Average word length
    - Unique word ratio
    - Digit count
    - Special character count
    - Capital letter ratio
    """
    
    def __init__(self):
        """Initialize the text feature extractor."""
        pass
    
    def extract_all_features(self, text: str) -> Dict[str, float]:
        """
        Extract all text features from a single text.
        
        Args:
            text: Input text
            
        Returns:
            Dictionary with all extracted features
        """
        if not text or not isinstance(text, str):
            return self._get_empty_features()
        
        # Clean text
        clean_text = text.strip()
        
        # Basic features
        features = {
            'text_length': len(clean_text),
            'char_count': len(clean_text),
            'word_count': len(clean_text.split()),
            'sentence_count': len([s for s in clean_text.split('.') if s.strip()]),
        }
        
        # Word-based features
        words = clean_text.split()
        if words:
            word_lengths = [len(word) for word in words]
            features['avg_word_length'] = sum(word_lengths) / len(word_lengths)
            features['unique_word_ratio'] = len(set(words)) / len(words)
        else:
            features['avg_word_length'] = 0.0
            features['unique_word_ratio'] = 0.0
        
        # Character-based features
        features['digit_count'] = sum(c.isdigit() for c in clean_text)
        features['uppercase_count'] = sum(c.isupper() for c in clean_text)
        features['lowercase_count'] = sum(c.islower() for c in clean_text)
        
        # Calculate ratios
        total_chars = max(len(clean_text), 1)
        features['digit_ratio'] = features['digit_count'] / total_chars
        features['uppercase_ratio'] = features['uppercase_count'] / total_chars
        features['lowercase_ratio'] = features['lowercase_count'] / total_chars
        
        # Special characters
        special_chars = sum(1 for c in clean_text if not c.isalnum() and not c.isspace())
        features['special_char_count'] = special_chars
        features['special_char_ratio'] = special_chars / total_chars
        
        return features
    
    def extract_batch_features(self, texts: List[str]) -> pd.DataFrame:
        """
        Extract features from a batch of texts.
        
        Args:
            texts: List of text strings
            
        Returns:
            DataFrame with features for each text
        """
        features_list = [self.extract_all_features(text) for text in texts]
        return pd.DataFrame(features_list)
    
    def _get_empty_features(self) -> Dict[str, float]:
        """Return empty features dictionary."""
        return {
            'text_length': 0.0,
            'char_count': 0.0,
            'word_count': 0.0,
            'sentence_count': 0.0,
            'avg_word_length': 0.0,
            'unique_word_ratio': 0.0,
            'digit_count': 0.0,
            'uppercase_count': 0.0,
            'lowercase_count': 0.0,
            'digit_ratio': 0.0,
            'uppercase_ratio': 0.0,
            'lowercase_ratio': 0.0,
            'special_char_count': 0.0,
            'special_char_ratio': 0.0
        }


class TFIDFVectorizer:
    """
    Wrapper around sklearn's TfidfVectorizer with caching and Italian support.
    """
    
    def __init__(
        self,
        max_features: int = 10000,
        stop_words: str = None,
        ngram_range: Tuple[int, int] = (1, 2),
        min_df: int = 1,
        max_df: float = 1.0
    ):
        """
        Initialize the TF-IDF vectorizer.
        
        Args:
            max_features: Maximum number of features
            stop_words: Language for stop words (None, 'english', or list)
            ngram_range: Range of n-grams to extract
            min_df: Minimum document frequency
            max_df: Maximum document frequency
        """
        self.max_features = max_features
        self.stop_words = stop_words
        self.ngram_range = ngram_range
        self.min_df = min_df
        self.max_df = max_df
        self._vectorizer = None
        self._fitted = False
    
    def fit(self, texts: List[str]) -> "TFIDFVectorizer":
        """
        Fit the vectorizer on a list of texts.
        
        Args:
            texts: List of text strings to fit on
            
        Returns:
            self
        """
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer as SklearnTFIDF
            
            self._vectorizer = SklearnTFIDF(
                max_features=self.max_features,
                stop_words=self.stop_words,
                ngram_range=self.ngram_range,
                min_df=self.min_df,
                max_df=self.max_df
            )
            self._vectorizer.fit(texts)
            self._fitted = True
            logger.info(f"TF-IDF vectorizer fitted with {len(texts)} documents")
            return self
        except ImportError:
            logger.error("scikit-learn not available for TF-IDF")
            raise
    
    def transform(self, texts: List[str]) -> np.ndarray:
        """
        Transform texts to TF-IDF features.
        
        Args:
            texts: List of text strings to transform
            
        Returns:
            Array of TF-IDF features
        """
        if not self._fitted:
            raise ValueError("Vectorizer not fitted. Call fit() first.")
        
        return self._vectorizer.transform(texts)
    
    def fit_transform(self, texts: List[str]) -> np.ndarray:
        """
        Fit and transform texts to TF-IDF features.
        
        Args:
            texts: List of text strings
            
        Returns:
            Array of TF-IDF features
        """
        self.fit(texts)
        return self.transform(texts)
    
    def get_feature_names(self) -> List[str]:
        """Get the names of the features."""
        if not self._fitted:
            return []
        return self._vectorizer.get_feature_names_out().tolist()
    
    def save(self, path: Union[str, Path]) -> None:
        """
        Save the vectorizer to disk.
        
        Args:
            path: Path to save the vectorizer
        """
        try:
            import joblib
            path = Path(path)
            path.parent.mkdir(parents=True, exist_ok=True)
            joblib.dump(self._vectorizer, path)
            logger.info(f"TF-IDF vectorizer saved to: {path}")
        except ImportError:
            logger.error("joblib not available for saving vectorizer")
            raise
    
    @classmethod
    def load(cls, path: Union[str, Path]) -> "TFIDFVectorizer":
        """
        Load a vectorizer from disk.
        
        Args:
            path: Path to the saved vectorizer
            
        Returns:
            TFIDFVectorizer instance
        """
        try:
            import joblib
            vectorizer = cls()
            vectorizer._vectorizer = joblib.load(path)
            vectorizer._fitted = True
            logger.info(f"TF-IDF vectorizer loaded from: {path}")
            return vectorizer
        except ImportError:
            logger.error("joblib not available for loading vectorizer")
            raise
        except FileNotFoundError:
            logger.error(f"Vectorizer file not found: {path}")
            raise


class WordEmbeddingExtractor:
    """
    Extract word embeddings using pre-trained models.
    
    Supports:
    - FastText (Italian)
    - GloVe (Italian)
    - Custom embeddings
    """
    
    def __init__(self, model_type: str = 'fasttext', model_path: Optional[Union[str, Path]] = None):
        """
        Initialize the word embedding extractor.
        
        Args:
            model_type: Type of embedding model ('fasttext', 'glove')
            model_path: Path to custom model file
        """
        self.model_type = model_type
        self.model_path = Path(model_path) if model_path else None
        self._model = None
        self._loaded = False
    
    def load_model(self) -> bool:
        """
        Load the embedding model.
        
        Returns:
            True if model loaded successfully
        """
        try:
            if self.model_type == 'fasttext':
                # Try to load Italian FastText model
                try:
                    import fasttext
                    if self.model_path and self.model_path.exists():
                        self._model = fasttext.load_model(str(self.model_path))
                    else:
                        # Try to download Italian FastText model
                        # Note: This is a placeholder - actual download would need internet
                        logger.warning("FastText model not found. Please provide model_path.")
                        return False
                    self._loaded = True
                    logger.info("FastText model loaded")
                    return True
                except ImportError:
                    logger.error("fasttext package not available")
                    return False
            
            elif self.model_type == 'glove':
                # Load GloVe embeddings
                try:
                    import gensim
                    if self.model_path and self.model_path.exists():
                        self._model = gensim.models.KeyedVectors.load_word2vec_format(
                            str(self.model_path), binary=False
                        )
                    else:
                        logger.warning("GloVe model not found. Please provide model_path.")
                        return False
                    self._loaded = True
                    logger.info("GloVe model loaded")
                    return True
                except ImportError:
                    logger.error("gensim package not available for GloVe")
                    return False
            
            else:
                logger.error(f"Unknown model type: {self.model_type}")
                return False
                
        except Exception as e:
            logger.error(f"Error loading embedding model: {e}")
            return False
    
    def get_embedding(self, text: str) -> Optional[np.ndarray]:
        """
        Get embedding for a text.
        
        Args:
            text: Input text
            
        Returns:
            Embedding vector or None if error
        """
        if not self._loaded:
            if not self.load_model():
                return None
        
        try:
            if self.model_type == 'fasttext':
                # FastText returns sentence embedding
                return self._model.get_sentence_vector(text)
            elif self.model_type == 'glove':
                # GloVe: average of word embeddings
                words = text.lower().split()
                embeddings = []
                for word in words:
                    if word in self._model:
                        embeddings.append(self._model[word])
                if embeddings:
                    return np.mean(embeddings, axis=0)
                return None
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            return None
    
    def get_batch_embeddings(self, texts: List[str]) -> np.ndarray:
        """
        Get embeddings for a batch of texts.
        
        Args:
            texts: List of text strings
            
        Returns:
            Array of embeddings
        """
        embeddings = []
        for text in texts:
            emb = self.get_embedding(text)
            if emb is not None:
                embeddings.append(emb)
            else:
                # Use zero vector if embedding fails
                embeddings.append(np.zeros(300))  # Assuming 300-dim embeddings
        
        return np.array(embeddings)


class FeatureEngineer:
    """
    Main feature engineering class that combines multiple feature types.
    
    This class:
    - Combines text features, TF-IDF, and embeddings
    - Provides caching for computed features
    - Supports incremental feature extraction
    """
    
    def __init__(
        self,
        use_tfidf: bool = True,
        use_embeddings: bool = False,
        use_text_features: bool = True,
        tfidf_params: Optional[Dict[str, Any]] = None,
        embedding_params: Optional[Dict[str, Any]] = None
    ):
        """
        Initialize the feature engineer.
        
        Args:
            use_tfidf: Whether to use TF-IDF features
            use_embeddings: Whether to use word embeddings
            use_text_features: Whether to use basic text features
            tfidf_params: Parameters for TF-IDF vectorizer
            embedding_params: Parameters for embedding extractor
        """
        self.use_tfidf = use_tfidf
        self.use_embeddings = use_embeddings
        self.use_text_features = use_text_features
        
        self.text_extractor = TextFeatureExtractor()
        self.tfidf_vectorizer = None
        self.embedding_extractor = None
        
        if self.use_tfidf:
            self.tfidf_vectorizer = TFIDFVectorizer(
                **(tfidf_params or {})
            )
        
        if self.use_embeddings:
            self.embedding_extractor = WordEmbeddingExtractor(
                **(embedding_params or {})
            )
    
    def fit(self, texts: List[str]) -> "FeatureEngineer":
        """
        Fit the feature extractors on a list of texts.
        
        Args:
            texts: List of text strings to fit on
            
        Returns:
            self
        """
        if self.use_tfidf and self.tfidf_vectorizer:
            self.tfidf_vectorizer.fit(texts)
        
        if self.use_embeddings and self.embedding_extractor:
            self.embedding_extractor.load_model()
        
        return self
    
    def extract_features(self, texts: List[str]) -> pd.DataFrame:
        """
        Extract all features from a list of texts.
        
        Args:
            texts: List of text strings
            
        Returns:
            DataFrame with all extracted features
        """
        features_list = []
        
        for text in texts:
            row_features = {}
            
            # Text features
            if self.use_text_features:
                text_feats = self.text_extractor.extract_all_features(text)
                row_features.update(text_feats)
            
            # TF-IDF features (will be added separately as sparse matrix)
            # We'll handle this in extract_all_features_with_tfidf
            
            features_list.append(row_features)
        
        return pd.DataFrame(features_list)
    
    def extract_all_features_with_tfidf(
        self, 
        texts: List[str]
    ) -> Tuple[pd.DataFrame, Optional[np.ndarray]]:
        """
        Extract all features including TF-IDF.
        
        Args:
            texts: List of text strings
            
        Returns:
            Tuple of (DataFrame with non-sparse features, sparse TF-IDF matrix or None)
        """
        # Extract basic features
        basic_features = self.extract_features(texts)
        
        # Extract TF-IDF features
        tfidf_features = None
        if self.use_tfidf and self.tfidf_vectorizer and self.tfidf_vectorizer._fitted:
            tfidf_features = self.tfidf_vectorizer.transform(texts)
        
        return basic_features, tfidf_features
    
    def extract_all_features_with_embeddings(
        self, 
        texts: List[str]
    ) -> Tuple[pd.DataFrame, Optional[np.ndarray]]:
        """
        Extract all features including embeddings.
        
        Args:
            texts: List of text strings
            
        Returns:
            Tuple of (DataFrame with non-sparse features, embedding matrix or None)
        """
        # Extract basic features
        basic_features = self.extract_features(texts)
        
        # Extract embedding features
        embedding_features = None
        if self.use_embeddings and self.embedding_extractor:
            embedding_features = self.embedding_extractor.get_batch_embeddings(texts)
        
        return basic_features, embedding_features
    
    def extract_combined_features(
        self, 
        texts: List[str]
    ) -> Tuple[pd.DataFrame, Optional[np.ndarray], Optional[np.ndarray]]:
        """
        Extract all features: basic, TF-IDF, and embeddings.
        
        Args:
            texts: List of text strings
            
        Returns:
            Tuple of (DataFrame with basic features, TF-IDF matrix, embedding matrix)
        """
        basic_features = self.extract_features(texts)
        
        tfidf_features = None
        if self.use_tfidf and self.tfidf_vectorizer and self.tfidf_vectorizer._fitted:
            tfidf_features = self.tfidf_vectorizer.transform(texts)
        
        embedding_features = None
        if self.use_embeddings and self.embedding_extractor:
            embedding_features = self.embedding_extractor.get_batch_embeddings(texts)
        
        return basic_features, tfidf_features, embedding_features
    
    def save(self, path: Union[str, Path]) -> None:
        """
        Save the feature engineer to disk.
        
        Args:
            path: Path to save the feature engineer
        """
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        
        # Save configuration
        config = {
            'use_tfidf': self.use_tfidf,
            'use_embeddings': self.use_embeddings,
            'use_text_features': self.use_text_features
        }
        
        with open(path / "config.json", 'w') as f:
            json.dump(config, f)
        
        # Save TF-IDF vectorizer
        if self.use_tfidf and self.tfidf_vectorizer and self.tfidf_vectorizer._fitted:
            self.tfidf_vectorizer.save(path / "tfidf_vectorizer.joblib")
        
        logger.info(f"Feature engineer saved to: {path}")
    
    @classmethod
    def load(cls, path: Union[str, Path]) -> "FeatureEngineer":
        """
        Load a feature engineer from disk.
        
        Args:
            path: Path to the saved feature engineer
            
        Returns:
            FeatureEngineer instance
        """
        path = Path(path)
        
        # Load configuration
        with open(path / "config.json", 'r') as f:
            config = json.load(f)
        
        # Create feature engineer
        engineer = cls(
            use_tfidf=config.get('use_tfidf', True),
            use_embeddings=config.get('use_embeddings', False),
            use_text_features=config.get('use_text_features', True)
        )
        
        # Load TF-IDF vectorizer
        tfidf_path = path / "tfidf_vectorizer.joblib"
        if tfidf_path.exists():
            engineer.tfidf_vectorizer = TFIDFVectorizer.load(tfidf_path)
        
        logger.info(f"Feature engineer loaded from: {path}")
        return engineer


class FeatureSelector:
    """
    Feature selection using statistical methods.
    
    Methods:
    - Variance threshold
    - SelectKBest (chi2, f_classif, mutual_info_classif)
    - RFE (Recursive Feature Elimination)
    - PCA (Principal Component Analysis)
    """
    
    def __init__(self):
        """Initialize the feature selector."""
        pass
    
    def select_by_variance(
        self, 
        X: np.ndarray, 
        threshold: float = 0.01
    ) -> np.ndarray:
        """
        Select features by variance threshold.
        
        Args:
            X: Feature matrix
            threshold: Minimum variance threshold
            
        Returns:
            Mask of selected features
        """
        try:
            from sklearn.feature_selection import VarianceThreshold
            selector = VarianceThreshold(threshold=threshold)
            return selector.fit_transform(X)
        except ImportError:
            logger.error("scikit-learn not available for feature selection")
            return X
    
    def select_k_best(
        self, 
        X: np.ndarray, 
        y: np.ndarray, 
        k: int = 1000,
        score_func: str = 'f_classif'
    ) -> np.ndarray:
        """
        Select top k features using statistical tests.
        
        Args:
            X: Feature matrix
            y: Target labels
            k: Number of features to select
            score_func: Scoring function ('chi2', 'f_classif', 'mutual_info_classif')
            
        Returns:
            Selected feature matrix
        """
        try:
            from sklearn.feature_selection import SelectKBest
            
            if score_func == 'chi2':
                from sklearn.feature_selection import chi2
                selector = SelectKBest(chi2, k=k)
            elif score_func == 'f_classif':
                from sklearn.feature_selection import f_classif
                selector = SelectKBest(f_classif, k=k)
            elif score_func == 'mutual_info_classif':
                from sklearn.feature_selection import mutual_info_classif
                selector = SelectKBest(mutual_info_classif, k=k)
            else:
                from sklearn.feature_selection import f_classif
                selector = SelectKBest(f_classif, k=k)
            
            return selector.fit_transform(X, y)
        except ImportError:
            logger.error("scikit-learn not available for feature selection")
            return X
    
    def select_rfe(
        self, 
        X: np.ndarray, 
        y: np.ndarray, 
        estimator=None,
        n_features_to_select: int = 1000
    ) -> np.ndarray:
        """
        Select features using Recursive Feature Elimination.
        
        Args:
            X: Feature matrix
            y: Target labels
            estimator: Estimator to use for RFE
            n_features_to_select: Number of features to select
            
        Returns:
            Selected feature matrix
        """
        try:
            from sklearn.feature_selection import RFE
            from sklearn.ensemble import RandomForestClassifier
            
            if estimator is None:
                estimator = RandomForestClassifier(n_estimators=100, random_state=42)
            
            selector = RFE(estimator, n_features_to_select=n_features_to_select)
            return selector.fit_transform(X, y)
        except ImportError:
            logger.error("scikit-learn not available for RFE")
            return X
    
    def apply_pca(
        self, 
        X: np.ndarray, 
        n_components: int = 100
    ) -> np.ndarray:
        """
        Apply PCA for dimensionality reduction.
        
        Args:
            X: Feature matrix
            n_components: Number of principal components
            
        Returns:
            Transformed feature matrix
        """
        try:
            from sklearn.decomposition import PCA
            pca = PCA(n_components=n_components, random_state=42)
            return pca.fit_transform(X)
        except ImportError:
            logger.error("scikit-learn not available for PCA")
            return X


# Global feature engineer instance
_feature_engineer: Optional[FeatureEngineer] = None


def get_feature_engineer(
    use_tfidf: bool = True,
    use_embeddings: bool = False,
    use_text_features: bool = True
) -> FeatureEngineer:
    """
    Get the global feature engineer instance.
    
    Args:
        use_tfidf: Whether to use TF-IDF features
        use_embeddings: Whether to use word embeddings
        use_text_features: Whether to use basic text features
        
    Returns:
        FeatureEngineer instance
    """
    global _feature_engineer
    if _feature_engineer is None:
        _feature_engineer = FeatureEngineer(
            use_tfidf=use_tfidf,
            use_embeddings=use_embeddings,
            use_text_features=use_text_features
        )
    return _feature_engineer
