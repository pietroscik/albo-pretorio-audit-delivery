#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Orchestrates the analysis/training/validation pipeline."""

import sys
import subprocess
from pathlib import Path
import argparse

def get_project_root() -> Path:
    """Trova la root del progetto cercando pyproject.toml."""
    path = Path(__file__).resolve()
    for _ in range(5):  # Max 5 livelli su
        if (path / "pyproject.toml").exists():
            return path
        path = path.parent
    return Path(__file__).resolve().parent.parent.parent.parent  # Fallback

PROJECT_ROOT = get_project_root()

def run_step(command, title, cwd=None, optional=False):
    print("\n" + "=" * 72)
    print(f"STEP: {title}")
    print(f"CMD : {' '.join(map(str, command))}")
    print("=" * 72)
    result = subprocess.run(command, cwd=cwd or PROJECT_ROOT)
    if result.returncode != 0:
        if optional:
            print(f"⚠️  Step opzionale fallito (skip): {title}")
            return result
        raise SystemExit(result.returncode)
    return result

def resolve_base_path(base: str, ente: str) -> str:
    base_path = Path(base)
    if (base_path / "albo_metadati.csv").exists() or (base_path / "albo_metadati.jsonl").exists():
        return str(base_path)
    parent = base_path.parent
    if (parent / "albo_metadati.csv").exists() or (parent / "albo_metadati.jsonl").exists():
        return str(parent)
    fallback = Path("data") / ente / "albo_download"
    return str(fallback)

def _module_command(module: str, extra_args=None):
    cmd = [sys.executable, "-m", module]
    if extra_args:
        cmd.extend(extra_args)
    return cmd

def _script_command(script_rel: str, extra_args=None):
    script = PROJECT_ROOT / script_rel
    cmd = [sys.executable, str(script)]
    if extra_args:
        cmd.extend(extra_args)
    return cmd

def _script_exists(script_rel: str) -> bool:
    return (PROJECT_ROOT / script_rel).exists()

def main() -> None:
    p = argparse.ArgumentParser(description="Pipeline orchestration")
    p.add_argument("--ente", required=True, help="ente identifier")
    p.add_argument("--base", default=None, help="base dir (optional)")
    p.add_argument("--adapter", help="adapter name (e.g. halley)")
    p.add_argument("--adapter-out", help="path for adapter jsonl output")
    p.add_argument("--limit", type=int, default=None)
    # LLM
    p.add_argument("--use-llm", action="store_true",
                    help="abilita arricchimento LLM nel parsing e audit")
    p.add_argument("--llm-provider", default=None,
                    help="provider LLM (openai, anthropic, ollama...)")
    p.add_argument("--llm-model", default=None,
                    help="modello LLM da usare")
    # Skip/only
    p.add_argument("--skip-scrape", action="store_true",
                    help="salta lo scraping")
    p.add_argument("--skip-clean", action="store_true",
                    help="salta la pulizia testi")
    p.add_argument("--skip-kg", action="store_true",
                    help="salta il Knowledge Graph")
    p.add_argument("--skip-audit", action="store_true",
                    help="salta il motore di audit")
    p.add_argument("--skip-validate", action="store_true",
                    help="salta la validazione output")
    p.add_argument("--only-audit", action="store_true",
                    help="esegui solo audit")
    p.add_argument("--only-analyze", action="store_true",
                    help="esegui solo parsing/analyze")
    p.add_argument("--force", action="store_true",
               help="Ignora cache e forza ri-elaborazione")
    args = p.parse_args()

    ente = args.ente
    base_arg = args.base or f"./data/{ente}/albo_download"
    resolved_base = resolve_base_path(base_arg, ente)
    limit_args = ["--limit", str(args.limit)] if args.limit else []

    # flag LLM da propagare agli step che li supportano
    llm_args = []
    if args.use_llm:
        llm_args.append("--use-llm")
    if args.llm_provider:
        llm_args.extend(["--llm-provider", args.llm_provider])
    if args.llm_model:
        llm_args.extend(["--llm-model", args.llm_model])

    # =========================================================
    # FASE 1: SCRAPING
    # =========================================================
    if not args.skip_scrape and not args.only_audit and not args.only_analyze:
        if args.adapter:
            adapter_module = f"delibere_comunali.scraping.adapters.{args.adapter}_adapter"
            adapter_out = args.adapter_out or f"data/{ente}/adapter_output.jsonl"
            run_step(
                _module_command(adapter_module, ["--ente", ente, "--out", adapter_out] + limit_args),
                f"Adapter scrape ({args.adapter})"
            )
            run_step(
                _module_command("delibere_comunali.scraping.ingest", [adapter_out, "--ente", ente]),
                "Ingest adapter output -> albo_download"
            )
        else:
            run_step(
                _module_command("delibere_comunali.scraping.new_albo_scraper", ["--ente", ente] + limit_args),
                "Scrape documents"
            )

    # =========================================================
    # FASE 2: ANALISI / PARSING (+ LLM opzionale)
    # =========================================================
    if not args.only_audit:
        run_step(
    _module_command(
        "delibere_comunali.parsing.analyze_albo",
        ["--base", resolved_base, "--ente", ente] + llm_args + (["--force"] if args.force else [])
    ),
    f"Analyze documents {'(+LLM)' if args.use_llm else ''}"
)

    # =========================================================
    # FASE 3: PULIZIA TESTI
    # =========================================================
    if not args.skip_clean and not args.only_audit:
        if _script_exists("scripts/clean_texts.py"):
            run_step(
                _script_command("scripts/clean_texts.py", ["--base", resolved_base]),
                "Clean texts"
            )
        else:
            print("⚠️  scripts/clean_texts.py non trovato (skip)")

    # =========================================================
    # FASE 4: KNOWLEDGE GRAPH
    # =========================================================
    if not args.skip_kg and not args.only_audit and not args.only_analyze:
        if _script_exists("scripts/build_knowledge_graph.py"):
            run_step(
                _script_command("scripts/build_knowledge_graph.py", ["--base", resolved_base]),
                "Build Knowledge Graph",
                optional=True
            )
        else:
            print("⚠️  scripts/build_knowledge_graph.py non trovato (skip)")

        if _script_exists("scripts/analyze_topology.py"):
            run_step(
                _script_command("scripts/analyze_topology.py", ["--base", resolved_base]),
                "Analyze Topology",
                optional=True
            )

    # =========================================================
    # FASE 5: AUDIT ENGINE (+ LLM opzionale)
    # =========================================================
    if not args.skip_audit and not args.only_analyze:
        run_step(
            _module_command(
                "delibere_comunali.processing.audit_engine",
                ["--base", resolved_base, "--ente", ente] + llm_args
            ),
            f"Audit Engine {'(+LLM)' if args.use_llm else ''}"
        )

    # =========================================================
    # FASE 6: VALIDAZIONE OUTPUT
    # =========================================================
    if not args.skip_validate and not args.only_analyze:
        if _script_exists("scripts/validate_output.py"):
            run_step(
                _script_command("scripts/validate_output.py", ["--base", resolved_base]),
                "Validate output",
                optional=True
            )

    print("\n" + "=" * 72)
    print(f"✅ Pipeline completata per '{ente}' → {resolved_base}")
    if args.use_llm:
        print(f"   LLM: {args.llm_provider or 'default'} / {args.llm_model or 'default'}")
    print("=" * 72)

if __name__ == "__main__":
    main()