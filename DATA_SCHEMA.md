# Schema dei Dati del Sistema

## Panoramica

Questo documento descrive tutti i file di output generati dal sistema durante l'esecuzione di un audit completo per un ente comunale.

## Format di Input

### File CSV
#### albo_metadati.csv
- `pdf_name`: Nome del file PDF
- `data_atto`: Data del documento
- `numero_atto`: Numero del documento
- `oggetto`: Oggetto del documento
- `doc_type`: Tipo di documento
- `categoria`: Categoria del documento
- `responsabile`: Responsabile del procedimento
- `beneficiario`: Eventuale beneficiario
- `importo`: Eventuale importo
- `cig`: Codice identificativo gara (CIG)
- `cup`: Codice unico progetto (CUP)

#### allegati_parsed.csv
- `pdf_name`: Nome del file PDF
- `file_path`: Percorso del file
- `content`: Contenuto estratto
- `metadata`: Metadati estratti
- `parsed_date`: Data di parsing
- `status`: Stato del parsing

### File JSONL
#### documenti_corpus.jsonl
- `id`: Identificatore univoco del documento
- `content`: Contenuto testuale del documento
- `metadata`: Metadati del documento
- `entities`: Entità estratte dal documento




