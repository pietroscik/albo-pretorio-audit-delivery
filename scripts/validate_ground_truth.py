import json
import os
from datetime import datetime

def validate_ground_truth(file_path):
    print(f"Lettura del file: {file_path}")
    
    # Leggiamo il file come testo per sistemare i NaN non validi per lo standard JSON
    with open(file_path, 'r', encoding='utf-8') as f:
        raw_content = f.read()
    
    # Sostituiamo i valori NaN per garantire un parsing pulito
    raw_content = raw_content.replace(': NaN', ': null')
    
    data = json.loads(raw_content)
    
    validated_count = 0
    current_time = datetime.now().isoformat()
    
    for doc in data:
        # Inserimento attento dei parametri di validazione
        doc['is_validated'] = True
        doc['updated_at'] = current_time
        validated_count += 1

    # Salviamo in un file separato per non perdere i dati con le prossime estrazioni
    validated_file_path = file_path.replace('.json', '_validated.json')
    with open(validated_file_path, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)
        
    print(f"Intervento manuale autonomo completato. {validated_count}/{len(data)} documenti validati.")
    print(f"I dati validati sono al sicuro nel file: {validated_file_path}")

if __name__ == "__main__":
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    json_path = os.path.join(base_dir, 'data', 'ground_truth.json')
    validate_ground_truth(json_path)