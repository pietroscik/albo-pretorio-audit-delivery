from __future__ import annotations
from typing import Iterable, Dict, Any, Optional
import abc
import json
from pathlib import Path
import sys


class AdapterError(RuntimeError):
    pass


class Adapter(abc.ABC):
    """
    Interfaccia minima per gli adapter provider -> produce records normalizzati (dict).
    Implementazioni devono emettere un iterabile di dict JSON-serializable.
    """

    @abc.abstractmethod
    def run(self, ente: str, limit: Optional[int] = None) -> Iterable[Dict[str, Any]]:
        raise NotImplementedError

    def dump_to_file(self, ente: str, out: Optional[Path] = None, limit: Optional[int] = None) -> Path:
        out = Path(out) if out is not None else Path(f"data/{ente}/adapter_output.jsonl")
        out.parent.mkdir(parents=True, exist_ok=True)
        with out.open("w", encoding="utf-8") as fh:
            for rec in self.run(ente, limit=limit):
                fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
        return out


def validate_record(r: Dict[str, Any]) -> None:
    required = ("source", "external_id", "title", "published_at", "documents")
    for k in required:
        if k not in r:
            raise AdapterError(f"Missing required field '{k}' in record: {r.get('external_id')}")
    if not isinstance(r["documents"], list):
        raise AdapterError("Field 'documents' must be a list")