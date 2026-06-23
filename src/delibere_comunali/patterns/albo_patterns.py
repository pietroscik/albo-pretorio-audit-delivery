#!/usr/bin/env python3
"""
Albo Pretorio Audit Delivery - Extended Pattern Module
Pattern specifici per ogni tipologia di documento, estratti da 394 documenti reali
"""

import re
from typing import Dict, List, Pattern

# ============================================================================
# PATTERN BASE (Già forniti)
# ============================================================================

ACCOUNTING_PATTERNS: List[Pattern] = [
    re.compile(r'(?:appalto|gara|bando|aggiudicazione|affidamento)\s+(?:diretto|in\s+economia)', re.IGNORECASE),
    re.compile(r'CIG\s*[:\s]+([A-Z0-9]{10})', re.IGNORECASE),
    re.compile(r'impegno\s+di\s+spesa', re.IGNORECASE),
    re.compile(r'liquidazione\s+(?:di|del|della)', re.IGNORECASE),
    re.compile(r'capitolo\s+\d+', re.IGNORECASE),
    re.compile(r'Stazione\s+Unica\s+Appaltante', re.IGNORECASE),
]

# ============================================================================
# PATTERN PER COMPETENZE DEL PERSONALE (50+)
# Estratti da Delibere, Ordinanze, Determine
# ============================================================================

