# script: update_imports.py
import os
import re
from pathlib import Path

root = Path("src/delibere_comunali")

# Mappa vecchi import -> nuovi import
import_map = {
    r'^from logger import': 'from delibere_comunali.utils.logger import',
    r'^from metrics import': 'from delibere_comunali.utils.metrics import',
    r'^from config import': 'from delibere_comunali.utils.config import',
    r'^from exceptions import': 'from delibere_comunali.utils.exceptions import',
    r'^from cache import': 'from delibere_comunali.utils.cache import',
    r'^from validation_utils import': 'from delibere_comunali.utils.validation_utils import',
    r'^from enhanced_extractor import': 'from delibere_comunali.parsing.enhanced_extractor import',
    r'^from llm_factory import': 'from delibere_comunali.rag.llm_factory import',
    r'^from online_comprehension_strategy import': 'from delibere_comunali.rag.online_comprehension_strategy import',
    r'^import logger': 'from delibere_comunali.utils import logger',
    r'^import metrics': 'from delibere_comunali.utils import metrics',
    r'^import config': 'from delibere_comunali.utils import config',
    r'^import exceptions': 'from delibere_comunali.utils import exceptions',
    r'^import cache': 'from delibere_comunali.utils import cache',
}

def update_file(filepath: Path):
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    original = content
    for old, new in import_map.items():
        content = re.sub(old, new, content)

    if content != original:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Updated: {filepath}")

# Aggiorna tutti i file Python in src/
for py_file in root.rglob("*.py"):
    update_file(py_file)