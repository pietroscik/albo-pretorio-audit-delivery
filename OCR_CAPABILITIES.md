# Capacità OCR del Sistema di Audit per Albi Pretori

## Panoramica

Il sistema è ora dotato di una pipeline OCR completa per l'elaborazione di documenti PDF scansionati, in aggiunta ai documenti con testo nativo. Questa funzionalità espande significativamente il perimetro di analisi consentendo di elaborare anche vecchi documenti, allegati tecnici e planimetrie che sono comuni nella documentazione amministrativa.

## Componenti Chiave

### 1. `ocr_processor.py`
- **Responsabilità**: Determina automaticamente se un PDF è scansionato o contiene testo nativo
- **Funzionalità principali**:
  - `is_pdf_scanned()`: Controlla se un PDF richiede OCR
  - `extract_text_from_scanned_pdf()`: Estrae testo da PDF scansionati usando Tesseract e OpenCV
  - `preprocess_image_for_ocr()`: Migliora le immagini per risultati OCR migliori
  - `extract_text_with_fallback()`: Seleziona automaticamente la modalità di estrazione appropriata

### 2. `text_extractor.py` (aggiornato)
- **Responsabilità**: Integra la logica OCR nel flusso di estrazione esistente
- **Miglioramenti**:
  - Utilizza il modulo OCR specializzato quando necessario
  - Segnala la sorgente dell'estrazione (testo nativo vs OCR)
  - Gestisce in modo elegante i casi di fallback

### 3. `post_process_classification.py`
- **Responsabilità**: Applica classificazioni migliorate ai documenti elaborati con OCR
- **Funzionalità principali**:
  - Validazione della qualità dell'OCR
  - Pulizia degli artefatti comuni dell'OCR
  - Classificazione migliorata per testo potenzialmente distorto
  - Generazione di report di qualità

## Flusso di Lavoro OCR

1. **Rilevamento automatico**: Il sistema determina se un PDF è scansionato o contiene testo nativo
2. **Selezione del metodo**: Se scansionato → OCR, se testo nativo → estrazione diretta
3. **Elaborazione**: Estrazione del testo usando il metodo appropriato
4. **Post-elaborazione**: Pulizia e classificazione migliorata per i documenti OCR
5. **Validazione**: Controllo della qualità e segnalazione di eventuali problemi

## Integrazione con la Pipeline Esistente

La pipeline OCR si integra perfettamente con il flusso esistente:

- **analyze_albo.py** continua a usare il TextExtractor in modo trasparente
- I documenti OCR vengono etichettati con `source: "ocr_specialized"` per tracciabilità
- I risultati vengono inviati al Knowledge Graph e alla dashboard come al solito
- La qualità OCR viene monitorata e riportata nei file di qualità

## Requisiti di Sistema

Per l'elaborazione OCR sono necessarie le seguenti dipendenze:

- `opencv-python`: Per la pre-elaborazione delle immagini
- `pytesseract`: Per l'engine OCR
- `PyMuPDF`: Per la manipolazione dei PDF
- `tesseract-ocr`: Engine OCR nativo (installazione separata richiesta)

## Comandi CLI

### Esecuzione della post-elaborazione OCR
```bash
python run.py post_process_classification --input data/avella/albo_download/atti_parsed.csv --output data/avella/albo_download/atti_parsed_enhanced.csv
```

### Esecuzione completa con OCR (integrata nella pipeline standard)
```bash
python run.py enterprise --ente avella --workflow full
```

## Benefici per l'Analisi

1. **Copertura completa**: Ora possiamo analizzare anche documenti scansionati
2. **Maggior quantità di dati**: Sblocco di "dark data" precedentemente non accessibile
3. **Audit più accurato**: Maggiori informazioni per l'identificazione di anomalie
4. **Knowledge Graph più ricco**: Più entità e relazioni da documenti precedentemente inaccessibili

## Qualità e Monitoraggio

- Ogni documento OCR include un indicatore di qualità
- I documenti con bassa qualità OCR sono segnalati per revisione manuale
- I report di qualità includono statistiche su PDF scansionati vs testo nativo
- La dashboard mostra indicatori specifici per documenti OCR