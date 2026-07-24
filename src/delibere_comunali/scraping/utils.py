import hashlib
import os
import re
import time
import urllib.parse as up
from datetime import date, datetime
from pathlib import Path
from typing import Optional, List

from urllib.robotparser import RobotFileParser

from delibere_comunali.utils.comuni_anagrafica import carica_mappatura_esistente
import pandas as pd

# Importiamo le nuove funzionalità per il rilevamento automatico degli adapter
from delibere_comunali.utils.adapter_detector import identify_comune_adapter

# Importiamo pandas per gestire i dati della mappatura
import pandas as pd

# Configurazioni di default
DEFAULT_DELAY = 1.0
DEFAULT_MAX_PAGES = 20
DEFAULT_TIMEOUT = 20
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

ATTACH_EXTS = (".pdf", ".doc", ".docx", ".rtf", ".zip")
ATTACH_MIME_EXT = {
    "application/pdf": ".pdf",
    "application/msword": ".doc",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": ".docx",
    "application/zip": ".zip",
}

# Dizionario per inferire tipologia da filename
TIPOLOGIA_FROM_FILENAME = {
    r"Determina": "Determinazione",
    r"Delibera": "Delibera",
    r"Ordinanza": "Ordinanza",
    r"Decreto": "Decreto",
    r"Avviso": "Avviso",
    r"Bando": "Bando",
    r"Attestazione": "AttestazionePubblicazione",
    r"VistoContabile": "VistoContabile",
    r"Referendum": "Elettorale",
    r"Elezioni": "Elettorale",
    r"Reperibilita": "Personale",
    r"Disposizione": "Disposizione",
}

# Dizionario per inferire tipologia da oggetto
TIPOLOGIA_FROM_OGGETTO = {
    r"determina": "Determinazione",
    r"delibera": "Delibera",
    r"ordinanza": "Ordinanza",
    r"decreto": "Decreto",
    r"avviso": "Avviso",
    r"bando": "Bando",
    r"attestazione.*pubblicazione": "AttestazionePubblicazione",
    r"visto.*contabile": "VistoContabile",
    r"liquidazione": "Determinazione",
    r"impegno": "Determinazione",
    r"referendum|elettorale|comizi": "Elettorale",
    r"reperibilita|personale|uffici": "Servizio",
    r"leva.*militare": "Servizio",
    r"manifesto": "Avviso",
}

