# Riferimento Comandi - Sistema Albo Pretorio Audit Delivery

Questo documento fornisce un riferimento aggiornato e accurato per tutti i comandi disponibili nel sistema, al fine di prevenire confusione dopo gli sviluppi recenti.

## Struttura del Sistema di Comando

Il sistema utilizza un **doppio sistema di comandi**:
1. **Comandi Click-based (Moderni)** - Implementati direttamente in [run.py](file:///c:/Users\39329\albo-pretorio-audit-delivery/run.py) con decorator Click
2. **Comandi Legacy** - Accessibili tramite sistema di mapping per retrocompatibilità

## Comandi Click-based (Consigliati)

### Comandi Principali
- `enterprise` - Workflow enterprise completo (opzioni: --ente, --workflow [full, analyze-only, scrape-only], --config)
- `audit` - Audit antifrode (opzioni: --base, --ente, --use-llm, --llm-provider, --llm-model)
- `build-kg` - Costruzione knowledge graph (opzioni: --base, --ente)
- `analyze-topology` - Analisi topologia grafo (opzioni: --base, --ente)
- `post-process-classification` - Post-elaborazione classificazioni (opzioni: --input, --output)
- `train-classifier` - Training modello di classificazione (opzioni: --ente)
- `supervised-training` - Training supervisionato (opzioni: --base, --ente)
- `metrics-exporter` - Server metriche (nessuna opzione richiesta)

### Sicurezza e Privacy
- `gdpr-delete` - Diritto all'oblio (opzioni: --user-identifier, --data-path)
- `privacy-report` - Report conformità GDPR (opzioni: --ente)

### Interfaccia Utente
- `control-room`, `dashboard`, `ui` - Dashboard di controllo (sinonimi)

## Comandi Legacy Disponibili

Comandi accessibili come `python run.py <comando>`:
- `scrape`, `analyze`, `pipeline`, `run-pipeline`, `scraper`
- `orchestrate`, `data-coord`, `config-mgmt`, `enterprise`
- `risk-assessment`, `management-kpi`, `actuarial-analysis`
- `rag`, `apply-corrections`, `validate-csv`, `validate-output`
- `detect-anomalies`, `export-linkeddata`, `clean-texts`, `sync-texts`
- `generate-groundtruth`, `visualize-graph`, `explore`, `reconcile`
- `validate-fase0`, `validate-ground`, `verify-output`, `update-preview`
- `finance-validate`, `random-forest`, `train`, `build-kg`, `analyze-topology`

## Workflow Enterprise

Il comando `enterprise` supporta tre opzioni di workflow:
1. `--workflow=full` (predefinito) - Esegue tutti i moduli disponibili
2. `--workflow=analyze-only` - Esegue solo l'analisi senza scraping
3. `--workflow=scrape-only` - Esegue solo lo scraping senza analisi

## Compatibilità e Best Practice

1. **Usare i comandi moderni** quando possibile per nuove implementazioni
2. **I comandi legacy sono mantenuti** per retrocompatibilità
3. **Controllare sempre con `python run.py --help`** per vedere i comandi effettivamente disponibili
4. **I comandi duplicati** (es. `build-kg` nei due sistemi) potrebbero avere comportamenti leggermente diversi

## Come Verificare i Comandi Disponibili

Eseguire uno dei seguenti comandi per vedere l'elenco aggiornato:

```bash
# Per i comandi moderni
python run.py --help

# Per i comandi legacy (mostra un messaggio di errore con la lista)
python run.py invalidcommand
```

## Nota sulle Versioni Precedenti

Alcune documentazioni o script potrebbero fare riferimento a workflow options come `risk_only`, `kpi_only`, ecc., ma queste non sono più supportate nel codice attuale. Le opzioni corrette sono: `full`, `analyze-only`, `scrape-only`.