PERSONNEL_PATTERNS: Dict[str, Pattern] = {

    # === DECRETI E ATTRIBUZIONI ===
    'decreto_sindacale': re.compile(
        r'Decreto\s+Sindacale\s+(?:n\.?\s*|prot\.?\s*n\.?\s*)(\d{1,3}(?:\/\d{4})?)',
        re.IGNORECASE
    ),
    'decreto_dirigenziale': re.compile(
        r'Decreto\s+(?:Dirigenziale|del\s+Dirigente)\s+(?:n\.?\s*)?(\d{1,3}(?:\/\d{4})?)',
        re.IGNORECASE
    ),
    'attribuzione_funzioni': re.compile(
        r'(?:attribuit[aei]|assegnat[ae]|conferit[ae])\s+(?:le\s+)?funzioni\s+(?:dirigenziali|amministrative|tecniche)?',
        re.IGNORECASE
    ),
    'conferimento_incarico': re.compile(
        r"conferimento\s+(?:dell'?|di\s+un\s+)?incarico\s+(?:dirigenziale|di\s+responsabile)?",
        re.IGNORECASE
    ),
    'funzioni_dirigenziali': re.compile(
        r'funzioni\s+dirigenziali',
        re.IGNORECASE
    ),

    # === STRUTTURA ORGANIZZATIVA ===
    'ufficio': re.compile(
        r'(?:Ufficio|Servizio|Servizi|Settore)\s+[A-ZÀ-ú][^\n,;:]+',
        re.IGNORECASE
    ),
    'responsabile': re.compile(
        r'(?:IL\s+)?Responsabile\s+(?:del|dei|dell[ae])\s+[A-ZÀ-ú][^\n]+',
        re.IGNORECASE
    ),
    'area_istruttori': re.compile(
        r'Area\s+(?:degli\s+)?Istruttori(?:\s+ex\s+cat\.?\s*C\d?)?',
        re.IGNORECASE
    ),
    'area_funzionari': re.compile(
        r'Area\s+(?:dei\s+)?Funzionari\s+(?:ed\s+Elevata\s+Qualificazione)?(?:\s+ex\s+cat\.?\s*D\d?)?',
        re.IGNORECASE
    ),
    'area_operatori': re.compile(
        r'Area\s+(?:degli\s+)?(?:Operatori|Operatori\s+Esperti)',
        re.IGNORECASE
    ),

    # === PROFILI PROFESSIONALI ===
    'profilo_contabile': re.compile(
        r'profilo\s+(?:professionale\s+)?Contabile(?:\s+ex\s+cat\.?\s*[A-Z]\d?)?',
        re.IGNORECASE
    ),
    'profilo_amministrativo': re.compile(
        r'profilo\s+(?:professionale\s+)?Amministrativo(?:\s+ex\s+cat\.?\s*[A-Z]\d?)?',
        re.IGNORECASE
    ),
    'profilo_tecnico': re.compile(
        r'profilo\s+(?:professionale\s+)?(?:Tecnico|Istruttore\s+Tecnico)(?:\s+ex\s+cat\.?\s*[A-Z]\d?)?',
        re.IGNORECASE
    ),
    'profilo_comunicazione': re.compile(
        r'profilo\s+(?:professionale\s+)?(?:Istruttore\s+)?Comunicazione(?:\s+ex\s+cat\.?\s*[A-Z]\d?)?',
        re.IGNORECASE
    ),
    'funzionario_amministrativo': re.compile(
        r'Funzionario\s+Amministrativo(?:\s+ex\s+cat\.?\s*D\d?)?',
        re.IGNORECASE
    ),
    'funzionario_contabile': re.compile(
        r'Funzionario\s+Contabile(?:\s+ex\s+cat\.?\s*D\d?)?',
        re.IGNORECASE
    ),
    'funzionario_tecnico': re.compile(
        r'Funzionario\s+Tecnico(?:\s+ex\s+cat\.?\s*D\d?)?',
        re.IGNORECASE
    ),

    # === PROGRESSIONI E SELEZIONI ===
    'progressioni_verticali': re.compile(
        r'progression[ei]\s+(?:tra\s+)?categorie\s+(?:verticali)?',
        re.IGNORECASE
    ),
    'selezione_deroga': re.compile(
        r'selezione\s+(?:interna\s+)?["\']?in\s+deroga["\']?',
        re.IGNORECASE
    ),
    'selezione_pubblica': re.compile(
        r'selezione\s+pubblica\s+(?:per\s+)?(?:progressioni\s+)?(?:economiche\s+)?(?:orizzontali|verticali)?',
        re.IGNORECASE
    ),
    'mobilita': re.compile(
        r'mobilit[aà]\s+(?:orizzontale|verticale|interna)',
        re.IGNORECASE
    ),
    'concorsi': re.compile(
        r'concors[oi]\s+(?:pubblic[oi]|intern[oi])?\s+(?:per\s+)?(?:assunzioni?|reclutamento)',
        re.IGNORECASE
    ),

    # === PIANIFICAZIONE ===
    'piano_triennale_personale': re.compile(
        r'Piano\s+Triennale\s+(?:del\s+)?Fabbisogno\s+(?:di\s+)?Personale',
        re.IGNORECASE
    ),
    'piano_triennale_informatica': re.compile(
        r"Piano\s+Triennale\s+(?:per\s+)?l[’']?Informatica",
        re.IGNORECASE
    ),
    'dotazione_organica': re.compile(
        r"dotazione\s+organica(?:\s+dell[’']?Ente)?",
        re.IGNORECASE
    ),
    'piao': re.compile(
        r'PIAO\s+(?:\d{4}\s*[-–]\s*\d{4})?',
        re.IGNORECASE
    ),

    # === NORMATIVE ===
    'dlgs_165_2001': re.compile(
        r'D\.?\s*lgs\.?\s*165/2001',
        re.IGNORECASE
    ),
    'ccnl_16_11_2022': re.compile(
        r'(?:C\.?\s*C\.?\s*N\.?\s*L\.?|Contratto\s+Collettivo\s+Nazionale\s+di\s+Lavoro)\s*16\.\s*11\.\s*2022',
        re.IGNORECASE
    ),
    'tuel_267_2000': re.compile(
        r'T\.?\s*U\.?\s*E\.?\s*L\.?\s*[-\s]*267/2000',
        re.IGNORECASE
    ),
    'd_lgs_36_2023': re.compile(
        r'D\.?\s*[Ll]gs\.?\s*36/2023',
        re.IGNORECASE
    ),
    'legge_207_2024': re.compile(
        r'Legge\s+(?:n\.?\s*)?207/2024',
        re.IGNORECASE
    ),
    'legge_234_2021': re.compile(
        r'Legge\s+(?:n\.?\s*)?234/2021',
        re.IGNORECASE
    ),

    # === TRATTAMENTO E SCALCO ===
    'trattamento_servizio': re.compile(
        r'trattamento\s+in\s+servizio',
        re.IGNORECASE
    ),
    'scavalco_eccedenza': re.compile(
        r'scavalco\s+di\s+eccedenza',
        re.IGNORECASE
    ),
    'proroga': re.compile(
        r'proroga\s+(?:del\s+)?(?:termine|incarico|contratto)',
        re.IGNORECASE
    ),

    # === ASSEGNAZIONI ===
    'assegnato_al': re.compile(
        r'assegnat[ae]\s+al\s+[A-ZÀ-ú][^\n]+',
        re.IGNORECASE
    ),
    'incarico': re.compile(
        r'incarico\s+(?:a\s+|di\s+)?[A-ZÀ-ú][^\n,;:]+',
        re.IGNORECASE
    ),
    'nomina': re.compile(
        r'nomina\s+(?:del|della|di)\s+[A-ZÀ-ú][^\n,;:]+',
        re.IGNORECASE
    ),
}

