"""
Feedback Handler Module for Active Learning.

This module implements a system for collecting user feedback on classification
predictions and using it to improve ML models through active learning.

Key Features:
- Collect user corrections for misclassified documents
- Store feedback in a structured format
- Retrain models incrementally with new feedback data
- Integrate with existing post-processing pipeline
"""

import json
import os
import hashlib
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime
import logging
import pandas as pd
import numpy as np

from ..utils.config import get_config
from ..utils.logger import get_logger

logger = get_logger(__name__)


class Feedback:
    """Represents a single piece of user feedback."""
    
    def __init__(
        self,
        document_id: str,
        original_category: str,
        corrected_category: str,
        text: str,
        oggetto: str = "",
        confidence: Optional[float] = None,
        user_id: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ):
        self.document_id = document_id
        self.original_category = original_category
        self.corrected_category = corrected_category
        self.text = text
        self.oggetto = oggetto
        self.confidence = confidence
        self.user_id = user_id
        self.timestamp = timestamp or datetime.now()
        
        # Generate unique feedback ID
        self.feedback_id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate a unique ID for this feedback."""
        content = f"{self.document_id}{self.original_category}{self.corrected_category}{self.timestamp.isoformat()}"
        return hashlib.md5(content.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert feedback to dictionary."""
        return {
            "feedback_id": self.feedback_id,
            "document_id": self.document_id,
            "original_category": self.original_category,
            "corrected_category": self.corrected_category,
            "text": self.text,
            "oggetto": self.oggetto,
            "confidence": self.confidence,
            "user_id": self.user_id,
            "timestamp": self.timestamp.isoformat()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Feedback":
        """Create feedback from dictionary."""
        return cls(
            document_id=data.get("document_id", ""),
            original_category=data.get("original_category", ""),
            corrected_category=data.get("corrected_category", ""),
            text=data.get("text", ""),
            oggetto=data.get("oggetto", ""),
            confidence=data.get("confidence"),
            user_id=data.get("user_id"),
            timestamp=datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat()))
        )


