import re

# Legge il file
with open('src/delibere_comunali/scraping/new_albo_scraper.py', 'r', encoding='utf-8') as file:
    content = file.read()

# Definisce la nuova logica per il controllo dei duplicati
new_logic = '''                    # Salta l'atto se è già stato scaricato e indicizzato in precedenza
                    # MA SOLO SE anche i file PDF esistono fisicamente
                    skip_item = False
                    if it.dettaglio_url and it.dettaglio_url in self.seen_metadata:
                        # Verifichiamo se esistono file PDF associati a questo documento
                        pdf_exists = False
                        
                        # Controlliamo se esistono PDF con nomi basati sugli allegati
                        for allegato_url in it.allegati or []:
                            filename = up.urlparse(allegato_url).path.split('/')[-1]
                            if filename:  # Assicuriamoci che il filename non sia vuoto
                                pdf_path = self.out_dir / "pdf" / filename
                                if pdf_path.exists():
                                    pdf_exists = True
                                    break
                        
                        # Se non abbiamo ancora verificato con allegati, controlliamo comunque
                        # se esiste un file basato sull'ID del documento
                        if not pdf_exists and it.dettaglio_url:
                            # Estrai l'ID dal dettaglio URL (es. id=49804)
                            from urllib.parse import parse_qs
                            parsed_url = up.urlparse(it.dettaglio_url)
                            params = parse_qs(parsed_url.query)
                            doc_ids = params.get('id', [])
                            
                            # Controlliamo tutti gli ID trovati nell'URL
                            for doc_id in doc_ids:
                                if doc_id:
                                    # Cerchiamo file PDF che contengano l'ID del documento
                                    import os
                                    for filename in os.listdir(self.out_dir / "pdf"):
                                        if filename.endswith('.pdf') and doc_id in filename:
                                            pdf_exists = True
                                            break
                                    if pdf_exists:
                                        break
                        
                        # Solo se troviamo file PDF associati, consideriamo il documento come realmente archiviato
                        if pdf_exists:
                            skip_item = True
                    
                    if skip_item:
                        self.log(f"  [skip] Già in archivio: {it.dettaglio_url}")
                        continue'''

# Sostituisce la vecchia logica con la nuova
content = re.sub(
    r'# Salta l\'atto se è già stato scaricato e indicizzato in precedenza\s+if it\.dettaglio_url and it\.dettaglio_url in self\.seen_metadata:\s+self\.log\(f"  \[skip\] Già in archivio: {it\.dettaglio_url}"\)\s+continue',
    new_logic,
    content
)

# Scrive il file modificato
with open('src/delibere_comunali/scraping/new_albo_scraper.py', 'w', encoding='utf-8') as file:
    file.write(content)

print("Modifica completata!")