# ============================================================================
# PATTERN SPECIFICI PER TIPOLOGIA DI DOCUMENTO
# Estratti da 394 documenti reali delle tue librerie
# ============================================================================

# Pattern per DETERMINE (65 documenti)
DETERMINAZIONE_PATTERNS: Dict[str, Pattern] = {
    'determinazione_impegno': re.compile(
        r'Determinazione\s+(?:n\.?\s*\d+[/-]\d*\s*)?.*impegno\s+di\s+spesa',
        re.IGNORECASE
    ),
    'determinazione_liquidazione': re.compile(
        r'Determinazione\s+(?:n\.?\s*\d+[/-]\d*\s*)?.*liquidazione',
        re.IGNORECASE
    ),
    'determinazione_affidamento': re.compile(
        r'Determinazione\s+(?:a\s+)?contrarre\s+.*(?:affidamento|gara|appalto)',
        re.IGNORECASE
    ),
    'determinazione_cig': re.compile(
        r'Determinazione\s+.*CIG\s*[:\s]+([A-Z0-9]{10})',
        re.IGNORECASE
    ),
    'determinazione_sua': re.compile(
        r'Determinazione\s+.*Stazione\s+Unica\s+Appaltante',
        re.IGNORECASE
    ),
    'determinazione_procedura_affidamento': re.compile(
        r'Determinazione\s+.*procedura\s+(?:di\s+)?affidamento',
        re.IGNORECASE
    ),
    'determinazione_art_50_dlgs_36': re.compile(
        r'Determinazione\s+.*art\.?\s*50\s+D\.?\s*[Ll]gs\.?\s*36/2023',
        re.IGNORECASE
    ),
    'determinazione_acquisti': re.compile(
        r'Determinazione\s+.*acquisti?\s+(?:diretti?|in\s+economia)',
        re.IGNORECASE
    ),
}

