# Technical Summary: Albo Pretorio Audit Process and Results

## Overview
This document provides a technical overview of the automated compliance audit conducted on the public notice boards (Albo Pretorio) of three municipalities in the province of Avellino, Italy: Avella, Baiano, and Quadrelle. The audit utilized the `delibere-comunali` toolset, a Python-based system designed for processing and analyzing administrative documents.

## System Architecture

### Core Components
1. **Scraper Module** (`delibere_comunali.scraping.new_albo_scraper`)
   - Automated collection of documents from Albo Pretorio websites
   - Handles pagination and session management
   - Downloads documents and stores metadata

2. **Processing Pipeline** (`delibere_comunali.pipeline`)
   - Text extraction from various document formats (PDF, DOC, etc.)
   - Document classification using ML models
   - Feature engineering for procedural analysis

3. **Procedural Analyzer** (`scripts/procedural_analysis.py`)
   - Identifies document sequences in administrative procedures
   - Evaluates completeness of procedural chains
   - Detects missing documents and violations

4. **Knowledge Graph Builder** (`scripts/build_knowledge_graph.py`)
   - Creates relationship graphs between documents
   - Visualizes connections in administrative procedures
   - Generates GEXF format outputs

5. **ML Model Trainer** (`scripts/train_model.py`)
   - Implements Random Forest classifier for document categorization
   - Uses hyperparameter optimization via RandomizedSearchCV
   - Stores trained models in joblib format

## Data Processing Results

