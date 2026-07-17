"""
Semantic RAG Engine for the Albo Pretorio Audit System.

This module provides advanced semantic search and retrieval capabilities
for processed municipal documents, enabling interactive querying of
the knowledge base built from public administration documents.
"""

import os
import sys
from pathlib import Path
from typing import List, Dict, Any, Optional, Union
import logging
import json
import pickle
from datetime import datetime

import faiss
import numpy as np
import pandas as pd
from sentence_transformers import SentenceTransformer
from transformers import AutoTokenizer, AutoModel
import torch

from ..utils.config import get_config
from ..utils.logger import get_logger
from ..utils.privacy_guard import get_privacy_guard
from ..models.parsed_document import ParsedDocument

logger = get_logger(__name__)


class SemanticRAGEngine:
    """
    Advanced RAG engine for semantic search and generation over processed municipal documents.
    Implements privacy-by-design principles and ensures GDPR compliance during semantic operations.
    """
    
    def __init__(self, ente: str, model_name: str = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"):
        self.ente = ente
        self.config = get_config()
        self.privacy_guard = get_privacy_guard()
        
        # Initialize embedding model
        try:
            self.embedding_model = SentenceTransformer(model_name)
        except Exception as e:
            logger.error(f"Failed to initialize embedding model: {e}")
            # Fallback to a simpler approach
            self.embedding_model = None
        
        # Setup paths
        self.data_path = Path(self.config.paths.data_dir) / ente / "albo_download"
        self.faiss_index_path = self.data_path / "faiss_index" / "index.bin"
        self.documents_path = self.data_path / "documenti_corpus.jsonl"
        self.metadata_path = self.data_path / "documenti_metadata.json"
        
        # Initialize FAISS index
        self.index = None
        self.documents = []
        self.metadata = []
        
        # Load index and documents if available
        self._load_index()
    
    def _load_index(self):
        """Load FAISS index and associated documents."""
        try:
            if self.faiss_index_path.exists():
                logger.info(f"Loading FAISS index from: {self.faiss_index_path}")
                self.index = faiss.read_index(str(self.faiss_index_path))
                
                # Load documents
                if self.documents_path.exists():
                    with open(self.documents_path, 'r', encoding='utf-8') as f:
                        self.documents = [json.loads(line) for line in f.readlines()]
                
                # Load metadata
                if self.metadata_path.exists():
                    with open(self.metadata_path, 'r', encoding='utf-8') as f:
                        self.metadata = json.load(f)
                
                logger.info(f"Loaded index with {self.index.ntotal} vectors")
            else:
                logger.warning(f"FAISS index not found at: {self.faiss_index_path}")
        except Exception as e:
            logger.error(f"Error loading FAISS index: {e}")
            self.index = None
    
    def _create_embeddings(self, texts: List[str]) -> np.ndarray:
        """Create embeddings for a list of texts."""
        if self.embedding_model is None:
            # Simple fallback using TF-IDF-like approach
            # This is a basic implementation for demonstration purposes
            from sklearn.feature_extraction.text import TfidfVectorizer
            vectorizer = TfidfVectorizer(max_features=512)
            embeddings = vectorizer.fit_transform(texts).toarray()
            return np.array(embeddings, dtype=np.float32)
        
        # Use the sentence transformer model
        embeddings = self.embedding_model.encode(texts)
        return embeddings.astype(np.float32)
    
    def _sanitize_query(self, query: str) -> str:
        """Sanitize query to remove potentially sensitive information."""
        # Apply privacy guard pseudonymization to the query
        sanitized_query = self.privacy_guard.pseudonymize_sensitive_data(query)
        return sanitized_query
    
    def search(self, query: str, k: int = 6, filter_by_category: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Perform semantic search on the document corpus.
        
        Args:
            query: Search query
            k: Number of results to return
            filter_by_category: Optional category filter
            
        Returns:
            List of dictionaries containing search results
        """
        try:
            # Sanitize the query
            sanitized_query = self._sanitize_query(query)
            
            if self.index is None or len(self.documents) == 0:
                logger.warning("Index not loaded, returning empty results")
                return []
            
            # Create embedding for the query
            query_embedding = self._create_embeddings([sanitized_query])
            
            # Perform similarity search
            scores, indices = self.index.search(query_embedding, k)
            
            results = []
            for score, idx in zip(scores[0], indices[0]):
                if idx < len(self.documents) and idx >= 0:
                    doc = self.documents[idx]
                    
                    # Apply category filter if specified
                    if filter_by_category and doc.get('categoria') != filter_by_category:
                        continue
                    
                    result = {
                        'score': float(score),
                        'document': doc,
                        'metadata': self.metadata[idx] if idx < len(self.metadata) else {},
                        'text_snippet': doc.get('testo', '')[:500]  # First 500 chars
                    }
                    results.append(result)
            
            # Sort by score (descending)
            results.sort(key=lambda x: x['score'], reverse=True)
            
            # Return top k results after filtering
            return results[:k]
            
        except Exception as e:
            logger.error(f"Error in semantic search: {e}")
            return []
    
    def generate_answer(self, query: str, context_docs: List[Dict[str, Any]], 
                      model_type: str = "local") -> str:
        """
        Generate an answer based on the query and context documents.
        
        Args:
            query: Original query
            context_docs: Context documents from search
            model_type: Type of model to use ("local", "gemini", "ollama")
            
        Returns:
            Generated answer
        """
        try:
            # Combine context from documents
            context_text = "\n\n".join([
                doc['document'].get('testo', '')[:1000]  # Limit to 1000 chars per doc
                for doc in context_docs[:3]  # Use top 3 documents
            ])
            
            # Prepare prompt
            prompt = f"""
            Contesto: {context_text}
            
            Domanda: {query}
            
            Rispondi in modo preciso e conciso basandoti esclusivamente sul contesto fornito. 
            Se la risposta non è presente nel contesto, rispondi "Non riesco a trovare la risposta nel contesto fornito."
            
            Risposta:
            """
            
            if model_type == "local":
                # Simple fallback using rule-based approach
                return self._simple_generate(prompt)
            else:
                # For now, use simple generation - in a real system we'd connect to LLM APIs
                return self._simple_generate(prompt)
                
        except Exception as e:
            logger.error(f"Error in answer generation: {e}")
            return "Errore nella generazione della risposta."
    
    def _simple_generate(self, prompt: str) -> str:
        """Simple answer generation fallback."""
        # This is a basic implementation - in a real system we'd use a proper LLM
        if "Non riesco a trovare la risposta" in prompt:
            return "Non riesco a trovare la risposta nel contesto fornito."
        return "Risposta generata dal sistema RAG. Per domande specifiche, consultare i documenti originali."
    
    def get_document_details(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """
        Retrieve detailed information about a specific document.
        
        Args:
            doc_id: Document identifier
            
        Returns:
            Document details or None if not found
        """
        try:
            # Look for document by ID in our loaded documents
            for i, doc in enumerate(self.documents):
                if doc.get('id') == doc_id or doc.get('documento_id') == doc_id:
                    # Apply privacy measures to the document content
                    doc_copy = doc.copy()
                    if 'testo' in doc_copy:
                        doc_copy['testo'] = self.privacy_guard.pseudonymize_sensitive_data(doc_copy['testo'])
                    
                    return {
                        'document': doc_copy,
                        'metadata': self.metadata[i] if i < len(self.metadata) else {},
                        'vector_index': i
                    }
            
            return None
        except Exception as e:
            logger.error(f"Error retrieving document details: {e}")
            return None
    
    def update_index(self, new_documents: List[Dict[str, Any]]):
        """
        Update the FAISS index with new documents.
        
        Args:
            new_documents: List of new documents to add to the index
        """
        try:
            if not new_documents:
                return
            
            # Extract text from new documents
            new_texts = [doc.get('testo', '') for doc in new_documents if doc.get('testo')]
            
            if not new_texts:
                logger.warning("No text content found in new documents")
                return
            
            # Create embeddings for new documents
            new_embeddings = self._create_embeddings(new_texts)
            
            # Initialize index if it doesn't exist
            if self.index is None:
                dimension = new_embeddings.shape[1]
                self.index = faiss.IndexFlatIP(dimension)  # Inner product for cosine similarity
            
            # Add new embeddings to index
            self.index.add(new_embeddings)
            
            # Add new documents to our collection
            self.documents.extend(new_documents)
            
            # Update metadata accordingly
            # For simplicity, we'll create basic metadata for new docs
            for doc in new_documents:
                self.metadata.append({
                    'added_date': datetime.now().isoformat(),
                    'source': doc.get('fonte', 'unknown'),
                    'processed': True
                })
            
            # Save updated index
            faiss.write_index(self.index, str(self.faiss_index_path))
            
            logger.info(f"Added {len(new_documents)} new documents to index. Total: {self.index.ntotal}")
            
        except Exception as e:
            logger.error(f"Error updating index: {e}")
    
    def get_statistics(self) -> Dict[str, Any]:
        """
        Get statistics about the RAG index and corpus.
        
        Returns:
            Dictionary with statistics
        """
        try:
            stats = {
                'total_documents': len(self.documents),
                'indexed_vectors': self.index.ntotal if self.index else 0,
                'embedding_dimension': self.index.d if self.index else 0,
                'ente': self.ente,
                'last_updated': datetime.now().isoformat()
            }
            
            # Add category distribution if available
            categories = {}
            for doc in self.documents:
                cat = doc.get('categoria', 'unknown')
                categories[cat] = categories.get(cat, 0) + 1
            
            stats['category_distribution'] = categories
            
            return stats
        except Exception as e:
            logger.error(f"Error getting statistics: {e}")
            return {}


def main():
    """Test function for the RAG engine."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Semantic RAG Engine for Albo Pretorio Audit")
    parser.add_argument("--ente", required=True, help="Entity name to process")
    parser.add_argument("--query", required=True, help="Search query")
    parser.add_argument("--k", type=int, default=5, help="Number of results to return")
    
    args = parser.parse_args()
    
    print(f"Initializing RAG engine for entity: {args.ente}")
    rag_engine = SemanticRAGEngine(args.ente)
    
    print(f"Performing search for: '{args.query}'")
    results = rag_engine.search(args.query, k=args.k)
    
    print(f"\nFound {len(results)} results:")
    for i, result in enumerate(results, 1):
        print(f"\n{i}. Score: {result['score']:.3f}")
        print(f"   Text snippet: {result['text_snippet'][:200]}...")
        print(f"   Category: {result['document'].get('categoria', 'N/A')}")
    
    print(f"\nRAG engine statistics:")
    stats = rag_engine.get_statistics()
    for key, value in stats.items():
        print(f"  {key}: {value}")


if __name__ == "__main__":
    main()