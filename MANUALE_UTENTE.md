# Manuale Utente - Albo Pretorio Audit Delivery

**Versione:** 1.0  
**Data:** 10/07/2026  
**Destinatari:** Operatori Albo Pretorio, Responsabili Trasparenza  

---

## 📖 **Indice**
1. [Introduzione](#-1-introduzione)
2. [Accesso al Sistema](#-2-accesso-al-sistema)
3. [Interfaccia Utente](#-3-interfaccia-utente)
4. [Gestione Documenti](#-4-gestione-documenti)
5. [Analisi e Classificazione](#-5-analisi-e-classificazione)
6. [Report e Statistiche](#-6-report-e-statistiche)
7. [Risoluzione Problemi](#-7-risoluzione-problemi)
8. [FAQ](#-8-faq)

---

## 🚀 **1. Introduzione**

### **1.1 Cos'è Albo Pretorio Audit Delivery**
**Albo Pretorio Audit Delivery** è un **sistema automatizzato** per:
- **Caricare, classificare e analizzare** documenti dell'Albo Pretorio
- **Verificare la conformità normativa** (D.Lgs. 33/2013)
- **Monitorare le sequenze procedurali** (es. Impegno → Liquidazione → Pagamento)
- **Generare report e statistiche** per la trasparenza amministrativa

### **1.2 A cosa serve**
Il sistema aiuta a:
✅ **Ridurre i tempi** di gestione dei documenti (fino al **50%**)
✅ **Migliorare l'accuratezza** della classificazione (fino al **+30%**)
✅ **Garantire la conformità** alle norme (D.Lgs. 33/2013, CAD, ecc.)
✅ **Automatizzare i processi** di analisi e reporting

### **1.3 Requisiti di Sistema**
| Requisito | Descrizione |
|-----------|-------------|
| **Sistema Operativo** | Linux, Windows, macOS |
| **Browser** | Chrome, Firefox, Edge (ultime versioni) |
| **Python** | 3.8+ (per script di supporto) |
| **Memoria RAM** | Minimo 4 GB (consigliati 8 GB) |
| **Spazio su Disco** | Minimo 10 GB (dipende dal numero di documenti) |
| **Connessione Internet** | Obbligatoria per aggiornamenti e autenticazione |

### **1.4 Ruoli e Permessi**

| Ruolo | Permessi | Descrizione |
|-------|----------|-------------|
| **Operatore Albo Pretorio** | ✅ Lettura, ✅ Scrittura, ❌ Amministrazione | Può caricare e gestire documenti |
| **Responsabile Trasparenza** | ✅ Lettura, ✅ Scrittura, ✅ Report | Può generare report e statistiche |
| **Amministratore** | ✅ Tutti | Può configurare il sistema e gestire gli utenti |

---

## 🔐 **2. Accesso al Sistema**

### **2.1 Modalità di Accesso**
Il sistema supporta **3 modalità di autenticazione**:

| Modalità | Descrizione | Come Accedere |
|----------|-------------|---------------|
| **SPID** | Sistema Pubblico di Identità Digitale | [https://www.spid.gov.it](https://www.spid.gov.it) |
| **CIE** | Carta di Identità Elettronica | Lettore CIE + App **CIE ID** |
| **CNS** | Carta Nazionale dei Servizi | Lettore smart card + Certificato |

> **⚠️ Attenzione:**
> *In ambiente di **test**, è possibile accedere con **credenziali locali** (username + password).*

### **2.2 Primo Accesso**
1. **Ricevi le credenziali** dal tuo Amministratore di Sistema (solo per ambienti di test)
2. **Accedi al portale** all'indirizzo: `https://[NOME_ENTE].albo-pretorio.it`
3. **Seleziona la modalità di autenticazione** (SPID, CIE, CNS)
4. **Accetta i termini di servizio** (Regolamento di Gestione e Privacy Policy)
5. **Completa il profilo** (se richiesto)

### **2.3 Accesso Successivo**
1. **Vai all'indirizzo** del portale
2. **Seleziona la modalità di autenticazione**
3. **Inserisci le credenziali** (SPID, CIE, CNS)
4. **Accedi al sistema**

### **2.4 Recupero Credenziali (Solo Test)**
Se hai **dimenticato la password** (solo per ambienti di test):
1. Clicca su **"Recupera password"**
2. Inserisci la tua **email**
3. Riceverai un **link per reimpostare la password**

> **⚠️ Attenzione:**
> *In produzione, **non è possibile** recuperare la password: usa **SPID/CIE/CNS**.*

---

## 🖥️ **3. Interfaccia Utente**

### **3.1 Dashboard Principale**
La **dashboard** è divisa in **4 sezioni principali**:

```
┌───────────────────────────────────────────────────────┐
│  ALBO PRETORIO AUDIT DELIVERY                          │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  │
│  │  📊 Statistiche │  │  📁 Documenti │  │  🔍 Analisi  │  │
│  │  - Totale: 120 │  │  - Caricati: 10│  │  - Sequenze: 5│  │
│  │  - Oggi: +12   │  │  - In attesa: 2 │  │  - Errori: 0  │  │
│  └─────────────┘  └─────────────┘  └─────────────┘  │
│                                                           │
│  ┌─────────────────────────────────────────────────┐  │
│  │  📋 Ultime Operazioni                              │  │
│  │  1. Delibera n. 123 - Caricata da Mario Rossi      │  │
│  │  2. Determinazione n. 45 - Classificata automatica │  │
│  │  3. Contratto XYZ - Analisi completata             │  │
│  └─────────────────────────────────────────────────┘  │
└───────────────────────────────────────────────────────┘
```

### **3.2 Menu Principale**

| Voce di Menu | Descrizione | Ruoli Abilitati |
|--------------|-------------|-----------------|
| **🏠 Dashboard** | Pagina principale con statistiche | Tutti |
| **📁 Documenti** | Gestione documenti (caricamento, modifica, cancellazione) | Operatore, Responsabile |
| **🔍 Analisi** | Analisi procedurali e sequenze | Operatore, Responsabile |
| **📊 Report** | Generazione report e statistiche | Responsabile, Amministratore |
| **⚙️ Impostazioni** | Configurazione sistema | Amministratore |
| **👤 Profilo** | Gestione profilo utente | Tutti |
| **🔒 Esci** | Disconnessione dal sistema | Tutti |

---

## 📁 **4. Gestione Documenti**

### **4.1 Caricamento Documenti**

#### **4.1.1 Caricamento Singolo**
1. **Vai su** `Documenti → Carica Documento`
2. **Seleziona il file** (PDF, XML, o altri formati supportati)
3. **Compila i metadati**:
   - **Tipo documento** (Delibera, Determinazione, Contratto, ecc.)
   - **Numero** (es. 123/2026)
   - **Data** (formato GG/MM/AAAA)
   - **Oggetto** (descrizione breve)
   - **Categorie** (se applicabile)
4. **Clicca su** `Carica`
5. **Attendi la conferma** (il sistema esegue validazione automatica)

#### **4.1.2 Caricamento Multiplo**
1. **Vai su** `Documenti → Carica Multiplo`
2. **Seleziona più file** (fino a 50 alla volta)
3. **Compila i metadati comuni** (se applicabile)
4. **Clicca su** `Carica Tutti`
5. **Verifica i risultati** (il sistema mostrerà eventuali errori)

> **✅ Consigli:**
> - Usa **nomi file descrittivi** (es. `Delibera_123_2026_Approvazione_Bilancio.pdf`)
> - **Verifica sempre** i metadati prima di caricare
> - Per documenti **complessi**, usa il caricamento singolo

### **4.2 Modifica Documenti**

1. **Vai su** `Documenti → Elenco Documenti`
2. **Cerca il documento** (usando filtri o ricerca testuale)
3. **Clicca su** `Modifica` (icona ✏️)
4. **Modifica i campi** necessari:
   - Metadati (numero, data, oggetto)
   - Classificazione (categoria, sottocategoria)
   - Allegati (aggiungi/rimuovi file)
5. **Clicca su** `Salva`

> **⚠️ Attenzione:**
> - **Non puoi modificare** documenti già **pubblicati** (solo l'Amministratore può farlo)
> - Le modifiche sono **tracciate** nel log del sistema

### **4.3 Cancellazione Documenti**

1. **Vai su** `Documenti → Elenco Documenti`
2. **Seleziona il documento** da cancellare
3. **Clicca su** `Cancella` (icona 🗑️)
4. **Inserisci la motivazione** (obbligatorio)
5. **Conferma la cancellazione**

> **⚠️ Attenzione:**
> - **Non puoi cancellare** documenti **pubblicati** (solo l'Amministratore può farlo)
> - La cancellazione è **definitiva** (ma i documenti rimangono in backup per 1 anno)

### **4.4 Ricerca Documenti**

#### **4.4.1 Ricerca Semplice**
1. **Vai su** `Documenti → Elenco Documenti`
2. **Usa la barra di ricerca** in alto
3. **Inserisci un termine** (es. "Delibera", "2026", "Bilancio")
4. **Premi Invio**

#### **4.4.2 Ricerca Avanzata**
1. **Vai su** `Documenti → Ricerca Avanzata`
2. **Compila i filtri**:
   - **Tipo documento** (Delibera, Determinazione, ecc.)
   - **Data da/ a**
   - **Numero documento**
   - **Categorie**
   - **Stato** (Caricato, Pubblicato, Archiviato)
   - **Classificazione** (Alta, Media, Bassa confidenza)
3. **Clicca su** `Cerca`

> **✅ Consigli:**
> - Usa **filtri combinati** per risultati più precisi
> - **Esporta i risultati** in CSV per analisi esterne

---

## 🔍 **5. Analisi e Classificazione**

### **5.1 Analisi Automatica**
Il sistema **analizza automaticamente** i documenti caricati per:
- **Classificarli** in categorie (Contabilità, Lavori Pubblici, ecc.)
- **Identificare sequenze procedurali** (es. Impegno → Liquidazione)
- **Assegnare punteggi di confidenza** (Alta, Media, Bassa)
- **Rilevare anomalie** (es. documenti mancanti in una sequenza)

#### **5.1.1 Avvio Analisi**
1. **Vai su** `Analisi → Esegui Analisi`
2. **Seleziona i documenti** da analizzare (o usa `Tutti`)
3. **Scegli il tipo di analisi**:
   - **Classificazione** (solo categorizzazione)
   - **Sequenze Procedurali** (analisi delle dipendenze)
   - **Completa** (classificazione + sequenze)
4. **Clicca su** `Avvia Analisi`
5. **Attendi il completamento** (il tempo dipende dal numero di documenti)

#### **5.1.2 Risultati dell'Analisi**
Dopo l'analisi, vedrai:
- **📊 Statistiche**: Numero di documenti analizzati, tempo impiegato
- **🏷️ Classificazione**: Distribuzione per categoria
- **🔗 Sequenze**: Sequenze procedurali identificate
- **⚠️ Anomalie**: Documenti mancanti, violazioni di dipendenza

### **5.2 Classificazione Manuale**
Se il sistema **non classifica correttamente** un documento:

1. **Vai su** `Documenti → Elenco Documenti`
2. **Trova il documento** con bassa confidenza
3. **Clicca su** `Modifica` (icona ✏️)
4. **Seleziona la categoria corretta** dal menu a tendina
5. **Imposta la confidenza** su `Alta`
6. **Salva**

> **✅ Consigli:**
> - **Verifica sempre** i documenti con **bassa confidenza**
> - Usa la **ricerca per confidenza** per trovare documenti da rivedere

### **5.3 Gestione Sequenze Procedurali**

#### **5.3.1 Visualizzazione Sequenze**
1. **Vai su** `Analisi → Sequenze Procedurali`
2. **Seleziona un gruppo** (es. per oggetto o beneficiario)
3. **Visualizza la sequenza**:
   - **Documenti presenti** (in ordine cronologico)
   - **Documenti mancanti** (se la sequenza è incompleta)
   - **Punteggio di completamento** (0-100%)

#### **5.3.2 Esempio di Sequenza**
```
Sequenza: Spesa Completa (Completamento: 80%)
┌───────────────────────────────────────────────────────┐
│  1. ✅ Delibera n. 123 (10/01/2026)                     │
│  2. ✅ Determinazione n. 45 (15/01/2026)               │
│  3. ✅ Impegno di Spesa n. 78 (20/01/2026)             │
│  4. ❌ Liquidazione (MANCANTE)                         │
│  5. ❌ Accertamento (MANCANTE)                          │
└───────────────────────────────────────────────────────┘
```

---

## 📊 **6. Report e Statistiche**

### **6.1 Tipologie di Report**

| Report | Descrizione | Frequenza | Destinatari |
|--------|-------------|-----------|-------------|
| **Report Giornaliero** | Attività del giorno (documenti caricati, analisi eseguite) | Ogni giorno | Operatori |
| **Report Settimanale** | Statistiche settimanali (classificazione, sequenze) | Ogni lunedì | Responsabile Trasparenza |
| **Report Mensile** | Analisi completa (conformità, qualità dati) | Ogni mese | Amministratore, DPO |
| **Report di Conformità** | Verifica conformità normativa | Ogni 6 mesi | Sindaco, DPO |

### **6.2 Generazione Report**

#### **6.2.1 Report Automatici**
I report **vengono generati automaticamente** e inviati via email ai destinatari.

#### **6.2.2 Report Manuali**
1. **Vai su** `Report → Genera Report`
2. **Seleziona il tipo di report**:
   - **Statistiche Classificazione**
   - **Analisi Sequenze**
   - **Conformità Normativa**
   - **Qualità Dati**
3. **Scegli il periodo** (da/a)
4. **Seleziona i filtri** (opzionale):
   - Tipo documento
   - Categoria
   - Ente
5. **Clicca su** `Genera Report`
6. **Scegli il formato**:
   - **PDF** (per stampa)
   - **CSV** (per analisi in Excel)
   - **JSON** (per integrazione con altri sistemi)
7. **Scarica o invia** il report

### **6.3 Esempio di Report**

#### **Report Statistiche Classificazione**
```
=== REPORT STATISTICHE CLASSIFICAZIONE ===
Periodo: 01/07/2026 - 10/07/2026

📊 Distribuzione per Categoria:
- Contabilità: 45 documenti (37.5%)
- Lavori Pubblici: 30 documenti (25.0%)
- Personale: 20 documenti (16.7%)
- Regolamenti: 15 documenti (12.5%)
- Altro: 10 documenti (8.3%)

🎯 Qualità Classificazione:
- Alta Confidenza: 80 documenti (66.7%)
- Media Confidenza: 30 documenti (25.0%)
- Bassa Confidenza: 10 documenti (8.3%)

⚠️ Documenti da Rivedere: 10
```

---

## ❓ **7. Risoluzione Problemi**

### **7.1 Problemi Comuni**

| Problema | Causa | Soluzione |
|----------|-------|----------|
| **Non riesco ad accedere** | Credenziali scadute o errate | Usa SPID/CIE o contatta l'Amministratore |
| **Documento non caricato** | Formato non supportato | Usa PDF, XML o formati aperti |
| **Classificazione errata** | Testo poco chiaro | Modifica manualmente la categoria |
| **Sequenza incompleta** | Documenti mancanti | Carica i documenti mancanti |
| **Report non generato** | Dati insufficienti | Carica più documenti |

### **7.2 Errori e Messaggi**

| Messaggio di Errore | Significato | Soluzione |
|---------------------|-------------|----------|
| **"Formato non supportato"** | Il file non è in un formato valido | Converti in PDF o XML |
| **"Dati mancanti"** | Metadati obbligatori non compilati | Compila tutti i campi richiesti |
| **"Permessi insufficienti"** | Non hai i permessi per l'operazione | Contatta l'Amministratore |
| **"Documento già pubblicato"** | Il documento è già stato pubblicato | Non puoi modificarlo (solo Amministratore) |
| **"Analisi in corso"** | Un'analisi è già in esecuzione | Attendi il completamento |

### **7.3 Contatti per Supporto**

| Tipo di Problema | Contatto | Email | Telefono |
|------------------|----------|-------|---------|
| **Accesso** | Amministratore di Sistema | it@ente.it | +39 XXX XXXXXXX |
| **Classificazione** | Responsabile Trasparenza | trasparenza@ente.it | +39 XXX XXXXXXX |
| **Normativa** | DPO | dpo@ente.it | +39 XXX XXXXXXX |
| **Tecnico** | Supporto Tecnico | supporto@ente.it | +39 XXX XXXXXXX |

---

## ❓ **8. FAQ (Domande Frequenti)**

### **8.1 Domande Generali**

**D: Cos'è Albo Pretorio Audit Delivery?**
**R:** È un sistema automatizzato per **gestire, analizzare e classificare** i documenti dell'Albo Pretorio, garantendo la **conformità normativa** e la **trasparenza amministrativa**.

**D: Chi può usare il sistema?**
**R:** Tutti gli **operatori dell'ente** (amministratori, responsabili trasparenza, operatori albo pretorio) con **ruoli e permessi** specifici.

**D: È necessario installare qualcosa?**
**R:** No, il sistema è **web-based** e accessibile da qualsiasi browser moderno.

---

### **8.2 Domande su Accesso e Autenticazione**

**D: Posso accedere senza SPID/CIE?**
**R:** In **produzione**, no. In **ambiente di test**, puoi usare credenziali locali (username + password).

**D: Ho dimenticato la password (ambiente test). Cosa faccio?**
**R:** Clicca su **"Recupera password"** e segui le istruzioni. In produzione, usa **SPID/CIE/CNS**.

**D: Il mio account è stato bloccato. Cosa faccio?**
**R:** Contatta l'**Amministratore di Sistema** per lo sblocco.

---

### **8.3 Domande su Documenti**

**D: Quali formati di file sono supportati?**
**R:** **PDF, XML, JSON, CSV**. Per i documenti ufficiali, si consiglia **PDF/A** (formato per archiviazione a lungo termine).

**D: Posso modificare un documento già pubblicato?**
**R:** No, solo l'**Amministratore** può modificare documenti pubblicati.

**D: Come faccio a sapere se un documento è stato classificato correttamente?**
**R:** Controlla il **punteggio di confidenza** (Alta, Media, Bassa). I documenti con **bassa confidenza** vanno rivisti manualmente.

---

### **8.4 Domande su Analisi e Report**

**D: Quanto tempo ci vuole per analizzare 100 documenti?**
**R:** Con la **parallelizzazione**, circa **1-2 minuti**. Senza parallelizzazione, circa **5-10 minuti**.

**D: Posso esportare i dati in Excel?**
**R:** Sì, puoi **esportare i report in formato CSV** e aprirli con Excel.

**D: Come faccio a vedere le sequenze procedurali?**
**R:** Vai su **Analisi → Sequenze Procedurali** e seleziona un gruppo di documenti.

---

### **8.5 Domande su Sicurezza e Privacy**

**D: I miei dati sono sicuri?**
**R:** Sì, il sistema usa:
- **Cifratura TLS 1.3** per la trasmissione
- **Autenticazione forte** (SPID/CIE/CNS)
- **Backup automatici** quotidiani
- **Logging completo** di tutte le operazioni

**D: I documenti sono accessibili a tutti?**
**R:** No, solo:
- **Documenti pubblicati**: Accessibili a tutti (come da legge)
- **Documenti in bozza**: Accessibili solo agli **operatori autorizzati**

**D: Cosa succede ai miei dati personali?**
**R:** I dati personali contenuti nei documenti **pubblici** (es. deliberazioni) sono **trattati in base all'obbligo legale** (D.Lgs. 33/2013). Non è richiesta l'anonimizzazione.

---

## 📌 **Appendice A: Scorciatoie da Tastiera**

| Scorciatoia | Azione |
|-------------|--------|
| **Ctrl + S** | Salva le modifiche |
| **Ctrl + F** | Ricerca nel documento |
| **Ctrl + P** | Stampa |
| **Esc** | Annulla/Chiudi |
| **F5** | Aggiorna la pagina |

---

## 📌 **Appendice B: Glossario**

| Termine | Descrizione |
|---------|-------------|
| **Albo Pretorio** | Strumento di pubblicità legale degli atti amministrativi |
| **D.Lgs. 33/2013** | Normativa sulla trasparenza amministrativa |
| **CAD** | Codice dell'Amministrazione Digitale |
| **SPID** | Sistema Pubblico di Identità Digitale |
| **CIE** | Carta di Identità Elettronica |
| **CNS** | Carta Nazionale dei Servizi |
| **DPO** | Data Protection Officer (Responsabile Protezione Dati) |
| **PDF/A** | Formato PDF per archiviazione a lungo termine |
| **Confidenza** | Livello di affidabilità della classificazione (Alta, Media, Bassa) |
| **Sequenza Procedurale** | Serie di documenti collegati (es. Delibera → Determinazione → Impegno) |

---

*Ultimo aggiornamento: 10/07/2026*
*Per domande o supporto, contatta: **supporto@ente.it**