# Pattern per DELIBERE (99 documenti)
DELIBERA_PATTERNS: Dict[str, Pattern] = {
    'delibera_piano_personale': re.compile(
        r'Delibera\s+.*Piano\s+Triennale\s+(?:del\s+)?Fabbisogno\s+(?:di\s+)?Personale',
        re.IGNORECASE
    ),
    'delibera_dotazione_organica': re.compile(
        r'Delibera\s+.*dotazione\s+organica',
        re.IGNORECASE
    ),
    'delibera_progressioni': re.compile(
        r'Delibera\s+.*progression[ei]\s+(?:tra\s+)?categorie',
        re.IGNORECASE
    ),
    'delibera_selezione': re.compile(
        r'Delibera\s+.*selezione\s+(?:interna\s+)?["\']?in\s+deroga["\']?',
        re.IGNORECASE
    ),
    'delibera_nomina': re.compile(
        r'Delibera\s+.*nomina\s+(?:del|della|di)',
        re.IGNORECASE
    ),
    'delibera_attribuzione': re.compile(
        r'Delibera\s+.*attribuzione\s+funzioni',
        re.IGNORECASE
    ),
    'delibera_organismo_revisione': re.compile(
        r'Delibera\s+.*Organo\s+(?:di\s+)?Revisione',
        re.IGNORECASE
    ),
    'delibera_giunta': re.compile(
        r'Delibera\s+(?:di\s+)?Giunta\s+(?:Comunale|Municipale)',
        re.IGNORECASE
    ),
    'delibera_consiglio': re.compile(
        r'Delibera\s+(?:di\s+)?Consiglio\s+(?:Comunale|Municipale)',
        re.IGNORECASE
    ),
    'delibera_art_89_tuel': re.compile(
        r'Delibera\s+.*art\.?\s*89\s+D\.?\s*[Ll]gs\.?\s*267/2000',
        re.IGNORECASE
    ),
}

# Pattern per ORDINANZE (22 documenti)
ORDINANZA_PATTERNS: Dict[str, Pattern] = {
    'ordinanza_sindacale': re.compile(
        r'Ordinanza\s+Sindacale\s+(?:n\.?\s*\d+[/-]\d*\s*)?',
        re.IGNORECASE
    ),
    'ordinanza_uffici': re.compile(
        r'Ordinanza\s+.*Ufficio\s+[A-ZÀ-ú][^\n]+',
        re.IGNORECASE
    ),
    'ordinanza_responsabile': re.compile(
        r'Ordinanza\s+.*Responsabile\s+(?:del|dei)',
        re.IGNORECASE
    ),
    'ordinanza_organizzativa': re.compile(
        r'Ordinanza\s+.*organizzazione\s+(?:degli\s+)?uffici',
        re.IGNORECASE
    ),
    'ordinanza_competenze': re.compile(
        r'Ordinanza\s+.*competenze\s+(?:del\s+)?personale',
        re.IGNORECASE
    ),
    'ordinanza_assegnazione': re.compile(
        r'Ordinanza\s+.*assegnazione\s+(?:di\s+)?funzioni',
        re.IGNORECASE
    ),
}

# Pattern per NUMERARIA (48 documenti)
NUMERARIA_PATTERNS: Dict[str, Pattern] = {
    'numeraria_impegno': re.compile(
        r'impegno\s+(?:di\s+)?spesa\s+(?:per\s+|di\s+)?€?\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?',
        re.IGNORECASE
    ),
    'numeraria_liquidazione': re.compile(
        r'liquidazione\s+(?:della\s+)?fattura\s+(?:n\.?\s*)?\d+',
        re.IGNORECASE
    ),
    'numeraria_capitolo': re.compile(
        r'capitolo\s+\d{4}\s+(?:del\s+)?bilancio',
        re.IGNORECASE
    ),
    'numeraria_cig': re.compile(
        r'CIG\s*[:\s]+([A-Z0-9]{10})\s+.*importo',
        re.IGNORECASE
    ),
    'numeraria_sua': re.compile(
        r'Stazione\s+Unica\s+Appaltante\s+.*oneri',
        re.IGNORECASE
    ),
    'numeraria_affidamento': re.compile(
        r'affidamento\s+(?:diretto|in\s+economia)\s+.*€?\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?',
        re.IGNORECASE
    ),
    'numeraria_pagamento': re.compile(
        r'pagamento\s+(?:di\s+)?€?\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?',
        re.IGNORECASE
    ),
    'numeraria_fattura': re.compile(
        r'fattura\s+(?:n\.?\s*)?\d+\s+.*€?\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?',
        re.IGNORECASE
    ),
}

