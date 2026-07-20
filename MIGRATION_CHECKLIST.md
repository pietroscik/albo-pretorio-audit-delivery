# ✅ Checklist di Migrazione: da `scripts/` a `src/`

## 🎯 Obiettivo

Questa guida fornisce un processo standardizzato per migrare gli script legacy dalla cartella `scripts/` all'architettura modulare in `src/delibere_comunali/`. L'obiettivo è eliminare il debito tecnico, centralizzare la logica e rendere il progetto più robusto e manutenibile.

---

## 🗺️ Processo di Migrazione (Esempio: `scripts/randomForest.py`)

Segui questi passaggi per ogni script che vuoi migrare.

### ☐ **Passo 1: Identifica e Analizza lo Script**

- **Script da migrare**: `scripts/randomForest.py`
- **Scopo**: Addestrare il modello di classificazione `RandomForestClassifier` con ottimizzazione degli iperparametri.
- **Criticità Attuali**:
  - Usa `argparse` per leggere i parametri, rendendolo difficile da chiamare da altri moduli.
  - Costruisce i percorsi dei file in modo autonomo, disallineato rispetto alla configurazione centrale.
  - È un'isola funzionale, non integrata con il resto dell'applicazione.

### ☐ **Passo 2: Crea il Nuovo Modulo in `src/`**

- **Crea un nuovo file**: `src/delibere_comunali/ml/classifier_trainer.py`.
  - La posizione è importante: la logica di training ML appartiene al package `ml`.
- **Copia il contenuto** di `scripts/randomForest.py` nel nuovo file.

### ☐ **Passo 3: Esegui il Refactoring del Codice**

L'obiettivo è trasformare lo script in un modulo Python riutilizzabile.

1. **Rimuovi `argparse`**: Elimina tutto il codice relativo a `argparse.ArgumentParser()`. I parametri verranno passati tramite argomenti di funzione.
2. **Incapsula la Logica**: Raggruppa la logica principale dello script in una funzione chiara e definita.
   ```python
   # In src/delibere_comunali/ml/classifier_trainer.py
   def train_and_evaluate_classifier(ente: str, base_path: Path):
       # ... logica di training ...
   ```
3. **Centralizza la Gestione dei Percorsi**: Sostituisci la costruzione manuale dei percorsi con la funzione di utilità già esistente.
   ```python
   # Rimuovi:
   # base_path = Path(f"data/{args.ente}/albo_download")
   
   # Usa:
   from delibere_comunali.utils.config import get_tenant_dir
   base_path = get_tenant_dir(ente)
   ```
4. **Rendi gli Import Relativi**: Assicurati che tutti gli import di moduli interni usino percorsi relativi al package `src`.
   ```python
   # Esempio
   from ..utils.config import get_tenant_dir
   ```

### ☐ **Passo 4: Integra il Nuovo Modulo in `run.py`**

1. **Crea un nuovo comando Click** in `run.py` per esporre la nuova funzionalità.
   ```python
   # In run.py
   @cli.command()
   @click.option('--ente', required=True, help='Nome dell\'ente.')
   def train_classifier(ente: str):
       """Addestra il modello di classificazione con ottimizzazione."""
       from delibere_comunali.ml.classifier_trainer import train_and_evaluate_classifier
       from delibere_comunali.utils.config import get_tenant_dir
       
       base_path = get_tenant_dir(ente)
       train_and_evaluate_classifier(ente=ente, base_path=base_path)
   ```
2. **Rimuovi il vecchio mapping** dal dizionario `COMMAND_MAP` in `run.py` per evitare duplicazioni.

### ☐ **Passo 5: Testa e Valida**

- Esegui il nuovo comando: `python run.py train-classifier --ente avella`.
- Verifica che il comportamento sia identico a quello del vecchio script.
- Controlla che il file del modello (`random_forest_model.joblib`) venga creato/aggiornato nella cartella corretta.

### ☐ **Passo 6: Pulisci e Documenta**

- **Elimina lo script legacy**: `git rm scripts/randomForest.py`.
- **Aggiorna la documentazione**: Modifica `README.md` e `CURRENT_COMMANDS.md` per riflettere il nuovo comando e rimuovere il vecchio.
- **Fai il commit** delle modifiche con un messaggio chiaro (es. `refactor: Migrate randomForest.py to a module`).