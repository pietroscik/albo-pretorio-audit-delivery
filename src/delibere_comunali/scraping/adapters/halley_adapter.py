from __future__ import annotations
import argparse
import hashlib
import json
from datetime import datetime
from typing import Iterable, Dict, Any, Optional
from delibere_comunali.scraping.adapter import Adapter, validate_record


class HalleyAdapter(Adapter):
    """
    Esempio minimale: costruisce record normalizzati per il provider "halley".
    Sostituire `fetch_*` con logica reale (requests / playwright / scrapy).
    """

    def _fake_fetch_items(self, ente: str, limit: Optional[int] = None):
        # stub: simulazione di paginazione -> sostituire con scraping reale
        sample = [
            {
                "external_id": f"{ente}-2026-001",
                "title": "Delibera su esempio",
                "published_at": "2026-01-15T10:00:00Z",
                "documents": [
                    {"url": "https://halley.example/allegato1.pdf", "filename": "allegato1.pdf"}
                ],
                "meta": {"tipo": "Delibera"},
            },
        ]
        for i, item in enumerate(sample):
            if limit and i >= limit:
                break
            yield item

    def run(self, ente: str, limit: Optional[int] = None) -> Iterable[Dict[str, Any]]:
        for raw in self._fake_fetch_items(ente, limit=limit):
            # normalizzazione: aggiungere source, hash su documenti, ISO date
            rec = {
                "source": "halley",
                "external_id": raw["external_id"],
                "title": raw["title"],
                "published_at": raw["published_at"],
                "raw_meta": raw.get("meta", {}),
                "documents": [],
            }
            for d in raw.get("documents", []):
                url = d.get("url")
                fn = d.get("filename") or url.split("/")[-1]
                # costruire id di dedup basico: sha256(url)
                digest = hashlib.sha256(url.encode("utf-8")).hexdigest() if url else ""
                rec["documents"].append({"url": url, "filename": fn, "content_hash": digest})
            validate_record(rec)
            yield rec


def cli():
    p = argparse.ArgumentParser()
    p.add_argument("--ente", required=True)
    p.add_argument("--out", help="Output jsonl file (default data/<ente>/adapter_output.jsonl)")
    p.add_argument("--limit", type=int, default=None)
    args = p.parse_args()
    adapter = HalleyAdapter()
    out = adapter.dump_to_file(args.ente, out=args.out, limit=args.limit)
    print(out)


if __name__ == "__main__":
    cli()