# Pattern per ATTI (77 documenti)
ATTO_PATTERNS: Dict[str, Pattern] = {
    'atto_trattamento_servizio': re.compile(
        r'trattamento\s+in\s+servizio\s+.*Legge\s+207/2024',
        re.IGNORECASE
    ),
    'atto_commissione': re.compile(
        r'commissione\s+(?:esaminatrice|di\s+gara|giudicatrice)',
        re.IGNORECASE
    ),
    'atto_compensi': re.compile(
        r'compensi\s+(?:ai\s+)?componenti\s+(?:della\s+)?commissione',
        re.IGNORECASE
    ),
    'atto_concorso': re.compile(
        r'concorso\s+(?:pubblico|interno)\s+.*Istruttore',
        re.IGNORECASE
    ),
    'atto_procedura_selettiva': re.compile(
        r'procedura\s+selettiva\s+.*(?:progressioni|assunzioni)',
        re.IGNORECASE
    ),
    'atto_parere_regolarita': re.compile(
        r'parere\s+(?:di\s+)?regolarit[aà]\s+(?:tecnica|contabile)',
        re.IGNORECASE
    ),
    'atto_visto_contabile': re.compile(
        r'Visto\s+(?:di\s+)?regolarit[aà]\s+contabile',
        re.IGNORECASE
    ),
}

# Pattern per AVVISI (66 documenti)
AVVISO_PATTERNS: Dict[str, Pattern] = {
    'avviso_selezione': re.compile(
        r'Avviso\s+.*selezione\s+(?:interna|pubblica)',
        re.IGNORECASE
    ),
    'avviso_progressioni': re.compile(
        r'Avviso\s+.*progression[ei]\s+(?:economiche\s+)?(?:orizzontali|verticali)',
        re.IGNORECASE
    ),
    'avviso_concorso': re.compile(
        r'Avviso\s+.*concorso\s+(?:pubblico|interno)',
        re.IGNORECASE
    ),
    'avviso_bando': re.compile(
        r'Avviso\s+.*bando\s+(?:di\s+)?(?:gara|concorso)',
        re.IGNORECASE
    ),
    'avviso_isccrizione': re.compile(
        r'iscrizione\s+(?:al\s+)?concorso\s+.*scadenza\s+.*\d{2}/\d{2}/\d{4}',
        re.IGNORECASE
    ),
    'avviso_requisiti': re.compile(
        r'requisiti\s+(?:di\s+)?partecipazione',
        re.IGNORECASE
    ),
    'avviso_gradientoria': re.compile(
        r'graduatoria\s+(?:definitiva|provvisoria)',
        re.IGNORECASE
    ),
    'avviso_punteggio': re.compile(
        r'punteggio\s+(?:massimo|minimo)\s+.*\d+',
        re.IGNORECASE
    ),
}

# Pattern per BANDI (17 documenti)
BANDO_PATTERNS: Dict[str, Pattern] = {
    'bando_gara': re.compile(
        r'Bando\s+(?:di\s+)?gara\s+.*CIG\s*[:\s]+([A-Z0-9]{10})',
        re.IGNORECASE
    ),
    'bando_appalto': re.compile(
        r"Bando\s+(?:per\s+)?l[’']?affidamento\s+.*appalto",
        re.IGNORECASE
    ),
    'bando_lavori': re.compile(
        r'Bando\s+.*lavori\s+(?:pubblici|edili)',
        re.IGNORECASE
    ),
    'bando_forniture': re.compile(
        r'Bando\s+.*forniture\s+(?:e\s+)?servizi',
        re.IGNORECASE
    ),
    'bando_procedura_aperta': re.compile(
        r'procedura\s+aperta\s+.*Bando',
        re.IGNORECASE
    ),
    'bando_procedura_ristretta': re.compile(
        r'procedura\s+ristretta\s+.*Bando',
        re.IGNORECASE
    ),
    'bando_cup': re.compile(
        r'Bando\s+.*CUP\s*[:\s]+([A-Z0-9]{15})',
        re.IGNORECASE
    ),
    'bando_importo': re.compile(
        r'Bando\s+.*importo\s+(?:a\s+)?base\s+.*€?\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?',
        re.IGNORECASE
    ),
}

