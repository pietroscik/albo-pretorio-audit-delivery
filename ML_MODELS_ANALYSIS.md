# Analisi dei Modelli ML nel Progetto

## Introduzione

Il sistema contiene tre distinti modelli di machine learning specializzati in diverse fasi del processo di classificazione e analisi dei documenti dell'albo pretorio. Ogni modello ha uno scopo specifico e contribuisce in modo complementare al miglioramento della qualità complessiva del sistema.

## Modello 1: `randomForest.py` - Risoluzione delle Ambiguità

### Descrizione
Questo modello si occupa principalmente della **risoluzione delle classificazioni ambigue**. È progettato per intervenire quando il sistema primario non riesce a classificare con certezza un documento, utilizzando una combinazione di regole avanzate e predizione ML per risolvere le ambiguità.

### Caratteristiche
- **Tipo**: Random Forest + Regole avanzate
- **Funzione principale**: Risoluzione delle ambiguità di classificazione
- **Input**: Documenti con classificazione_confidence = 'ambiguous'
- **Output**: Nuova classificazione con confidenza elevata
- **Approccio**: Prima applica regole specifiche, poi ricorre al modello ML se necessario
- **Soglie di confidenza**: 
  - ≥ 0.65: "ml_predicted_high_conf"
  - ≥ 0.50: "ml_predicted_medium_conf"

### Vantaggi
- Approccio ibrido (regole + ML) per maggiore accuratezza
- Gestisce specificamente il problema delle classificazioni ambigue
- Include regole contestuali specifiche per i documenti amministrativi

## Modello 2: `train_model.py` - Modello di Classificazione Principale

### Descrizione
Questo è il **modello principale di classificazione** utilizzato per assegnare le categorie ai documenti. Implementa un approccio completo di machine learning con ottimizzazione degli iperparametri tramite GridSearchCV.

### Caratteristiche
- **Tipo**: Random Forest con ottimizzazione iperparametri
- **Funzione principale**: Classificazione primaria dei documenti
- **Input**: Oggetto + testo dei documenti
- **Output**: Categoria del documento con relativa confidenza
- **Ottimizzazione**: GridSearchCV con ricerca su 26244 combinazioni
- **Metrica di valutazione**: f1_macro
- **Supporto multi-tenant**: Supporta diversi enti comunali

### Vantaggi
- Ottimizzazione completa degli iperparametri
- Valutazione approfondita con test set
- Supporto per active learning (correzioni manuali)
- Alta precisione grazie all'ottimizzazione

## Modello 3: `enhance_ml_model.py` - Modello di Miglioramento Continuo

### Descrizione
Questo modello implementa un sistema di **active learning e miglioramento continuo**. Si occupa di rafforzare il modello principale utilizzando i dati risolti precedentemente, creando un ciclo di miglioramento continuo.

### Caratteristiche
- **Tipo**: Random Forest con active learning
- **Funzione principale**: Miglioramento del modello esistente
- **Input**: Documenti con alta confidenza (risolti da altri modelli)
- **Output**: Modello aggiornato e migliorato
- **Approccio**: Utilizza dati precedentemente risolti per rafforzare il modello
- **Focus**: Adattamento dinamico al dominio specifico

### Vantaggi
- Sistema di miglioramento continuo
- Adattamento al dominio specifico dell'ente
- Utilizza i dati già classificati per rinforzare il modello
- Approccio flessibile ai dati limitati

## SWOT Analysis della Configurazione ML

### Punti di Forza (Strengths)
- **Approccio modulare**: Tre modelli distinti con ruoli ben definiti
- **Gestione delle ambiguità**: Soluzione specifica per il problema delle classificazioni incerte
- **Ottimizzazione avanzata**: Ricerca completa degli iperparametri
- **Active learning**: Integrazione di feedback umano per migliorare continuamente
- **Supporto multi-tenant**: Adattamento ai diversi enti comunali
- **Valutazione completa**: Metriche approfondite (precision, recall, f1-score macro)
- **Resilienza**: Approccio ibrido regole + ML per maggiore robustezza

### Opportunità (Opportunities)
- **Integrazione avanzata**: Maggior coordinamento tra i modelli attraverso il CentralOrchestrator
- **Espansione delle capacità**: Possibilità di aggiungere modelli per altre funzionalità (NER, sentiment analysis)
- **Miglioramento delle prestazioni**: Ottimizzazione ulteriore delle soglie di confidenza
- **Scalabilità**: Estensione del sistema a più enti contemporaneamente
- **Dashboard di monitoraggio**: Monitoraggio in tempo reale delle prestazioni dei modelli

### Debolezze (Weaknesses)
- **Complessità**: Sistema complesso con più modelli che richiede gestione attenta
- **Overhead computazionale**: Ogni documento può passare attraverso più modelli
- **Dipendenza tra modelli**: I modelli sono interdipendenti, rendendo difficile l'isolamento
- **Tempi di addestramento**: Ottimizzazione completa richiede tempi lunghi (come osservato)
- **Configurazione ripetuta**: Simile configurazione tra i modelli porta a duplicazione di codice

### Minacce (Threats)
- **Obsolescenza**: Modelli che potrebbero diventare obsoleti senza continua supervisione
- **Drift concettuale**: Cambiamenti nei documenti ufficiali potrebbero invalidare i modelli
- **Dipendenza dagli iperparametri**: Prestazioni dipendenti da configurazione ottimale
- **Scalabilità dei dati**: Difficoltà crescente di gestire grandi volumi di dati
- **Mantenimento**: Necessità di competenze specifiche per mantenere e aggiornare i modelli

## Conclusioni

La configurazione ML del sistema rappresenta un approccio sofisticato e ben strutturato per affrontare le sfide della classificazione automatica dei documenti amministrativi. I tre modelli lavorano in sinergia per garantire:

1. Una classificazione primaria accurata con ottimizzazione completa
2. Una gestione efficace delle ambiguità
3. Un sistema di miglioramento continuo basato su feedback

Questa architettura consente di affrontare in modo robusto le problematiche specifiche del dominio amministrativo, dove la precisione e la gestione delle eccezioni sono fondamentali. Tuttavia, richiede una gestione attenta per bilanciare complessità, prestazioni e tempi di elaborazione.