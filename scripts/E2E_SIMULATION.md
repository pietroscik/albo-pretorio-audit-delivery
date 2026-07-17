# Simulazione End-to-End per il Bilanciamento del Carico

## Panoramica

Questo script simula uno scenario realistico di ingestion di documenti con tipologie miste (PDF con testo nativo e PDF scansionati) per testare la distribuzione del carico tra il motore principale e i worker OCR tramite la coda Redis.

## Funzionalità

- Generazione automatica di PDF di prova (sia nativi che "scansionati")
- Simulazione del rilevamento automatico di PDF scansionati
- Routing intelligente verso i worker OCR o il motore standard
- Misurazione delle performance di elaborazione
- Report dettagliato dei risultati

## Dipendenze

Lo script richiede le seguenti dipendenze aggiuntive rispetto al sistema principale:

```bash
pip install faker reportlab redis
```

## Utilizzo

### Esecuzione della simulazione completa

```bash
cd scripts/
python e2e_simulation.py
```

### Output

Lo script genera:
- PDF di prova in una directory temporanea
- Report delle performance in formato CSV
- Log dettagliati delle operazioni

## Scenario Simulato

1. **Generazione Documenti**: Creazione di 10 PDF con testo nativo e 5 PDF "scansionati"
2. **Rilevamento Automatico**: Ogni PDF viene analizzato per determinare se è scansionato
3. **Routing Intelligente**: 
   - PDF nativi → Motore standard
   - PDF scansionati → Worker OCR via coda Redis
4. **Misurazione Performance**: Tempo di elaborazione, errori, bilanciamento del carico

## Metriche Monitorate

- Numero di documenti elaborati via motore standard
- Numero di documenti elaborati via OCR worker
- Tempo medio di elaborazione
- Tasso di errori
- Utilizzo della coda Redis

## Validazione dell'Architettura

La simulazione verifica che:

- Il rilevamento automatico di PDF scansionati funzioni correttamente
- Il routing verso i worker OCR sia efficiente
- Il motore principale rimanga reattivo durante l'elaborazione OCR
- La coda Redis gestisca correttamente il carico
- Le performance siano adeguate per scenari di produzione

## Integrazione con CI/CD

Lo script può essere integrato nella pipeline CI/CD per testare periodicamente:

- L'integrazione tra i diversi componenti
- Le performance di elaborazione
- La resilienza del sistema
- Il bilanciamento del carico

## Output di Esempio

```
🧪 Starting End-to-End Load Balancing Simulation...
📚 Generating mock PDF documents...
✅ Generated 10 native and 5 scanned PDFs
🔄 Running load balancing simulation...
✅ Processed via standard engine: native_00.pdf
✅ Processed via OCR: scanned_00.pdf
...

📊 Simulation Results:
  Native text PDFs processed: 10
  Scanned PDFs processed via OCR: 5
  Total errors: 0
  Average processing time: 3.24s
```

## Risultati Attesi

- Tutti i PDF nativi devono essere elaborati dal motore standard
- Tutti i PDF scansionati devono essere elaborati dai worker OCR
- Bassa incidenza di errori (< 5%)
- Tempi di elaborazione accettabili per entrambi i percorsi
- Nessun blocco del sistema durante l'elaborazione OCR