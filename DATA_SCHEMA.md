# 📄 Schema Dati - `allegati_parsed.csv`

Questo documento descrive la struttura e il significato delle colonne principali del file `allegati_parsed.csv`, che rappresenta il database centrale del sistema di analisi.

## Colonne Principali

| Nome Colonna                  | Tipo Dati | Descrizione |
|-------------------------------|-----------|-------------|
| `doc_type`                    | `string`  | Tipologia giuridica dell'atto (es. Determinazione). |
| `category`                    | `string`  | Classificazione tematica dell'atto. |
| `oggetto`                     | `string`  | L'oggetto testuale dell'atto. |
| `importo_max`                 | `float`   | Importo massimo rilevato in euro. |
| `cig`                         | `string`  | Codice Identificativo Gara. |
| `cup`                         | `string`  | Codice Unico di Progetto. |
| `beneficiario`                | `string`  | Ente, azienda o persona destinataria dei fondi. |
| `responsabile`                | `string`  | RUP o dirigente firmatario. |
| `accounting_relevant`         | `boolean` | Indica se l'atto ha rilevanza contabile. |
| `anomalie`                    | `string`  | Anomalie rilevate nel documento. |
| `legal_urn`                   | `string`  | Identificativo standard dell'atto. |
| `is_signed`                   | `boolean` | Presenza di firma digitale. |
| `is_accessible`               | `boolean` | PDF testuale (non immagine). |
| `atto_group`                  | `string`  | Raggruppamento dell'atto. |
| `capitolo`                    | `string`  | Capitolo di bilancio. |
| `codice_appalti`              | `string`  | Riferimenti normativi codice appalti. |
| `compliance_score`            | `float`   | Punteggio di aderenza procedurale. |
| `data_atto`                   | `string`  | Data di emissione. |
| `has_visto_contabile`         | `boolean` | Presenza del visto di regolarità. |
| `impegno_anno`                | `float`   | Anno di impegno di spesa. |
| `impegno_num`                 | `float`   | Numero impegno di spesa. |
| `numero_atto`                 | `string`  | Numero progressivo documento. |
| `tipo_procedura`              | `string`  | Es. Affidamento diretto. |
| `veridicità_score`            | `float`   | Score di confidenza dell'estrazione. |