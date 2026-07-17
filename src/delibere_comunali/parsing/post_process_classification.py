"""
Post-processing classification module for OCR-enhanced documents.
This module applies advanced classification to documents processed with OCR,
ensuring quality and consistency in the parsed document output.
"""

import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
import logging

from ..models.parsed_document import ParsedDocument
from .document_classifier import DocumentClassifier
from ..utils.logger import get_logger
from ..utils.config import get_config

logger = get_logger(__name__)


class OCRPostProcessor:
    """
    Post-processing handler for documents that went through OCR processing.
    Applies enhanced classification and validation for OCR-generated content.
    """
    
    def __init__(self):
        self.config = get_config()
        self.classifier = DocumentClassifier()
        self.min_confidence_threshold = self.config.parsing.min_classification_confidence or 0.6
        
    def enhance_classifications(self, parsed_documents: List[ParsedDocument]) -> List[ParsedDocument]:
        """
        Enhance document classifications for OCR-processed documents.
        
        Args:
            parsed_documents: List of ParsedDocument objects to enhance
            
        Returns:
            Enhanced list of ParsedDocument objects with improved classifications
        """
        enhanced_docs = []
        
        for doc in parsed_documents:
            # Check if document was processed via OCR
            was_ocr_processed = 'ocr' in (doc.source or '').lower() if doc.source else False
            
            if was_ocr_processed:
                # Apply enhanced classification for OCR-processed documents
                enhanced_doc = self._enhance_single_document(doc)
            else:
                # For non-OCR documents, just validate existing classification
                enhanced_doc = self._validate_single_document(doc)
            
            enhanced_docs.append(enhanced_doc)
        
        return enhanced_docs
    
    def _enhance_single_document(self, doc: ParsedDocument) -> ParsedDocument:
        """
        Apply enhanced classification and cleaning for a single OCR-processed document.
        
        Args:
            doc: Single ParsedDocument to enhance
            
        Returns:
            Enhanced ParsedDocument object
        """
        # Create a copy to avoid modifying original
        enhanced_doc = ParsedDocument()
        for attr in dir(doc):
            if not attr.startswith('_') and hasattr(doc, attr):
                setattr(enhanced_doc, attr, getattr(doc, attr))
        
        # Clean OCR artifacts from text
        if enhanced_doc._text:
            enhanced_doc._text = self._clean_ocr_artifacts(enhanced_doc._text)
        
        # Re-classify document with enhanced logic for OCR content
        if enhanced_doc._text:
            classification_result = self.classifier.classify_document(enhanced_doc._text)
            
            # Only update classification if confidence is high enough
            if classification_result and classification_result.get('confidence', 0) >= self.min_confidence_threshold:
                enhanced_doc.doc_type = classification_result.get('doc_type', enhanced_doc.doc_type)
                enhanced_doc.category = classification_result.get('category', enhanced_doc.category)
        
        # Log if confidence is low (indicating potential OCR quality issue)
        if classification_result and classification_result.get('confidence', 0) < self.min_confidence_threshold:
            logger.warning(
                f"Low confidence classification for OCR-processed document {enhanced_doc.pdf_name}: "
                f"{classification_result.get('confidence', 0):.2f}. May need manual review."
            )
        
        return enhanced_doc
    
    def _validate_single_document(self, doc: ParsedDocument) -> ParsedDocument:
        """
        Validate and potentially enhance a non-OCR document.
        
        Args:
            doc: Single ParsedDocument to validate
            
        Returns:
            Potentially enhanced ParsedDocument object
        """
        # Create a copy to avoid modifying original
        validated_doc = ParsedDocument()
        for attr in dir(doc):
            if not attr.startswith('_') and hasattr(doc, attr):
                setattr(validated_doc, attr, getattr(doc, attr))
        
        # For non-OCR documents, perform validation only
        # Check if classification is missing or low confidence and attempt to improve
        if (not validated_doc.doc_type or not validated_doc.category) and validated_doc._text:
            classification_result = self.classifier.classify_document(validated_doc._text)
            
            if classification_result and classification_result.get('confidence', 0) >= self.min_confidence_threshold:
                if not validated_doc.doc_type:
                    validated_doc.doc_type = classification_result.get('doc_type', validated_doc.doc_type)
                if not validated_doc.category:
                    validated_doc.category = classification_result.get('category', validated_doc.category)
        
        return validated_doc
    
    def _clean_ocr_artifacts(self, text: str) -> str:
        """
        Clean common OCR artifacts from text.
        
        Args:
            text: Raw OCR text to clean
            
        Returns:
            Cleaned text with OCR artifacts removed
        """
        if not text:
            return text
        
        # Remove common OCR artifacts
        cleaned_text = text
        
        # Replace common OCR misrecognitions
        replacements = {
            # Numbers commonly misrecognized as letters
            r'\b0\b': 'O',  # standalone 0 to O
            r'\b1\b': 'I',  # standalone 1 to I
            r'\b5\b': 'S',  # standalone 5 to S
            # Common character swaps
            r'I(?=[A-Z])': '1',  # Capital I followed by capital letter to 1
            r'O(?=\d)': '0',    # O followed by digit to 0
        }
        
        for pattern, replacement in replacements.items():
            import re
            cleaned_text = re.sub(pattern, replacement, cleaned_text)
        
        # Normalize whitespace
        import re
        cleaned_text = re.sub(r'\s+', ' ', cleaned_text).strip()
        
        return cleaned_text
    
    def generate_quality_report(self, parsed_documents: List[ParsedDocument]) -> Dict:
        """
        Generate a quality report for OCR-processed documents.
        
        Args:
            parsed_documents: List of ParsedDocument objects to analyze
            
        Returns:
            Quality report dictionary
        """
        total_docs = len(parsed_documents)
        ocr_processed = sum(1 for doc in parsed_documents if 
                           doc.source and 'ocr' in doc.source.lower())
        low_quality_ocr = 0  # Placeholder - would need confidence scores
        
        report = {
            'total_documents': total_docs,
            'ocr_processed_count': ocr_processed,
            'ocr_percentage': (ocr_processed / total_docs * 100) if total_docs > 0 else 0,
            'low_quality_ocr_count': low_quality_ocr,
            'timestamp': pd.Timestamp.now().isoformat()
        }
        
        return report


