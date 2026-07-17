# Setup Grafana per il Monitoraggio del Sistema

## Panoramica

Questo documento descrive come configurare e utilizzare Grafana per monitorare il sistema di audit per albi pretori comunali con dashboard preconfigurate.

## Architettura del Monitoraggio

Il sistema di monitoraggio è composto da:

- **Prometheus**: Raccoglie e memorizza le metriche dal sistema
- **Grafana**: Visualizza le metriche attraverso dashboard intuitive
- **Sistema di audit**: Espone metriche in formato Prometheus

## Avvio del Sistema di Monitoraggio

### Con Docker Compose (raccomandato)

```bash
docker-compose up -d
```

Questo avvierà tutti i servizi inclusi Prometheus e Grafana.

### Accesso a Grafana

Dopo l'avvio, Grafana sarà disponibile all'indirizzo:

```
http://localhost:3000
```

Le credenziali di default sono:
- **Username**: admin
- **Password**: admin

## Dashboard Disponibili

### 1. Albo Pretorio Audit - System Metrics

Questa dashboard preconfigurata mostra:

- **Documenti elaborati**: Numero totale di documenti processati suddivisi per tipo e metodo
- **Tempi di elaborazione**: Distribuzione dei tempi di processing (P95, P99)
- **Dimensione code Redis**: Monitoraggio delle code di lavoro
- **Stato worker**: Online/offline per diversi tipi di worker
- **Tassi di errore**: Errori per modulo e tipo
- **Throughput**: Velocità di elaborazione dei documenti
- **Rapporto OCR vs Standard**: Percentuale di documenti elaborati con OCR rispetto al metodo standard

### 2. Metriche in Tempo Reale

Le metriche vengono aggiornate ogni 5 secondi e includono:

- `documents_processed_total`: Conteggio cumulativo di documenti elaborati
- `document_processing_seconds`: Tempo di elaborazione per documento
- `redis_queue_size`: Dimensione delle code Redis
- `worker_status`: Stato dei worker
- `errors_total`: Conteggio degli errori

## Configurazione Personalizzata

### Aggiunta di Nuove Dashboard

Per aggiungere nuove dashboard:

1. Creare un file JSON di dashboard in `grafana/dashboards/`
2. Riavviare il servizio Grafana: `docker-compose restart grafana`

### Modifica delle Dashboard Esistenti

Le dashboard sono gestite come codice (Infrastructure as Code), quindi:

1. Modificare il file JSON corrispondente in `grafana/dashboards/`
2. Riavviare il contenitore Grafana per applicare le modifiche

## Monitoraggio Specifico per Ente

Le dashboard supportano il filtraggio per ente tramite variabili Grafana. Nella dashboard principale:

1. Selezionare l'ente desiderato dal menu a discesa
2. I grafici si aggiorneranno automaticamente per mostrare solo i dati per quell'ente

## Allarmi e Notifiche

### Configurazione Allarmi

Per configurare allarmi su Grafana:

1. Accedere a Grafana
2. Andare in "Alerting" → "Alert Rules"
3. Creare una nuova regola basata sulle metriche del sistema

### Esempi di Allarmi Utili

- `redis_queue_size > 100`: Allarme quando la coda Redis supera 100 elementi
- `worker_status == 0`: Allarme quando un worker va offline
- `rate(errors_total[5m]) > 0`: Allarme quando si verificano errori

## Risoluzione dei Problemi

### Grafana non si avvia

Controllare i log con:
```bash
docker-compose logs grafana
```

### Dashboard non appare

Assicurarsi che il file della dashboard sia presente in `grafana/dashboards/` e che il servizio Grafana sia stato riavviato.

### Metriche non arrivano

Controllare che Prometheus stia scrapando correttamente i target:
1. Accedere a `http://localhost:9090`
2. Andare in "Status" → "Targets"
3. Verificare che i target `audit-engine` e `metrics-exporter` siano UP

## Sicurezza

### Cambio Password di Default

Dopo il primo accesso, cambiare immediatamente la password di default di Grafana.

### Accesso Sicuro

In produzione, configurare Grafana dietro un reverse proxy con SSL/TLS.

## Integrazione con Altro Software

Il sistema espone metriche in formato Prometheus standard, quindi è possibile integrarlo facilmente con:

- Alertmanager per gestione allarmi
- CloudWatch, Datadog o altri sistemi di monitoraggio
- Pipeline ELK per analisi avanzate