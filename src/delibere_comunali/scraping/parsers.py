import re
from typing import Tuple, List, Optional
from pathlib import Path

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
    
    # Halleyweb-specific logic: Look for document links that might be handled by JavaScript
    # Check for elements containing "Documento" or "Allegato" text
    for element in soup.find_all(['a', 'span', 'div'], string=re.compile(r'(documento|allegato|pdf|scarica)', re.I)):
        parent = element.find_parent()
        # Look for clickable elements that might trigger downloads
        for a in parent.find_all('a', href=True) if parent else []:
            href = a['href']
            if 'javascript:' in href.lower():
                # For JavaScript links, we need to look for alternative download mechanisms
                # Look for onclick attributes that might contain the real download URL
                onclick_attr = a.get('onclick', '')
                if onclick_attr:
                    # Try to extract URL from onclick (common patterns in Italian systems)
                    matches = re.findall(r"['\"]([^'\"]*\.pdf[^'\"]*)['\"]", onclick_attr)
                    for match in matches:
                        if match.lower().endswith('.pdf') or 'pdf' in match.lower():
                            allegati.append(up.urljoin(base_url, match))
            else:
                allegati.append(up.urljoin(base_url, href))
    
    # Look for other potential attachment patterns in Halleyweb
    # Search for elements with specific classes or IDs commonly used in Halleyweb
    for a in soup.find_all("a", href=True):
        href = a["href"]
        label = compact_text(a.get_text(" "))
        
        # Check if this is a Halleyweb domain
        is_halleyweb = 'halleyweb' in base_url.lower()
        
        from .utils import looks_like_attachment
        if looks_like_attachment(href, label):
            allegati.append(up.urljoin(base_url, href))
        elif is_halleyweb:
            # Special handling for Halleyweb attachments
            # Look for links that might be document downloads despite JavaScript
            if ('documento' in label.lower() or 'allegato' in label.lower() or 
                'pdf' in label.lower() or '.pdf' in href.lower()):
                # Even if it's a javascript: link, we'll add the base URL for potential processing
                if 'javascript:' in href.lower():
                    # Look for alternative download methods in Halleyweb
                    # Sometimes there are direct links to getdoc.php or similar
                    onclick = a.get('onclick', '')
                    if onclick:
                        # Extract potential direct download URLs from onclick handlers
                        doc_matches = re.findall(r"['\"]([^'\"]*(?:getdoc|download|pdf)[^'\"]*\.(?:php|pdf|doc|docx|zip|p7m))['\"]", onclick, re.I)
                        for match in doc_matches:
                            allegati.append(up.urljoin(base_url, match))
                else:
                    allegati.append(up.urljoin(base_url, href))
    
    # Fallback: Look for any potential document links in Halleyweb
    if 'halleyweb' in base_url.lower():
        # Look for table rows or divs that contain document-related information
        for element in soup.find_all(['tr', 'div', 'td'], string=re.compile(r'documento|allegato', re.I)):
            parent = element.find_parent()
            # Look for links in the same context
            if parent:
                for a in parent.find_all('a', href=True):
                    href = a['href']
                    label = compact_text(a.get_text(" "))
                    if ('documento' in label.lower() or 'allegato' in label.lower() or 
                        '.pdf' in href.lower() or 'pdf' in label.lower()):
                        if 'javascript:' in href.lower():
                            # Try to extract from onclick
                            onclick = a.get('onclick', '')
                            if onclick:
                                doc_matches = re.findall(r"['\"]([^'\"]*(?:getdoc|download|pdf)[^'\"]*\.(?:php|pdf|doc|docx|zip|p7m))['\"]", onclick, re.I)
                                for match in doc_matches:
                                    allegati.append(up.urljoin(base_url, match))
                        else:
                            allegati.append(up.urljoin(base_url, href))
    
    # NEW: Enhanced Halleyweb detection - look for specific elements that indicate downloadable content
    # Look for elements with specific Halleyweb patterns
    if 'halleyweb' in base_url.lower():
        # Look for elements that are likely to be download triggers (not just links)
        for element in soup.find_all(['a', 'span', 'div', 'button'], attrs={'onclick': True}):
            onclick = element.get('onclick', '')
            text_content = compact_text(element.get_text())
            
            # Look for common Halleyweb download function patterns
            if any(pattern in onclick.lower() for pattern in ['scarica', 'download', 'getdoc', 'allegato', 'documento']):
                # Try to extract any parameters that might be document identifiers
                doc_params = re.findall(r"['\"]([^'\"]*(?:getdoc|download|pdf|Documento|Allegato)[^'\"]*\.(?:php|pdf|doc|docx|zip|p7m))['\"]|(\d+)", onclick, re.I)
                for param in doc_params:
                    if isinstance(param, tuple):
                        param = param[0] or param[1]  # Take the first non-empty group
                    if param:
                        if any(ext in param.lower() for ext in ['.php', '.pdf', '.doc', '.docx', '.zip', '.p7m']):
                            allegati.append(up.urljoin(base_url, param))
                        else:
                            # It might be an ID parameter, construct a possible download URL
                            # Common Halleyweb pattern: download.php?id=X or getdoc.php?doc=X
                            possible_urls = [
                                f"{base_url.split('?')[0]}?id={param}",
                                f"{base_url.split('/mc/')[0]}/mc/getdoc.php?id={param}",
                                f"{base_url.split('/mc/')[0]}/mc/download.php?id={param}"
                            ]
                            for possible_url in possible_urls:
                                if not any(existing_url in possible_url for existing_url in allegati):
                                    allegati.append(possible_url)
        
        # Look for table structures that typically contain document links
        for table in soup.find_all('table'):
            for row in table.find_all('tr'):
                row_text = compact_text(row.get_text())
                if any(word in row_text.lower() for word in ['documento', 'allegato', 'pdf', 'scarica']):
                    # Look for clickable elements in this row
                    for cell in row.find_all(['td', 'th']):
                        for link in cell.find_all(['a', 'span', 'div'], attrs={'onclick': True}):
                            onclick = link.get('onclick', '')
                            if any(pattern in onclick.lower() for pattern in ['scarica', 'download', 'getdoc']):
                                # Add the whole onclick as a potential source for Playwright to process
                                # In this case, we'll just track that this element should be clicked
                                # The actual download will happen via Playwright's download interception
                                href_placeholder = f"javascript_handler:{compact_text(link.get_text())}:{onclick}"
                                if href_placeholder not in allegati:
                                    allegati.append(href_placeholder)
    
    # NEW: Extract potential download URLs from inline JavaScript code
    # Look for JavaScript variables or functions that might contain download URLs
    script_tags = soup.find_all('script')
    for script in script_tags:
        if script.string:
            script_content = script.string
            
            # Look for common Halleyweb download patterns in JavaScript
            js_pdf_matches = re.findall(r"['\"]([^'\"]*(?:getdoc|download|pdf|Documento|Allegato)[^'\"]*\.(?:php|pdf|doc|docx|zip|p7m))['\"]", script_content, re.I)
            for match in js_pdf_matches:
                # Make sure it's a relative path or full URL
                if match.startswith('/') or '://' in match or '../' in match or './' in match:
                    allegati.append(up.urljoin(base_url, match))
                else:
                    # It might be a query parameter pattern, try to construct full URL
                    if 'getdoc' in match.lower() or 'download' in match.lower():
                        full_url = up.urljoin(base_url, match)
                        allegati.append(full_url)
            
            # Pattern 2: Function calls that might contain URLs
            func_matches = re.findall(r"(?:href|src|location)\s*[+]?=\s*['\"]([^'\"]*(?:getdoc|download|pdf|Documento|Allegato)[^'\"]*\.(?:php|pdf|doc|docx|zip|p7m))['\"]", script_content, re.I)
            for match in func_matches:
                full_url = up.urljoin(base_url, match)
                allegati.append(full_url)
            
            # Pattern 3: URLs embedded in parameters
            param_matches = re.findall(r"[?&]([^=]*[dD][oO][cC]|[fF][iI][lL][eE]|[uU][rR][lL])=([^&\"'>\s]+)", script_content)
            for _, param_value in param_matches:
                if re.search(r'\.(pdf|doc|docx|zip|p7m|php)$', param_value, re.I):
                    full_url = up.urljoin(base_url, param_value)
                    allegati.append(full_url)

    # NEW: Look for hidden input fields that might contain document URLs (common in form-based downloads)
    hidden_inputs = soup.find_all('input', {'type': 'hidden'})
    for input_elem in hidden_inputs:
        value = input_elem.get('value', '')
        name = input_elem.get('name', '').lower()
        if ('documento' in name or 'allegato' in name or 'pdf' in name or 
            value.lower().endswith(('.pdf', '.doc', '.docx', '.zip', '.p7m', '.php'))):
            if 'getdoc' in value or 'download' in value:
                full_url = up.urljoin(base_url, value)
                allegati.append(full_url)

    # NEW: Look for iframe elements that might contain documents
    iframes = soup.find_all('iframe', src=True)
    for iframe in iframes:
        src = iframe.get('src', '')
        if ('getdoc' in src.lower() or 'download' in src.lower() or 
            src.lower().endswith(('.pdf', '.doc', '.docx', '.zip', '.p7m', '.php'))):
            full_url = up.urljoin(base_url, src)
            allegati.append(full_url)

    # NEW: Special handling for Halleyweb - if we have javascript_handlers, 
    # we'll process them differently in the main scraper
    filtered_allegati = []
    for allegato in allegati:
        if allegato.startswith('javascript_handler:'):
            # This is a placeholder for an element that needs to be clicked
            # We'll handle this in the main scraper with Playwright
            filtered_allegati.append(allegato)
        else:
            # Regular URL
            filtered_allegati.append(allegato)
    
    allegati = filtered_allegati

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