### Avella
- **Documents Collected**: 1,177
- **Output Files Generated**:
  - [allegati_parsed.csv](file:///c%3A/Users/39329/albo-pretorio-audit-delivery/data/avella/albo_download/allegati_parsed.csv): Complete parsed document metadata
  - [atti_audited.csv](file:///c%3A/Users/39329/albo-pretorio-audit-delivery/data/avella/albo_download/atti_audited.csv): Audit results with procedural completeness scores
  - [documenti_features.csv](file:///c%3A/Users/39329/albo-pretorio-audit-delivery/data/avella/albo_download/documenti_features.csv): Feature vectors for ML classification
  - [random_forest_model.joblib](file:///c%3A/Users/39329/albo-pretorio-audit-delivery/data/avella/albo_download/random_forest_model.joblib): Trained classification model
  - [report/](file:///c%3A/Users/39329/albo-pretorio-audit-delivery/data/avella/albo_download/report/) directory with analysis reports

### Baiano
- **Documents Collected**: 640
- **Output Files Generated**:
  - [allegati_parsed.csv](file:///c%3A/Users/39329/albo-pretorio-audit-delivery/data/baiano/albo_download/allegati_parsed.csv): Complete parsed document metadata
  - [atti_audited.csv](file:///c%3A/Users/39329/albo-pretorio-audit-delivery/data/baiano/albo_download/atti_audited.csv): Audit results with procedural completeness scores
  - [documenti_features.csv](file:///c%3A/Users/39329/albo-pretorio-audit-delivery/data/baiano/albo_download/documenti_features.csv): Feature vectors for ML classification
  - [random_forest_model.joblib](file:///c%3A/Users/39329/albo-pretorio-audit-delivery/data/baiano/albo_download/random_forest_model.joblib): Trained classification model
  - [random_forest_model_enhanced.joblib](file:///c%3A/Users/39329/albo-pretorio-audit-delivery/data/baiano/albo_download/random_forest_model_enhanced.joblib): Enhanced model after active learning
  - [feedback_operatore.csv](file:///c%3A/Users/39329/albo-pretorio-audit-delivery/data/baiano/albo_download/feedback_operatore.csv): Human validation feedback for model improvement
  - [report/](file:///c%3A/Users/39329/albo-pretorio-audit-delivery/data/baiano/albo_download/report/) directory with analysis reports

### Quadrelle
- **Documents Collected**: 674
- **Output Files Generated**:
  - [allegati_parsed.csv](file:///c%3A/Users/39329/albo-pretorio-audit-delivery/data/quadrelle/albo_download/allegati_parsed.csv): Complete parsed document metadata
  - [atti_audited.csv](file:///c%3A/Users/39329/albo-pretorio-audit-delivery/data/quadrelle/albo_download/atti_audited.csv): Audit results with procedural completeness scores
  - [documenti_features.csv](file:///c%3A/Users/39329/albo-pretorio-audit-delivery/data/quadrelle/albo_download/documenti_features.csv): Feature vectors for ML classification
  - [random_forest_model.joblib](file:///c%3A/Users/39329/albo-pretorio-audit-delivery/data/quadrelle/albo_download/random_forest_model.joblib): Trained classification model
  - [report/](file:///c%3A/Users/39329/albo-pretorio-audit-delivery/data/quadrelle/albo_download/report/) directory with analysis reports

## Technical Challenges Encountered

### ML Model Training Issues
During the audit, the ML model training phase encountered significant challenges:

1. **Feature Extraction Problems**: The TF-IDF vectorizer reported "After pruning, no terms remain. Try a lower min_df or a higher max_df." This occurred during the training for Quadrelle, indicating that the document preprocessing resulted in no meaningful features remaining after applying the minimum document frequency threshold.

2. **High Failure Rate**: During hyperparameter optimization using RandomizedSearchCV, 543 out of 600 model fits failed, resulting in mostly NaN scores. This suggests that the text preprocessing pipeline may not be producing suitable input for the ML algorithms.

3. **Low Confidence Classifications**: Across all municipalities, 100% of documents were classified with low confidence, indicating that the models were unable to reliably categorize the documents.

### Potential Causes
- **Poor OCR Quality**: Many documents may have been scanned images with poor OCR results
- **Inconsistent Formatting**: Documents from different time periods or departments may have inconsistent formatting
- **Limited Training Data**: The initial training set may be insufficient for the variety of document types present
- **Language Complexity**: Administrative Italian may have specialized terminology that requires more targeted preprocessing

## Procedural Analysis Results

### Document Sequence Patterns
The procedural analysis identified several recurring patterns in the administrative procedures:

1. **Incomplete Chains**: Most procedural sequences were missing critical documents required for full transparency
2. **Single Document Publications**: Many procedures consisted of single documents (e.g., only an "Avviso Gara" without the preceding deliberation or determination)
3. **Low Completion Scores**: Average completion scores ranged from 10-16%, indicating poor adherence to complete procedural documentation

### Common Missing Documents
Across all municipalities, the following procedural documents were frequently missing:
- Delibera (Deliberation)
- Determinazione (Determination)
- Progetto Definitivo (Final Project)
- Progetto Esecutivo (Executive Project)
- Gara (Tender)
- Aggiudicazione (Award)
- Contratto (Contract)
- Direzione Lavori (Construction Supervision)
- Collaudo (Final Inspection)

## System Performance Metrics

### Processing Time
- **Avella**: Successfully processed 1,177 documents with complete pipeline execution
- **Baiano**: Successfully processed 640 documents with complete pipeline execution including enhanced model training
- **Quadrelle**: Successfully processed 674 documents though with ML training challenges noted

### Storage Requirements
- **Avella**: ~5.5 GB of processed data (including PDFs and text extracts)
- **Baiano**: ~4.3 GB of processed data (including PDFs and text extracts)
- **Quadrelle**: ~8.3 GB of processed data (including PDFs and text extracts)

## Recommendations for Technical Improvements

### Preprocessing Enhancement
1. **OCR Quality Improvement**: Implement better OCR engines like Tesseract with Italian language models
2. **Image Preprocessing**: Apply image enhancement techniques before OCR for scanned documents
3. **Text Cleaning**: Develop more sophisticated text cleaning routines for administrative Italian

### Model Architecture
1. **Multi-language Models**: Utilize pre-trained models like multilingual BERT for better language understanding
2. **Ensemble Methods**: Combine multiple classification approaches to improve robustness
3. **Active Learning Loop**: Implement continuous learning from human feedback as seen in Baiano's enhanced model

### Pipeline Robustness
1. **Error Handling**: Improve error handling in feature extraction to prevent pipeline failures
2. **Parameter Tuning**: Implement adaptive parameter tuning for TF-IDF vectorization based on document characteristics
3. **Validation Checks**: Add data validation steps to ensure quality before ML processing

## Conclusion
The technical implementation of the audit system demonstrates both the power of automated compliance checking and the challenges inherent in processing real-world administrative documents. While the system successfully collected and analyzed thousands of documents across three municipalities, the technical challenges highlight the need for continued refinement of preprocessing and classification components to achieve more reliable results.