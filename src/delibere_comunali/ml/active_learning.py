"""
Active Learning Module for ML Model Improvement.

This module implements an active learning system that:
1. Identifies uncertain predictions (low confidence)
2. Requests user feedback for these predictions
3. Uses feedback to improve the model
4. Tracks model performance over time

Key Features:
- Uncertainty sampling for active learning
- Feedback integration with existing pipeline
- Model versioning and performance tracking
- Automatic retraining scheduling
"""

import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from datetime import datetime, timedelta
import logging
import pandas as pd
import numpy as np

from ..utils.config import get_config
from ..utils.logger import get_logger
from .feedback_handler import Feedback, FeedbackStore, ActiveLearningManager, get_feedback_manager

logger = get_logger(__name__)


class UncertaintySampler:
    """
    Implements uncertainty sampling strategies for active learning.
    
    Strategies:
    - Least Confident: Select samples with lowest prediction confidence
    - Margin Sampling: Select samples with smallest margin between top classes
    - Entropy Sampling: Select samples with highest prediction entropy
    """
    
    def __init__(self, threshold: float = 0.7):
        """
        Initialize the uncertainty sampler.
        
        Args:
            threshold: Confidence threshold below which to request feedback
        """
        self.threshold = threshold
    
    def get_least_confident(
        self,
        predictions: np.ndarray,
        probabilities: np.ndarray,
        n_samples: int = 10
    ) -> List[int]:
        """
        Get indices of least confident predictions.
        
        Args:
            predictions: Array of predicted classes
            probabilities: Array of prediction probabilities
            n_samples: Number of samples to return
            
        Returns:
            List of indices of least confident predictions
        """
        if len(predictions) == 0:
            return []
        
        # Get confidence (max probability for each sample)
        confidences = np.max(probabilities, axis=1)
        
        # Get indices sorted by confidence (ascending)
        sorted_indices = np.argsort(confidences)
        
        # Return indices with lowest confidence
        return sorted_indices[:min(n_samples, len(sorted_indices))].tolist()
    
    def get_margin_samples(
        self,
        probabilities: np.ndarray,
        n_samples: int = 10
    ) -> List[int]:
        """
        Get indices of samples with smallest prediction margin.
        
        Margin = difference between probabilities of top 2 classes.
        
        Args:
            probabilities: Array of prediction probabilities
            n_samples: Number of samples to return
            
        Returns:
            List of indices with smallest margin
        """
        if len(probabilities) == 0:
            return []
        
        # Sort probabilities for each sample
        sorted_probs = np.sort(probabilities, axis=1)[:, ::-1]
        
        # Calculate margin (difference between top 2)
        margins = sorted_probs[:, 0] - sorted_probs[:, 1]
        
        # Get indices sorted by margin (ascending)
        sorted_indices = np.argsort(margins)
        
        return sorted_indices[:min(n_samples, len(sorted_indices))].tolist()
    
    def get_entropy_samples(
        self,
        probabilities: np.ndarray,
        n_samples: int = 10
    ) -> List[int]:
        """
        Get indices of samples with highest prediction entropy.
        
        Args:
            probabilities: Array of prediction probabilities
            n_samples: Number of samples to return
            
        Returns:
            List of indices with highest entropy
        """
        if len(probabilities) == 0:
            return []
        
        # Calculate entropy: -sum(p * log(p))
        # Add small epsilon to avoid log(0)
        epsilon = 1e-10
        safe_probs = np.clip(probabilities, epsilon, 1 - epsilon)
        entropy = -np.sum(safe_probs * np.log(safe_probs), axis=1)
        
        # Get indices sorted by entropy (descending)
        sorted_indices = np.argsort(entropy)[::-1]
        
        return sorted_indices[:min(n_samples, len(sorted_indices))].tolist()
    
    def should_request_feedback(self, confidence: float) -> bool:
        """
        Determine if feedback should be requested based on confidence.
        
        Args:
            confidence: Prediction confidence score
            
        Returns:
            True if feedback should be requested
        """
        return confidence < self.threshold


class ActiveLearningPipeline:
    """
    Pipeline for integrating active learning with document processing.
    
    This class:
    1. Processes documents through the normal pipeline
    2. Identifies uncertain predictions
    3. Requests feedback for uncertain predictions
    4. Uses feedback to improve future predictions
    """
    
    def __init__(
        self,
        feedback_manager: Optional[ActiveLearningManager] = None,
        uncertainty_threshold: float = 0.7
    ):
        """
        Initialize the active learning pipeline.
        
        Args:
            feedback_manager: FeedbackManager instance
            uncertainty_threshold: Confidence threshold for requesting feedback
        """
        self.feedback_manager = feedback_manager or get_feedback_manager()
        self.sampler = UncertaintySampler(threshold=uncertainty_threshold)
        self.min_feedback_for_retrain = 50
    
    def process_with_active_learning(
        self,
        df: pd.DataFrame,
        model,
        vectorizer=None,
        text_column: str = "text",
        category_column: str = "category",
        confidence_column: str = "classification_confidence_score"
    ) -> Tuple[pd.DataFrame, List[Feedback]]:
        """
        Process documents with active learning.
        
        Args:
            df: DataFrame with documents to process
            model: Trained ML model
            vectorizer: Text vectorizer
            text_column: Name of column with document text
            category_column: Name of column with categories
            confidence_column: Name of column with confidence scores
            
        Returns:
            Tuple of (updated DataFrame, list of feedbacks that need user input)
        """
        # Identify documents that need feedback
        feedback_requests = []
        
        # Filter documents with low confidence
        low_conf_mask = df[confidence_column] < self.sampler.threshold
        low_conf_docs = df[low_conf_mask]
        
        if len(low_conf_docs) > 0:
            logger.info(f"Found {len(low_conf_docs)} documents with low confidence")
            
            # For each low confidence document, create a feedback request
            for idx, row in low_conf_docs.iterrows():
                feedback = Feedback(
                    document_id=str(row.get("pdf_name", row.get("id", idx))),
                    original_category=row.get(category_column, ""),
                    corrected_category=None,  # To be filled by user
                    text=row.get(text_column, ""),
                    oggetto=row.get("oggetto", ""),
                    confidence=row.get(confidence_column),
                    user_id=None
                )
                feedback_requests.append(feedback)
        
        # Check if we have enough feedback to retrain
        if self.feedback_manager.feedback_store.get_feedback_count() >= self.min_feedback_for_retrain:
            logger.info("Enough feedback collected, retraining model...")
            self.feedback_manager.enhance_existing_model()
        
        return df, feedback_requests
    
    def apply_feedback_and_retrain(
        self,
        feedbacks: List[Feedback]
    ) -> bool:
        """
        Apply a list of feedbacks and retrain the model.
        
        Args:
            feedbacks: List of Feedback objects with user corrections
            
        Returns:
            True if model was retrained successfully
        """
        # Save all feedbacks
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
        
        # Retrain model if we have enough feedback
        if self.feedback_manager.feedback_store.get_feedback_count() >= self.min_feedback_for_retrain:
            return self.feedback_manager.enhance_existing_model()
        
        return False


