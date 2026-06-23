# 📚 Documentazione API - Motore RAG

Questo documento descrive le funzioni principali esposte dai moduli `rag_app.py` e `src/web/rag_chat.py` per l'interazione con il sistema di Retrieval-Augmented Generation (RAG).

## Funzioni Core

### `esegui_query_rag_core(query, ente, only_accounting)`

Questa è la funzione di **alto livello** e il punto di ingresso principale per interrogare il sistema RAG da moduli esterni, come la `app_control_room.py`. È progettata per essere multi-tenant e domain-aware.

- **Descrizione**: Esegue una query in linguaggio naturale su un corpus documentale specifico di un ente, con la possibilità di filtrare i risultati per dominio di pertinenza.
- **Parametri**:
  - `query` (str): La domanda dell'utente (es. "Quali sono gli affidamenti diretti sotto i 40k euro?").
  - `ente` (str): Il nome dell'ente (es. "baiano", "avella"). Questo parametro determina la cartella `data/{ente}/albo_download` da cui caricare il corpus e l'indice FAISS.
  - `only_accounting` (bool, default=`False`): Se `True`, la ricerca viene ristretta ai soli documenti marcati con `accounting_relevant=True`, aumentando drasticamente la precisione per le domande finanziarie.
- **Valore di Ritorno**:
  - `str`: La risposta testuale generata dall'LLM, oppure un messaggio di errore formattato in caso di problemi.
- **Logica Interna**:
  1. Utilizza una cache in memoria (`_multi_tenant_rag_chains`) per memorizzare le chain RAG già inizializzate per ogni combinazione di `ente` e `only_accounting`, evitando di ricaricare l'indice FAISS ad ogni chiamata.
  2. Se una chain non è in cache, la inizializza chiamando `_init_rag_system_core` o, in fallback, `_init_local_chain_core`.
  3. Invoca il metodo `.invoke()` della chain, passando sia la `query` che il flag `only_accounting`.

---

### `LLMFailoverRAGChain.invoke(question, only_accounting)`

Il cuore del motore RAG, che orchestra il recupero dei documenti e la generazione della risposta.

- **Descrizione**: Esegue il processo RAG completo: recupera i documenti pertinenti, costruisce il contesto e interroga una catena di LLM in failover.
- **Parametri**:
  - `question` (str): La domanda dell'utente.
  - `only_accounting` (bool, default=`False`): Il flag che attiva il filtro di dominio.
- **Logica Interna**:
  1. **Retrieval**:
     - Se il retriever è un indice **FAISS**, esegue una ricerca per similarità. Per ottimizzare, recupera un numero maggiore di documenti (`k_fetch=20`) se `only_accounting` è `True`, per poi filtrare in memoria i risultati e mantenere solo i 6 più pertinenti con `accounting_relevant=True`.
     - Se il retriever è il **`LocalTokenRetriever`** (fallback lessicale), passa direttamente il flag `only_accounting` per filtrare i documenti prima ancora di calcolare l'overlap dei token.
  2. **Context Formatting**: Prepara il contesto per l'LLM formattando i documenti recuperati e aggiungendo metadati chiave come `[Fonte: ...]`, `[CIG: ...]`, ecc.
  3. **LLM Failover**: Prova a invocare i modelli LLM (es. Gemini, Mistral) in ordine di priorità. Se un modello fallisce (es. per quota esaurita, errore 429), entra in un "cooldown" di 60 secondi e il sistema passa automaticamente al modello successivo nella catena.

---

### `_load_corpus_documents(corpus_path)`

Funzione di utilità per caricare e preparare i documenti per l'indicizzazione.

- **Descrizione**: Legge il file `documenti_corpus.jsonl`, lo divide in chunk e arricchisce ogni chunk con i metadati più importanti (oggetto, CIG, CUP, RUP, beneficiario, etc.) come prefisso testuale.
- **Logica Interna**:
  1. Utilizza `RecursiveCharacterTextSplitter` per dividere il testo dei documenti in frammenti più piccoli e sovrapposti.
  2. Per ogni chunk, costruisce un **prefisso testuale** contenente i metadati chiave. Questo passaggio è **cruciale** perché "ancora" il contenuto del chunk al suo contesto amministrativo, migliorando drasticamente l'accuratezza del retrieval semantico.
  3. Salva il flag `accounting_relevant` all'interno dei metadati di ogni `Document` di LangChain.