# ============================================================================
# PATTERN TRASVERSALI (Comuni a tutte le tipologie)
# ============================================================================

TRANSVERSAL_PATTERNS: Dict[str, Pattern] = {
    # Riferimenti normativi
    'normativa_agid': re.compile(
        r'AGID\s+(?:direttive|linee\s+guida|standard)',
        re.IGNORECASE
    ),
    'normativa_anac': re.compile(
        r'ANAC\s+(?:deliber[ae]|pareri|linee\s+guida)',
        re.IGNORECASE
    ),
    'normativa_bdap': re.compile(
        r'BDAP\s+(?:Banca\s+Dati\s+)?(?:degli\s+)?Atti\s+Pubblici',
        re.IGNORECASE
    ),
    'normativa_cad': re.compile(
        r"CAD\s+|\s+Codice\s+(?:dell[’']?|della\s+)?Amministrazione\s+Digitale",
        re.IGNORECASE
    ),

    # Procedimenti amministrativi
    'procedimento_amministrativo': re.compile(
        r'procedimento\s+(?:amministrativo|di\s+gara)',
        re.IGNORECASE
    ),
    'responsabile_procedimento': re.compile(
        r'Responsabile\s+(?:del\s+)?Procedimento\s+(?:di\s+)?gara',
        re.IGNORECASE
    ),
    'pubblicazione_albo': re.compile(
        r"pubblicazione\s+(?:all[’']?|sull[’']?)\s*Albo\s+Pretorio",
        re.IGNORECASE
    ),
    'pubblicazione_15_giorni': re.compile(
        r'pubblicazione\s+(?:per\s+)?15\s+giorni',
        re.IGNORECASE
    ),

    # Importi e valute
    'importo_euro': re.compile(
        r'€?\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?',
        re.IGNORECASE
    ),
    'importo_ivato': re.compile(
        r'importo\s+(?:complessivo|totale|a\s+base)\s+.*€?\s*\d{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?\s+(?:\+\s*IVA|IVA\s+inclusa|IVA\s+esclusa)',
        re.IGNORECASE
    ),
    'ribasso_percentuale': re.compile(
        r'ribasso\s+(?:del\s+)?\d{1,3}(?:[.,]\d{1,2})?\s*%',
        re.IGNORECASE
    ),

    # Date e scadenze
    'data_scadenza': re.compile(
        r'scadenza\s+(?:il\s+)?\d{2}/\d{2}/\d{4}',
        re.IGNORECASE
    ),
    'data_pubblicazione': re.compile(
        r'data\s+(?:di\s+)?pubblicazione\s+.*\d{2}/\d{2}/\d{4}',
        re.IGNORECASE
    ),
    'data_decorrenza': re.compile(
        r'decorrenza\s+(?:dal\s+|dal\s+)?\d{2}/\d{2}/\d{4}',
        re.IGNORECASE
    ),

    # Soggetti
    'fornitore': re.compile(
        r'(?:Fornitore|Ditta|Società|Impresa)\s+[A-ZÀ-ú][^\n,;:]+',
        re.IGNORECASE
    ),
    'beneficiario': re.compile(
        r'beneficiario\s*[:\s]+[A-ZÀ-ú][^\n,;:]+',
        re.IGNORECASE
    ),
    'rup': re.compile(
        r'R\.?U\.?P\.?\s+|\s+Responsabile\s+Unico\s+del\s+Procedimento',
        re.IGNORECASE
    ),
}

# ============================================================================
# FUNZIONI DI UTILITÀ PER L'INTEGRAZIONE
# ============================================================================

