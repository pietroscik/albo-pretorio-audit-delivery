from collections import defaultdict
from typing import DefaultDict, Dict, Iterable, List, Set

import hashlib

from src.models.administrative_event import AdministrativeEvent, ActorType
from src.models.procedure import Procedure


class ProcedureBuilder:
    """Costruisce procedimenti a partire dagli eventi amministrativi."""

    def __init__(self):
        self.procedures: Dict[str, Procedure] = {}
        self.beneficiary_count: DefaultDict[str, int] = defaultdict(int)
        self._beneficiary_procedures: DefaultDict[str, Set[str]] = defaultdict(set)

    def _reset(self) -> None:
        self.procedures = {}
        self.beneficiary_count = defaultdict(int)
        self._beneficiary_procedures = defaultdict(set)

    def add_event(self, event: AdministrativeEvent) -> str:
        procedure_id = self._get_procedure_id(event)
        if procedure_id not in self.procedures:
            self.procedures[procedure_id] = Procedure(procedure_id=procedure_id)

        for actor in event.actors:
            if actor.actor_type == ActorType.BENEFICIARIO and actor.name not in {"NON IDENTIFICATO", "DIVERSI/NON APPLICABILE"}:
                self.beneficiary_count[actor.name] += 1
                self._beneficiary_procedures[actor.name].add(procedure_id)

        self.procedures[procedure_id].add_event(event)
        return procedure_id

    def link_events_by_cig(self, events: Iterable[AdministrativeEvent]) -> Dict[str, Procedure]:
        self._reset()
        for event in events:
            self.add_event(event)
        return dict(self.procedures)

    def _get_procedure_id(self, event: AdministrativeEvent) -> str:
        """Determina l'ID del procedimento basato su CIG/CUP o hash stabile."""
        if event.cig:
            return f"CIG_{event.cig}"
        if event.cup:
            return f"CUP_{event.cup}"
        seed = f"{event.title or ''}_{event.document_date or ''}_{event.metadata.get('ente', '')}"
        digest = hashlib.sha1(seed.encode("utf-8")).hexdigest()[:16]
        return f"HASH_{digest}"

    def get_all_procedures(self) -> List[Procedure]:
        return list(self.procedures.values())

    def detect_anomalies(self) -> Dict[str, List[str]]:
        """Rileva anomalie topologiche e procedurali."""
        anomalies: Dict[str, List[str]] = defaultdict(list)

        for beneficiary, count in self.beneficiary_count.items():
            if count >= 3:
                for proc_id in self._beneficiary_procedures.get(beneficiary, set()):
                    anomalies[proc_id].append(
                        f"VIOLAZIONE ROTAZIONE FORNITORI: il fornitore {beneficiary} compare in {count} atti distinti."
                    )

        for proc_id, procedure in self.procedures.items():
            event_types = [event.event_type.value for event in procedure.events]
            if procedure.events and len(event_types) >= 5:
                most_common = max(event_types.count(event_type) for event_type in set(event_types))
                if most_common / len(event_types) >= 0.8:
                    anomalies[proc_id].append(
                        f"FRAMMENTAZIONE PROCEDIMENTALE: {len(procedure.events)} eventi sul procedimento con prevalenza di {event_types[0]}."
                    )
            if "Liquidazione" in event_types and "Impegno di spesa" not in event_types:
                anomalies[proc_id].append(
                    f"PROCEDIMENTO INCOMPLETO: il procedimento {proc_id} presenta una liquidazione ma manca l'atto di impegno."
                )

        return dict(anomalies)
