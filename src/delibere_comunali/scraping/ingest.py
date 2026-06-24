from __future__ import annotations
import argparse
import json
from pathlib import Path
from typing import Iterable, Dict, Any
from datetime import datetime
import csv
import requests  # aggiunto per il download degli allegati


def normalize_iso(s: str) -> str:
    try:
        dt = datetime.fromisoformat(s.replace("Z", "+00:00"))
        return dt.astimezone().isoformat()
    except Exception:
        return s


def ingest_jsonl(path: Path, ente: str) -> Path:
    path = Path(path)
    out_dir = Path("data") / ente / "albo_download"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_jsonl = out_dir / "albo_metadati.jsonl"
    out_csv = out_dir / "albo_metadati.csv"

    rows = []
    with path.open("r", encoding="utf-8") as fh_in, out_jsonl.open("w", encoding="utf-8") as fh_out:
        for line in fh_in:
            rec = json.loads(line)
            rec["published_at"] = normalize_iso(rec.get("published_at", ""))
            fh_out.write(json.dumps(rec, ensure_ascii=False) + "\n")

            # download primo documento (se URL presente) e costruisci nome file stabile
            first_doc_name = ""
            docs = rec.get("documents") or []
            if isinstance(docs, list) and docs:
                first = docs[0]
                fn = first.get("filename") or (first.get("url") or "").split("/")[-1] or ""
                url = first.get("url") or ""
                if fn:
                    # sanitizza e rende univoco: <external_id>_<filename>
                    safe_fn = fn.replace(" ", "_")
                    saved_name = f"{rec.get('external_id','noid')}_{safe_fn}"
                    saved_path = out_dir / saved_name
                    if url:
                        try:
                            resp = requests.get(url, timeout=20, stream=True)
                            resp.raise_for_status()
                            with saved_path.open("wb") as sf:
                                for chunk in resp.iter_content(8192):
                                    if chunk:
                                        sf.write(chunk)
                        except Exception:
                            # fallback: se download fallisce, non bloccare pipeline
                            saved_name = fn  # lascia il nome originale (non presente sul fs)
                    else:
                        # se non c'è url, non scarichiamo; ma creiamo nome per coerenza
                        saved_name = saved_name
                    first_doc_name = saved_name

            raw_meta = rec.get("raw_meta") or {}
            tipologia = rec.get("tipologia") or raw_meta.get("tipo") or raw_meta.get("tipologia") or ""
            rows.append({
                "external_id": rec.get("external_id", ""),
                "source": rec.get("source", ""),
                "title": rec.get("title", ""),
                "published_at": rec.get("published_at", ""),
                "raw_meta": json.dumps(raw_meta, ensure_ascii=False),
                "documents": json.dumps(rec.get("documents", []), ensure_ascii=False),
                "allegati": first_doc_name or "",
                "oggetto": rec.get("title", ""),
                "tipologia": tipologia,
            })

    # write CSV so legacy analyze_albo finds data/albo_metadati.csv
    fieldnames = ["external_id", "source", "title", "published_at", "raw_meta", "documents", "allegati", "oggetto", "tipologia"]
    with out_csv.open("w", encoding="utf-8", newline="") as fh_csv:
        writer = csv.DictWriter(fh_csv, fieldnames=fieldnames)
        writer.writeheader()
        for r in rows:
            writer.writerow(r)

    return out_jsonl


def cli():
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument("jsonl", help="adapter output (.jsonl)")
    p.add_argument("--ente", required=True)
    args = p.parse_args()
    out = ingest_jsonl(Path(args.jsonl), args.ente)
    print(out)


if __name__ == "__main__":
    cli()