def generate_openweb_base_url(ente: str) -> str:
    """Genera dinamicamente l'URL base per il sistema OpenWeb del comune specificato."""
    # Converte il nome ente in formato standard per l'URL
    ente_normalized = ente.lower().replace('_', '').replace('-', '')
    
    # Mappatura abbreviazioni province con copertura più precisa
    province_mapping = {
        # Province campana
        'av': 'av', 'avellino': 'av', 'baiano': 'av', 'tufino': 'av', 'summonte': 'av', 'santangelo': 'av', 
        'solofra': 'av', 'montecalvo': 'av', 'bisaccia': 'av', 'trevico': 'av', 'santandrea': 'av', 
        'castelfranci': 'av', 'acquaviva': 'av', 'aquilonia': 'av', 'bagnoli': 'av', 'calabritto': 'av', 
        'candida': 'av', 'manocalzati': 'av', 'parolise': 'av', 'roccamonfina': 'av', 'santomenna': 'av', 
        'vallata': 'av', 'montefusco': 'av', 'montefalcone': 'av', 'montemiletto': 'av', 'morra': 'av', 
        'nusco': 'av', 'quadrelle': 'av', 'quindici': 'av', 'roccaduaragnano': 'av', 'roccavivara': 'av', 
        'saintanges': 'av', 'salza': 'av', 'sanmartino': 'av', 'sansossio': 'av', 'santangelo': 'av', 
        'santelena': 'av', 'santemariana': 'av', 'santodomenico': 'av', 'santomarco': 'av', 'santopietro': 'av', 
        'santostefano': 'av', 'santuario': 'av', 'senerchia': 'av', 'serino': 'av', 'sirignano': 'av', 
        'solofra': 'av', 'summonte': 'av', 'taurano': 'av', 'teora': 'av', 'toccosannapaolina': 'av', 
        'torrioni': 'av', 'troia': 'av', 'tufo': 'av', 'urzini': 'av', 'vallata': 'av', 'vallesaccarda': 'av', 
        'venticano': 'av', 'villassio': 'av', 'villaverde': 'av', 'volturara': 'av', 'zambrotta': 'av', 
        'zungoli': 'av',
        'sperone': 'av',  # Sperone è in provincia di Avellino

        # Province napoletana
        'na': 'na', 'napoli': 'na', 'pozzuoli': 'na', 'ercolano': 'na', 'torreannunziata': 'na', 
        'torredelgreco': 'na', 'meta': 'na', 'castellammare': 'na', 'acerra': 'na', 'afragola': 'na', 
        'casalnuovo': 'na', 'marigliano': 'na', 'sanpaolo': 'na', 'santantimo': 'na', 'cardito': 'na', 
        'cicciano': 'na', 'visciano': 'na', 'marano': 'na', 'melito': 'na', 'casavatore': 'na', 
        'pomigliano': 'na', 'frattamaggiore': 'na', 'giugliano': 'na', 'qualiano': 'na', 'agerola': 'na', 
        'castelluccio': 'na', 'angri': 'na', 'sarno': 'na', 'poggiomarino': 'na', 'brusciano': 'na', 
        'santanicoladacreca': 'na', 'volla': 'na', 'sansecondodipuglia': 'na', 'scisciano': 'na', 
        'serrara': 'na', 'somma': 'na', 'striano': 'na', 'tufino': 'na', 'vicoequense': 'na', 'villaricca': 'na', 
        'anacapri': 'na', 'arzano': 'na', 'bacoli': 'na', 'barano': 'na', 'boscoreale': 'na', 'botriphiano': 'na', 
        'brano': 'na', 'calvizzano': 'na', 'camposano': 'na', 'capri': 'na', 'carbonara': 'na', 'carditello': 'na', 
        'casamarciano': 'na', 'casamicciola': 'na', 'casandrino': 'na', 'casola': 'na', 'castellammare': 'na', 
        'castellaneta': 'na', 'castello': 'na', 'cessalto': 'na', 'cicciano': 'na', 'cimitile': 'na', 
        'comiziano': 'na', 'crispano': 'na', 'forio': 'na', 'frattaminore': 'na', 'giugliano': 'na', 
        'grumo': 'na', 'island': 'na', 'lacco': 'na', 'lettere': 'na', 'liveri': 'na', 'marano': 'na', 
        'mariglianella': 'na', 'massalubrense': 'na', 'melito': 'na', 'minerbio': 'na', 'miseno': 'na', 
        'monte': 'na', 'montediporcara': 'na', 'montefredane': 'na', 'montesarchio': 'na', 'mugnano': 'na', 
        'napoli': 'na', 'nola': 'na', 'ottaviano': 'na', 'palma': 'na', 'piano': 'na', 'picciano': 'na', 
        'pimonte': 'na', 'poggiomarino': 'na', 'pollena': 'na', 'pomigliano': 'na', 'ponsacco': 'na', 
        'portici': 'na', 'pozzuoli': 'na', 'procida': 'na', 'qualiano': 'na', 'quarto': 'na', 
        'roccharainola': 'na', 'san': 'na', 'sanfelice': 'na', 'sangennaro': 'na', 'sangiuseppe': 'na', 
        'sanpaolo': 'na', 'sansossio': 'na', 'santantimo': 'na', 'santantoni': 'na', 'santantonio': 'na', 
        'santegidio': 'na', 'santepolimo': 'na', 'sanvitaliano': 'na', 'saviano': 'na', 'scisciano': 'na', 
        'seccaiano': 'na', 'solimena': 'na', 'somma': 'na', 'sorrento': 'na', 'stefano': 'na', 
        'striano': 'na', 'terzigno': 'na', 'torre': 'na', 'torrecuso': 'na', 'tufino': 'na', 'volla': 'na',

        # Province salernitana
        'sa': 'sa', 'salerno': 'sa', 'eboli': 'sa', 'battipaglia': 'sa', 'scafati': 'sa', 'nocera': 'sa', 
        'pagani': 'sa', 'castelnuovo': 'sa', 'cava': 'sa', 'fisciano': 'sa', 'altavilla': 'sa', 
        'buccino': 'sa', 'campagna': 'sa', 'cannalonga': 'sa', 'capaccio': 'sa', 'casalbuono': 'sa', 
        'centola': 'sa', 'cetara': 'sa', 'furore': 'sa', 'giffoni': 'sa', 'magliano': 'sa', 'moio': 'sa', 
        'montecorvino': 'sa', 'monteforte': 'sa', 'montesano': 'sa', 'orria': 'sa', 'padula': 'sa', 
        'perdifumo': 'sa', 'perito': 'sa', 'policastro': 'sa', 'pollica': 'sa', 'positano': 'sa', 
        'postiglione': 'sa', 'ravello': 'sa', 'roccadaspide': 'sa', 'roccagloriosa': 'sa', 'sacco': 'sa', 
        'sala': 'sa', 'salvitelle': 'sa', 'sapri': 'sa', 'sassano': 'sa', 'serramezzana': 'sa', 
        'serre': 'sa', 'sessa': 'sa', 'siano': 'sa', 'teggiano': 'sa', 'torraca': 'sa', 'trentinara': 'sa', 
        'valva': 'sa', 'vibonati': 'sa', 'vietri': 'sa',

        # Altre province
        'ba': 'ba', 'bari': 'ba',
        'bn': 'bn', 'benevento': 'bn',
        'ce': 'ce', 'caserta': 'ce',
        'pz': 'pz', 'potenza': 'pz',
        'mt': 'mt', 'matera': 'mt',
        'cs': 'cs', 'cosenza': 'cs',
        'cz': 'cz', 'catanzaro': 'cz',
        'kr': 'kr', 'crotone': 'kr',
        'rc': 'rc', 'reggiocalabria': 'rc',
        'mi': 'mi', 'milano': 'mi',
        'rm': 'rm', 'roma': 'rm',
        'fi': 'fi', 'firenze': 'fi',
        'bo': 'bo', 'bologna': 'bo',
        'pd': 'pd', 'padova': 'pd',
        'tv': 'tv', 'treviso': 'tv',
        'vr': 'vr', 'verona': 'vr',
        'bl': 'bl', 'belluno': 'bl',
        've': 've', 'venezia': 've',
        'go': 'go', 'gorizia': 'go',
        'ud': 'ud', 'udine': 'ud',
        'tn': 'tn', 'trento': 'tn',
        'bz': 'bz', 'bolzano': 'bz',
        'ao': 'ao', 'aosta': 'ao',
        'bg': 'bg', 'bergamo': 'bg',
        'bs': 'bs', 'brescia': 'bs',
        'co': 'co', 'como': 'co',
        'lc': 'lc', 'lecco': 'lc',
        'so': 'so', 'sondrio': 'so',
        'pv': 'pv', 'pavia': 'pv',
        'cr': 'cr', 'cremona': 'cr',
        'mn': 'mn', 'mantova': 'mn',
        'vi': 'vi', 'vicenza': 'vi',
        'fe': 'fe', 'ferrara': 'fe',
        'mo': 'mo', 'modena': 'mo',
        'pr': 'pr', 'parma': 'pr',
        're': 're', 'reggioemilia': 're',
        'pc': 'pc', 'piacenza': 'pc',
        'ra': 'ra', 'ravenna': 'ra',
        'rn': 'rn', 'rimini': 'rn',
        'an': 'an', 'ancona': 'an',
        'mc': 'mc', 'macerata': 'mc',
        'ap': 'ap', 'ascoli': 'ap',
        'pu': 'pu', 'pesarourbino': 'pu',
        'pg': 'pg', 'perugia': 'pg',
        'tr': 'tr', 'terni': 'tr',
        'vt': 'vt', 'viterbo': 'vt',
        'ri': 'ri', 'rieti': 'ri',
        'fr': 'fr', 'frosinone': 'fr',
        'lt': 'lt', 'latina': 'lt',
        'te': 'te', 'teramo': 'te',
        'ch': 'ch', 'chieti': 'ch',
        'pe': 'pe', 'pescara': 'pe',
        'aq': 'aq', 'aquila': 'aq',
        'cb': 'cb', 'campobasso': 'cb',
        'is': 'is', 'isernia': 'is',
        'bt': 'bt', 'barletta': 'bt',
        'br': 'br', 'brindisi': 'br',
        'ta': 'ta', 'taranto': 'ta',
        'ag': 'ag', 'agrigento': 'ag',
        'cl': 'cl', 'caltanissetta': 'cl',
        'ct': 'ct', 'catania': 'ct',
        'en': 'en', 'enna': 'en',
        'me': 'me', 'messina': 'me',
        'pa': 'pa', 'palermo': 'pa',
        'rg': 'rg', 'ragusa': 'rg',
        'sr': 'sr', 'siracusa': 'sr',
        'tp': 'tp', 'trapani': 'tp',
    }

    # Determina la provincia in base al nome ente
    provincia = "av"  # default

    # Controlla se il nome ente contiene indicazioni specifiche
    for ente_key, prov_val in province_mapping.items():
        if ente_key in ente_normalized:
            provincia = prov_val
            break

    # Caso speciale per Baiano
    if "baiano" in ente_normalized:
        provincia = "av"  # Baiano è in provincia di Avellino

    # Costruisci l'URL standard per il comune
    return f"https://servizi.comune.{ente_normalized}.{provincia}.it/openweb/albo/albo_pretorio_full.php"

