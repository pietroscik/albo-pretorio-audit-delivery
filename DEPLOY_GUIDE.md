# Guida al Deployment

Questa guida descrive come effettuare il deployment del sistema "Albo Pretorio Audit Delivery" in un ambiente di produzione presso un ente pubblico italiano.

## Prerequisiti

### Infrastruttura
- Server Linux (Ubuntu 20.04 LTS o CentOS 8+ consigliati)
- Python 3.8+ (preferibilmente 3.11+)
- Memoria RAM: minimo 8GB (consigliati 16GB+ per analisi simultanee)
- Spazio disco: minimo 50GB (consigliati 100GB+ per dati storici)
- Connessione Internet (per aggiornamenti e API esterne)

### Sicurezza
- Firewall configurato per consentire solo le porte necessarie
- Sistema di autenticazione centralizzato (possibilmente SPID)
- Crittografia a riposo per i dati sensibili
- Politiche di backup e disaster recovery

## Installazione

### 1. Clonazione del repository
```bash
git clone https://github.com/pietroscik/albo-pretorio-audit-delivery.git
cd albo-pretorio-audit-delivery
```

### 2. Creazione ambiente virtuale
```bash
python -m venv venv
source venv/bin/activate  # Su Windows: venv\Scripts\activate
```

### 3. Installazione dipendenze
```bash
pip install -r requirements.txt
```

### 4. Configurazione ambiente
Creare un file `.env` nella radice del progetto:
```env
# Chiavi API (gestite tramite variabili d'ambiente)
GOOGLE_API_KEY=tua_chiave_api
MISTRAL_API_KEY=tua_chiave_mistral

# Configurazione database (se utilizzato)
DATABASE_URL=sqlite:///./albo_pretorio.db

# Configurazione logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/albo_pretorio/app.log

# Configurazione SSL (produzione)
SSL_CERT_PATH=/path/to/certificate.crt
SSL_KEY_PATH=/path/to/private.key
```

## Configurazione per ambiente PA

### 1. Autenticazione
Per l'integrazione con sistemi di autenticazione pubblica (SPID):

1. Configurare un gateway di autenticazione
2. Implementare middleware per la gestione delle sessioni
3. Verificare la compatibilità con i sistemi di identità digitale

### 2. Conformità normativa
Assicurarsi che il deployment rispetti:

- **D.Lgs. 33/2013** - Trasparenza amministrativa
- **D.Lgs. 196/2003** - Protezione dati personali (Codice Privacy)
- **CAD (Codice Amministrazione Digitale)**
- **Linee guida AgID** per i sistemi informatici della PA

### 3. Sicurezza
- Limitare l'accesso ai dati sensibili
- Implementare log di audit completi
- Configurare sistemi di monitoraggio
- Applicare aggiornamenti di sicurezza tempestivamente

## Guida al Deployment Docker

Questa guida illustra come eseguire il sistema di audit degli albi pretori comunali utilizzando Docker e Docker Compose.

### Prerequisiti

- Docker Engine (versione 20.10 o superiore)
- Docker Compose (versione 2.0 o superiore)
- Almeno 4 GB di RAM disponibile per l'esecuzione completa

### Build dell'Immagine Docker

```bash
# Nella directory principale del progetto
docker build -t albo-pretorio-audit .
```

### Esecuzione con Docker Compose

Per avviare l'intero sistema con tutti i servizi:

```bash
# Avvia tutti i servizi in background
docker-compose up -d

# Controlla lo stato dei servizi
docker-compose ps

# Visualizza i log in tempo reale
docker-compose logs -f
```

### Servizi Disponibili

Dopo l'avvio, saranno disponibili i seguenti servizi:

- **Scraper** (interno): Esegue lo scraping degli albi pretori
- **Control Room**: `http://localhost:8501` - Dashboard di controllo principale
- **RAG App**: `http://localhost:8504` - Interfaccia per il RAG semantico
- **Web Dashboard**: `http://localhost:8503` - Dashboard web generale

### Esecuzione di Operazioni Specifiche

#### Solo scraping di un comune specifico:

```bash
# Esegui uno scraping diretto
docker run --rm -v $(pwd)/data:/app/data albo-pretorio-audit python -m src.delibere_comunali.scraping.new_albo_scraper --ente sperone --max-pages 5
```

#### Esecuzione di un audit completo:

```bash
# Esegui un audit completo
docker run --rm -v $(pwd)/data:/app/data albo-pretorio-audit python run.py audit --ente sperone --workflow full
```

### Gestione dei Dati

I dati vengono memorizzati nei volumi Docker:

- `/data`: Metadati e documenti scaricati
- `/logs`: Log delle operazioni

I volumi sono montati come bind mounts per persistenza locale.

