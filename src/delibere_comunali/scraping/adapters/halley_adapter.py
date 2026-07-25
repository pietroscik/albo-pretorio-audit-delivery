"""
Adattatore per il sistema Halleyweb (AgID-compliant).
Implementa un'architettura ibrida per ottimizzare prestazioni e scalabilità.
"""
import asyncio
import re
from typing import Optional, List, Dict, Any, Tuple
from pathlib import Path
import tempfile
import time

try:
    from playwright.async_api import async_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

from .base_adapter import BaseAdapter
from bs4 import BeautifulSoup
import urllib.parse as up

from ..models import AlboItem
from ..utils import looks_like_attachment, url_doc_name
from ..utils import looks_like_attachment, url_doc_name


class HalleyAdapter(BaseAdapter):
    """
    Adattatore intelligente per Halleyweb che implementa:
    - Fase 1: Ricerca metadati con requests
    - Fase 2: Download mirato con Playwright
    - Gestione contesti browser ottimizzata
    - Sniffing della rete invece di DOM clicking
    """
    
    def __init__(self, timeout: int = 30000, max_concurrent_downloads: int = 1):
        super().__init__(timeout=timeout, max_retries=3)
        self.max_concurrent_downloads = max_concurrent_downloads
        self.browser_instance = None
        self.browser_context = None
        self.download_count = 0
        self.max_downloads_per_session = 50  # Reset browser ogni 50 download
        
        # Cache per rilevamento automatico
        self.platform_cache: Dict[str, bool] = {}
        
    async def initialize_browser(self):
        """Inizializza l'istanza del browser una sola volta"""
        if not PLAYWRIGHT_AVAILABLE:
            raise RuntimeError("Playwright è richiesto per Halleyweb")
            
        if self.browser_instance is None:
            self.playwright = await async_playwright().start()
            self.browser_instance = await self.playwright.chromium.launch(headless=True)
        
        if self.browser_context is None:
            self.browser_context = await self.browser_instance.new_context(accept_downloads=True)
    
    async def cleanup_browser(self):
        """Pulisce le risorse del browser"""
        if self.browser_context:
            await self.browser_context.close()
            self.browser_context = None
        # Non chiudiamo il browser qui, lo teniamo vivo per riutilizzo
        
    async def reset_browser_if_needed(self):
        """Resetta il browser se abbiamo superato il limite di download"""
        self.download_count += 1
        if self.download_count >= self.max_downloads_per_session:
            if self.browser_context:
                await self.browser_context.close()
            if self.browser_instance:
                await self.browser_instance.close()
            self.browser_instance = None
            self.browser_context = None
            self.download_count = 0
            await self.initialize_browser()
    
    def is_halleyweb_url(self, url: str) -> bool:
        """Rileva automaticamente se un URL appartiene a Halleyweb"""
        cache_key = url.split('/')[2]  # Dominio
        if cache_key in self.platform_cache:
            return self.platform_cache[cache_key]
        
        # Ricerca pattern comuni di Halleyweb
        is_halley = 'halleyweb' in url.lower() or any(pattern in url.lower() for pattern in [
            '/mc/', '/halley/', 'c064103', 'halleyweb.com'
        ])
        
        # Ricerca anche nell'HTML della homepage per caratteristiche Halleyweb
        if not is_halley:
            try:
                response = requests.head(url, timeout=min(self.timeout//1000, 10))
                # Cerca header o contenuti che indicano Halleyweb
                server_header = response.headers.get('Server', '').lower()
                if 'halley' in server_header:
                    is_halley = True
                else:
                    # Fai una breve richiesta GET per cercare caratteristiche Halleyweb
                    response = requests.get(url, timeout=min(self.timeout//1000, 5))
                    content_lower = response.text.lower()[:5000]  # Solo primi 5KB per velocità
                    halley_indicators = [
                        'halleyweb', 'halley informatica', 'c064103',
                        'mc_p_ricerca', 'mc_p_dettaglio', 'getdoc'
                    ]
                    is_halley = any(indicator in content_lower for indicator in halley_indicators)
            except:
                # Se fallisce, torna a pattern URL
                pass
        
        self.platform_cache[cache_key] = is_halley
        return is_halley
    
    def scrape_metadata_with_requests(self, url: str) -> Tuple[List[AlboItem], Optional[str]]:
        """
        Fase 1: Ricerca metadati usando requests (molto più veloce)
        """
        try:
            response = requests.get(url, timeout=self.timeout//1000)
            response.raise_for_status()
            html = response.text
            
            # Parsing simile a quello standard ma ottimizzato per Halleyweb
            soup = BeautifulSoup(html, "html.parser")
            items = []
            
            # Cerca tabelle o div con elementi di albo pretorio
            rows = soup.select("table tr")
            if not rows:
                rows = soup.select("div.risultato, div.elenco, li")
            
            for r in rows:
                a = r.find("a", href=True)
                if not a:
                    continue
                href = up.urljoin(url, a["href"])
                
                # Estrai testo dalle celle
                tds = r.find_all("td")
                
                titolo_val = ""
                oggetto_val = ""
                ufficio_val = ""
                numero_val = None
                data_val = None
                tipologia_val = None

                if len(tds) >= 4:
                    colonne = [td.get_text(separator=" ", strip=True) for td in tds]
                    row_text = " ".join(colonne)
                    
                    # Estrai informazioni
                    oggetto_val = max(colonne, key=len) if colonne else ""
                    titolo_val = oggetto_val[:150] + ("..." if len(oggetto_val) > 150 else "")
                    
                    # Estrai data
                    import re
                    data_match = re.search(r"\b(\d{2}/\d{2}/\d{4})\b", row_text)
                    if data_match:
                        data_val = data_match.group(1)
                    
                    # Estrai numero
                    num_match = re.search(r"\b(n\.|numero)\s*[:\s]*([0-9/]+)", row_text, re.I)
                    if num_match:
                        numero_val = num_match.group(2)
                    
                    # Estrai tipologia
                    tipo_match = re.search(r"\b(delibera|determinazione|ordinanza|avviso|bando)\b", row_text, re.I)
                    if tipo_match:
                        tipologia_val = tipo_match.group(1).capitalize()
                else:
                    row_text = r.get_text(separator=" | ", strip=True)
                    oggetto_val = row_text
                    titolo_val = row_text[:150]

                item = AlboItem(
                    page_url=url,
                    titolo=titolo_val or "Senza titolo",
                    numero=numero_val,
                    data_pubblicazione=data_val,
                    tipologia=tipologia_val,
                    ufficio=ufficio_val,
                    oggetto=oggetto_val,
                    dettaglio_url=href,
                )
                items.append(item)

            # Trova link successivo
            next_link = None
            for c in soup.find_all("a", string=re.compile(r"(successiva|successivo|pagina successiva|avanti|>)", re.I)):
                if c.get("href"):
                    next_link = up.urljoin(url, c["href"])
                    break

            return items, next_link
            
        except Exception as e:
            print(f"Errore nello scraping metadati con requests: {e}")
            return [], None
    
    async def download_attachment_with_playwright(self, url: str, download_dir: str) -> List[str]:
        """
        Fase 2: Download mirato usando Playwright con network sniffing
        """
        if not PLAYWRIGHT_AVAILABLE:
            return []
        
        downloaded_files = []
        
        try:
            await self.initialize_browser()
            page = await self.browser_context.new_page()
            page.set_default_timeout(self.timeout)
            
            # Naviga alla pagina di dettaglio
            await page.goto(url, wait_until="networkidle")
            
            # Logica specifica per Halleyweb: gestisce i popup JS per il download
            # es: <a href="javascript:void(0);" onclick="window.open('mc_attachment.php?mc=14702');">
            attachment_links = await page.query_selector_all("a[onclick*='mc_attachment.php'], a[onclick*='getdoc']")

            for link in attachment_links:
                try:
                    # Ascolta l'evento popup che viene scatenato da window.open
                    async with self.browser_context.expect_page() as popup_info:
                        await link.click(force=True)
                    
                    popup = await popup_info.value
                    await popup.wait_for_load_state("domcontentloaded", timeout=15000)

                    # Il popup stesso potrebbe essere il file o potrebbe innescare un download.
                    try:
                        # Attendi un download sulla pagina popup
                        async with popup.expect_download(timeout=15000) as download_info:
                            await popup.wait_for_timeout(3000) # Attendi che il JS/redirect inneschi il download

                        download = await download_info.value
                        filename = download.suggested_filename or f"attachment_{int(time.time())}.pdf"
                        filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                        
                        filepath = Path(download_dir) / filename
                        await download.save_as(str(filepath))
                        downloaded_files.append(str(filepath))
                    except Exception:
                        # Se expect_download fallisce, il contenuto del popup potrebbe essere il file.
                        # Questo accade se il server risponde con Content-Type: application/pdf
                        # ma senza Content-Disposition: attachment.
                        if 'pdf' in popup.url.lower() or 'p7m' in popup.url.lower():
                            response = await popup.context.request.get(popup.url)
                            body = await response.body()
                            filename = Path(up.urlparse(popup.url).path).name or f"attachment_{int(time.time())}.pdf"
                            filepath = Path(download_dir) / filename
                            filepath.write_bytes(body)
                            downloaded_files.append(str(filepath))
                    finally:
                        await popup.close()
                except Exception as e:
                    print(f"Warning: Failed to handle Halley popup: {e}")
                    continue
            
                                await element.click(force=True)  # Usa force=True per evitare problemi di visibilità
                                await page.wait_for_timeout(2000)
                                
                                download = await download_info.value
                                filename = download.suggested_filename or f"attachment_{int(time.time())}.pdf"
                                filename = re.sub(r'[<>:"/\\|?*]', '_', filename)
                                
                                filepath = Path(download_dir) / filename
                                await download.save_as(str(filepath))
                                downloaded_files.append(str(filepath))
                                
                        except Exception:
                            # Se il download non avviene immediatamente, continua con il prossimo elemento
                            continue
                            
                except Exception:
                    continue
            
            await page.close()
            
            # Resetta il browser se necessario
            await self.reset_browser_if_needed()
            
        except Exception as e:
            print(f"Errore nel download con Playwright: {e}")
        
        return downloaded_files
    
    def parse_detail_page_with_requests(self, html: str, base_url: str) -> Tuple[Optional[str], Optional[str], List[str]]:
        """
        Parsing della pagina di dettaglio usando solo requests/BeautifulSoup
        Estrae allegati cercando pattern Halleyweb specifici
        """
        soup = BeautifulSoup(html, "html.parser")
        text = " ".join(soup.get_text(separator=" | ").split())

        # Estrai oggetto e ufficio
        ogg = None
        uff = None
        
        # Cerca pattern comuni in Halleyweb
        ogg_match = re.search(r"\b(?:oggetto|titolo)\b\s*[:|]\s*(.+?)(?=\s*\|\s*(?:ufficio|settore|area|allegati?|pubblicazione|numero)\b|\s*$)", text, re.I)
        if ogg_match:
            ogg = ogg_match.group(1).strip(" :-|")
        
        uff_match = re.search(r"\b(?:ufficio|settore|area)\b\s*[:|]\s*(.+?)(?=\s*\|\s*(?:oggetto|titolo|allegati?|pubblicazione|numero)\b|\s*$)", text, re.I)
        if uff_match:
            uff = uff_match.group(1).strip(" :-|")

        allegati = []
        
        # Cerca link specifici di Halleyweb che potrebbero essere allegati
        for a in soup.find_all("a", href=True):
            href = a["href"]
            label = " ".join(a.get_text().split())
            
            # Controlla se è un allegato secondo la nostra logica
            if looks_like_attachment(href, label):
                allegati.append(up.urljoin(base_url, href))
            elif 'halleyweb' in base_url.lower():
                # Logica specifica per Halleyweb
                if any(keyword in label.lower() for keyword in ['documento', 'allegato', 'scarica', 'pdf']):
                    allegati.append(up.urljoin(base_url, href))
                elif 'javascript:' in href.lower():
                    # Estrai eventuali URL da onclick se il link è javascript:
                    onclick = a.get('onclick', '')
                    if onclick:
                        # Cerca possibili URL nei parametri onclick
                        matches = re.findall(r"['\"]([^'\"]*(?:getdoc|download|pdf)[^'\"]*\.(?:php|pdf|doc|docx|zip|p7m))['\"]", onclick, re.I)
                        for match in matches:
                            allegati.append(up.urljoin(base_url, match))
        
        # Rimuovi duplicati
        seen = set()
        unique_allegati = []
        for url in allegati:
            if url not in seen:
                seen.add(url)
                unique_allegati.append(url)
        
        return ogg, uff, unique_allegati
    
    async def close(self):
        """Chiude tutte le risorse del browser"""
        if self.browser_context:
            await self.browser_context.close()
        if self.browser_instance:
            await self.browser_instance.close()
        if hasattr(self, 'playwright'):
            await self.playwright.stop()


# Funzione factory per rilevamento automatico
def create_halley_adapter_if_needed(url: str) -> Optional['HalleyAdapter']:
    """
    Factory che restituisce un HalleyAdapter se il sito è Halleyweb, altrimenti None
    """
    adapter = HalleyAdapter()
    if adapter.is_halleyweb_url(url):
        return adapter
    else:
        # Cleanup se abbiamo creato un'istanza per il check
        # (in realtà non abbiamo ancora inizializzato il browser in is_halleyweb_url)
        return None