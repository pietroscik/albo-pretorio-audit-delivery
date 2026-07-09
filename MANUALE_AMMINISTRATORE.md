# Manuale Amministratore - Albo Pretorio Audit Delivery

**Versione:** 1.0  
**Data:** 10/07/2026  
**Destinatari:** Amministratori di Sistema, Responsabili IT  

---

## 📖 **Indice**
1. [Introduzione](#-1-introduzione)
2. [Accesso e Autenticazione](#-2-accesso-e-autenticazione)
3. [Gestione Utenti e Ruoli](#-3-gestione-utenti-e-ruoli)
4. [Configurazione del Sistema](#-4-configurazione-del-sistema)
5. [Gestione Documenti Avanzata](#-5-gestione-documenti-avanzata)
6. [Monitoraggio e Manutenzione](#-6-monitoraggio-e-manutenzione)
7. [Sicurezza e Backup](#-7-sicurezza-e-backup)
8. [Risoluzione Problemi](#-8-risoluzione-problemi)
9. [API e Integrazioni](#-9-api-e-integrazioni)
10. [FAQ](#-10-faq)

---

## 🚀 **1. Introduzione**

### **1.1 Cos'è Albo Pretorio Audit Delivery (per Amministratori)**
**Albo Pretorio Audit Delivery** è un **sistema complesso** che richiede **configurazione, manutenzione e monitoraggio** per garantire:
- **Disponibilità** (24/7)
- **Sicurezza** (protezione dati, accessi controllati)
- **Prestazioni** (ottimizzazione risorse)
- **Conformità** (rispetto norme e regolamenti)

### **1.2 Requisiti per l'Amministratore**
| Requisito | Descrizione |
|-----------|-------------|
| **Conoscenze Tecniche** | Python, Linux, Database (SQL/NoSQL) |
| **Conoscenze Normative** | D.Lgs. 33/2013, CAD, GDPR |
| **Accesso** | Permessi di **root/sudo** sul server |
| **Strumenti** | Terminal, Git, Docker (opzionale) |

### **1.3 Ruoli e Responsabilità**

| Ruolo | Responsabilità | Competenze Richieste |
|-------|----------------|----------------------|
| **Amministratore di Sistema** | Gestione server, configurazione, manutenzione | ✅ Tecniche, ✅ Normative |
| **Responsabile IT** | Supervisione tecnologica, sicurezza | ✅ Tecniche, ⚠️ Normative |
| **DPO** | Conformità GDPR, privacy | ⚠️ Tecniche, ✅ Normative |

---

## 🔐 **2. Accesso e Autenticazione**

### **2.1 Modalità di Accesso Amministratore**
L'Amministratore può accedere al sistema tramite:

| Modalità | Descrizione | Livello di Sicurezza | Obbligatorio |
|----------|-------------|---------------------|--------------|
| **SPID (Livello 3)** | Identità digitale con autenticazione forte | ⭐⭐⭐⭐⭐ | ✅ |
| **CIE + PIN** | Carta di Identità Elettronica con PIN | ⭐⭐⭐⭐⭐ | ✅ |
| **CNS + Certificato** | Carta Nazionale dei Servizi | ⭐⭐⭐⭐ | ✅ |
| **SSH + Chiave Privata** | Accesso diretto al server | ⭐⭐⭐⭐⭐ | ✅ (per manutenzione) |

### **2.2 Primo Accesso**
1. **Ricevi le credenziali** di Amministratore dal Responsabile IT
2. **Accedi al pannello di amministrazione**: `https://[NOME_ENTE].albo-pretorio.it/admin`
3. **Autenticati** con SPID/CIE/CNS
4. **Accetta i termini** (Regolamento di Gestione)
5. **Configura il profilo** (imposta email, telefono, ecc.)

### **2.3 Accesso via SSH (per manutenzione)**
```bash
# Connessione al server
ssh admin@[IP_SERVER] -p 22

# Autenticazione con chiave privata (consigliato)
ssh -i ~/.ssh/albo_pretorio_key admin@[IP_SERVER]

# Verifica connessione
ping [IP_SERVER]
```

---

## 👥 **3. Gestione Utenti e Ruoli**

### **3.1 Elenco Utenti**

#### **3.1.1 Visualizzazione Utenti**
1. **Vai su** `Amministrazione → Utenti`
2. **Vedi la lista** di tutti gli utenti con:
   - **Nome e Cognome**
   - **Email**
   - **Ruolo**
   - **Data di creazione**
   - **Ultimo accesso**
   - **Stato** (Attivo, Bloccato, Disabilitato)

#### **3.1.2 Filtri e Ricerca**
- **Filtra per ruolo** (Amministratore, Responsabile, Operatore, Ospite)
- **Filtra per stato** (Attivo, Bloccato, Disabilitato)
- **Cerca per nome/email**

---

### **3.2 Creazione Utente**

#### **3.2.1 Creazione Manuale**
1. **Vai su** `Amministrazione → Utenti → Aggiungi Utente`
2. **Compila i campi**:
   - **Nome e Cognome** (obbligatorio)
   - **Email** (obbligatorio, univoca)
   - **Ruolo** (Amministratore, Responsabile, Operatore, Ospite)
   - **Ente** (se multi-tenant)
   - **Note** (opzionale)
3. **Scegli il metodo di autenticazione**:
   - **SPID** (consigliato)
   - **CIE**
   - **CNS**
   - **Credenziali Locali** (solo per test)
4. **Clicca su** `Crea Utente`
5. **Invia le credenziali** all'utente (se credenziali locali)

#### **3.2.2 Creazione Bulk (da CSV)**
1. **Prepara un file CSV** con le seguenti colonne:
   ```csv
   nome,cognome,email,ruolo,ente
   Mario,Rossi,mario.rossi@ente.it,Operatore,Comune di Roma
   Giovanni,Bianchi,giovanni.bianchi@ente.it,Responsabile,Comune di Roma
   ```
2. **Vai su** `Amministrazione → Utenti → Importa Utenti`
3. **Carica il file CSV**
4. **Verifica i dati** e conferma l'importazione

> **✅ Consigli:**
> - Usa **SPID/CIE** per tutti gli utenti in produzione
> - Assegna **ruoli minimi** (principio del **least privilege**)
> - **Verifica sempre** l'email prima di inviare le credenziali

---

### **3.3 Modifica Utente**

1. **Vai su** `Amministrazione → Utenti`
2. **Trova l'utente** (usando filtri o ricerca)
3. **Clicca su** `Modifica` (icona ✏️)
4. **Modifica i campi** necessari:
   - Ruolo
   - Ente
   - Email
   - Stato (Attivo/Bloccato)
5. **Clicca su** `Salva`

> **⚠️ Attenzione:**
> - **Non puoi modificare** il ruolo di un **Amministratore** (solo un altro Amministratore può farlo)
> - Le modifiche sono **tracciate** nel log di sistema

---

### **3.4 Blocco e Sblocco Utente**

#### **3.4.1 Blocco Manuale**
1. **Vai su** `Amministrazione → Utenti`
2. **Seleziona l'utente** da bloccare
3. **Clicca su** `Blocca` (icona 🚫)
4. **Inserisci la motivazione** (obbligatorio)
5. **Conferma il blocco**

#### **3.4.2 Sblocco Utente**
1. **Vai su** `Amministrazione → Utenti`
2. **Filtra per stato** = `Bloccato`
3. **Seleziona l'utente** da sbloccare
4. **Clicca su** `Sblocca` (icona ✅)
5. **Conferma lo sblocco**

#### **3.4.3 Blocco Automatico**
Il sistema **blocca automaticamente** un utente dopo:
- **5 tentativi di accesso falliti** (in 1 ora)
- **Notifica automatica** all'Amministratore

---

### **3.5 Eliminazione Utente**

1. **Vai su** `Amministrazione → Utenti`
2. **Seleziona l'utente** da eliminare
3. **Clicca su** `Elimina` (icona 🗑️)
4. **Inserisci la motivazione** (obbligatorio)
5. **Conferma l'eliminazione**

> **⚠️ Attenzione:**
> - **Non puoi eliminare** l'utente **Amministratore** se è l'unico
> - L'eliminazione è **definitiva** (ma i dati rimangono in backup per 1 anno)
> - **Assegna sempre** i documenti dell'utente a un altro utente prima di eliminarlo

---

### **3.6 Gestione Ruoli e Permessi**

#### **3.6.1 Ruoli Predefiniti**

| Ruolo | Permessi | Descrizione |
|-------|----------|-------------|
| **Amministratore** | ✅ Tutti | Gestione completa del sistema |
| **Responsabile Trasparenza** | ✅ Lettura, ✅ Scrittura, ✅ Report, ❌ Amministrazione | Supervisione pubblicazione dati |
| **Operatore Albo Pretorio** | ✅ Lettura, ✅ Scrittura, ❌ Report, ❌ Amministrazione | Gestione documenti |
| **Ospite** | ✅ Solo Lettura | Accesso in sola lettura (per audit) |

#### **3.6.2 Permessi Dettagliati**

| Azione | Amministratore | Responsabile | Operatore | Ospite |
|--------|---------------|--------------|-----------|-------|
| **Gestione Utenti** | ✅ | ❌ | ❌ | ❌ |
| **Configurazione Sistema** | ✅ | ❌ | ❌ | ❌ |
| **Caricamento Documenti** | ✅ | ✅ | ✅ | ❌ |
| **Modifica Documenti** | ✅ | ✅ | ✅ | ❌ |
| **Cancellazione Documenti** | ✅ | ❌ | ❌ | ❌ |
| **Pubblicazione Documenti** | ✅ | ✅ | ❌ | ❌ |
| **Esecuzione Analisi** | ✅ | ✅ | ✅ | ❌ |
| **Generazione Report** | ✅ | ✅ | ❌ | ✅ |
| **Accesso a Dati Sensibili** | ✅ | ❌ | ❌ | ❌ |
| **Gestione Backup** | ✅ | ❌ | ❌ | ❌ |

#### **3.6.3 Creazione Ruoli Personalizzati**
1. **Vai su** `Amministrazione → Ruoli → Aggiungi Ruolo`
2. **Inserisci il nome** del ruolo (es. "Supervisore")
3. **Seleziona i permessi** (spunta le caselle)
4. **Clicca su** `Crea Ruolo`

> **✅ Consigli:**
> - Usa **ruoli predefiniti** quando possibile
> - **Documenta sempre** i ruoli personalizzati
> - **Testa i permessi** prima di assegnare il ruolo a un utente

---

## ⚙️ **4. Configurazione del Sistema**

### **4.1 Configurazione Generale**

#### **4.1.1 Parametri di Base**
1. **Vai su** `Amministrazione → Configurazione → Generale`
2. **Modifica i parametri**:
   - **Nome Ente**
   - **Logo Ente** (carica file PNG/JPG)
   - **URL Base** (es. `https://comune.roma.albo-pretorio.it`)
   - **Lingua Predefinita** (Italiano, Inglese)
   - **Fuso Orario** (UTC, CET, CEST)
3. **Clicca su** `Salva`

#### **4.1.2 Parametri di Parallelizzazione**
| Parametro | Descrizione | Valore Consigliato |
|-----------|-------------|--------------------|
| **Abilita Parallelizzazione** | Attiva/disattiva esecuzione parallela | ✅ **Attivato** |
| **Numero Max Workers** | Numero massimo di thread paralleli | 4-8 (dipende dal server) |
| **Timeout Esecuzione** | Tempo massimo per operazione (secondi) | 300 (5 minuti) |

#### **4.1.3 Parametri di Caching**
| Parametro | Descrizione | Valore Consigliato |
|-----------|-------------|--------------------|
| **Abilita Caching** | Attiva/disattiva caching | ✅ **Attivato** |
| **Dimensione Max Cache** | Numero massimo di voci in cache | 50-100 |
| **TTL Cache (ore)** | Tempo di vita delle voci in cache | 24 |
| **Directory Cache** | Percorso per salvataggio cache | `/var/cache/albo_pretorio` |

---

### **4.2 Configurazione per Ente (Multi-Tenant)**

#### **4.2.1 Aggiunta Nuovo Ente**
1. **Vai su** `Amministrazione → Enti → Aggiungi Ente`
2. **Compila i campi**:
   - **Nome Ente** (obbligatorio)
   - **Codice ISTAT** (obbligatorio)
   - **Codice Fiscale** (obbligatorio)
   - **Partita IVA** (opzionale)
   - **Indirizzo** (obbligatorio)
   - **Email** (obbligatorio)
   - **Telefono** (opzionale)
   - **Logo** (opzionale)
   - **Directory Base** (es. `/var/albo_pretorio/comune_roma`)
3. **Clicca su** `Crea Ente`

#### **4.2.2 Configurazione Specifiche Ente**
1. **Seleziona l'ente** dall'elenco
2. **Modifica i parametri**:
   - **Regole di Dipendenza** (personalizzate per l'ente)
   - **Soglie di Confidenza** (per la classificazione)
   - **Termini di Conservazione** (personalizzati)
   - **Notifiche** (email per scadenze, report, ecc.)
3. **Clicca su** `Salva`

---

### **4.3 Configurazione Regole di Dipendenza**

#### **4.3.1 Regole Predefinite**
Il sistema include **regole predefinite** per le sequenze procedurali tipiche:

```python
# Esempio di regola predefinita
"Liquidazione": {
    "required": ["Impegno di Spesa"],
    "optional": ["Determinazione", "Delibera"],
    "weights": {"Impegno di Spesa": 1.0, "Determinazione": 0.7},
    "tolerance_days": 30
}
```

#### **4.3.2 Modifica Regole**
1. **Vai su** `Amministrazione → Regole → Dipendenze`
2. **Seleziona la regola** da modificare (es. "Liquidazione")
3. **Modifica i parametri**:
   - **Documenti Required** (obbligatori)
   - **Documenti Optional** (facoltativi)
   - **Pesi** (importanza di ogni documento)
   - **Tolleranza (giorni)** (tempo massimo tra documenti)
4. **Clicca su** `Salva`

#### **4.3.3 Aggiunta Nuova Regola**
1. **Vai su** `Amministrazione → Regole → Aggiungi Regola`
2. **Inserisci il nome** della regola (es. "Contratto Pubblico")
3. **Definisci i parametri** (come sopra)
4. **Clicca su** `Crea Regola`

> **✅ Consigli:**
> - **Testa sempre** le nuove regole con dati reali
> - **Documenta** le regole personalizzate
> - **Allinea** le regole alle **procedure interne** dell'ente

---

### **4.4 Configurazione Notifiche**

#### **4.4.1 Tipologie di Notifiche**

| Notifica | Descrizione | Destinatari | Frequenza |
|----------|-------------|-------------|-----------|
| **Scadenza Documento** | Avviso di scadenza conservazione | Responsabile Trasparenza | 30 giorni prima |
| **Bassa Confidenza** | Documenti con bassa confidenza | Operatori | Giornaliera |
| **Errore Analisi** | Fallimento analisi automatica | Amministratore | Immediata |
| **Report Settimanale** | Statistiche settimanali | Responsabile Trasparenza | Ogni lunedì |
| **Report Mensile** | Statistiche mensili | Amministratore, DPO | Ogni mese |

#### **4.4.2 Configurazione Email**
1. **Vai su** `Amministrazione → Notifiche → Configurazione Email`
2. **Compila i parametri**:
   - **Server SMTP** (es. `smtp.ente.it`)
   - **Porta** (es. 587 per TLS)
   - **Username** (es. `noreply@ente.it`)
   - **Password**
   - **Mittente** (es. `Albo Pretorio <noreply@ente.it>`)
   - **Soggetto Predefinito** (es. `[Albo Pretorio] {tipo_notifica}`)
3. **Testa la configurazione** con `Invia Email di Test`
4. **Clicca su** `Salva`

#### **4.4.3 Configurazione Webhook**
1. **Vai su** `Amministrazione → Notifiche → Webhook`
2. **Aggiungi un nuovo webhook**:
   - **URL** (es. `https://slack.com/api/webhook`)
   - **Eventi** (seleziona gli eventi da notificare)
   - **Header** (opzionale, es. `Authorization: Bearer XXX`)
3. **Testa il webhook** con `Invia Test`
4. **Clicca su** `Salva`

---

## 📁 **5. Gestione Documenti Avanzata**

### **5.1 Importazione Massiva**

#### **5.1.1 Importazione da CSV**
1. **Prepara un file CSV** con i documenti da importare:
   ```csv
   pdf_name,doc_type,numero_atto,data_atto,oggetto,ente
   Delibera_123.pdf,Delibera,123,10/01/2026,Approvazione Bilancio 2026,Comune di Roma
   Determinazione_45.pdf,Determinazione,45,15/01/2026,Acquisto Materiale,Comune di Roma
   ```
2. **Vai su** `Documenti → Importa → Da CSV`
3. **Carica il file CSV**
4. **Mappa i campi** (se necessario)
5. **Avvia l'importazione**

#### **5.1.2 Importazione da Cartella**
1. **Prepara una cartella** con i file PDF/XML
2. **Vai su** `Documenti → Importa → Da Cartella`
3. **Seleziona la cartella**
4. **Scegli le opzioni**:
   - **Ricorsivo** (sì/no)
   - **Sovrascrivi documenti esistenti** (sì/no)
5. **Avvia l'importazione**

> **✅ Consigli:**
> - Usa **nomi file descrittivi** (es. `Delibera_123_2026.pdf`)
> - **Verifica sempre** i dati importati
> - **Esegui test** con piccoli lotti prima di importare tutto

---

### **5.2 Esportazione Dati**

#### **5.2.1 Esportazione Documenti**
1. **Vai su** `Documenti → Esporta`
2. **Seleziona i documenti** (o usa `Tutti`)
3. **Scegli il formato**:
   - **CSV** (dati tabellari)
   - **JSON** (dati strutturati)
   - **XML** (formato standard)
   - **ZIP** (documenti + metadati)
4. **Clicca su** `Esporta`

#### **5.2.2 Esportazione Report**
1. **Vai su** `Report → [Seleziona Report]`
2. **Genera il report**
3. **Scegli il formato** (PDF, CSV, JSON)
4. **Scarica o invia** il report

---

### **5.3 Pulizia Dati**

#### **5.3.1 Pulizia Manuali**
1. **Vai su** `Documenti → Pulizia`
2. **Seleziona i criteri**:
   - **Documenti duplicati**
   - **Documenti senza metadati**
   - **Documenti scaduti**
   - **Documenti con bassa confidenza**
3. **Clicca su** `Cerca`
4. **Rivedi i risultati** e seleziona i documenti da pulire
5. **Clicca su** `Pulisci`

#### **5.3.2 Pulizia Automatica**
Il sistema **pulisce automaticamente**:
- **Cache** (ogni 7 giorni)
- **Log vecchi** (dopo 1 anno)
- **Documenti temporanei** (dopo 30 giorni)

---

## 📊 **6. Monitoraggio e Manutenzione**

### **6.1 Dashboard di Monitoraggio**

#### **6.1.1 Statistiche Generali**
La dashboard mostra:
- **📈 Documenti**: Totale, caricati oggi, in attesa
- **🔍 Analisi**: Eseguite, in corso, fallite
- **⚠️ Errori**: Numero di errori (classificazione, sequenze)
- **💾 Spazio**: Occupato, disponibile
- **👥 Utenti**: Attivi, bloccati, online

#### **6.1.2 Statistiche Avanzate**
1. **Vai su** `Monitoraggio → Statistiche`
2. **Seleziona il periodo**
3. **Visualizza i grafici**:
   - **Documenti per tipo** (torta)
   - **Documenti per data** (linea)
   - **Classificazione per confidenza** (istogramma)
   - **Tempi di analisi** (linea)

---

### **6.2 Log di Sistema**

#### **6.2.1 Visualizzazione Log**
1. **Vai su** `Monitoraggio → Log`
2. **Filtra per**:
   - **Tipo** (Info, Warning, Error, Critical)
   - **Data** (da/a)
   - **Utente**
   - **Operazione**
3. **Clicca su** `Cerca`

#### **6.2.2 Esportazione Log**
1. **Vai su** `Monitoraggio → Log`
2. **Applica i filtri**
3. **Clicca su** `Esporta` (CSV, JSON)

> **✅ Consigli:**
> - **Monitora regolarmente** i log per rilevare anomalie
> - **Esporta i log** per archiviazione esterna
> - **Configura alert** per errori critici

---

### **6.3 Manutenzione Ordinaria**

#### **6.3.1 Calendario Manutenzione**

| Attività | Frequenza | Responsabile | Note |
|----------|-----------|---------------|------|
| **Backup** | Quotidiano | Sistema Automatico | Alle 02:00 |
| **Verifica Integrità** | Settimanale | Amministratore | Ogni lunedì |
| **Aggiornamento Software** | Mensile | Amministratore | Prima domenica del mese |
| **Pulizia Cache** | Settimanale | Sistema Automatico | Ogni domenica |
| **Ottimizzazione DB** | Mensile | Amministratore | Ogni primo del mese |

#### **6.3.2 Esecuzione Backup**
```bash
# Backup manuale (da terminale)
python3 scripts/backup.py --full --output /backup/albo_pretorio_$(date +%Y%m%d).zip

# Backup incrementale
python3 scripts/backup.py --incremental --output /backup/albo_pretorio_incr_$(date +%Y%m%d).zip

# Verifica backup
python3 scripts/verify_backup.py --path /backup/albo_pretorio_20260710.zip
```

#### **6.3.3 Aggiornamento Software**
```bash
# Aggiorna il codice da Git
git pull origin main

# Installa dipendenze
pip install -r requirements.txt

# Esegui migrazioni database (se necessario)
python3 scripts/migrate_db.py

# Riavvia i servizi
sudo systemctl restart albo-pretorio
```

---

## 🔒 **7. Sicurezza e Backup**

### **7.1 Gestione Backup**

#### **7.1.1 Configurazione Backup**
1. **Vai su** `Amministrazione → Backup`
2. **Configura i parametri**:
   - **Frequenza** (Giornaliero, Settimanale, Mensile)
   - **Ora** (es. 02:00)
   - **Destinazione** (Locale, Cloud, NAS)
   - **Tipologia** (Completo, Incrementale)
   - **Retention** (numero di backup da conservare)
3. **Clicca su** `Salva`

#### **7.1.2 Test Backup**
1. **Vai su** `Amministrazione → Backup`
2. **Clicca su** `Esegui Backup Test`
3. **Verifica il risultato**

#### **7.1.3 Ripristino da Backup**
1. **Vai su** `Amministrazione → Backup`
2. **Seleziona il backup** da ripristinare
3. **Clicca su** `Ripristina`
4. **Conferma il ripristino**

> **⚠️ Attenzione:**
> - **Il ripristino sovrascrive** i dati attuali
> - **Esegui sempre un backup** prima di ripristinare
> - **Testa il ripristino** in ambiente di test

---

### **7.2 Gestione Sicurezza**

#### **7.2.1 Certificati SSL**
1. **Genera un certificato** (es. con Let's Encrypt):
   ```bash
   sudo certbot certonly --webroot -w /var/www/albo_pretorio -d albo-pretorio.ente.it
   ```
2. **Configura il server web** (Nginx/Apache) per usare il certificato
3. **Verifica il certificato**:
   ```bash
   openssl s_client -connect albo-pretorio.ente.it:443 -servername albo-pretorio.ente.it | openssl x509 -noout -dates
   ```

#### **7.2.2 Firewall**
```bash
# Esempio di configurazione UFW (Ubuntu)
sudo ufw allow 22/tcp       # SSH
sudo ufw allow 80/tcp       # HTTP
sudo ufw allow 443/tcp      # HTTPS
sudo ufw allow 5432/tcp     # PostgreSQL (solo interno)
sudo ufw enable

# Verifica stato
sudo ufw status
```

#### **7.2.3 Autenticazione a Due Fattori (2FA)**
1. **Vai su** `Amministrazione → Sicurezza → 2FA`
2. **Abilita 2FA** per:
   - **Amministratori** (obbligatorio)
   - **Responsabili** (consigliato)
   - **Operatori** (opzionale)
3. **Scegli il metodo**:
   - **TOTP** (Google Authenticator, Authy)
   - **SMS** (via provider esterno)
   - **Email** (codice temporaneo)

---

### **7.3 Gestione Incidenti**

#### **7.3.1 Procedura per Violazione Dati**
1. **Isola il sistema** (disconnetti dalla rete)
2. **Blocca gli accessi** non autorizzati
3. **Notifica il DPO** entro **72 ore** (GDPR Art. 33)
4. **Raccogli le prove** (log, screenshot, ecc.)
5. **Redigi un report** con:
   - **Data e ora** dell'incidente
   - **Tipologia** di violazione
   - **Dati coinvolti**
   - **Misure correttive** adottate

#### **7.3.2 Procedura per Malfunzionamento**
1. **Verifica i log** (`Monitoraggio → Log`)
2. **Riavvia i servizi** (se necessario)
   ```bash
   sudo systemctl restart albo-pretorio
   ```
3. **Notifica l'Amministratore**
4. **Apri un ticket** di supporto

---

## 🛠️ **8. Risoluzione Problemi**

### **8.1 Problemi Comuni**

| Problema | Causa | Soluzione |
|----------|-------|----------|
| **Sistema non risponde** | Server down | Riavvia il server: `sudo systemctl restart albo-pretorio` |
| **Accesso negato** | Permessi insufficienti | Verifica ruolo utente |
| **Documenti non caricati** | Spazio insufficiente | Libera spazio su disco |
| **Analisi lenta** | Troppi documenti | Aumenta `max_workers` o usa caching |
| **Errore 500** | Problema server | Controlla log: `tail -f /var/log/albo_pretorio/error.log` |

### **8.2 Errori e Messaggi**

| Messaggio di Errore | Significato | Soluzione |
|---------------------|-------------|----------|
| **"Database connection failed"** | Problema connessione DB | Verifica credenziali DB in `config.py` |
| **"Permission denied"** | Permessi file insufficienti | `chmod -R 755 /var/albo_pretorio` |
| **"MemoryError"** | Memoria insufficiente | Aumenta RAM o riduci `max_workers` |
| **"Timeout"** | Operazione troppo lenta | Aumenta `timeout` in configurazione |
| **"Invalid token"** | Token SPID/CIE scaduto | Rinnova autenticazione |

### **8.3 Debug Avanzato**

#### **8.3.1 Abilitare Debug Mode**
1. **Modifica `config.py`**:
   ```python
   DEBUG = True
   LOG_LEVEL = 'DEBUG'
   ```
2. **Riavvia il sistema**
3. **Controlla i log**:
   ```bash
   tail -f /var/log/albo_pretorio/debug.log
   ```

#### **8.3.2 Test di Connettività**
```bash
# Test connessione database
python3 -c "from delibere_comunali.utils.config import get_db_connection; conn = get_db_connection(); print('✅ DB OK' if conn else '❌ DB Error')"

# Test connessione cache
python3 -c "from delibere_comunali.core.orchestrator import ResultCache; cache = ResultCache(); print('✅ Cache OK' if cache else '❌ Cache Error')"

# Test parallelizzazione
python3 -c "from concurrent.futures import ThreadPoolExecutor; print('✅ ThreadPool OK')"
```

---

## 🌐 **9. API e Integrazioni**

### **9.1 API REST**

#### **9.1.1 Endpoint Disponibili**

| Endpoint | Metodo | Descrizione | Autenticazione |
|----------|--------|-------------|----------------|
| `/api/v1/documents` | GET | Elenco documenti | ✅ Token |
| `/api/v1/documents` | POST | Carica documento | ✅ Token |
| `/api/v1/documents/{id}` | GET | Dettagli documento | ✅ Token |
| `/api/v1/documents/{id}` | PUT | Modifica documento | ✅ Token |
| `/api/v1/documents/{id}` | DELETE | Cancella documento | ✅ Token |
| `/api/v1/analysis` | POST | Esegui analisi | ✅ Token |
| `/api/v1/reports` | GET | Elenco report | ✅ Token |
| `/api/v1/reports/{id}` | GET | Scarica report | ✅ Token |
| `/api/v1/stats` | GET | Statistiche | ✅ Token |

#### **9.1.2 Autenticazione API**
1. **Genera un token API**:
   - **Vai su** `Amministrazione → API → Token`
   - **Clicca su** `Genera Token`
   - **Copia il token** (sarà mostrato una sola volta)

2. **Usa il token nelle richieste**:
   ```bash
   curl -X GET "https://albo-pretorio.ente.it/api/v1/documents" \
     -H "Authorization: Bearer YOUR_TOKEN"
   ```

#### **9.1.3 Esempi di Chiamate API**

**Elenco documenti:**
```bash
curl -X GET "https://albo-pretorio.ente.it/api/v1/documents?limit=10" \
  -H "Authorization: Bearer YOUR_TOKEN"
```

**Carica documento:**
```bash
curl -X POST "https://albo-pretorio.ente.it/api/v1/documents" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@Delibera_123.pdf" \
  -F "doc_type=Delibera" \
  -F "numero_atto=123" \
  -F "data_atto=10/01/2026"
```

**Esegui analisi:**
```bash
curl -X POST "https://albo-pretorio.ente.it/api/v1/analysis" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"type": "full", "documents": [1, 2, 3]}'
```

---

### **9.2 Integrazione con PDND**

#### **9.2.1 Configurazione PDND**
1. **Registra l'ente** su [PDND](https://dati.gov.it/)
2. **Ottieni le credenziali** (Client ID, Client Secret)
3. **Vai su** `Amministrazione → Integrazioni → PDND`
4. **Inserisci le credenziali**
5. **Testa la connessione**

#### **9.2.2 Pubblicazione su PDND**
1. **Vai su** `Documenti → Pubblica su PDND`
2. **Seleziona i documenti** da pubblicare
3. **Mappa i campi** (se necessario)
4. **Clicca su** `Pubblica`

---

### **9.3 Integrazione con SPID**

#### **9.3.1 Configurazione SPID**
1. **Registra il servizio** su [SPID](https://www.spid.gov.it/)
2. **Ottieni le credenziali** (Client ID, Client Secret, Metadata URL)
3. **Vai su** `Amministrazione → Integrazioni → SPID`
4. **Inserisci i parametri**:
   - **Entity ID**
   - **Assertion Consumer Service URL**
   - **Metadata URL**
   - **Certificato** (PEM)
   - **Chiave Privata** (PEM)
5. **Testa la configurazione**

#### **9.3.2 Livelli di Sicurezza SPID**
| Livello | Descrizione | Utilizzo |
|--------|-------------|----------|
| **SPID 1** | Autenticazione base | Accesso pubblico |
| **SPID 2** | Autenticazione forte | Accesso operatori |
| **SPID 3** | Autenticazione forte + firma | Accesso amministratori |

---

## ❓ **10. FAQ (Domande Frequenti per Amministratori)**

### **10.1 Domande Generali**

**D: Come faccio ad aggiungere un nuovo ente?**
**R:** Vai su `Amministrazione → Enti → Aggiungi Ente` e compila i campi richiesti.

**D: Posso disabilitare la parallelizzazione?**
**R:** Sì, vai su `Amministrazione → Configurazione → Generale` e disabilita `Abilita Parallelizzazione`.

**D: Come faccio a vedere lo spazio occupato?**
**R:** Vai su `Monitoraggio → Statistiche` e controlla la sezione `Spazio`.

---

### **10.2 Domande su Utenti e Ruoli**

**D: Posso creare un ruolo personalizzato?**
**R:** Sì, vai su `Amministrazione → Ruoli → Aggiungi Ruolo` e definisci i permessi.

**D: Come faccio a bloccare un utente?**
**R:** Vai su `Amministrazione → Utenti`, seleziona l'utente e clicca su `Blocca`.

**D: Posso eliminare l'utente Amministratore?**
**R:** No, non puoi eliminare l'unico Amministratore. Devi prima creare un altro Amministratore.

---

### **10.3 Domande su Sicurezza**

**D: Come faccio a configurare il firewall?**
**R:** Usa `ufw` (Ubuntu) o `firewalld` (CentOS) per aprire le porte necessarie (22, 80, 443).

**D: Come faccio a generare un certificato SSL?**
**R:** Usa `certbot` (Let's Encrypt): `sudo certbot certonly --webroot -w /var/www/albo_pretorio -d albo-pretorio.ente.it`

**D: Come faccio a abilitare la 2FA?**
**R:** Vai su `Amministrazione → Sicurezza → 2FA` e abilita per i ruoli desiderati.

---

### **10.4 Domande su Manutenzione**

**D: Come faccio a eseguire un backup manuale?**
**R:** Esegui: `python3 scripts/backup.py --full --output /backup/albo_pretorio_$(date +%Y%m%d).zip`

**D: Come faccio ad aggiornare il sistema?**
**R:** Esegui: `git pull origin main && pip install -r requirements.txt && sudo systemctl restart albo-pretorio`

**D: Come faccio a verificare l'integrità dei dati?**
**R:** Esegui: `python3 scripts/verify_integrity.py`

---

### **10.5 Domande su API e Integrazioni**

**D: Come faccio a generare un token API?**
**R:** Vai su `Amministrazione → API → Token` e clicca su `Genera Token`.

**D: Come faccio a integrare con PDND?**
**R:** Registra l'ente su PDND, ottieni le credenziali e configurale in `Amministrazione → Integrazioni → PDND`.

**D: Come faccio a integrare con SPID?**
**R:** Registra il servizio su SPID, ottieni le credenziali e configurale in `Amministrazione → Integrazioni → SPID`.

---

## 📌 **Appendice A: Comandi Utili**

### **A.1 Comandi di Sistema**
```bash
# Avviare il sistema
sudo systemctl start albo-pretorio

# Fermare il sistema
sudo systemctl stop albo-pretorio

# Riavviare il sistema
sudo systemctl restart albo-pretorio

# Verificare stato
sudo systemctl status albo-pretorio

# Visualizzare log
sudo journalctl -u albo-pretorio -f
```

### **A.2 Comandi di Manutenzione**
```bash
# Pulizia cache
python3 scripts/clean_cache.py

# Ottimizzazione database
python3 scripts/optimize_db.py

# Verifica integrità
python3 scripts/verify_integrity.py

# Test connessioni
python3 scripts/test_connections.py
```

### **A.3 Comandi di Debug**
```bash
# Abilitare debug mode
python3 -c "import os; os.environ['DEBUG'] = 'True'; from delibere_comunali.core.orchestrator import CentralOrchestrator; o = CentralOrchestrator()"

# Test parallelizzazione
python3 -c "from concurrent.futures import ThreadPoolExecutor; with ThreadPoolExecutor(max_workers=4) as executor: print('✅ Parallelizzazione OK')"

# Test caching
python3 -c "from delibere_comunali.core.orchestrator import ResultCache; cache = ResultCache(); cache.set('test', 'value'); print('✅ Cache OK' if cache.get('test') else '❌ Cache Error')"
```

---

## 📌 **Appendice B: Glossario**

| Termine | Descrizione |
|---------|-------------|
| **API** | Application Programming Interface (Interfaccia di Programmazione) |
| **Backup** | Copia di sicurezza dei dati |
| **CAD** | Codice dell'Amministrazione Digitale |
| **CIE** | Carta di Identità Elettronica |
| **CNS** | Carta Nazionale dei Servizi |
| **DPO** | Data Protection Officer (Responsabile Protezione Dati) |
| **JSON** | JavaScript Object Notation (Formato dati) |
| **PDND** | Piattaforma Digitale Nazionale Dati |
| **RBAC** | Role-Based Access Control (Controllo Accessi Basato su Ruoli) |
| **SPID** | Sistema Pubblico di Identità Digitale |
| **SSL** | Secure Sockets Layer (Cifratura) |
| **TLS** | Transport Layer Security (Cifratura avanzata) |
| **Token** | Chiave di accesso temporanea |
| **2FA** | Two-Factor Authentication (Autenticazione a 2 fattori) |

---

*Ultimo aggiornamento: 10/07/2026*
*Per domande o supporto, contatta: **it@ente.it**