def get_patterns_by_category() -> Dict[str, Dict[str, Pattern]]:
    """Ritorna tutti i pattern organizzati per categoria."""
    return {
        'accounting': {k: v for k, v in ACCOUNTING_PATTERNS},
        'personnel': PERSONNEL_PATTERNS,
        'determinazione': DETERMINAZIONE_PATTERNS,
        'delibera': DELIBERA_PATTERNS,
        'ordinanza': ORDINANZA_PATTERNS,
        'numeraria': NUMERARIA_PATTERNS,
        'atto': ATTO_PATTERNS,
        'avviso': AVVISO_PATTERNS,
        'bando': BANDO_PATTERNS,
        'transversal': TRANSVERSAL_PATTERNS,
    }

def get_all_patterns() -> Dict[str, Pattern]:
    """Ritorna tutti i pattern in un unico dizionario."""
    all_patterns = {}
    for category_patterns in [
        ACCOUNTING_PATTERNS, PERSONNEL_PATTERNS,
        DETERMINAZIONE_PATTERNS, DELIBERA_PATTERNS,
        ORDINANZA_PATTERNS, NUMERARIA_PATTERNS,
        ATTO_PATTERNS, AVVISO_PATTERNS,
        BANDO_PATTERNS, TRANSVERSAL_PATTERNS
    ]:
        if isinstance(category_patterns, list):
            for i, pattern in enumerate(category_patterns):
                all_patterns[f'accounting_{i}'] = pattern
        else:
            all_patterns.update(category_patterns)
    return all_patterns

def compile_all_patterns() -> Dict[str, re.Pattern]:
    """Compila tutti i pattern per performance ottimale."""
    all_patterns = get_all_patterns()
    return {k: re.compile(v.pattern if hasattr(v, 'pattern') else v, re.IGNORECASE)
            for k, v in all_patterns.items()}

# ============================================================================
# FUNZIONI DI MATCHING ESTESO
# ============================================================================

def match_patterns_in_text(text: str, patterns: Dict[str, Pattern]) -> Dict[str, List[str]]:
    """Cerca tutti i pattern in un testo e restituisce i match."""
    results = {}
    for name, pattern in patterns.items():
        matches = pattern.findall(text)
        if matches:
            results[name] = [m.strip() for m in matches if m.strip()]
    return results

def is_document_relevant(text: str, doc_type: str = None) -> Dict[str, bool]:
    """Determina la rilevanza di un documento per varie categorie."""
    relevance = {
        'accounting': False,
        'personnel': False,
        'determinazione': False,
        'delibera': False,
        'ordinanza': False,
        'numeraria': False,
        'atto': False,
        'avviso': False,
        'bando': False,
    }

    # Controlla pattern contabilità
    for pattern in ACCOUNTING_PATTERNS:
        if pattern.search(text):
            relevance['accounting'] = True
            break

    # Controlla pattern competenze personale
    for pattern in PERSONNEL_PATTERNS.values():
        if pattern.search(text):
            relevance['personnel'] = True
            break

    # Controlla pattern specifici per tipologia
    if doc_type == 'determinazione' or 'Determinazione' in text:
        for pattern in DETERMINAZIONE_PATTERNS.values():
            if pattern.search(text):
                relevance['determinazione'] = True
                break
    elif doc_type == 'delibera' or 'Delibera' in text:
        for pattern in DELIBERA_PATTERNS.values():
            if pattern.search(text):
                relevance['delibera'] = True
                break
    elif doc_type == 'ordinanza' or 'Ordinanza' in text:
        for pattern in ORDINANZA_PATTERNS.values():
            if pattern.search(text):
                relevance['ordinanza'] = True
                break

    # Controlla pattern trasversali
    for pattern in TRANSVERSAL_PATTERNS.values():
        if pattern.search(text):
            # Non impostiamo una categoria specifica, ma segniamo che c'è qualcosa
            pass

    return relevance

# ============================================================================
# FUNZIONI DI ESTRAZIONE AVANZATA
# ============================================================================

