# 📄 Schema Dati - `allegati_parsed.csv`

Questo documento descrive la struttura e il significato delle colonne principali del file `allegati_parsed.csv`, che rappresenta il database centrale del sistema di analisi.

## Colonne Principali

| Nome Colonna                  | Tipo Dati | Descrizione                                                                                                                              | Esempio                               |
|-------------------------------|-----------|------------------------------------------------------------------------------------------------------------------------------------------|---------------------------------------|
| `pdf_name`                    | `string`  | **CHIAVE PRIMARIA**. Nome univoco del file PDF o P7M analizzato.                                                                         | `Delibera_123_01012026.pdf`           |
| `doc_type`                    | `string`  | Tipologia giuridica dell'atto, inferita dal nome del file o dal contenuto (es. Delibera, Determinazione).                                | `Determinazione`                      |
| `category`                    | `string`  | Classificazione tematica dell'atto, basata su un motore rule-based o su un modello ML.                                                    | `Lavori Pubblici`                     |
| `oggetto`                     | `string`  | L'oggetto testuale dell'atto, estratto tramite Regex o LLM.                                                                              | `Affidamento servizio di pulizia...`  |
| `importo_max`                 | `float`   | L'importo monetario più alto rilevato nel documento, normalizzato in formato numerico.                                                   | `4500.50`                             |
| `cig`                         | `string`  | **Codice Identificativo Gara**. Estratto dal testo.                                                                                      | `BBA7EC995E`                          |
| `cup`                         | `string`  | **Codice Unico di Progetto**. Estratto dal testo.                                                                                        | `C57H25002250004`                     |
| `beneficiario`                | `string`  | Il nome normalizzato del fornitore o del beneficiario dell'atto.                                                                          | `ACME SRL`                            |
| `responsabile`                | `string`  | Il nome normalizzato del Responsabile Unico del Procedimento (RUP) o del firmatario dell'atto.                                           | `MARIO ROSSI`                         |
| `accounting_relevant`         | `boolean` | **Flag di Dominio**. `True` se l'atto ha rilevanza contabile/finanziaria, `False` altrimenti. Usato per il filtro globale.             | `True`                                |
| `classification_confidence`   | `string`  | Indica il livello di confidenza della classificazione: `high`, `ambiguous`, `ml_predicted`, `human_reviewed`.                            | `high`                                |
| `extraction_method`           | `string`  | Traccia la pipeline di estrazione utilizzata (es. `visto_strutturata`, `fallback_layout`, `+GEMINI_REFINED`).                               | `visto_strutturata+GEMINI_REFINED`    |
| `anomalie`                    | `string`  | Stringa che descrive le anomalie rilevate dal motore antifrode (es. `Sospetto Frazionamento`, `CIG Fantasma`).                           | `Sindrome della Soglia`               |
| `legal_urn`                   | `string`  | **Uniform Resource Name** generato secondo lo standard Normeinrete (NIR) per l'identificazione univoca dell'atto.                        | `urn:nir:baiano;dirigente:delibera...`|
| `is_signed`                   | `boolean` | `True` se il documento PDF contiene una firma digitale valida (PAdES/CAdES).                                                             | `True`                                |
| `is_accessible`               | `boolean` | `True` se il PDF è testuale e non un'immagine scannerizzata, indicando un livello base di accessibilità.                               | `True`                                |
| `text_sha256`                 | `string`  | Hash SHA-256 del contenuto testuale estratto, utilizzato per la deduplicazione di documenti identici.                                    | `e8d68022ff9e...`                     |
| `text_preview`                | `string`  | Un'anteprima dei primi 1200 caratteri del testo, usata per l'addestramento del modello ML e per le visualizzazioni rapide.              | `COMUNE DI BAIANO...`                 |