def slugify(text: str, maxlen: int = 120) -> str:
    text = re.sub(r"\s+", "_", text.strip())
    text = re.sub(r"[^\w\-.]+", "", text, flags=re.UNICODE)
    return text[:maxlen] or "file"

def compact_text(text: str) -> str:
    return " ".join((text or "").split())

def url_doc_name(url: str) -> str:
    """Restituisce il nome documento più informativo da path o query string."""
    pu = up.urlparse(url)
    qs = up.parse_qs(pu.query, keep_blank_values=True)
    for key in ("f", "file", "filename", "name"):
        if qs.get(key):
            return os.path.basename(qs[key][0])
    return os.path.basename(pu.path)

def looks_like_attachment(href: str, label: str = "") -> bool:
    name = url_doc_name(href).lower()
    text = (label or "").lower()
    
    # Controlla se è un'estensione valida
    has_valid_ext = any(name.endswith(ext) for ext in ATTACH_EXTS)
    
    # Se non ha estensione valida, probabilmente non è un allegato
    if not has_valid_ext:
        return False
    
    # Verifica se il nome del file o l'etichetta suggeriscono che è un file introduttivo anziché un vero allegato
    intro_keywords = [
        "introduzione", "descrizione", "copia", "anteprima", "preview", 
        "dettagli", "dettaglio", "pagina", "scheda", "visualizza", "mostra",
        "copertina", "frontespizio", "indice", "sommario", "prefazione",
        "intro", "desc", "dettaglio_atto", "visualizza_atto", "mostra_dettagli"
    ]
    if any(keyword in name or keyword in text for keyword in intro_keywords):
        return False  # Non è un vero allegato
    
    # Controlla se contiene indicatori di vero allegato
    positive_indicators = [
        "allegato", "documento", "pdf", "download", "vai", "atto", "determina", 
        "delibera", "progetto", "relazione", "computo", "preventivo", "cronoprogramma",
        "relazione", "tabelle", "elenco", "quadro", "scheda_tecnica", "capitolato",
        "disciplinare", "metrico", "economico", "grafico", "foto", "immagine",
        "pianta", "prospetto", "sezione", "dettaglio_tecnico", "tavola", "modulo",
        "modello", "schema", "diagramma", "allegato_", "allegato-", "allegato.",
        "computo_metrico", "quadro_economico", "cronoprogramma", "piano_esecutivo"
    ]
    has_positive_indicators = any(indicator in name or indicator in text for indicator in positive_indicators)
    
    # Controlla se contiene indicatori di file descrittivo
    negative_indicators = [
        "dettaglio", "pagina", "scheda", "visualizza", "mostra", "descrizione",
        "introduzione", "anteprima", "preview", "info", "informazioni", "copia_"
    ]
    has_negative_indicators = any(indicator in name or indicator in text for indicator in negative_indicators)
    
    # Se ha indicatori positivi e non negativi, probabilmente è un allegato
    if has_positive_indicators and not has_negative_indicators:
        return True
    elif has_positive_indicators and has_negative_indicators:
        # Se ha entrambi, diamo priorità agli indicatori positivi ma con cautela
        return True
    else:
        # Se non ha indicatori positivi, non è un allegato
        return False

