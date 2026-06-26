Ecco un report dettagliato sullo stato attuale del repository `albo-pretorio-audit-delivery`. L'analisi evidenzia il contrasto tra l'architettura moderna (Sprint 1) e il debito tecnico ereditato (scripts legacy).

---

# 📊 Report Audit Tecnico: Repository `albo-pretorio-audit-delivery`

## 1. Analisi Strutturale (Mapping vs Realta)

Il progetto è in uno stato di **transizione architetturale**.

* **Il Nucleo (src/):** È solido, modulare e orientato a un approccio RegTech professionale. I moduli `parsing`, `rag`, e `scraping` seguono standard moderni.
* **Il Perimetro (scripts/):** È la zona di rischio. Molti script utilizzano percorsi relativi o assoluti che non sono compatibili con la nuova struttura `src/` basata su `config.py`.

### Incongruenze Rilevate

| Area | Stato | Note di Disallineamento |
| --- | --- | --- |
| **Configurazione** | ⚠️ Parziale | `config.py` esiste ma non è ancora il *single source of truth* per tutti i moduli. |
| **CLI / Entrypoint** | ✅ Risolto | `run.py` ora è centralizzato. Tuttavia, i file in `scripts/` potrebbero ancora cercare di leggere `../data/` invece di usare `Config.DATA_DIR`. |
| **Dipendenze** | ⚠️ Critico | `requirements.txt` e `pyproject.toml` divergono. Il risolutore PIP va in `resolution-too-deep` perché non c'è un *lock* coerente. |
| **ML/AI Pipeline** | ⚠️ Alto | Il modello `global_rf_model.joblib` presente in `assets/` è obsoleto rispetto alla versione di `scikit-learn` (1.9.0) ora installata. |

---

## 2. Dettaglio Disallineamenti Critici

### A. Il "Debito Documentale"

La documentazione (`ARCHITECTURE.md`, `README.md`) descrive ancora una pipeline basata su `daily_run.sh`.

* **Rischio:** Un nuovo contributor non saprebbe che il comando corretto oggi è `python run.py pipeline`.
* **Azione:** Aggiornare `README.md` per puntare esclusivamente all'interfaccia CLI di `run.py`.

### B. Incongruenze nel Data Flow

Il modulo `knowledge_graph/` genera output in `report/`, ma gli script legacy (`scripts/visualizza_grafo.py`) si aspettano di leggere da `data/`.

* **Rischio:** `visualizza_grafo.py` non troverà i nuovi file generati dal `GraphBuilder`, rendendo i report invisibili alla dashboard legacy.

### C. Gestione dei "Testi Corti" (22.56%)

Il report di qualità ha evidenziato che la pipeline di scraping ingestisce troppi "nodi fantasma".

* **Impatto:** Il grafo di 443 nodi è sovradimensionato rispetto al contenuto informativo reale (solo 195 atti).
* **Disallineamento:** Il `GraphBuilder` non ha ancora una logica di *pre-filtering* dedicata agli allegati irrilevanti.

---

## 3. Road-map di Allineamento (Priorità)

Per trasformare il repo in una configurazione "Formula 1" priva di errori, suggerisco questo ordine di interventi:

1. **Standardizzazione Path (Settimana 1):** Obbligare tutti gli script in `scripts/` a importare `Config` da `src/delibere_comunali/utils/config.py`. Se uno script non riesce a importare `Config`, va considerato "Legacy da sostituire".
2. **Sincronizzazione ML (Settimana 1):** Rigenerare i modelli `.joblib` usando `python run.py train`. Eliminare i file `.joblib` vecchi per forzare il sistema a usare solo versioni compatibili con le librerie attuali.
3. **Pulizia Dipendenze (Settimana 2):** * Eliminare `requirements.txt` dopo aver consolidato tutto in `pyproject.toml`.
* Installare con `pip install -e .` per avere un ambiente di sviluppo pulito.


4. **Filtro "Testi Corti" (Settimana 2):** Implementare una *Cleaning Layer* nel `parser` che scarta i documenti con `text_words < 200` prima della generazione dei metadati.

---

## 4. Conclusione

Il repository è **funzionale e potente**, ma soffre di "eccesso di opzioni". Hai troppi modi per fare la stessa cosa (vecchi script vs nuovi moduli).

**Il mio suggerimento:** Non cercare di riparare gli script legacy. Trattali come "sola lettura". Ogni volta che ne apri uno per un bug, convertilo in un modulo dentro `src/` e rimuovilo dalla cartella `scripts/`.

**Vuoi che io generi una "Checklist di Migrazione" automatizzata che puoi seguire per spostare un file alla volta da `scripts/` a `src/` senza rompere nulla?** 🚀🛡️