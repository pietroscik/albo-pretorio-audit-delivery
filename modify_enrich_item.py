import re

with open('src/delibere_comunali/scraping/new_albo_scraper.py', 'r', encoding='utf-8') as file:
    content = file.read()

# Sostituiamo la chiamata ripetuta con l'uso del dato già caricato
content = content.replace(
    """        if not it.provincia and self.args.ente:
            # Cerca di determinare la provincia dal nome dell'ente
            comune_data = get_comune_data(self.args.ente)
            if comune_data and 'provincia' in comune_data:
                it.provincia = comune_data['provincia']""",
    """        if not it.provincia and hasattr(self, 'comune_data'):
            # Usa i dati del comune già caricati nel costruttore
            comune_data = self.comune_data
            if comune_data and 'provincia' in comune_data:
                it.provincia = comune_data['provincia']"""
)

with open('src/delibere_comunali/scraping/new_albo_scraper.py', 'w', encoding='utf-8') as file:
    file.write(content)

print("Modifica completata!")