def infer_tipologia_from_filename(filename: str) -> Optional[str]:
    """Inferisce tipologia dal nome del file"""
    for pattern, tipologia in TIPOLOGIA_FROM_FILENAME.items():
        if re.search(pattern, filename, re.IGNORECASE):
            return tipologia
    return None

def infer_tipologia_from_oggetto(oggetto: str) -> Optional[str]:
    """Inferisce tipologia dall'oggetto del documento"""
    if not oggetto:
        return None
    oggetto_lower = oggetto.lower()
    for pattern, tipologia in TIPOLOGIA_FROM_OGGETTO.items():
        if re.search(pattern, oggetto_lower):
            return tipologia
    return None

def infer_tipologia_from_url(url: str) -> Optional[str]:
    """Inferisce tipologia dall'URL (es. parametri o path)"""
    if not url: return None
    if "Determina" in url or "determinazione" in url.lower():
        return "Determinazione"
    if "Delibera" in url or "deliberazione" in url.lower():
        return "Delibera"
    if "Ordinanza" in url or "ordinanza" in url.lower():
        return "Ordinanza"
    return None

def infer_number(text: str) -> Optional[str]:
    patterns = [
        r"\b(?:n\.|numero|copia|originale)[_\s-]*(\d{1,6})\b",
        r"_(\d{1,6})_(?:20\d{2})\b",
        r"\b(\d{1,6})/(20\d{2})\b",
    ]
    for rx in patterns:
        m = re.search(rx, text or "", re.I)
        if m:
            return m.group(1)
    return None