def apply_post_processing_classification(input_csv_path: Path, output_csv_path: Path) -> bool:
    """
    Apply post-processing classification to a CSV of parsed documents.
    
    Args:
        input_csv_path: Path to input CSV with parsed documents
        output_csv_path: Path to output CSV with enhanced classifications
        
    Returns:
        True if successful, False otherwise
    """
    try:
        logger.info(f"Starting post-processing classification for: {input_csv_path}")
        
        # Read the input CSV
        df = pd.read_csv(input_csv_path)
        logger.info(f"Loaded {len(df)} documents for post-processing")
        
        # Initialize the post-processor
        post_processor = OCRPostProcessor()
        
        # Convert DataFrame to ParsedDocument objects
        parsed_docs = []
        for _, row in df.iterrows():
            doc = ParsedDocument()
            for col in df.columns:
                if hasattr(doc, col) and pd.notna(row[col]):
                    setattr(doc, col, row[col])
            parsed_docs.append(doc)
        
        # Apply enhancements
        enhanced_docs = post_processor.enhance_classifications(parsed_docs)
        
        # Convert back to DataFrame
        enhanced_data = []
        for doc in enhanced_docs:
            doc_dict = {}
            for attr in dir(doc):
                if not attr.startswith('_') and hasattr(ParsedDocument, attr):
                    doc_dict[attr] = getattr(doc, attr)
            enhanced_data.append(doc_dict)
        
        enhanced_df = pd.DataFrame(enhanced_data)
        
        # Save the enhanced DataFrame
        enhanced_df.to_csv(output_csv_path, index=False)
        logger.info(f"Saved enhanced classifications to: {output_csv_path}")
        
        # Generate and save quality report
        quality_report = post_processor.generate_quality_report(enhanced_docs)
        report_path = output_csv_path.with_name(output_csv_path.stem + '_quality_report.json')
        with open(report_path, 'w', encoding='utf-8') as f:
            import json
            json.dump(quality_report, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Quality report saved to: {report_path}")
        
        return True
        
    except Exception as e:
        logger.error(f"Error in post-processing classification: {e}")
        return False


def main():
    """Command line interface for the OCR post-processing module."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Post-process OCR-classified documents")
    parser.add_argument("--input", required=True, help="Input CSV file path")
    parser.add_argument("--output", required=True, help="Output CSV file path")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    output_path = Path(args.output)
    
    if not input_path.exists():
        print(f"Error: Input file does not exist: {input_path}")
        return 1
    
    success = apply_post_processing_classification(input_path, output_path)
    
    if success:
        print(f"Successfully processed {input_path} -> {output_path}")
        return 0
    else:
        print(f"Failed to process {input_path}")
        return 1


if __name__ == "__main__":
    exit(main())