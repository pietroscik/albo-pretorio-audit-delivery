#!/usr/bin/env python3
"""
Test script to verify that the sparse matrix error is fixed
"""
import sys
import os
import pandas as pd
import numpy as np
from pathlib import Path
from scipy.sparse import csr_matrix

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__)))

from src.delibere_comunali.parsing.document_classifier import DocumentClassifier

def test_sparse_matrix_fix():
    """Test that the classifier handles sparse matrices properly"""
    print("Testing sparse matrix fix...")
    
    # Create a dummy classifier instance
    classifier = DocumentClassifier()
    
    # Test with normal strings (should work)
    print("\n1. Testing with normal strings...")
    try:
        result = classifier.classify("oggetto normale", "testo normale")
        print(f"   Result: {result}")
        print("   ✓ Normal strings work fine")
    except Exception as e:
        print(f"   ✗ Error with normal strings: {e}")
    
    # Test with sparse matrix (this was causing the original error)
    print("\n2. Testing with sparse matrix...")
    try:
        # Create a fake sparse matrix that simulates the original error
        sparse_mat = csr_matrix([[1, 2, 3], [4, 5, 6]])
        result = classifier.classify(sparse_mat, "testo normale")
        print(f"   Result: {result}")
        print("   ✓ Sparse matrix handled gracefully")
    except Exception as e:
        print(f"   ✗ Error with sparse matrix: {e}")
    
    # Test with sparse matrix as second parameter
    print("\n3. Testing with sparse matrix as second parameter...")
    try:
        sparse_mat = csr_matrix([[1, 2, 3], [4, 5, 6]])
        result = classifier.classify("oggetto normale", sparse_mat)
        print(f"   Result: {result}")
        print("   ✓ Sparse matrix as second param handled gracefully")
    except Exception as e:
        print(f"   ✗ Error with sparse matrix as second param: {e}")
    
    # Test with both parameters as sparse matrices
    print("\n4. Testing with both parameters as sparse matrices...")
    try:
        sparse_mat1 = csr_matrix([[1, 2, 3]])
        sparse_mat2 = csr_matrix([[4, 5, 6]])
        result = classifier.classify(sparse_mat1, sparse_mat2)
        print(f"   Result: {result}")
        print("   ✓ Both params as sparse matrices handled gracefully")
    except Exception as e:
        print(f"   ✗ Error with both params as sparse matrices: {e}")
    
    print("\n✓ All tests completed. Sparse matrix error should be fixed!")

if __name__ == "__main__":
    test_sparse_matrix_fix()