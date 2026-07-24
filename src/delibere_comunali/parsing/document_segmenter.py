"""
Document Segmenter - Motore di segmentazione strutturale per atti amministrativi.

Divide un documento legale (delibera, determinazione, ecc.) in sezioni semantiche:
- Intestazione: Metadati del documento (numero, data, tipologia, ecc.)
- Premessa: Contesto, riferimenti normativi, considerazioni
- Dispositivo: Decisioni effettive (importi, affidamenti, ecc.)
- Allegati: Riferimenti a documenti allegati

Questo modulo risolve il "vuoto semantico" permettendo di:
1. Assegnare un peso diverso alle entità in base alla sezione
2. Evitare falsi positivi (es. importi citati in premessa ma non nel dispositivo)
3. Estrarre informazioni strutturate con contesto legale
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Dict, List, Optional, Tuple


class SectionType(Enum):
    """Tipi di sezioni in un documento amministrativo."""

    INTESTAZIONE = "intestazione"
    PREMESSA = "premessa"
    DISPOSITIVO = "dispositivo"
    ALLEGATI = "allegati"
    ALTRO = "altro"


@dataclass
class DocumentSection:
    """Rappresenta una sezione di un documento."""

    section_type: SectionType
    text: str
    start_line: int
    end_line: int
    confidence: float  # 0.0-1.0


class DocumentSegmenter:
    """
    Segmenta un documento amministrativo in sezioni semantiche.

    Utilizza pattern basati su:
    - Parole chiave tipiche di ogni sezione
    - Struttura tipica degli atti amministrativi
    - Regole di transizione tra sezioni
    """

    def __init__(self):
        # Pattern per rilevare l'inizio di ogni sezione
        self.section_patterns = {
            SectionType.INTESTAZIONE: {
                "keywords": [
                    r"Comune di",
                    r"Albo Pretorio",
                    r"N\.?\s*[0-9]+",
                    r"Data\s+[0-9]{2}/[0-9]{2}/[0-9]{4}",
                    r"Determinazione",
                    r"Delibera",
                    r"Ordinanza",
                    r"Decreto",
                    r"Oggetto:",
                    r"Prot\.?\s*[0-9]+",
                    r"Rep\.?\s*[0-9]+",
                ],
                "start_weight": 1.0,  # Priorità massima per l'intestazione
                "end_weight": 0.1,  # Bassa priorità per la fine
            },
            SectionType.PREMESSA: {
                "keywords": [
                    r"Visto",
                    r"Considerato",
                    r"Richiamato",
                    r"Atteso",
                    r"Dato atto",
                    r"Preso atto",
                    r"Ritenuto",
                    r"Valutato",
                    r"Premesso che",
                    r"In considerazione",
                    r"Per le ragioni",
                    r"[Vv]isto",
                    r"[Cc]onsiderato",
                    r"[Rr]ichiamato",
                    r"[Dd]ato atto",
                    r"[Pp]reso atto",
                    r"[Aa]cquisito",
                    r"[Rr]itenuto",
                ],
                "start_weight": 0.9,
                "end_weight": 0.3,
            },
            SectionType.DISPOSITIVO: {
                "keywords": [
                    r"Determina",
                    r"Delibera",
                    r"Ordina",
                    r"Dispone",
                    r"Impegna",
                    r"Liquida",
                    r"Affida",
                    r"Assegna",
                    r"Autorizza",
                    r"Approva",
                    r"Respinge",
                    r"Revoca",
                    r"[Dd]etermina",
                    r"[Dd]ispone",
                    r"[Ii]mpegna",
                    r"[Ll]iquida",
                ],
                "start_weight": 0.95,
                "end_weight": 0.5,
            },
            SectionType.ALLEGATI: {
                "keywords": [
                    r"Allegato",
                    r"Documentazione",
                    r"PDF",
                    r"File",
                    r"Si allega",
                    r"Come da allegato",
                    r"Documenti allegati",
                    r"[Aa]llegato",
                ],
                "start_weight": 0.8,
                "end_weight": 0.2,
            },
        }

        # Pattern per rilevare la fine di una sezione
        self.section_end_patterns = [
            r"\n\s*\n",  # Paragrafo vuoto
            r"\n[\-\*\=]{3,}\n",  # Separatore orizzontale
            r"\n[A-Z][A-Z\s]+:\n",  # Intestazione nuova sezione
        ]

    def segment(self, text: str) -> List[DocumentSection]:
        """
        Segmenta un documento in sezioni semantiche.

        Args:
            text: Testo del documento da segmentare

        Returns:
            Lista di DocumentSection ordinate per posizione nel documento
        """
        if not text or not text.strip():
            return []

        lines = text.split("\n")
        sections = []
        current_section = None
        current_text = []
        current_section_start_line = 0

        for line_num, line in enumerate(lines):
            line_stripped = line.strip()

            # Salta linee vuote (ma le contiamo per la numerazione)
            if not line_stripped:
                if current_text:
                    current_text.append(line)
                continue

            # Verifica se questa linea inizia una nuova sezione
            new_section_type = self._detect_section_start(line_stripped)

            if new_section_type and new_section_type != current_section:
                # Salva la sezione corrente (se esiste)
                if current_section and current_text:
                    section_text = "\n".join(current_text)
                    sections.append(
                        DocumentSection(
                            section_type=current_section,
                            text=section_text,
                            start_line=current_section_start_line,
                            end_line=line_num - 1,
                            confidence=self._calculate_confidence(
                                current_section, section_text
                            ),
                        )
                    )

                # Inizia una nuova sezione
                current_section = new_section_type
                current_section_start_line = line_num
                current_text = [line]
            else:
                # Continua la sezione corrente
                if current_section:
                    current_text.append(line)
                else:
                    # Se non abbiamo ancora una sezione, iniziamo con ALTRO
                    current_section = SectionType.ALTRO
                    current_section_start_line = line_num
                    current_text = [line]

        # Salva l'ultima sezione
        if current_section and current_text:
            section_text = "\n".join(current_text)
            sections.append(
                DocumentSection(
                    section_type=current_section,
                    text=section_text,
                    start_line=current_section_start_line,
                    end_line=len(lines) - 1,
                    confidence=self._calculate_confidence(
                        current_section, section_text
                    ),
                )
            )

        # Se non abbiamo trovato nessuna sezione, restituisci tutto come ALTRO
        if not sections:
            sections.append(
                DocumentSection(
                    section_type=SectionType.ALTRO,
                    text=text,
                    start_line=0,
                    end_line=len(lines) - 1,
                    confidence=0.5,
                )
            )

        # Unisci sezioni adiacenti dello stesso tipo
        sections = self._merge_adjacent_sections(sections)

        return sections

    def _detect_section_start(self, line: str) -> Optional[SectionType]:
        """
        Rileva se una linea segna l'inizio di una nuova sezione.

        Args:
            line: Linea di testo da analizzare

        Returns:
            SectionType se rilevata una nuova sezione, None altrimenti
        """
        for section_type, config in self.section_patterns.items():
            for keyword in config["keywords"]:
                if re.search(keyword, line, re.IGNORECASE):
                    return section_type
        return None

    def _calculate_confidence(self, section_type: SectionType, text: str) -> float:
        """
        Calcola la confidenza che una sezione sia correttamente identificata.

        Args:
            section_type: Tipo di sezione
            text: Testo della sezione

        Returns:
            Confidenza (0.0-1.0)
        """
        if not text.strip():
            return 0.0

        config = self.section_patterns.get(section_type, {})
        if not config:
            return 0.5

        # Conta quante keyword della sezione sono presenti nel testo
        keyword_count = 0
        for keyword in config["keywords"]:
            if re.search(keyword, text, re.IGNORECASE):
                keyword_count += 1

        # Normalizza in base al numero di keyword
        max_keywords = len(config["keywords"])
        confidence = min(1.0, keyword_count / max_keywords * config["start_weight"])

        return max(confidence, 0.1)  # Minimo 0.1

    def _merge_adjacent_sections(
        self, sections: List[DocumentSection]
    ) -> List[DocumentSection]:
        """
        Unisce sezioni adiacenti dello stesso tipo.

        Args:
            sections: Lista di sezioni da unire

        Returns:
            Lista di sezioni unificate
        """
        if not sections:
            return sections

        merged = [sections[0]]

        for section in sections[1:]:
            if section.section_type == merged[-1].section_type:
                # Unisci con l'ultima sezione
                merged[-1].text += "\n" + section.text
                merged[-1].end_line = section.end_line
                # Aggiorna confidenza (media ponderata)
                merged[-1].confidence = (merged[-1].confidence + section.confidence) / 2
            else:
                merged.append(section)

        return merged

    def get_section_text(
        self, sections: List[DocumentSection], section_type: SectionType
    ) -> str:
        """
        Ottiene il testo di una specifica sezione.

        Args:
            sections: Lista di sezioni segmentate
            section_type: Tipo di sezione da estrarre

        Returns:
            Testo della sezione, o stringa vuota se non trovata
        """
        for section in sections:
            if section.section_type == section_type:
                return section.text
        return ""

    def get_section_confidence(
        self, sections: List[DocumentSection], section_type: SectionType
    ) -> float:
        """
        Ottiene la confidenza di una specifica sezione.

        Args:
            sections: Lista di sezioni segmentate
            section_type: Tipo di sezione

        Returns:
            Confidenza (0.0-1.0), o 0.0 se non trovata
        """
        for section in sections:
            if section.section_type == section_type:
                return section.confidence
        return 0.0


class WeightedEntityExtractor:
    """
    Estrattore di entità con pesatura basata sulla sezione.

    Assegna un peso diverso alle entità in base alla sezione in cui si trovano:
    - Dispositivo: Peso alto (entità rilevanti per l'audit)
    - Intestazione: Peso medio (metadati) + BOOST per entità di protocollo
      (CIG, CUP, ecc.)
    - Premessa: Peso basso (contesto, possibili falsi positivi)
    - Allegati: Peso medio (riferimenti a documenti)

    Regole speciali:
    - Entità di protocollo (CIG, CUP, numero_atto, data_atto, oggetto) in
      Intestazione: boost a 1.0
    - Altre entità in Intestazione: peso 0.6
    - Entità in Premessa: peso 0.3 (falsi positivi)
    - Entità in Dispositivo: peso 1.0 (rilevanti)
    """

    # Pesi per ogni sezione
    SECTION_WEIGHTS = {
        SectionType.INTESTAZIONE: 0.6,  # Ridotto da 0.7 a 0.6
        SectionType.PREMESSA: 0.3,
        SectionType.DISPOSITIVO: 1.0,
        SectionType.ALLEGATI: 0.6,
        SectionType.ALTRO: 0.5,
    }

    # Entità di protocollo che meritano boost se trovate in Intestazione
    PROTOCOL_ENTITIES = {"cig", "cup", "numero_atto", "data_atto", "oggetto"}

    def __init__(self, segmenter: DocumentSegmenter):
        self.segmenter = segmenter

    def extract_with_weights(self, text: str, entity_extractor) -> Dict[str, Dict]:
        """
        Estrae entità con pesatura basata sulla sezione.

        Args:
            text: Testo del documento
            entity_extractor: Funzione che estrae entità da un testo
                (es. lambda text: {"amounts": [...], "companies": [...]})

        Returns:
            Dizionario con entità e pesi:
            {
                "amounts": [
                    {"value": 1000, "weight": 1.0, "section": "dispositivo"}, ...
                ],
                "companies": [
                    {"name": "Ditta X", "weight": 0.3, "section": "premessa"}, ...
                ]
            }
        """
        # Segmenta il documento
        sections = self.segmenter.segment(text)

        # Inizializza il risultato
        weighted_entities = {}

        # Estrai entità da ogni sezione
        for section in sections:
            section_text = section.text
            if not section_text.strip():
                continue

            # Estrai entità dalla sezione
            entities = entity_extractor(section_text)

            for entity_type, entity_list in entities.items():
                if entity_type not in weighted_entities:
                    weighted_entities[entity_type] = []

                for entity in entity_list:
                    # Determina il peso in base alla sezione e al tipo di entità
                    weight = self._get_entity_weight(entity_type, section.section_type)

                    weighted_entities[entity_type].append(
                        {
                            "value": entity,
                            "weight": weight,
                            "section": section.section_type.value,
                            "confidence": section.confidence,
                        }
                    )

        return weighted_entities

    def _get_entity_weight(self, entity_type: str, section_type: SectionType) -> float:
        """
        Calcola il peso di un'entità in base al tipo di entità e sezione.

        Args:
            entity_type: Tipo di entità (es. 'cig', 'beneficiario', 'importi_raw')
            section_type: Tipo di sezione

        Returns:
            Peso (0.0-1.0)
        """
        # Entità di protocollo in Intestazione: boost a 1.0
        if (
            section_type == SectionType.INTESTAZIONE
            and entity_type.lower() in self.PROTOCOL_ENTITIES
        ):
            return 1.0

        # Peso standard per la sezione
        return self.SECTION_WEIGHTS.get(section_type, 0.5)

    def get_high_confidence_entities(
        self, weighted_entities: Dict[str, Dict], min_weight: float = 0.7
    ) -> Dict[str, List]:
        """
        Filtra le entità con peso superiore a una soglia.

        Args:
            weighted_entities: Entità con pesi (da extract_with_weights)
            min_weight: Peso minimo per includere un'entità

        Returns:
            Dizionario con solo entità ad alta confidenza
        """
        high_confidence = {}

        for entity_type, entities in weighted_entities.items():
            high_confidence[entity_type] = [
                e["value"] for e in entities if e["weight"] >= min_weight
            ]

        return high_confidence


# Funzione di utilità per segmentare e estrarre in un solo passo
def segment_and_extract(
    text: str, entity_extractor
) -> Tuple[List[DocumentSection], Dict[str, Dict]]:
    """
    Segmenta un documento ed estrae entità con pesatura.

    Args:
        text: Testo del documento
        entity_extractor: Funzione che estrae entità da un testo

    Returns:
        Tupla di (sezioni, entità con pesi)
    """
    segmenter = DocumentSegmenter()
    extractor = WeightedEntityExtractor(segmenter)

    sections = segmenter.segment(text)
    weighted_entities = extractor.extract_with_weights(text, entity_extractor)

    return sections, weighted_entities
