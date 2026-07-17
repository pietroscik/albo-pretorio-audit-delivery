# Orchestrazione con Docker Compose

## Panoramica

Questo documento descrive come orchestrare l'intero ecosistema del sistema di audit per albi pretori comunali utilizzando Docker Compose. L'orchestrazione include tutti i servizi necessari per un deployment enterprise completo.

## Architettura del Sistema

L'orchestrazione comprende i seguenti servizi:

1. **audit-engine**: Servizio principale per l'analisi e l'audit dei documenti
2. **web-dashboard**: Dashboard Streamlit per la visualizzazione dei dati
3. **rag-service**: Servizio RAG per l'interazione con il corpus documentale
4. **postgres**: Database PostgreSQL per la persistenza dei metadati
5. **redis**: Cache e gestione delle sessioni
6. **ocr-worker**: Worker dedicato all'elaborazione OCR (opzionale)

## Prerequisiti

- Docker versione 20.10 o superiore
- Docker Compose versione 2.0 o superiore
- Spazio sufficiente per i volumi persistenti

## Deploy dell'Ecosistema

### Deploy Completo
```bash
docker-compose up -d
```

### Deploy Parziale (solo alcuni servizi)
```bash
# Solo il motore di audit
docker-compose up -d audit-engine

# Solo dashboard e servizi dipendenti
docker-compose up -d postgres redis web-dashboard
```

### Deploy con Override (per ambienti specifici)
```bash
# Utilizzando un file di override personalizzato
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

## Gestione del Sistema

### Visualizzazione dei Log
```bash
# Log di tutti i servizi
docker-compose logs -f

# Log di un servizio specifico
docker-compose logs -f audit-engine
```

### Scalabilità
```bash
# Scalare il numero di worker OCR
docker-compose up -d --scale ocr-worker=3

# Scalare il servizio di audit
docker-compose up -d --scale audit-engine=2
```

### Backup e Recovery
```bash
# Backup del database
docker-compose exec postgres pg_dump -U audit_user albo_audit > backup.sql

# Ripristino del database
docker-compose exec -T postgres psql -U audit_user albo_audit < backup.sql
```

## Monitoraggio e Health Checks

Tutti i servizi includono health checks per garantire la disponibilità:

- **postgres**: Verifica la connettività al database
- **redis**: Verifica la disponibilità del servizio
- **audit-engine**: Verifica la corretta esecuzione del processo
- **web-dashboard**: Verifica la disponibilità dell'interfaccia web

## Sicurezza

L'orchestrazione implementa diverse misure di sicurezza:

1. **Isolamento di Rete**: Tutti i servizi operano su una rete dedicata
2. **Utenti Non-Root**: I container eseguono come utenti non-root
3. **Gestione Credenziali**: Password gestite tramite variabili d'ambiente
4. **Accesso Controllato**: Porte esposte solo dove necessario

## Persistenza dei Dati

I dati critici sono mantenuti persistenti tramite volumi Docker:

- **postgres_data**: Dati del database PostgreSQL
- **redis_data**: Dati della cache Redis
- **./data**: Dati di input/output del sistema
- **./logs**: File di log del sistema

## Ambienti di Esecuzione

### Sviluppo
```bash
docker-compose -f docker-compose.yml up -d
```

### Produzione
```bash
docker-compose -f docker-compose.yml -f docker-compose.prod.yml up -d
```

### Test
```bash
docker-compose -f docker-compose.yml -f docker-compose.test.yml up -d
```

## Best Practices per la Produzione

1. **Gestione Credenziali**: Utilizzare Docker Secrets o variabili d'ambiente criptate
2. **Backup Regolari**: Implementare backup automatizzati per i volumi critici
3. **Monitoraggio**: Integrare con sistemi di monitoraggio esterni (Prometheus, Grafana)
4. **Logging**: Centralizzare i log in un sistema di log management
5. **Sicurezza**: Aggiornare regolarmente le immagini e monitorare le vulnerabilità

## Troubleshooting

### Problemi Comuni e Soluzioni

#### Servizio non parte
Controllare i log:
```bash
docker-compose logs <service-name>
```

#### Problemi di memoria
Aggiungere limiti di memoria nel compose file:
```yaml
services:
  audit-engine:
    # ... altre configurazioni ...
    deploy:
      resources:
        limits:
          memory: 4G
        reservations:
          memory: 1G
```

#### Problemi di rete
Verificare la configurazione della rete e i collegamenti tra servizi.

## Scaling e Performance

Per ambienti con carichi elevati:

1. **Load Balancing**: Aggiungere un load balancer davanti ai servizi web
2. **Database Scaling**: Utilizzare replica e clustering per il database
3. **Worker Distribution**: Distribuire i worker OCR su più nodi
4. **Caching Strategy**: Ottimizzare la strategia di caching in base all'uso

## Aggiornamenti

Per aggiornare il sistema:

1. Fermare i servizi:
```bash
docker-compose down
```

2. Ricreare le immagini:
```bash
docker-compose build --pull
```

3. Riavviare i servizi:
```bash
docker-compose up -d
```