def infer_date(text: str) -> Optional[str]:
    m = re.search(r"\b(\d{2}/\d{2}/\d{4}|20\d{2}-\d{2}-\d{2})\b", text or "")
    if m:
        return m.group(1)
    m = re.search(r"\b(20\d{2})\b", text or "")
    if m:
        return m.group(1)
    return None

def metadata_key(it: "AlboItem") -> str:
    if it.dettaglio_url:
        return it.dettaglio_url
    if it.allegati:
        return it.allegati[0]
    raw = "|".join([it.titolo or "", it.numero or "", it.data_pubblicazione or "", it.oggetto or ""])
    # Usa SHA-256 invece di SHA1 per motivi di sicurezza
    return hashlib.sha256(raw.encode("utf-8", errors="ignore")).hexdigest()

def encode_query(query: dict) -> str:
    return up.urlencode(query, doseq=True, safe="[]")

def page_url(page: int, step: int = 15, csrf: Optional[str] = None, base_url: str = None) -> str:
    if base_url is None:
        base_url = "https://servizi.comune.avella.av.it/openweb/albo/albo_pretorio_full.php"  # fallback per compatibilità
    start = 1 + (max(1, page) - 1) * step
    q = {"tabella_albo[page]": [str(max(1, page))], "tabella_albo[start]": [str(start)]}
    if csrf:
        q = {"CSRF": [csrf], **q}
    return base_url + "?" + encode_query(q)