### Monitoraggio e Logging

#### Controllare i log di un servizio specifico:

```bash
docker-compose logs scraper
docker-compose logs control-room
```

#### Verificare lo stato di salute:

```bash
docker-compose ps
docker stats
```

### Esecuzione in Produzione

Per un deployment in produzione, è consigliabile:

1. Utilizzare un registry Docker privato
2. Configurare un reverse proxy (es. nginx) con SSL/TLS
3. Implementare backup automatici dei volumi dati
4. Configurare alerting e monitoraggio esterni

#### Esempio di configurazione per produzione:

```yaml
# docker-compose.prod.yml
version: '3.8'

services:
  scraper:
    # ... configurazione base ...
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '0.5'
          memory: 1G
    restart: always
```

### Risoluzione dei Problemi

#### Se i servizi non partono correttamente:

```bash
# Controlla i log dettagliati
docker-compose logs --tail=50 <service_name>

# Ricrea un servizio specifico
docker-compose up --force-recreate <service_name>
```

#### Se Playwright non riesce ad avviare il browser:

Controllare che le dipendenze di sistema siano installate correttamente nell'immagine. L'immagine ufficiale Playwright dovrebbe già includerle tutte.

### Sicurezza

- Tutti i servizi girano con utente non-root
- Le porte sono esposte solo localmente per default
- Nessun dato sensibile è hard-coded nell'immagine

### Aggiornamento del Sistema

Per aggiornare il sistema:

```bash
# Aggiorna il codice
git pull origin main

# Ricostruisci l'immagine
docker-compose build --no-cache

# Riavvia i servizi
docker-compose down && docker-compose up -d
```

## Configurazione del servizio di sistema (Linux)

### 1. Creazione del servizio systemd
Creare il file `/etc/systemd/system/albo-pretorio.service`:
```ini
[Unit]
Description=Albo Pretorio Audit Delivery
After=network.target

[Service]
Type=simple
User=albo-user
WorkingDirectory=/opt/albo-pretorio-audit-delivery
ExecStart=/opt/albo-pretorio-audit-delivery/venv/bin/python run.py control-room
Restart=always
EnvironmentFile=/opt/albo-pretorio-audit-delivery/.env

[Install]
WantedBy=multi-user.target
```

### 2. Avvio del servizio
```bash
sudo systemctl daemon-reload
sudo systemctl enable albo-pretorio
sudo systemctl start albo-pretorio
```

## Monitoraggio e manutenzione

### 1. Logging
- I log sono salvati in `./logs/` o nel percorso specificato
- Controllare regolarmente i file di log per errori o avvisi
- Implementare sistemi di alert per eventi critici

### 2. Backup
- Configurare backup automatici dei dati
- Verificare periodicamente la ripristinabilità dei backup
- Mantenere almeno 3 copie recenti

### 3. Aggiornamenti
- Pianificare aggiornamenti regolari
- Testare gli aggiornamenti in ambiente di staging
- Mantenere una strategia di rollback

## Sicurezza e audit

### 1. Accesso
- Limitare l'accesso ai soli utenti autorizzati
- Implementare registrazione delle attività di accesso
- Utilizzare sistemi di autenticazione forte

### 2. Dati
- Criptare i dati sensibili a riposo
- Implementare retention policy per i dati
- Assicurarsi che i dati siano cancellati secondo le normative

### 3. Verifiche
- Eseguire regolarmente test di penetrazione
- Verificare la conformità alle normative
- Aggiornare le politiche di sicurezza

## Integrazione con sistemi PA

### 1. SPID
- Configurare l'autenticazione tramite SPID
- Implementare gestione sessioni conformi
- Verificare compatibilità con enti IdP

### 2. PagoPA
- Se applicabile, integrare con sistema di pagamento
- Assicurarsi che i pagamenti siano gestiti in modo sicuro

### 3. Anagrafe Nazionale
- Se applicabile, integrare con sistemi anagrafici
- Rispettare vincoli di sicurezza e privacy

## Troubleshooting

### Errori comuni
- **API Keys mancanti**: Verificare il file `.env`
- **Permessi insufficienti**: Controllare i permessi sui file e directory
- **Memoria insufficiente**: Aumentare la RAM o ottimizzare i parametri

### Contatti di supporto
Per problemi critici, contattare:
- Amministratore di sistema: [email_amministratore]
- Supporto tecnico: [email_supporto]
- Sicurezza: [email_sicurezza]

## Conformità GDPR

Questo sistema è stato progettato per rispettare pienamente il Regolamento Generale sulla Protezione dei Dati (GDPR):

- Nessun trattamento di dati personali sensibili
- Conservazione limitata ai fini specifici
- Diritti degli interessati garantiti
- Privacy by design e by default