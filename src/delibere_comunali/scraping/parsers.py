import re
from typing import Tuple, List, Optional

from bs4 import BeautifulSoup
import urllib.parse as up

from .models import AlboItem

# Regex costants
TIPO_RX = re.compile(r"\b(delibera|determinazione|ordinanza|avviso|bando)\b", re.I)
NUM_RX = re.compile(r"\b(n\.|numero)\s*[:\s]*([0-9/]+)", re.I)
DATA_RX = re.compile(r"\b(pubblicazione|affissione|dal|data)\s*[:\s]*([0-9]{2}/[0-9]{2}/[0-9]{4}|[0-9]{4}-[0-9]{2}-[0-9]{2})", re.I)

def compact_text(text: str) -> str:
    """Funzione helper per compattare il testo."""
    return " ".join((text or "").split())

def parse_list_page(html: str, base_url: str) -> Tuple[List[AlboItem], Optional[str]]:
    soup = BeautifulSoup(html, "html.parser")
    items: List[AlboItem] = []

    rows = soup.select("table tr")
    if not rows:
        rows = soup.select("div.risultato, div.elenco, li")

    for r in rows:
        a = r.find("a", href=True)
        if not a:
            continue
        href = up.urljoin(base_url, a["href"])
        
        # Scorporiamo la riga nelle sue celle (<td>)
        tds = r.find_all("td")
        
        titolo_val = ""
        oggetto_val = ""
        ufficio_val = ""
        numero_val = None
        data_val = None
        tipologia_val = None

        if len(tds) >= 4:
            # Estraiamo il testo pulito da ogni colonna
            colonne = [td.get_text(separator=" ", strip=True) for td in tds]
            row_text = " ".join(colonne)
            
            # 1. L'Oggetto è quasi sempre la colonna con più testo
            oggetto_val = max(colonne, key=len)
            titolo_val = oggetto_val[:150] + ("..." if len(oggetto_val) > 150 else "")
            
            # 2. Pulizia dell'Ufficio
            for col in colonne:
                if "Ufficio" in col or "Area" in col or "Settore" in col:
                    ufficio_val = col.replace("|", "").strip()
                    break
                    
            # 3. Estrazione Data (cerchiamo formato GG/MM/AAAA)
            m_data = DATA_RX.search(row_text) or re.search(r"\b(\d{2}/\d{2}/\d{4})\b", row_text)
            if m_data:
                data_val = m_data.group(1) if len(m_data.groups()) == 1 else m_data.group(2)
                
            # 4. Estrazione Numero (cerchiamo es. "123 / 2025" o "N. 123")
            m_num = re.search(r"\b(\d+)\s*/\s*20\d{2}\b", row_text) or NUM_RX.search(row_text)
            if m_num:
                numero_val = m_num.group(1) if len(m_num.groups()) == 1 else m_num.group(2)
                
            # 5. Tipologia
            from .utils import infer_tipologia_from_url
            tipologia_val = infer_tipologia_from_url(href)
            if not tipologia_val:
                m_tip = TIPO_RX.search(row_text)
                if m_tip:
                    tip_val = m_tip.group(1).capitalize()
                    tipologia_val = "Determinazione" if tip_val == "Determina" else tip_val
        else:
            # Fallback per righe anomale senza colonne standard
            row_text = " ".join((r.get_text(separator=" | ") or "").split())
            oggetto_val = re.sub(r"\bVai\b", "", row_text, flags=re.I).strip(" |")
            titolo_val = oggetto_val[:150]

        # Creiamo il record pulito
        item = AlboItem(
            page_url=base_url,
            titolo=titolo_val if titolo_val else "Senza titolo",
            numero=numero_val,
            data_pubblicazione=data_val,
            tipologia=tipologia_val,
            ufficio=ufficio_val,
            oggetto=oggetto_val,
            dettaglio_url=href,
        )
        items.append(item)

    # Link "successivo" per la paginazione
    a_next = soup.find("a", rel=lambda v: v and "next" in v.lower())
    if a_next and a_next.get("href"):
        return items, up.urljoin(base_url, a_next["href"])

    for c in soup.find_all("a", string=re.compile(r"(successiva|successivo|pagina successiva|avanti|>)", re.I)):
        if c.get("href"):
            return items, up.urljoin(base_url, c["href"])

    for a in soup.select("a"):
        txt = (a.get_text() or "").strip()
        if txt in (">", "»", ">>") and a.get("href"):
            return items, up.urljoin(base_url, a["href"])

    from .utils import guess_next_url
    return items, guess_next_url(base_url)

def parse_detail_page(html: str, base_url: str) -> Tuple[Optional[str], Optional[str], List[str]]:
    soup = BeautifulSoup(html, "html.parser")
    text = compact_text(soup.get_text(separator=" | "))

    ogg = None
    m_ogg = re.search(
        r"\b(?:oggetto|titolo)\b\s*[:|]\s*(.+?)(?=\s*\|\s*(?:ufficio|settore|area|allegati?|pubblicazione|numero)\b|\s*$)",
        text,
        re.I,
    )
    if m_ogg:
        ogg = m_ogg.group(1).strip(" :-|")

    uff = None
    m_uff = re.search(
        r"\b(?:ufficio|settore|area)\b\s*[:|]\s*(.+?)(?=\s*\|\s*(?:oggetto|titolo|allegati?|pubblicazione|numero)\b|\s*$)",
        text,
        re.I,
    )
    if m_uff:
        uff = m_uff.group(1).strip(" :-|")

    allegati = []
    for a in soup.find_all("a", href=True):
        href = a["href"]
        label = compact_text(a.get_text(" "))
        from .utils import looks_like_attachment
        if looks_like_attachment(href, label):
            allegati.append(up.urljoin(base_url, href))

    if not allegati and base_url.lower().endswith(".pdf"):
        allegati.append(base_url)

    # dedup
    seen = {}
    out = []
    for u in allegati:
        if u not in seen:
            seen[u] = 1
            out.append(u)
    return ogg, uff, out