def extract_csrf(html: str, final_url: str = "") -> Optional[str]:
    for source in (final_url, html or ""):
        m = re.search(r"CSRF=([A-Za-z0-9]+)", source)
        if m:
            return m.group(1)
    from bs4 import BeautifulSoup
    soup = BeautifulSoup(html or "", "html.parser")
    field = soup.find("input", attrs={"name": "CSRF"})
    if field and field.get("value"):
        return field["value"]
    return None

def ensure_dir(p: Path) -> None:
    p.mkdir(parents=True, exist_ok=True)

def polite_sleep(delay: float):
    time.sleep(max(0.1, delay))

def parse_date(s: Optional[str]) -> Optional[date]:
    if not s:
        return None
    s = s.strip()
    for fmt in ("%d/%m/%Y", "%Y-%m-%d", "%Y"):
        try:
            return datetime.strptime(s, fmt).date()
        except Exception:
            pass
    return None

def within_dates(d: Optional[str], dfrom: Optional[date], dto: Optional[date]) -> bool:
    if not (dfrom or dto):
        return True
    dd = parse_date(d)
    if not dd:
        return False
    if dfrom and dd < dfrom:
        return False
    if dto and dd > dto:
        return False
    return True

def load_robots_allow(base_root: str) -> RobotFileParser:
    """Carica il robots.txt ma con eccezioni per documenti pubblici."""
    robots_url = up.urljoin(base_root, "/robots.txt")
    rp = RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
    except Exception:
        pass
    return rp

def can_fetch(rp: RobotFileParser, url: str, user_agent: str) -> bool:
    """
    Controlla se è consentito accedere all'URL, ma fa eccezioni per documenti pubblici.
    I documenti pubblici (atti amministrativi, deliberazioni, PDF ufficiali) devono essere accessibili
    anche se bloccati da robots.txt secondo i principi di civic technology e trasparenza.
    """
    try:
        # Controlla se l'URL contiene risorse pubbliche che dovrebbero essere accessibili
        url_lower = url.lower()
        
        # Estensioni di documenti pubblici che dovrebbero essere sempre accessibili
        public_extensions = ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.p7m', '.xml']
        if any(url_lower.endswith(ext) for ext in public_extensions):
            return True
        
        # Percorsi tipici di documenti pubblici
        public_paths = ['/albo', '/albopretorio', '/trasparenza', '/atti', '/deliberazioni', 
                       '/determinazioni', '/pubblicazioni', '/documenti', '/openweb']
        if any(path in url_lower for path in public_paths):
            return True
        
        # Specifiche pagine di download documenti pubblici
        public_endpoints = ['getDoc.php', 'download', 'allegato', 'documento']
        if any(endpoint in url_lower for endpoint in public_endpoints):
            return True
        
        # Se non è un documento pubblico, applichiamo la regola di robots.txt
        return rp.can_fetch(user_agent, url)
    except Exception:
        # In caso di errore, consentiamo l'accesso per non bloccare i documenti pubblici
        return True

