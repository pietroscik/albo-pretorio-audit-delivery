import os
from pathlib import Path
import hashlib
from collections import defaultdict
import pypdfium2 as pdfium

# Leggo tutti i file PDF nella cartella
pdf_dir = Path('data/baiano/albo_download/pdf')
pdf_files = list(pdf_dir.glob('*.pdf')) + list(pdf_dir.glob('*.PDF'))

# Calcoliamo l'hash del testo estratto da ogni file
text_hashes = {}
hash_to_files = defaultdict(list)

# Analizzo tutti i file PDF disponibili
for i, pdf_file in enumerate(pdf_files):
    try:
        pdf = pdfium.PdfDocument(pdf_file)
        text = ''
        for page in pdf:
            text_page = page.get_textpage()
            text += text_page.get_text_range()
            text_page.close()
        pdf.close()

        # Normalizziamo il testo come fa il sistema
        text = text.replace('\n', ' ').replace('\r', ' ').strip()
        text_hash = hashlib.sha256(text.encode('utf-8')).hexdigest()
        
        text_hashes[pdf_file.name] = text_hash
        hash_to_files[text_hash].append(pdf_file.name)
    except Exception as e:
        print('Errore nell\'estrazione del testo da {}: {}'.format(pdf_file, e))

print('Totale file PDF analizzati: {}'.format(len(text_hashes)))
print('Hash testuali univoci: {}'.format(len(hash_to_files)))

# Troviamo i duplicati basati sul testo estratto
duplicates = {h: files for h, files in hash_to_files.items() if len(files) > 1}
print('Gruppi di file con lo stesso testo: {}'.format(len(duplicates)))

if duplicates:
    print('\nEsempi di file con lo stesso testo estratto:')
    for i, (hash_val, files) in enumerate(list(duplicates.items())[:10]):
        print('\nGruppo {} (hash: {}...):'.format(i+1, hash_val[:10]))
        for file in files:
            print('  - {}'.format(file))
else:
    print('\nNessun duplicato trovato nei file analizzati.')

# Riporto i risultati principali
print('\n--- RIEPILOGO ANALISI DEI DUPLICATI ---')
print('File PDF totali: {}'.format(len(pdf_files)))
print('File con testo univoco: {}'.format(len(hash_to_files)))
print('File identificati come duplicati: {}'.format(len(pdf_files) - len(hash_to_files)))
print('Percentuale di duplicati: {:.2f}%'.format(((len(pdf_files) - len(hash_to_files)) / len(pdf_files)) * 100 if len(pdf_files) > 0 else 0))