class ModelPerformanceTracker:
    """
    Track model performance over time.
    
    This class:
    - Logs model performance metrics
    - Tracks accuracy over time
    - Identifies performance degradation
    - Suggests when to retrain
    """
    
    def __init__(self, storage_path: Optional[Union[str, Path]] = None):
        """
        Initialize the performance tracker.
        
        Args:
            storage_path: Path to store performance data
        """
        config = get_config()
        
        if storage_path is None:
            data_dir = config.get_path("DATA_DIR")
            self.storage_path = data_dir / "model_performance"
        else:
            self.storage_path = Path(storage_path)
        
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self.performance_file = self.storage_path / "performance.jsonl"
    
    def log_performance(
        self,
        model_version: str,
        accuracy: float,
        precision: float,
        recall: float,
        f1_score: float,
        timestamp: Optional[datetime] = None,
        dataset_size: Optional[int] = None
    ) -> None:
        """
        Log model performance metrics.
        
        Args:
            model_version: Version identifier for the model
            accuracy: Accuracy score
            precision: Precision score
            recall: Recall score
            f1_score: F1 score
            timestamp: When the evaluation was performed
            dataset_size: Size of the evaluation dataset
        """
        record = {
            "model_version": model_version,
            "timestamp": (timestamp or datetime.now()).isoformat(),
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1_score": f1_score,
            "dataset_size": dataset_size
        }
        
        try:
            with open(self.performance_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record, ensure_ascii=False) + '\n')
            logger.info(f"Logged performance for model {model_version}: accuracy={accuracy:.3f}, f1={f1_score:.3f}")
        except Exception as e:
            logger.error(f"Error logging performance: {e}")
    
    def get_performance_history(self) -> pd.DataFrame:
        """
        Get the history of model performance.
        
        Returns:
            DataFrame with performance history
        """
        records = []
        
        if self.performance_file.exists():
            try:
                with open(self.performance_file, 'r', encoding='utf-8') as f:
                    for line in f:
                        line = line.strip()
                        if line:
                            try:
                                records.append(json.loads(line))
                            except json.JSONDecodeError:
                                continue
            except Exception as e:
                logger.error(f"Error loading performance history: {e}")
        
        return pd.DataFrame(records)
    
    def get_latest_performance(self) -> Optional[Dict[str, Any]]:
        """
        Get the latest performance record.
        
        Returns:
            Dictionary with latest performance metrics, or None if no records
        """
        df = self.get_performance_history()
        if df.empty:
            return None
        
        return df.iloc[-1].to_dict()
    
    def check_degradation(self, threshold: float = 0.05) -> bool:
        """
        Check if model performance has degraded significantly.
        
        Args:
            threshold: Minimum degradation to trigger alert
            
        Returns:
            True if performance has degraded significantly
        """
        df = self.get_performance_history()
        
        if len(df) < 2:
            return False
        
        # Get latest and previous performance
        latest = df.iloc[-1]
        previous = df.iloc[-2]
        
        # Check if accuracy has dropped significantly
        accuracy_drop = previous['accuracy'] - latest['accuracy']
        
        return accuracy_drop > threshold


# Convenience functions
def should_request_feedback(confidence: float, threshold: float = 0.7) -> bool:
    """
    Determine if feedback should be requested for a prediction.
    
    Args:
        confidence: Prediction confidence score
        threshold: Confidence threshold
        
    Returns:
        True if feedback should be requested
    """
    sampler = UncertaintySampler(threshold=threshold)
    return sampler.should_request_feedback(confidence)


def get_uncertain_samples(
    predictions: np.ndarray,
    probabilities: np.ndarray,
    method: str = "least_confident",
    n_samples: int = 10
) -> List[int]:
    """
    Get indices of uncertain samples for feedback.
    
    Args:
        predictions: Array of predicted classes
        probabilities: Array of prediction probabilities
        method: Sampling method ("least_confident", "margin", "entropy")
        n_samples: Number of samples to return
        
    Returns:
        List of indices of uncertain samples
    """
    sampler = UncertaintySampler()
    
    if method == "least_confident":
        return sampler.get_least_confident(predictions, probabilities, n_samples)
    elif method == "margin":
        return sampler.get_margin_samples(probabilities, n_samples)
    elif method == "entropy":
        return sampler.get_entropy_samples(probabilities, n_samples)
    else:
        return sampler.get_least_confident(predictions, probabilities, n_samples)
