# Guida al Machine Learning e Active Learning (Feedback Loop)

Il progetto utilizza un sistema di classificazione intelligente basato su `RandomForestClassifier` per categorizzare automaticamente gli atti amministrativi. Una delle feature più avanzate implementate è il **Feedback Loop (Active Learning)**. 

Questo permette al sistema di "imparare dai propri errori" sfruttando le correzioni manuali fatte da un operatore umano su un file Excel.

## 🔄 Come funziona il Ciclo

1. **Prima Estrazione (`analyze_albo.py`):**
   Lo script prova a classificare il documento tramite regole (RegEx). Se il documento è ambiguo o sconosciuto, e se esiste già un modello ML, chiede al modello di predirlo. I documenti predetti dal modello ricevono una `classification_confidence` pari a `ml_predicted`.

2. **Generazione dell'Excel:**
   Durante il salvataggio in `albo_analisi.xlsx`, lo script individua tutti gli atti classificati tramite ML. Questi vengono copiati in un foglio speciale chiamato **`revisione_ml`**. Lo script aggiunge una colonna vuota chiamata `categoria_corretta`. Viene creato anche un foglio `anomalie_da_addestrare` per la revisione delle anomalie.

3. **Intervento Umano (La tua parte):**
   L'utente apre il file `albo_analisi.xlsx` e va sul foglio `revisione_ml`. 
   * Se la categoria scelta dal ML è sbagliata, l'utente scrive la categoria esatta nella colonna `categoria_corretta`.
   * Salva il file Excel.

4. **Riaddestramento (`randomForest.py`):**
   Quando lanci di nuovo `run_pipeline.py` (che a sua volta lancia `randomForest.py`), il sistema:
   * Legge il file Excel `albo_analisi.xlsx`.
   * Cerca il foglio `revisione_ml`.
   * Prende tutte le tue correzioni dalla colonna `categoria_corretta`.
   * **Aggiorna automaticamente** i CSV di base (`documenti_features.csv` e `allegati_parsed.csv`), impostando la tua categoria corretta e portando la confidenza a `high`.
   * Addestra un nuovo modello Random Forest includendo i tuoi nuovi esempi "certi".

5. **Riclassificazione:**
   Il nuovo modello (ora più intelligente) ricalcola le probabilità sui documenti che erano rimasti ancora ambigui, migliorando costantemente l'accuratezza globale del dataset.

## 🧠 Modello Globale (Federated Learning)
In assenza di un modello locale nella cartella dell'ente, `analyze_albo.py` è programmato per cercare un "Cervello Globale" in `assets/models/global_rf_model.joblib`. Questo permette a Comuni piccoli (con pochi dati storici) di beneficiare dell'addestramento effettuato su Comuni più grandi.

## 💡 Suggerimenti
* Non è necessario correggere *tutti* i documenti. Anche solo correggere 10-20 documenti particolarmente difficili darà al modello le chiavi di lettura per riconoscerli in futuro.
* Assicurati che i nomi delle categorie inserite manualmente in Excel corrispondano esattamente ai nomi previsti nel sistema (es. "Delibera di Giunta", "Lavori Pubblici").