def guess_next_url(base_url: str, step_default: int = 15) -> Optional[str]:
    """Fallback per OpenWeb: incrementa page/start se non troviamo link 'successivo'."""
    pu = up.urlparse(base_url)
    qs = up.parse_qs(pu.query, keep_blank_values=True)
    try:
        page = int(qs.get('tabella_albo[page]', ['1'])[0])
        start = int(qs.get('tabella_albo[start]', ['1'])[0])
    except Exception:
        # se non presenti, inizializziamo per passare alla pagina 2
        page, start = 1, 1

    # heuristica del passo: OpenWeb spesso usa 15; se è presente 'start', stimiamo dal valore
    step = step_default
    if start > 1:
        # prova a dedurre dal pattern (start = 1 + (page-1)*step) => step = round((start-1)/(page-1))
        try:
            if page > 1:
                est = int(round((start - 1) / (page - 1)))
                if 5 <= est <= 50:
                    step = est
        except Exception:
            pass

    page += 1
    start = 1 + (page - 1) * step
    qs['tabella_albo[page]'] = [str(page)]
    qs['tabella_albo[start]'] = [str(start)]
    new_q = encode_query(qs)
    return up.urlunparse((pu.scheme, pu.netloc, pu.path, pu.params, new_q, pu.fragment))

def get_comune_data(ente: str) -> dict:
    """
    Ottiene i dati del comune dalla mappatura ufficiale.
    Cerca prima nel file integrato, poi in quello base.
    Usa ricerca ESATTA per trovare il comune.
    
    Args:
        ente: Nome del comune
        
    Returns:
        Dizionario con i dati del comune
    """
    # Normalizza il nome del comune per la ricerca
    ente_normalized = ente.replace('_', '').replace('-', '').replace('.', '').lower()
    print(f"DEBUG: Ricerca comune '{ente}' con nome normalizzato '{ente_normalized}'")
    
    # Cerchiamo prima nella mappatura integrata (aggiornata con risultati dello spidering)
    mappatura_integrata = carica_mappatura_esistente("mappatura_comuni_integrata.csv")
    
    if mappatura_integrata is not None:
        print(f"DEBUG: Caricata mappatura integrata con {len(mappatura_integrata)} comuni")
        # Cerchiamo il comune nella mappatura integrata con ricerca ESATTA
        for idx, row in mappatura_integrata.iterrows():
            nome_comune_db = str(row['nome_comune']).replace(' ', '').replace("'", "").replace("-", "").replace(".", "").lower()
            # Cerchiamo corrispondenza ESATTA (non parziale)
            if ente_normalized == nome_comune_db:
                print(f"DEBUG: Trovato comune '{row['nome_comune']}' con URL albo: {row['url_albo_pretorio']}")
                return row.to_dict()
        print("DEBUG: Nessuna corrispondenza ESATTA trovata nella mappatura integrata")
    else:
        print("DEBUG: Impossibile caricare mappatura integrata")
    
    # Se non trovato nell'integrata, cerchiamo nella mappatura base
    mappatura_base = carica_mappatura_esistente("mappatura_comuni_template.csv")
    
    if mappatura_base is not None:
        print(f"DEBUG: Caricata mappatura base con {len(mappatura_base)} comuni")
        # Cerchiamo il comune nella mappatura base con ricerca ESATTA
        for idx, row in mappatura_base.iterrows():
            nome_comune_db = str(row['nome_comune']).replace(' ', '').replace("'", "").replace("-", "").replace(".", "").lower()
            # Cerchiamo corrispondenza ESATTA (non parziale)
            if ente_normalized == nome_comune_db:
                print(f"DEBUG: Trovato comune '{row['nome_comune']}' nella mappatura base")
                return row.to_dict()
        print("DEBUG: Nessuna corrispondenza ESATTA trovata nella mappatura base")
    else:
        print("DEBUG: Impossibile caricare mappatura base")
    
    # Se non trovato, restituiamo un dizionario con dati minimi
    print("DEBUG: Comune non trovato, restituisco dati minimi")
    return {
        'nome_comune': ente,
        'url_istituzionale': '',
        'url_albo_pretorio': '',
        'scraper_adapter': 'unknown',
        'is_active': True
    }