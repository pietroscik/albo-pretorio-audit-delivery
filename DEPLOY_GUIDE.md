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

## Deployment con Docker (Consigliato)

### 1. Build dell'immagine
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "run.py"]
```

### 2. Compose file
```yaml
version: '3.8'

services:
  albo-pretorio:
    build: .
    ports:
      - "8000:8000"
    environment:
      - GOOGLE_API_KEY=${GOOGLE_API_KEY}
      - DATABASE_URL=${DATABASE_URL}
    volumes:
      - ./data:/app/data
      - ./logs:/app/logs
    restart: unless-stopped
```

### 3. Avvio del servizio
```bash
docker-compose up -d
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