class FeedbackStore:
    """
    Store and manage user feedback for active learning.
    
    Supports multiple storage backends:
    - JSON files (default)
    - CSV files
    - Database (future)
    """
    
    def __init__(self, storage_path: Optional[Union[str, Path]] = None):
        """
        Initialize the feedback store.
        
        Args:
            storage_path: Path to the feedback storage directory
        """
        config = get_config()
        
        if storage_path is None:
            # Default storage path
            data_dir = config.get_path("DATA_DIR")
            self.storage_path = data_dir / "feedback"
        else:
            self.storage_path = Path(storage_path)
        
        # Ensure storage directory exists
        self.storage_path.mkdir(parents=True, exist_ok=True)
        
        # Feedback file paths
        self.feedback_file = self.storage_path / "feedback.jsonl"
        self.feedback_csv = self.storage_path / "feedback.csv"
        
        logger.info(f"Feedback store initialized at: {self.storage_path}")
    
    def save_feedback(self, feedback: Feedback) -> bool:
        """
        Save a single feedback to storage.
        
        Args:
            feedback: Feedback object to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            # Save to JSONL (one feedback per line)
            with open(self.feedback_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(feedback.to_dict(), ensure_ascii=False) + '\n')
            
            # Also save to CSV for easier analysis
            self._update_csv()
            
            logger.info(f"Saved feedback {feedback.feedback_id} for document {feedback.document_id}")
            return True
        except Exception as e:
            logger.error(f"Error saving feedback: {e}")
            return False
    
    def save_batch_feedback(self, feedbacks: List[Feedback]) -> int:
        """
        Save multiple feedbacks to storage.
        
        Args:
            feedbacks: List of Feedback objects to save
            
        Returns:
            Number of feedbacks saved successfully
        """
        saved_count = 0
        for feedback in feedbacks:
            if self.save_feedback(feedback):
                saved_count += 1
        return saved_count
    
    def load_all_feedback(self) -> List[Feedback]:
        """
        Load all feedback from storage.
        
        Returns:
            List of Feedback objects
        """
        feedbacks = []
        
        if self.feedback_file.exists():
            try:
                with open(self.feedback_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                data = json.loads(line)
                                feedbacks.append(Feedback.from_dict(data))
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                logger.error(f"Error loading feedback: {e}")
        
        return feedbacks
    
    def _update_csv(self) -> None:
        """Update the CSV file with all feedback data."""
        try:
            feedbacks = self.load_all_feedback()
            if not feedbacks:
                return
            
            # Create DataFrame
            data = [f.to_dict() for f in feedbacks]
            df = pd.DataFrame(data)
            
            # Save to CSV
            df.to_csv(self.feedback_csv, index=False, encoding='utf-8')
            logger.debug(f"Updated CSV with {len(feedbacks)} feedbacks")
        except Exception as e:
            logger.error(f"Error updating CSV: {e}")
    
    def get_feedback_by_document(self, document_id: str) -> List[Feedback]:
        """
        Get all feedback for a specific document.
        
        Args:
            document_id: ID of the document
            
        Returns:
            List of Feedback objects for the document
        """
        all_feedback = self.load_all_feedback()
        return [f for f in all_feedback if f.document_id == document_id]
    
    def get_feedback_by_category(self, category: str) -> List[Feedback]:
        """
        Get all feedback where the corrected category matches.
        
        Args:
            category: Category to filter by
            
        Returns:
            List of Feedback objects
        """
        all_feedback = self.load_all_feedback()
        return [f for f in all_feedback if f.corrected_category == category]
    
    def get_feedback_count(self) -> int:
        """Get the total number of feedbacks stored."""
        return len(self.load_all_feedback())
    
    def clear_feedback(self) -> None:
        """Clear all feedback from storage."""
        try:
            if self.feedback_file.exists():
                self.feedback_file.unlink()
            if self.feedback_csv.exists():
                self.feedback_csv.unlink()
            logger.info("Cleared all feedback")
        except Exception as e:
            logger.error(f"Error clearing feedback: {e}")


class ActiveLearningManager:
    """
    Manager for active learning workflow.
    
    This class coordinates:
    - Collecting feedback
    - Retraining models
    - Updating predictions
    """
    
    def __init__(self, feedback_store: Optional[FeedbackStore] = None):
        """
        Initialize the active learning manager.
        
        Args:
            feedback_store: FeedbackStore instance (created if None)
        """
        self.feedback_store = feedback_store or FeedbackStore()
        self.model_path = None
        self.vectorizer_path = None
        
        # Set model paths from config
        config = get_config()
        model_dir = config.get_path("MODEL_DIR")
        self.model_path = model_dir / "random_forest_model.joblib"
        self.vectorizer_path = model_dir / "tfidf_vectorizer.joblib"
    
    def submit_feedback(
        self,
        document_id: str,
        original_category: str,
        corrected_category: str,
        text: str,
        oggetto: str = "",
        confidence: Optional[float] = None,
        user_id: Optional[str] = None
    ) -> Feedback:
        """
        Submit user feedback for a document.
        
        Args:
            document_id: ID of the document
            original_category: Original (incorrect) category
            corrected_category: Corrected category from user
            text: Document text
            oggetto: Document oggetto/subject
            confidence: Original confidence score
            user_id: ID of the user providing feedback
            
        Returns:
            The saved Feedback object
        """
        feedback = Feedback(
            document_id=document_id,
            original_category=original_category,
            corrected_category=corrected_category,
            text=text,
            oggetto=oggetto,
            confidence=confidence,
            user_id=user_id
        )
        
        self.feedback_store.save_feedback(feedback)
        return feedback
    
    def get_training_data_from_feedback(self) -> Tuple[pd.DataFrame, pd.Series]:
        """
        Extract training data from collected feedback.
        
        Returns:
            Tuple of (X, y) where X is features and y is labels
        """
        feedbacks = self.feedback_store.load_all_feedback()
        
        if not feedbacks:
            logger.warning("No feedback available for training")
            return pd.DataFrame(), pd.Series(dtype=str)
        
        # Create DataFrame from feedback
        data = []
        for feedback in feedbacks:
            # Combine text and oggetto
            full_text = f"{feedback.oggetto} {feedback.text}".strip()
            data.append({
                "text": full_text,
                "category": feedback.corrected_category
            })
        
        df = pd.DataFrame(data)
        
        # Check if we have enough data
        if len(df) < 10:
            logger.warning(f"Not enough feedback data for training (only {len(df)} samples)")
            return pd.DataFrame(), pd.Series(dtype=str)
        
        return df["text"], df["category"]
    
    def retrain_model(self, min_samples: int = 50) -> bool:
        """
        Retrain the ML model with feedback data.
        
        Args:
            min_samples: Minimum number of feedback samples required for retraining
            
        Returns:
            True if model was retrained successfully, False otherwise
        """
        try:
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.ensemble import RandomForestClassifier
            import joblib
            
            # Get training data from feedback
            X_text, y = self.get_training_data_from_feedback()
            
            if len(X_text) < min_samples:
                logger.info(f"Not enough feedback samples ({len(X_text)}) for retraining (min: {min_samples})")
                return False
            
            # Vectorize text
            vectorizer = TfidfVectorizer(
                max_features=10000,
                stop_words='italian',
                ngram_range=(1, 2)
            )
            X = vectorizer.fit_transform(X_text)
            
            # Train model
            model = RandomForestClassifier(
                n_estimators=100,
                random_state=42,
                n_jobs=-1,
                class_weight='balanced'
            )
            model.fit(X, y)
            
            # Save model and vectorizer
            if self.model_path:
                self.model_path.parent.mkdir(parents=True, exist_ok=True)
                joblib.dump(model, self.model_path)
                logger.info(f"Saved retrained model to: {self.model_path}")
            
            if self.vectorizer_path:
                self.vectorizer_path.parent.mkdir(parents=True, exist_ok=True)
                joblib.dump(vectorizer, self.vectorizer_path)
                logger.info(f"Saved vectorizer to: {self.vectorizer_path}")
            
            logger.info(f"Model retrained with {len(X_text)} feedback samples")
            return True
            
        except ImportError as e:
            logger.error(f"Required packages not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Error retraining model: {e}")
            return False
    
    def enhance_existing_model(self) -> bool:
        """
        Enhance the existing model with feedback data.
        
        This method:
        1. Loads the existing model
        2. Gets feedback data
        3. Combines with original training data (if available)
        4. Retrains the model
        
        Returns:
            True if model was enhanced successfully, False otherwise
        """
        try:
            import joblib
            from sklearn.feature_extraction.text import TfidfVectorizer
            from sklearn.ensemble import RandomForestClassifier
            
            # Try to load existing model
            if self.model_path and self.model_path.exists():
                model = joblib.load(self.model_path)
                logger.info("Loaded existing model")
            else:
                logger.warning("No existing model found, creating new one")
                model = None
            
            # Get feedback data
            X_text, y = self.get_training_data_from_feedback()
            
            if len(X_text) < 10:
                logger.info("Not enough feedback data for enhancement")
                return False
            
            # Vectorize text
            vectorizer = TfidfVectorizer(
                max_features=10000,
                stop_words='italian',
                ngram_range=(1, 2)
            )
            X_new = vectorizer.fit_transform(X_text)
            
            # If we have an existing model, try to use its vectorizer
            if model and self.vectorizer_path and self.vectorizer_path.exists():
                try:
                    existing_vectorizer = joblib.load(self.vectorizer_path)
                    # Use existing vectorizer if compatible
                    X_new = existing_vectorizer.transform(X_text)
                    vectorizer = existing_vectorizer
                    logger.info("Using existing vectorizer")
                except Exception:
                    logger.warning("Could not use existing vectorizer, using new one")
            
            # If no existing model, create new one
            if model is None:
                model = RandomForestClassifier(
                    n_estimators=100,
                    random_state=42,
                    n_jobs=-1,
                    class_weight='balanced'
                )
            
            # Retrain model with new data
            model.fit(X_new, y)
            
            # Save updated model and vectorizer
            if self.model_path:
                self.model_path.parent.mkdir(parents=True, exist_ok=True)
                joblib.dump(model, self.model_path)
            
            if self.vectorizer_path:
                self.vectorizer_path.parent.mkdir(parents=True, exist_ok=True)
                joblib.dump(vectorizer, self.vectorizer_path)
            
            logger.info(f"Model enhanced with {len(X_text)} feedback samples")
            return True
            
        except ImportError as e:
            logger.error(f"Required packages not available: {e}")
            return False
        except Exception as e:
            logger.error(f"Error enhancing model: {e}")
            return False
    
    def get_feedback_stats(self) -> Dict[str, Any]:
        """
        Get statistics about collected feedback.
        
        Returns:
            Dictionary with feedback statistics
        """
        feedbacks = self.feedback_store.load_all_feedback()
        
        if not feedbacks:
            return {
                "total_feedback": 0,
                "categories": {},
                "users": 0,
                "documents": 0
            }
        
        # Count by category
        category_counts = {}
        for feedback in feedbacks:
            cat = feedback.corrected_category
            category_counts[cat] = category_counts.get(cat, 0) + 1
        
        # Count unique users and documents
        unique_users = len(set(f.user_id for f in feedbacks if f.user_id))
        unique_docs = len(set(f.document_id for f in feedbacks))
        
        return {
            "total_feedback": len(feedbacks),
            "categories": category_counts,
            "users": unique_users,
            "documents": unique_docs,
            "latest_feedback": max(f.timestamp for f in feedbacks).isoformat() if feedbacks else None
        }


# Global instance for easy access
_feedback_manager: Optional[ActiveLearningManager] = None


def get_feedback_manager() -> ActiveLearningManager:
    """
    Get the global feedback manager instance.
    
    Returns:
        ActiveLearningManager instance
    """
    global _feedback_manager
    if _feedback_manager is None:
        _feedback_manager = ActiveLearningManager()
    return _feedback_manager


def submit_classification_feedback(
    document_id: str,
    original_category: str,
    corrected_category: str,
    text: str,
    oggetto: str = "",
    confidence: Optional[float] = None,
    user_id: Optional[str] = None
) -> Feedback:
    """
    Convenience function to submit classification feedback.
    
    Args:
        document_id: ID of the document
        original_category: Original (incorrect) category
        corrected_category: Corrected category from user
        text: Document text
        oggetto: Document oggetto/subject
        confidence: Original confidence score
        user_id: ID of the user providing feedback
        
    Returns:
        The saved Feedback object
    """
    manager = get_feedback_manager()
    return manager.submit_feedback(
        document_id=document_id,
        original_category=original_category,
        corrected_category=corrected_category,
        text=text,
        oggetto=oggetto,
        confidence=confidence,
        user_id=user_id
    )