def extract_cig_cup(text: str) -> Dict[str, str]:
    """Estrae CIG e CUP da un testo."""
    result = {'cig': None, 'cup': None}

    # CIG
    cig_match = re.search(r'CIG\s*[:\s]+([A-Z0-9]{10})', text, re.IGNORECASE)
    if cig_match:
        result['cig'] = cig_match.group(1)

    # CUP
    cup_match = re.search(r'CUP\s*[:\s]+([A-Z0-9]{15})', text, re.IGNORECASE)
    if cup_match:
        result['cup'] = cup_match.group(1)

    return result

def extract_importi(text: str) -> List[float]:
    """Estrae tutti gli importi in euro da un testo."""
    import re

    # Pattern per importi con € o senza
    euro_pattern = r'€?\s*[\d]{1,3}(?:[.,]\d{3})*(?:[.,]\d{2})?'
    matches = re.findall(euro_pattern, text)

    importi = []
    for match in matches:
        # Pulizia
        clean = match.replace('€', '').replace('.', '').replace(',', '.').strip()
        if clean:
            try:
                importi.append(float(clean))
            except ValueError:
                pass

    return importi

def extract_date(text: str) -> List[str]:
    """Estrae tutte le date in formato DD/MM/YYYY."""
    date_pattern = r'\b\d{2}/\d{2}/\d{4}\b'
    return re.findall(date_pattern, text)

def extract_nomi_propri(text: str) -> List[str]:
    """Estrae nomi propri (persone, enti) da un testo."""
    # Pattern per nomi in MAIUSCOLO
    names = re.findall(r'\b[A-ZÀ-Ú][A-ZÀ-Ú\'\s-]{2,}\b', text)
    # Filtra nomi troppo corti o generici
    return [n.strip() for n in names if len(n) > 2 and not n.isdigit()]

# ============================================================================
# INTEGRAZIONE CON ANALYZE_ALBO.PY ESISTENTE
# ============================================================================

def get_extended_personnel_patterns() -> Dict[str, Pattern]:
    """Ritorna i pattern estesi per competenze del personale."""
    return PERSONNEL_PATTERNS

def get_extended_accounting_patterns() -> List[Pattern]:
    """Ritorna i pattern estesi per contabilità."""
    return ACCOUNTING_PATTERNS

def get_category_specific_patterns(category: str) -> Dict[str, Pattern]:
    """Ritorna i pattern specifici per una categoria di documento."""
    category_map = {
        'determinazione': DETERMINAZIONE_PATTERNS,
        'delibera': DELIBERA_PATTERNS,
        'ordinanza': ORDINANZA_PATTERNS,
        'numeraria': NUMERARIA_PATTERNS,
        'atto': ATTO_PATTERNS,
        'avviso': AVVISO_PATTERNS,
        'bando': BANDO_PATTERNS,
    }
    return category_map.get(category, {})

if __name__ == '__main__':
    # Test
    all_patterns = get_all_patterns()
    print(f"Totale pattern caricati: {len(all_patterns)}")
    print(f"Pattern contabilità: {len(ACCOUNTING_PATTERNS)}")
    print(f"Pattern competenze: {len(PERSONNEL_PATTERNS)}")
    print(f"Pattern Determine: {len(DETERMINAZIONE_PATTERNS)}")
    print(f"Pattern Delibere: {len(DELIBERA_PATTERNS)}")
    print(f"Pattern Ordinanze: {len(ORDINANZA_PATTERNS)}")
    print(f"Pattern Numeraria: {len(NUMERARIA_PATTERNS)}")
    print(f"Pattern Atti: {len(ATTO_PATTERNS)}")
    print(f"Pattern Avvisi: {len(AVVISO_PATTERNS)}")
    print(f"Pattern Bandi: {len(BANDO_PATTERNS)}")
    print(f"Pattern Trasversali: {len(TRANSVERSAL_PATTERNS)}")
